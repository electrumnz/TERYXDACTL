"""Safety rules of the control box emulator (the spec for the Pico firmware)."""

import pytest

from teryx.canbus import messages as M
from teryx.canbus import shinegle as SG
from teryx.sim.controlbox import ControlBox

DIRECTIONS = {0: "neutral", 1: "forward", 2: "reverse"}


def shinegle_frames(speed, direction):
    """What the Shinegle sends for this speed and direction, whatever the installed layout."""
    mc = {**SG.MC_DEFAULTS, "mc.speed": speed, "mc.direction": DIRECTIONS[direction]}
    for msg, raw in SG.encode(mc):
        yield msg.name, msg.decode(msg.encode(raw))


class Bench:
    """Drives a ControlBox with a fake clock, like the dash and Shinegle would."""

    def __init__(self):
        self.cb = ControlBox()
        self.t = 0.0
        self.speed = 0.0
        self.direction = 1
        self.hold = None   # (tray, winch, armed)
        self.dash_alive = True
        self.shinegle_alive = True

    def run(self, seconds, dt=0.02):
        steps = int(round(seconds / dt))
        for _ in range(steps):
            self.t += dt
            if self.shinegle_alive:
                for name, values in shinegle_frames(self.speed, self.direction):
                    self.cb.on_frame(name, values, self.t)
            if self.dash_alive:
                self.cb.on_frame("PI_HEARTBEAT", {"dash_state": 1}, self.t)
                if self.hold:
                    tray, winch, armed = self.hold
                    self.cb.on_frame("PI_HOLD", {"tray": tray, "winch": winch, "winch_armed": armed}, self.t)
            self.cb.step(dt, self.t)

    def drive_req(self, fourwd=0, diff=0):
        self.cb.on_frame("PI_DRIVE", {"fourwd_req": fourwd, "diff_target": diff}, self.t)


@pytest.fixture
def b():
    bench = Bench()
    bench.run(0.2)          # Shinegle speed arrives
    bench.drive_req(0, 0)   # dash's first frame after boot drives 4WD to a known end stop
    bench.run(1.5)
    return bench


def test_boots_ok_and_in_2wd(b):
    assert b.cb.state() == "ok"
    assert b.cb.fourwd_state() == "2wd"
    assert b.cb.faults() == set()


def test_4wd_engages_when_slow(b):
    b.drive_req(1)
    b.run(0.5)
    assert b.cb.fourwd_state() == "to_4wd"
    b.run(2.5)
    assert b.cb.fourwd_state() == "4wd"


def test_4wd_refused_when_too_fast_and_not_done_later(b):
    b.speed = 20
    b.run(0.2)
    b.drive_req(1)
    b.run(0.2)
    assert b.cb.reject_reason == "too_fast"
    assert b.cb.reject_count == 1
    # The dash keeps resending the same request every second; slowing down must not engage it
    b.speed = 0
    for _ in range(3):
        b.drive_req(1)
        b.run(1.0)
    assert b.cb.fourwd_state() == "2wd"


def test_4wd_limit_follows_settings(b):
    b.cb.on_frame("PI_SETTINGS", {"key": 3, "value": 25}, b.t)
    assert b.cb.acks[-1] == {"key": 3, "status": 0, "value": 25}
    b.speed = 20
    b.run(0.2)
    b.drive_req(1)
    b.run(3)
    assert b.cb.fourwd_state() == "4wd"


def test_setting_values_are_clamped(b):
    b.cb.on_frame("PI_SETTINGS", {"key": 3, "value": 500}, b.t)
    assert b.cb.settings["fourwd_max_kmh"] == 40
    assert b.cb.acks[-1]["value"] == 40 and b.cb.acks[-1]["status"] == 2
    assert not b.cb.on_defaults
    b.cb.on_frame("PI_SETTINGS", {"key": M.SETTING_RESET, "value": 0}, b.t)
    assert b.cb.on_defaults and b.cb.settings["fourwd_max_kmh"] == 1


def test_diff_lock_moves_to_target(b):
    b.speed = 10
    b.run(0.1)
    b.drive_req(0, 60)
    b.run(3)
    assert b.cb.diff.pos == pytest.approx(0.6)


def test_diff_lock_refused_above_15(b):
    b.speed = 16
    b.run(0.1)
    b.drive_req(0, 100)
    b.run(1)
    assert b.cb.reject_reason == "too_fast"
    assert b.cb.diff.pos == 0


def test_diff_unlocks_while_moving(b):
    # Unlocking always works, so you can drop the lock before a turn
    b.drive_req(0, 100)
    b.run(4)
    assert b.cb.diff.pos == pytest.approx(1.0)
    b.speed = 20
    b.run(0.1)
    b.drive_req(0, 0)
    b.run(4)
    assert b.cb.diff.pos == pytest.approx(0.0)


