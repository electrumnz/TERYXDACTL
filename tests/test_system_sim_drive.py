"""System sim: the Shinegle and the Aqua power steering on ASSUMED behaviour.

The real control box firmware talks to a modelled Shinegle (pedal through the
wires, HPD, faults, PLACEHOLDER CAN layout) and a modelled Aqua EPS ECU (the
Toyota frames in teryx/eps_toyota.py, assist that drops with speed, limp mode,
torque sensor faults). The assumptions are named constants in teryx/rig/models.py;
when the bench test says otherwise, change the constant and these tests show what
moved. docs/system-sim.md has the list.
"""

import os

import pytest

from teryx.rig import models as MD
from teryx.rig.firmware import compiler

needs_cc = pytest.mark.skipif(compiler() is None and not os.environ.get("TERYX_RIG_REQUIRED"),
                              reason="needs a C compiler and pthreads (Linux/macOS)")
pytestmark = needs_cc


@pytest.fixture
def teryx():
    from teryx.rig import System
    s = System()
    s.key(True)
    s.park(True)
    s.run(4)
    yield s
    s.close()


def snap(s):
    return s.dash.snapshot()


def setting(s, name, value):
    s.dash.set_setting(name, value, timeout=0)   # the ack comes back as the sim runs
    s.run(0.3)


# ---------------------------------------------------------------- power steering
def test_steering_assist_and_the_pico_hears_the_ecu(teryx):
    s = teryx
    assert s.eps()["mode"] == "normal" and s.eps()["assist_ratio"] == 3.0   # crawling: full assist
    s.steer(3.0)                       # a light push on the wheel
    s.run(1.0)
    st = snap(s)
    assert st["steer.state"] == "ok" and st["steer.heard"] and st["steer.frames"]
    assert st["steer.angle"] > 100     # 0x260 angle, through the Pico's 0x718, on the dash
    assert st["steer.torque"] == 300   # 3 Nm at the ASSUMED 0.01 Nm per bit
    s.steer(0)


def test_assist_drops_as_the_teryx_speeds_up(teryx):
    s = teryx
    s.park(False)
    s.fnr("forward")
    s.throttle(1.0)
    assert s.run(15, until=lambda: snap(s)["mc.speed"] > 35)
    s.run(0.2)
    e = s.eps()
    assert e["told_kmh"] > 30 and e["assist_ratio"] < 2.5   # 3.0 when crawling
    s.throttle(0)


def test_no_power_steering_with_the_key_off_is_a_heavy_manual_column(teryx):
    s = teryx
    s.key(False)
    s.run(1)
    assert s.eps()["mode"] == "manual"
    s.steer(3.0)                       # not enough to turn it by hand
    s.run(1)
    assert s.eps()["angle_deg"] == 0
    s.steer(8.0)                       # leaning on it
    s.run(1)
    assert 0 < s.eps()["angle_deg"] < 200


def test_limp_mode_setting_stops_the_speed_frames(teryx):
    s = teryx
    setting(s, "eps_mode", 1)
    s.run(1.5)
    assert snap(s)["steer.state"] == "limp" and not snap(s)["steer.frames"]
    assert s.eps()["mode"] == "limp" and s.eps()["assist_ratio"] == MD.ASSIST_LIMP


def test_quiet_ecu_shows_no_reply_when_listening(teryx):
    s = teryx
    setting(s, "eps_listen", 1)
    s.run(0.5)
    assert snap(s)["steer.state"] == "ok"
    s.m["EPS_ECU"].silent = True       # e.g. the Aqua doesn't use the opendbc frames after all
    s.run(1.5)
    assert snap(s)["steer.state"] == "no_reply"
    assert s.eps()["mode"] == "normal"  # it still steers: the Pico's speed frames still go


def test_torque_sensor_wire_off_is_an_ecu_fault(teryx):
    s = teryx
    setting(s, "eps_listen", 1)
    s.m["EPS_COL"].trq2_broken = True
    s.run(0.5)
    assert s.eps()["mode"] == "fault" and s.eps()["assist_ratio"] == 0
    assert snap(s)["steer.state"] == "ecu_fault"


# ---------------------------------------------------------------- Shinegle
def test_pedal_down_at_key_on_does_nothing_until_lifted(teryx):
    s = teryx
    s.key(False)
    s.run(1)
    s.park(False)
    s.fnr("forward")
    s.throttle(0.6)
    s.key(True)                        # foot already down: high pedal disable
    s.run(3)
    assert s.m["SG1202"].hpd and snap(s)["mc.speed"] < 0.5
    s.throttle(0)
    s.run(0.2)
    s.throttle(0.6)
    assert s.run(5, until=lambda: snap(s)["mc.speed"] > 5)
    s.throttle(0)


def test_cut_throttle_wire_means_no_drive(teryx):
    s = teryx
    s.park(False)
    s.fnr("forward")
    s.pull_fuse("S08")                 # THROTTLE.WIPER -> SG1202.J1-16 cut
    s.throttle(0.8)
    s.run(3)
    assert snap(s)["mc.speed"] < 0.5
    s.pull_fuse("S08", pulled=False)
    assert s.run(5, until=lambda: snap(s)["mc.speed"] > 5)
    s.throttle(0)


def test_park_brake_on_blocks_drive(teryx):
    """docs/park-brake.md: F can be picked with the park brake on, but the Pico opens the
    pedal switch wire (relay 6) so the Shinegle gives no drive until it's let off."""
    s = teryx                          # key on, park brake on
    s.fnr("forward")
    s.throttle(0.8)
    s.run(3)
    st = snap(s)
    assert st["pico.park_block"] and st["drive.park_block"]
    assert st["mc.direction"] == "forward" and st["mc.speed"] < 0.5
    assert s.m["SG1202"].report(s.net.get)["throttle"] == 0
    s.park(False)                      # let it off: drive straight away (pedal still down)
    assert s.run(5, until=lambda: snap(s)["mc.speed"] > 5)
    assert not snap(s)["pico.park_block"]
    s.throttle(0)


def test_park_interlock_setting_off_lets_it_drive(teryx):
    s = teryx
    setting(s, "park_interlock", 0)
    s.fnr("forward")
    s.throttle(1.0)
    s.run(1)
    assert not snap(s)["pico.park_block"]
    assert s.m["SG1202"].report(s.net.get)["throttle"] > 0.5   # the pedal reaches the Shinegle again
    s.throttle(0)


def test_shinegle_fault_reaches_the_dash(teryx):
    s = teryx
    s.sim.apply({"shinegle_fault": ["motor_over_temp", True]})
    s.run(0.5)
    assert "motor_over_temp" in snap(s)["mc.faults"]
    s.sim.apply({"shinegle_fault": ["motor_over_temp", False]})
    s.run(0.5)
    assert "motor_over_temp" not in snap(s)["mc.faults"]
