import random

import pytest

from teryx.canbus.codec import Message, Signal
from teryx.canbus.registry import ALL_MESSAGES


@pytest.mark.parametrize("msg", ALL_MESSAGES, ids=lambda m: m.name)
def test_every_message_round_trips(msg):
    rng = random.Random(msg.can_id)
    for _ in range(50):
        values = {}
        for s in msg.signals:
            raw = rng.randint(s.raw_min, s.raw_max)
            values[s.name] = raw * s.scale + s.offset
        decoded = msg.decode(msg.encode(values))
        for s in msg.signals:
            assert decoded[s.name] == pytest.approx(values[s.name], abs=s.scale / 2 + 1e-9), s.name


def test_values_are_clamped_not_wrapped():
    m = Message("T", 0x1, "dash", 0, signals=(Signal("a", 0, 8), Signal("b", 8, 8, signed=True)))
    d = m.decode(m.encode({"a": 999, "b": -999}))
    assert d == {"a": 255, "b": -128}


def test_overlapping_signals_are_refused():
    with pytest.raises(ValueError):
        Message("T", 0x1, "dash", 0, signals=(Signal("a", 0, 8), Signal("b", 4, 8)))


def test_layouts_match_the_io_list():
    from teryx.canbus import messages as M
    # 0x703 hold-to-run: tray i8 byte 0, winch i8 byte 1, armed bit byte 2
    data = M.PI_HOLD.encode({"tray": -1, "winch": 1, "winch_armed": 1})
    assert data[:3] == bytes([0xFF, 0x01, 0x01])
    # 0x713: 12V as u16 mV
    assert M.PICO_POWER.encode({"aux_12v": 13.6, "pico_temp": -5})[:3] == (13600).to_bytes(2, "little") + bytes([251])
    # Shinegle speed frame the Pico reads: u16 0.1 km/h, direction byte 2
    from teryx.canbus import shinegle as SG
    assert SG.SG_MOTOR.can_id == 0x180
    assert SG.SG_MOTOR.encode({"speed": 12.3, "direction": 2})[:3] == (123).to_bytes(2, "little") + b"\x02"


def test_protocol_doc_is_up_to_date():
    from pathlib import Path

    from teryx.canbus.docs import render
    doc = Path(__file__).resolve().parent.parent / "docs" / "CAN_PROTOCOL.md"
    assert doc.read_text(encoding="utf-8") == render(), "run: python -m teryx canmap"


def test_dbc_export_matches_our_codec():
    cantools = pytest.importorskip("cantools")
    from teryx.canbus.dbc import render
    db = cantools.database.load_string(render(), "dbc")
    rng = random.Random(1)
    for msg in ALL_MESSAGES:
        theirs = db.get_message_by_frame_id(msg.can_id)
        values = {s.name: rng.randint(s.raw_min, s.raw_max) * s.scale + s.offset for s in msg.signals}
        decoded = theirs.decode(msg.encode(values), decode_choices=False)
        for s in msg.signals:
            assert decoded[s.name] == pytest.approx(values[s.name], abs=s.scale / 2 + 1e-9)


def test_dbc_file_is_up_to_date():
    from pathlib import Path

    from teryx.canbus.dbc import render
    dbc = Path(__file__).resolve().parent.parent / "docs" / "teryx.dbc"
    assert dbc.read_text(encoding="utf-8") == render(), "run: python -m teryx canmap"
