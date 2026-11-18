"""The parts list in config/bom.yaml covers every part in config/wiring.yaml."""

import copy

import pytest

from teryx import bom as B


@pytest.fixture(scope="module")
def data():
    return B.load()


def test_every_wiring_part_is_on_the_list(data):
    problems = B.check(*copy.deepcopy(data))
    assert problems == [], "\n".join(problems)


def test_generated_list_is_up_to_date(data):
    for path, text in B.outputs(*copy.deepcopy(data)).items():
        assert path.read_text(encoding="utf-8") == text, f"{path.name} is stale: run python -m teryx bom"


def test_new_wiring_part_not_on_the_list_fails(data):
    bom, wiring = copy.deepcopy(data)
    wiring["devices"]["NEW_THING"] = {"name": "New thing", "zone": "cab", "status": "planned"}
    assert any("NEW_THING" in p for p in B.check(bom, wiring))


def test_part_listed_twice_fails(data):
    bom, wiring = copy.deepcopy(data)
    bom["owned"]["PI5"] = "a second Pi"
    assert any("PI5" in p and "more than once" in p for p in B.check(bom, wiring))


def test_unknown_via_part_fails(data):
    bom, wiring = copy.deepcopy(data)
    wiring["wires"][0]["via"] = "mystery resistor"
    assert any("mystery resistor" in p for p in B.check(bom, wiring))


def test_counts_come_from_the_wiring(data):
    bom, wiring = copy.deepcopy(data)
    c = B.counts(bom, wiring)
    # 12 fuse block fuses plus the inline ones
    assert sum(c["blade"].values()) >= 12
    assert c["vias"]["1N5408"] >= 6
    assert c["wire_m"][1.5] > 0 and c["can_m"] > 0
