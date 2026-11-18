"""Our own CAN messages: Pi 5 dash <-> Pico 2 control box (IDs 0x700-0x71F).

Layouts follow the IO list (docs/io-list.md, section 6) and config/io-map.yaml.
All values little-endian. The Shinegle's frames live in ``shinegle.py``.

The dash only ever *asks*. The control box decides if a request is safe, does
it (or not), and reports what the outputs are actually doing.
"""

from __future__ import annotations

from .codec import Message, Signal as S
from ..regen import REGEN_LIMIT, REGEN_STATE


# ---------------------------------------------------------------- enums
PICO_STATE = {0: "boot", 1: "ok", 2: "degraded", 3: "failsafe"}
DASH_STATE = {0: "boot", 1: "ok", 2: "shutting_down", 3: "sentry"}   # sentry: docs/sentry.md
FOURWD_STATE = {0: "2wd", 1: "4wd", 2: "to_4wd", 3: "to_2wd", 4: "fault", 5: "unknown"}  # unknown = after boot, before the first move
TRAY_STATE = {0: "down", 1: "up", 2: "mid", 3: "raising", 4: "lowering", 5: "fault"}
DIFF_STATE = {0: "idle", 1: "moving", 2: "fault"}
LIGHT_EFFECT = {0: "none", 1: "strobe", 2: "chase", 3: "outside_only", 4: "inside_only", 5: "breathe", 6: "sos"}
REJECT_REASON = {
    0: "none",
    1: "too_fast",        # speed above the limit for that action
    2: "not_stopped",     # needs speed 0
    3: "speed_unknown",   # no Shinegle speed, so "stopped" can't be proven
    4: "not_armed",       # winch not armed
    5: "interlock",       # e.g. tray while winching
    6: "actuator_fault",
    7: "low_12v",
    8: "dash_link",       # request arrived while the dash link was down
    9: "ignition_off",
    10: "at_limit",       # e.g. tray up when already fully up
    11: "not_parked",     # firmware update needs the Teryx parked
    12: "winch_remote",   # handheld winch remote in use
    13: "bad_frame",
    14: "wait_timeout",   # 4WD / diff waited shift_wait_ms for the right speed and gave up
    15: "busy",           # another drive change is waiting or running
}
REJECT_TEXT = {
    "too_fast": "Slow down first",
    "not_stopped": "Stop the Teryx first",
    "speed_unknown": "No speed signal, can't confirm stopped",
    "not_armed": "Arm the winch first",
    "interlock": "Blocked by another action",
    "actuator_fault": "Actuator fault, check it",
    "low_12v": "12V supply too low",
    "dash_link": "Dash link was down",
    "ignition_off": "Key is off",
    "at_limit": "Already at the end of travel",
    "not_parked": "Park the Teryx first",
    "winch_remote": "Winch remote is in use",
    "bad_frame": "Request not understood",
    "wait_timeout": "Gave up waiting. Try again",
    "busy": "Wait for the last change to finish",
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
    13: "diff_overcurrent",
    14: "io_bus",          # MCP23017 or ADS1115 not answering
    15: "brake_pedal",     # brake pedal sensor out of range or disagrees with the brake switch
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
    7: "in.trailer",      # trailer plugged in: reed switch in the 7-pin socket (see docs/cameras.md)
}
# Vehicle lock (docs/vehicle-lock.md)
LOCK_CMD = {1: "lock", 2: "unlock", 3: "verify", 4: "set_pin", 5: "set_puk", 6: "remove",
            7: "remote"}   # remote: text from the owner's phone, docs/remote-access.md
