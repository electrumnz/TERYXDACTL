"""Our own CAN messages: Pi 5 dash <-> Pico 2 control box (IDs 0x700-0x71F).

Layouts follow the IO list (docs/io-list.md, section 6) and config/io-map.yaml.
All values little-endian. The Shinegle's frames live in ``shinegle.py``.

The dash only ever *asks*. The control box decides if a request is safe, does
it (or not), and reports what the outputs are actually doing.
"""

from __future__ import annotations

from .codec import Message, Signal as S


# ---------------------------------------------------------------- enums
PICO_STATE = {0: "boot", 1: "ok", 2: "degraded", 3: "failsafe"}
DASH_STATE = {0: "boot", 1: "ok", 2: "shutting_down"}
FOURWD_STATE = {0: "2wd", 1: "4wd", 2: "to_4wd", 3: "to_2wd", 4: "fault"}
TRAY_STATE = {0: "down", 1: "up", 2: "mid", 3: "raising", 4: "lowering", 5: "fault"}
DIFF_STATE = {0: "idle", 1: "moving", 2: "fault"}
LIGHT_EFFECT = {0: "none", 1: "strobe", 2: "chase", 3: "outside_only", 4: "inside_only", 5: "breathe"}
REJECT_REASON = {
    0: "none",
    1: "too_fast",        # speed above the limit for that action
    2: "not_stopped",     # needs speed 0
    3: "speed_unknown",   # no Shinegle speed, so "stopped" can't be proven
    4: "not_armed",       # winch not armed
    5: "interlock",       # e.g. tray while winching
    6: "actuator_fault",
    7: "low_12v",
}
REJECT_TEXT = {
    "too_fast": "Slow down first",
    "not_stopped": "Stop the Teryx first",
    "speed_unknown": "No speed signal, can't confirm stopped",
    "not_armed": "Arm the winch first",
    "interlock": "Blocked by another action",
    "actuator_fault": "Actuator fault, check it",
    "low_12v": "12V supply too low",
}
FAULT_BITS = {   # 0x710 bytes 1-2
    0: "dash_link",
    1: "speed_unknown",
    2: "fourwd_timeout",
    3: "fourwd_overcurrent",
    4: "diff_timeout",
    5: "diff_pot_stuck",
    6: "tray_timeout",
    7: "tray_overcurrent",
    8: "tray_limit_switch",
    9: "winch_interlock",
    10: "low_12v",
    11: "pico_hot",
    12: "watchdog_reset",
}
RELAY_BITS = {   # 0x711 byte 0, relay 1 = bit 0
    0: "light.rear",
    1: "trailer.tail",
    2: "trailer.brake",
    3: "winch.in",
    4: "winch.out",
    5: "winch.isolator",
    6: "aux.accessory",
    7: "power.hold",
}
INPUT_BITS = {   # 0x710 byte 3, MCP23017 B0-B7
    0: "in.ignition",
    1: "in.brake",
    2: "in.reverse",
    3: "in.tray_down",
    4: "in.tray_up",
    5: "in.winch_remote",
    6: "in.park",
    7: "in.spare",
}
FRONT_LIGHTS = ("light.front_1", "light.front_2", "light.front_3", "light.front_4")
PWM_LIGHTS = FRONT_LIGHTS + ("light.interior",)

