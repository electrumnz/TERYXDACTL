"""Find the Shinegle's bit rate by listening at each common rate in turn.

    python -m teryx decode bitrate --port /dev/ttyACM0      (Teryx sniffer, Windows: COM5)
    sudo python -m teryx decode bitrate --socketcan can0    (Pi CAN HAT)

Always listen-only, so a wrong guess can't disturb the bus (a normal-mode
adaptor at the wrong rate sends error frames that can upset the controller).
"""

from __future__ import annotations

import subprocess
import time

RATES = (250_000, 500_000, 125_000, 1_000_000, 100_000, 50_000, 800_000, 20_000)


def _count(bus, seconds: float) -> tuple[int, set[int]]:
    end = time.monotonic() + seconds
    n, ids = 0, set()
    while time.monotonic() < end:
        m = bus.recv(0.1)
        if m is not None and not m.is_error_frame:
            n += 1
            ids.add(m.arbitration_id)
    return n, ids


def try_slcan(port: str, seconds: float = 2.0, rates=RATES, print_fn=print) -> int | None:
    from ..canbus.bus import open_bus
    best = (0, None)
    for rate in rates:
        try:
            bus = open_bus(f"slcan:{port}@{rate}", listen_only=True)
        except Exception as e:
            print_fn(f"  {rate // 1000:>5}k  couldn't open the adaptor: {e}")
            return None
        try:
            n, ids = _count(bus, seconds)
        finally:
            bus.shutdown()
        print_fn(f"  {rate // 1000:>5}k  {n:>5} frames, {len(ids)} ids")
        if n > best[0]:
            best = (n, rate)
    return best[1]


def try_socketcan(iface: str, seconds: float = 2.0, rates=RATES, print_fn=print) -> int | None:
    from ..canbus.bus import open_bus
    best = (0, None)
    for rate in rates:
        subprocess.run(["ip", "link", "set", iface, "down"], check=False)
        r = subprocess.run(["ip", "link", "set", iface, "up", "type", "can", "bitrate", str(rate),
                            "listen-only", "on", "restart-ms", "100"], capture_output=True, text=True)
        if r.returncode:
            print_fn(f"  {rate // 1000:>5}k  ip link failed (run with sudo?): {r.stderr.strip()}")
            return None
        bus = open_bus(f"socketcan:{iface}")
        try:
            n, ids = _count(bus, seconds)
        finally:
            bus.shutdown()
        print_fn(f"  {rate // 1000:>5}k  {n:>5} frames, {len(ids)} ids")
        if n > best[0]:
            best = (n, rate)
    return best[1]
