"""The parts list, made from config/bom.yaml and config/wiring.yaml.

    python -m teryx bom           check, then write the list into docs/
    python -m teryx bom --check   only check (tests run this)

Every device in the wiring must be bought, owned, kit or later in bom.yaml,
and every `via:` part must be known. Wire by size, CAN cable, fuses, fuse
holders, lugs and waterproof plugs are counted from the wiring itself.
"""

from __future__ import annotations

import csv
import io
import math
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "config" / "bom.yaml"
WIRING = ROOT / "config" / "wiring.yaml"
CSV_OUT = ROOT / "docs" / "pbtech-order.csv"
MD_OUT = ROOT / "docs" / "pbtech-order.md"
START = "<!-- parts list: made by `python -m teryx bom` from config/bom.yaml + config/wiring.yaml. Don't edit by hand -->"
END = "<!-- end parts list -->"

NOT_WIRE = {"hv", "hvneg", "motor", "usb", "hdmi", "csi", "pcie", "video", "audio", "can", "spk"}
BOX_ZONES = {"control_box", "dash"}


def load() -> tuple[dict, dict]:
    with open(SOURCE, encoding="utf-8") as f:
        bom = yaml.safe_load(f)
    with open(WIRING, encoding="utf-8") as f:
        wiring = yaml.safe_load(f)
    return bom, wiring


def _pin(wiring: dict, ref: str) -> tuple[str, str, dict]:
    dev, pin = ref.split(".", 1)
    pv = (wiring["devices"][dev].get("pins") or {}).get(pin) or {}
    if isinstance(pv, str):
        pv = {"v": pv}
    return dev, pin, pv


def placed(bom: dict) -> dict[str, list[str]]:
    """Device id -> every place in bom.yaml that accounts for it."""
    out: dict[str, list[str]] = {}
    for line in bom["lines"]:
        for dev in line.get("covers") or []:
            out.setdefault(dev, []).append(f"line {line['id']}")
    for kind in ("owned", "kit", "later"):
        for dev in bom.get(kind) or {}:
            out.setdefault(dev, []).append(kind)
    return out


def check(bom: dict | None = None, wiring: dict | None = None) -> list[str]:
    if bom is None or wiring is None:
        bom, wiring = load()
    problems = []
    devices = wiring["devices"]
    where = placed(bom)
    for dev in devices:
        if dev not in where:
            problems.append(f"{dev} ({devices[dev].get('name')}) is in the wiring but not on the parts list")
        elif len(where[dev]) > 1:
            problems.append(f"{dev} is on the parts list more than once: {', '.join(where[dev])}")
    for dev in where:
        if dev not in devices:
            problems.append(f"{dev} is on the parts list but not in the wiring")
    ids = Counter(line["id"] for line in bom["lines"])
    problems += [f"line id {i} is used {n} times" for i, n in ids.items() if n > 1]
    for line in bom["lines"]:
        if line["shop"] not in bom["shops"]:
            problems.append(f"line {line['id']}: unknown shop {line['shop']}")
        if not line.get("qty") or line.get("each") is None:
            problems.append(f"line {line['id']}: needs a qty and a price")
    for w in wiring["wires"]:
        via = w.get("via")
        if via and via not in bom["via_parts"]:
            problems.append(f"wire {w['id']}: via '{via}' has no parts in via_parts")
    for dev in bom.get("plugs") or []:
        if dev not in devices:
            problems.append(f"plug for unknown device {dev}")
    return problems


# ------------------------------------------------------------------ counting
def _skip_wire(bom: dict, wiring: dict, w: dict) -> bool:
    """Wires that aren't ours to buy: kit looms, later parts, winch kit cables."""
    a, b = w["from"].split(".")[0], w["to"].split(".")[0]
    later, kit = bom.get("later") or {}, bom.get("kit") or {}
    if a in later or b in later:
        return True
    if a in kit and b in kit and not w.get("via"):   # a new lead with a diode in it is ours to buy
        return True
    if w.get("sys") == "hv":
        return True
    note = (w.get("note") or "").lower()
    if "came with the winch" in note or "winch kit" in note:
        return True
    return w.get("mm2") == 35 and w.get("status") == "confirmed"


