"""Control box (Pico) settings as shown on the Safety limits screen.

The real list comes from `teryx.canbus.messages.SETTINGS` (test environment work). If that
can't be imported (for example while working on the UI on its own), this fallback list is
used. Keys match the 0x704 table agreed between the dash, the simulator and the firmware.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class Setting:
    key: int
    name: str
    label: str
    default: int
    units: str = ""
    scale: float | None = None   # raw * scale = value shown (eg 0.1 A steps)
    step: int = 1
    min: int = 0
    max: int = 65535
    help: str = ""
    editable: bool = True


FALLBACK: list[Setting] = [
    Setting(1, "heartbeat_timeout_ms", "Dash lost after", 500, "ms", None, 50, 100, 5000, "Stop moving parts if the dash goes quiet this long."),
    Setting(2, "speed_timeout_ms", "Speed lost after", 500, "ms", None, 50, 100, 5000, "Treat speed as unknown if the motor controller goes quiet this long."),
    Setting(3, "fourwd_max_kmh", "2WD/4WD change below", 5, "km/h", None, 1, 0, 40),
    Setting(4, "fourwd_max_run_ms", "4WD actuator max run", 3000, "ms", None, 250, 500, 10000),
    Setting(5, "fourwd_overcurrent_da", "4WD actuator current limit", 60, "A", 0.1, 5, 5, 300),
    Setting(6, "diff_max_kmh", "Diff lock change below", 15, "km/h", None, 1, 0, 40),
    Setting(7, "diff_max_run_ms", "Diff actuator max run", 4000, "ms", None, 250, 500, 10000),
    Setting(8, "diff_overcurrent_da", "Diff actuator current limit", 80, "A", 0.1, 5, 5, 300),
    Setting(9, "tray_max_run_ms", "Tray max run", 20000, "ms", None, 1000, 1000, 60000),
    Setting(10, "tray_overcurrent_da", "Tray current limit", 100, "A", 0.1, 5, 5, 300),
    Setting(11, "winch_dead_time_ms", "Winch in/out dead time", 100, "ms", None, 50, 50, 1000),
    Setting(12, "winch_auto_disarm_s", "Winch auto disarm", 120, "s", None, 10, 10, 3600),
    Setting(13, "shutdown_wait_s", "Shutdown wait after key off", 30, "s", None, 5, 5, 300),
    Setting(14, "diff_pot_min_raw", "Diff pot open point", 1000, "raw", None, 1, 0, 32767, editable=False),
    Setting(15, "diff_pot_max_raw", "Diff pot locked point", 25000, "raw", None, 1, 0, 32767, editable=False),
    Setting(16, "light_dimmable_mask", "Dimmable lights", 0b11111, "", None, 1, 0, 31, editable=False),
    Setting(17, "hold_to_run_timeout_ms", "Hold-to-run stop after", 300, "ms", None, 50, 100, 2000, "Stop the tray or winch if the dash's repeats stop this long."),
]

SAVE_KEY = 0xF0
RESET_KEY = 0xF1


def _from_teryx() -> list[Setting] | None:
    """Use the shared CAN definitions if they're installed: key -> (name, unit, default, min, max)."""
    try:
        from teryx.canbus.messages import SETTINGS  # type: ignore
    except Exception:
        return None
    fb = {s.key: s for s in FALLBACK}
    out: list[Setting] = []
    for key, (name, unit, default, lo, hi) in sorted(SETTINGS.items()):
        base = fb.get(key)
        scale = 0.1 if unit == "0.1A" else None
        out.append(Setting(
            key=key, name=name,
            label=base.label if base else name.replace("_", " "),
            default=default, units="A" if scale else unit, scale=scale,
            step=base.step if base else 1, min=lo, max=hi,
            help=base.help if base else "", editable=base.editable if base else True,
        ))
    return out or None


def catalogue() -> list[Setting]:
    return _from_teryx() or FALLBACK


def by_name(name: str) -> Setting | None:
    return next((s for s in catalogue() if s.name == name), None)


def current_values(gateway: Any) -> dict[str, int]:
    """Last values the control box acked, by name. Falls back to defaults."""
    raw = getattr(gateway, "settings", None) or {}
    out = {}
    for s in catalogue():
        v = raw.get(s.name, raw.get(s.key, raw.get(str(s.key))))
        out[s.name] = int(v) if v is not None else s.default
    return out


def listing(gateway: Any) -> list[dict]:
    vals = current_values(gateway)
    return [{**asdict(s), "value": vals[s.name]} for s in catalogue()]
