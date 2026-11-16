"""Reads config/io-map.yaml (from the IO list) when it is there.

Only the "safety" defaults are used for now. If the file or PyYAML is missing,
the built-in defaults in canbus/messages.py are used, which match it.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .canbus import messages as M

log = logging.getLogger("teryx.config")

IO_MAP = Path(__file__).resolve().parent.parent / "config" / "io-map.yaml"

# io-map safety key -> (setting name, multiplier)
_SAFETY = {
    "heartbeat_timeout_ms": ("heartbeat_timeout_ms", 1),
    "speed_timeout_ms": ("speed_timeout_ms", 1),
    "fourwd_max_kmh": ("fourwd_max_kmh", 1),
    "fourwd_max_run_s": ("fourwd_max_run_ms", 1000),
    "fourwd_overcurrent_a": ("fourwd_overcurrent_da", 10),
    "diff_max_kmh": ("diff_max_kmh", 1),
    "diff_max_run_s": ("diff_max_run_ms", 1000),
    "diff_overcurrent_a": ("diff_overcurrent_da", 10),
    "tray_max_run_s": ("tray_max_run_ms", 1000),
    "tray_overcurrent_a": ("tray_overcurrent_da", 10),
    "winch_dead_time_ms": ("winch_dead_time_ms", 1),
    "winch_auto_disarm_s": ("winch_auto_disarm_s", 1),
    "shutdown_wait_s": ("shutdown_wait_s", 1),
    "hold_to_run_timeout_ms": ("hold_to_run_timeout_ms", 1),
}


def safety_defaults(path: Path = IO_MAP) -> dict[str, int]:
    settings = M.default_settings()
    if not path.exists():
        return settings
    try:
        import yaml
    except ImportError:
        log.info("PyYAML not installed, using built-in safety defaults")
        return settings
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for key, value in (data.get("safety") or {}).items():
        if key in _SAFETY and isinstance(value, (int, float)) and not isinstance(value, bool):
            name, mult = _SAFETY[key]
            settings[name] = int(round(value * mult))
    return settings
