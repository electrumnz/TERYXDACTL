"""Whole-vehicle wiring: checks config/wiring.yaml and draws docs/wiring/ from it.

    python -m teryx wiring           check, then write docs/wiring/
    python -m teryx wiring --check   only check (exit 1 on problems)

What gets written (never edit these by hand, edit the YAML):

    docs/wiring/sheet-<name>.svg   one single line diagram per system
    docs/wiring/README.md          wire and fuse schedule, devices, things to check
    docs/wiring/index.html         one page viewer with search (also on GitHub Pages at /wiring/)

Our own code, MIT like the rest of the repo, no extra packages beyond PyYAML.
(WireViz was looked at: it's GPL-3.0 and needs Graphviz, so we don't copy or
depend on it.)
"""

from __future__ import annotations

import json
from collections import defaultdict
from html import escape
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
ZONE_FILL = {
    "hv": "#fff1f0", "engine_bay": "#fff8e6", "cab": "#f0f6ff", "dash": "#eef9f1",
    "control_box": "#f6f1ff", "front": "#f4f4f4", "rear": "#f4f4f4", "trailer": "#f4f4f4",
}


# ----------------------------------------------------------------- loading
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
        elif o["driver"] == "bts7960":
            for k, pin in o["pins"].items():
                need(f"PICO.{pin}", f"BTS{o['unit']}.{k.upper()}", oid)
    for iid, i in io["inputs"]["digital"].items():
        pin = i["expander_pin"]
        ch = int(pin[1:]) + 1
        need(f"OPTO.OUT{ch}", f"MCP1.{pin}", iid)
    adc = {"ads1115": "ADS1", "ads1115_2": "ADS2"}
    for aid, a in io["inputs"]["analogue"].items():
        target = f"PICO.{a['pin']}" if a["adc"] == "pico" else f"{adc[a['adc']]}.A{a['channel']}"
        if target not in ends:
            errs.append(f"io-map says {aid} is on {target}, but no wire goes there")
    return errs


# ----------------------------------------------------------------- drawing
BOX_W = 270
COL_GAP = 170
ROW = 20


def _t(x, y, s, size=12, anchor="start", weight="normal", fill="#1f2328", extra=""):
    return (f'<text x="{x:.0f}" y="{y:.0f}" font-size="{size}" text-anchor="{anchor}" '
            f'font-weight="{weight}" fill="{fill}"{extra}>{escape(str(s))}</text>')


def _wrap(s: str, n: int) -> list[str]:
    words, lines, cur = s.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > n:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + ([cur] if cur else [])


def wire_label(d: dict, w: dict) -> str:
    bits = [w["id"]]
    if w.get("mm2") is not None:
        bits.append(f"{w['mm2']:g} mm²")
    f = fuse_for(d, w)
    if f is not None and w.get("fuse") is not None:
        bits.append(f"{f:g} A")
    if w.get("via"):
        bits.append(f"via {w['via']}")
    return "  ".join(bits)


POWER_PINS = {"VCC", "VDD", "GND", "3V3", "JDVCC", "VSYS", "5V", "P1_3V3", "V5", "V12", "COM12"}


def _is_power_pin(pin: str) -> bool:
    return pin in POWER_PINS


