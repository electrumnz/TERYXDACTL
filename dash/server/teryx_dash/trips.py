"""Trip logging: distance, energy used and put back, and a range estimate.

Runs on the Pi next to the gateway, so trips keep logging even if the screen's browser
restarts. Samples the live state once a second.

- The current trip runs from key on to key off. A trip shorter than 50 m isn't kept.
  If the Pi was off for more than 30 minutes (no samples), that also starts a new trip.
- Trip A is a trip meter you reset yourself.
- Range = energy left in the pack / how many Wh per km you've been using. That figure
  learns from real driving: every 0.25 km we note the distance and the energy that went
  out of (or back into) the pack, measured from pack volts x amps. The newest km count
  most (a km driven 5 km ago counts half as much as the one you just drove), and the
  figure is pulled gently toward your lifetime average so one steep hill doesn't swing
  it wildly. A fresh pack starts from a 180 Wh/km guess until there's real driving.
  It's saved to disk, so it carries on learning across restarts.

Saved to ~/.config/teryx/trips.json on the Pi (never in the repo).
"""

from __future__ import annotations

import json
import os
import time
from collections import deque
from pathlib import Path
from typing import Any

HISTORY_MAX = 100
MIN_TRIP_KM = 0.05
NEW_TRIP_GAP_S = 30 * 60
RECENT_KM = 20.0              # how much recent driving we keep to learn from
CHUNK_KM = 0.25
HALF_LIFE_KM = 5.0            # driving this far back counts half as much
PRIOR_KM = 1.5                # how hard the lifetime average (or first guess) pulls, as km
LEARNT_KM = 5.0               # past this much recent driving the figure counts as learnt
MIN_WH_PER_KM = 30.0
DEFAULT_WH_PER_KM = 180.0     # first guess for a 700 kg UTV on gravel, replaced once driven
DEFAULT_PACK_KWH = 7.5        # 72 V x 105 Ah, TBC: set the real figure in Settings > Display
SAVE_EVERY_S = 30


def _blank(now: float, soc: float | None = None) -> dict:
    return {"start": now, "end": now, "km": 0.0, "used_wh": 0.0, "regen_wh": 0.0, "max_kmh": 0.0,
            "moving_s": 0.0, "soc_start": soc, "soc_end": soc}


