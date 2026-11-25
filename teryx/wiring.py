"""Whole-vehicle wiring: checks config/wiring.yaml and draws docs/wiring/ from it.

    python -m teryx wiring           check, then write docs/wiring/
    python -m teryx wiring --check   only check (exit 1 on problems)

What gets written (never edit these by hand, edit the YAML):

    docs/wiring/schematic.json     the whole-vehicle drawing model (teryx/wiring_sld.py), which
                                   docs/wiring/index.html lays out and draws on one big grid
                                   (also on GitHub Pages at /wiring/)
    docs/wiring/README.md          wire and fuse schedule, devices, things to check

Our own code, MIT like the rest of the repo, no extra packages beyond PyYAML.
(WireViz was looked at: it's GPL-3.0 and needs Graphviz, so we don't copy or
depend on it.)
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "config" / "wiring.yaml"
IO_MAP = ROOT / "config" / "io-map.yaml"
OUT_DIR = ROOT / "docs" / "wiring"

STATUSES = ["placeholder", "tbc", "planned", "confirmed", "from_manual", "measured"]
STATUS_RANK = {"placeholder": 0, "tbc": 1, "planned": 2, "confirmed": 3, "from_manual": 3, "measured": 4}
# colour, dash pattern, words for the legend
STATUS_STYLE = {
    "measured":    ("#1a7f37", "",     "Measured on the Teryx"),
    "from_manual": ("#0969da", "",     "From a maker's manual"),
    "confirmed":   ("#0969da", "",     "Confirmed by Sam / part owned"),
    "planned":     ("#424a53", "",     "Our design, not built yet"),
    "tbc":         ("#bf8700", "7 4",  "TBC: needs checking"),
    "placeholder": ("#8250df", "2 4",  "Placeholder / later"),
}
AUTO_MULTI = {"gnd", "hvneg", "can"}
NEVER_MIX = {"hv", "hvneg", "motor"}


# ----------------------------------------------------------------- loading
POWER_IN_PINS = {"VCC", "VDD", "VIN", "VSYS", "JDVCC", "V12", "V5", "B+", "DC_IN", "IN"}


def load(path: Path = SOURCE) -> dict:
    import yaml
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    for dev_id, dev in d["devices"].items():
        pins = {}
        for name, p in (dev.get("pins") or {}).items():
            p = {"v": p} if isinstance(p, str) else dict(p)
            p.setdefault("multi", p["v"] in AUTO_MULTI)
            pins[str(name)] = p
        dev["pins"] = pins
        dev.setdefault("optional", False)
    for w in d["wires"]:
        a, b = (_split(w["from"]), _split(w["to"]))
        w["_a"], w["_b"] = a, b
        if "status" not in w:
            sa = d["devices"].get(a[0], {}).get("status", "tbc")
            sb = d["devices"].get(b[0], {}).get("status", "tbc")
            w["status"] = min((sa, sb), key=lambda s: STATUS_RANK.get(s, 0))
        w.setdefault("optional", False)
    return d


def _split(end: str) -> tuple[str, str]:
    dev, _, pin = str(end).partition(".")
    return dev, pin


def fuse_for(d: dict, w: dict):
    """The fuse protecting a wire: its own `fuse`, else the fuse on its `from` pin."""
    if w.get("fuse") is not None:
        return w["fuse"]
    dev = d["devices"].get(w["_a"][0])
    if dev:
        return dev["pins"].get(w["_a"][1], {}).get("fuse_a")
    return None


# ----------------------------------------------------------------- checks
def check(d: dict | None = None) -> list[str]:
    """Every problem found, as plain sentences. Empty list = all good."""
    d = d or load()
    devs = d["devices"]
    sheets = d["sheets"]
    table = {float(k): float(v) for k, v in d["wire_table_mm2_to_max_fuse_a"].items()}
    errs: list[str] = []

    for dev_id, dev in devs.items():
        if dev.get("status") not in STATUS_RANK:
            errs.append(f"{dev_id}: status {dev.get('status')!r} isn't one of {STATUSES}")
        if dev.get("status") == "tbc" and not dev.get("check") and not dev.get("note"):
            errs.append(f"{dev_id}: TBC devices need a `check` or `note` saying what to find out")

    seen_ids: set[str] = set()
    uses: dict[tuple[str, str], list[str]] = defaultdict(list)
    for w in d["wires"]:
        wid = w.get("id", "?")
        if wid in seen_ids:
            errs.append(f"{wid}: wire id used twice")
        seen_ids.add(wid)
        if w.get("sys") not in sheets:
            errs.append(f"{wid}: sheet {w.get('sys')!r} isn't in `sheets`")
        if w["status"] not in STATUS_RANK:
            errs.append(f"{wid}: status {w['status']!r} isn't one of {STATUSES}")
        pins = []
        for dev_id, pin in (w["_a"], w["_b"]):
            if dev_id not in devs:
                errs.append(f"{wid}: no device {dev_id}")
                continue
            if pin not in devs[dev_id]["pins"]:
                errs.append(f"{wid}: {dev_id} has no pin {pin!r}")
                continue
            uses[(dev_id, pin)].append(wid)
            pins.append(devs[dev_id]["pins"][pin])
        if len(pins) != 2:
            continue
        va, vb = pins[0]["v"], pins[1]["v"]
        if va != vb:
            if {va, vb} & NEVER_MIX:
                errs.append(f"{wid}: joins {va} to {vb}. The traction side never meets anything else on a wire")
            elif {va, vb} == {"gnd", "hvneg"}:
                errs.append(f"{wid}: joins chassis ground to the pack negative")
            elif not w.get("via"):
                errs.append(f"{wid}: joins {va} ({w['from']}) to {vb} ({w['to']}) with nothing in between. "
                            f"Add `via:` (opto, divider, diode, dongle) or fix the pins")

        # fuse and wire size
        from_pin = pins[0]
        fuse = fuse_for(d, w)
        mm2 = w.get("mm2")
        if from_pin.get("supply") and w["status"] != "tbc":
            if fuse is None:
                errs.append(f"{wid}: leaves a supply ({w['from']}) with no fuse")
            if mm2 is None:
                errs.append(f"{wid}: leaves a supply ({w['from']}) with no wire size")
        if fuse is not None and mm2 is not None and w.get("rating_from") != "maker":
            mm2f = float(mm2)
            if mm2f not in table:
                errs.append(f"{wid}: {mm2} mm² isn't in the wire table")
            elif float(fuse) > table[mm2f]:
                need = min((k for k, v in table.items() if v >= float(fuse)), default=None)
                errs.append(f"{wid}: {mm2} mm² is only good for a {table[mm2f]:g} A fuse, "
                            f"but it's on {fuse} A. Use {need:g} mm² or a smaller fuse"
                            if need else f"{wid}: {fuse} A is past the wire table, size it from the maker")

    for (dev_id, pin), wids in uses.items():
        if len(wids) > 1 and not devs[dev_id]["pins"][pin]["multi"]:
            errs.append(f"{dev_id}.{pin} has {len(wids)} wires ({', '.join(wids)}). "
                        f"Mark the pin `multi: true` if that's meant")

    # Every board's power input has to be wired, or it won't run (BTS7960 4-9 VCC was missed once)
    for dev_id, dev in devs.items():
        for pin in dev["pins"]:
            if pin in POWER_IN_PINS and (dev_id, pin) not in uses:
                errs.append(f"{dev_id}.{pin}: power input with no wire, so the board won't run")

    # CAN: exactly two terminators per bus
    buses: dict[str, set[str]] = defaultdict(set)
    for w in d["wires"]:
        if w.get("bus"):
            buses[w["bus"]] |= {w["_a"][0], w["_b"][0]}
    for bus, members in buses.items():
        ends = sorted(m for m in members if any(p.get("term") for p in devs[m]["pins"].values()))
        if len(ends) != 2:
            errs.append(f"CAN bus {bus!r}: needs a 120 ohm terminator at exactly two ends, has {ends or 'none'}")

    # AI HAT+ 2 standing rule: the PCIe port and the HAT header stay for it
    if "AIHAT" not in devs:
        errs.append("AIHAT is missing. Every design keeps room for the AI HAT+ 2")
    for w in d["wires"]:
        for end, other in ((w["_a"], w["_b"]), (w["_b"], w["_a"])):
            if end == ("PI5", "PCIE") and other[0] != "AIHAT":
                errs.append(f"{w['id']}: the Pi's PCIe port is kept for the AI HAT+ 2, not {other[0]}")
            if end == ("PI5", "HAT_HDR") and other[0] != "AIHAT":
                errs.append(f"{w['id']}: the Pi's 40-pin header is kept for the AI HAT+ 2 stacking header")

    errs += check_io_map(d)
    return errs


def check_io_map(d: dict, io_map: Path = IO_MAP) -> list[str]:
    """The Pico wiring has to agree with config/io-map.yaml (which the firmware uses)."""
    import yaml
    io = yaml.safe_load(io_map.read_text(encoding="utf-8"))
    links = {(w["from"], w["to"]) for w in d["wires"]} | {(w["to"], w["from"]) for w in d["wires"]}
    ends = {w["from"] for w in d["wires"]} | {w["to"] for w in d["wires"]}
    errs = []

    def need(a, b, what):
        if (a, b) not in links:
            errs.append(f"io-map says {what}: no wire {a} <-> {b}")

    for oid, o in io["outputs"].items():
        if o["driver"] == "mosfet":
            ch = int(o["pin"][2:]) - 15          # GP16 -> IN1
            need(f"PICO.{o['pin']}", f"MOSFET.IN{ch}", oid)
        elif o["driver"] == "relay":
            need(f"MCP1.{o['expander_pin']}", f"RELAYS.IN{o['relay']}", oid)
        elif o["driver"] == "pca9685":
            for target in o["to"]:
                need(f"PCA.PWM{o['channel']}", target, oid)
        elif o["driver"] == "bts7960":
            for k, pin in o["pins"].items():
                need(f"PICO.{pin}", f"BTS{o['unit']}.{k.upper()}", oid)
    for iid, i in io["inputs"]["digital"].items():
        pin = i["expander_pin"]
        ch = i.get("opto", int(pin[1:]) + 1)
        mcp = f"MCP{i.get('expander', 1)}"
        if pin in ("A7", "B7"):
            errs.append(f"io-map: {iid} is on {mcp} {pin}, which is output only on newer MCP23017 chips")
        need(f"OPTO.OUT{ch}", f"{mcp}.{pin}", iid)
    adc = {"ads1115": "ADS1", "ads1115_2": "ADS2"}
    for aid, a in io["inputs"]["analogue"].items():
        target = f"PICO.{a['pin']}" if a["adc"] == "pico" else f"{adc[a['adc']]}.A{a['channel']}"
        if target not in ends:
            errs.append(f"io-map says {aid} is on {target}, but no wire goes there")
    return errs


# ----------------------------------------------------------------- tables
def _md(s) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def checklist(d: dict) -> list[str]:
    items = []
    for dev_id, dev in d["devices"].items():
        if dev.get("check"):
            items.append(f"**{dev['name']}** ({dev_id}): {dev['check']}")
    return items


def render_readme(d: dict) -> str:
    devs = d["devices"]
    counts = defaultdict(int)
    for w in d["wires"]:
        counts[w["status"]] += 1
    out = [
        "# Teryx wiring (made from `config/wiring.yaml`)",
        "",
        "Don't edit this file or schematic.json here. Edit [`config/wiring.yaml`](../../config/wiring.yaml), then run",
        "`python -m teryx wiring`. A test fails if they get out of step, and it also checks the wiring",
        "itself: every fused feed has a fuse, wires are thick enough for their fuse, no 12 V or 72 V",
        "wire lands on a 3.3 V pin, each CAN bus has exactly two 120 ohm ends, the Pico pins match",
        "`config/io-map.yaml`, and the Pi's PCIe port and header stay free for the AI HAT+ 2.",
        "",
        "Why things are wired this way (power hold, diodes, CAN rules): [`docs/wiring.md`](../wiring.md).",
        "The drawing: one big schematic of the whole Teryx on a pan and zoom grid, online at",
        "<https://electrumnz.github.io/TERYXDACTL/wiring/> (or open [`index.html`](index.html) through any",
        "web server). It's laid out from [`schematic.json`](schematic.json) by [`sld.js`](sld.js) with ELK",
        "(elkjs, EPL-2.0, unchanged copy in [`vendor/`](vendor/)). The simulator page links to it and lights",
        "up the live wires.",
        "",
        f"**{len(devs)} devices, {len(d['wires'])} wires.** By status: "
        + ", ".join(f"{counts[s]} {s}" for s in reversed(STATUSES) if counts[s]) + ".",
        "Nothing has been checked on the real Teryx yet.",
        "",
        "Wire sizes follow the conservative table in the YAML (from",
        "[speedingparts.eu](https://info.speedingparts.eu/what-cable-size-should-you-use-in-a-12v-automotive-system),",
        "runs up to about 5 m). Go one size up for bundled or hot runs.",
        "",
        "## Systems on the drawing",
        "",
    ]
    from . import wiring_sld
    for sec in wiring_sld.build(d)["sections"]:
        out.append(f"{sec['no']}. {sec['title']} ({len(sec['wires'])} wires)")
    out.append("")

    out += ["## Things to check or photograph on the Teryx", ""]
    out += [f"- [ ] {c}" for c in checklist(d)]
    tbc_wires = [w for w in d["wires"] if w["status"] == "tbc" and w.get("note")]
    if tbc_wires:
        out += ["", "Wires marked TBC, with what's unknown:", ""]
        out += [f"- {w['id']} {w['from']} to {w['to']}: {w['note']}" for w in tbc_wires]

    out += ["", "## Fuse block", "", "| Slot | Fuse | Feeds | Wires |", "|---|---|---|---|"]
    fb = devs.get("FB", {}).get("pins", {})
    for pin, p in fb.items():
        if "fuse_a" in p:
            wids = [w["id"] for w in d["wires"] if w["from"] == f"FB.{pin}"]
            out.append(f"| {pin} | {p['fuse_a']:g} A | {_md(p.get('desc', ''))} | {', '.join(wids)} |")
    out += ["", "Fuses not in the block (inline, at the battery or on a board):", "",
            "| Wire | Fuse | From | To |", "|---|---|---|---|"]
    for w in d["wires"]:
        if w.get("fuse") is not None and not w["from"].startswith("FB."):
            out.append(f"| {w['id']} | {w['fuse']:g} A | {w['from']} | {w['to']} |")

    out += ["", "## Wire schedule", ""]
    for key, sh in d["sheets"].items():
        ws = [w for w in d["wires"] if w["sys"] == key]
        out += [f"### {sh['title']}", "", "| Wire | From | To | Size | Fuse | Via | Status | Note |",
                "|---|---|---|---|---|---|---|---|"]
        for w in ws:
            f = fuse_for(d, w)
            out.append("| " + " | ".join([
                w["id"], _md(w["from"]), _md(w["to"]),
                f"{w['mm2']:g} mm²" if w.get("mm2") is not None else "",
                f"{f:g} A" if f is not None else "",
                _md(w.get("via", "")),
                w["status"] + (" (optional)" if w.get("optional") else ""),
                _md(w.get("note", "")),
            ]) + " |")
        out.append("")

    out += ["## Devices", "", "| ID | Device | Where | Status | Notes |", "|---|---|---|---|---|"]
    for dev_id, dev in devs.items():
        note = dev.get("note", "")
        if dev.get("doc"):
            note = (note + f" See [`{dev['doc']}`](../../{dev['doc']}).").strip()
        out.append(f"| {dev_id} | {_md(dev['name'])} | {dev.get('zone', '')} | {dev['status']}"
                   f"{' (optional)' if dev.get('optional') else ''} | {_md(note)} |")
    return "\n".join(out) + "\n"


# ----------------------------------------------------------------- output
def outputs(d: dict | None = None) -> dict[Path, str]:
    d = d or load()
    from . import wiring_sld
    import copy
    return {
        OUT_DIR / "README.md": render_readme(copy.deepcopy(d)),
        OUT_DIR / "schematic.json": wiring_sld.render(copy.deepcopy(d)),
    }


def write() -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = outputs()
    for path, text in files.items():
        path.write_text(text, encoding="utf-8", newline="\n")
    keep = set(files)
    for old in OUT_DIR.glob("sheet-*.svg"):
        if old not in keep:
            old.unlink()
    return sorted(files)


def main(check_only: bool = False) -> int:
    problems = check()
    for p in problems:
        print("problem:", p)
    if problems:
        print(f"{len(problems)} problem(s) in config/wiring.yaml")
        return 1
    print("config/wiring.yaml: all checks pass")
    if not check_only:
        for p in write():
            print("wrote", p.relative_to(ROOT))
    return 0