def _layout(d: dict, sheet: str):
    wires = [w for w in d["wires"] if w["sys"] == sheet]
    root = d["sheets"][sheet]["root"]
    adj: dict[str, list[str]] = defaultdict(list)
    order: list[str] = []
    for w in wires:
        a, b = w["_a"][0], w["_b"][0]
        adj[a].append(b)
        adj[b].append(a)
        for x in (a, b):
            if x not in order:
                order.append(x)
    # Columns: distance from the sheet's root. Power and ground pins (VCC, GND...)
    # are left out at first, so a board sits next to what drives it, not next
    # to whatever powers it.
    sig: dict[str, list[str]] = defaultdict(list)
    for w in wires:
        if not (_is_power_pin(w["_a"][1]) or _is_power_pin(w["_b"][1])):
            sig[w["_a"][0]].append(w["_b"][0])
            sig[w["_b"][0]].append(w["_a"][0])
    col: dict[str, int] = {}

    def bfs(graph, start):
        queue = [start]
        while queue:
            n = queue.pop(0)
            for m in graph[n]:
                if m not in col:
                    col[m] = col[n] + 1
                    queue.append(m)

    starts = ([root] if root in adj else []) + order
    for s in starts:                      # signal wires first
        if s not in col and (s == root or sig[s]):
            col[s] = 0
            bfs(sig, s)
    changed = True
    while changed:                        # then hang power-only devices off their neighbours
        changed = False
        for s in sorted(col, key=col.get):
            before = len(col)
            bfs(adj, s)
            changed |= len(col) != before
        for s in order:
            if s not in col:
                col[s] = 0
                changed = True
                break
    # pins used on this sheet, in the device's own pin order
    used: dict[str, list[str]] = defaultdict(list)
    for w in wires:
        for dev, pin in (w["_a"], w["_b"]):
            if pin not in used[dev]:
                used[dev].append(pin)
    for dev in used:
        names = list(d["devices"][dev]["pins"])
        used[dev].sort(key=names.index)
    return wires, col, used, order