# ---------------------------------------------------------------- Pi -> Pico
PI_HEARTBEAT = Message(
    "PI_HEARTBEAT", 0x700, "dash", 100,
    comment="Pico stops tray, winch and actuators if this goes quiet for 500 ms.",
    signals=(
        S("counter", 0, 8),
        S("dash_state", 8, 8, choices=DASH_STATE),
    ),
)
PI_LIGHTS = Message(
    "PI_LIGHTS", 0x701, "dash", 1000,
    comment="On change, plus a resend every 1 s. Brightness 0-255 (0 = off). "
            "On/off-only bars treat anything above 0 as on.",
    signals=(
        S("front_1", 0, 8), S("front_2", 8, 8), S("front_3", 16, 8), S("front_4", 24, 8),
        S("interior", 32, 8),
        S("effect", 40, 8, choices=LIGHT_EFFECT),
        S("rear_on", 48, 1),
        S("rear_auto", 49, 1, comment="Rear pods on automatically in reverse"),
        S("counter", 56, 8),
    ),
)
PI_DRIVE = Message(
    "PI_DRIVE", 0x702, "dash", 1000,
    comment="On change, plus a resend every 1 s.",
    signals=(
        S("fourwd_req", 0, 8, comment="0 = 2WD, 1 = 4WD"),
        S("diff_target", 8, 8, unit="%"),
        S("counter", 56, 8),
    ),
)
PI_HOLD = Message(
    "PI_HOLD", 0x703, "dash", 100,
    comment="Hold-to-run, sent at 10 Hz only while a button is held. "
            "Pico stops if it goes quiet for 300 ms.",
    signals=(
        S("tray", 0, 8, signed=True, comment="-1 down, 0 stop, +1 up"),
        S("winch", 8, 8, signed=True, comment="-1 out, 0 stop, +1 in"),
        S("winch_armed", 16, 1),
        S("counter", 56, 8),
    ),
)
PI_SETTINGS = Message(
    "PI_SETTINGS", 0x704, "dash", 0,
    comment="On change, one key per frame. The Pico echoes it on 0x714 as an ack. "
            "Keys are in SETTINGS below. 0xF0 = save to flash, 0xF1 = reset defaults.",
    signals=(
        S("key", 0, 8),
        S("value", 16, 16),
    ),
)
PI_FW_UPDATE = Message(
    "PI_FW_UPDATE", 0x71F, "dash", 0,
    comment="Pico reboots to its bootloader when magic = 0x5445 ('TE') and parked.",
    signals=(S("magic", 0, 16),),
)

# ---------------------------------------------------------------- Pico -> Pi
PICO_STATUS = Message(
    "PICO_STATUS", 0x710, "controlbox", 100,
    signals=(
        S("counter", 0, 8),
        S("fault_bits", 8, 16, comment="See FAULT_BITS"),
        S("inputs", 24, 8, comment="MCP23017 B0-B7, see INPUT_BITS"),
        S("state", 32, 2, choices=PICO_STATE),
        S("on_defaults", 35, 1, comment="Pico is running on default settings, please resend"),
        S("reject_reason", 40, 4, choices=REJECT_REASON, comment="Why the last request was refused"),
        S("reject_count", 44, 4, comment="Goes up by one each time a request is refused"),
        S("winch_armed", 48, 1),
    ),
)
PICO_OUTPUTS = Message(
    "PICO_OUTPUTS", 0x711, "controlbox", 100,
    comment="What the outputs are actually doing (after effects and safety).",
    signals=(
        S("relays", 0, 8, comment="See RELAY_BITS"),
        S("front_1", 8, 8), S("front_2", 16, 8), S("front_3", 24, 8), S("front_4", 32, 8),
        S("interior", 40, 8),
        S("effect", 48, 8, choices=LIGHT_EFFECT),
    ),
)
PICO_ACTUATORS = Message(
    "PICO_ACTUATORS", 0x712, "controlbox", 100,
    signals=(
        S("diff_pct", 0, 8, unit="%", comment="From the actuator pot"),
        S("fourwd", 8, 8, choices=FOURWD_STATE),
        S("tray", 16, 8, choices=TRAY_STATE),
        S("diff_current", 24, 8, scale=0.1, unit="A"),
        S("fourwd_current", 32, 8, scale=0.1, unit="A"),
        S("tray_current", 40, 8, scale=0.1, unit="A"),
        S("tray_pct", 48, 8, unit="%", comment="Estimate from run time, no pot on the tray"),
        S("diff_target", 56, 8, unit="%"),
    ),
)
PICO_POWER = Message(
    "PICO_POWER", 0x713, "controlbox", 1000,
    signals=(
        S("aux_12v", 0, 16, scale=0.001, unit="V"),
        S("pico_temp", 16, 8, signed=True, unit="C"),
    ),
)