def test_tray_needs_hold_to_run(b):
    b.hold = (1, 0, 0)
    b.run(2)
    assert b.cb.tray_state() == "raising"
    up = b.cb.tray.pos
    assert up > 0.05
    b.hold = None                      # finger off, frames stop
    b.run(0.5)
    assert b.cb.tray_state() == "mid"
    assert b.cb.tray.pos == pytest.approx(up, abs=0.03)


def test_tray_reaches_top_limit(b):
    b.hold = (1, 0, 0)
    b.run(17)
    assert b.cb.tray_state() == "up"
    assert b.cb.relays()  # still sane
    assert b.cb.inp("in.tray_up")


def test_tray_refused_when_moving(b):
    b.speed = 3
    b.hold = (1, 0, 0)
    b.run(1)
    assert b.cb.reject_reason == "not_stopped"
    assert b.cb.tray.pos == 0


def test_tray_refused_without_speed_signal(b):
    b.shinegle_alive = False
    b.run(1)
    assert "speed_unknown" in b.cb.faults()
    b.hold = (1, 0, 0)
    b.run(1)
    assert b.cb.reject_reason == "speed_unknown"
    assert b.cb.tray.pos == 0


def test_winch_needs_arming(b):
    b.hold = (0, 1, 0)
    b.run(0.5)
    assert b.cb.reject_reason == "not_armed"
    assert not b.cb.relays()["winch.in"]
    b.hold = (0, 0, 1)
    b.run(0.2)
    assert b.cb.relays()["winch.isolator"]
    b.hold = (0, 1, 1)
    b.run(0.5)
    assert b.cb.relays()["winch.in"] and not b.cb.relays()["winch.out"]


def test_winch_never_in_and_out_together(b):
    b.hold = (0, 1, 1)
    b.run(0.5)
    b.hold = (0, -1, 1)
    b.run(0.04)   # inside the 100 ms dead time
    r = b.cb.relays()
    assert not (r["winch.in"] and r["winch.out"])
    assert not r["winch.out"]
    b.run(0.3)
    assert b.cb.relays()["winch.out"]


def test_winch_auto_disarms(b):
    b.hold = (0, 0, 1)
    b.run(0.2)
    b.hold = None
    b.run(121)
    assert not b.cb.winch_armed


def test_lost_dash_stops_things_but_keeps_lights(b):
    b.cb.on_frame("PI_LIGHTS", {"front_1": 200, "front_2": 0, "front_3": 0, "front_4": 0,
                                "interior": 50, "effect": 0, "rear_on": 0, "rear_auto": 1}, b.t)
    b.hold = (0, 0, 1)
    b.run(0.2)
    b.drive_req(0, 100)
    b.run(1)
    assert b.cb.diff.moving
    b.dash_alive = False
    b.run(0.7)
    assert "dash_link" in b.cb.faults()
    assert b.cb.state() == "degraded"
    assert not b.cb.diff.moving
    assert not b.cb.winch_armed
    assert b.cb.lights_out["front_1"] == 200


def test_rear_pods_come_on_in_reverse(b):
    assert not b.cb.relays()["light.rear"]
    b.direction = 2
    b.run(0.1)
    assert b.cb.relays()["light.rear"]
    assert b.cb.inp("in.reverse")


def test_on_off_only_lights(b):
    b.cb.on_frame("PI_SETTINGS", {"key": 16, "value": 0b10000}, b.t)  # only interior dims
    b.cb.on_frame("PI_LIGHTS", {"front_1": 10, "front_2": 0, "front_3": 0, "front_4": 0,
                                "interior": 10, "effect": 0, "rear_on": 0, "rear_auto": 0}, b.t)
    b.run(0.1)
    assert b.cb.lights_out["front_1"] == 255
    assert b.cb.lights_out["interior"] == 10


def test_jammed_diff_trips_on_current(b):
    b.cb.on_frame("BENCH_INPUTS", {"inputs": 0, "force_mask": 0, "fault_inject": 0b001}, b.t)
    b.drive_req(0, 100)
    b.run(5)
    assert "diff_overcurrent" in b.cb.faults()
    assert not b.cb.diff.moving


def test_diff_pot_disconnected(b):
    b.cb.on_frame("BENCH_INPUTS", {"inputs": 0, "force_mask": 0, "fault_inject": 0b01000}, b.t)
    b.drive_req(0, 100)
    b.run(0.5)
    assert "diff_pot_stuck" in b.cb.faults()


def test_io_bus_and_low_12v(b):
    b.cb.on_frame("BENCH_INPUTS", {"inputs": 0, "force_mask": 0, "fault_inject": 0b10000, "aux_mv": 10500}, b.t)
    b.run(0.2)
    assert {"io_bus", "low_12v"} <= b.cb.faults()


