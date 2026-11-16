"""Write the CAN map as a .dbc file, for SavvyCAN, cantools, Kvaser etc.

The Python definitions stay the source of truth; this is an export.
"""

from __future__ import annotations

from pathlib import Path

from .registry import ALL_MESSAGES

NODES = {"dash": "PI_DASH", "controlbox": "PICO_BOX", "shinegle": "SHINEGLE", "sim": "BENCH"}


def render() -> str:
    lines = ['VERSION "teryx"', "", "NS_ :", "", "BS_:", "", "BU_: " + " ".join(NODES.values()), ""]
    comments, values = [], []
    for m in ALL_MESSAGES:
        lines.append(f"BO_ {m.can_id} {m.name}: {m.dlc} {NODES[m.sender]}")
        for s in m.signals:
            sign = "-" if s.signed else "+"
            lo = s.raw_min * s.scale + s.offset
            hi = s.raw_max * s.scale + s.offset
            lines.append(f' SG_ {s.name} : {s.start}|{s.length}@1{sign} ({s.scale:g},{s.offset:g}) '
                         f'[{lo:g}|{hi:g}] "{s.unit}" Vector__XXX')
            if s.comment:
                comments.append(f'CM_ SG_ {m.can_id} {s.name} "{s.comment}";')
            if s.choices:
                vals = " ".join(f'{k} "{v}"' for k, v in s.choices.items())
                values.append(f"VAL_ {m.can_id} {s.name} {vals} ;")
        if m.comment or m.placeholder:
            text = ("PLACEHOLDER layout. " if m.placeholder else "") + m.comment
            comments.append(f'CM_ BO_ {m.can_id} "{text.strip()}";')
        lines.append("")
    return "\n".join(lines + comments + [""] + values) + "\n"


def write_dbc(out: str | Path = "docs/teryx.dbc") -> Path:
    path = Path(out)
    path.write_text(render(), encoding="utf-8")
    return path
