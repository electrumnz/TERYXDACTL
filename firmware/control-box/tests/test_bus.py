#!/usr/bin/env python3
"""End-to-end check of the host build over the UDP bus, standard library only.

Starts control-box-host, plays the dash (heartbeat, requests) and the Shinegle
(speed), and checks what comes back on 0x710-0x714.

    python3 tests/test_bus.py path/to/control-box-host
"""
import os
import socket
import struct
import subprocess
import sys
import tempfile
import time

GROUP, PORT = "239.0.7.0", 47100 + os.getpid() % 500   # own port so it can't clash
FMT = struct.Struct("<IBB2x8s")


class Bus:
    def __init__(self):
        self.rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            self.rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.rx.bind((GROUP, PORT))
        mreq = struct.pack("4s4s", socket.inet_aton(GROUP), socket.inet_aton("127.0.0.1"))
        self.rx.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self.rx.setblocking(False)
        self.tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.tx.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 0)
        self.tx.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        self.tx.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton("127.0.0.1"))
        self.last = {}
        self.count = {}

    def send(self, can_id, data):
        data = bytes(data)
        self.tx.sendto(FMT.pack(can_id, len(data), 0, data.ljust(8, b"\0")), (GROUP, PORT))

    def drain(self):
        while True:
            try:
                pkt = self.rx.recv(64)
            except BlockingIOError:
                return
            if len(pkt) != 16:
                continue
            can_id, dlc, _f, data = FMT.unpack(pkt)
            if 0x710 <= can_id <= 0x714:
                self.last[can_id] = data[:dlc]
                self.count[can_id] = self.count.get(can_id, 0) + 1


def main():
    exe = sys.argv[1]
    bus = Bus()
    settings = tempfile.NamedTemporaryFile(delete=False).name
    os.unlink(settings)
    proc = subprocess.Popen([exe, "--bus", f"udp:{GROUP}:{PORT}", "--settings", settings, "--quiet"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    fails = []

    def check(cond, what):
        print(("ok   " if cond else "FAIL ") + what)
        if not cond:
            fails.append(what)

    state = {"speed": 0, "hold": None}

    def run(seconds):
        end = time.monotonic() + seconds
        n = 0
        while time.monotonic() < end:
            bus.send(0x700, [n & 0xFF, 1])
            bus.send(0x180, list(struct.pack("<H", state["speed"])) + [1, 0])
            if state["hold"] is not None:
                bus.send(0x703, state["hold"])
            n += 1
            for _ in range(10):
                bus.drain()
                time.sleep(0.01)

    try:
        run(1.0)
        check(bus.count.get(0x710, 0) >= 5, "status 0x710 arrives at about 10 Hz")
        st = bus.last.get(0x710, b"\0" * 8)
        check(st[4] & 0x03 == 1, "state ok once the dash and speed are there")
        check(st[4] & 0x08, "asks for settings (on defaults)")

        # Settings round trip
        bus.send(0x704, [3, 0] + list(struct.pack("<H", 8)))
        run(0.3)
        ack = bus.last.get(0x714)
        check(ack is not None and ack[0] == 3 and struct.unpack("<H", ack[2:4])[0] == 8, "setting acked on 0x714")

        # 4WD: refused at 20 km/h, done when stopped and asked again
        state["speed"] = 200
        run(0.3)
        bus.send(0x702, [1, 0])
        run(0.3)
        st = bus.last[0x710]
        check(st[5] & 0x0F == 1, "4WD refused when too fast (reject reason too_fast)")
        state["speed"] = 0
        bus.send(0x702, [0, 0])
        run(0.2)
        bus.send(0x702, [1, 0])
        run(2.5)
        check(bus.last[0x712][1] == 1, "4WD engaged when stopped")

        # Diff to 40 %
        bus.send(0x702, [1, 40])
        run(2.5)
        check(abs(bus.last[0x712][0] - 40) <= 3, f"diff reached 40 % (got {bus.last[0x712][0]})")

        # Lights
        bus.send(0x701, [255, 128, 128, 255, 60, 0, 0, 0])
        run(0.6)
        out = bus.last[0x711]
        check(list(out[1:6]) == [255, 128, 128, 255, 60], f"light levels applied ({list(out[1:6])})")
        check(out[0] & 0x02, "trailer tail on with front lights")

        # Tray hold-to-run, then let go
        state["hold"] = [1, 0, 0]
        run(1.5)
        check(bus.last[0x712][2] == 3, "tray raising while held")
        state["hold"] = None
        run(0.6)
        check(bus.last[0x712][2] == 2, "tray stops (mid) when released")

        # Bench frame: reverse input on, auto rear
        bus.send(0x701, [0, 0, 0, 0, 0, 0, 0x02, 0])
        bus.send(0x7E0, [0x05, 0x04, 0])
        run(0.4)
        check(bus.last[0x711][0] & 0x01, "rear pods on in reverse (bench input)")

        # Save settings, then firmware update request when parked
        bus.send(0x704, [0xF0, 0, 0, 0])
        bus.send(0x7E0, [0, 0, 0])
        run(0.2)
        bus.send(0x71F, [0x45, 0x54])
        time.sleep(0.3)
        run(0.5)
        check(bus.last[0x710][4] & 0x08 == 0, "came back from the update reboot with the saved settings")
    finally:
        proc.terminate()
        out, _ = proc.communicate(timeout=5)
        if os.path.exists(settings):
            os.unlink(settings)
    check("firmware update requested" in out, "host build acted out the bootloader reboot")
    print(f"\n{len(fails)} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
