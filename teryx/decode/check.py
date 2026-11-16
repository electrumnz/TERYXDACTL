"""Check a .dbc against a capture, and install it.

    python -m teryx decode check shinegle-draft.dbc captures/2026-11-20_1012
    python -m teryx decode install shinegle-draft.dbc

``check`` decodes the capture with the .dbc the same way the dash will, then
shows, step by step, what each Teryx value did, and puts every reading Sam
typed next to the decoded value at that moment. If the numbers line up, the
.dbc is right.

``install`` copies the .dbc to teryx/canbus/shinegle.dbc (the one file the
sim, dash and tests load), regenerates the protocol docs, and tells you if the
Pico firmware's speed frame no longer matches.
"""

from __future__ import annotations

import re
import shutil
import statistics
from collections import defaultdict
from pathlib import Path

from ..canbus.shinegle import Layout
from .session import Session, load

REPO = Path(__file__).resolve().parents[2]
INSTALLED = REPO / "teryx" / "canbus" / "shinegle.dbc"
FIRMWARE_PROTOCOL = REPO / "firmware" / "control-box" / "src" / "core" / "protocol.h"


def decode_timeline(layout: Layout, session: Session) -> list[tuple[float, dict]]:
    state: dict = {}
    out = []
    for f in session.frames:
        m = layout.by_id.get(f.id)
        if m is None or m.extended != f.ext:
            continue
        layout.merge(state, m, m.decode(f.data))
        out.append((f.t, dict(state)))
    return out


def _at(timeline, t: float) -> dict:
    import bisect
    i = bisect.bisect_right([x[0] for x in timeline], t) - 1
    return timeline[i][1] if i >= 0 else {}


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".")
    if isinstance(v, list):
        return ",".join(v) or "-"
    return str(v)


def check(dbc: str | Path, capture: str | Path) -> str:
    layout = Layout.from_file(dbc)
    session = load(capture)
    timeline = decode_timeline(layout, session)
    lines = [f"# Check of {Path(dbc).name} against {session.path.name if session.path else capture}", ""]
    if not timeline:
        lines += ["**Nothing decoded.** None of the ids in the .dbc are in this capture."]
        return "\n".join(lines) + "\n"
    times = [t for t, _ in timeline]

    readings = [(st, r) for st, r in session.readings]
    if readings:
        lines += ["## Readings vs decoded", "", "| Step | Value | You read | We decoded | OK? |", "|---|---|---|---|---|"]
        bad = 0
        for st, r in readings:
            got = _at(timeline, r.t).get(f"mc.{r.name}")
            if got is None:
                ok = "not in .dbc"
            else:
                tol = max(abs(r.value) * 0.05, 1.0)
                ok = "yes" if abs(float(got) - r.value) <= tol else "**NO**"
                bad += ok != "yes"
            lines.append(f"| {st.title} | {r.name} | {_fmt(r.value)} | {_fmt(got) if got is not None else '-'} | {ok} |")
        lines += ["", f"{len(readings) - bad} of {len(readings)} readings match (within 5% or 1 unit).", ""]

    lines += ["## Step by step", ""]
    for st in session.steps:
        if st.skipped or st.end is None:
            continue
        lo = next((i for i, t in enumerate(times) if t >= st.start), None)
        if lo is None:
            continue
        rows = [s for t, s in timeline[lo:] if t < st.end]
        if not rows:
            lines += [f"### {st.title}", "", "No frames.", ""]
            continue
        lines += [f"### {st.title}", "", "| Value | Min | Typical | Max |", "|---|---|---|---|"]
        keys = sorted({k for s in rows for k in s})
        for k in keys:
            vals = [s[k] for s in rows if k in s]
            if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
                lines.append(f"| {k} | {_fmt(min(vals))} | {_fmt(statistics.median(vals))} | {_fmt(max(vals))} |")
            else:
                seen = []
                for v in vals:
                    v = _fmt(v)
                    if not seen or seen[-1] != v:
                        seen.append(v)
                lines.append(f"| {k} | | {' > '.join(seen[:12])}{' ...' if len(seen) > 12 else ''} | |")
        if st.phases:
            by_phase = defaultdict(set)
            for p_i, p in enumerate(st.phases):
                end = st.phases[p_i + 1].t if p_i + 1 < len(st.phases) else st.end
                mid = _at(timeline, (p.t + end) / 2)
                for k in ("mc.direction", "mc.mode", "mc.brake", "mc.faults", "mc.throttle"):
                    if k in mid:
                        by_phase[p.label].add(f"{k[3:]}={_fmt(mid[k])}")
            lines += ["", "Mid-phase: " + "; ".join(f"**{lab}**: {', '.join(sorted(v))}" for lab, v in by_phase.items())]
        lines.append("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- install

def firmware_speed_frame() -> int | None:
    if not FIRMWARE_PROTOCOL.exists():
        return None
    m = re.search(r"#define\s+CAN_ID_MC_SPEED\s+0x([0-9A-Fa-f]+)", FIRMWARE_PROTOCOL.read_text())
    return int(m.group(1), 16) if m else None


def firmware_matches(layout: Layout) -> tuple[bool, str]:
    """The Pico reads speed from bytes 0-1 (u16 LE x0.1) and direction from byte 2 of one frame."""
    m = layout.speed_message
    fw = firmware_speed_frame()
    if m is None:
        return False, "the .dbc has no speed signal, so the Pico can't get speed for its interlocks"
    speed = next((s for s in m.signals if s.name == "speed"), None)
    direction = next((s for s in m.signals if s.name == "direction"), None)
    ok = (fw == m.can_id and not m.extended and speed is not None and speed.start == 0 and speed.length == 16
          and not speed.big_endian and abs(speed.scale - 0.1) < 1e-9 and speed.offset == 0
          and direction is not None and direction.start == 16 and direction.length == 8
          and layout.direction.get(1) == "forward" and layout.direction.get(2) == "reverse")
    if ok:
        return True, "matches the Pico firmware's speed frame"
    return False, (f"the Pico firmware reads speed from 0x{fw:03X} bytes 0-1 and direction from byte 2, "
                   f"but the new layout has speed in {m.name} (0x{m.can_id:X}). The firmware "
                   "(firmware/control-box/src/core/controller.c, CAN_ID_MC_SPEED) needs updating "
                   "before the control box goes on the real bus.")


def install(dbc: str | Path, target: Path = INSTALLED) -> list[str]:
    layout = Layout.from_file(dbc)      # refuses a file that won't load
    msgs = []
    if not layout.messages:
        raise ValueError("that .dbc has no messages")
    if layout.speed_message is None:
        msgs.append("WARNING: no 'speed' signal (or rpm with teryx.kmh_per_rpm), so the dash shows 0 km/h.")
    shutil.copyfile(dbc, target)
    msgs.append(f"installed {dbc} -> {target}")
    ok, why = firmware_matches(layout)
    msgs.append(("OK: " if ok else "TODO: ") + why)
    return msgs
