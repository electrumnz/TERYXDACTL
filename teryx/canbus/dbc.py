"""Read and write .dbc files (the CAN database format SavvyCAN, cantools, Kvaser
and most CAN tools understand).

``render`` exports our Python message definitions (``docs/teryx.dbc``).
``parse`` / ``load`` read a .dbc back into ``Message`` objects. That is how the
Shinegle layout gets into Teryx OS: the decoding tools write a .dbc, and
``teryx/canbus/shinegle.py`` loads it.

Only the parts of the format we need are supported: standard and extended ids,
little and big-endian signals, scale/offset, units, value tables (VAL_),
comments (CM_) and the GenMsgCycleTime attribute. Multiplexed signals are
refused with a clear error rather than decoded wrongly.
"""

from __future__ import annotations

import re
from pathlib import Path

from .codec import Message, Signal

NODES = {"dash": "PI_DASH", "controlbox": "PICO_BOX", "shinegle": "SHINEGLE", "sim": "BENCH"}
_SENDERS = {v: k for k, v in NODES.items()}
PLACEHOLDER_TAG = "PLACEHOLDER layout."
EXTENDED_FLAG = 0x80000000


def _num(x: float) -> str:
    return f"{x:.10g}"


def _text(t: str) -> str:
    return t.replace('"', "'")


def render(messages=None, header_comment: str = "") -> str:
    """Write ``messages`` (default: every message Teryx OS knows) as DBC text."""
    if messages is None:
        from .registry import ALL_MESSAGES
        messages = ALL_MESSAGES
    lines = ['VERSION "teryx"', "", "NS_ :", "", "BS_:", "", "BU_: " + " ".join(NODES.values()), ""]
    comments, values, attrs = [], [], []
    if header_comment:
        comments.append(f'CM_ "{_text(header_comment)}";')
    for m in messages:
        dbc_id = m.can_id | (EXTENDED_FLAG if m.extended else 0)
        lines.append(f"BO_ {dbc_id} {m.name}: {m.dlc} {NODES.get(m.sender, 'Vector__XXX')}")
        for s in m.signals:
            sign = "-" if s.signed else "+"
            order = 0 if s.big_endian else 1
            lo = s.raw_min * s.scale + s.offset
            hi = s.raw_max * s.scale + s.offset
            lo, hi = min(lo, hi), max(lo, hi)
            lines.append(f' SG_ {s.name} : {s.start}|{s.length}@{order}{sign} ({_num(s.scale)},{_num(s.offset)}) '
                         f'[{lo:g}|{hi:g}] "{s.unit}" Vector__XXX')
            if s.comment:
                comments.append(f'CM_ SG_ {dbc_id} {s.name} "{_text(s.comment)}";')
            if s.choices:
                vals = " ".join(f'{k} "{v}"' for k, v in s.choices.items())
                values.append(f"VAL_ {dbc_id} {s.name} {vals} ;")
        if m.comment or m.placeholder:
            text = (PLACEHOLDER_TAG + " " if m.placeholder else "") + m.comment
            comments.append(f'CM_ BO_ {dbc_id} "{_text(text.strip())}";')
        if m.period_ms:
            attrs.append(f'BA_ "GenMsgCycleTime" BO_ {dbc_id} {m.period_ms};')
        lines.append("")
    defs = ['BA_DEF_ BO_ "GenMsgCycleTime" INT 0 65535;', 'BA_DEF_DEF_ "GenMsgCycleTime" 0;']
    return "\n".join(lines + comments + [""] + defs + attrs + [""] + values) + "\n"