PICO_SETTINGS_ACK = Message(
    "PICO_SETTINGS_ACK", 0x714, "controlbox", 0,
    comment="Echo of each 0x704 frame once the Pico has applied it (value is what it actually used).",
    signals=(
        S("key", 0, 8),
        S("value", 16, 16),
    ),
)

# ---------------------------------------------------------------- bench only
BENCH_INPUTS = Message(
    "BENCH_INPUTS", 0x7E0, "sim", 100,
    comment="HOST/BENCH BUILD ONLY. Lets the simulator drive the Pico's wired inputs "
            "and inject faults. The real Pico firmware ignores it.",
    signals=(
        S("inputs", 0, 8, comment="Bits as INPUT_BITS"),
        S("force_mask", 8, 8, comment="Which input bits to force"),
        S("fault_inject", 16, 8, comment="See BENCH_FAULTS"),
    ),
)
BENCH_FAULTS = {0: "jam_diff", 1: "jam_tray", 2: "fourwd_overcurrent"}

TERYX_MESSAGES: tuple[Message, ...] = (
    PI_HEARTBEAT, PI_LIGHTS, PI_DRIVE, PI_HOLD, PI_SETTINGS, PI_FW_UPDATE,
    PICO_STATUS, PICO_OUTPUTS, PICO_ACTUATORS, PICO_POWER, PICO_SETTINGS_ACK,
    BENCH_INPUTS,
)

# ---------------------------------------------------------------- settings (0x704 keys)
# key: (name, unit, default, min, max). Defaults match config/io-map.yaml "safety".
SETTINGS: dict[int, tuple[str, str, int, int, int]] = {
    1: ("heartbeat_timeout_ms", "ms", 500, 100, 5000),
    2: ("speed_timeout_ms", "ms", 500, 100, 5000),
    3: ("fourwd_max_kmh", "km/h", 5, 0, 40),
    4: ("fourwd_max_run_ms", "ms", 3000, 500, 10000),
    5: ("fourwd_overcurrent_da", "0.1A", 60, 5, 300),
    6: ("diff_max_kmh", "km/h", 15, 0, 40),
    7: ("diff_max_run_ms", "ms", 4000, 500, 10000),
    8: ("diff_overcurrent_da", "0.1A", 80, 5, 300),
    9: ("tray_max_run_ms", "ms", 20000, 1000, 60000),
    10: ("tray_overcurrent_da", "0.1A", 100, 5, 300),
    11: ("winch_dead_time_ms", "ms", 100, 50, 1000),
    12: ("winch_auto_disarm_s", "s", 120, 10, 3600),
    13: ("shutdown_wait_s", "s", 30, 5, 300),
    14: ("diff_pot_min_raw", "raw", 1000, 0, 32767),
    15: ("diff_pot_max_raw", "raw", 25000, 0, 32767),
    16: ("light_dimmable_mask", "bits", 0b11111, 0, 31),
    17: ("hold_to_run_timeout_ms", "ms", 300, 100, 2000),
}
SETTING_SAVE = 0xF0
SETTING_RESET = 0xF1
SETTING_KEYS = {v[0]: k for k, v in SETTINGS.items()}


def default_settings() -> dict[str, int]:
    return {name: default for name, _u, default, _lo, _hi in SETTINGS.values()}


def bits_to_names(bits: int, table: dict[int, str]) -> list[str]:
    return [name for bit, name in table.items() if int(bits) & (1 << bit)]


def names_to_bits(names, table: dict[int, str]) -> int:
    rev = {v: k for k, v in table.items()}
    return sum(1 << rev[n] for n in set(names) if n in rev)


def enum_value(table: dict[int, str], name: str) -> int:
    return {v: k for k, v in table.items()}[name]