LOCK_STATE = {0: "off", 1: "unlocked", 2: "locked"}
LOCK_RESULT = {
    0: "none", 1: "ok", 2: "wrong", 3: "not_parked", 4: "no_pin", 5: "lockout",
    6: "bad_digits", 7: "not_allowed", 8: "recovered", 9: "pending",
}
LOCK_RESULT_TEXT = {
    "wrong": "Wrong PIN",
    "not_parked": "Stop, put the park brake on and wait for everything to finish first",
    "no_pin": "Set a PIN first",
    "lockout": "Too many wrong tries. Wait, then try again",
    "bad_digits": "PIN must be 4 to 6 digits",
    "not_allowed": "Not allowed right now",
    "recovered": "Unlocked with the recovery code. Set a new PIN",
    "pending": "Remote lock: locks once it has been stopped for 10 s or the key is off",
}
LOCK_PIN_MIN, LOCK_PIN_MAX, LOCK_PUK_LEN = 4, 6, 8

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
        S("winch_timed_s", 24, 8, unit="s",
          comment="Timed pull length, 0 = plain hold. Pico stops it on time by itself, "
                  "capped at setting 21"),
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
PI_LOCK = Message(
    "PI_LOCK", 0x705, "dash", 0,
    comment="Vehicle lock command, on demand (docs/vehicle-lock.md). Digits are BCD, first digit "
            "in the high nibble of d0. PIN 4-6 digits, recovery code 8. The Pico keeps only a "
            "salted hash and answers on 0x716 straight away.",
    signals=(
        S("cmd", 0, 8, choices=LOCK_CMD),
        S("n_digits", 8, 8),
        S("d0", 16, 8), S("d1", 24, 8), S("d2", 32, 8), S("d3", 40, 8),
        S("counter", 48, 8),
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
        S("fourwd_wait", 36, 1, comment="A 2WD/4WD request is waiting for the right speed (docs/drive-changes.md)"),
        S("diff_wait", 37, 1, comment="A diff lock request is waiting for the right speed"),
        S("throttle_hold", 38, 1, comment="Throttle held: a shift is running from a standstill"),
        S("reject_reason", 40, 4, choices=REJECT_REASON, comment="Why the last request was refused"),
        S("reject_count", 44, 4, comment="Goes up by one each time a request is refused"),
        S("winch_armed", 48, 1),
        S("speed_valid", 49, 1),
        S("reverse_active", 50, 1),
        S("shutdown_request", 51, 1, comment="Key off: Pi should shut down"),
        S("parked", 52, 1, comment="Stopped and safe for OTA updates"),
        S("sentry_hold", 53, 1, comment="Key off, power kept on because the Pi asked for sentry"),
        S("sentry_flat", 54, 1, comment="Sentry refused: 12V under setting 32 (until the key goes on)"),
        S("speed", 56, 8, unit="km/h", comment="Speed as the Pico sees it, 255 = unknown"),
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
        S("diff_target", 56, 8, unit="%", comment="While diff_wait is set, the % it's waiting to move to"),
    ),
)
PICO_POWER = Message(
    "PICO_POWER", 0x713, "controlbox", 1000,
    signals=(
        S("aux_12v", 0, 16, scale=0.001, unit="V"),
        S("pico_temp", 16, 8, signed=True, unit="C"),
        S("diff_pot_raw", 24, 16, comment="Raw ADS1115 reading, for calibrating keys 14/15"),
        S("fw_major", 40, 8),
        S("fw_minor", 48, 8),
        S("winch_idle_s", 56, 8, unit="s", comment="Seconds since the winch last ran while armed (caps at 255)"),
    ),
)

PICO_SETTINGS_ACK = Message(
    "PICO_SETTINGS_ACK", 0x714, "controlbox", 0,
    comment="Echo of each 0x704 frame once the Pico has applied it (value is what it actually used).",
    signals=(
        S("key", 0, 8),
        S("status", 8, 8, choices={0: "ok", 1: "unknown_key", 2: "out_of_range", 3: "locked"}),
        S("value", 16, 16),
    ),
)

PICO_REGEN = Message(
    "PICO_REGEN", 0x715, "controlbox", 100,
    comment="Brake pedal regen (docs/brake-regen.md). All zero with state off while the feature is off.",
    signals=(
        S("pedal_pct", 0, 8, unit="%", comment="Brake pedal travel from the pedal sensor"),
        S("request_pct", 8, 8, unit="%", comment="Regen asked of the Shinegle, after every limit"),
        S("state", 16, 4, choices=REGEN_STATE),
        S("limit", 20, 4, choices=REGEN_LIMIT, comment="What is holding regen back, if anything"),
        S("pedal_raw", 24, 16, comment="Raw ADS1115 reading, for calibrating keys 28/29"),
        S("brake_light", 40, 1, comment="Regen is strong enough to light the brake lights"),
    ),
)

