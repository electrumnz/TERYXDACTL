"""The Shinegle decoding kit: DBC reading, the practice capture, analysis, check, install, capture."""

import random
import threading
import time
from pathlib import Path

import can
import pytest

from teryx.canbus import shinegle as SG
from teryx.canbus.codec import Message, Signal
from teryx.canbus.dbc import DbcError, parse, render
from teryx.canbus.shinegle import Layout
from teryx.decode import session as S
from teryx.decode.analyse import analyse, draft_dbc, write_outputs
from teryx.decode.capture import Capture, Recorder
from teryx.decode.check import check, firmware_matches, install
from teryx.decode.demo import EXPECTED, make_demo
from teryx.decode.procedure import BY_ID, STEPS

# ----------------------------------------------------------------------------- codec / dbc

def test_big_endian_signal_layout():
    # DBC big-endian 16 bit with MSB at byte 0 bit 7: bytes 0-1 hold the value MSB first
    m = Message("T", 1, "shinegle", 0, signals=(Signal("v", 7, 16, big_endian=True, scale=0.1),
                                                 Signal("w", 16, 8)))
    data = m.encode({"v": 123.4, "w": 7})
    assert data[:3] == (1234).to_bytes(2, "big") + b"\x07"
    assert m.decode(data)["v"] == pytest.approx(123.4)


def test_big_endian_overlap_is_refused():
    with pytest.raises(ValueError):
        Message("T", 1, "shinegle", 0, signals=(Signal("a", 7, 16, big_endian=True), Signal("b", 8, 8)))


def test_big_endian_matches_cantools():
    cantools = pytest.importorskip("cantools")
    rng = random.Random(3)
    sigs = (Signal("a", 7, 16, big_endian=True, signed=True, scale=0.5),
            Signal("b", 21, 6, big_endian=True), Signal("c", 24, 12), Signal("d", 39, 3, big_endian=True))
    m = Message("T", 0x123, "shinegle", 10, signals=sigs)
    db = cantools.database.load_string(render([m]), "dbc")
    theirs = db.get_message_by_frame_id(0x123)
    for _ in range(100):
        vals = {s.name: rng.randint(s.raw_min, s.raw_max) * s.scale for s in sigs}
        data = m.encode(vals)
        assert theirs.encode(vals) == data
        got = theirs.decode(data)
        assert all(got[k] == pytest.approx(v) for k, v in vals.items())


def test_dbc_round_trip_keeps_everything():
    text = Path(SG.DBC_PATH).read_text()
    msgs, general = parse(text)
    again, general2 = parse(render(msgs, header_comment=general))
    assert again == msgs and general2 == general
    assert all(m.placeholder for m in msgs)
    assert {m.period_ms for m in msgs} == {50, 100, 200, 500}


def test_dbc_extended_ids_and_errors():
    m = Message("X", 0x0CF11E05, "shinegle", 20, extended=True, signals=(Signal("rpm", 0, 16),))
    back, _ = parse(render([m]))
    assert back[0].extended and back[0].can_id == 0x0CF11E05
    with pytest.raises(DbcError):
        parse('BO_ 1 A: 8 X\n SG_ s m1 : 0|8@1+ (1,0) [0|255] "" X\n')


def test_placeholder_layout_matches_the_old_hand_written_one():
    # The sim and the Pico firmware were written against these bytes
    assert SG.PLACEHOLDER
    assert SG.SPEED_MESSAGE.can_id == 0x180
    data = SG.SPEED_MESSAGE.encode({"speed": 12.3, "direction": 2})
    assert data[:3] == (123).to_bytes(2, "little") + b"\x02"
    faults = SG.BY_NAME["SG_FAULTS"]
    raw = next(v for m, v in SG.encode({**SG.MC_DEFAULTS, "mc.faults": ["over_current", "precharge"]})
               if m is faults)
    assert faults.encode(raw)[:2] == (0b10_0000_0001).to_bytes(2, "little")
    assert SG.FAULT_TEXT["hall_sensor"] == "Motor position sensor fault"
    assert firmware_matches(SG.LAYOUT)[0]


