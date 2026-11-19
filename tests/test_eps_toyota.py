"""Toyota EPS spoof frames (docs/power-steering-wrecker.md)."""

from teryx.eps_toyota import (MAX_ASSIST_KMH, RPM_ID, SPEED_ID, assist_speed_kmh, frames,
                              rpm_frame, speed_frame, toyota_checksum)


def test_frames_match_the_working_retrofit():
    # Exact bytes from the Carloop thread that woke a 2008 Prius EPS.
    assert rpm_frame(1674).hex(" ").upper() == "06 8A 00 19 00 00 92 09"
    assert speed_frame(16.38).hex(" ").upper() == "00 00 00 00 8D 06 66 B5"


def test_checksum_is_last_byte():
    for can_id, data in ((RPM_ID, rpm_frame(900)), (SPEED_ID, speed_frame(37.5))):
        assert data[-1] == toyota_checksum(can_id, data)


def test_low_speed_gets_full_assist():
    assert assist_speed_kmh(0) == MAX_ASSIST_KMH
    assert assist_speed_kmh(None) == MAX_ASSIST_KMH
    assert assist_speed_kmh(40) == 40


def test_silent_when_not_ready():
    assert frames(10, engine_ready=False) == []
    ids = [i for i, _ in frames(10, engine_ready=True)]
    assert ids == [RPM_ID, SPEED_ID]


# ---------------------------------------------------------------- Aqua build (docs/power-steering-aqua.md)
import re
from pathlib import Path

from teryx import eps_toyota as E
from teryx.canbus import messages as M

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "firmware" / "control-box" / "src" / "core"


def test_reads_the_ecu_like_opendbc():
    # Built with cantools from opendbc's _toyota_2017.dbc STEER_TORQUE_SENSOR, our checksum.
    d = bytes.fromhex("09ff8800af012cd6")
    assert E.decode_ecu_frame(E.TORQUE_ID, d) == {
        "override": True, "angle_init": True, "torque_driver": -120, "angle_deg": 10.03, "torque_eps": 300}
    # opendbc toyota_nodsu_pt.dbc EPS_STATUS with LKA_STATE 17 (permanent fault)
    assert E.decode_ecu_frame(E.STATUS_ID, bytes.fromhex("0300002200000091"))["lka_state"] == 17
    assert E.decode_ecu_frame(E.TORQUE_ID, bytes.fromhex("09ff8800af012c00")) is None   # bad checksum


def test_assist_curve():
    c = E.AssistCurve()
    assert c.told_kmh(None) == 16.3 and c.told_kmh(5) == 16.3 and c.told_kmh(30) == 30
    c = E.AssistCurve.from_settings({"eps_floor_kmh_x10": 100, "eps_speed_gain_pct": 200, "eps_max_kmh": 50})
    assert c.told_kmh(3) == 10 and c.told_kmh(20) == 40 and c.told_kmh(40) == 50
    sent = dict(E.frames(30, True, E.AssistCurve(gain_pct=150)))
    assert int.from_bytes(sent[E.SPEED_ID][5:7], "big") == 4500


def _c_defines(path: Path) -> dict[str, int]:
    out = {}
    for name, val in re.findall(r"#define\s+(\w+)\s+(0x[0-9A-Fa-f]+|\d+)u?\b", path.read_text()):
        out[name] = int(val, 0)
    return out


def test_python_matches_the_firmware():
    h = _c_defines(CORE / "eps.h")
    assert h["EPS_BITRATE"] == E.EPS_BITRATE
    assert h["EPS_PERIOD_MS"] == round(E.SEND_PERIOD_S * 1000)
    assert h["EPS_RPM_ID"] == E.RPM_ID and h["EPS_SPEED_ID"] == E.SPEED_ID
    assert h["EPS_SPEED_ENCODER"] == E.SPEED_ENCODER
    assert h["EPS_TORQUE_ID"] == E.TORQUE_ID and h["EPS_STATUS_ID"] == E.STATUS_ID
    assert h["EPS_DIAG_REPLY_ID"] == E.DIAG_REPLY_ID
    assert h["EPS_STATUS_PERMANENT_FAULT"] == E.STATUS_PERMANENT_FAULT
    assert _c_defines(CORE / "protocol.h")["CAN_ID_PICO_STEER"] == M.PICO_STEER.can_id


def test_steering_settings_match_the_firmware():
    proto = (CORE / "protocol.h").read_text()
    keys = {n: int(v) for n, v in re.findall(r"SET_(EPS_\w+)\s*=\s*(\d+)", proto)}
    ranges = {n: tuple(map(int, r)) for n, *r in
              re.findall(r"\[SET_(EPS_\w+)\]\s*=\s*\{(\d+),\s*(\d+),\s*(\d+)\}", (CORE / "settings.c").read_text())}
    assert len(keys) == 8 and keys.keys() == ranges.keys()
    for cname, key in keys.items():
        name, _unit, default, lo, hi = M.SETTINGS[key]
        assert name.startswith("eps_"), (cname, name)
        assert ranges[cname] == (default, lo, hi), cname
    assert M.SETTINGS[keys["EPS_RPM"]][2] == E.RPM_RUNNING
    assert M.SETTINGS[keys["EPS_FLOOR_KMH_X10"]][2] == round(E.MAX_ASSIST_KMH * 10)


def test_steer_state_names_match_the_firmware():
    h = (CORE / "eps.h").read_text()
    states = {int(v): n.lower() for n, v in re.findall(r"STEER_(\w+)\s*=\s*(\d+),", h)}
    assert states == M.STEER_STATE