def test_4wd_overcurrent(b):
    b.cb.on_frame("BENCH_INPUTS", {"inputs": 0, "force_mask": 0, "fault_inject": 0b100}, b.t)
    b.drive_req(1)
    b.run(1)
    assert "fourwd_overcurrent" in b.cb.faults()
    assert b.cb.fourwd_state() == "fault"


def test_key_off_holds_power_then_drops(b):
    ign = 1 << 0
    b.cb.on_frame("BENCH_INPUTS", {"inputs": 0, "force_mask": ign, "fault_inject": 0}, b.t)
    b.run(1)
    assert b.cb.relays()["power.hold"] and not b.cb.relays()["aux.accessory"]
    b.run(30)
    assert not b.cb.relays()["power.hold"]


def test_frames_encode(b):
    from teryx.canbus.registry import BY_NAME
    for name, values in b.cb.frames():
        BY_NAME[name].encode(values)


def test_io_map_safety_values_are_read(tmp_path):
    from teryx.config import safety_defaults
    f = tmp_path / "io-map.yaml"
    f.write_text("safety:\n  fourwd_max_kmh: 7\n  tray_max_run_s: 12\n  tray_requires_stopped: true\n")
    s = safety_defaults(f)
    assert s["fourwd_max_kmh"] == 7 and s["tray_max_run_ms"] == 12000
    assert s["diff_max_kmh"] == 15


def test_built_in_defaults_match_the_io_list():
    from pathlib import Path

    from teryx.config import safety_defaults
    io_map = Path(__file__).resolve().parent.parent / "config" / "io-map.yaml"
    if not io_map.exists():
        pytest.skip("io-map.yaml not on this branch yet")
    assert safety_defaults(io_map) == M.default_settings()


def test_4wd_unknown_until_first_move():
    bench = Bench()
    bench.run(1)
    assert bench.cb.fourwd_state() == "unknown"
    bench.drive_req(0)
    bench.run(1.5)
    assert bench.cb.fourwd_state() == "2wd"


def test_unknown_setting_key(b):
    b.cb.on_frame("PI_SETTINGS", {"key": 99, "value": 1}, b.t)
    assert b.cb.acks[-1]["status"] == 1


def test_tray_fault_cleared_by_next_press(b):
    b.cb.on_frame("BENCH_INPUTS", {"inputs": 0, "force_mask": 0, "fault_inject": 0b010}, b.t)
    b.hold = (1, 0, 0)
    b.run(2)
    assert b.cb.tray_state() == "fault"
    b.hold = None
    b.cb.on_frame("BENCH_INPUTS", {"inputs": 0, "force_mask": 0, "fault_inject": 0}, b.t)
    b.run(0.5)
    b.hold = (1, 0, 0)
    b.run(1)
    assert b.cb.tray_state() == "raising"


def test_tray_at_limit_is_refused(b):
    b.hold = (-1, 0, 0)
    b.run(0.3)
    assert b.cb.reject_reason == "at_limit"


def test_winch_arming_needs_stopped(b):
    b.speed = 5
    b.hold = (0, 0, 1)
    b.run(0.3)
    assert not b.cb.winch_armed and b.cb.reject_reason == "not_stopped"


def test_winch_refused_with_remote_in_use(b):
    b.cb.on_frame("BENCH_INPUTS", {"inputs": 1 << 5, "force_mask": 1 << 5, "fault_inject": 0}, b.t)
    b.hold = (0, 1, 1)
    b.run(0.3)
    assert b.cb.reject_reason == "winch_remote"


def test_status_extras(b):
    st = dict(b.cb.frames())["PICO_STATUS"]
    assert st["speed_valid"] == 1 and st["speed"] == 0 and st["parked"] == 0  # in drive
    b.direction = 0
    b.run(0.1)
    assert dict(b.cb.frames())["PICO_STATUS"]["parked"] == 1
    b.shinegle_alive = False
    b.run(1)
    assert dict(b.cb.frames())["PICO_STATUS"]["speed"] == 255


def test_clear_faults_setting(b):
    b.cb.on_frame("BENCH_INPUTS", {"inputs": 0, "force_mask": 0, "fault_inject": 0b100}, b.t)
    b.drive_req(1)
    b.run(1)
    assert b.cb.fourwd_state() == "fault"
    b.cb.on_frame("PI_SETTINGS", {"key": M.SETTING_CLEAR_FAULTS, "value": 0}, b.t)
    assert "fourwd_overcurrent" not in b.cb.faults()


def test_unknown_4wd_homes_on_resend_once_speed_is_known():
    bench = Bench()
    bench.shinegle_alive = False
    bench.drive_req(0)          # first frame, no speed yet: refused
    bench.run(0.5)
    assert bench.cb.reject_reason == "speed_unknown"
    bench.shinegle_alive = True
    bench.run(0.5)
    bench.drive_req(0)          # the 1 s resend
    bench.run(1.5)
    assert bench.cb.fourwd_state() == "2wd"
