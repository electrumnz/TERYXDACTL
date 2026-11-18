"""Draws our own wiring diagram of the Shinegle SG1202 from config/shinegle-sg1202.yaml.

    python -m teryx shinegle-diagram     writes docs/img/sg1202-wiring.svg

The YAML is the source of truth. The SVG is plain, single line, and readable by
people and by other tools (every wire carries data-pin / data-name attributes).
"""

from __future__ import annotations

from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "config" / "shinegle-sg1202.yaml"
OUTPUT = ROOT / "docs" / "img" / "sg1202-wiring.svg"

STATUS_STYLE = {
    "from_manual": ("#1f6feb", ""),          # solid blue
    "measured": ("#1a7f37", ""),             # solid green
    "tbc": ("#bf8700", "6 4"),               # dashed amber
    "unknown": ("#8c959f", "2 4"),           # dotted grey
}

# Where each outside device sits: (side, order). Left = control side, right = motor side.
LAYOUT = [
    ("key", "left"), ("shifter", "left"), ("throttle", "left"), ("programmer", "left"),
    ("speedo", "left"),
    ("speed_sensor", "right"), ("motor_temp", "right"),
]


def load(path: Path = SOURCE) -> dict:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _t(x, y, s, size=13, anchor="start", weight="normal", fill="#1f2328"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
            f'font-weight="{weight}" fill="{fill}">{escape(str(s))}</text>')


def render(data: dict | None = None) -> str:
    d = data or load()
    j1 = {int(k): v for k, v in d["j1"].items()}
    W = 1200
    ctrl_x, ctrl_w = 470, 260
    row = 22
    out: list[str] = []

    # --- devices and the pins they use, laid out top to bottom per side
    y_left, y_right = 150, 150
    wires: list[str] = []
    boxes: list[str] = []
    pin_y: dict[int, list[int]] = {}
    for key, side in LAYOUT:
        dev = d["devices"][key]
        pins = dev["pins"]
        h = max(44, row * len(pins) + 18)
        y0 = y_left if side == "left" else y_right
        bx = 40 if side == "left" else W - 300
        boxes.append(f'<rect x="{bx}" y="{y0}" width="260" height="{h}" rx="6" '
                     f'fill="#f6f8fa" stroke="#57606a"/>')
        boxes.append(_t(bx + 10, y0 + 18, dev["name"], 13, weight="bold"))
        note = dev.get("note") or (f'via {dev["via"]}' if dev.get("via") else "")
        if note:
            boxes.append(_t(bx + 10, y0 + h - 8, note, 10, fill="#57606a"))
        for i, p in enumerate(pins):
            y = y0 + 30 + i * row - (0 if len(pins) > 1 else 0)
            info = j1.get(p, {"name": f"J1-{p}", "status": "unknown"})
            colour, dash = STATUS_STYLE.get(info.get("status", "unknown"), STATUS_STYLE["unknown"])
            x1, x2 = (bx + 260, ctrl_x) if side == "left" else (ctrl_x + ctrl_w, bx)
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            wires.append(
                f'<g data-pin="J1-{p}" data-name="{escape(info["name"])}" data-status="{info.get("status")}">'
                f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{colour}" stroke-width="2"{dash_attr}/>'
                + _t((x1 + x2) / 2, y - 4, f'J1-{p} {info["name"]}', 11, "middle", fill=colour)
                + "</g>")
            pin_y.setdefault(p, []).append(y)
        if side == "left":
            y_left += h + 16
        else:
            y_right += h + 16

    # --- power side, drawn under the right-hand devices
    py = max(y_right, 330) + 10
    power_rows = [("B+", "Battery + via 150 A air-break switch"), ("B-", "Battery -"),
                  ("U", "Motor U"), ("V", "Motor V"), ("W", "Motor W")]
    for i, (name, label) in enumerate(power_rows):
        y = py + i * 26
        wires.append(f'<g data-pin="{name}" data-status="from_manual">'
                     f'<line x1="{ctrl_x + ctrl_w}" y1="{y}" x2="{W - 300}" y2="{y}" '
                     f'stroke="#cf222e" stroke-width="4"/>'
                     + _t(ctrl_x + ctrl_w + 10, y - 6, name, 12, weight="bold", fill="#cf222e")
                     + "</g>")
        boxes.append(_t(W - 290, y + 4, label, 12))
    bottom = max(y_left, py + len(power_rows) * 26) + 20

    # --- not-drawn items (CAN, brake)
    nd_y = bottom + 30
    nd = [_t(ctrl_x, nd_y, "Not drawn in the manual (pins TBC):", 13, weight="bold", fill="#9a6700")]
    for i, item in enumerate(d.get("not_drawn", [])):
        nd.append(f'<g data-pin="TBC" data-name="{escape(item["name"])}" data-status="tbc">'
                  + _t(ctrl_x, nd_y + 20 + i * 18, f'{item["name"]}: {item["note"]}', 12, fill="#9a6700")
                  + "</g>")
    unknown = [p for p in range(1, 36) if p not in j1]
    nd.append(_t(ctrl_x, nd_y + 20 + len(d.get("not_drawn", [])) * 18,
                 f"J1 pins with no known use: {', '.join(map(str, unknown))}", 12, fill="#57606a"))
    H = nd_y + 60 + len(d.get("not_drawn", [])) * 18

    # --- controller box
    c = d["controller"]
    ctrl = [f'<rect x="{ctrl_x}" y="120" width="{ctrl_w}" height="{bottom - 120}" rx="10" '
            f'fill="#ffffff" stroke="#1f2328" stroke-width="2"/>',
            _t(ctrl_x + ctrl_w / 2, 150, f'Shinegle {c["model"]}', 18, "middle", "bold"),
            _t(ctrl_x + ctrl_w / 2, 170, "AC motor controller", 12, "middle"),
            _t(ctrl_x + ctrl_w / 2, 188, f'{c["battery_v"][0]}-{c["battery_v"][1]} V, '
               f'{c["max_current_a"]} A max', 12, "middle", fill="#57606a"),
            _t(ctrl_x + ctrl_w / 2, bottom - 14, "J1: AMP 35-way 776163-1", 11, "middle", fill="#57606a")]

    legend = [_t(40, 40, "Shinegle SG1202 wiring (Teryx OS redraw)", 22, weight="bold"),
              _t(40, 62, "Source: Shinegle SG12X2 manual, Fig. 2 and 3. Data: config/shinegle-sg1202.yaml",
                 12, fill="#57606a")]
    lx = 40
    for label, key in (("From the manual", "from_manual"), ("Measured on the Teryx", "measured"),
                       ("Expected, pin TBC", "tbc"), ("Unknown", "unknown")):
        colour, dash = STATUS_STYLE[key]
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        legend.append(f'<line x1="{lx}" y1="90" x2="{lx + 34}" y2="90" stroke="{colour}" '
                      f'stroke-width="2"{dash_attr}/>')
        legend.append(_t(lx + 40, 94, label, 12))
        lx += 220
    legend.append(_t(40, 112, "Programmer lead carries +12 V on J1-25: never plug it into a USB port.",
                     12, weight="bold", fill="#cf222e"))

    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
               f'height="{H}" font-family="Arial, Helvetica, sans-serif">')
    out.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    out += legend + ctrl + boxes + wires + nd
    out.append("</svg>")
    return "\n".join(out) + "\n"


def write(path: Path = OUTPUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(), encoding="utf-8")
    return path
