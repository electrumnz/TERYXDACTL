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
        "The rest of the manual (how to use the programmer, our notes) is in",
        "[`shinegle-sg1810-programmer.md`](shinegle-sg1810-programmer.md).",
        "",
        "Copied from the manual's own tables, typos kept. **CN ours** is our own translation",
        "of the Chinese, to check Shinegle's English against. Values are \"for reference only\"",
        "(the manual's words) and won't match every controller.",
        "",
        "## Attached list 1: programmer parameters (附表1 编程器参数)",
        "",
        "**Green** = highlighted green in the manual, the only ones Shinegle say can be changed.",
        "",
        "| Page | Name | Value | Chinese | CN ours | Shinegle English | Remark (Chinese) | Remark CN ours | Remark (English) | Our note |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in p["params"]:
        name = f'**{r["name"]}** (green)' if r.get("adjustable") else r["name"]
        out.append("| " + " | ".join(_cell(x) for x in (
            r["page"], name, r.get("value"), r.get("cn"), r.get("cn_ours"), r.get("en"),
            r.get("remark_cn"), r.get("remark_cn_ours"), r.get("remark_en"), r.get("note"))) + " |")
    fn = p["footnote"]
    out += ["", "**Footnote (备注):**", "", f'> {fn["cn"]}', ">", f'> CN ours: {fn["cn_ours"]}', ">",
            f'> {fn["en"]}', "", f'Our note: {fn["note"]}', ""]

    out += [
        "## Attached list 2: fault codes (附表2 SHINEGLE 控制器故障代码列表及原因分析)",
        "",
        "The code is the LED flash count and the ErrorCode the programmer shows.",
        "",
        "| Code | Chinese | CN ours | Shinegle English | Cause (CN ours) | Cause (Shinegle English) | Fix (CN ours) | Fix (Shinegle English) | Our note |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for f in load_faults():
        out.append("| " + " | ".join(_cell(x) for x in (
            f["code"], f.get("cn"), f.get("cn_ours"), f.get("en"), f.get("cause_cn_ours"),
            f.get("cause_en"), f.get("fix_cn_ours"), f.get("fix_en"), f.get("note"))) + " |")
    out += ["", "### Fault causes and fixes in the original Chinese", "",
            "| Code | 编程器显示 | 故障原因 | 解决方法 |", "|---|---|---|---|"]
    for f in load_faults():
        out.append("| " + " | ".join(_cell(x) for x in (
            f["code"], f.get("cn"), f.get("cause_cn"), f.get("fix_cn"))) + " |")
    return "\n".join(out) + "\n"


def write(path: Path = OUTPUT) -> Path:
    path.write_text(render(), encoding="utf-8")
    return path
