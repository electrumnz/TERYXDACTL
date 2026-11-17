"""Emulates the Pico 2 control box, frame for frame.

It listens on the bus like the real Pico (dash requests, Shinegle speed, bench
inputs), moves the actuators at realistic speeds, applies the IO list safety
rules and sends back 0x710-0x714. The real firmware (control box thread) must
behave the same, so this file doubles as a readable spec. Swap it out with
``--no-controlbox`` and run the firmware's host build on the same bus instead.

Safety rules (IO list section 7, values from SETTINGS):
 1. Dash heartbeat lost 500 ms -> stop winch, tray and actuators, disarm winch.
    Lights stay as they are. Driving is never touched.
 2. No Shinegle speed for 500 ms -> speed unknown, block anything needing "stopped".
 3. 2WD/4WD only below 1 km/h (stopped, per Kawasaki). Runs to end stop, max 3 s, stops on current > 6 A.
    Position is "unknown" after boot until the first move to an end stop.
 4. Adding diff lock % only below 15 km/h; unlocking at any speed. Max run 4 s. Pot not moving -> fault.
    3/4 extra (docs/drive-changes.md): a 4WD or diff request that is only too fast
    WAITS up to shift_wait_ms for the speed to come right, then runs. Asking for
    what's already there cancels it; a wait that runs out is dropped (wait_timeout).
    One drive change at a time ("busy"), except taking diff lock off. Throttle is
    held while a shift runs, only if it started from a standstill, never once moving.
 5. Tray only when stopped, hold-to-run. Limit switches, current > 10 A, max 20 s.
    A latched tray fault is cleared by the next accepted press.
 6. Winch: arming needs stopped + known speed. Running needs armed + stopped +
    hold-to-run. 100 ms dead time between in and out. Auto-disarm after 2 min idle.
    Refused while the handheld remote is in use.
 7. Reverse -> rear pods on (if auto). Camera is handled on the Pi.
 8. Key-off -> hold power for shutdown_wait_s, then drop power.hold.
 9. Brake pedal regen (off by default, setting brake_regen_on): see teryx/regen.py.
    Regen strong enough also lights the trailer brake lights.

Requests act on a *change* of value. The dash resends 0x701/0x702 every second
so a rebooted Pico picks them up, but a refused 4WD request is not quietly
done later when the speed drops.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..canbus import messages as M
from ..canbus import shinegle as SG
from ..config import safety_defaults
from ..regen import BrakeRegen

FW_VERSION = (0, 1)  # what the fake box reports as its firmware version


@dataclass
class Actuator:
    """Linear actuator. ``pos`` 0..1 of stroke."""
    rate: float                 # fraction of stroke per second
    pos: float = 0.0
    target: float = 0.0
    running_for: float = 0.0
    current: float = 0.0
    jammed: bool = False
    faulted: bool = False

    def drive(self, dt: float, run_current: float) -> None:
        if self.faulted:
            self.current = 0.0
            return
        d = self.target - self.pos
        if abs(d) < 1e-4:
            self.running_for = 0.0
            self.current += (0 - self.current) * min(1, dt * 20)
            return
        self.running_for += dt
        if self.jammed:
            self.current += (run_current * 4 - self.current) * min(1, dt * 4)
            return
        step = self.rate * dt
        self.pos = self.target if abs(d) <= step else self.pos + math.copysign(step, d)
        self.current += (run_current - self.current) * min(1, dt * 10)

    def stop(self) -> None:
        self.target = self.pos
        self.running_for = 0.0

    @property
    def moving(self) -> bool:
        return abs(self.target - self.pos) > 1e-4 and not self.faulted


@dataclass
class ControlBox:
    settings: dict = field(default_factory=safety_defaults)
    on_defaults: bool = True
    t: float = 0.0
    # actuators
    fourwd: Actuator = field(default_factory=lambda: Actuator(rate=0.5, pos=0.5, target=0.5))  # 2 s end to end
    fourwd_known: bool = False     # unknown after boot until the first move to an end stop
    diff: Actuator = field(default_factory=lambda: Actuator(rate=0.3))       # 3.3 s 0-100 %
    tray: Actuator = field(default_factory=lambda: Actuator(rate=1 / 16))    # 400 mm at 25 mm/s
    fourwd_fault: bool = False
    # safe drive changes: (start time, wanted position) while waiting for the right speed
    fourwd_wait: tuple | None = None
    diff_wait: tuple | None = None
    throttle_hold: bool = False
    throttle_hold_blocked: bool = False
    # winch
    winch_armed: bool = False
    winch_dir: int = 0
    winch_idle: float = 0.0
    winch_dead_until: float = 0.0
    winch_timed_s: int = 0             # 0x703 byte 3: timed pull length, 0 = plain hold
    winch_timed_start: float | None = None
    winch_timed_done: bool = False
    # requests
    lights_req: dict = field(default_factory=lambda: {
        "front_1": 0, "front_2": 0, "front_3": 0, "front_4": 0, "interior": 0,
        "effect": 0, "rear_on": 0, "rear_auto": 1})
    lights_out: dict = field(default_factory=dict)
    hold_tray: int = 0
    hold_winch: int = 0
    last_hold: float = -1e9
    _last_drive_req: dict | None = None
    _last_hold_vals: tuple = (0, 0)
    # links
    last_dash: float = -1e9
    last_speed: float = -1e9
    speed: float = 0.0
    direction: str = "neutral"
    brake: bool = False
    soc: float | None = None
    throttle: float = 0.0
    # brake pedal regen: pedal sensor raw reading (wired to the second ADS1115), None = no sensor
    pedal_raw: int | None = None
    regen: BrakeRegen = field(default_factory=BrakeRegen)
    # inputs
    inputs: dict = field(default_factory=lambda: {n: False for n in M.INPUT_BITS.values()})
    forced: dict = field(default_factory=dict)
    bench_faults: set = field(default_factory=set)
    ignition_off_at: float | None = None
    aux_12v: float = 13.6
    bench_aux_mv: int = 0
    temp: float = 32.0
    # faults / rejects
    latched: set = field(default_factory=set)
    reject_reason: str = "none"
    reject_count: int = 0
    acks: list = field(default_factory=list)   # pending 0x714 frames

    def __post_init__(self):
        self.inputs["in.ignition"] = True
        self.inputs["in.tray_down"] = True

    # ------------------------------------------------------------ helpers
    def s(self, name: str) -> int:
        return self.settings[name]

    def dash_ok(self) -> bool:
        return self.t - self.last_dash < self.s("heartbeat_timeout_ms") / 1000

    def speed_known(self) -> bool:
        return self.t - self.last_speed < self.s("speed_timeout_ms") / 1000

    def stopped(self) -> bool:
        return self.speed_known() and self.speed < 0.5

    def reject(self, reason: str) -> None:
        self.reject_reason = reason
        self.reject_count = (self.reject_count + 1) & 0xF

    def inp(self, name: str) -> bool:
        return self.forced.get(name, self.inputs[name])

    # ------------------------------------------------------------ bus input
    def on_frame(self, name: str, v: dict, now: float) -> None:
        self.t = now
        if name in SG.BY_NAME:
            mc = SG.decode(SG.BY_NAME[name], v)
            if "mc.speed" in mc:
                self.last_speed = now
                self.speed = mc["mc.speed"]
            self.direction = mc.get("mc.direction", self.direction)
            self.brake = mc.get("mc.brake", self.brake)
            self.soc = mc.get("mc.soc", self.soc)
            self.throttle = mc.get("mc.throttle", self.throttle)
        elif name == "PI_HEARTBEAT":
            self.last_dash = now
        elif name == "PI_LIGHTS":
            self.lights_req = {k: v[k] for k in self.lights_req}
        elif name == "PI_DRIVE":
            self._drive_request(v)
        elif name == "PI_HOLD":
            self._hold_request(v, now)
        elif name == "PI_SETTINGS":
            self._setting(int(v["key"]), int(v["value"]))
        elif name == "BENCH_INPUTS":
            mask = int(v["force_mask"])
            self.forced = {n: bool(int(v["inputs"]) & (1 << b))
                           for b, n in M.INPUT_BITS.items() if mask & (1 << b)}
            self.bench_faults = set(M.bits_to_names(v["fault_inject"], M.BENCH_FAULTS))
            self.bench_aux_mv = int(v.get("aux_mv", 0))

    def _setting(self, key: int, value: int) -> None:
        status = 0
        if key == M.SETTING_RESET:
            self.settings = safety_defaults()
            self.on_defaults = True
        elif key == M.SETTING_SAVE:
            pass
        elif key == M.SETTING_CLEAR_FAULTS:
            self.latched.clear()
            self.fourwd_fault = False
            for act in (self.fourwd, self.diff, self.tray):
                act.faulted = False
            self.regen.clear_fault()
        elif key in M.SETTINGS:
            name, _u, _d, lo, hi = M.SETTINGS[key]
            if not lo <= value <= hi:
                status = 2
                value = max(lo, min(hi, value))
            self.settings[name] = value
            self.on_defaults = False
        else:
            status = 1
        self.acks.append({"key": key, "status": status, "value": value})

    def _drive_request(self, v: dict) -> None:
        prev = self._last_drive_req
        self._last_drive_req = dict(v)
        speed_ok = self.speed_known()
        resend_while_unknown = (prev is not None and v["fourwd_req"] == prev["fourwd_req"]
                                and not self.fourwd_known and not self.fourwd.moving)
        if resend_while_unknown and speed_ok and self.speed < self.s("fourwd_max_kmh") \
                and self.inp("in.ignition") and not self.fourwd_fault:
            # Position unknown after boot: a resend may home it (quietly, no reject spam)
            self.fourwd.target = 1.0 if v["fourwd_req"] else 0.0
        if prev is None or v["fourwd_req"] != prev["fourwd_req"]:
            want = 1.0 if v["fourwd_req"] else 0.0
            self.fourwd_wait = None   # a new request replaces (or cancels) a wait
            if want != self.fourwd.target or self.fourwd_fault or not self.fourwd_known:
                reason = self._shift_check(self.s("fourwd_max_kmh"))
                if reason is None and (self.diff.moving or self.diff_wait is not None):
                    reason = "busy"
                if reason is None:
                    self._start_4wd(want)
                elif reason == "too_fast" and self.s("shift_wait_ms") > 0:
                    self.fourwd_wait = (self.t, want)
                else:
                    self.reject(reason)
        if prev is None or v["diff_target"] != prev["diff_target"]:
            want = max(0, min(100, v["diff_target"])) / 100
            self.diff_wait = None
            if abs(want - self.diff.target) > 0.005:
                adding = want > self.diff.pos + 0.02
                reason = self._shift_check(self.s("diff_max_kmh") if adding else 1e9)
                if reason is None and adding and (self.fourwd.moving or self.fourwd_wait is not None):
                    reason = "busy"
                if reason is None:
                    self._start_diff(want)
                elif reason == "too_fast" and self.s("shift_wait_ms") > 0:
                    self.diff_wait = (self.t, want)
                else:
                    self.reject(reason)

    def _shift_check(self, limit_kmh: float) -> str | None:
        if not self.inp("in.ignition"):
            return "ignition_off"
        if not self.speed_known():
            return "speed_unknown"
        if self.speed >= limit_kmh:
            return "too_fast"
        return None

    def _start_4wd(self, want: float) -> None:
        self.fourwd_fault = False
        self.fourwd.faulted = False
        self.latched -= {"fourwd_timeout", "fourwd_overcurrent"}
        self.fourwd.target = want

    def _start_diff(self, want: float) -> None:
        self.diff.faulted = False
        self.latched -= {"diff_timeout", "diff_pot_stuck"}
        self.diff.target = want

    def _wait_tick(self) -> None:
        """Start a waiting request once it's safe; drop it on a hard reason or time-out."""
        wait_s = self.s("shift_wait_ms") / 1000
        if not self.dash_ok() or not self.inp("in.ignition"):
            self.fourwd_wait = self.diff_wait = None   # rule 1 / key-off: drop quietly
        if self.fourwd_wait is not None:
            start, want = self.fourwd_wait
            reason = self._shift_check(self.s("fourwd_max_kmh"))
            if reason is None and self.diff.moving:
                reason = "busy"
            if reason is None:
                self.fourwd_wait = None
                self._start_4wd(want)
            elif reason not in ("too_fast", "busy"):
                self.fourwd_wait = None
                self.reject(reason)
            elif self.t - start >= wait_s:
                self.fourwd_wait = None
                self.reject("wait_timeout")
        if self.diff_wait is not None:
            start, want = self.diff_wait
            reason = self._shift_check(self.s("diff_max_kmh"))
            if reason is None:
                self.diff_wait = None
                self._start_diff(want)
            elif reason != "too_fast":
                self.diff_wait = None
                self.reject(reason)
            elif self.t - start >= wait_s:
                self.diff_wait = None
                self.reject("wait_timeout")

    def _update_throttle_hold(self) -> None:
        shifting = self.fourwd.moving or self.diff.moving
        if not shifting or not self.s("shift_throttle_hold"):
            self.throttle_hold = self.throttle_hold_blocked = False
        elif not self.stopped():
            # Never cut throttle while moving: drop it and keep it off for this shift
            self.throttle_hold, self.throttle_hold_blocked = False, True
        elif not self.throttle_hold_blocked:
            self.throttle_hold = True

    def _hold_request(self, v: dict, now: float) -> None:
        self.last_hold = now
        tray, winch = int(v["tray"]), int(v["winch"])
        armed = bool(v["winch_armed"])
        if armed and not self.winch_armed:
            if not self.speed_known():
                self.reject("speed_unknown")
            elif not self.stopped():
                self.reject("not_stopped")
            else:
                self.winch_armed = True
                self.winch_idle = 0.0
        elif not armed and self.winch_armed and winch == 0 and tray == 0:
            self.winch_armed = False
        new_tray = tray != self._last_hold_vals[0]
        new_winch = winch != self._last_hold_vals[1]
        self._last_hold_vals = (tray, winch)

        if tray:
            reason = None
            if not self.inp("in.ignition"):
                reason = "ignition_off"
            elif not self.speed_known():
                reason = "speed_unknown"
            elif not self.stopped():
                reason = "not_stopped"
            elif self.winch_dir:
                reason = "interlock"
            elif (tray > 0 and self.inp("in.tray_up")) or (tray < 0 and self.inp("in.tray_down")):
                reason = "at_limit"
            if reason:
                tray = 0
                if new_tray:
                    self.reject(reason)
            elif new_tray:
                # The next accepted press clears a latched tray fault (matches the firmware)
                self.latched -= {"tray_overcurrent", "tray_timeout"}
        if winch:
            reason = None
            if not self.winch_armed:
                reason = "not_armed"
            elif self.inp("in.winch_remote"):
                reason = "winch_remote"
            elif not self.speed_known():
                reason = "speed_unknown"
            elif not self.stopped():
                reason = "not_stopped"
            elif self.tray.moving or tray:
                reason = "interlock"
            if reason:
                winch = 0
                if new_winch:
                    self.reject(reason)
        timed = int(v.get("winch_timed_s", 0) or 0)
        if new_winch or not timed:
            self.winch_timed_start = None
            self.winch_timed_done = False
        self.winch_timed_s = timed
        self.hold_tray, self.hold_winch = tray, winch

    # ------------------------------------------------------------ tick
    def step(self, dt: float, now: float) -> None:
        self.t = now
        dash_ok = self.dash_ok()
        hold_ok = dash_ok and now - self.last_hold < self.s("hold_to_run_timeout_ms") / 1000
        if not hold_ok:
            # Frames stopped: treat it as a release, so the next press counts as new
            self.hold_tray = self.hold_winch = 0
            self._last_hold_vals = (0, 0)
            self.winch_timed_s = 0
        if not dash_ok:
            # Rule 1: stop everything that moves, disarm the winch
            self.fourwd.stop()
            self.diff.stop()
            self.winch_armed = False
        if not self.speed_known() and self.hold_winch:
            self.hold_winch = 0

        # --- inputs we can work out ourselves
        self.inputs["in.reverse"] = self.direction == "reverse"
        self.inputs["in.brake"] = self.brake
        self.inputs["in.tray_down"] = self.tray.pos <= 0.001
        self.inputs["in.tray_up"] = self.tray.pos >= 0.999

        # --- brake pedal regen (rule 9)
        self.regen.step(dt, self.settings, pedal_raw=self.pedal_raw, brake_switch=self.inp("in.brake"),
                        speed_kmh=self.speed if self.speed_known() else None,
                        direction=self.direction, soc=self.soc, fourwd=self.fourwd_state(),
                        throttle_pct=self.throttle)

        # --- waiting 4WD / diff requests
        self._wait_tick()

        # --- 4WD: runs to end stop, max run time, current limit
        self.fourwd.jammed = False
        was_moving = self.fourwd.moving
        self.fourwd.drive(dt, run_current=2.5)
        if was_moving and not self.fourwd.moving and not self.fourwd.faulted:
            self.fourwd_known = True
        if "fourwd_overcurrent" in self.bench_faults and self.fourwd.moving:
            self.fourwd.current = 7.5
        if self.fourwd.moving:
            if self.fourwd.current * 10 > self.s("fourwd_overcurrent_da"):
                self.latched.add("fourwd_overcurrent")
                self._fault_actuator(self.fourwd)
                self.fourwd_fault = True
            elif self.fourwd.running_for * 1000 > self.s("fourwd_max_run_ms"):
                self.latched.add("fourwd_timeout")
                self._fault_actuator(self.fourwd)
                self.fourwd_fault = True

        # --- diff: closed loop on the pot
        pot_gone = "pot_disconnected" in self.bench_faults
        self.diff.jammed = "jam_diff" in self.bench_faults
        if pot_gone and self.diff.moving:
            self.latched.add("diff_pot_stuck")
            self._fault_actuator(self.diff)
        self.diff.drive(dt, run_current=3.0)
        if self.diff.current * 10 > self.s("diff_overcurrent_da"):
            self.latched.add("diff_overcurrent")
            self._fault_actuator(self.diff)
        if self.diff.moving and self.diff.running_for * 1000 > self.s("diff_max_run_ms"):
            self.latched.add("diff_timeout")
            if self.diff.jammed:
                self.latched.add("diff_pot_stuck")
            self._fault_actuator(self.diff)

        self._update_throttle_hold()

        # --- tray: hold-to-run, limit switches, current, max run
        if self.hold_tray > 0 and not self.inp("in.tray_up"):
            self.tray.target = 1.0
        elif self.hold_tray < 0 and not self.inp("in.tray_down"):
            self.tray.target = 0.0
        else:
            self.tray.stop()
        self.tray.jammed = "jam_tray" in self.bench_faults
        self.tray.drive(dt, run_current=5.0 if self.hold_tray > 0 else 2.5)
        if self.tray.moving:
            if self.tray.current * 10 > self.s("tray_overcurrent_da"):
                self.latched.add("tray_overcurrent")
                self.tray.stop()
                self.hold_tray = 0
            elif self.tray.running_for * 1000 > self.s("tray_max_run_ms"):
                self.latched.add("tray_timeout")
                self.tray.stop()
        if self.inp("in.tray_up") and self.inp("in.tray_down"):
            self.latched.add("tray_limit_switch")   # both limits at once = broken wire
        else:
            self.latched.discard("tray_limit_switch")

        # --- winch with dead time between directions
        want = self.hold_winch if self.winch_armed else 0
        timed = self.winch_timed_s
        if timed and self.winch_timed_done:
            want = 0
        if want != self.winch_dir:
            if self.winch_dir != 0 and want != 0:
                want = 0  # never straight from in to out
            if self.winch_dir != 0 and want == 0:
                self.winch_dead_until = now + self.s("winch_dead_time_ms") / 1000
            if want != 0 and now < self.winch_dead_until:
                want = 0
            self.winch_dir = want
        if timed and not self.winch_timed_done:
            # Timed pull: the control box times it itself, capped at its own max
            if self.winch_dir and self.winch_timed_start is None:
                self.winch_timed_start = now
            elif not self.winch_dir and self.winch_timed_start is not None:
                self.winch_timed_done = True   # cut short: needs a new press
            secs = min(timed, self.s("winch_timed_max_s"))
            if self.winch_timed_start is not None and now - self.winch_timed_start >= secs:
                self.winch_timed_done = True
                self.winch_dir = 0
                self.winch_dead_until = now + self.s("winch_dead_time_ms") / 1000
        if self.winch_armed:
            self.winch_idle = 0.0 if self.winch_dir else self.winch_idle + dt
            if self.winch_idle > self.s("winch_auto_disarm_s"):
                self.winch_armed = False
        if self.inp("in.winch_remote") and self.winch_dir:
            self.latched.add("winch_interlock")
            self.winch_dir = 0
        else:
            self.latched.discard("winch_interlock")

        # --- 12 V and temperature
        winch_a = {0: 0, 1: 180, -1: 60}[self.winch_dir]
        self.aux_12v += ((13.6 - winch_a * 0.006) - self.aux_12v) * min(1, dt * 5)
        if self.bench_aux_mv:
            self.aux_12v = self.bench_aux_mv / 1000
        self.temp += ((32 + winch_a * 0.03) - self.temp) * dt * 0.02

        # --- key-off and power hold
        if not self.inp("in.ignition"):
            if self.ignition_off_at is None:
                self.ignition_off_at = now
        else:
            self.ignition_off_at = None

        self._update_lights()

    def _fault_actuator(self, act: Actuator) -> None:
        act.stop()
        act.faulted = True

    def _update_lights(self) -> None:
        r = self.lights_req
        mask = self.s("light_dimmable_mask")
        fronts = [int(r[f"front_{n}"]) for n in range(1, 5)]
        eff = M.LIGHT_EFFECT.get(int(r["effect"]), "none")
        t = self.t
        if eff == "strobe":
            fronts = [b if int(t * 8) % 2 == 0 else 0 for b in fronts]
        elif eff == "chase":
            k = int(t * 6) % 4
            fronts = [b if i == k else 0 for i, b in enumerate(fronts)]
        elif eff == "outside_only":
            fronts = [fronts[0], 0, 0, fronts[3]]
        elif eff == "inside_only":
            fronts = [0, fronts[1], fronts[2], 0]
        elif eff == "sos":
            # ... --- ... in 100 ms units
            pattern = "1010100011101110111000101010000000"
            on = pattern[int(t * 10) % len(pattern)] == "1"
            fronts = [b if on else 0 for b in fronts]
        elif eff == "breathe":
            k = 0.5 + 0.5 * math.sin(t * 2)
            if mask & 0b1111:
                fronts = [round(b * k) for b in fronts]
        levels = fronts + [int(r["interior"])]
        # On/off-only bars: anything above 0 is full on
        levels = [lvl if mask & (1 << i) else (255 if lvl else 0) for i, lvl in enumerate(levels)]
        rear = bool(r["rear_on"]) or (bool(r["rear_auto"]) and self.inp("in.reverse"))
        self.lights_out = {
            **{f"front_{n}": levels[n - 1] for n in range(1, 5)},
            "interior": levels[4], "effect": int(r["effect"]), "rear": rear,
        }

    # ------------------------------------------------------------ outputs
    def relays(self) -> dict[str, bool]:
        lo = self.lights_out
        any_front = any(lo.get(f"front_{n}", 0) for n in range(1, 5))
        ign = self.inp("in.ignition")
        holding = ign or (self.ignition_off_at is not None
                          and self.t - self.ignition_off_at < self.s("shutdown_wait_s"))
        return {
            "light.rear": bool(lo.get("rear")),
            "trailer.tail": any_front,
            "trailer.brake": self.inp("in.brake") or self.regen.out.brake_light,
            "winch.in": self.winch_dir == 1,
            "winch.out": self.winch_dir == -1,
            "winch.isolator": self.winch_armed,
            "aux.accessory": ign,
            "power.hold": holding,
        }

    def faults(self) -> set[str]:
        f = set(self.latched)
        if not self.dash_ok():
            f.add("dash_link")
        if not self.speed_known():
            f.add("speed_unknown")
        if self.aux_12v * 1000 < self.s("low_12v_mv"):
            f.add("low_12v")
        if "io_bus_dead" in self.bench_faults:
            f.add("io_bus")
        if self.temp > 70:
            f.add("pico_hot")
        if self.regen.fault and self.s("brake_regen_on"):
            f.add("brake_pedal")
        return f

    def state(self) -> str:
        if self.t < 0.5:
            return "boot"
        return "degraded" if self.faults() else "ok"

    def fourwd_state(self) -> str:
        if self.fourwd_fault:
            return "fault"
        if self.fourwd.moving:
            return "to_4wd" if self.fourwd.target > self.fourwd.pos else "to_2wd"
        if not self.fourwd_known:
            return "unknown"
        return "4wd" if self.fourwd.pos > 0.5 else "2wd"

    def parked(self) -> bool:
        return self.stopped() and (self.direction == "neutral" or self.inp("in.park"))

    def tray_state(self) -> str:
        if {"tray_overcurrent", "tray_timeout", "tray_limit_switch"} & self.latched:
            return "fault"
        if self.tray.moving:
            return "raising" if self.tray.target > self.tray.pos else "lowering"
        if self.inp("in.tray_down"):
            return "down"
        if self.inp("in.tray_up"):
            return "up"
        return "mid"

    def frames(self) -> list[tuple[str, dict]]:
        inputs = {**self.inputs, **self.forced}
        lo = self.lights_out
        rg = self.regen.out
        out = [
            ("PICO_STATUS", {
                "fault_bits": M.names_to_bits(self.faults(), M.FAULT_BITS),
                "inputs": M.names_to_bits([n for n, on in inputs.items() if on], M.INPUT_BITS),
                "state": M.enum_value(M.PICO_STATE, self.state()),
                "on_defaults": int(self.on_defaults),
                "fourwd_wait": int(self.fourwd_wait is not None),
                "diff_wait": int(self.diff_wait is not None),
                "throttle_hold": int(self.throttle_hold),
                "reject_reason": M.enum_value(M.REJECT_REASON, self.reject_reason),
                "reject_count": self.reject_count,
                "winch_armed": int(self.winch_armed),
                "speed_valid": int(self.speed_known()),
                "reverse_active": int(self.inp("in.reverse")),
                "shutdown_request": int(not self.inp("in.ignition")),
                "parked": int(self.parked()),
                "speed": min(254, round(self.speed)) if self.speed_known() else 255,
            }),
            ("PICO_OUTPUTS", {
                "relays": M.names_to_bits([n for n, on in self.relays().items() if on], M.RELAY_BITS),
                **{f"front_{n}": lo[f"front_{n}"] for n in range(1, 5)},
                "interior": lo["interior"], "effect": lo["effect"],
            }),
            ("PICO_ACTUATORS", {
                "diff_pct": self.diff.pos * 100,
                "fourwd": M.enum_value(M.FOURWD_STATE, self.fourwd_state()),
                "tray": M.enum_value(M.TRAY_STATE, self.tray_state()),
                "diff_current": self.diff.current,
                "fourwd_current": self.fourwd.current,
                "tray_current": self.tray.current,
                "tray_pct": self.tray.pos * 100,
                "diff_target": (self.diff_wait[1] if self.diff_wait else self.diff.target) * 100,
            }),
            ("PICO_POWER", {
                "aux_12v": self.aux_12v, "pico_temp": self.temp,
                "diff_pot_raw": self.s("diff_pot_min_raw")
                + self.diff.pos * (self.s("diff_pot_max_raw") - self.s("diff_pot_min_raw")),
                "fw_major": FW_VERSION[0], "fw_minor": FW_VERSION[1],
                "winch_idle_s": min(255, self.winch_idle) if self.winch_armed else 0,
            }),
            ("PICO_REGEN", {
                "pedal_pct": rg.pedal_pct, "request_pct": rg.request_pct,
                "state": M.enum_value(M.REGEN_STATE, rg.state),
                "limit": M.enum_value(M.REGEN_LIMIT, rg.limit),
                "pedal_raw": self.pedal_raw or 0, "brake_light": int(rg.brake_light),
            }),
        ]
        return out
