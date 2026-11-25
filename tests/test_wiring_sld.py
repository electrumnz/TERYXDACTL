"""The whole-vehicle schematic (docs/wiring/): the drawing model is sound and it lays out.

The model (teryx/wiring_sld.py -> docs/wiring/schematic.json) is checked here in Python. The
layout runs in JavaScript (docs/wiring/sld.js with ELK), so the last test runs
tools/wiring_sld_check.mjs under Node: on Linux CI it must run, elsewhere it skips without Node.
"""

import copy
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from teryx import wiring as W
from teryx import wiring_sld as S

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def model():
    return S.build(W.load())


def test_every_wire_is_in_one_section_and_area(model):
    seen = {}
    for sec in model["sections"]:
        for area in sec["areas"]:
            for wid in area["wires"]:
                assert wid not in seen, f"{wid} drawn twice"
                seen[wid] = sec["key"]
    assert set(seen) == {w["id"] for w in model["wires"]}


def test_power_comes_first(model):
    keys = [s["key"] for s in model["sections"]]
    assert keys[:3] == ["hv", "power", "ground"]


def test_every_wire_end_has_a_pin_on_a_part(model):
    for w in model["wires"]:
        area = f"{w['sec']}/{w['sub']}"
        for end, which in ((w["from"], "from"), (w["to"], "to")):
            if w["earth"] == which:
                continue                       # the earth symbol stands in for the star point
            part = model["parts"].get(f"{area}:{end[0]}")
            assert part, f"{w['id']}: {end[0]} not drawn in {area}"
            assert any(p["pin"] == end[1] for p in part["ports"]), f"{w['id']}: no {end[1]} on {part['id']}"


def test_earths_are_symbols_and_listed_at_the_star(model):
    earths = [w for w in model["wires"] if w["earth"]]
    assert len(earths) > 20
    assert {r["wire"] for r in model["earth_refs"]} == {w["id"] for w in earths}
    assert all(w["colour"] == "BK" for w in earths)


def test_control_signals_are_kept_apart_from_power(model):
    lights = next(s for s in model["sections"] if s["key"] == "lights")
    assert [a["key"] for a in lights["areas"]] == ["power", "control"]
    ctrl = set(next(a for a in lights["areas"] if a["key"] == "control")["wires"])
    for w in model["wires"]:
        if w["id"] in ctrl and not w["earth"]:
            doms = {model["devices"][e[0]]["pins"][e[1]]["v"] for e in (w["from"], w["to"])}
            assert doms <= S.LOGIC | {"gnd"}, f"{w['id']} is power but drawn with the control signals"


def test_symbols_are_real_symbols(model):
    kinds = {d: model["devices"][d]["kind"] for d in ("FB", "RELAYS", "LB1", "BAT12", "KEY", "CONTACTOR", "WINCH_MOTOR", "PICO")}
    assert kinds == {"FB": "fuseblock", "RELAYS": "relays", "LB1": "lamp", "BAT12": "battery", "KEY": "key",
                     "CONTACTOR": "contactor", "WINCH_MOTOR": "motor", "PICO": "module"}


def test_symbol_can_be_set_in_the_yaml():
    d = W.load()
    d["devices"]["IMU"]["symbol"] = "camera"
    assert S.build(d)["devices"]["IMU"]["kind"] == "camera"


def test_inline_fuses_and_diodes(model):
    p03 = next(w for w in model["wires"] if w["id"] == "P03")
    assert p03["inline_fuse"] == 7.5 and p03["via_kind"] == "diode"
    # a fuse block way is drawn in the block, not again on the wire
    assert all(w["inline_fuse"] is None for w in model["wires"] if w["from"][0] in ("FB", "FB2"))


def test_colour_from_the_yaml_wins():
    d = W.load()
    w = next(x for x in d["wires"] if x["id"] == "P03")
    w["colour"] = "RD/WH"
    assert next(x for x in S.build(copy.deepcopy(d))["wires"] if x["id"] == "P03")["colour"] == "RD/WH"


def test_elk_is_kept_with_its_licence():
    vendor = ROOT / "docs" / "wiring" / "vendor"
    assert (vendor / "elk.bundled.js").exists()
    assert "Eclipse Public License" in (vendor / "ELK-LICENSE.md").read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("node") is None and not os.environ.get("TERYX_RIG_REQUIRED"),
                    reason="needs Node to run the page's layout code")
def test_the_drawing_lays_out_with_no_overlaps():
    r = subprocess.run(["node", str(ROOT / "tools" / "wiring_sld_check.mjs")], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
