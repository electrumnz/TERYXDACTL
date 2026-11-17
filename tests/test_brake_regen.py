"""Brake pedal regen rules (teryx/regen.py, docs/brake-regen.md)."""

import pytest

from teryx.canbus import messages as M
from teryx.regen import BrakeRegen
from teryx.sim.vehicle import PEDAL_RAW_DOWN, PEDAL_RAW_UP, Vehicle

from test_controlbox import Bench


def settings(**over):
    s = M.default_settings()
    s["brake_regen_on"] = 1
    s.update(over)
    return s


def raw(pedal_pct):
    return round(PEDAL_RAW_UP + pedal_pct / 100 * (PEDAL_RAW_DOWN - PEDAL_RAW_UP))


def run(r, s, seconds=1.0, dt=0.02, **kw):
    args = dict(pedal_raw=raw(30), brake_switch=True, speed_kmh=30.0, direction="forward",
                soc=60.0, fourwd="4wd")
    args.update(kw)
    out = None
    for _ in range(int(seconds / dt)):
        out = r.step(dt, s, **args)
    return out


def test_off_by_default():
    assert M.default_settings()["brake_regen_on"] == 0
    out = run(BrakeRegen(), M.default_settings())
    assert out.state == "off" and out.request_pct == 0


def test_pedal_curve_and_strength():
    s = settings(brake_regen_pct=100, brake_regen_start_pct=5, brake_regen_full_pct=30)
    assert run(BrakeRegen(), s, pedal_raw=raw(3)).request_pct == 0          # dead zone, resting foot
    assert run(BrakeRegen(), s, pedal_raw=raw(17.5)).request_pct == pytest.approx(50, abs=1)
    assert run(BrakeRegen(), s, pedal_raw=raw(60)).request_pct == pytest.approx(100, abs=1)
    s["brake_regen_pct"] = 40
    assert run(BrakeRegen(), s, pedal_raw=raw(60)).request_pct == pytest.approx(40, abs=1)


def test_fades_at_low_speed_and_none_when_stopped():
    s = settings(brake_regen_pct=100, brake_regen_fade_kmh=10)
    out = run(BrakeRegen(), s, speed_kmh=5.0)
    assert out.request_pct == pytest.approx(50, abs=1) and out.limit == "low_speed"
    assert run(BrakeRegen(), s, speed_kmh=0.0).request_pct == 0


def test_nothing_without_speed_or_out_of_forward():
    s = settings()
    assert run(BrakeRegen(), s, speed_kmh=None).limit == "speed_unknown"
    assert run(BrakeRegen(), s, speed_kmh=None).request_pct == 0
    for d in ("reverse", "neutral"):
        out = run(BrakeRegen(), s, direction=d)
        assert out.request_pct == 0 and out.limit == "not_forward"


def test_none_with_throttle_on():
    out = run(BrakeRegen(), settings(), throttle_pct=30.0)
    assert out.request_pct == 0 and out.limit == "throttle"


def test_backs_off_when_battery_is_full():
    s = settings(brake_regen_pct=100)
    assert run(BrakeRegen(), s, soc=94.0).request_pct == pytest.approx(50, abs=1)
    out = run(BrakeRegen(), s, soc=99.0)
    assert out.request_pct == 0 and out.limit == "battery_full"


def test_less_regen_in_2wd():
    s = settings(brake_regen_pct=100, brake_regen_2wd_pct=60)
    assert run(BrakeRegen(), s, fourwd="2wd").request_pct == pytest.approx(60, abs=1)
    assert run(BrakeRegen(), s, fourwd="unknown").request_pct == pytest.approx(60, abs=1)


def test_ramps_up_but_drops_straight_away():
    s = settings(brake_regen_pct=100)
    r = BrakeRegen()
    first = r.step(0.02, s, pedal_raw=raw(60), brake_switch=True, speed_kmh=30, direction="forward",
                   soc=50, fourwd="4wd")
    assert first.request_pct <= 5.01
    run(r, s, pedal_raw=raw(60))
    assert r.out.request_pct == pytest.approx(100)
    off = r.step(0.02, s, pedal_raw=raw(0), brake_switch=False, speed_kmh=30, direction="forward",
                 soc=50, fourwd="4wd")
    assert off.request_pct == 0


