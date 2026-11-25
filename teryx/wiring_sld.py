"""The whole-vehicle schematic: config/wiring.yaml as one big drawing model.

    python -m teryx wiring     writes docs/wiring/schematic.json (with the other wiring files)

docs/wiring/index.html + sld.js read schematic.json, lay the whole thing out in one go
with ELK (elkjs, EPL-2.0, kept unchanged in docs/wiring/vendor/) and draw it as one
canvas on an unlimited pan/zoom grid, with IEC 60617 style symbols that we draw ourselves.

This file decides *what* goes on the drawing, the page decides *where*:

* One canvas, no sheets or frames. Every device is drawn once and every wire runs
  end to end between the two devices it joins.
* Earth wires are drawn as the earth symbol at the device, like any schematic; the
  earth star point lists every one of them.
* Each device and wire still carries the system it belongs to (traction, 12 V, lights
  and so on), so the page can find a system and the wire list can group by it.
* Every device gets a symbol kind: a plain box with pins for boards and controllers,
  real symbols for lamps, switches, fuses, motors, batteries, relays, contactors.
  Set `symbol:` on a device in wiring.yaml to override the guess.
* Wires carry their number, size, suggested colour, fuse and anything in line
  (diode, opto). In-line fuses and diodes become symbols on the wire.

Our own code, MIT like the rest of the repo.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict

from . import wiring as W

# Power first, then control. The keys are wiring.yaml `sheets`.
SECTION_ORDER = ["hv", "power", "ground", "sg", "winch", "lights", "drive", "trailer",
                 "logic", "inputs", "can", "rc", "dash"]

EARTH_POINTS = {("GND_STAR", "G"), ("BAT12", "neg")}


# Symbol kind for each device (wiring.yaml `symbol:` wins).
#   rows kinds:  a symbol per row between two pins, rows joined to one common pin
#   box kinds:   a box with pin labels, with a small glyph saying what it is
ROW_KINDS = {"lamp", "switch", "key", "estop", "limit", "fuse", "breaker", "diode",
             "battery", "motor", "speaker", "isolator", "contactor"}
BOX_KINDS = {"module", "controller", "converter", "machine", "connector", "camera",
             "display", "pot", "relays", "fuseblock", "bus", "star"}

_SYMBOL_GUESS = [
    (r"PACK|BAT12", "battery"),
    (r"HV_ISO", "isolator"),
    (r"CONTACTOR", "contactor"),
    (r"SG1202|EPS_ECU|WINCH_SOL", "controller"),
    (r"MOTOR|ACT_DIFF|EPS_COL", "machine"),
    (r"WINCH_MOTOR|ACT_4WD|ACT_TRAY", "motor"),
    (r"DCDC|.*_BUCK|SCREEN_PSU|GLOVE_USB", "converter"),
    (r"KIT_KEY|KEY", "key"),
    (r"ESTOP", "estop"),
    (r"LIM_.*", "limit"),
    (r"FNR|LIMP_SW|HSW_.*|BRAKE_SW|PARK_SW", "switch"),
    (r"THROTTLE", "pot"),
    (r"GND_STAR", "star"),
    (r"RAIL", "bus"),
    (r"FB2?", "fuseblock"),
    (r"TVS", "diode"),
    (r"BRK_.*", "breaker"),
    (r"RELAYS2?|RC_REL", "relays"),
    (r"LB.*|FLOOD_.*|HEAD_.*|TAIL_.*|BEACON", "lamp"),
    (r"SPEAKERS|SUB", "speaker"),
    (r"TRAILER|TCAM_PLUG", "connector"),
    (r"CAM_.*", "camera"),
    (r"SCREEN", "display"),
]

# Short tag letters, IEC 81346-2 style, shown before the device id.
TAG_LETTER = {
    "battery": "G", "converter": "T", "isolator": "Q", "contactor": "Q", "controller": "A",
    "machine": "M", "motor": "M", "key": "S", "estop": "S", "limit": "B", "switch": "S",
    "pot": "B", "star": "PE", "bus": "W", "fuseblock": "F", "diode": "R", "breaker": "F",
    "relays": "K", "lamp": "E", "speaker": "P", "connector": "X", "camera": "B",
    "display": "P", "module": "A",
}


def symbol_of(dev_id: str, dev: dict) -> str:
    if dev.get("symbol"):
        return dev["symbol"]
    for pat, kind in _SYMBOL_GUESS:
        if re.fullmatch(pat, dev_id):
            return kind
    return "module"


def suggested_colour(d: dict, w: dict) -> str:
    """Wire colour: the wire's own `colour`, else a suggestion from what it carries."""
    if w.get("colour"):
        return str(w["colour"])
    devs = d["devices"]
    a = devs[w["_a"][0]]["pins"][w["_a"][1]]
    b = devs[w["_b"][0]]["pins"][w["_b"][1]]
    vs = {a["v"], b["v"]}
    if vs & {"hv", "motor", "hvneg"}:
        return "OG"                        # high voltage cable is orange
    if "gnd" in vs:
        return "BK"
    if "can" in vs:
        m = re.search(r"CAN_?([HL])", f"{w['_a'][1]} {w['_b'][1]}".upper())
        return {"H": "YE", "L": "GN"}.get(m.group(1), "") if m else ""
    if a.get("supply") or W.fuse_for(d, w) is not None:
        return "RD"
    return ""