PICO_LOCK = Message(
    "PICO_LOCK", 0x716, "controlbox", 100,
    comment="Vehicle lock state (docs/vehicle-lock.md). Also sent straight after every 0x705.",
    signals=(
        S("state", 0, 8, choices=LOCK_STATE),
        S("tries_left", 8, 8, comment="Wrong tries left before a lockout"),
        S("lockout_s", 16, 16, unit="s", comment="Lockout time left"),
        S("window", 32, 1, comment="Change window open (PIN checked in the last 60 s)"),
        S("puk_set", 33, 1, comment="A recovery code is stored"),
        S("inhibit", 34, 1, comment="Drive inhibit asked for (how is TBC until the Shinegle is decoded)"),
        S("lockout", 35, 1),
        S("pending", 36, 1, comment="Remote lock asked for, waiting until stopped 10 s or key off"),
        S("result", 40, 8, choices=LOCK_RESULT, comment="Result of the last 0x705"),
        S("result_count", 48, 8, comment="Goes up by one per 0x705"),
        S("fails", 56, 8, comment="Wrong tries in a row (kept over power cuts)"),
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
        S("aux_mv", 24, 16, unit="mV", comment="Fake 12V reading, 0 = leave alone"),
    ),
)
BENCH_FAULTS = {0: "jam_diff", 1: "jam_tray", 2: "fourwd_overcurrent", 3: "pot_disconnected", 4: "io_bus_dead"}

TERYX_MESSAGES: tuple[Message, ...] = (
    PI_HEARTBEAT, PI_LIGHTS, PI_DRIVE, PI_HOLD, PI_SETTINGS, PI_LOCK, PI_FW_UPDATE,
    PICO_STATUS, PICO_OUTPUTS, PICO_ACTUATORS, PICO_POWER, PICO_SETTINGS_ACK, PICO_REGEN, PICO_LOCK,
    BENCH_INPUTS,
)

# ---------------------------------------------------------------- settings (0x704 keys)
# key: (name, unit, default, min, max). Defaults match config/io-map.yaml "safety".
SETTINGS: dict[int, tuple[str, str, int, int, int]] = {
    1: ("heartbeat_timeout_ms", "ms", 500, 100, 5000),
    2: ("speed_timeout_ms", "ms", 500, 100, 5000),
    3: ("fourwd_max_kmh", "km/h", 1, 0, 40),
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
    18: ("relay_active_low", "bool", 0, 0, 1),
    19: ("tray_full_travel_ms", "ms", 16000, 1000, 60000),
    20: ("low_12v_mv", "mV", 11000, 9000, 13000),
    21: ("winch_timed_max_s", "s", 30, 1, 120),
    # Brake pedal regen (docs/brake-regen.md). Off until the Shinegle is checked.
    22: ("brake_regen_on", "bool", 0, 0, 1),
    23: ("brake_regen_pct", "%", 50, 0, 100),
    24: ("brake_regen_start_pct", "%", 5, 0, 50),
    25: ("brake_regen_full_pct", "%", 30, 5, 100),
    26: ("brake_regen_fade_kmh", "km/h", 5, 0, 20),
    27: ("brake_regen_2wd_pct", "%", 60, 0, 100),
    28: ("brake_pedal_min_raw", "raw", 2000, 0, 32767),
    29: ("brake_pedal_max_raw", "raw", 22000, 0, 32767),
    # Safe drive changes (docs/drive-changes.md)
    30: ("shift_wait_ms", "ms", 10000, 0, 30000),
    31: ("shift_throttle_hold", "bool", 1, 0, 1),
    # Sentry (docs/sentry.md)
    32: ("sentry_min_12v_mv", "mV", 12200, 11000, 13500),
}
SETTING_SAVE = 0xF0
SETTING_RESET = 0xF1
SETTING_CLEAR_FAULTS = 0xF2
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
