"""System sim: the real Pico firmware inside the whole-vehicle wiring (docs/system-sim.md).

Every test here goes switch -> wire -> opto -> MCP23017 -> firmware -> CAN -> dash,
or dash -> CAN -> firmware -> pin -> wire -> driver board -> fuse -> lamp/motor,
using config/wiring.yaml as drawn. If a wire, a fuse, a ground or a pin number is
wrong in the diagram or the firmware, one of these fails.
"""

import os

import pytest

from teryx import wiring
from teryx.rig import models as MD
from teryx.rig.firmware import compiler

# CI sets TERYX_RIG_REQUIRED on Linux so the sim can't quietly skip there.
needs_cc = pytest.mark.skipif(compiler() is None and not os.environ.get("TERYX_RIG_REQUIRED"),
                              reason="needs a C compiler and pthreads (Linux/macOS)")


def test_every_device_has_a_model():
    d = wiring.load()
    built = MD.build(d["devices"])
    missing = [dev for dev in d["devices"] if dev not in built]
    assert not missing, f"add a model to teryx/rig/models.py (or a NOT_SIMULATED reason) for: {missing}"
    stale = [dev for dev in MD.NOT_SIMULATED if dev not in d["devices"]]
    assert not stale, f"NOT_SIMULATED lists devices that aren't in wiring.yaml: {stale}"


@pytest.fixture
def teryx():
    from teryx.rig import System
    s = System()
    s.key(True)
    s.park(True)
    s.run(4)     # boot, and let the 4WD home from "unknown" (3 s)
    yield s
    s.close()


def snap(s):
    return s.dash.snapshot()


@needs_cc
def test_boots_clean(teryx):
    s = teryx
    st = snap(s)
    assert st["pico.online"] and st["pico.state"] == "ok"
    assert st["pico.faults"] == []
    assert st["mc.online"]
    for chip in ("MCP1", "MCP2", "ADS1", "PCA", "PICO_CAN", "EPS_CAN", "OPTO", "RELAYS", "RELAYS2",
                 "PI_CAN", "PI5", "SCREEN", *(f"BTS{n}" for n in range(1, 10))):
        assert s.powered(chip), f"{chip} has no power or no ground"
    fw = s.fw
    assert fw.can_bitrate(s.can_index["PICO_CAN"]) == 250_000
    assert fw.can_bitrate(s.can_index["EPS_CAN"]) == 500_000
    version = open(wiring.ROOT / "firmware" / "VERSION").read().strip()
    assert st["pico.version"] == ".".join(version.split(".")[:2])
    assert st["in.ignition"] and st["in.park"] and not st["in.brake"]
    assert st["an.aux_12v"] == pytest.approx(12.6, abs=0.05)     # divider -> ADS1115 A1 -> CAN
    assert s.problems == []


@needs_cc
def test_front_bars_dim_through_the_mosfet_board(teryx):
    s, d = teryx, teryx.dash
    d.request("light.front_1", 255)
    d.request("light.front_2", 180)
    d.request("light.interior", 64)
    s.run(0.5)
    assert s.lamp("LB1") == pytest.approx(1.0)
    assert s.lamp("LB2") == pytest.approx(180 / 255, abs=0.01)
    assert s.lamp("LB3") == 0 and s.lamp("LB4") == 0
    assert s.lamp("LB_INT") == pytest.approx(64 / 255, abs=0.01)
    s.pull_fuse("FB.F1")                     # bars 1 + 4 share way 1
    s.run(0.1)
    assert s.lamp("LB1") == 0 and s.lamp("LB2") > 0.6


@needs_cc
def test_headlights_tails_and_brakes(teryx):
    s, d = teryx, teryx.dash
    d.request("light.head", "low")
    d.request("light.tail", 120)
    s.run(0.5)
    for side in ("HEAD_L", "HEAD_R"):
        assert s.lamp(side, "low") == pytest.approx(1.0) and s.lamp(side, "high") == 0
    for side in ("TAIL_L", "TAIL_R"):
        assert s.lamp(side, "tail") == pytest.approx(120 / 255, abs=0.02)
        assert s.lamp(side, "stop") == 0
    d.request("light.head", "high")
    s.run(0.5)
    assert s.lamp("HEAD_L", "high") == pytest.approx(1.0) and s.lamp("HEAD_L", "low") == 0
    s.brake(True)
    s.run(0.3)
    assert snap(s)["in.brake"]
    assert s.lamp("TAIL_L", "stop") == 1.0 and s.lamp("TAIL_R", "stop") == 1.0