# What a wire carries, for the line colour on the drawing (the page can turn colours off).
LINE_KINDS = {"hv": "72 V traction", "12v": "12 V power", "logic": "5 V / 3.3 V logic",
              "gnd": "Earth / negative", "can": "CAN bus", "signal": "Signals, video, audio"}


def line_kind(d: dict, w: dict) -> str:
    devs = d["devices"]
    vs = {devs[e[0]]["pins"][e[1]]["v"] for e in (w["_a"], w["_b"])}
    if vs & {"hv", "motor", "hvneg"}:
        return "hv"
    if vs == {"gnd"}:
        return "gnd"
    if "can" in vs:
        return "can"
    if "12v" in vs:
        return "12v"
    if vs <= {"3v3", "5v", "gnd"}:
        return "logic"
    return "signal"


def _section_of(d: dict, w: dict, home: dict[str, str]) -> str:
    if w["sys"] != "ground":
        return w["sys"]
    ends = [w["_a"], w["_b"]]
    others = [e for e in ends if tuple(e) not in EARTH_POINTS]
    if not others:
        return "ground"
    return home.get(others[0][0], "ground")


def _homes(d: dict) -> dict[str, str]:
    """Each device's main section: where most of its non-earth wires are."""
    count: dict[str, Counter] = defaultdict(Counter)
    for w in d["wires"]:
        if w["sys"] == "ground":
            continue
        for dev, _ in (w["_a"], w["_b"]):
            count[dev][w["sys"]] += 1
    order = {k: i for i, k in enumerate(SECTION_ORDER)}
    return {dev: min(c.items(), key=lambda kv: (-kv[1], order.get(kv[0], 99)))[0] for dev, c in count.items()}


def _row_layout(kind: str, dev: dict) -> dict:
    """Rows for a row-symbol device: [(left pin, right pin or None, glyph)], plus the common pin."""
    pins = list(dev["pins"])
    if kind == "contactor":
        return {"rows": [["in", "out", "contact"], ["coil_pos", "coil_neg", "coil"]], "common": None}
    if len(pins) <= 2:
        return {"rows": [[pins[0], pins[1] if len(pins) > 1 else None, kind]], "common": None}
    common = next((p for p in pins if dev["pins"][p]["v"] == "gnd"), None)
    if common is None:
        common = next((p for p in pins if p.upper() in ("COM", "FEED", "C", "GND", "NEG")), pins[0])
    return {"rows": [[p, None, kind] for p in pins if p != common], "common": common}


