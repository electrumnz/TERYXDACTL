import can
import pytest

from teryx.canbus.udpbus import FMT, UdpCanBus


def test_wire_format():
    pkt = FMT.pack(0x710, 8, 0, bytes(range(8)))
    assert len(pkt) == 16
    assert pkt[:4] == (0x710).to_bytes(4, "little")


def test_two_programs_share_the_bus():
    try:
        a, b = UdpCanBus(port=47123), UdpCanBus(port=47123)
    except OSError as e:
        pytest.skip(f"no multicast here: {e}")
    try:
        a.send(can.Message(arbitration_id=0x700, data=[1, 2, 3], is_extended_id=False))
        got = b.recv(1.0)
        assert got is not None and got.arbitration_id == 0x700 and bytes(got.data) == b"\x01\x02\x03"
        assert a.recv(0.1) is None   # doesn't hear itself
    finally:
        a.shutdown()
        b.shutdown()