@needs_cc
def test_brakes_and_backup_toggle_work_with_the_control_box_dead(teryx):
    s = teryx
    s.trailer(True)
    s.pull_fuse("P08")                       # the control box's 2 A inline fuse
    s.run(1)
    assert s.fw is None and not s.powered("MCP1")
    assert not snap(s)["pico.online"]
    s.brake(True)
    s.run(0.1)
    assert s.lamp("TAIL_L", "stop") == 1.0 and s.lamp("TAIL_R", "stop") == 1.0
    assert s.trailer_pin("P6_STOP") == 1.0
    s.brake(False)
    s.backup_lights(True)
    s.run(0.1)
    assert s.lamp("HEAD_L", "low") == 1.0 and s.lamp("HEAD_R", "low") == 1.0
    assert s.lamp("TAIL_L", "tail") == 1.0 and s.lamp("TAIL_R", "tail") == 1.0
    assert s.trailer_pin("P7_TAIL") == 1.0
    # the Schottky diodes keep the backup feed out of the BTS7960 outputs
    assert s.volts("BTS4.M+") == 0.0
    s.pull_fuse("P08", False)
    s.run(2)
    assert snap(s)["pico.state"] == "ok" and s.problems == []


@needs_cc
def test_reverse_lights_floods_and_trailer_reverse_pin(teryx):
    s = teryx
    s.trailer(True)
    s.fnr("reverse")
    s.run(0.5)
    st = snap(s)
    assert st["in.reverse"] and st["in.trailer"]
    assert s.lamp("FLOOD_L") == 1.0 and s.lamp("FLOOD_R") == 1.0
    assert s.relay(1) and s.trailer_pin("P2_REV") == 1.0
    s.fnr("neutral")
    s.run(0.5)
    assert s.lamp("FLOOD_L") == 0 and s.trailer_pin("P2_REV") == 0


@needs_cc
def test_trailer_plug_tail_stop_and_light_bar(teryx):
    s, d = teryx, teryx.dash
    assert not snap(s)["in.trailer"]
    s.trailer(True)
    d.request("light.tail", 255)
    d.request("light.trailer_bar", 128)
    s.run(0.5)
    assert snap(s)["in.trailer"]                      # reed -> opto 8 -> MCP2 B0
    assert s.trailer_pin("P7_TAIL") > 0.9
    assert s.lamp("LB_TRL") == pytest.approx(128 / 255, abs=0.02)
    s.brake(True)
    s.run(0.2)
    assert s.trailer_pin("P6_STOP") == 1.0


@needs_cc
def test_beacon_strobe_and_full_emergency_flash_the_real_lamps(teryx):
    s, d = teryx, teryx.dash
    s.trailer(True)
    d.request("light.interior", 64)
    d.request("light.flash", "warning")
    seen = {"amber": 0, "white": 0}
    for _ in range(100):
        s.run(0.01)
        a, w = s.lamp("BEACON", "amber"), s.lamp("BEACON", "white")
        assert not (a and w)
        seen["amber"] += a > 0
        seen["white"] += w > 0
    assert seen["amber"] > 5 and seen["white"] > 5
    assert s.lamp("HEAD_L", "low") == 0 and snap(s)["light.flash_running"]

    d.request("light.flash", "emergency")
    pairs = set()
    for _ in range(100):
        s.run(0.01)
        hl, hr = s.lamp("HEAD_L", "low") > 0, s.lamp("HEAD_R", "low") > 0
        b1, b4 = s.lamp("LB1") > 0, s.lamp("LB4") > 0
        assert s.lamp("HEAD_L", "high") == 0 and s.lamp("HEAD_R", "high") == 0
        assert s.lamp("LB_INT") == pytest.approx(64 / 255, abs=0.01)    # cabin left alone
        pairs.add((hl, hr, b1, b4, s.lamp("TAIL_L", "stop") > 0, s.lamp("TAIL_R", "stop") > 0,
                   s.lamp("FLOOD_L") > 0, s.lamp("FLOOD_R") > 0, s.lamp("LB_TRL") > 0))
    assert (True, False, True, False, True, False, True, False, True) in pairs     # left side
    assert (False, True, False, True, False, True, False, True, False) in pairs    # right side
    s.brake(True)                                     # rule 1: brake lamps steady full
    for _ in range(30):
        s.run(0.01)
        assert s.lamp("TAIL_L", "stop") == 1.0 and s.lamp("TAIL_R", "stop") == 1.0
    s.brake(False)

    d.request("light.flash", "off")                  # one tap and it's all back to normal
    s.run(0.3)
    for _ in range(40):
        s.run(0.01)
        assert s.lamp("BEACON", "amber") == 0 and s.lamp("HEAD_L", "low") == 0 and s.lamp("LB1") == 0
    assert not snap(s)["light.flash_running"]


