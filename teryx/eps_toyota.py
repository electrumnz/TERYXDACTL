"""Toyota Aqua EPS column: what the Pico tells it and how it reads it back.

Docs: docs/power-steering-aqua.md (Aqua build, bench test, assumptions) and
docs/power-steering-wrecker.md (why a wrecker column, where the frames came from).
Firmware twin: firmware/control-box/src/core/eps.c / eps.h. tests/test_eps_toyota.py
checks the numbers here match the C header and the settings table.

The column's own Toyota ECU (89650-52B51) reads the torque sensor and drives the
motor. The Pico only says "engine running" (0x2C4) and "this is our speed"
(0x0B4) every 20 ms on the column's own 500 kbit/s bus. Stop sending and it
drops back to limp mode, never to more assist. Lose power and it's a manual
column.

ASSUMED (until the bench test): the Aqua wants the same two frames as a
2004-09 Prius, the only Toyota EPS with a proven standalone recipe, and it talks
back with the same frames as the Toyota EPS ECUs in opendbc (0x260 torque and
angle, 0x262 status, diagnostics on 0x7A1/0x7A9). Every one of these lives in a
named constant or a dash setting, so a bench result is a one-line change.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------- what we send
EPS_BITRATE = 500_000          # ASSUMED: Toyota powertrain CAN rate
SEND_PERIOD_S = 0.020          # 20 ms, as in the working Prius retrofit (100 ms wasn't enough)
RPM_ID = 0x2C4                 # ASSUMED for the Aqua: engine RPM (Prius gen 2)
SPEED_ID = 0x0B4               # ASSUMED for the Aqua: vehicle speed (Prius gen 2, opendbc SPEED)
SPEED_LSB_KMH = 0.01           # Prius thread: 0.0062 mph per bit, which is 0.01 km/h
SPEED_ENCODER = 0x8D           # byte 4, copied from the retrofit
MAX_ASSIST_KMH = 16.3          # 0x0666, the "10 mph" setting the thread ran for max assist
RPM_RUNNING = 1674             # 0x068A, the value the thread sends

# ---------------------------------------------------------------- what we listen for
TORQUE_ID = 0x260              # ASSUMED: opendbc STEER_TORQUE_SENSOR
STATUS_ID = 0x262              # ASSUMED: opendbc EPS_STATUS (may not exist on a non-LKA Aqua)
DIAG_REQUEST_ID = 0x7A1        # Toyota EPS diagnostic address (opendbc fingerprints)
DIAG_REPLY_ID = 0x7A9
ANGLE_DEG_PER_BIT = 0.0573
STATUS_PERMANENT_FAULT = 17    # opendbc LKA_STATE "permanent_fault"

# ---------------------------------------------------------------- modes and states
MODE_MANUAL, MODE_LIMP, MODE_NORMAL = 0, 1, 2


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
    return _seal(SPEED_ID, bytearray([0, 0, 0, 0, SPEED_ENCODER, raw >> 8, raw & 0xFF, 0x00]))


@dataclass
class AssistCurve:
    """Settings 34-36. The Toyota ECU has its own speed-to-assist map; we only pick
    what speed to tell it. Below the floor: the floor (full assist when crawling).
    Above it: real speed x gain, capped."""
    floor_kmh: float = MAX_ASSIST_KMH
    gain_pct: int = 100
    max_kmh: int = 120

    @classmethod
    def from_settings(cls, s: dict) -> "AssistCurve":
        return cls(s.get("eps_floor_kmh_x10", 163) / 10, s.get("eps_speed_gain_pct", 100),
                   s.get("eps_max_kmh", 120))

    def told_kmh(self, real_kmh: float | None) -> float:
        v = 0.0 if real_kmh is None else real_kmh * self.gain_pct / 100
        return min(max(v, self.floor_kmh), float(self.max_kmh))


def assist_speed_kmh(real_kmh: float | None, floor_kmh: float = MAX_ASSIST_KMH) -> float:
    """Default curve: below the floor report the floor, above it the truth."""
    return AssistCurve(floor_kmh=floor_kmh, max_kmh=10_000).told_kmh(real_kmh)


def frames(real_kmh: float | None, engine_ready: bool, curve: AssistCurve | None = None,
           rpm: int = RPM_RUNNING) -> list[tuple[int, bytes]]:
    """What to send this 20 ms tick. Nothing when the drive isn't ready (key off,
    vehicle locked, fault): the ECU then drops to limp mode, never to more assist."""
    if not engine_ready:
        return []
    kmh = (curve or AssistCurve(max_kmh=10_000)).told_kmh(real_kmh)
    return [(RPM_ID, rpm_frame(rpm)), (SPEED_ID, speed_frame(kmh))]


def _be16(b: bytes) -> int:
    return int.from_bytes(b, "big", signed=True)


def decode_ecu_frame(can_id: int, data: bytes) -> dict | None:
    """What the Aqua ECU says, if it's a frame we know (for the sniffer and tests).
    Returns None for frames we don't know or with a bad checksum."""
    data = bytes(data)
    if can_id in (TORQUE_ID, STATUS_ID) and (len(data) < 5 or data[-1] != toyota_checksum(can_id, data)):
        return None
    if can_id == TORQUE_ID and len(data) == 8:
        return {
            "override": bool(data[0] & 0x01),
            "angle_init": bool(data[0] & 0x08),
            "torque_driver": _be16(data[1:3]),
            "angle_deg": round(_be16(data[3:5]) * ANGLE_DEG_PER_BIT, 2),
            "torque_eps": _be16(data[5:7]),
        }
    if can_id == STATUS_ID and len(data) >= 4:
        return {"lka_state": (data[3] >> 1) & 0x7F, "ipas_state": data[0] & 0x0F}
    return None