def write_dbc(out: str | Path = "docs/teryx.dbc") -> Path:
    path = Path(out)
    path.write_text(render(), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- reading

class DbcError(ValueError):
    pass


_BO = re.compile(r"^BO_\s+(\d+)\s+(\w+)\s*:\s*(\d+)\s+(\w+)", re.MULTILINE)
_SG = re.compile(
    r"^\s+SG_\s+(\w+)\s*(\w*)\s*:\s*(\d+)\|(\d+)@([01])([+-])\s*"
    r"\(\s*([-+.\deE]+)\s*,\s*([-+.\deE]+)\s*\)\s*\[\s*([-+.\deE]+)\s*\|\s*([-+.\deE]+)\s*\]\s*"
    r'"([^"]*)"')
_CM_BO = re.compile(r'CM_\s+BO_\s+(\d+)\s+"([^"]*)"\s*;', re.DOTALL)
_CM_SG = re.compile(r'CM_\s+SG_\s+(\d+)\s+(\w+)\s+"([^"]*)"\s*;', re.DOTALL)
_CM_ALL = re.compile(r'CM_\s+"([^"]*)"\s*;', re.DOTALL)
_VAL = re.compile(r"VAL_\s+(\d+)\s+(\w+)\s+((?:-?\d+\s+\"[^\"]*\"\s*)*);", re.DOTALL)
_VAL_ITEM = re.compile(r'(-?\d+)\s+"([^"]*)"')
_CYCLE = re.compile(r'BA_\s+"GenMsgCycleTime"\s+BO_\s+(\d+)\s+(\d+)\s*;')


def parse(text: str, default_sender: str = "shinegle") -> tuple[list[Message], str]:
    """DBC text -> (messages, the file's general comment)."""
    msg_comments = {int(i): c for i, c in _CM_BO.findall(text)}
    sig_comments = {(int(i), n): c for i, n, c in _CM_SG.findall(text)}
    choices = {(int(i), n): {int(k): v for k, v in _VAL_ITEM.findall(body)}
               for i, n, body in _VAL.findall(text)}
    cycles = {int(i): int(p) for i, p in _CYCLE.findall(text)}
    general = "\n".join(_CM_ALL.findall(text))

    blocks = list(_BO.finditer(text))
    messages = []
    for n, bo in enumerate(blocks):
        dbc_id, name, dlc, tx = int(bo.group(1)), bo.group(2), int(bo.group(3)), bo.group(4)
        end = blocks[n + 1].start() if n + 1 < len(blocks) else len(text)
        body = text[bo.end():end]
        signals = []
        for line in body.splitlines():
            if not line.strip().startswith("SG_"):
                if line.strip() and not line.startswith((" ", "\t")):
                    break   # end of this message's block
                continue
            sg = _SG.match(line)
            if not sg:
                raise DbcError(f"can't read signal line in {name}: {line.strip()}")
            sname, mux = sg.group(1), sg.group(2)
            if mux:
                raise DbcError(f"{name}.{sname}: multiplexed signals aren't supported yet")
            comment = sig_comments.get((dbc_id, sname), "")
            signals.append(Signal(
                sname, int(sg.group(3)), int(sg.group(4)),
                scale=float(sg.group(7)), offset=float(sg.group(8)),
                signed=sg.group(6) == "-", unit=sg.group(11),
                choices=choices.get((dbc_id, sname)) or None,
                comment=comment, big_endian=sg.group(5) == "0"))
        comment = msg_comments.get(dbc_id, "")
        placeholder = comment.startswith(PLACEHOLDER_TAG)
        if placeholder:
            comment = comment[len(PLACEHOLDER_TAG):].strip()
        try:
            messages.append(Message(
                name, dbc_id & 0x1FFFFFFF, _SENDERS.get(tx, default_sender), cycles.get(dbc_id, 0),
                signals=tuple(signals), dlc=dlc, extended=bool(dbc_id & EXTENDED_FLAG),
                comment=comment, placeholder=placeholder))
        except ValueError as e:
            raise DbcError(str(e)) from None
    return messages, general


def load(path: str | Path, default_sender: str = "shinegle") -> tuple[list[Message], str]:
    return parse(Path(path).read_text(encoding="utf-8", errors="replace"), default_sender)
