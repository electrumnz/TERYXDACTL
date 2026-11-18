"""RC mode rules for beach and ramp launching (teryx/rc_mode.py, docs/rc-beach-launch.md)."""

from teryx.rc_mode import (ARMED, DRIVING, FAULT, FORWARD, HOLD, NEUTRAL, OFF, REVERSE,
                           Permit, Radio, RcBox, Vehicle, trq_volts)


def armed_box(now=0.0):
    box = RcBox()
    assert box.arm(now, Radio(t=now), Permit(t=now), Vehicle()) == ""
    assert box.state == ARMED
    return box


def drive(box, now, veh=None, **radio):
    radio.setdefault("deadman", True)
    return box.tick(now, Radio(t=now, **radio), Permit(t=now), veh or Vehicle(parked=False))


def test_off_does_nothing():
    out = RcBox().tick(0, Radio(t=0, deadman=True, throttle=1), Permit(t=0), Vehicle())
    assert out.state == OFF and not out.relays and out.throttle == 0


def test_arming_rules():
    box = RcBox()
    ok = dict(radio=Radio(t=0), permit=Permit(t=0), veh=Vehicle())
    assert box.arm(0, None, ok["permit"], ok["veh"]) == "radio_lost"
    assert box.arm(0, ok["radio"], None, ok["veh"]) == "control_box_lost"
    assert box.arm(0, ok["radio"], Permit(t=0, allowed=False, reason="locked"), ok["veh"]) == "locked"
    assert box.arm(0, ok["radio"], ok["permit"], Vehicle(parked=False)) == "not_parked"
    assert box.arm(0, ok["radio"], ok["permit"], Vehicle(brake_ok=False)) == "no_brake"
    assert box.arm(0, Radio(t=0, deadman=True), ok["permit"], ok["veh"]) == "deadman_held"
    assert box.arm(0, Radio(t=0, throttle=0.5), ok["permit"], ok["veh"]) == "throttle_not_zero"
    assert box.arm(0, Radio(t=0, direction=REVERSE), ok["permit"], ok["veh"]) == "not_neutral"
    assert box.arm(0, **ok) == "" and box.state == ARMED


def test_reverse_with_trigger():
    box = armed_box()
    drive(box, 0.02, direction=REVERSE)          # select reverse while stopped
    out = drive(box, 0.04, direction=REVERSE, throttle=0.6)
    assert out.state == DRIVING and out.direction == REVERSE
    assert out.throttle == 0.6 and out.brake == 0 and out.relays


def test_radio_silence_stops_within_timeout():
    box = armed_box()
    drive(box, 0.02, direction=REVERSE)
    drive(box, 0.04, direction=REVERSE, throttle=0.6)
    stale = Radio(t=0.04, deadman=True, direction=REVERSE, throttle=0.6)
    assert box.tick(0.20, stale, Permit(t=0.20), Vehicle(parked=False)).throttle == 0.6
    out = box.tick(0.25, stale, Permit(t=0.25), Vehicle(parked=False))
    assert out.state == HOLD and out.reason == "radio_lost"
    assert out.throttle == 0 and out.brake == 1 and out.direction == NEUTRAL


def test_receiver_failsafe_flag_stops():
    box = armed_box()
    out = box.tick(0.02, Radio(t=0.02, deadman=True, failsafe=True), Permit(t=0.02), Vehicle())
    assert out.reason == "radio_lost" and out.brake == 1


def test_control_box_permit_lost_or_withdrawn():
    box = armed_box()
    out = box.tick(0.5, Radio(t=0.5, deadman=True), Permit(t=0.0), Vehicle())
    assert out.reason == "control_box_lost"
    out = box.tick(0.6, Radio(t=0.6, deadman=True), Permit(t=0.6, allowed=False, reason="locked"), Vehicle())
    assert out.reason == "locked" and out.throttle == 0


def test_deadman_release_stops_and_needs_trigger_let_go():
    box = armed_box()
    drive(box, 0.02, direction=FORWARD)
    assert drive(box, 0.04, direction=FORWARD, throttle=0.5).throttle == 0.5
    out = drive(box, 0.06, direction=FORWARD, throttle=0.5, deadman=False)
    assert out.reason == "deadman" and out.throttle == 0 and out.brake == 1
    # grab the dead-man again with the trigger still pulled: still stopped
    assert drive(box, 0.08, direction=FORWARD, throttle=0.5).throttle == 0
    drive(box, 0.10, direction=FORWARD, throttle=0.0)
    assert drive(box, 0.12, direction=FORWARD, throttle=0.5).throttle == 0.5