@needs_cc
def test_4wd_and_diff_lock_move_and_report(teryx):
    s, d = teryx, teryx.dash
    d.request("act.4wd", 1)
    assert s.run(4, until=lambda: snap(s)["act.4wd"] == "4wd")
    assert s.actuator("ACT_4WD").pos == 1.0
    d.request("act.diff", 50)
    assert s.run(6, until=lambda: abs(snap(s)["an.diff_pos"] - 50) <= 3 and s.actuator("ACT_DIFF").drive == 0)
    assert s.actuator("ACT_DIFF").pos == pytest.approx(0.5, abs=0.05)   # pot -> ADS1115 A0 closes the loop
    d.request("act.4wd", 0)
    assert s.run(4, until=lambda: snap(s)["act.4wd"] == "2wd")
    assert s.actuator("ACT_4WD").pos == 0.0
    assert snap(s)["pico.faults"] == []


@needs_cc
def test_tray_runs_to_the_up_limit_switch(teryx):
    s, d = teryx, teryx.dash
    for _ in range(250):
        d.hold("act.tray", 1)
        s.run(0.1)
        if snap(s)["act.tray"] == "up":
            break
    d.hold("act.tray", 0)
    s.run(0.3)
    st = snap(s)
    assert st["act.tray"] == "up" and st["in.tray_up"] and not st["in.tray_down"]
    assert s.actuator("ACT_TRAY").pos >= 0.99
    assert st["pico.faults"] == []


@needs_cc
def test_broken_tray_limit_wire_locks_the_tray_out(teryx):
    s, d = teryx, teryx.dash
    s.pull_fuse("I05")      # up-limit wire cut: NC input reads "at limit" while the tray is down
    s.run(0.5)
    assert "tray_limit_switch" in snap(s)["pico.faults"]
    for _ in range(5):
        d.hold("act.tray", 1)
        s.run(0.1)
    assert s.actuator("ACT_TRAY").pos == 0.0


@needs_cc
def test_winch_from_the_dash_and_by_hand(teryx):
    s, d = teryx, teryx.dash
    d.request("winch.armed", True)
    s.run(0.3)
    for _ in range(8):
        d.hold("winch", 1)
        s.run(0.1)
    assert s.relay(4) and s.m["WINCH_MOTOR"].turning(s.net.get) == "in"
    assert not snap(s)["in.winch_remote"]     # the Pico's own pull isn't mistaken for the remote
    d.hold("winch", 0)
    s.run(0.3)
    assert s.m["WINCH_MOTOR"].turning(s.net.get) is None
    for where in ("cab", "winch"):
        s.winch_switch(where, "out")
        s.run(0.3)
        assert s.m["WINCH_MOTOR"].turning(s.net.get) == "out" and snap(s)["in.winch_remote"]
        s.winch_switch(where, None)
        s.run(0.3)
    s.winch_remote("in")
    s.run(0.3)
    assert s.m["WINCH_MOTOR"].turning(s.net.get) == "in" and snap(s)["in.winch_remote"]
    for _ in range(4):
        d.hold("winch", -1)                    # the dash tries to pay out while the remote pulls in
        s.run(0.1)
    assert snap(s)["pico.reject"] == "winch_remote" and not s.relay(5)
    s.winch_remote(None)
    s.run(0.3)
    assert s.problems == []                     # never both coils at once
    s.winch_breaker(False)                     # push the 250 A breaker off: the winch is dead
    s.winch_remote("in")
    s.run(0.2)
    assert s.m["WINCH_MOTOR"].turning(s.net.get) is None


