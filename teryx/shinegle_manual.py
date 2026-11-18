"""Our copy of the Shinegle SG1810 programmer manual's tables.

    python -m teryx shinegle-manual     writes docs/shinegle-sg1810-tables.md

The YAML files are the source of truth:
    config/shinegle-sg1810-params.yaml   programmer parameters (pages 0-f)
    config/shinegle-faults.yaml          fault codes 1-46

`fault(code)` gives the dash a plain English name for a controller error code.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARAMS = ROOT / "config" / "shinegle-sg1810-params.yaml"
FAULTS = ROOT / "config" / "shinegle-faults.yaml"
OUTPUT = ROOT / "docs" / "shinegle-sg1810-tables.md"
DASH_JS = ROOT / "dash" / "web" / "js" / "shinegle-codes.js"


def _load(path: Path) -> dict:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_params() -> list[dict]:
    return _load(PARAMS)["params"]


def load_faults() -> list[dict]:
    return _load(FAULTS)["faults"]


def _codes(entry: dict) -> range:
    c = entry["code"]
    if isinstance(c, int):
        return range(c, c + 1)
    lo, hi = (int(x) for x in str(c).split("-"))
    return range(lo, hi + 1)


def fault(code: int) -> dict | None:
    """The fault entry for a controller error code, or None if it's not in the table."""
    for f in load_faults():
        if code in _codes(f):
            return f
    return None


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return "<br>".join(f"{i}. {_cell(x)}" for i, x in enumerate(v, 1))
    return str(v).replace("|", "\\|").replace("\n", " ")


def render() -> str:
    p = _load(PARAMS)
    out = [
        "# SG1810 programmer: parameter and fault tables",
        "",
        "Made by `python -m teryx shinegle-manual` from",
        "[`config/shinegle-sg1810-params.yaml`](../config/shinegle-sg1810-params.yaml) and",
        "[`config/shinegle-faults.yaml`](../config/shinegle-faults.yaml). Edit those, not this file.",
        "The rest of the manual is in [`shinegle-sg1810-programmer.md`](shinegle-sg1810-programmer.md).",
        "",
        "The Chinese is from the manual. The English is our own translation of it.",
        "Values are \"for reference only\" (the manual's words) and won't match every controller.",
        "",
        "## Parameters (附表1 编程器参数)",
        "",
        "**Green** = green in the manual, the only ones Shinegle allow changing (to suit the vehicle's load).",
        "",
        "| Page | Name | Value | 说明 | Description | 备注 | Remark | Note |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in p["params"]:
        name = f'**{r["name"]}** (green)' if r.get("adjustable") else r["name"]
        out.append("| " + " | ".join(_cell(x) for x in (
            r["page"], name, r.get("value"), r.get("cn"), r.get("en"),
            r.get("remark_cn"), r.get("remark"), r.get("note"))) + " |")
    fn = p["footnote"]
    out += ["", f'备注：{fn["cn"]}', "", f'Footnote: {fn["en"]}', ""]

    out += [
        "## Fault codes (附表2 SHINEGLE 控制器故障代码列表及原因分析)",
        "",
        "The code is the LED flash count and the ErrorCode the programmer shows.",
        "",
        "| Code | Fault | Causes | Fixes | Note |",
        "|---|---|---|---|---|",
    ]
    for f in load_faults():
        out.append("| " + " | ".join(_cell(x) for x in (
            f["code"], f.get("en"), f.get("cause"), f.get("fix"), f.get("note"))) + " |")
    out += ["", "### 中文原文 (the Chinese)", "",
            "| 代码 | 编程器显示 | 故障原因 | 解决方法 |", "|---|---|---|---|"]
    for f in load_faults():
        out.append("| " + " | ".join(_cell(x) for x in (
            f["code"], f.get("cn"), f.get("cause_cn"), f.get("fix_cn"))) + " |")
    return "\n".join(out) + "\n"


def render_js() -> str:
    """The fault table as a JS module for the dash, so a controller ErrorCode shows the
    manual's words (and what to do) instead of a bare number."""
    import json
    rows = {}
    for f in load_faults():
        if f["code"] == 1 or "Reserved" in f["en"]:
            continue
        fix = [x for x in (f.get("fix") or []) if x and x != "None"]
        for code in _codes(f):
            rows[code] = {"text": f["en"], "fix": (". ".join(x.rstrip(". …") for x in fix) + ".") if fix else ""}
    body = ",\n".join(f"  {k}: {json.dumps(v, ensure_ascii=False)}" for k, v in sorted(rows.items()))
    return ("// Shinegle SG1810 controller ErrorCodes (same number as the LED flash count).\n"
            "// Made by `python -m teryx shinegle-manual` from config/shinegle-faults.yaml. Don't edit by hand.\n"
            "export const SHINEGLE_CODES = {\n" + body + ",\n};\n")


def write(path: Path = OUTPUT, js: Path = DASH_JS) -> Path:
    path.write_text(render(), encoding="utf-8")
    js.write_text(render_js(), encoding="utf-8")
    return path
