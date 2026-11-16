"""Work out which bytes are which, from a capture made with the guided procedure.

    python -m teryx decode analyse captures/2026-11-20_1012

Writes, next to the capture:
    report.md          what was found, how sure we are, what to check next
    shinegle-draft.dbc a draft .dbc using the Teryx signal names
    candidates.json    every scored guess, for the next round of decoding

How it guesses (no magic, just bookkeeping):
  * Every byte, every pair of bytes (little and big-endian, signed and not)
    and every single bit is a "candidate" signal.
  * Bytes that count up by one each frame are counters. Bytes that equal the
    sum or XOR of the others are checksums. Those are set aside.
  * Phase marks (Sam pressing Enter as they move a switch) find on/off bits and
    value tables: a good candidate holds one steady value per phase, the same
    value for the same label, and different values for different labels.
  * Readings off the Shinegle dash (battery volts, speed ...) fit a straight
    line raw -> value. Two or more different readings give scale and offset;
    one reading is matched against common scales (1, 0.1, 0.01 ...) and
    temperature offsets (-40, -50 ...).
  * Smooth sweeps (throttle, rpm, current) separate real signals from noise
    and say which of LE / BE / 8-bit is right.
  * Ids that vanish while the Shinegle dash is unplugged are sent by the dash.
Then each Teryx name gets the best candidate that doesn't overlap one already
taken. Anything not confident stays out of the .dbc and is listed in the report.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ..canbus.codec import Message, Signal
from ..canbus.dbc import parse, render
from .procedure import BY_ID as STEP_INFO
from .session import Session, load

NICE_SCALES = (1, 0.1, 0.01, 0.5, 0.2, 0.25, 0.05, 0.02, 0.001, 2, 10, 0.125, 0.0625,
               100 / 255, 0.4)
TEMP_OFFSETS = (0, -40, -50, -30, -20, -100)
SAMPLE_GAP = 0.04       # seconds between samples kept per id (25 Hz is plenty)
SETTLE = 0.4            # ignore this long after each phase mark (switch bounce, lag)
MIN_SCORE = 0.5         # below this a guess stays out of the .dbc
FLAG_NAMES = {"brake", "ready", "limp"}
ENUM_NAMES = {"direction", "mode"}
# Contrasts between whole steps, for flags with no phase marks of their own
CONTRASTS = {"ready": (("key_on", 0), ("ready_idle", 1))}
UNITS = {"speed": "km/h", "rpm": "rpm", "batt_v": "V", "batt_a": "A", "soc": "%", "throttle": "%",
         "motor_temp": "C", "ctrl_temp": "C", "batt_temp": "C", "odometer": "km"}


@dataclass(frozen=True)
class Cand:
    can_id: int
    start: int          # DBC start bit
    length: int
    big_endian: bool = False
    signed: bool = False

    @property
    def key(self) -> str:
        if self.length == 1:
            return f"0x{self.can_id:X} byte {self.start // 8} bit {self.start % 8}"
        order = "BE" if self.big_endian else "LE"
        sign = "i" if self.signed else "u"
        byte = self.start // 8
        return f"0x{self.can_id:X} byte {byte} {sign}{self.length}{' ' + order if self.length > 8 else ''}"

    def signal(self, name: str, **kw) -> Signal:
        return Signal(name, self.start, self.length, signed=self.signed, big_endian=self.big_endian, **kw)

    def bits(self) -> set[int]:
        return set(self.signal("x").bits())

    def extract(self, data: bytes) -> int:
        if self.length == 1:
            return (data[self.start // 8] >> (self.start % 8)) & 1 if len(data) > self.start // 8 else 0
        if self.length == 8:
            i = self.start // 8
            v = data[i] if len(data) > i else 0
        elif self.big_endian:
            i = self.start // 8
            v = (data[i] << 8 | data[i + 1]) if len(data) > i + 1 else 0
        else:
            i = self.start // 8
            v = (data[i] | data[i + 1] << 8) if len(data) > i + 1 else 0
        if self.signed and v >= 1 << (self.length - 1):
            v -= 1 << self.length
        return v


@dataclass
class Guess:
    name: str
    cand: Cand
    score: float
    scale: float = 1.0
    offset: float = 0.0
    choices: dict | None = None
    field_start: int | None = None      # narrowed bit field inside the candidate (enums)
    field_len: int | None = None
    why: str = ""

    def signal(self) -> Signal:
        c = self.cand
        start, length = c.start, c.length
        if self.field_start is not None:
            start, length = self.field_start, self.field_len
        comment = ""
        if self.name.startswith("fault_"):
            comment = self.name[len("fault_"):].replace("_", " ").capitalize() + " fault"
        elif self.name == "batt_a":
            comment = "+ = draw, - = regen or charging"
        return Signal(self.name, start, length, scale=self.scale, offset=self.offset, signed=c.signed,
                      choices=self.choices, big_endian=c.big_endian and length > 8,
                      unit=UNITS.get(self.name, ""), comment=comment)


@dataclass
class IdInfo:
    can_id: int
    ext: bool
    count: int
    dlcs: list[int]
    period_ms: int
    counters: list[int] = field(default_factory=list)     # byte index
    checksums: list[tuple[int, str]] = field(default_factory=list)
    constant: list[int] = field(default_factory=list)
    from_dash: bool = False


# --------------------------------------------------------------------------- helpers

def _series(session: Session) -> dict[int, list[tuple[float, bytes]]]:
    out: dict[int, list] = defaultdict(list)
    last: dict[int, float] = {}
    for f in session.frames:
        if f.t - last.get(f.id, -1e9) >= SAMPLE_GAP:
            out[f.id].append((f.t, f.data))
            last[f.id] = f.t
    return out


def _in(rows, t0: float, t1: float):
    import bisect
    times = [r[0] for r in rows] if not hasattr(rows, "_times") else rows._times
    a, b = bisect.bisect_left(times, t0), bisect.bisect_left(times, t1)
    return rows[a:b]


class _Rows(list):
    """Frames of one id, with a time index for quick slicing."""

    def __init__(self, rows):
        super().__init__(rows)
        self._times = [r[0] for r in rows]


def _id_info(session: Session, can_id: int) -> IdInfo:
    frames = [f for f in session.frames if f.id == can_id]
    times = [f.t for f in frames]
    gaps = [b - a for a, b in zip(times, times[1:]) if b > a]
    period = int(round(statistics.median(gaps) * 100) * 10) if gaps else 0
    dlcs = sorted({len(f.data) for f in frames})
    info = IdInfo(can_id, frames[0].ext, len(frames), dlcs, period)
    n = max(dlcs)
    datas = [f.data.ljust(n, b"\0") for f in frames]
    for i in range(n):
        col = [d[i] for d in datas]
        if len(set(col)) == 1:
            info.constant.append(i)
            continue
        diffs = Counter((b - a) & 0xFF for a, b in zip(col, col[1:]))
        step, hits = diffs.most_common(1)[0]
        if step != 0 and hits >= 0.9 * (len(col) - 1) and len(set(col)) >= 4:
            info.counters.append(i)
            continue
        others = [j for j in range(n) if j != i]
        s_hits = sum(1 for d in datas if d[i] == sum(d[j] for j in others) & 0xFF)
        x_hits = 0
        for d in datas:
            x = 0
            for j in others:
                x ^= d[j]
            x_hits += d[i] == x
        if len(set(col)) >= 4 and max(s_hits, x_hits) >= 0.95 * len(datas):
            info.checksums.append((i, "sum" if s_hits >= x_hits else "xor"))
    return info


def _candidates(info: IdInfo) -> list[Cand]:
    skip = set(info.counters) | {i for i, _ in info.checksums}
    n = max(info.dlcs)
    out = []
    for i in range(n):
        if i in skip:
            continue
        for sg in (False, True):
            out.append(Cand(info.can_id, i * 8, 8, signed=sg))
        if i + 1 < n and i + 1 not in skip:
            for sg in (False, True):
                out.append(Cand(info.can_id, i * 8, 16, signed=sg))
                out.append(Cand(info.can_id, i * 8 + 7, 16, big_endian=True, signed=sg))
    return out


def _bits(info: IdInfo) -> list[Cand]:
    skip = set(info.counters) | {i for i, _ in info.checksums} | set(info.constant)
    return [Cand(info.can_id, i * 8 + b, 1) for i in range(max(info.dlcs)) if i not in skip for b in range(8)]


def _value_near(rows: _Rows, c: Cand, t: float, span: float = 0.5) -> float | None:
    near = _in(rows, t - span, t + span)
    if not near:
        near = _in(rows, t - 2, t + 2)
    if not near:
        return None
    return statistics.median(c.extract(d) for _, d in near)


def _nice(x: float, choices=NICE_SCALES, tol=0.015) -> float | None:
    for n in choices:
        for sign in (1, -1):
            if abs(x - sign * n) <= tol * n:
                return sign * n
    return None


def _simplicity(c: Cand, scale: float, offset: float) -> float:
    """Small nudge towards the simplest explanation, so ties break sensibly."""
    a = abs(scale)
    rank = NICE_SCALES.index(a) if a in NICE_SCALES else len(NICE_SCALES)
    f = 1 - 0.01 * rank
    f *= 0.99 if c.signed else 1.0
    f *= 0.995 if c.big_endian else 1.0
    f *= 1.0 if offset in TEMP_OFFSETS else 0.8
    return f


def _calm(rows, c: Cand) -> float:
    """1 for a value that rarely changes, towards 0 for one that changes every frame."""
    vals = [c.extract(d) for _, d in rows]
    if len(vals) < 2:
        return 1.0
    rate = sum(a != b for a, b in zip(vals, vals[1:])) / (len(vals) - 1)
    return 1 / (1 + 5 * rate)


def _round_sig(x: float, n: int = 4) -> float:
    return 0.0 if x == 0 else round(x, -int(math.floor(math.log10(abs(x)))) + n - 1)


# --------------------------------------------------------------------------- scoring

def _phase_windows(step) -> list[tuple[str, float, float]]:
    out = []
    for i, p in enumerate(step.phases):
        end = step.phases[i + 1].t if i + 1 < len(step.phases) else (step.end or p.t + 5)
        if end - p.t > SETTLE + 0.2:
            out.append((p.label, p.t + SETTLE, end - 0.15))
    return out


def _labelled_windows(session: Session, name: str):
    """(label, t0, t1) windows that say what ``name`` should be, from phases or step contrasts."""
    wins = []
    if name in CONTRASTS:
        for step_id, label in CONTRASTS[name]:
            st = session.step(step_id)
            if st and st.end:
                wins.append((str(label), st.start + 1, st.end - 0.5))
        return wins if len({w[0] for w in wins}) > 1 else []
    for st in session.steps:
        info = STEP_INFO.get(st.id)
        if st.skipped or not info or info.hints.get(name) != "phases":
            continue
        wins += _phase_windows(st)
    return wins


def _purity(rows: _Rows, c: Cand, wins) -> tuple[float, dict[str, int]]:
    """How well ``c`` holds one value per labelled window. Returns (score, label -> value)."""
    modes, pur = [], []
    for label, t0, t1 in wins:
        vals = [c.extract(d) for _, d in _in(rows, t0, t1)]
        if not vals:
            continue
        v, n = Counter(vals).most_common(1)[0]
        modes.append((label, v))
        pur.append(n / len(vals))
    if len(modes) < 2:
        return 0.0, {}
    by_label: dict[str, Counter] = defaultdict(Counter)
    for label, v in modes:
        by_label[label][v] += 1
    table = {label: cnt.most_common(1)[0][0] for label, cnt in by_label.items()}
    same = sum(cnt.most_common(1)[0][1] for cnt in by_label.values()) / len(modes)
    labels = list(table)
    pairs = [(a, b) for i, a in enumerate(labels) for b in labels[i + 1:]]
    diff = sum(table[a] != table[b] for a, b in pairs) / len(pairs) if pairs else 0
    return statistics.mean(pur) * same * diff, table


def _toggle_rate(rows: _Rows, c: Cand, exclude: list[tuple[float, float]]) -> float:
    changes = n = 0
    last = None
    for t, d in rows:
        if any(a <= t <= b for a, b in exclude):
            last = None
            continue
        v = c.extract(d)
        if last is not None:
            n += 1
            changes += v != last
        last = v
    return changes / n if n else 0.0


def _score_flag(session, rows, info, name, wins):
    span = [(min(w[1] for w in wins) - 2, max(w[2] for w in wins) + 2)]
    best = []
    for c in _bits(info):
        p, table = _purity(rows, c, wins)
        if p < 0.6:
            continue
        rate = _toggle_rate(rows, c, span)
        score = p / (1 + 50 * rate)
        on_labels = {"pressed", "1", "on", "unplugged"}
        on_vals = {v for k, v in table.items() if k in on_labels}
        inverted = on_vals == {0}
        best.append(Guess(name, c, score, scale=-1.0 if inverted else 1.0, offset=1.0 if inverted else 0.0,
                          why=f"bit follows the marks ({p:.0%} match, toggles {rate:.1%} of the time elsewhere)"
                              + (", inverted (0 = on)" if inverted else "")))
    return best


def _score_enum(session, rows, info, name, wins):
    span = [(min(w[1] for w in wins) - 2, max(w[2] for w in wins) + 2)]
    out = []
    for c in _candidates(info):
        if c.length != 8 or c.signed:
            continue
        p, table = _purity(rows, c, wins)
        if p < 0.6:
            continue
        varying = 0
        vals = list(table.values())
        for v in vals:
            varying |= v ^ vals[0]
        if not varying:
            continue
        lo = (varying & -varying).bit_length() - 1
        hi = varying.bit_length() - 1
        flen = hi - lo + 1
        field_c = Cand(c.can_id, c.start + lo, flen)
        rate = _toggle_rate(rows, field_c, span)
        choices = {}
        for label, v in table.items():
            choices.setdefault((v >> lo) & ((1 << flen) - 1), label)
        out.append(Guess(name, c, p / (1 + 50 * rate), choices=dict(sorted(choices.items())),
                         field_start=c.start + lo, field_len=flen,
                         why=f"bits {lo}-{hi} of the byte hold one value per position ({p:.0%} match)"))
    return out


def _reading_points(session: Session, name: str) -> list[tuple[float, float, float]]:
    """(t0, t1, value) for every known value of ``name``: typed readings, and numeric phase labels."""
    pts = [(r.t - 0.5, r.t + 0.5, r.value) for st, r in session.readings if r.name == name and not st.skipped]
    for st in session.steps:
        info = STEP_INFO.get(st.id)
        if st.skipped or not info or info.hints.get(name) != "phases":
            continue
        for label, t0, t1 in _phase_windows(st):
            try:
                pts.append((t0, t1, float(label)))
            except ValueError:
                pass
    return pts


def _fit(xs: list[float], ys: list[float]):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    b = my - a * mx
    ss = sum((y - my) ** 2 for y in ys)
    res = sum((y - (a * x + b)) ** 2 for x, y in zip(xs, ys))
    return a, b, (1 - res / ss) if ss else 0.0


def _sweep_quality(session, rows, c: Cand, name: str) -> float:
    """0..1: does ``c`` move smoothly in the steps where ``name`` should sweep, and sit still at idle?"""
    steps = [st for st in session.steps if not st.skipped and st.end
             and STEP_INFO.get(st.id) and STEP_INFO[st.id].hints.get(name) == "sweep"]
    if not steps:
        return 0.5
    vals = [c.extract(d) for st in steps for _, d in _in(rows, st.start, st.end)]
    if len(vals) < 10:
        return 0.0
    rng = max(vals) - min(vals)
    if rng == 0:
        return 0.0
    tv = sum(abs(b - a) for a, b in zip(vals, vals[1:]))
    smooth = min(1.0, (rng / tv) * 8) if tv else 0.0
    distinct = min(1.0, len(set(vals)) / 25)
    return smooth * distinct


def _score_numeric(session, rows, info, name):
    pts = _reading_points(session, name)
    if not pts:
        return []
    ys_all = [p[2] for p in pts]
    out = []
    for c in _candidates(info):
        xs, ys = [], []
        for t0, t1, y in pts:
            near = _in(rows, t0, t1) or _in(rows, t0 - 2, t1 + 2)
            if near:
                xs.append(statistics.median(c.extract(d) for _, d in near))
                ys.append(y)
        if len(xs) < max(1, len(pts) // 2):
            continue
        coverage = len(xs) / len(pts)
        if len(set(ys)) >= 2 and len(xs) >= 2:
            fit = _fit(xs, ys)
            if not fit or fit[2] < 0.9:
                continue
            a, b, r2 = fit
            yr = (max(ys) - min(ys)) or 1

            def resid(sc, of):
                return statistics.mean(abs(sc * x + of - y) for x, y in zip(xs, ys))

            def offset_for(sc):
                off = statistics.mean(y - sc * x for x, y in zip(xs, ys))
                nice_off = next((o for o in TEMP_OFFSETS if abs(off - o) <= 0.03 * yr + 0.5), None)
                return nice_off if nice_off is not None else _round_sig(off, 3)

            # The readings are rounded by the Shinegle dash, so a fit of 0.0985 is
            # really 0.1. Take a common scale if it explains the readings about as well.
            scale, nice = _round_sig(a), False
            base = resid(a, b)
            # How finely the dash shows this value (rpm in tens, volts in tenths ...)
            res = next((r for r in (100, 10, 1, 0.1, 0.01)
                        if all(abs(y / r - round(y / r)) < 1e-6 for y in ys)), 0.001)
            for n in sorted(NICE_SCALES, key=lambda n: abs(abs(a) - n)):
                sc = math.copysign(n, a)
                if abs(abs(a) - n) <= 0.06 * n and resid(sc, offset_for(sc)) <= 1.5 * base + 0.6 * res:
                    scale, nice = sc, True
                    break
            offset = offset_for(scale)
            err = resid(scale, offset) / yr
            niceness = 1.0 if nice else 0.85
            score = max(0.0, r2 - err) * niceness * coverage * _simplicity(c, scale, offset)
            why = f"fits {len(xs)} readings (R² {r2:.3f}), value = raw x {scale:g} {offset:+g}"
        else:
            # One distinct value: match it against common scales and offsets.
            y = statistics.mean(ys)
            x = statistics.mean(xs)
            if max(xs) - min(xs) > max(1.0, 0.02 * abs(x)):
                continue   # same reading each time, but the raw value jumped about: not this one
            if x == 0 and y != 0:
                continue
            best = None
            for s in NICE_SCALES:
                for o in TEMP_OFFSETS if "temp" in name else (0,):
                    e = abs(x * s + o - y) / max(abs(y), 1.0)
                    if best is None or e < best[0]:
                        best = (e, s, o)
            e, scale, offset = best
            if e > 0.03:
                continue
            spread = len({c.extract(d) for _, d in rows}) / 2
            plausible = 1.0 if spread > 1 else 0.85   # a constant byte matching is weaker evidence
            score = 0.7 * (1 - e / 0.03) * plausible * coverage * _simplicity(c, scale, offset)
            score *= 0.8 + 0.2 * _calm(rows, c)
            why = f"one reading ({y:g}) matches raw {x:g} x {scale:g} {offset:+g}"
        sweep = _sweep_quality(session, rows, c, name)
        score *= 0.7 + 0.3 * sweep
        out.append(Guess(name, c, score, scale=scale, offset=offset, why=why))
    del ys_all
    return out


# --------------------------------------------------------------------------- main

@dataclass
class Result:
    session: Session
    ids: dict[int, IdInfo]
    guesses: dict[str, list[Guess]]
    chosen: dict[str, Guess]
    dash_ids: list[int]
    request_response: bool
    moving_unknown: list[Cand]


def _dash_ids(session: Session, series) -> tuple[list[int], bool]:
    st = session.step("dash_unplugged")
    if not st:
        return [], False
    wins = [w for w in _phase_windows(st) if w[0] == "unplugged"]
    if not wins:
        return [], False
    _, t0, t1 = wins[0]
    gone, total = [], 0
    for can_id, rows in series.items():
        before = len(_in(rows, st.start, wins[0][1] - SETTLE))
        during = len(_in(rows, t0, t1))
        if before >= 3:
            total += 1
            if during == 0:
                gone.append(can_id)
    return sorted(gone), bool(total) and len(gone) == total


def analyse(path_or_session) -> Result:
    session = path_or_session if isinstance(path_or_session, Session) else load(path_or_session)
    raw_series = _series(session)
    series = {k: _Rows(v) for k, v in raw_series.items()}
    ids = {k: _id_info(session, k) for k in series}
    dash_ids, req_resp = _dash_ids(session, series)
    for k in dash_ids:
        ids[k].from_dash = True

    names = set()
    for st in session.steps:
        info = STEP_INFO.get(st.id)
        if info and not st.skipped:
            names |= {n for n in info.hints if not n.startswith("_")}
            names |= set(info.readings)
    names |= {r.name for _, r in session.readings}

    guesses: dict[str, list[Guess]] = {}
    for name in sorted(names):
        found: list[Guess] = []
        wins = _labelled_windows(session, name)
        for can_id, rows in series.items():
            if ids[can_id].from_dash:
                continue
            if (name in FLAG_NAMES or name.startswith("fault_")) and wins:
                found += _score_flag(session, rows, ids[can_id], name, wins)
            elif name in ENUM_NAMES and wins:
                found += _score_enum(session, rows, ids[can_id], name, wins)
            else:
                found += _score_numeric(session, rows, ids[can_id], name)
        found.sort(key=lambda g: (-g.score, g.cand.signed, g.cand.length))
        guesses[name] = found[:12]

    # Hand out names, best first, never two signals on the same bits.
    chosen: dict[str, Guess] = {}
    taken: dict[int, set[int]] = defaultdict(set)
    pool = sorted((g for gs in guesses.values() for g in gs),
                  key=lambda g: (-g.score, g.cand.signed, g.cand.length))
    for g in pool:
        if g.name in chosen or g.score < MIN_SCORE:
            continue
        bits = set(g.signal().bits())
        if bits & taken[g.cand.can_id]:
            continue
        chosen[g.name] = g
        taken[g.cand.can_id] |= bits

    # Moving bytes nobody claimed, so they still show up in SavvyCAN
    moving = []
    for can_id, info in ids.items():
        if info.from_dash:
            continue
        for i in range(max(info.dlcs)):
            if i in info.constant or i in info.counters or any(i == j for j, _ in info.checksums):
                continue
            if not set(range(i * 8, i * 8 + 8)) & taken[can_id]:
                moving.append(Cand(can_id, i * 8, 8))
    return Result(session, ids, guesses, chosen, dash_ids, req_resp, moving)


# --------------------------------------------------------------------------- outputs

def draft_messages(res: Result) -> list[Message]:
    by_id: dict[int, list[Signal]] = defaultdict(list)
    for g in res.chosen.values():
        by_id[g.cand.can_id].append(g.signal())
    for c in res.moving_unknown:
        by_id[c.can_id].append(Signal(f"unknown_b{c.start // 8}", c.start, 8,
                                      comment="moves, but we don't know what it is yet"))
    msgs = []
    for can_id in sorted(by_id):
        info = res.ids[can_id]
        sigs = sorted(by_id[can_id], key=lambda s: min(s.bits()))
        if info.counters and not any(s.name == "counter" for s in sigs):
            i = info.counters[0]
            sigs.append(Signal("counter", i * 8, 8))
        names = [s.name for s in sigs]
        sigs = [s for s in sigs if names.count(s.name) == 1 or s.name.startswith("unknown")]
        msgs.append(Message(f"SG_{can_id:X}", can_id, "shinegle", info.period_ms, tuple(sigs),
                            dlc=max(info.dlcs), extended=info.ext,
                            comment="DRAFT from a capture. Check before trusting."))
    return msgs


def draft_dbc(res: Result) -> str:
    general = (f"Shinegle SG1202 layout for Teryx OS. DRAFT made by 'python -m teryx decode analyse' "
               f"from {res.session.path.name if res.session.path else 'a capture'}. "
               "Check each signal with 'python -m teryx decode check' before installing.")
    text = render(draft_messages(res), header_comment=general)
    parse(text)   # make sure what we wrote loads back
    return text


def _conf(score: float) -> str:
    return "high" if score >= 0.85 else "medium" if score >= 0.65 else "low" if score >= MIN_SCORE else "guess"


def report(res: Result) -> str:
    s = res.session
    out = ["# Shinegle decode report", ""]
    dur = (s.frames[-1].t - s.frames[0].t) if s.frames else 0
    out += [f"Capture: `{s.path}`  ", f"{len(s.frames)} frames over {dur / 60:.1f} minutes, "
            f"{len(res.ids)} ids, {sum(1 for x in s.steps if not x.skipped)} steps marked.", ""]
    if not s.frames:
        out += ["**No frames at all.** Check the wiring (CAN H to H, L to L), the bitrate and that the "
                "adaptor was open. Run `python -m teryx decode bitrate` first.", ""]
        return "\n".join(out)
    if res.request_response:
        out += ["> **Everything went quiet with the Shinegle dash unplugged.** The controller only talks "
                "when the dash asks. The dash's frames are listed below; the next step is to replay them "
                "from the Pi (needs the sniffer's transmit jumper fitted).", ""]
    out += ["## What we found", "", "| Teryx name | Where | Scale / values | Confidence | Why |",
            "|---|---|---|---|---|"]
    for name in sorted(res.guesses):
        g = res.chosen.get(name)
        if not g:
            best = res.guesses[name][0] if res.guesses[name] else None
            hint = f"best guess {best.cand.key} ({best.score:.2f})" if best else "no candidates"
            out.append(f"| `{name}` | not found | | | {hint} |")
            continue
        sig = g.signal()
        where = g.cand.key if g.field_start is None else \
            f"0x{g.cand.can_id:X} byte {g.field_start // 8} bits {g.field_start % 8}-{g.field_start % 8 + g.field_len - 1}"
        sv = ", ".join(f"{k}={v}" for k, v in g.choices.items()) if g.choices else \
            f"x {sig.scale:g} {sig.offset:+g}"
        out.append(f"| `{name}` | {where} | {sv} | {_conf(g.score)} ({g.score:.2f}) | {g.why} |")
    out += ["", "## Every id on the bus", "",
            "| Id | Frames | Every | Bytes | Constant bytes | Counter | Checksum | Sent by |",
            "|---|---|---|---|---|---|---|---|"]
    for can_id in sorted(res.ids):
        i = res.ids[can_id]
        ident = f"0x{can_id:08X}" if i.ext else f"0x{can_id:03X}"
        out.append(f"| {ident} | {i.count} | {i.period_ms} ms | {'/'.join(map(str, i.dlcs))} | "
                   f"{', '.join(map(str, i.constant)) or '-'} | {', '.join(map(str, i.counters)) or '-'} | "
                   f"{', '.join(f'{b} ({k})' for b, k in i.checksums) or '-'} | "
                   f"{'Shinegle dash' if i.from_dash else 'controller?'} |")
    if res.moving_unknown:
        out += ["", "## Moving bytes nobody claimed", "",
                "These change but didn't match anything we marked. They're in the draft as `unknown_bN` "
                "so you can graph them in SavvyCAN:", ""]
        out += [f"- {c.key}" for c in res.moving_unknown]
    out += ["", "## Runner-up guesses", "", "If a name above looks wrong, one of these may be right.", ""]
    for name in sorted(res.guesses):
        alts = [g for g in res.guesses[name] if res.chosen.get(name) is not g][:3]
        if alts:
            out.append(f"- `{name}`: " + "; ".join(f"{g.cand.key} ({g.score:.2f}, {g.why})" for g in alts))
    notes = [(st.title, n) for st in s.steps for n in st.notes]
    if notes:
        out += ["", "## Notes typed during the capture", ""] + [f"- {t}: {n}" for t, n in notes]
    out += ["", "## Next", "",
            "1. `python -m teryx decode check shinegle-draft.dbc <capture>` and look at each step's values.",
            "2. Fix anything odd in SavvyCAN (load the capture and the draft .dbc, graph the signal).",
            "3. `python -m teryx decode install shinegle-draft.dbc` when it looks right.", ""]
    return "\n".join(out)


def candidates_json(res: Result) -> str:
    def g2d(g: Guess):
        return {"where": g.cand.key, "can_id": g.cand.can_id, "start": g.cand.start, "length": g.cand.length,
                "big_endian": g.cand.big_endian, "signed": g.cand.signed, "score": round(g.score, 3),
                "scale": g.scale, "offset": g.offset, "choices": g.choices, "why": g.why,
                "field_start": g.field_start, "field_len": g.field_len}
    return json.dumps({
        "chosen": {n: g2d(g) for n, g in res.chosen.items()},
        "guesses": {n: [g2d(g) for g in gs] for n, gs in res.guesses.items()},
        "dash_ids": res.dash_ids, "request_response": res.request_response,
    }, indent=1)


def write_outputs(res: Result, out_dir: Path | None = None) -> dict[str, Path]:
    base = res.session.path
    out_dir = Path(out_dir) if out_dir else (base if base and base.is_dir() else (base.parent if base else Path(".")))
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {"report": out_dir / "report.md", "dbc": out_dir / "shinegle-draft.dbc",
             "candidates": out_dir / "candidates.json"}
    files["report"].write_text(report(res), encoding="utf-8")
    files["dbc"].write_text(draft_dbc(res), encoding="utf-8")
    files["candidates"].write_text(candidates_json(res), encoding="utf-8")
    return files