def render_sheet(d: dict, sheet: str) -> str:
    wires, col, used, order = _layout(d, sheet)
    devs = d["devices"]
    ncols = max(col.values(), default=0) + 1
    top = 150
    W = 40 + ncols * (BOX_W + COL_GAP) - COL_GAP + 40
    W = max(W, 1100) + 90   # room for loops on the right

    # place boxes
    pos: dict[str, tuple[float, float, float]] = {}
    col_y = defaultdict(lambda: top)
    title_lines: dict[str, list[str]] = {}
    pin_at: dict[tuple[str, str], float] = {}

    def place(dev):
        info = devs[dev]
        lines = _wrap(info["name"], 34)
        title_lines[dev] = lines
        h = 26 + 15 * len(lines) + ROW * len(used[dev]) + 8
        x = 40 + col[dev] * (BOX_W + COL_GAP)
        y = col_y[col[dev]]
        pos[dev] = (x, y, h)
        for i, pin in enumerate(used[dev]):
            pin_at[(dev, pin)] = y + 26 + 15 * len(lines) + i * ROW
        col_y[col[dev]] = y + h + 22

    for c in range(ncols):
        members = [x for x in order if col.get(x) == c]

        def weight(dev):
            ys = []
            for w in wires:
                for me, other in ((w["_a"], w["_b"]), (w["_b"], w["_a"])):
                    if me[0] == dev and other in pin_at and not _is_power_pin(other[1]):
                        ys.append(pin_at[other])
            return (sum(ys) / len(ys)) if ys else 1e9 + order.index(dev)
        for dev in sorted(members, key=weight):
            place(dev)
    H = max(col_y.values(), default=top) + 40

    def pin_xy(dev, pin, other):
        x, y, _ = pos[dev]
        i = used[dev].index(pin)
        py = y + 26 + 15 * len(title_lines[dev]) + i * ROW + 6
        right = col[other] >= col[dev]
        return (x + BOX_W if right else x), py, right

    boxes, paths, labels = [], [], []
    for dev, (x, y, h) in pos.items():
        info = devs[dev]
        st = info["status"]
        colour, dash, _ = STATUS_STYLE.get(st, STATUS_STYLE["tbc"])
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        fill = ZONE_FILL.get(info.get("zone"), "#f6f8fa")
        boxes.append(f'<g data-device="{escape(dev)}" data-status="{st}">'
                     f'<title>{escape(dev + ": " + info["name"] + (" - " + info["note"] if info.get("note") else ""))}</title>'
                     f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{h}" rx="6" fill="{fill}" '
                     f'stroke="{colour}" stroke-width="1.5"{dash_attr}/>')
        for i, line in enumerate(title_lines[dev]):
            boxes.append(_t(x + 10, y + 18 + 15 * i, line, 13, weight="bold"))
        sub = f"{dev} · {st}" + (" · optional" if info.get("optional") else "")
        boxes.append(_t(x + 10, y + 18 + 15 * len(title_lines[dev]), sub, 10, fill=colour))
        for i, pin in enumerate(used[dev]):
            py = y + 26 + 15 * len(title_lines[dev]) + i * ROW + 6
            p = info["pins"][pin]
            text = pin + (f"  {p['desc']}" if p.get("desc") else "")
            if len(text) > 40:
                text = text[:39] + "…"
            boxes.append(f'<line x1="{x}" y1="{py}" x2="{x + BOX_W}" y2="{py}" stroke="#d0d7de" stroke-width="0.5"/>')
            boxes.append(_t(x + BOX_W / 2, py + 4, text, 11, "middle", fill="#424a53"))
        boxes.append("</g>")

    crowd: dict[tuple[str, str], int] = defaultdict(int)
    for w in wires:
        crowd[w["_a"]] += 1
        crowd[w["_b"]] += 1
    for w in wires:
        (da, pa), (db, pb) = w["_a"], w["_b"]
        x1, y1, r1 = pin_xy(da, pa, db)
        x2, y2, r2 = pin_xy(db, pb, da)
        colour, dash, _ = STATUS_STYLE.get(w["status"], STATUS_STYLE["tbc"])
        mm2 = float(w.get("mm2") or 0.5)
        width = 1.4 if mm2 < 1 else 2.2 if mm2 < 4 else 3.2 if mm2 < 16 else 4.5
        if devs[da]["pins"][pa]["v"] in NEVER_MIX:
            width = 4.5
        dx = max(60.0, abs(x2 - x1) / 2)
        c1 = x1 + (dx if r1 else -dx)
        c2 = x2 + (dx if r2 else -dx)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        opac = ' stroke-opacity="0.65"' if w.get("optional") else ""
        tip = f"{w['id']}: {w['from']} -> {w['to']}" + (f" - {w['note']}" if w.get("note") else "")
        paths.append(f'<g data-wire="{escape(w["id"])}" data-from="{escape(w["from"])}" '
                     f'data-to="{escape(w["to"])}" data-status="{w["status"]}"><title>{escape(tip)}</title>'
                     f'<path d="M{x1:.0f},{y1:.0f} C{c1:.0f},{y1:.0f} {c2:.0f},{y2:.0f} {x2:.0f},{y2:.0f}" '
                     f'fill="none" stroke="{colour}" stroke-width="{width}"{dash_attr}{opac}/></g>')
        # label next to the end whose pin has fewer wires, so labels don't pile up
        if crowd[(db, pb)] < crowd[(da, pa)]:
            lx, ly, rr = x2, y2, r2
        else:
            lx, ly, rr = x1, y1, r1
        anchor = "start" if rr else "end"
        lx = lx + (8 if rr else -8)
        labels.append(_t(lx, ly - 3, wire_label(d, w), 9.5, anchor, fill=colour,
                         extra=' stroke="#ffffff" stroke-width="3" paint-order="stroke"'))

    sh = d["sheets"][sheet]
    head = [_t(40, 40, sh["title"], 22, weight="bold"),
            _t(40, 62, f"Teryx OS wiring, sheet '{sheet}'. Made from config/wiring.yaml by "
               "`python -m teryx wiring`. Don't edit this file.", 12, fill="#57606a")]
    lx = 40
    for key in ("measured", "from_manual", "planned", "tbc", "placeholder"):
        colour, dash, words = STATUS_STYLE[key]
        if key == "from_manual":
            words = "Manual / confirmed"
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        head.append(f'<line x1="{lx}" y1="92" x2="{lx + 34}" y2="92" stroke="{colour}" stroke-width="2.5"{dash_attr}/>')
        head.append(_t(lx + 40, 96, words, 12))
        lx += 210
    head.append(_t(40, 120, "Labels: wire id, size, fuse (if the wire has its own), and anything in between. "
                   "Faded = optional. Hover for notes. Full table: docs/wiring/README.md", 11, fill="#57606a"))

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           f'font-family="Arial, Helvetica, sans-serif" data-sheet="{sheet}">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    out += head + paths + boxes + labels
    out.append("</svg>")
    return "\n".join(out) + "\n"


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
        "Don't edit this file or the SVGs here. Edit [`config/wiring.yaml`](../../config/wiring.yaml), then run",
        "`python -m teryx wiring`. A test fails if they get out of step, and it also checks the wiring",
        "itself: every fused feed has a fuse, wires are thick enough for their fuse, no 12 V or 72 V",
        "wire lands on a 3.3 V pin, each CAN bus has exactly two 120 ohm ends, the Pico pins match",
        "`config/io-map.yaml`, and the Pi's PCIe port and header stay free for the AI HAT+ 2.",
        "",
        "Why things are wired this way (power hold, diodes, CAN rules): [`docs/wiring.md`](../wiring.md).",
        "Viewer with search: [`index.html`](index.html), also online at",
        "<https://electrumnz.github.io/TERYXDACTL/wiring/>.",
        "",
        f"**{len(devs)} devices, {len(d['wires'])} wires.** By status: "
        + ", ".join(f"{counts[s]} {s}" for s in reversed(STATUSES) if counts[s]) + ".",
        "Nothing has been checked on the real Teryx yet.",
        "",
        "Wire sizes follow the conservative table in the YAML (from",
        "[speedingparts.eu](https://info.speedingparts.eu/what-cable-size-should-you-use-in-a-12v-automotive-system),",
        "runs up to about 5 m). Go one size up for bundled or hot runs.",
        "",
        "## Sheets",
        "",
    ]
    for key, sh in d["sheets"].items():
        out += [f"### {sh['title']}", "", f"![{key}](sheet-{key}.svg)", ""]

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