def test_estop():
    box = armed_box()
    out = drive(box, 0.02, estop=True)
    assert out.reason == "estop" and out.brake == 1


def test_direction_only_changes_when_stopped():
    box = armed_box()
    drive(box, 0.02, direction=FORWARD)
    moving = Vehicle(parked=False, motor_kmh=3)
    out = drive(box, 0.04, veh=moving, direction=REVERSE, throttle=0.3)
    assert out.direction == FORWARD and "stop_to_change_direction" in out.warn


def test_speed_caps():
    box = armed_box()
    drive(box, 0.02, direction=REVERSE)
    out = drive(box, 0.04, veh=Vehicle(parked=False, motor_kmh=3.2), direction=REVERSE, throttle=1)
    assert out.throttle == 0 and "speed_cap" in out.warn and out.brake == 0
    out = drive(box, 0.06, veh=Vehicle(parked=False, motor_kmh=5.0), direction=REVERSE, throttle=1)
    assert out.throttle == 0 and out.brake > 0


def test_brake_trigger_beats_go_trigger():
    box = armed_box()
    drive(box, 0.02, direction=FORWARD)
    out = drive(box, 0.04, veh=Vehicle(parked=False, motor_kmh=2), direction=FORWARD, throttle=1, brake=0.4)
    assert out.throttle == 0 and out.brake == 0.4


def test_holds_on_brake_when_stopped_and_off_throttle():
    box = armed_box()
    out = drive(box, 0.02, direction=REVERSE)
    assert out.throttle == 0 and out.brake == 1


def test_water_limit_blocks_reverse_not_forward():
    box = armed_box()
    drive(box, 0.02, direction=REVERSE)
    wet = Vehicle(parked=False, wet=1)
    out = drive(box, 0.04, veh=wet, direction=REVERSE, throttle=0.5)
    assert out.throttle == 0 and "water_limit" in out.warn
    drive(box, 0.06, veh=wet, direction=FORWARD)
    assert drive(box, 0.08, veh=wet, direction=FORWARD, throttle=0.5).throttle == 0.5


def test_wheelspin_on_sand_cuts_drive():
    box = armed_box()
    drive(box, 0.02, direction=FORWARD)
    digging = Vehicle(parked=False, motor_kmh=4, ground_kmh=0.1)
    t, out = 0.02, None
    for _ in range(80):                       # 1.6 s
        t += 0.02
        out = drive(box, t, veh=digging, direction=FORWARD, throttle=0.6)
    assert out.state == HOLD and out.reason == "wheelspin" and out.throttle == 0


def test_no_wheelspin_check_without_gps():
    box = armed_box()
    drive(box, 0.02, direction=FORWARD)
    t = 0.02
    for _ in range(100):
        t += 0.02
        out = drive(box, t, veh=Vehicle(parked=False, motor_kmh=4, ground_kmh=None), direction=FORWARD, throttle=0.6)
    assert out.state == DRIVING


def test_stall_when_stuck():
    box = armed_box()
    drive(box, 0.02, direction=REVERSE)
    t = 0.02
    for _ in range(160):                      # 3.2 s
        t += 0.02
        out = drive(box, t, direction=REVERSE, throttle=0.8)
    assert out.reason == "stalled" and out.throttle == 0


def test_winch_only_when_stopped_in_neutral():
    box = armed_box()
    out = drive(box, 0.02, winch=1)
    assert out.winch == 1 and out.brake == 1 and out.throttle == 0
    drive(box, 0.04, direction=FORWARD)
    out = drive(box, 0.06, veh=Vehicle(parked=False, motor_kmh=2), direction=FORWARD, throttle=0.3, winch=1)
    assert out.winch == 0 and "winch_needs_stop" in out.warn


def test_winch_stops_on_link_loss():
    box = armed_box()
    drive(box, 0.02, winch=-1)
    out = box.tick(0.5, Radio(t=0.02, deadman=True, winch=-1), Permit(t=0.5), Vehicle())
    assert out.winch == 0


def test_steering_follows_stick_rate_limited():
    box = armed_box()
    out = drive(box, 0.02, steer=1.0)
    assert 0 < out.steer_target_deg <= 180 * 0.02 + 1e-9
    t1, t2 = out.trq_v
    assert t1 > 2.5 > t2 and abs((t1 - 2.5) + (t2 - 2.5)) < 1e-9


