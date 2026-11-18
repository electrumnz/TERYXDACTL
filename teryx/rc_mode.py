"""RC mode for beach and ramp launching: the rules the RC box follows.

See docs/rc-beach-launch.md. The RC box is a second Pico 2 that sits between
the radio receiver and the Teryx's driving inputs (steering torque sensor,
throttle wiper, forward/reverse wires, brake actuator). It only takes over
while ALL of these hold, every tick:

* a fresh radio packet (no older than ``link_timeout_s``) with no failsafe flag,
* a fresh "RC allowed" permit from the main control box Pico (same timeout),
* the dead-man switch on the remote held down,
* the e-stop on the remote not pressed.

Lose any one and it stops: throttle 0, brake on, neutral. Hard-wired relays
put the real steering sensor, pedal and F-N-R switch back if the RC box itself
dies (that part is hardware, see the doc). This file is the readable spec. The
RC box firmware has to behave the same, and tests/test_rc_mode.py checks it.

Speeds are km/h. ``motor_kmh`` is what the Shinegle says (worked out from the
motor, so it spins with the wheels). ``ground_kmh`` is GPS speed over the
ground. On sand the two pulling apart is how we spot wheelspin.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# States
OFF = "off"            # RC not on. Relays out, the Teryx drives normally
ARMED = "armed"        # RC on, relays in, holding still on the brake
DRIVING = "driving"
HOLD = "hold"          # stopped on the brake because something isn't right
FAULT = "fault"        # needs a re-arm from the dash (steering readback, brake fault)

NEUTRAL, FORWARD, REVERSE = 0, 1, -1

DEFAULTS = {
    "link_timeout_s": 0.20,     # ELRS / SIYI failsafe is far slower than this, so we time out ourselves
    "fwd_cap_kmh": 5.0,         # Auckland Council asks for 10 km/h max when launching. RC goes slower
    "rev_cap_kmh": 3.0,
    "overspeed_brake_kmh": 1.5,  # this far over the cap: brake as well as cut throttle
    "stopped_kmh": 0.5,
    "spin_motor_kmh": 3.0,      # wheels turning at least this fast...
    "spin_ground_kmh": 0.5,     # ...while the ground speed is below this...
    "spin_s": 1.5,              # ...for this long = digging in. Cut and stop
    "stall_throttle": 0.5,      # throttle at least this...
    "stall_s": 3.0,             # ...and nothing moving for this long = stuck. Cut and stop
    "steer_rate_deg_s": 180.0,  # how fast the wanted steering angle can move
    "steer_max_deg": 400.0,     # wheel angle at full lock, TBC on the Teryx
    "steer_gain": 0.004,        # torque command per degree of error (tune on the bench)
    "trq_span_v": 1.0,          # torque sensor swing from centre at full command. TBC: measure the column
    "trq_centre_v": 2.5,        # Toyota: TRQ1 2.3-2.7 V at centre, TRQ1 and TRQ2 within 0.3 V
    "trq_readback_tol_v": 0.15,
    # Driving from a phone over 4G (getting it back if it's pinched). Off unless Sam turns it on
    # with his PIN. Lag over 4G is far worse and jumpier than local Wi-Fi, so it's crawl only.
    "allow_4g": False,
    "cap_4g_kmh": 2.0,
    "max_rtt_4g_s": 0.30,       # operators struggle from about 300 ms round trip (Frontiers review)
    "link_timeout_4g_s": 0.50,  # 4G jitter would trip 200 ms all the time. 0.5 s at 2 km/h is 28 cm
}

LINKS = ("radio", "wifi", "4g", "bt")   # bt: a Bluetooth pad paired to the Pi (rc_pad.py)


@dataclass
class Radio:
    """One decoded packet from the receiver (SBUS or CRSF)."""
    t: float                    # when it arrived
    steer: float = 0.0          # -1 full left .. +1 full right
    throttle: float = 0.0       # 0..1, right trigger (or pistol-grip trigger pulled)
    brake: float = 0.0          # 0..1, left trigger (or pistol-grip trigger pushed)
    direction: int = NEUTRAL    # 3-position switch: -1 R, 0 N, +1 F
    deadman: bool = False       # sprung button or trigger, must be held
    estop: bool = False
    winch: int = 0              # -1 out, 0, +1 in (hold-to-run buttons)
    drive: float | None = None  # stick mode: -1 full back .. +1 full forward. None = trigger mode
    failsafe: bool = False      # receiver says it has lost the transmitter
    link: str = "radio"         # radio (handheld's own link), wifi (phone on the Teryx's hotspot), 4g, bt (pad on the Pi)
    rtt_s: float | None = None  # round trip the Pi measured to the phone (wifi and 4g)
    video_ok: bool = True       # the phone says its camera picture is live and fresh


@dataclass
class Permit:
    """The main control box Pico says RC is allowed (sent at 10 Hz or more)."""
    t: float
    allowed: bool = True
    reason: str = ""            # why not, when not


@dataclass
class Vehicle:
    motor_kmh: float = 0.0
    ground_kmh: float | None = None   # GPS. None = no fix, so no wheelspin check
    parked: bool = True               # park brake on and stopped
    wet: int = 0                      # water probes: 0 dry, 1 at axle-cap height, 2 higher
    brake_ok: bool = True             # brake actuator fitted and passed its self-test
    trq_readback: tuple[float, float] | None = None  # measured DAC volts (TRQ1, TRQ2)


@dataclass
class Out:
    relays: bool = False        # True = RC box drives steering, throttle and F-N-R
    throttle: float = 0.0
    direction: int = NEUTRAL
    brake: float = 1.0          # 0 off .. 1 full
    steer_target_deg: float = 0.0
    trq_v: tuple[float, float] = (2.5, 2.5)
    winch: int = 0              # request passed to the main Pico's winch rules
    state: str = OFF
    reason: str = ""
    warn: list[str] = field(default_factory=list)


class RcBox:
    def __init__(self, settings: dict | None = None):
        self.s = dict(DEFAULTS, **(settings or {}))
        self.state = OFF
        self.reason = ""
        self.direction = NEUTRAL
        self.steer_target = 0.0
        self.steer_actual = 0.0
        self.spin_for = 0.0
        self.stall_for = 0.0
        self.need_recentre = False   # after a cut, throttle must go back to 0 before it works again
        self.last_t: float | None = None
        self.stick_centred = True    # stick mode: has the stick been back to the middle since braking?

    # ---- arming ------------------------------------------------------------
    def arm(self, now: float, radio: Radio | None, permit: Permit | None, veh: Vehicle) -> str:
        """Called when RC mode is switched on (dash, then confirmed on the remote).
        Returns "" when armed, or why not."""
        why = self._link_problem(now, radio, permit)
        if why:
            return why
        if radio.link == "4g" and not self.s["allow_4g"]:
            return "4g_off"
        if not veh.parked:
            return "not_parked"
        if not veh.brake_ok:
            return "no_brake"        # no RC without a working brake actuator, ever
        if radio.deadman:
            return "deadman_held"    # must be let go at arm time, so a stuck button can't drive
        if radio.throttle > 0.05 or (radio.drive is not None and abs(radio.drive) > 0.05):
            return "throttle_not_zero"
        if radio.direction != NEUTRAL:
            return "not_neutral"
        self.state, self.reason = ARMED, ""
        self.direction = NEUTRAL
        self.need_recentre = False
        self.spin_for = self.stall_for = 0.0
        self.last_t = now
        return ""

    def disarm(self) -> None:
        self.state, self.reason = OFF, ""

    # ---- every tick (20 ms on the RC box) ----------------------------------
    def tick(self, now: float, radio: Radio | None, permit: Permit | None, veh: Vehicle,
             steer_angle_deg: float = 0.0) -> Out:
        dt = 0.0 if self.last_t is None else max(0.0, now - self.last_t)
        self.last_t = now
        self.steer_actual = steer_angle_deg
        if radio is not None and radio.drive is not None:
            radio = self._map_stick(radio, veh.motor_kmh)
        out = Out(state=self.state)
        if self.state == OFF:
            return out
        out.relays = True

        if self.state == FAULT:
            return self._stop(out, self.reason)

        # 1. anything that means "stop now"
        why = self._link_problem(now, radio, permit)
        if not why and radio.estop:
            why = "estop"
        if not why and not veh.brake_ok:
            why = "brake_fault"
        if not why and veh.trq_readback is not None and self._readback_bad(veh.trq_readback):
            self.state, self.reason = FAULT, "steer_readback"
            out.relays = False   # hand steering back to the real sensor
            return self._stop(out, self.reason)
        if why:
            self.state, self.reason = HOLD, why
            self.need_recentre = True
            return self._stop(out, why)
        if not radio.deadman:
            self.state, self.reason = HOLD, "deadman"
            self.need_recentre = True
            return self._stop(out, "deadman", steer=radio, dt=dt)

        # dead-man held and link good: back to work once the throttle has been let go
        if self.need_recentre:
            if radio.throttle > 0.05:
                if self.reason == "deadman":   # dead-man is back, so the stick is what's stopping us now
                    self.reason = "recentre"
                return self._stop(out, self.reason, steer=radio, dt=dt)
            self.need_recentre = False
        self.state, self.reason = DRIVING, ""

        # 2. steering follows the stick, rate limited
        self._steer(radio, dt, out)

        stopped = veh.motor_kmh < self.s["stopped_kmh"]
        on_4g = radio.link == "4g"

        # 3. winch: only when stopped, in neutral and not on the throttle
        if radio.winch:
            if stopped and radio.throttle < 0.05 and radio.direction == NEUTRAL:
                out.winch = radio.winch
                out.direction = self.direction = NEUTRAL
                out.brake, out.throttle = 1.0, 0.0
                out.state = self.state
                return out
            out.warn.append("winch_needs_stop")

        # 4. direction only changes when stopped and off the throttle
        if radio.direction != self.direction:
            if stopped and radio.throttle < 0.05:
                self.direction = radio.direction
            else:
                out.warn.append("stop_to_change_direction")
        out.direction = self.direction

        throttle = radio.throttle if self.direction != NEUTRAL else 0.0
        if radio.brake > 0.05:
            throttle = 0.0           # brake trigger always beats the go trigger

        # 5. water: no more reverse once the probe at axle-cap height is wet
        if self.direction == REVERSE and veh.wet >= 1:
            throttle = 0.0
            out.warn.append("too_deep" if veh.wet >= 2 else "water_limit")

        # 6. speed cap
        cap = self.s["fwd_cap_kmh"] if self.direction == FORWARD else self.s["rev_cap_kmh"]
        if on_4g:
            cap = min(cap, self.s["cap_4g_kmh"])
        over = veh.motor_kmh - cap
        if over > 0:
            throttle = 0.0
            out.warn.append("speed_cap")

        # 7. digging in (wheelspin) and stuck (stall)
        if throttle > 0.2 and veh.ground_kmh is not None \
                and veh.motor_kmh >= self.s["spin_motor_kmh"] and veh.ground_kmh < self.s["spin_ground_kmh"]:
            self.spin_for += dt
        else:
            self.spin_for = 0.0
        if throttle >= self.s["stall_throttle"] and veh.motor_kmh < 0.3 \
                and (veh.ground_kmh is None or veh.ground_kmh < 0.3):
            self.stall_for += dt
        else:
            self.stall_for = 0.0
        if self.spin_for >= self.s["spin_s"] or self.stall_for >= self.s["stall_s"]:
            why = "wheelspin" if self.spin_for >= self.s["spin_s"] else "stalled"
            self.spin_for = self.stall_for = 0.0
            self.state, self.reason = HOLD, why
            self.need_recentre = True
            return self._stop(out, why, steer=radio, dt=0.0)

        out.throttle = max(0.0, min(1.0, throttle))
        brake = 0.0
        if over > self.s["overspeed_brake_kmh"]:
            brake = min(1.0, 0.3 + 0.2 * over)
        elif out.throttle == 0.0 and stopped:
            brake = 1.0              # sitting still: hold it on the brake (slope, waves)
        out.brake = max(brake, max(0.0, min(1.0, radio.brake)))
        out.state = self.state
        return out

    # ---- helpers -----------------------------------------------------------
    def _map_stick(self, radio: Radio, motor_kmh: float) -> Radio:
        """One stick for go and stop, like an RC car: push forward to go forward,
        pull back to go backward, and pull against the way you're moving to brake.
        Changing direction needs a full stop AND the stick back in the middle first,
        so braking hard to a stop never rolls straight on into reverse."""
        dz = 0.05
        v = max(-1.0, min(1.0, radio.drive))
        moving = motor_kmh >= self.s["stopped_kmh"]
        want = FORWARD if v > dz else REVERSE if v < -dz else NEUTRAL
        thr = brk = 0.0
        direction = self.direction
        if abs(v) <= dz:
            self.stick_centred = True
        elif moving and self.direction != NEUTRAL and want != self.direction:
            brk = abs(v)                 # pulling against the way we're going = brake
            self.stick_centred = False
        elif want == self.direction:
            thr = abs(v)
        elif not moving and self.stick_centred:
            direction = want             # stopped and came back through the middle: swap
            thr = abs(v)
        else:
            brk = abs(v)                 # stopped but still holding from the brake: keep braking
        if direction != self.direction and not moving:
            self.direction = direction
        return Radio(t=radio.t, steer=radio.steer, throttle=thr, brake=max(brk, radio.brake),
                     direction=self.direction, deadman=radio.deadman, estop=radio.estop,
                     winch=radio.winch, failsafe=radio.failsafe, link=radio.link,
                     rtt_s=radio.rtt_s, video_ok=radio.video_ok)

    def _link_problem(self, now: float, radio: Radio | None, permit: Permit | None) -> str:
        to = self.s["link_timeout_s"]
        rto = self.s["link_timeout_4g_s"] if radio is not None and radio.link == "4g" else to
        if radio is None or now - radio.t > rto or radio.failsafe or radio.link not in LINKS:
            return "radio_lost"
        if permit is None or now - permit.t > to:
            return "control_box_lost"
        if radio.link == "4g":
            if not self.s["allow_4g"]:
                return "4g_off"
            if radio.rtt_s is None or radio.rtt_s > self.s["max_rtt_4g_s"]:
                return "lag"
            if not radio.video_ok:
                return "no_video"

        if not permit.allowed:
            return permit.reason or "not_allowed"
        return ""

    def _stop(self, out: Out, why: str, steer: Radio | None = None, dt: float = 0.0) -> Out:
        out.throttle = 0.0
        out.brake = 1.0
        out.direction = NEUTRAL
        out.winch = 0
        out.state, out.reason = self.state, why
        if steer is not None and out.relays:
            self._steer(steer, dt, out)   # still steer while held: helps line up the trailer
        else:
            out.trq_v = (self.s["trq_centre_v"],) * 2
        return out

    def _steer(self, radio: Radio, dt: float, out: Out) -> None:
        want = max(-1.0, min(1.0, radio.steer)) * self.s["steer_max_deg"]
        step = self.s["steer_rate_deg_s"] * dt
        d = want - self.steer_target
        self.steer_target += max(-step, min(step, d))
        out.steer_target_deg = self.steer_target
        cmd = max(-1.0, min(1.0, (self.steer_target - self.steer_actual) * self.s["steer_gain"]))
        out.trq_v = trq_volts(cmd, self.s["trq_centre_v"], self.s["trq_span_v"])

    def _readback_bad(self, measured: tuple[float, float]) -> bool:
        tol = self.s["trq_readback_tol_v"]
        c = self.s["trq_centre_v"]
        # the two lines must mirror each other about the centre, like a real Toyota sensor
        return abs((measured[0] - c) + (measured[1] - c)) > tol


def trq_volts(cmd: float, centre: float = 2.5, span: float = 1.0) -> tuple[float, float]:
    """Fake torque sensor output for a command of -1 (full left) .. +1 (full right).
    TRQ1 and TRQ2 move in opposite directions about the centre, so the column ECU's
    "do the two agree" check passes. Span is TBC until the Aqua column is measured."""
    cmd = max(-1.0, min(1.0, cmd))
    return (round(centre + cmd * span, 4), round(centre - cmd * span, 4))
