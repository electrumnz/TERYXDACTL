"""Brake pedal regen: the control box's rules, in plain Python.

The first part of the brake pedal asks the Shinegle for regen (motor braking)
before, and on top of, the normal hydraulic brakes. See docs/brake-regen.md.

This runs on the control box (the Pico), never on the dash, and it is OFF by
default (setting ``brake_regen_on`` = 0) until the real Shinegle has been checked
for a way to take a regen request. The simulator's control box uses this file;
the Pico firmware must copy it rule for rule when it gets the feature.

Rules (all of them can only ever LOWER the regen request, never raise it):

 1. Feature off -> no request, state "off".
 2. Pedal sensor reading outside its calibrated range (broken wire, short, not
    calibrated) -> no request, fault latched until "clear faults".
 3. Pedal reads well down but the stock brake switch says "not pressed" for
    0.5 s -> sensor can't be trusted, same as rule 2.
 4. Pedal travel below ``brake_regen_start_pct`` -> nothing. Then it ramps
    linearly to 100 % at ``brake_regen_full_pct`` and holds there.
 5. Times the strength setting ``brake_regen_pct``.
 6. Speed unknown, not in forward, or throttle on (left-foot braking on a
    climb is a real off-road trick, so the motor isn't made to fight itself)
    -> nothing.
 7. Fades to nothing below ``brake_regen_fade_kmh`` (motor braking can't hold a
    stop, and it goes jerky near zero). The hydraulic brakes do the last bit.
 8. Battery nearly full -> fades from 100 % at 90 % charge to nothing at 98 %.
 9. Not in 4WD (2WD, moving, unknown) -> times ``brake_regen_2wd_pct``, because
    then it only brakes the rear wheels and can lock them on gravel.
10. The request rises at most 250 %/s (no snatch). It drops straight away.

The hydraulic brakes are never touched by any of this: the sensor only watches
the pedal, so if all of this fails you still have normal brakes.
"""

from __future__ import annotations

from dataclasses import dataclass

REGEN_STATE = {0: "off", 1: "ready", 2: "active", 3: "limited", 4: "sensor_fault"}
REGEN_LIMIT = {
    0: "none",
    1: "low_speed",
    2: "speed_unknown",
    3: "not_forward",
    4: "battery_full",
    5: "two_wd",
    6: "sensor",
    7: "throttle",
}

PLAUSIBLE_AFTER_S = 0.5     # rule 3
RISE_PER_S = 250.0          # rule 10, % per second
BRAKE_LIGHT_PCT = 10.0      # regen request that lights the brake lights (TBC on the vehicle)
THROTTLE_OFF_PCT = 5.0      # rule 6
SOC_FADE_START = 90.0       # rule 8
SOC_FADE_END = 98.0


@dataclass
class RegenOut:
    pedal_pct: float = 0.0
    request_pct: float = 0.0     # 0-100 % of the Shinegle's max regen
    state: str = "off"
    limit: str = "none"
    brake_light: bool = False


@dataclass
class BrakeRegen:
    fault: bool = False          # latched sensor fault (rule 2/3)
    _implausible_for: float = 0.0
    _last: float = 0.0
    out: RegenOut = None  # type: ignore[assignment]

    def __post_init__(self):
        self.out = RegenOut()

    def clear_fault(self) -> None:
        self.fault = False
        self._implausible_for = 0.0

    def pedal_pct(self, raw: int | None, lo: int, hi: int) -> float | None:
        """Pedal travel 0-100 %, or None if the reading can't be trusted."""
        span = hi - lo
        if raw is None or span < 1000:
            return None
        if raw < lo - 0.05 * span or raw > hi + 0.10 * span:
            return None
        return max(0.0, min(100.0, (raw - lo) * 100.0 / span))

    def step(self, dt: float, s: dict, *, pedal_raw: int | None, brake_switch: bool,
             speed_kmh: float | None, direction: str, soc: float | None, fourwd: str,
             throttle_pct: float = 0.0) -> RegenOut:
        out = RegenOut()
        if not s.get("brake_regen_on", 0):
            self._last = 0.0
            self.out = out
            return out

        pct = self.pedal_pct(pedal_raw, s["brake_pedal_min_raw"], s["brake_pedal_max_raw"])
        if pct is None:
            self.fault = True
        else:
            out.pedal_pct = pct
            # Rule 3: pedal is well past the regen zone but the brake switch says it's up
            if pct >= max(s["brake_regen_full_pct"], 40) and not brake_switch:
                self._implausible_for += dt
                if self._implausible_for >= PLAUSIBLE_AFTER_S:
                    self.fault = True
            else:
                self._implausible_for = 0.0
        if self.fault:
            out.state, out.limit = "sensor_fault", "sensor"
            self._last = 0.0
            self.out = out
            return out

        start, full = s["brake_regen_start_pct"], s["brake_regen_full_pct"]
        if out.pedal_pct <= start or full <= start:
            want = 0.0
        else:
            want = min(1.0, (out.pedal_pct - start) / (full - start)) * 100.0
        want *= s["brake_regen_pct"] / 100.0
        pedal_wants = want > 0

        limit = "none"
        if speed_kmh is None:
            want, limit = 0.0, "speed_unknown"
        elif direction != "forward":
            want, limit = 0.0, "not_forward"
        elif throttle_pct > THROTTLE_OFF_PCT:
            want, limit = 0.0, "throttle"
        else:
            fade = s["brake_regen_fade_kmh"]
            if fade > 0 and speed_kmh < fade:
                want *= max(0.0, speed_kmh / fade)
                limit = "low_speed"
            if soc is not None and soc > SOC_FADE_START:
                k = max(0.0, (SOC_FADE_END - soc) / (SOC_FADE_END - SOC_FADE_START))
                if k < 1:
                    want *= k
                    limit = "battery_full"
            if fourwd != "4wd" and s["brake_regen_2wd_pct"] < 100:
                want *= s["brake_regen_2wd_pct"] / 100.0
                if limit == "none":
                    limit = "two_wd"

        # Rule 10: rise limited, fall straight away
        want = min(want, self._last + RISE_PER_S * dt)
        self._last = want
        out.request_pct = round(want, 2)
        out.limit = limit if pedal_wants else "none"
        if not pedal_wants:
            out.state = "ready"
        else:   # 2WD scaling is normal running, not a warning
            out.state = "active" if limit in ("none", "two_wd") else "limited"
        out.brake_light = want >= BRAKE_LIGHT_PCT
        self.out = out
        return out