def test_layout_round_trip_through_the_sim_names():
    mc = {**SG.MC_DEFAULTS, "mc.speed": 23.4, "mc.direction": "reverse", "mc.mode": "sport",
          "mc.brake": True, "mc.batt_v": 75.1, "mc.batt_a": -12.3, "mc.faults": ["throttle"]}
    state = {}
    for msg, raw in SG.encode(mc):
        SG.merge(state, msg, msg.decode(msg.encode(raw)))
    assert state["mc.speed"] == pytest.approx(23.4)
    assert state["mc.direction"] == "reverse" and state["mc.mode"] == "sport" and state["mc.brake"] is True
    assert state["mc.faults"] == ["throttle"]
    assert state["mc.power_kw"] == pytest.approx(75.1 * -12.3 / 1000, abs=0.01)


def test_speed_from_rpm_when_there_is_no_speed_signal():
    m = Message("R", 0x200, "shinegle", 20, signals=(Signal("rpm", 0, 16),))
    lay = Layout([m], "teryx.kmh_per_rpm=0.01")
    assert lay.speed_message is m
    assert lay.decode(m, {"rpm": 3000})["mc.speed"] == pytest.approx(30.0)


# ----------------------------------------------------------------------------- logs

def test_candump_and_savvycan_logs(tmp_path):
    f = S.Frame(1.5, 0x0CF11E05, bytes([1, 2, 3]), True)
    line = S.format_candump(f)
    assert line == "(1.500000) can0 0CF11E05#010203\n"
    assert S.parse_candump_line(line) == f
    assert S.parse_candump_line("(2.0) can0 180#R") == S.Frame(2.0, 0x180, b"", False)
    csv = tmp_path / "savvy.csv"
    csv.write_text("Time Stamp,ID,Extended,Dir,Bus,LEN,D1,D2,D3,D4,D5,D6,D7,D8\n"
                   "1500000,00000180,false,Rx,0,2,0A,0B\n")
    assert S.read_log(csv) == [S.Frame(1.5, 0x180, b"\x0a\x0b", False)]


# ----------------------------------------------------------------------------- analysis

@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    return make_demo(tmp_path_factory.mktemp("demo") / "practice", seed=4)


@pytest.fixture(scope="module")
def result(demo):
    return analyse(demo)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_analysis_finds_each_hidden_signal(result, name):
    can_id, start, length, big_endian, scale, offset = EXPECTED[name]
    g = result.chosen.get(name)
    assert g is not None, f"{name} not found"
    sig = g.signal()
    assert (g.cand.can_id, sig.start, sig.length, sig.big_endian) == (can_id, start, length, big_endian)
    assert sig.scale == pytest.approx(scale, rel=0.01)
    assert sig.offset == pytest.approx(offset, abs=0.5)


def test_analysis_value_tables_and_bus_facts(result):
    assert result.chosen["direction"].choices == {1: "forward", 2: "reverse", 3: "neutral"}
    assert result.chosen["mode"].choices == {1: "eco", 2: "normal", 3: "sport"}
    assert result.dash_ids == [0x601] and not result.request_response
    assert result.ids[0x0CF11F05].counters == [7]
    assert result.ids[0x7A0].constant == list(range(8))


def test_draft_dbc_loads_and_decodes_the_capture(demo, result, tmp_path):
    files = write_outputs(result, tmp_path)
    lay = Layout.from_file(files["dbc"])
    assert not lay.placeholder
    assert 0x601 not in lay.by_id               # dash frames stay out of the controller's layout
    assert lay.speed_message.can_id == 0x351
    assert lay.direction == {1: "forward", 2: "reverse", 3: "neutral"}
    text = check(files["dbc"], demo)
    assert "**NO**" not in text
    n = sum(1 for _, _ in S.load(demo).readings)
    assert f"{n} of {n} readings match" in text
    assert "| not found |" not in files["report"].read_text()


def test_install_flags_the_pico_speed_frame(result, tmp_path):
    draft = tmp_path / "draft.dbc"
    draft.write_text(draft_dbc(result))
    out = install(draft, target=tmp_path / "installed.dbc")
    assert (tmp_path / "installed.dbc").read_text() == draft.read_text()
    assert any(line.startswith("TODO:") and "CAN_ID_MC_SPEED" in line for line in out)
    out = install(SG.DBC_PATH, target=tmp_path / "placeholder.dbc")
    assert any(line.startswith("OK:") for line in out)


