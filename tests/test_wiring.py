"""The whole-vehicle wiring in config/wiring.yaml is sane, and docs/wiring/ matches it."""

import copy

import pytest

from teryx import wiring as W


@pytest.fixture(scope="module")
def data():
    return W.load()


def test_wiring_has_no_problems(data):
    problems = W.check(copy.deepcopy(data))
    assert problems == [], "\n".join(problems)


def test_generated_files_are_up_to_date(data):
    for path, text in W.outputs(copy.deepcopy(data)).items():
        assert path.exists(), f"missing {path.name}: run python -m teryx wiring"
        assert path.read_text(encoding="utf-8") == text, f"{path.name} is stale: run python -m teryx wiring"


def _with(data, **wire):
    d = copy.deepcopy(data)
    w = {"id": "ZZ1", "sys": "power", "status": "planned", **wire}
    w["_a"], w["_b"] = W._split(w["from"]), W._split(w["to"])
    d["wires"].append(w)
    return W.check(d)


def test_catches_12v_on_a_3v3_pin(data):
    assert any("ZZ1" in p and "12v" in p for p in _with(data, **{"from": "FB.F1", "to": "PICO.GP16", "mm2": 1.5}))


def test_catches_a_wire_too_thin_for_its_fuse(data):
    probs = _with(data, **{"from": "BAT12.pos", "to": "AMP.REM", "mm2": 0.5, "fuse": 30})
    assert any("ZZ1" in p and "only good for" in p for p in probs)


def test_catches_an_unfused_feed(data):
    probs = _with(data, **{"from": "BAT12.pos", "to": "SCREEN.DC_IN", "mm2": 1.0})
    assert any("ZZ1" in p and "no fuse" in p for p in probs)


def test_catches_the_pcie_port_being_taken(data):
    probs = _with(data, **{"from": "SSD.USB", "to": "PI5.PCIE", "sys": "dash"})
    assert any("AI HAT+ 2" in p for p in probs)


def test_catches_a_pin_used_twice(data):
    probs = _with(data, **{"from": "PICO.GP16", "to": "MOSFET.IN2", "sys": "lights"})
    assert any("PICO.GP16" in p for p in probs)


def test_catches_traction_wired_to_12v(data):
    probs = _with(data, **{"from": "PACK.pos", "to": "FB.IN", "via": "anything"})
    assert any("traction side" in p for p in probs)


def test_each_can_bus_has_two_ends(data):
    d = copy.deepcopy(data)
    d["devices"]["PICO_CAN"]["pins"]["CANH"]["term"] = True
    assert any("terminator" in p for p in W.check(d))


def test_io_map_mismatch_is_caught(data):
    d = copy.deepcopy(data)
    d["wires"] = [w for w in d["wires"] if w["id"] != "LT11"]   # GP16 -> front bar 1 MOSFET
    assert any("light.front_1" in p for p in W.check(d))