def _length(bom: dict, wiring: dict, w: dict) -> float:
    za = wiring["devices"][w["from"].split(".")[0]].get("zone")
    zb = wiring["devices"][w["to"].split(".")[0]].get("zone")
    if za == zb:
        return bom["zone_m"]["same"]
    key = "-".join(sorted([za, zb]))
    return bom["zone_m"].get(key, 2.0)


def counts(bom: dict, wiring: dict) -> dict:
    """Everything counted from the wiring."""
    wire_m: Counter = Counter()
    can_m = spk_m = 0.0
    blade: Counter = Counter()
    inline_blade = 0
    midi: Counter = Counter()
    lugs: Counter = Counter()
    vias: Counter = Counter()
    plug_pins: dict[str, set] = {d: set() for d in bom.get("plugs") or []}
    for w in wiring["wires"]:
        if _skip_wire(bom, wiring, w):
            continue
        a, pa_name, pa = _pin(wiring, w["from"])
        b, pb_name, pb = _pin(wiring, w["to"])
        v = pa.get("v") or pb.get("v")
        za = wiring["devices"][a].get("zone")
        zb = wiring["devices"][b].get("zone")
        length = _length(bom, wiring, w)
        for via, parts in (bom["via_parts"].get(w.get("via")) or {}).items() if w.get("via") else ():
            vias[via] += parts
        for dev, pin in ((a, pa_name), (b, pb_name)):
            if dev in plug_pins:
                plug_pins[dev].add(pin)
        if v == "can":
            can_m += length
            continue
        if v == "spk":
            spk_m += length * 2
            continue
        if v in NOT_WIRE:
            continue
        mm2 = w.get("mm2")
        if mm2 is None and za == zb and za in BOX_ZONES:
            continue  # jumper wire inside a box
        mm2 = mm2 or 0.5
        wire_m[mm2] += length
        if mm2 >= 4:
            lugs[mm2] += 2
        fuse = w.get("fuse")
        if fuse and pa.get("supply") and a != "FB":
            if fuse <= 30:
                inline_blade += 1
                blade[fuse] += 1
            elif fuse <= 100:
                midi[fuse] += 1
    for pin, pv in (wiring["devices"]["FB"].get("pins") or {}).items():
        if isinstance(pv, dict) and pv.get("fuse_a"):
            blade[pv["fuse_a"]] += 1
    plugs: Counter = Counter()
    for dev, pins in plug_pins.items():
        n = len(pins)
        size = next((s for s in sorted(bom["plug_pair"]) if s >= n), max(bom["plug_pair"]))
        if n:
            plugs[size] += 1
    return {"wire_m": wire_m, "can_m": can_m, "spk_m": spk_m, "blade": blade,
            "inline_blade": inline_blade, "midi": midi, "lugs": lugs, "vias": vias, "plugs": plugs}


def _up(x: float, step: int = 5) -> int:
    """Add 25% for routing and spare, then round up to the step."""
    return int(math.ceil(x * 1.25 / step) * step)


def _num(x) -> str:
    return f"{x:g}"


