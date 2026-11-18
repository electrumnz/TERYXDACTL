"""Frames that keep a wrecked Toyota EPS column happy (docs/power-steering-wrecker.md).

A 2004-2009 Prius (gen 2) EPS ECU wants two CAN frames on its own 500 kbit/s
bus: engine RPM (0x2C4, from the engine computer) and vehicle speed (0x0B4,
from the ABS computer). Without them it sulks in limp mode with little
assist. Sending both every 20 ms wakes it straight away. Byte layouts come
from a working retrofit (Carloop community thread, see the doc); the last
byte is Toyota's usual checksum, checked against both frames from that thread.

This is only the signal side. The Toyota ECU still reads the torque sensor and
drives the motor itself, so if these frames stop the column goes back to limp
mode, and if the column loses power it steers like a manual column.
"""

from __future__ import annotations

EPS_BITRATE = 500_000
SEND_PERIOD_S = 0.020          # 20 ms, as in the working retrofit
RPM_ID = 0x2C4
SPEED_ID = 0x0B4
SPEED_LSB_KMH = 0.01           # thread: 0.0062 mph per bit, which is 0.01 km/h
MAX_ASSIST_KMH = 16.3          # 0x0666, the "10 mph" setting the thread ran for max assist
RPM_RUNNING = 1674             # 0x068A, the value the thread sends


def toyota_checksum(can_id: int, data: bytes) -> int:
    """Sum of the ID bytes, the length and every data byte but the last, low 8 bits."""
    total = (can_id >> 8) + (can_id & 0xFF) + len(data) + sum(data[:-1])
    return total & 0xFF


def _seal(can_id: int, body: bytearray) -> bytes:
    body[-1] = toyota_checksum(can_id, body)
    return bytes(body)


def rpm_frame(rpm: int = RPM_RUNNING) -> bytes:
    """0x2C4: engine RPM in bytes 0-1. The other bytes are copied from the thread."""
    rpm = max(0, min(int(rpm), 0xFFFF))
    return _seal(RPM_ID, bytearray([rpm >> 8, rpm & 0xFF, 0x00, 0x19, 0x00, 0x00, 0x92, 0x00]))


def speed_frame(kmh: float) -> bytes:
    """0x0B4: vehicle speed in bytes 5-6 at 0.01 km/h per bit."""
    raw = max(0, min(round(kmh / SPEED_LSB_KMH), 0xFFFF))
    return _seal(SPEED_ID, bytearray([0, 0, 0, 0, 0x8D, raw >> 8, raw & 0xFF, 0x00]))


def assist_speed_kmh(real_kmh: float | None, floor_kmh: float = MAX_ASSIST_KMH) -> float:
    """Speed to tell the EPS. Below the floor we report the floor, so crawling
    and parking get full assist with no dead zone. Above it, tell the truth so
    assist firms up. Unknown speed: report the floor (heavier never lighter
    than a real low speed, and the thread found it "drives great")."""
    if real_kmh is None or real_kmh < floor_kmh:
        return floor_kmh
    return float(real_kmh)


def frames(real_kmh: float | None, engine_ready: bool) -> list[tuple[int, bytes]]:
    """What to send this 20 ms tick. Nothing when the drive isn't ready (key off,
    vehicle locked, fault): the ECU then drops to limp mode, never to more assist."""
    if not engine_ready:
        return []
    return [(RPM_ID, rpm_frame()), (SPEED_ID, speed_frame(assist_speed_kmh(real_kmh)))]
