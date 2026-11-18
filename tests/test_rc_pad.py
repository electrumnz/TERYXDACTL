"""Bluetooth pad paired to the Pi (teryx/rc_pad.py) driving through the RC box rules."""

from teryx.rc_mode import ARMED, DRIVING, HOLD, REVERSE, Permit, RcBox, Vehicle
from teryx.rc_pad import (ABS_HAT0X, ABS_HAT0Y, ABS_RX, ABS_RZ, ABS_Y, ABS_Z, BTN_EAST, BTN_SELECT,
                          BTN_SOUTH, BTN_START, BTN_TL, EV_ABS, EV_KEY, PadMapper)


def press(m, t, code, down=True):
    m.event(t, EV_KEY, code, 1 if down else 0)


def stick(m, t, code, v):
    m.event(t, EV_ABS, code, v)


def arm(m, t=0.0):
    press(m, t, BTN_START)
    m.packet(t + 1.1)
    press(m, t + 1.1, BTN_START, False)
    return m.commands()


def test_centred_pad_is_neutral_and_safe():
    p = PadMapper().packet(0)
    assert p.link == "bt" and p.drive == 0 and p.steer == 0 and not p.deadman and not p.failsafe


def test_start_held_one_second_arms_and_again_disarms():
    m = PadMapper()
    press(m, 0, BTN_START)
    m.packet(0.5)
    assert m.commands() == [] and not m.armed      # a tap isn't enough
    m.packet(1.05)
    assert m.commands() == [("rc", "arm")] and m.armed
    m.packet(2.0)
    assert m.commands() == []                      # one press, one change
    press(m, 2.1, BTN_START, False)
    assert arm(m, 3.0) == [("rc", "disarm")] and not m.armed


def test_cant_arm_holding_the_deadman_or_a_stick():
    m = PadMapper()
    press(m, 0, BTN_TL)
    assert arm(m) == [("rc", "not_centred")] and not m.armed
    press(m, 2, BTN_TL, False)
    stick(m, 2, ABS_Y, -20000)
    assert arm(m, 3) == [("rc", "not_centred")]


def test_sticks_and_triggers():
    m = PadMapper()
    stick(m, 0, ABS_Y, -32768)                     # stick up = forward
    stick(m, 0, ABS_RX, 32767)
    p = m.packet(0)
    assert p.drive > 0.99 and p.steer > 0.99
    stick(m, 0, ABS_Y, 0)
    stick(m, 0, ABS_Z, 1023)                       # LT = brake / back
    assert m.packet(0).drive < -0.99
    stick(m, 0, ABS_Z, 0)
    stick(m, 0, ABS_RZ, 512)                       # RT half = go half
    assert 0.4 < m.packet(0).drive < 0.6


def test_buttons_winch_estop_and_dash_commands():
    m = PadMapper()
    press(m, 0, BTN_TL)
    press(m, 0, BTN_SOUTH)
    p = m.packet(0)
    assert p.deadman and p.winch == 1
    press(m, 0, BTN_SOUTH, False)
    press(m, 0, BTN_EAST)
    assert m.packet(0).winch == -1
    for code, v in ((ABS_HAT0Y, -1), (ABS_HAT0Y, 0), (ABS_HAT0Y, 1), (ABS_HAT0X, 1), (ABS_HAT0X, -1)):
        stick(m, 0, code, v)
    assert m.commands() == [("lights", "toggle"), ("fourwd", "toggle"), ("diff", 25), ("diff", -25)]
    press(m, 1, BTN_SELECT)
    press(m, 1, BTN_SELECT, False)
    assert m.packet(1).estop                       # e-stop latches


def test_drives_through_the_rc_box_and_stops_when_bluetooth_drops():
    box, m = RcBox(), PadMapper()
    veh = Vehicle()
    assert box.arm(0, m.packet(0), Permit(t=0), veh) == ""
    assert box.state == ARMED
    press(m, 0.02, BTN_TL)
    stick(m, 0.02, ABS_Y, 32767)                   # pull back = reverse from a stop
    t, out = 0.02, None
    for _ in range(10):
        t += 0.02
        out = box.tick(t, m.packet(t), Permit(t=t), Vehicle(parked=False))
    assert out.state == DRIVING and out.direction == REVERSE and out.throttle > 0.9
    m.lost()                                       # pad gone: failsafe straight away
    t += 0.02
    out = box.tick(t, m.packet(t), Permit(t=t), Vehicle(parked=False))
    assert out.state == HOLD and out.throttle == 0 and out.brake == 1 and out.reason == "radio_lost"


def test_packets_stop_means_stop():
    box, m = RcBox(), PadMapper()
    box.arm(0, m.packet(0), Permit(t=0), Vehicle())
    press(m, 0, BTN_TL)
    stick(m, 0, ABS_Y, -32768)
    last = m.packet(0.02)
    box.tick(0.02, last, Permit(t=0.02), Vehicle(parked=False))
    out = box.tick(0.3, last, Permit(t=0.3), Vehicle(parked=False))   # nothing new for 280 ms
    assert out.state == HOLD and out.reason == "radio_lost"


def test_letting_go_of_lb_stops():
    box, m = RcBox(), PadMapper()
    box.arm(0, m.packet(0), Permit(t=0), Vehicle())
    press(m, 0, BTN_TL)
    stick(m, 0, ABS_Y, -32768)
    box.tick(0.02, m.packet(0.02), Permit(t=0.02), Vehicle(parked=False))
    press(m, 0.03, BTN_TL, False)
    out = box.tick(0.04, m.packet(0.04), Permit(t=0.04), Vehicle(parked=False))
    assert out.state == HOLD and out.throttle == 0


def test_pad_back_needs_arming_again():
    m = PadMapper()
    arm(m)
    m.lost()
    m.found()
    assert not m.armed and not m.estop