def all_lines(bom: dict, wiring: dict) -> list[dict]:
    c = counts(bom, wiring)
    lines = []
    for line in bom["lines"]:
        line = dict(line)
        if line.get("notes") == "AUTO":
            line["notes"] = "Contents, counted from the wiring: " + ", ".join(
                f"{k} x{v}" for k, v in sorted(c["vias"].items())) + ". Buy a few spare of each"
        lines.append(line)
    src = "Estimate; counted from config/wiring.yaml"
    for mm2, m in sorted(c["wire_m"].items()):
        qty = _up(m, 1 if mm2 >= 10 else 5)  # thick cable is sold by the metre
        lines.append({"id": f"wire_{mm2}", "shop": "local", "part": f"Auto cable {_num(mm2)} mm² (metres)", "qty": qty,
                      "each": bom["wire_price_m"][mm2], "source": src,
                      "notes": f"About {m:.0f} m in the plan + 25%. Split red (+) / black (-) / a signal colour"})
    if c["can_m"]:
        lines.append({"id": "can_cable", "shop": "local", "part": "CAN cable, 2-core twisted + screen (metres)",
                      "qty": _up(c["can_m"]), "each": bom["can_cable_price_m"], "source": src})
    if c["spk_m"]:
        lines.append({"id": "spk_cable", "shop": "local", "part": "Speaker cable (metres)",
                      "qty": max(10, _up(c["spk_m"])), "each": bom["speaker_cable_price_m"], "source": src})
    blade_txt = ", ".join(f"{_num(a)} A x{n + 2}" for a, n in sorted(c["blade"].items()))
    lines.append({"id": "blade_fuses", "shop": "local", "part": "Standard blade fuses, Narva or Jaycar (not AliExpress)",
                  "qty": sum(n + 2 for n in c["blade"].values()), "each": bom["blade_fuse_each"], "source": src,
                  "notes": f"{blade_txt} (2 spare of each)"})
    if c["inline_blade"]:
        lines.append({"id": "inline_holders", "shop": "local", "part": "Waterproof inline blade fuse holder",
                      "qty": c["inline_blade"], "each": bom["inline_holder_each"], "source": src,
                      "notes": "Feeds that don't come off the fuse block (bucks, screen, amp, 12V sense, accessories)"})
    for amps, n in sorted(c["midi"].items()):
        lines.append({"id": f"midi_{_num(amps)}", "shop": "local", "part": f"{_num(amps)} A MIDI fuse + bolt-down holder",
                      "qty": n, "each": bom["midi_fuse_each"] + bom["midi_holder_each"], "source": src,
                      "notes": "At the battery, one per big feed (fuse block, power steering, amp)"})
    for mm2, n in sorted(c["lugs"].items()):
        lines.append({"id": f"lugs_{mm2}", "shop": "local", "part": f"Tinned lugs for {_num(mm2)} mm², M8 hole",
                      "qty": n + 2, "each": bom["lug_each"], "source": src, "notes": "2 spare"})
    for size, n in sorted(c["plugs"].items()):
        lines.append({"id": f"plug_{size}", "shop": "aliexpress", "part": f"Waterproof {size}-pin plug pair (DT style)",
                      "qty": n + 1, "each": bom["plug_pair"][size], "source": src,
                      "notes": "So lights, actuators, switches and cameras unplug; 1 spare"})
    order = {k: v["order"] for k, v in bom["shops"].items()}
    lines.sort(key=lambda ln: order[ln["shop"]])
    for ln in lines:
        ln["total"] = round(ln["qty"] * ln["each"], 2)
    return lines


# ------------------------------------------------------------------ output
def _money(x: float) -> str:
    return f"{x:,.2f}"