def test_steer_readback_fault_hands_steering_back():
    box = armed_box()
    out = box.tick(0.02, Radio(t=0.02, deadman=True), Permit(t=0.02),
                   Vehicle(trq_readback=(3.0, 3.0)))
    assert box.state == FAULT and out.reason == "steer_readback" and not out.relays
    out = drive(box, 0.04)
    assert out.state == FAULT and out.throttle == 0


def test_trq_volts_mirror_and_clamp():
    assert trq_volts(0) == (2.5, 2.5)
    assert trq_volts(2) == (3.5, 1.5)
    assert trq_volts(-0.5, span=0.8) == (2.1, 2.9)


# ---- stick mode: one stick for forward, brake and reverse ----

def test_stick_forward_brake_then_reverse_needs_centre():
    box = armed_box()
    out = drive(box, 0.02, drive=0.5)
    assert out.direction == FORWARD and out.throttle == 0.5
    moving = Vehicle(parked=False, motor_kmh=3)
    out = drive(box, 0.04, veh=moving, drive=-0.7)
    assert out.direction == FORWARD and out.throttle == 0 and out.brake == 0.7
    # stopped, stick still held back: keeps braking, does NOT roll into reverse
    out = drive(box, 0.06, drive=-0.7)
    assert out.throttle == 0 and out.brake >= 0.7 and out.direction == FORWARD
    drive(box, 0.08, drive=0.0)
    out = drive(box, 0.10, drive=-0.4)
    assert out.direction == REVERSE and out.throttle == 0.4


def test_stick_must_be_centred_to_arm():
    box = RcBox()
    assert box.arm(0, Radio(t=0, drive=0.3), Permit(t=0), Vehicle()) == "throttle_not_zero"


def test_stick_mode_still_capped_and_watched():
    box = armed_box()
    drive(box, 0.02, drive=-0.2)
    out = drive(box, 0.04, veh=Vehicle(parked=False, motor_kmh=3.5), drive=-1)
    assert out.direction == REVERSE and out.throttle == 0 and "speed_cap" in out.warn
    out = box.tick(0.5, Radio(t=0.04, deadman=True, drive=-1), Permit(t=0.5), Vehicle(parked=False))
    assert out.reason == "radio_lost" and out.throttle == 0


# ---- driving from a phone over 4G: off by default, crawl only, lag-aware ----

def test_4g_refused_unless_turned_on():
    box = RcBox()
    r = Radio(t=0, link="4g", rtt_s=0.1)
    assert box.arm(0, r, Permit(t=0), Vehicle()) == "4g_off"
    box = RcBox({"allow_4g": True})
    assert box.arm(0, r, Permit(t=0), Vehicle()) == ""


def test_4g_crawl_cap_and_lag_stop():
    box = RcBox({"allow_4g": True})
    assert box.arm(0, Radio(t=0, link="4g", rtt_s=0.1), Permit(t=0), Vehicle()) == ""
    g = dict(link="4g", rtt_s=0.12)
    drive(box, 0.02, drive=0.5, **g)
    out = drive(box, 0.04, veh=Vehicle(parked=False, motor_kmh=2.2), drive=1, **g)
    assert out.throttle == 0 and "speed_cap" in out.warn
    out = drive(box, 0.06, veh=Vehicle(parked=False, motor_kmh=1), drive=1, link="4g", rtt_s=0.45)
    assert out.reason == "lag" and out.throttle == 0 and out.brake == 1


def test_4g_needs_live_video_and_tolerates_some_jitter():
    box = RcBox({"allow_4g": True})
    box.arm(0, Radio(t=0, link="4g", rtt_s=0.1), Permit(t=0), Vehicle())
    out = box.tick(0.4, Radio(t=0.0, link="4g", rtt_s=0.1, deadman=True), Permit(t=0.4), Vehicle())
    assert out.state == DRIVING          # 400 ms old is OK on 4G...
    out = box.tick(0.6, Radio(t=0.0, link="4g", rtt_s=0.1, deadman=True), Permit(t=0.6), Vehicle())
    assert out.reason == "radio_lost"   # ...600 ms isn't
    out = drive(box, 0.7, link="4g", rtt_s=0.1, video_ok=False)
    assert out.reason == "no_video"


def test_turning_4g_off_stops_a_4g_session():
    box = RcBox({"allow_4g": True})
    box.arm(0, Radio(t=0, link="4g", rtt_s=0.1), Permit(t=0), Vehicle())
    box.s["allow_4g"] = False
    assert drive(box, 0.02, link="4g", rtt_s=0.1).reason == "4g_off"
