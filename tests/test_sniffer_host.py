"""End to end: the sniffer firmware's host build, driven by python-can's slcan
driver and a raw GVRET handshake, with the test environment's UDP bus playing
the Shinegle. Linux only (needs cmake, a C compiler and pseudo terminals)."""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux") or not shutil.which("cmake"),
                                reason="needs Linux and cmake")
serial = pytest.importorskip("serial")

import can  # noqa: E402

from teryx.canbus.bus import open_bus  # noqa: E402

FW = Path(__file__).resolve().parent.parent / "firmware" / "can-sniffer"
PORT = 47600 + os.getpid() % 300
SPEC = f"udp:239.0.7.0:{PORT}"


@pytest.fixture(scope="module")
def host_binary(tmp_path_factory):
    build = tmp_path_factory.mktemp("sniffer-build")
    subprocess.run(["cmake", "-S", str(FW), "-B", str(build), "-DSNIFFER_HOST=ON"], check=True,
                   capture_output=True)
    subprocess.run(["cmake", "--build", str(build)], check=True, capture_output=True)
    return build / "can-sniffer-host"


@pytest.fixture
def sniffer(host_binary, tmp_path):
    def start(*extra):
        link = tmp_path / "ttySNIFF"
        p = subprocess.Popen([str(host_binary), "--bus", SPEC, "--link", str(link), *extra],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert p.stdout.readline().strip() == str(link)
        procs.append(p)
        return str(link)
    procs = []
    yield start
    for p in procs:
        p.terminate()
        p.wait(5)


def _shinegle(bus, n=20, can_id=0x180):
    for i in range(n):
        bus.send(can.Message(arbitration_id=can_id, data=bytes([i, 2, 3]), is_extended_id=False))
        bus.send(can.Message(arbitration_id=0x0CF11E05, data=bytes([i]), is_extended_id=True))
        time.sleep(0.005)


def _recv_all(bus, seconds=0.5):
    out, end = [], time.monotonic() + seconds
    while time.monotonic() < end:
        m = bus.recv(0.05)
        if m is not None:
            out.append(m)
    return out


def test_python_can_slcan_listen_only(sniffer):
    link = sniffer()
    udp = open_bus(SPEC)
    sl = open_bus(f"slcan:{link}@250000", listen_only=True)
    try:
        time.sleep(0.2)
        _shinegle(udp)
        got = _recv_all(sl)
        std = [m for m in got if not m.is_extended_id]
        ext = [m for m in got if m.is_extended_id]
        assert len(std) == 20 and std[5].arbitration_id == 0x180 and bytes(std[5].data) == bytes([5, 2, 3])
        assert len(ext) == 20 and ext[0].arbitration_id == 0x0CF11E05
        # Sending is refused without the TX jumper: nothing reaches the bus
        sl.send(can.Message(arbitration_id=0x123, data=b"\x01", is_extended_id=False))
        assert not [m for m in _recv_all(udp, 0.3) if m.arbitration_id == 0x123]
    finally:
        sl.shutdown()
        udp.shutdown()


def test_slcan_send_with_tx_jumper(sniffer):
    link = sniffer("--tx")
    udp = open_bus(SPEC)
    sl = open_bus(f"slcan:{link}@250000")    # normal mode
    try:
        time.sleep(0.2)
        sl.send(can.Message(arbitration_id=0x123, data=b"\x01\x02", is_extended_id=False))
        hits = [m for m in _recv_all(udp, 0.5) if m.arbitration_id == 0x123]
        assert hits and bytes(hits[0].data) == b"\x01\x02"
    finally:
        sl.shutdown()
        udp.shutdown()


def test_gvret_handshake_like_savvycan(sniffer):
    link = sniffer()
    udp = open_bus(SPEC)
    port = serial.Serial(link, 115200, timeout=0.5)
    try:
        port.write(bytes([0xE7, 0xE7, 0xF1, 0x07, 0xF1, 0x0C]))
        reply = port.read(11)
        assert reply[:2] == b"\xf1\x07" and reply[8:11] == b"\xf1\x0c\x01"
        _shinegle(udp, 3)
        data = port.read(3 * 2 * 12 + 20)
        frames = data.count(b"\xf1\x00")
        assert frames >= 4   # 3 standard (3 data bytes, 15 long) + 3 extended (13 long)
    finally:
        port.close()
        udp.shutdown()


def test_capture_tool_records_through_the_sniffer(sniffer, tmp_path):
    """The real capture path: Recorder on a python-can slcan bus through the sniffer."""
    from teryx.decode.capture import Recorder
    from teryx.decode.session import load
    link = sniffer()
    udp = open_bus(SPEC)
    sl = open_bus(f"slcan:{link}@250000", listen_only=True)
    rec = Recorder(sl, tmp_path / "bus.log").start()
    try:
        time.sleep(0.2)
        _shinegle(udp, 10)
        time.sleep(0.5)
    finally:
        rec.stop()
        sl.shutdown()
        udp.shutdown()
    frames = load(tmp_path / "bus.log").frames
    assert len(frames) == 20 and {f.id for f in frames} == {0x180, 0x0CF11E05}