class TripLog:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.current: dict | None = None
        self.trip_a: dict = _blank(time.time())
        self.lifetime = {"km": 0.0, "used_wh": 0.0, "regen_wh": 0.0}
        self.history: list[dict] = []
        self.chunks: deque = deque()     # (km, net_wh) per CHUNK_KM, newest last
        self._chunk = [0.0, 0.0]
        self._last_t: float | None = None
        self._ign = False
        self._saved_at = 0.0
        self.load()

    # ------------------------------------------------------------ persistence
    def load(self) -> None:
        if not self.path:
            return
        try:
            d = json.loads(self.path.read_text())
        except Exception:
            return
        self.current = d.get("current")
        self.trip_a = d.get("trip_a") or self.trip_a
        self.lifetime.update(d.get("lifetime") or {})
        self.history = list(d.get("history") or [])[:HISTORY_MAX]
        self.chunks = deque(tuple(c) for c in d.get("chunks") or [])
        self._last_t = d.get("last_sample")

    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({
            "current": self.current, "trip_a": self.trip_a, "lifetime": self.lifetime,
            "history": self.history, "chunks": list(self.chunks), "last_sample": self._last_t,
        }))
        os.replace(tmp, self.path)

    # ------------------------------------------------------------ logging
    def _end_trip(self) -> None:
        if self.current and self.current["km"] >= MIN_TRIP_KM:
            self.history.insert(0, self.current)
            del self.history[HISTORY_MAX:]
        self.current = None

    def sample(self, s: dict, now: float | None = None) -> None:
        now = time.time() if now is None else now
        ign = s.get("in.ignition", True) is not False
        soc = s.get("mc.soc")
        gap = None if self._last_t is None else now - self._last_t
        self._last_t = now

        if self.current and (gap is None or gap > NEW_TRIP_GAP_S or (self._ign and not ign)):
            self._end_trip()
        self._ign = ign
        if not ign:
            self._maybe_save(now)
            return
        if self.current is None:
            self.current = _blank(now, soc)
        if gap is None or gap <= 0 or gap > 5:   # first sample, clock jump or a stall: don't integrate
            return

        mc_ok = s.get("mc.online", True) is not False
        speed = float(s.get("mc.speed") or 0) if mc_ok else 0.0
        # Distance from speed. (The controller's odometer may only count in 0.1 km steps,
        # which is too coarse to add up second by second.)
        km = speed * gap / 3600
        wh = 0.0
        if mc_ok:
            v, a = s.get("mc.batt_v"), s.get("mc.batt_a")
            if v is not None and a is not None:
                wh = float(v) * float(a) * gap / 3600
            elif s.get("mc.power_kw") is not None:
                wh = float(s["mc.power_kw"]) * 1000 * gap / 3600

        for t in (self.current, self.trip_a, self.lifetime):
            t["km"] += km
            if wh >= 0:
                t["used_wh"] += wh
            else:
                t["regen_wh"] += -wh
        for t in (self.current, self.trip_a):
            t["end"] = now
            if speed > 0.5:
                t["moving_s"] += gap
            t["max_kmh"] = max(t["max_kmh"], speed)
        if soc is not None:
            self.current["soc_end"] = soc
            if self.current.get("soc_start") is None:
                self.current["soc_start"] = soc

        self._chunk[0] += km
        self._chunk[1] += wh
        if self._chunk[0] >= CHUNK_KM:
            self.chunks.append((round(self._chunk[0], 4), round(self._chunk[1], 2)))
            self._chunk = [0.0, 0.0]
            while sum(c[0] for c in self.chunks) - self.chunks[0][0] >= RECENT_KM:
                self.chunks.popleft()
        self._maybe_save(now)

    def _maybe_save(self, now: float) -> None:
        if now - self._saved_at >= SAVE_EVERY_S:
            self._saved_at = now
            try:
                self.save()
            except OSError:
                pass

    def reset_trip_a(self, now: float | None = None) -> None:
        self.trip_a = _blank(time.time() if now is None else now)
        self.save()

    def clear_history(self) -> None:
        self.history = []
        self.save()

    # ------------------------------------------------------------ figures
    def recent_km(self) -> float:
        return sum(c[0] for c in self.chunks)

    def wh_per_km(self) -> tuple[float, str]:
        """Learnt use per km, and how much to trust it: guess, learning or learnt."""
        return learn_wh_per_km(list(self.chunks), self.lifetime)

    def summary(self, state: dict, pack_kwh: float = DEFAULT_PACK_KWH) -> dict[str, Any]:
        whk, basis = self.wh_per_km()
        soc = state.get("mc.soc")
        left_kwh = None if soc is None else max(0.0, float(soc)) / 100 * pack_kwh
        rng = None if left_kwh is None else left_kwh * 1000 / whk
        return {
            "current": _figures(self.current), "trip_a": _figures(self.trip_a),
            "lifetime": _figures(self.lifetime), "history": [_figures(t) for t in self.history],
            "wh_per_km": round(whk, 1), "basis": basis, "learnt_km": round(self.recent_km(), 1),
            "pack_kwh": pack_kwh,
            "kwh_left": None if left_kwh is None else round(left_kwh, 2),
            "range_km": None if rng is None else round(rng, 1),
        }


def learn_wh_per_km(chunks: list, lifetime: dict) -> tuple[float, str]:
    """Distance-weighted average of recent use, pulled toward a starting point.

    chunks: (km, net Wh) oldest first. Each chunk's weight halves every HALF_LIFE_KM of
    driving since it. The starting point (lifetime average once there's 2 km of it,
    else the first guess) counts as PRIOR_KM of driving, so a single short climb or
    downhill can't swing the range much, but a few km of real driving takes over.
    The web page's demo mode has a copy of this in dash/web/js/tripdata.js.
    """
    has_avg = lifetime.get("km", 0) >= 2.0
    if has_avg:
        prior = max(MIN_WH_PER_KM, (lifetime["used_wh"] - lifetime["regen_wh"]) / lifetime["km"])
    else:
        prior = DEFAULT_WH_PER_KM
    w_km = w_wh = back = total = 0.0
    for km, wh in reversed(chunks):
        w = 0.5 ** (back / HALF_LIFE_KM)
        w_km += w * km
        w_wh += w * wh
        back += km
        total += km
    if total < CHUNK_KM:
        return prior, ("average" if has_avg else "guess")
    est = (prior * PRIOR_KM + w_wh) / (PRIOR_KM + w_km)
    return max(MIN_WH_PER_KM, est), ("learnt" if total >= LEARNT_KM else "learning")


def _figures(t: dict | None) -> dict | None:
    if t is None:
        return None
    out = dict(t)
    net = t["used_wh"] - t["regen_wh"]
    out["net_wh"] = round(net, 1)
    out["wh_per_km"] = round(net / t["km"], 1) if t["km"] >= 0.1 else None
    out["avg_kmh"] = round(t["km"] / (t["moving_s"] / 3600), 1) if t.get("moving_s", 0) > 10 else None
    for k in ("km", "used_wh", "regen_wh", "max_kmh", "moving_s"):
        if k in out:
            out[k] = round(out[k], 3 if k == "km" else 1)
    return out