@pytest.mark.parametrize("bad", [None, 0, 32767])
def test_broken_sensor_means_no_regen_until_cleared(bad):
    s = settings()
    r = BrakeRegen()
    out = run(r, s, pedal_raw=bad)
    assert out.state == "sensor_fault" and out.request_pct == 0
    # A good reading again doesn't quietly bring it back
    assert run(r, s).state == "sensor_fault"
    r.clear_fault()
    assert run(r, s).request_pct > 0


def test_uncalibrated_sensor_is_a_fault():
    out = run(BrakeRegen(), settings(brake_pedal_min_raw=5000, brake_pedal_max_raw=5100))
    assert out.state == "sensor_fault"


def test_pedal_deep_but_brake_switch_off_is_a_fault():
    s = settings()
    r = BrakeRegen()
    run(r, s, seconds=0.3, pedal_raw=raw(70), brake_switch=False)
    assert not r.fault                      # short blips are fine
    run(r, s, seconds=0.5, pedal_raw=raw(70), brake_switch=False)
    assert r.fault and r.out.request_pct == 0


def test_light_pedal_without_brake_switch_is_normal():
    # The whole point: regen in the first bit of travel, before the switch or the pads
    out = run(BrakeRegen(), settings(), seconds=2, pedal_raw=raw(20), brake_switch=False)
    assert out.request_pct > 0 and out.state == "active"


def test_strong_regen_lights_the_brake_lights():
    s = settings(brake_regen_pct=100)
    assert run(BrakeRegen(), s, pedal_raw=raw(30)).brake_light
    assert not run(BrakeRegen(), s, pedal_raw=raw(6)).brake_light


# ------------------------------------------------------------ control box emulator

def regen_bench(on=True):
    b = Bench()
    b.run(0.2)
    b.drive_req(0, 0)
    b.run(1.5)
    if on:
        b.cb.on_frame("PI_SETTINGS", {"key": M.SETTING_KEYS["brake_regen_on"], "value": 1}, b.t)
    return b


def test_control_box_sends_regen_frame_and_lights_brake_lights():
    b = regen_bench()
    b.speed = 30
    b.cb.pedal_raw = raw(25)
    b.run(1.0)
    frames = dict(b.cb.frames())
    assert frames["PICO_REGEN"]["request_pct"] > 0
    assert M.REGEN_STATE[frames["PICO_REGEN"]["state"]] == "active"
    assert b.cb.relays()["trailer.brake"]
    M.PICO_REGEN.encode(frames["PICO_REGEN"])


def test_control_box_flags_broken_pedal_sensor():
    b = regen_bench()
    b.speed = 30
    b.cb.pedal_raw = 0
    b.run(0.5)
    assert "brake_pedal" in b.cb.faults()
    b.cb.on_frame("PI_SETTINGS", {"key": M.SETTING_CLEAR_FAULTS, "value": 0}, b.t)
    b.cb.pedal_raw = raw(0)
    b.run(0.2)
    assert "brake_pedal" not in b.cb.faults()


def test_control_box_no_regen_when_flag_off():
    b = regen_bench(on=False)
    b.speed = 30
    b.cb.pedal_raw = raw(25)
    b.run(1.0)
    assert b.cb.regen.out.request_pct == 0
    assert "brake_pedal" not in b.cb.faults()


# ------------------------------------------------------------ vehicle model

def stopping_distance(regen):
    v = Vehicle(soc=60)
    v.inp.direction = "forward"
    v.speed_ms = 40 / 3.6
    v.inp.brake = 0.1
    v.regen_request = regen
    d = 0.0
    for _ in range(3000):
        v.step(0.01)
        d += v.speed_ms * 0.01
        if v.speed_ms <= 0:
            break
    return d, v


def test_pedal_regen_shortens_the_stop_and_charges_the_battery():
    plain, _ = stopping_distance(0.0)
    with_regen, _ = stopping_distance(1.0)
    assert with_regen < plain
    v = Vehicle(soc=60)
    v.inp.direction = "forward"
    v.speed_ms = 30 / 3.6
    v.regen_request = 1.0
    v.step(0.05)
    assert v.pack_current < 0          # charging


def test_hydraulic_brakes_unchanged_by_regen_setting():
    # Same pedal, regen off: the hydraulic force is exactly what it was before this feature
    a, b = Vehicle(), Vehicle()
    for v in (a, b):
        v.inp.direction = "forward"
        v.speed_ms = 10
        v.inp.brake = 0.5
    b.regen_request = 0.0
    a.step(0.1)
    b.step(0.1)
    assert a.speed_ms == b.speed_ms
