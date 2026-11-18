"""Every other light (stock lamps, floods, beacon, trailer) and the light show.

The control box's rules, in plain Python. The simulator's control box uses this
file and the Pico firmware copies it rule for rule (firmware/control-box/src/core/
lights.c). The four front bars and the cabin bar keep their own code (0x701 and
its effects); the light show drives them too. See docs/lights.md.

Rules:
 1. Brake pressed -> both brake lamps and the trailer stop pin at FULL, always,
    whatever else is going on (show, lock, dimming). The brake switch also feeds
    the lamps through diodes in the wiring, so they work with the Pico dead too.
 2. Low and high beam never on together on one side. High wins.
 3. Moving (or speed unknown) -> headlights and tails don't dim: anything above
    off is full. Dimming them is a parked thing.
 4. Tails come on by themselves with any headlight or front bar.
 5. Beacon flashes at a fixed 3 Hz (NZ Vehicle Lighting Rule 11.1(2): 2 to 4 Hz).
    The white side takes turns with the amber, and only while stopped: on the
    road only red or amber may show to the rear.
 6. Rear floods: on, or on by themselves in reverse (setting on the dash). In
    reverse they're always full.
 7. The trailer bar is only live while the trailer plug is in.
 8. Locked (docs/vehicle-lock.md) -> everything off except rule 1.
 9. Key on but no dash (Pi not up yet, or gone quiet) -> low beams and tails on
    at full, so you're never left in the dark with no way to turn them on. The
    Teryx has no headlight switch; a hidden backup toggle in the wiring does the
    same thing with the control box dead.
10. The light show only runs with the key on, the park brake on, the Teryx known
    to be stopped (speed signal there and under 0.5 km/h), the dash talking and
    not locked. Any of those goes and the show stops at once. Never while driving.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Order matters: it's the order of the CAN nibbles in 0x717 and the PCA9685 map.
LAMPS = ("head_l_low", "head_l_high", "head_r_low", "head_r_high",
         "tail_l", "brake_l", "tail_r", "brake_r",
         "trailer_tail", "trailer_stop", "flood_l", "flood_r", "beacon", "trailer_bar", "beacon_white")
FRONT = ("front_1", "front_2", "front_3", "front_4", "interior")   # 0x701 lights
LIGHT_SHOW = {0: "none", 1: "wave", 2: "breathe", 3: "roar", 4: "party"}
SHOW_TEXT = {"wave": "Wave", "breathe": "Breathe", "roar": "Roar", "party": "Party"}

BEACON_PERIOD_MS = 333        # 3 Hz
BEACON_ON_MS = 167
SHOW_PERIOD_MS = {1: 2000, 2: 3000, 3: 8000, 4: 2000}

# Where each lamp sits, left (-1) to right (+1), for the sweeps.
_X = {"head_l_low": -1.0, "front_1": -0.6, "front_2": -0.2, "front_3": 0.2, "front_4": 0.6,
      "head_r_low": 1.0, "tail_l": -1.0, "flood_l": -0.6, "trailer_tail": 0.0, "trailer_bar": 0.0,
      "flood_r": 0.6, "tail_r": 1.0, "beacon_white": 0.0, "brake_l": -1.0, "brake_r": 1.0, "beacon": 0.0, "interior": 0.0,
      "head_l_high": -1.0, "head_r_high": 1.0, "trailer_stop": 0.0}
_RED = {"tail_l", "tail_r", "brake_l", "brake_r", "trailer_tail", "trailer_stop"}
_HIGH = {"head_l_high", "head_r_high"}
_LEFT = {"head_l_low", "front_1", "front_2", "tail_l", "brake_l", "flood_l"}
_RIGHT = {"head_r_low", "front_3", "front_4", "tail_r", "brake_r", "flood_r"}


def _tri(t: int, period: int) -> int:
    """0 -> 255 -> 0 over one period."""
    p = t % period
    half = period // 2
    return (p * 255 // half) if p < half else ((period - p) * 255 // half)


def show_level(show: int, lamp: str, t: int) -> int:
    """0-255 for one lamp, t ms into the show. Integer maths only, so the C copy matches."""
    if show == 1:     # wave: a soft spot of light sweeps left to right and back
        period = SHOW_PERIOD_MS[1]
        pos = _tri(t, period) * 24 // 255 - 12          # -12 .. +12 (tenths)
        if lamp in _HIGH or lamp in ("brake_l", "brake_r", "trailer_stop"):
            return 0
        if lamp in ("beacon", "beacon_white"):
            return 255 if -2 <= pos <= 2 else 0
        if lamp == "interior":
            return 60
        x = int(_X[lamp] * 10)
        d = abs(x - pos)
        return max(0, 255 - d * 255 // 5)
    if show == 2:     # breathe: everything fades up and down, the reds the other way
        lvl = _tri(t, SHOW_PERIOD_MS[2])
        if lamp in _HIGH:
            return 0
        return 255 - lvl if lamp in _RED else lvl
    if show == 3:     # roar: red glow, eyes open, roar, heartbeat, fade out
        t %= SHOW_PERIOD_MS[3]
        if t < 2000:
            return t * 255 // 2000 if lamp in _RED else 0
        if t < 3000:
            if lamp in _RED:
                return 255
            if lamp in ("head_l_low", "head_r_low"):
                return (t - 2000) * 255 // 1000
            return 0
        if t < 3800:
            if lamp in ("head_l_low", "head_r_low"):
                return 0
            if lamp == "interior":
                return 255
            return 255 if ((t - 3000) // 50) % 2 == 0 else 0      # 10 Hz strobe
        if t < 6000:
            if lamp in _HIGH:
                return 0
            beat = (t - 3800) % 900
            return 255 if beat < 100 or 250 <= beat < 350 else 40
        if lamp in _HIGH:
            return 0
        return (8000 - t) * 255 // 2000 // (1 if lamp in _RED else 4)
    if show == 4:     # party: left and right swap at 4 Hz, the bars chase, beacon on the beat
        step = t // 125
        if lamp in _HIGH or lamp == "interior":
            return 0
        if lamp == "beacon":
            return 255 if step % 4 == 0 else 0
        if lamp == "beacon_white":
            return 255 if step % 4 == 2 else 0
        if lamp in ("front_1", "front_2", "front_3", "front_4"):
            return 255 if int(lamp[-1]) - 1 == step % 4 else 0
        if lamp in _LEFT:
            return 255 if step % 2 == 0 else 0
        if lamp in _RIGHT:
            return 255 if step % 2 == 1 else 0
        return 255 if step % 2 == 0 else 0
    return 0


@dataclass
class LightsReq:
    """What the dash asks for on 0x706 (plus the rear bits of 0x701)."""
    head_low: int = 0
    head_high: int = 0
    tail: int = 0          # 0 = automatic (on with any headlight or front bar)
    rear: int = 0          # rear flood level when on, 0 = full
    trailer_bar: int = 0
    beacon: int = 0
    show: int = 0
    beacon_white: int = 0
    rear_on: bool = False
    rear_auto: bool = True


@dataclass
class LightsState:
    brake: bool = False
    reverse: bool = False
    trailer: bool = False
    stopped: bool = False   # speed known and under 0.5 km/h
    park: bool = False      # park brake on
    ignition: bool = False
    locked: bool = False
    dash_ok: bool = True
    front_on: bool = False  # any front bar asked for
    now_ms: int = 0


@dataclass
class LightsOut:
    level: dict = field(default_factory=lambda: {k: 0 for k in LAMPS})
    front: dict | None = None     # show levels for the 0x701 lights, None = leave them alone
    show_running: bool = False
    show_blocked: bool = False


class Lights:
    """Keeps the show clock. One per control box."""

    def __init__(self):
        self.show_start_ms = 0
        self._running = 0

    def show_ok(self, req: LightsReq, st: LightsState) -> bool:
        return bool(req.show in SHOW_PERIOD_MS and st.ignition and st.park and st.stopped
                    and st.dash_ok and not st.locked)

    def step(self, req: LightsReq, st: LightsState) -> LightsOut:
        out = LightsOut()
        lv = out.level
        moving = not st.stopped

        # Normal running
        if req.head_high:
            lv["head_l_high"] = lv["head_r_high"] = req.head_high
        elif req.head_low:
            lv["head_l_low"] = lv["head_r_low"] = req.head_low
        heads_on = bool(req.head_high or req.head_low)
        tail = req.tail or (255 if heads_on or st.front_on else 0)
        lv["tail_l"] = lv["tail_r"] = lv["trailer_tail"] = tail
        if moving:                                           # rule 3
            for k in ("head_l_low", "head_l_high", "head_r_low", "head_r_high",
                      "tail_l", "tail_r", "trailer_tail"):
                if lv[k]:
                    lv[k] = 255
        if req.rear_auto and st.reverse:
            lv["flood_l"] = lv["flood_r"] = 255
        elif req.rear_on:
            lv["flood_l"] = lv["flood_r"] = req.rear or 255
        if req.beacon and st.now_ms % BEACON_PERIOD_MS < BEACON_ON_MS:   # rule 5
            lv["beacon"] = req.beacon
        if req.beacon_white and st.stopped and st.now_ms % BEACON_PERIOD_MS >= BEACON_ON_MS:
            lv["beacon_white"] = req.beacon_white
        if st.trailer:
            lv["trailer_bar"] = req.trailer_bar
        if st.ignition and not st.dash_ok:                   # rule 9
            if not lv["head_l_high"]:
                lv["head_l_low"] = lv["head_r_low"] = 255
            lv["tail_l"] = lv["tail_r"] = lv["trailer_tail"] = 255
        if st.locked:                                        # rule 8
            for k in lv:
                lv[k] = 0

        # Light show, parked only (rule 10)
        ok = self.show_ok(req, st)
        if ok:
            if self._running != req.show:
                self._running = req.show
                self.show_start_ms = st.now_ms
            t = st.now_ms - self.show_start_ms
            for k in LAMPS:
                lv[k] = show_level(req.show, k, t)
            if not st.trailer:
                lv["trailer_bar"] = 0
            out.front = {k: show_level(req.show, k, t) for k in FRONT}
            out.show_running = True
        else:
            self._running = 0
            out.show_blocked = bool(req.show)

        # Rule 2, then rule 1 last so nothing can undo it
        for lo, hi in (("head_l_low", "head_l_high"), ("head_r_low", "head_r_high")):
            if lv[hi]:
                lv[lo] = 0
        if st.brake:
            lv["brake_l"] = lv["brake_r"] = lv["trailer_stop"] = 255
        elif not ok:
            lv["brake_l"] = lv["brake_r"] = lv["trailer_stop"] = 0
        return out