@needs_cc
def test_key_off_holds_power_until_the_pi_has_shut_down(teryx):
    s = teryx
    assert s.relay(7) and s.powered("GLOVE_USB") and s.powered("CAM_REAR")
    s.key(False)
    s.run(0.5)
    assert not s.relay(7) and not s.powered("GLOVE_USB")   # accessory off at once
    assert snap(s)["pico.shutdown_request"]
    assert s.relay(8) and s.volts("RAIL.BUS") > 12          # held up by relay 8, not the key
    t_off = s.t
    assert s.run(40, until=lambda: s.volts("RAIL.BUS") == 0)
    held = s.t - t_off
    assert 1 + s.pi_poweroff_s + 9 < held < 1 + s.pi_poweroff_s + 12   # Pi stops, then 10 s, then off
    assert s.fw is None and not s.pi_powered()
    s.key(True)
    assert s.run(3, until=lambda: s.dash.snapshot().get("pico.state") == "ok")


@needs_cc
def test_vehicle_lock_opens_the_shinegle_key_line(teryx):
    s, d = teryx, teryx.dash
    d.lock("set_pin", "1234")
    s.run(0.5)
    d.lock("lock")
    s.run(0.5)
    assert snap(s)["lock.state"] == "locked"
    assert s.relay(10) and not s.m["SG1202"].ksi(s.net.get)
    assert not s.relay(9)                        # power steering off while locked
    s.park(False)
    s.fnr("forward")
    s.throttle(0.6)
    s.run(2)
    assert s.sim.vehicle.speed_ms == 0
    s.throttle(0)
    s.fnr("neutral")
    s.park(True)
    d.lock("unlock", "1234")
    s.run(1)
    assert snap(s)["lock.state"] == "unlocked" and s.m["SG1202"].ksi(s.net.get)


@needs_cc
def test_drive_and_e_stop(teryx):
    s = teryx
    s.park(False)
    s.fnr("forward")
    s.throttle(0.4)
    assert s.run(5, until=lambda: snap(s)["mc.speed"] > 8)
    assert snap(s)["mc.direction"] == "forward"
    s.estop(True)
    s.run(0.2)
    assert not s.m["SG1202"].ksi(s.net.get)      # the e-stop is in series with KSI
    s.estop(False)
    s.throttle(0)


@needs_cc
def test_power_steering_gets_ignition_and_its_frames(teryx):
    s = teryx
    assert s.relay(9) and s.m["EPS_ECU"].awake(s.net.get)
    before = dict(s.eps_frames)
    s.run(1)
    for cid in (0x0B4, 0x2C4):                   # speed + engine running, 500 kbit/s steering bus
        assert s.eps_frames.get(cid, 0) - before.get(cid, 0) >= 40


@needs_cc
def test_low_12v_is_seen_through_the_divider(teryx):
    s = teryx
    s.battery(11.0)
    assert s.run(8, until=lambda: "low_12v" in snap(s)["pico.faults"])
    assert snap(s)["an.aux_12v"] == pytest.approx(11.0, abs=0.05)


@needs_cc
def test_lost_logic_ground_is_an_io_fault(teryx):
    s = teryx
    s.pull_fuse("G39")                           # MCP1's ground wire
    assert s.run(2, until=lambda: "io_bus" in snap(s)["pico.faults"])


@needs_cc
def test_sim_catches_a_wiring_mistake():
    """Move one PWM wire to the wrong Pico pin and the bar it feeds goes dark."""
    from teryx.rig import System
    d = wiring.load()
    for w in d["wires"]:
        if w["id"] == "LT12":                    # GP17 -> MOSFET IN2 (front bar 2)
            w["from"] = "PICO.GP21"
    s = System(wiring_data=d)
    try:
        s.key(True)
        s.run(3)
        s.dash.request("light.front_2", 255)
        s.run(0.5)
        assert s.dash.snapshot()["light.front_2"] == 255   # the Pico thinks it's on...
        assert s.lamp("LB2") == 0                         # ...but the bar is dark
    finally:
        s.close()