def build(d: dict | None = None) -> dict:
    """The drawing model that docs/wiring/sld.js lays out and draws."""
    d = d or W.load()
    devs = d["devices"]
    home = _homes(d)
    sec_keys = [k for k in SECTION_ORDER if k in d["sheets"]] + [k for k in d["sheets"] if k not in SECTION_ORDER]

    wires_out = []
    used: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {"in": 0, "out": 0}))
    earth_refs: list[dict] = []
    for w in d["wires"]:
        sec = _section_of(d, w, home)
        a, b = tuple(w["_a"]), tuple(w["_b"])
        earth_end = None
        if b in EARTH_POINTS and a not in EARTH_POINTS:
            earth_end = "to"
        elif a in EARTH_POINTS and b not in EARTH_POINTS:
            earth_end = "from"
        fuse = w.get("fuse")
        inline_fuse = fuse if (fuse is not None and symbol_of(a[0], devs[a[0]]) != "fuseblock") else None
        kind, _k = _via_kind(w.get("via"))
        out = {
            "id": w["id"], "sec": sec, "from": list(a), "to": list(b),
            "mm2": w.get("mm2"), "fuse": W.fuse_for(d, w), "inline_fuse": inline_fuse,
            "via": w.get("via"), "via_kind": kind, "colour": suggested_colour(d, w), "line": line_kind(d, w),
            "status": w["status"], "optional": bool(w.get("optional")),
            "note": w.get("note", ""), "bus": w.get("bus"), "earth": earth_end,
        }
        wires_out.append(out)
        if earth_end:
            dev_end = a if earth_end == "to" else b
            u = used[dev_end[0]][dev_end[1]]
            u["earth"] = u.get("earth", 0) + 1
            pt = b if earth_end == "to" else a
            earth_refs.append({"wire": w["id"], "dev": dev_end[0], "pin": dev_end[1], "part": dev_end[0],
                               "point": list(pt)})
        else:
            used[a[0]][a[1]]["out"] += 1
            used[b[0]][b[1]]["in"] += 1

    # The earth star: one stub per earth wire, listing where each one lands.
    for ref in earth_refs:
        used[ref["point"][0]][ref["point"][1]]["in"] += 1

    order = {k: i for i, k in enumerate(sec_keys)}
    def sec_of_dev(dev_id):
        return home.get(dev_id, "ground")

    parts: dict[str, dict] = {}
    for dev_id, pins in sorted(used.items(), key=lambda kv: (order.get(sec_of_dev(kv[0]), 99), kv[0])):
        dev = devs[dev_id]
        kind = symbol_of(dev_id, dev)
        ports = []
        # pins in yaml order so boxes read like the datasheet
        for pin in dev["pins"]:
            if pin not in pins:
                continue
            u = pins[pin]
            if u.get("earth"):
                ports.append({"pin": pin, "side": "S"})
                if not (u["in"] or u["out"]):
                    continue
            if u["in"] and u["out"]:
                ports.append({"pin": pin, "side": "W"})
                ports.append({"pin": pin, "side": "E"})
            else:
                ports.append({"pin": pin, "side": "W" if u["in"] >= u["out"] and u["in"] else "E"})
        part = {"id": dev_id, "dev": dev_id, "sec": sec_of_dev(dev_id), "kind": kind, "ports": ports}
        if kind in ROW_KINDS:
            part.update(_row_layout(kind, dev))
        parts[dev_id] = part

    devices_out = {}
    for dev_id, dev in devs.items():
        kind = symbol_of(dev_id, dev)
        devices_out[dev_id] = {
            "name": dev["name"], "zone": dev.get("zone"), "status": dev.get("status"),
            "optional": bool(dev.get("optional")), "note": dev.get("note", ""), "check": dev.get("check", ""),
            "doc": dev.get("doc", ""), "kind": kind, "tag": TAG_LETTER.get(kind, "A"),
            "parts": [dev_id] if dev_id in parts else [],
            "pins": {p: {k: v for k, v in spec.items() if k in ("v", "desc", "fuse_a", "supply", "term")}
                     for p, spec in dev["pins"].items()},
        }

    sections = []
    for i, k in enumerate(sec_keys, 1):
        sections.append({"key": k, "no": i, "title": d["sheets"][k]["title"],
                         "parts": [p for p in parts if parts[p]["sec"] == k],
                         "wires": [w["id"] for w in wires_out if w["sec"] == k]})

    return {
        "version": 2,
        "source": "config/wiring.yaml",
        "lines": LINE_KINDS,
        "statuses": {k: {"colour": c, "dash": dash, "label": label} for k, (c, dash, label) in W.STATUS_STYLE.items()},
        "sections": sections,
        "devices": devices_out,
        "parts": parts,
        "wires": wires_out,
        "earth_refs": earth_refs,
        "wire_table": d.get("wire_table_mm2_to_max_fuse_a", {}),
    }


def _via_kind(via: str | None) -> tuple[str, float]:
    """What sits in line on a wire: 'diode', 'opto', 'divider', 'flyback' or 'plain'."""
    if not via:
        return "plain", 1.0
    t = via.lower()
    if "flyback" in t:
        return "flyback", 0.0
    if "divider" in t:
        return "divider", 1.0
    if "opto" in t:
        return "opto", 1.0
    if "diode" in t or re.search(r"1n\d{4}", t) or "schottky" in t:
        return "diode", 1.0
    return "box", 1.0


def render(d: dict | None = None) -> str:
    return json.dumps(build(d), indent=1, ensure_ascii=False, sort_keys=False) + "\n"
