"""The SG1202 wiring YAML is sane and the SVG matches it."""

from teryx import shinegle_diagram as D


def test_pins_are_valid_and_devices_use_known_pins():
    d = D.load()
    pins = {int(p) for p in d["j1"]}
    assert all(1 <= p <= d["connectors"]["J1"]["pins"] for p in pins)
    for dev in d["devices"].values():
        assert set(dev["pins"]) <= pins, dev["name"]
    statuses = {v["status"] for v in d["j1"].values()}
    assert statuses <= set(D.STATUS_STYLE)


def test_programmer_pins_match_the_manual():
    d = D.load()
    names = {int(p): v["name"] for p, v in d["j1"].items()}
    assert [names[p] for p in d["devices"]["programmer"]["pins"]] == ["V12_OUT", "SCI_TX", "SCI_RX", "GND"]


def test_svg_is_up_to_date():
    assert D.OUTPUT.read_text(encoding="utf-8") == D.render(), "run: python -m teryx shinegle-diagram"
