"""Stock lamps, floods, beacon, trailer bar and the parked-only light show (teryx/lights.py)."""

from teryx.canbus import messages as M
from teryx.lights import LAMPS, LIGHT_SHOW, Lights, LightsReq, LightsState, show_level


def parked(**kw):
    base = dict(stopped=True, park=True, ignition=True, dash_ok=True, trailer=True)
    base.update(kw)
    return LightsState(**base)


def driving(**kw):
    base = dict(stopped=False, park=False, ignition=True, dash_ok=True)
    base.update(kw)
    return LightsState(**base)


def run(req, st, ms=0):
    st.now_ms = ms
    return Lights().step(req, st).level


def test_brake_is_full_whatever_else_happens():
    for st in (driving(brake=True), parked(brake=True), parked(brake=True, locked=True)):
        for show in (0, 1, 2, 3, 4):
            L = Lights()
            for ms in range(0, 8000, 37):
                st.now_ms = ms
                lv = L.step(LightsReq(show=show, tail=10), st).level
                assert lv["brake_l"] == lv["brake_r"] == lv["trailer_stop"] == 255


def test_brake_off_when_not_pressed_and_no_show():
    lv = run(LightsReq(head_low=255, tail=255), driving())
    assert lv["brake_l"] == lv["brake_r"] == lv["trailer_stop"] == 0


def test_low_and_high_never_together():
    for show in range(5):
        L = Lights()
        for ms in range(0, 8000, 23):
            st = parked(now_ms=ms)
            lv = L.step(LightsReq(head_low=200, head_high=200, show=show), st).level
            assert not (lv["head_l_low"] and lv["head_l_high"])
            assert not (lv["head_r_low"] and lv["head_r_high"])


def test_high_wins_over_low():
    lv = run(LightsReq(head_low=100, head_high=100), parked())
    assert lv["head_l_high"] == lv["head_r_high"] == 100 and lv["head_l_low"] == 0


def test_headlights_and_tails_dim_only_when_parked():
    lv = run(LightsReq(head_low=60, tail=40), parked())
    assert lv["head_l_low"] == 60 and lv["tail_l"] == 40
    lv = run(LightsReq(head_low=60, tail=40), driving())
    assert lv["head_l_low"] == lv["head_r_low"] == 255 and lv["tail_l"] == lv["tail_r"] == 255
    lv = run(LightsReq(head_low=60), parked(stopped=False))   # speed unknown counts as moving
    assert lv["head_l_low"] == 255


def test_tails_follow_headlights_and_bars():
    assert run(LightsReq(head_low=255), driving())["tail_l"] == 255
    assert run(LightsReq(), driving(front_on=True))["tail_r"] == 255
    assert run(LightsReq(), driving())["tail_l"] == 0


def test_beacon_flashes_at_3_hz():
    L, st, on = Lights(), parked(), []
    for ms in range(0, 3000, 5):
        st.now_ms = ms
        on.append(L.step(LightsReq(beacon=180), st).level["beacon"])
    rises = sum(1 for a, b in zip(on, on[1:]) if a == 0 and b)
    assert 8 <= rises <= 10                    # 3 Hz over 3 s
    assert max(on) == 180


def test_floods():
    assert run(LightsReq(rear_on=True, rear=80), parked())["flood_l"] == 80
    assert run(LightsReq(rear_on=True), parked())["flood_r"] == 255
    lv = run(LightsReq(rear_on=False, rear_auto=True, rear=80), driving(reverse=True))
    assert lv["flood_l"] == lv["flood_r"] == 255
    assert run(LightsReq(rear_on=False, rear_auto=False), driving(reverse=True))["flood_l"] == 0


def test_trailer_bar_only_with_the_trailer_plugged_in():
    assert run(LightsReq(trailer_bar=90), parked(trailer=True))["trailer_bar"] == 90
    assert run(LightsReq(trailer_bar=90), parked(trailer=False))["trailer_bar"] == 0


def test_locked_turns_everything_off_but_the_brakes():
    lv = run(LightsReq(head_low=255, tail=255, beacon=255, trailer_bar=255, rear_on=True), parked(locked=True))
    assert all(v == 0 for v in lv.values())


def test_show_only_when_parked():
    for st in (driving(), parked(park=False), parked(stopped=False), parked(ignition=False),
               parked(locked=True), parked(dash_ok=False)):
        out = Lights().step(LightsReq(show=1), st)
        assert not out.show_running and out.show_blocked and out.front is None
    out = Lights().step(LightsReq(show=1), parked())
    assert out.show_running and not out.show_blocked and out.front is not None


def test_show_stops_the_moment_it_moves():
    L = Lights()
    st = parked(now_ms=0)
    assert L.step(LightsReq(show=4), st).show_running
    st = driving(now_ms=100)
    out = L.step(LightsReq(show=4, head_low=255), st)
    assert not out.show_running and out.front is None
    assert out.level["head_l_low"] == 255 and out.level["beacon"] == 0


def test_every_show_uses_every_lamp_and_stays_in_range():
    for show in LIGHT_SHOW:
        if not show:
            continue
        seen = set()
        for t in range(0, 8000, 10):
            for k in LAMPS + ("front_1", "front_2", "front_3", "front_4", "interior"):
                v = show_level(show, k, t)
                assert 0 <= v <= 255
                if v:
                    seen.add(k)
        assert {"head_l_low", "tail_l", "tail_r", "flood_l", "flood_r", "front_1", "front_4"} <= seen, show


def test_can_frames_round_trip():
    v = {"head_low": 10, "head_high": 0, "tail": 0, "rear": 200, "trailer_bar": 30,
         "beacon": 255, "show": 3, "counter": 7}
    assert M.PI_LIGHTS2.decode(M.PI_LIGHTS2.encode(v)) == v
    lv = {k: i for i, k in enumerate(LAMPS)}
    d = M.PICO_LIGHTS2.decode(M.PICO_LIGHTS2.encode({**lv, "show_running": 1, "show_blocked": 0, "pwm_ok": 1}))
    assert all(d[k] == lv[k] for k in LAMPS) and d["show_running"] == 1


def test_sim_control_box_runs_a_show_and_reports_it():
    from teryx.sim.controlbox import ControlBox
    cb = ControlBox()
    cb.on_frame("PI_HEARTBEAT", {"counter": 0, "dash_state": 1}, 0.0)
    cb.on_frame("PI_LIGHTS2", {"head_low": 0, "head_high": 0, "tail": 0, "rear": 0,
                                "trailer_bar": 0, "beacon": 0, "show": 2, "counter": 0}, 0.0)
    cb.step(0.01, 0.01)
    frames = dict(cb.frames())
    assert frames["PICO_LIGHTS2"]["show_blocked"] == 1     # no speed signal, park brake off


def test_no_dash_with_the_key_on_puts_low_beams_and_tails_on():
    lv = run(LightsReq(), driving(dash_ok=False))
    assert lv["head_l_low"] == lv["head_r_low"] == lv["tail_l"] == lv["tail_r"] == 255
    lv = run(LightsReq(head_high=255), driving(dash_ok=False))
    assert lv["head_l_high"] == 255 and lv["head_l_low"] == 0
    assert run(LightsReq(), driving(dash_ok=False, ignition=False))["head_l_low"] == 0