def render_index(d: dict, svgs: dict[str, str]) -> str:
    rows = []
    for w in d["wires"]:
        f = fuse_for(d, w)
        rows.append({"id": w["id"], "from": w["from"], "to": w["to"], "sheet": w["sys"],
                     "mm2": w.get("mm2"), "fuse": f, "via": w.get("via", ""),
                     "status": w["status"], "optional": w.get("optional", False), "note": w.get("note", "")})
    names = {k: v["name"] for k, v in d["devices"].items()}
    tabs = "".join(f'<button data-sheet="{k}">{escape(v["title"].split(":")[0])}</button>'
                   for k, v in d["sheets"].items())
    panes = "".join(f'<figure data-sheet="{k}" hidden>{svgs[k]}</figure>' for k in d["sheets"])
    checks = "".join(f"<li>{escape(c.replace('**', ''))}</li>" for c in checklist(d))
    data = json.dumps({"wires": rows, "names": names}, ensure_ascii=False, separators=(",", ":"))
    return f"""<!doctype html>
<html lang="en-NZ">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Teryx wiring</title>
<style>
:root {{ --bg:#f6f8fa; --card:#ffffff; --ink:#1f2328; --muted:#57606a; --line:#d0d7de; --accent:#0969da; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0d1117; --card:#161b22; --ink:#e6edf3; --muted:#8d96a0; --line:#30363d; --accent:#4493f8; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.45 system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }}
header, main {{ max-width:1400px; margin:0 auto; padding:16px; }}
h1 {{ margin:8px 0 4px; font-size:24px; }}
p {{ color:var(--muted); margin:4px 0 12px; }}
nav {{ display:flex; flex-wrap:wrap; gap:6px; margin:12px 0; }}
nav button {{ border:1px solid var(--line); background:var(--card); color:var(--ink); border-radius:16px; padding:6px 12px; cursor:pointer; font:inherit; font-size:13px; }}
nav button[aria-pressed=true] {{ background:var(--accent); border-color:var(--accent); color:#fff; }}
figure {{ margin:0; background:#fff; border:1px solid var(--line); border-radius:8px; overflow:auto; max-height:80vh; }}
figure svg {{ display:block; }}
section {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px 16px; margin:16px 0; }}
h2 {{ font-size:18px; margin:4px 0 8px; }}
input[type=search] {{ width:100%; padding:8px 10px; border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--ink); font:inherit; }}
.tablewrap {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; font-size:13px; margin-top:8px; }}
th, td {{ text-align:left; padding:5px 8px; border-bottom:1px solid var(--line); vertical-align:top; }}
th {{ color:var(--muted); font-weight:600; }}
td.s-tbc {{ color:#bf8700; }} td.s-placeholder {{ color:#8250df; }}
li {{ margin:4px 0; }}
.hl path {{ stroke-width:6 !important; stroke-opacity:1 !important; }}
</style>
</head>
<body>
<header>
<h1>Teryx wiring</h1>
<p>Made from <code>config/wiring.yaml</code> in the repo. Nothing here has been checked on the Teryx yet: amber dashed is TBC, purple dotted is a later add-on. Tap a wire in the table to find it on its sheet.</p>
<nav>{tabs}</nav>
</header>
<main>
{panes}
<section>
<h2>Find a wire</h2>
<input type="search" id="q" placeholder="Search: FB.F3, PICO.GP16, winch, 10 mm², tbc">
<div class="tablewrap"><table><thead><tr><th>Wire</th><th>From</th><th>To</th><th>Size</th><th>Fuse</th><th>Via</th><th>Status</th><th>Note</th></tr></thead><tbody id="rows"></tbody></table></div>
</section>
<section>
<h2>Things to check or photograph</h2>
<ul>{checks}</ul>
</section>
</main>
<script>
const DATA = {data};
const figs = [...document.querySelectorAll('figure')];
const btns = [...document.querySelectorAll('nav button')];
function show(sheet) {{
  figs.forEach(f => f.hidden = f.dataset.sheet !== sheet);
  btns.forEach(b => b.setAttribute('aria-pressed', b.dataset.sheet === sheet));
  try {{ localStorage.setItem('teryx-wiring-sheet', sheet); }} catch (e) {{}}
}}
btns.forEach(b => b.onclick = () => show(b.dataset.sheet));
let start = btns[0].dataset.sheet;
try {{ start = localStorage.getItem('teryx-wiring-sheet') || start; }} catch (e) {{}}
show(btns.some(b => b.dataset.sheet === start) ? start : btns[0].dataset.sheet);
const dev = e => {{ const id = e.split('.')[0]; return (DATA.names[id] || id) + ' ' + e; }};
const tbody = document.getElementById('rows');
function draw(q) {{
  q = q.trim().toLowerCase();
  tbody.innerHTML = '';
  for (const w of DATA.wires) {{
    const text = [w.id, dev(w.from), dev(w.to), w.sheet, w.mm2 ? w.mm2 + ' mm²' : '', w.via, w.status, w.note].join(' ').toLowerCase();
    if (q && !q.split(/\\s+/).every(t => text.includes(t))) continue;
    const tr = document.createElement('tr');
    const cells = [w.id, w.from, w.to, w.mm2 ? w.mm2 + ' mm²' : '', w.fuse != null ? w.fuse + ' A' : '', w.via, w.status + (w.optional ? ' (optional)' : ''), w.note];
    cells.forEach((c, i) => {{ const td = document.createElement('td'); td.textContent = c; if (i === 6) td.className = 's-' + w.status; tr.appendChild(td); }});
    tr.style.cursor = 'pointer';
    tr.onclick = () => {{
      show(w.sheet);
      document.querySelectorAll('.hl').forEach(g => g.classList.remove('hl'));
      const g = document.querySelector('figure[data-sheet="' + w.sheet + '"] g[data-wire="' + w.id + '"]');
      if (g) {{ g.classList.add('hl'); g.scrollIntoView({{block: 'center', inline: 'center'}}); }}
    }};
    tbody.appendChild(tr);
  }}
}}
document.getElementById('q').oninput = e => draw(e.target.value);
draw('');
</script>
</body>
</html>
"""


# ----------------------------------------------------------------- output
def outputs(d: dict | None = None) -> dict[Path, str]:
    d = d or load()
    svgs = {k: render_sheet(d, k) for k in d["sheets"]}
    files = {OUT_DIR / f"sheet-{k}.svg": v for k, v in svgs.items()}
    files[OUT_DIR / "README.md"] = render_readme(d)
    files[OUT_DIR / "index.html"] = render_index(d, svgs)
    return files


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
