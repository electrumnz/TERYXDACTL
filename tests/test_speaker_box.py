"""Speaker pod maths (teryx/speaker_box.py) and config/speaker_pods.yaml."""

import math

import pytest

from teryx import speaker_box as S


@pytest.fixture(scope="module")
def cfg():
    return S.load()


def test_pod_config_is_sound(cfg):
    assert S.check(cfg) == []


def test_closed_box_textbook_numbers():
    # Vb = Vas gives alpha 1: fc and Qtc both go up by sqrt(2)
    fc, qtc = S.Driver(50, 0.5, 20).closed(20)
    assert fc == pytest.approx(50 * math.sqrt(2))
    assert qtc == pytest.approx(0.5 * math.sqrt(2))
    # and back again
    assert S.Driver(50, 0.5, 20).vb_for_qtc(0.5 * math.sqrt(2)) == pytest.approx(20)
    assert S.Driver(50, 0.9, 20).vb_for_qtc(0.707) is None


def test_ts_from_a_simulated_sweep():
    # Make the impedance curve of a known driver and get its numbers back.
    re_, fs, qms, qes = 3.2, 55.0, 4.0, 0.95
    r0 = 1 + qms / qes

    def z(f):
        x = qms * (f / fs - fs / f)
        return re_ * abs(1 + (r0 - 1) / complex(1, x))
    pts = [(f, z(f)) for f in [30 + i for i in range(0, 80)]]
    got = S.ts_from_impedance(re_, pts)
    assert got["fs"] == pytest.approx(fs, rel=0.02)
    assert got["qms"] == pytest.approx(qms, rel=0.05)
    assert got["qes"] == pytest.approx(qes, rel=0.05)
    # added mass: 20 g more on the cone drops Fs by sqrt(mms / (mms + 20 g))
    mms = 0.030
    fs2 = fs * math.sqrt(mms / (mms + 0.020))
    got = S.ts_from_impedance(re_, pts, added_g=20, fs_added=fs2, cone_d_mm=165)
    assert got["mms_g"] == pytest.approx(30, rel=0.05)
    assert got["vas_l"] > 0


def test_eq_flattens_the_bass_hump(cfg):
    d = cfg["driver"]
    p = S.plan_eq(cfg, S.Driver(d["fs"], d["qts"], d["vas_l"]))
    assert p["qtc"] > 1.2                       # the pod alone is peaky (free-air speaker)
    assert p["max_boost_db"] <= cfg["eq"]["max_boost_db"] + 0.01
    # pod + EQ follows the target 2nd order shape
    for f in (60, 90, 150, 400):
        got = 20 * math.log10(abs(S.hp2(f, p["fc"], p["qtc"]))) + S.lt_db(f, p["fc"], p["qtc"], p["fp"], p["qp"])
        assert got == pytest.approx(20 * math.log10(abs(S.hp2(f, p["fp"], p["qp"]))), abs=0.01)


def test_pipewire_biquad_matches_the_maths(cfg):
    d = cfg["driver"]
    p = S.plan_eq(cfg, S.Driver(d["fs"], d["qts"], d["vas_l"]))
    for rate in (44100, 48000):
        c = S.biquad(rate, p["fc"], p["qtc"], p["fp"], p["qp"])
        for f in (40, 90, 127, 300, 2000):
            assert S.biquad_db(c, f, rate) == pytest.approx(S.lt_db(f, p["fc"], p["qtc"], p["fp"], p["qp"]), abs=0.05)
