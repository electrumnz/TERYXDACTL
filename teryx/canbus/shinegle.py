"""Shinegle SG1202 adapter.

The Shinegle frame layout lives in ONE file: ``teryx/canbus/shinegle.dbc``.
This module loads it and turns raw Shinegle frames into the io-map names
(``mc.speed``, ``mc.batt_v`` ...) that the dash, sim and tests use, and (for
the simulator) turns io-map values back into frames.

The shipped .dbc is a PLACEHOLDER (made up so we could build first). The
decoding kit (``python -m teryx decode ...``, see docs/shinegle-decode.md)
writes a real one. Drop it in place and everything picks it up. Nothing in
here needs editing as long as the .dbc follows the naming rules below.

Signal naming rules in the .dbc (anything else is ignored by the dash):

    speed       km/h                 -> mc.speed
    rpm         motor rpm            -> mc.rpm      (motor_rpm works too)
    direction   value table with neutral / forward / reverse   -> mc.direction
    mode        value table with eco / normal / sport          -> mc.mode
    throttle    %                    -> mc.throttle
    brake, ready, limp   0/1         -> mc.brake, mc.ready, mc.limp
    batt_v, batt_a (+ = draw), soc   -> mc.batt_v, mc.batt_a, mc.soc
    motor_temp, ctrl_temp, batt_temp -> same names under mc.
    odometer    km                   -> mc.odometer
    fault_<name>   one bit each; the signal comment is the text the dash shows
    counter     rolling counter, filled in by the sim

If the controller only sends rpm, put ``teryx.kmh_per_rpm=<number>`` in the
file's general comment (CM_ "...") and speed is worked out from rpm.

Set the TERYX_SHINEGLE_DBC environment variable to try another .dbc without
replacing the shipped one.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from .codec import Message
from .dbc import load

DBC_PATH = Path(os.environ.get("TERYX_SHINEGLE_DBC") or Path(__file__).with_name("shinegle.dbc"))

_SIMPLE = {   # dbc signal name -> io-map name, plain numbers
    "speed": "mc.speed", "rpm": "mc.rpm", "motor_rpm": "mc.rpm", "throttle": "mc.throttle",
    "batt_v": "mc.batt_v", "batt_a": "mc.batt_a", "soc": "mc.soc",
    "motor_temp": "mc.motor_temp", "ctrl_temp": "mc.ctrl_temp", "batt_temp": "mc.batt_temp",
    "odometer": "mc.odometer",
    "error_code": "mc.error_code",   # the SG1810 ErrorCode (LED flash count), config/shinegle-faults.yaml
}
_FLAGS = {"brake": "mc.brake", "ready": "mc.ready", "limp": "mc.limp"}
_ENUMS = {"direction": ("mc.direction", "neutral"), "mode": ("mc.mode", "eco")}

# Every mc.* value the dash expects, with what to show before the first frame
# arrives (or forever, if the real controller doesn't send it).
MC_DEFAULTS = {
    "mc.speed": 0.0, "mc.rpm": 0, "mc.direction": "neutral", "mc.mode": "eco",
    "mc.throttle": 0, "mc.brake": False, "mc.ready": False, "mc.limp": False,
    "mc.batt_v": 0.0, "mc.batt_a": 0.0, "mc.soc": 0, "mc.power_kw": 0.0,
    "mc.motor_temp": 0, "mc.ctrl_temp": 0, "mc.batt_temp": 0,
    "mc.faults": [], "mc.odometer": 0.0, "mc.error_code": 0,
}


def _pretty(name: str) -> str:
    return name.replace("_", " ").capitalize()


class Layout:
    """One Shinegle layout (a loaded .dbc) with the io-map translation built in."""

    def __init__(self, messages, general: str = ""):
        self.messages: tuple[Message, ...] = tuple(messages)
        self.general = general
        self.placeholder = any(m.placeholder for m in self.messages) or "PLACEHOLDER" in general
        self.fault_bits: dict[int, str] = {}
        self.fault_text: dict[str, str] = {}
        self.fault_owner: dict[str, str] = {}
        self.direction = {0: "neutral", 1: "forward", 2: "reverse"}
        self.mode = {0: "eco", 1: "normal", 2: "sport"}
        self.speed_message = None
        for m in self.messages:
            for sig in m.signals:
                if sig.name.startswith("fault_"):
                    n = sig.name[len("fault_"):]
                    self.fault_bits[len(self.fault_bits)] = n
                    self.fault_text[n] = sig.comment or _pretty(n)
                    self.fault_owner[n] = m.name
                elif sig.name == "direction" and sig.choices:
                    self.direction = {k: v.lower() for k, v in sig.choices.items()}
                elif sig.name == "mode" and sig.choices:
                    self.mode = {k: v.lower() for k, v in sig.choices.items()}
                elif sig.name == "speed" and self.speed_message is None:
                    self.speed_message = m
        kmh = re.search(r"teryx\.kmh_per_rpm\s*=\s*([-+.\deE]+)", general)
        self.kmh_per_rpm = float(kmh.group(1)) if kmh else None
        if self.speed_message is None and self.kmh_per_rpm:   # speed worked out from rpm instead
            self.speed_message = next((m for m in self.messages for sig in m.signals
                                       if sig.name in ("rpm", "motor_rpm")), None)
        self.by_name = {m.name: m for m in self.messages}
        self.by_id = {m.can_id: m for m in self.messages}

    @classmethod
    def from_file(cls, path) -> Layout:
        return cls(*load(path, default_sender="shinegle"))

    def decode(self, msg: Message, v: dict) -> dict:
        """Raw decoded Shinegle signals -> io-map mc.* values (only what this frame carries)."""
        out: dict = {}
        faults = None
        for name, value in v.items():
            if name in _SIMPLE:
                out[_SIMPLE[name]] = value
            elif name in _FLAGS:
                out[_FLAGS[name]] = bool(value)
            elif name in _ENUMS:
                key, default = _ENUMS[name]
                table = self.direction if name == "direction" else self.mode
                out[key] = table.get(int(value), default)
            elif name.startswith("fault_"):
                faults = faults or []
                if value:
                    faults.append(name[len("fault_"):])
        if faults is not None:
            out["mc.faults"] = faults
        if "mc.speed" not in out and "mc.rpm" in out and self.kmh_per_rpm:
            out["mc.speed"] = round(abs(out["mc.rpm"]) * self.kmh_per_rpm, 1)
        if "mc.batt_v" in out and "mc.batt_a" in out:
            out["mc.power_kw"] = round(out["mc.batt_v"] * out["mc.batt_a"] / 1000, 2)
        return out

    def merge(self, state: dict, msg: Message, v: dict) -> None:
        """Fold one frame into a running state dict (power and faults can span frames)."""
        new = self.decode(msg, v)
        if "mc.faults" in new:
            others = [f for f in state.get("mc.faults", ()) if self.fault_owner.get(f) != msg.name]
            new["mc.faults"] = others + new["mc.faults"]
        state.update(new)
        if "mc.batt_v" in state and "mc.batt_a" in state:
            state["mc.power_kw"] = round(state["mc.batt_v"] * state["mc.batt_a"] / 1000, 2)

    def encode(self, mc: dict) -> list[tuple[Message, dict]]:
        """io-map mc.* values -> list of (Message, raw values). Used by the simulator."""
        rev = {"direction": {n: k for k, n in self.direction.items()},
               "mode": {n: k for k, n in self.mode.items()}}
        active = set(mc.get("mc.faults", ()))
        out = []
        for m in self.messages:
            values = {}
            for sig in m.signals:
                n = sig.name
                if n in _SIMPLE and _SIMPLE[n] in mc:
                    values[n] = mc[_SIMPLE[n]]
                elif n in _FLAGS:
                    values[n] = int(bool(mc.get(_FLAGS[n], False)))
                elif n in _ENUMS:
                    key, default = _ENUMS[n]
                    values[n] = rev[n].get(mc.get(key, default), 0)
                elif n.startswith("fault_"):
                    values[n] = int(n[len("fault_"):] in active)
            out.append((m, values))
        return out


LAYOUT = Layout.from_file(DBC_PATH)

# Module-level names the rest of Teryx OS uses
SHINEGLE_MESSAGES: tuple[Message, ...] = LAYOUT.messages
GENERAL_COMMENT = LAYOUT.general
PLACEHOLDER = LAYOUT.placeholder
FAULT_BITS, FAULT_TEXT = LAYOUT.fault_bits, LAYOUT.fault_text
DIRECTION, MODE = LAYOUT.direction, LAYOUT.mode
SPEED_MESSAGE, KMH_PER_RPM = LAYOUT.speed_message, LAYOUT.kmh_per_rpm
BY_NAME = LAYOUT.by_name
decode, merge, encode = LAYOUT.decode, LAYOUT.merge, LAYOUT.encode