def render_md(bom: dict, wiring: dict) -> str:
    lines = all_lines(bom, wiring)
    out = [START, ""]
    totals = {}
    for shop, info in sorted(bom["shops"].items(), key=lambda kv: kv[1]["order"]):
        mine = [ln for ln in lines if ln["shop"] == shop]
        total = sum(ln["total"] for ln in mine)
        totals[info["title"]] = total
        out += [f"### {info['title']}", "", "| Part | Qty | Each NZ$ | Total NZ$ | Price from | Notes |", "|---|---|---|---|---|---|"]
        for ln in mine:
            part = f"[{ln['part']}]({ln['link']})" if ln.get("link") else ln["part"]
            if ln.get("sku"):
                part += f" ({ln['sku']})"
            out.append(f"| {part} | {ln['qty']} | {_money(ln['each'])} | {_money(ln['total'])} | {ln.get('source', '')} | {ln.get('notes', '')} |")
        out += [f"| **Total** | | | **{_money(total)}** | | |", ""]
    grand = sum(totals.values())
    out += ["### Totals", "", "| Shop | NZ$ |", "|---|---|"]
    out += [f"| {k} | {_money(v)} |" for k, v in totals.items()]
    out += [f"| **Everything** | **{_money(grand)}** |", ""]
    out += ["### Already got (not in the totals)", ""]
    out += [", ".join(sorted(set(bom["owned"].values()))) + ". " +
            ", ".join(f"{b['part']} (NZ${b['each']:.0f})" for b in bom.get("bought") or []) + ".", ""]
    out += ["### Comes with the Shinegle kit or the stock Teryx", "",
            ", ".join(f"{wiring['devices'][d]['name']}" for d in bom["kit"]) + ".", ""]
    out += ["### Later (not in the totals)", "", "| Part | Shop | About NZ$ | Notes |", "|---|---|---|---|"]
    out += [f"| {ln['part']} | {ln['shop']} | {_money(ln['each'])} | {ln.get('notes', '')} |" for ln in bom["later_lines"]]
    out += ["", "Wiring parts waiting on that: " + "; ".join(f"{d}: {t}" for d, t in bom["later"].items()) + ".", "",
            "Tools aren't listed (crimpers, soldering iron, heat gun, multimeter, 3D printer).", "", END]
    return "\n".join(out)


def render_csv(bom: dict, wiring: dict) -> str:
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    wr.writerow(["Group", "Shop", "Part", "SKU", "Qty", "Price NZ$ incl GST (each)", "Line total NZ$", "Price source", "Notes", "Link"])
    lines = all_lines(bom, wiring)
    for ln in lines:
        wr.writerow([bom["shops"][ln["shop"]]["title"], ln["shop"], ln["part"], ln.get("sku", ""), ln["qty"],
                     f"{ln['each']:.2f}", f"{ln['total']:.2f}", ln.get("source", ""), ln.get("notes", ""), ln.get("link", "")])
    for ln in bom["later_lines"]:
        wr.writerow(["Later", ln["shop"], ln["part"], "", 0, f"{ln['each']:.2f}", "0.00", "", ln.get("notes", ""), ""])
    for shop, info in sorted(bom["shops"].items(), key=lambda kv: kv[1]["order"]):
        wr.writerow(["", "", f"TOTAL {info['title']}", "", "", "", f"{sum(ln['total'] for ln in lines if ln['shop'] == shop):.2f}", "", "", ""])
    wr.writerow(["", "", "TOTAL everything", "", "", "", f"{sum(ln['total'] for ln in lines):.2f}", "", "", ""])
    return buf.getvalue()


def outputs(bom: dict | None = None, wiring: dict | None = None) -> dict[Path, str]:
    if bom is None or wiring is None:
        bom, wiring = load()
    md = MD_OUT.read_text(encoding="utf-8")
    if START not in md or END not in md:
        raise ValueError(f"{MD_OUT.name} is missing the parts list markers")
    head, rest = md.split(START, 1)
    tail = rest.split(END, 1)[1]
    return {MD_OUT: head + render_md(bom, wiring) + tail, CSV_OUT: render_csv(bom, wiring)}


def main(check_only: bool = False) -> int:
    problems = check()
    for p in problems:
        print("problem:", p)
    if problems:
        print(f"{len(problems)} problem(s) in config/bom.yaml")
        return 1
    print("config/bom.yaml: every wiring part is on the list")
    if not check_only:
        for path, text in outputs().items():
            path.write_text(text, encoding="utf-8", newline="\n")
            print("wrote", path.relative_to(ROOT))
    return 0