def test_request_response_controller_is_spotted(tmp_path):
    # Every id stops while the dash is unplugged: the controller only answers the dash
    folder = tmp_path / "quiet"
    folder.mkdir()
    t0 = 1000.0
    with open(folder / "bus.log", "w") as log:
        for i in range(3000):
            t = t0 + i * 0.01
            if not (10 <= t - t0 < 20):
                log.write(S.format_candump(S.Frame(t, 0x100, b"\x01\x02")))
                log.write(S.format_candump(S.Frame(t, 0x101, b"\x03")))
    rec = S.StepRecord("dash_unplugged", "Dash unplugged", t0, t0 + 30,
                       phases=[S.Phase(t0 + 10, "unplugged"), S.Phase(t0 + 20, "plugged back in")])
    S.save_steps(folder, [rec], {})
    res = analyse(folder)
    assert res.request_response and res.dash_ids == [0x100, 0x101]
    write_outputs(res)
    assert "only talks when the dash asks" in (folder / "report.md").read_text()


def test_bare_log_without_marks_still_reports(tmp_path):
    log = tmp_path / "plain.log"
    log.write_text("".join(S.format_candump(S.Frame(i * 0.02, 0x180, bytes([i & 0xFF, 5]))) for i in range(500)))
    res = analyse(log)
    assert res.ids[0x180].counters == [0] and res.ids[0x180].constant == [1]
    write_outputs(res)
    assert (tmp_path / "report.md").exists()


def test_procedure_is_consistent():
    assert len({s.id for s in STEPS}) == len(STEPS)
    for st in STEPS:
        for name, kind in st.hints.items():
            assert kind in ("sweep", "phases", "steady", "gone")
            if kind == "phases":
                assert st.phases, st.id
    assert "throttle" in BY_ID["throttle_hold"].hints


# ----------------------------------------------------------------------------- capture

def test_guided_capture_records_marks_readings_and_frames(tmp_path):
    bus_tx = can.Bus(interface="virtual", channel="cap-test")
    bus_rx = can.Bus(interface="virtual", channel="cap-test")
    stop = threading.Event()

    def shinegle():
        while not stop.is_set():
            bus_tx.send(can.Message(arbitration_id=0x180, data=b"\x01\x02", is_extended_id=False))
            time.sleep(0.005)
    threading.Thread(target=shinegle, daemon=True).start()

    answers = iter([
        "",                 # brake: start
        "", "", "", "",     # pressed, released, pressed, released
        "n felt spongy",
        "", "",             # pressed, released
        "",                 # finish step
        "",                 # throttle hold: start
        "", "", "", "",     # phase 0, 25 ... readings follow
    ])
    replies = {"25": ["13", "1100", "", "74.1"]}

    def fake_input(prompt):
        time.sleep(0.02)
        if "speed in km/h" in prompt and replies["25"]:
            return replies["25"].pop(0)
        if "motor rpm" in prompt or "battery amps" in prompt or "battery volts" in prompt:
            return replies["25"].pop(0) if replies["25"] else ""
        try:
            return next(answers)
        except StopIteration:
            return "q"

    rec = Recorder(bus_rx, tmp_path / "bus.log").start()
    cap = Capture(tmp_path, rec, {"bus": "virtual"}, input_fn=fake_input, print_fn=lambda *a: None)
    cap.run([BY_ID["brake"], BY_ID["throttle_hold"]])
    rec.stop()
    stop.set()
    bus_tx.shutdown()
    bus_rx.shutdown()

    sess = S.load(tmp_path)
    assert len(sess.frames) > 10
    brake = sess.step("brake")
    assert [p.label for p in brake.phases] == list(BY_ID["brake"].phases)
    assert brake.notes == ["felt spongy"] and brake.end > brake.start
    hold = next(s for s in sess.steps if s.id == "throttle_hold")
    got = {r.name: r.value for r in hold.readings}
    assert got == {"speed": 13.0, "rpm": 1100.0, "batt_v": 74.1}
    assert hold.end is not None
