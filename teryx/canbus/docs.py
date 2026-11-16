"""Generate docs/CAN_PROTOCOL.md from the message definitions, so the doc never drifts."""

from __future__ import annotations

from pathlib import Path

from . import messages as M
from . import shinegle as SG
from .codec import Message


def _bits(s) -> str:
    if s.start % 8 == 0 and s.length % 8 == 0:
        b0, n = s.start // 8, s.length // 8
        return f"byte {b0}" if n == 1 else f"bytes {b0}-{b0 + n - 1}"
    return f"byte {s.start // 8} bit {s.start % 8}" + (f" (+{s.length} bits)" if s.length > 1 else "")


def _type(s) -> str:
    t = ("i" if s.signed else "u") + str(s.length)
    if s.scale != 1:
        t += f" x{s.scale:g}"
    if s.offset:
        t += f" {s.offset:+g}"
    return t


def _table(m: Message) -> str:
    rate = f"every {m.period_ms} ms" if m.period_ms else "on change"
    out = [f"### 0x{m.can_id:03X} {m.name}", "",
           f"From **{m.sender}**, {rate}." + (" **PLACEHOLDER.**" if m.placeholder else "")]
    if m.comment:
        out += ["", m.comment]
    out += ["", "| Signal | Where | Type | Unit | Notes |", "|---|---|---|---|---|"]
    for s in m.signals:
        notes = s.comment
        if s.choices:
            notes = (notes + " " if notes else "") + ", ".join(f"{k}={v}" for k, v in s.choices.items())
        out.append(f"| `{s.name}` | {_bits(s)} | {_type(s)} | {s.unit} | {notes} |")
    return "\n".join(out) + "\n"


def _enum(title: str, table: dict, prefix="bit") -> str:
    rows = "\n".join(f"| {k} | `{v}` |" for k, v in table.items())
    return f"**{title}**\n\n| {prefix} | name |\n|---|---|\n{rows}\n"


def render() -> str:
    parts = [
        "# Teryx CAN protocol",
        "",
        "Generated from `teryx/canbus/` by `python -m teryx canmap`. Don't edit by hand.",
        "",
        "All values little-endian. Physical value = raw x scale + offset. Standard 11-bit ids.",
        "Bit rate: match the Shinegle (likely 250 kbit/s, TBC).",
        "",
        "## Pi 5 dash -> Pico 2 control box", "",
    ]
    parts += [_table(m) for m in M.TERYX_MESSAGES if m.sender == "dash"]
    parts += ["## Pico 2 control box -> Pi 5 dash", ""]
    parts += [_table(m) for m in M.TERYX_MESSAGES if m.sender == "controlbox"]
    parts += ["## Bench only", ""]
    parts += [_table(m) for m in M.TERYX_MESSAGES if m.sender == "sim"]
    parts += [_enum("Bench fault inject bits (0x7E0 byte 2)", M.BENCH_FAULTS)]
    parts += ["## Lookup tables", ""]
    parts += [_enum("Fault bits (0x710 bytes 1-2)", M.FAULT_BITS),
              _enum("Input bits (0x710 byte 3, MCP23017 B0-B7)", M.INPUT_BITS),
              _enum("Relay bits (0x711 byte 0, relay 1 = bit 0)", M.RELAY_BITS),
              _enum("Reject reasons (0x710 byte 5 low nibble)", M.REJECT_REASON, "value")]
    rows = "\n".join(f"| {k} (0x{k:02X}) | `{n}` | {u} | {d} | {lo}-{hi} |"
                     for k, (n, u, d, lo, hi) in M.SETTINGS.items())
    parts += ["**Settings keys (0x704 / 0x714)**", "",
              "| key | name | unit | default | range |", "|---|---|---|---|---|", rows,
              f"| {M.SETTING_SAVE} (0xF0) | save to flash | | | |",
              f"| {M.SETTING_RESET} (0xF1) | reset to defaults | | | |", ""]
    parts += ["## Shinegle SG1202 (PLACEHOLDER)", "",
              "Made-up layout so we can build now. Replace in `teryx/canbus/shinegle.py` "
              "once the real bus has been recorded.", ""]
    parts += [_table(m) for m in SG.SHINEGLE_MESSAGES]
    parts += [_enum("Shinegle fault bits (placeholder)", SG.FAULT_BITS)]
    return "\n".join(parts)


def write_protocol_doc(out: str | Path = "docs/CAN_PROTOCOL.md") -> Path:
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(), encoding="utf-8")
    return path
