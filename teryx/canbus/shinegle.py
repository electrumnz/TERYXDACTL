"""Shinegle SG1202 adapter. THE ONLY FILE THAT KNOWS THE SHINEGLE FRAME LAYOUT.

Everything else in Teryx OS works with the io-map names (mc.speed, mc.batt_v ...).
This file turns raw Shinegle CAN frames into those names, and (for the
simulator) turns them back into frames.

!!! PLACEHOLDER !!!
Shinegle don't publish their CAN layout. The IDs and bit positions below are
made up so we can build and test now. Once we've recorded the real bus with the
Shinegle dash + programmer plugged in (see docs/TEST_ENVIRONMENT.md, "Swapping
in the real Shinegle"), replace the Message definitions and the two functions
at the bottom. The dash, sim and tests keep working as long as ``decode``
still returns the same mc.* names.
"""

from __future__ import annotations

from .codec import Message, Signal as S

PLACEHOLDER = True

DIRECTION = {0: "neutral", 1: "forward", 2: "reverse"}
MODE = {0: "eco", 1: "normal", 2: "sport"}
FAULT_BITS = {   # mc.faults, 16-bit field
    0: "over_current",
    1: "over_voltage",
    2: "under_voltage",
    3: "motor_over_temp",
    4: "controller_over_temp",
    5: "hall_sensor",
    6: "throttle",
    7: "comms",
    8: "battery_over_temp",
    9: "precharge",
}
FAULT_TEXT = {
    "over_current": "Motor over current",
    "over_voltage": "Battery voltage too high",
    "under_voltage": "Battery voltage too low",
    "motor_over_temp": "Motor too hot",
    "controller_over_temp": "Controller too hot",
    "hall_sensor": "Motor position sensor fault",
    "throttle": "Throttle fault",
    "comms": "Controller comms fault",
    "battery_over_temp": "Battery too hot",
    "precharge": "Precharge fault",
}

SG_MOTOR = Message(
    "SG_MOTOR", 0x180, "shinegle", 50, placeholder=True,
    comment="Bytes 0-2 are what the Pico reads for its speed interlocks.",
    signals=(
        S("speed", 0, 16, scale=0.1, unit="km/h"),
        S("direction", 16, 8, choices=DIRECTION),
        S("mode", 24, 2, choices=MODE),
        S("ready", 26, 1),
        S("limp", 27, 1),
        S("brake", 28, 1),
        S("throttle", 32, 8, unit="%"),
        S("motor_rpm", 40, 16, signed=True, unit="rpm"),
        S("counter", 56, 8),
    ),
)
SG_BATTERY = Message(
    "SG_BATTERY", 0x181, "shinegle", 100, placeholder=True,
    signals=(
        S("batt_v", 0, 16, scale=0.1, unit="V"),
        S("batt_a", 16, 16, scale=0.1, signed=True, unit="A", comment="+ = draw, - = regen"),
        S("soc", 32, 8, unit="%"),
        S("counter", 56, 8),
    ),
)
SG_TEMPS = Message(
    "SG_TEMPS", 0x182, "shinegle", 500, placeholder=True,
    signals=(
        S("motor_temp", 0, 8, offset=-40, unit="C"),
        S("ctrl_temp", 8, 8, offset=-40, unit="C"),
        S("batt_temp", 16, 8, offset=-40, unit="C"),
        S("counter", 56, 8),
    ),
)
SG_FAULTS = Message(
    "SG_FAULTS", 0x183, "shinegle", 200, placeholder=True,
    signals=(
        S("faults", 0, 16),
        S("odometer", 16, 32, scale=0.1, unit="km"),
        S("counter", 56, 8),
    ),
)

SHINEGLE_MESSAGES: tuple[Message, ...] = (SG_MOTOR, SG_BATTERY, SG_TEMPS, SG_FAULTS)
SPEED_MESSAGE = SG_MOTOR   # the Pico watches this one for its speed interlocks


def decode(msg: Message, v: dict) -> dict:
    """Raw decoded Shinegle signals -> io-map mc.* values."""
    if msg is SG_MOTOR:
        return {
            "mc.speed": v["speed"],
            "mc.rpm": v["motor_rpm"],
            "mc.direction": DIRECTION.get(v["direction"], "neutral"),
            "mc.mode": MODE.get(v["mode"], "eco"),
            "mc.throttle": v["throttle"],
            "mc.brake": bool(v["brake"]),
            "mc.ready": bool(v["ready"]),
            "mc.limp": bool(v["limp"]),
        }
    if msg is SG_BATTERY:
        return {"mc.batt_v": v["batt_v"], "mc.batt_a": v["batt_a"], "mc.soc": v["soc"],
                "mc.power_kw": round(v["batt_v"] * v["batt_a"] / 1000, 2)}
    if msg is SG_TEMPS:
        return {"mc.motor_temp": v["motor_temp"], "mc.ctrl_temp": v["ctrl_temp"],
                "mc.batt_temp": v["batt_temp"]}
    if msg is SG_FAULTS:
        return {"mc.faults": [n for b, n in FAULT_BITS.items() if v["faults"] & (1 << b)],
                "mc.odometer": v["odometer"]}
    return {}


def encode(mc: dict) -> list[tuple[Message, dict]]:
    """io-map mc.* values -> list of (Message, raw values). Used by the simulator."""
    rev_dir = {n: k for k, n in DIRECTION.items()}
    rev_mode = {n: k for k, n in MODE.items()}
    rev_fault = {n: k for k, n in FAULT_BITS.items()}
    return [
        (SG_MOTOR, {
            "motor_rpm": mc["mc.rpm"], "speed": mc["mc.speed"],
            "direction": rev_dir[mc["mc.direction"]], "mode": rev_mode[mc["mc.mode"]],
            "throttle": mc["mc.throttle"],
            "brake": int(mc["mc.brake"]), "ready": int(mc["mc.ready"]), "limp": int(mc["mc.limp"]),
        }),
        (SG_BATTERY, {"batt_v": mc["mc.batt_v"], "batt_a": mc["mc.batt_a"], "soc": mc["mc.soc"]}),
        (SG_TEMPS, {"motor_temp": mc["mc.motor_temp"], "ctrl_temp": mc["mc.ctrl_temp"],
                    "batt_temp": mc["mc.batt_temp"]}),
        (SG_FAULTS, {"faults": sum(1 << rev_fault[f] for f in mc["mc.faults"]),
                     "odometer": mc["mc.odometer"]}),
    ]
