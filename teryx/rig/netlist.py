"""config/wiring.yaml as an electrical network, solved switch by switch.

This is a switch-level solver, not SPICE. Each net ends up with a level:

    Level(v, duty)    v volts for `duty` of the time (PWM), off or low the rest
    None              floating: nothing drives it

Plain wires join pins into nets. Wires whose `via` is a diode only pass a high
level one way (from -> to). A divider scales it. Flyback diodes never conduct
in normal running, so they are left out. Closed contacts (relays, switches,
fuses, the key) join nets while they are closed. Device models (models.py) add
drivers: a battery drives 12.6 V, an opto output pulls low, a BTS7960 half
bridge drives its supply or ground. Strong drivers beat weak ones (pull-ups,
pull-downs). A strong high and a strong low on one net is a short, and is
reported.

That is enough to answer "does this lamp light, does this relay click, does
the Pico see this switch" for every wire in the diagram, which is what the
system sim is for. It does not do currents, voltage drop or timing inside a
PWM cycle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .. import wiring


@dataclass(frozen=True)
class Level:
    v: float
    duty: float = 1.0

    @property
    def avg(self) -> float:
        return self.v * self.duty

    def high(self, thresh: float = 1.6) -> bool:
        return self.v >= thresh and self.duty >= 0.5


GND = Level(0.0, 1.0)


def is_high(lv: Level | None, thresh: float = 1.6) -> bool:
    return lv is not None and lv.high(thresh)


def is_ground(lv: Level | None) -> bool:
    return lv is not None and lv.v < 0.5 and lv.duty >= 0.999


class _UF:
    def __init__(self):
        self.p: dict[str, str] = {}

    def find(self, x: str) -> str:
        p = self.p
        p.setdefault(x, x)
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def via_kind(via: str | None) -> tuple[str, float]:
    """('plain'|'diode'|'scale'|'none', factor) for a wire's `via` text."""
    if not via:
        return "plain", 1.0
    t = via.lower()
    if "flyback" in t:
        return "none", 0.0
    if "divider" in t:
        m = re.search(r"(\d+(?:\.\d+)?)k\s*/\s*(\d+(?:\.\d+)?)k", t)
        if m:
            top, bottom = float(m.group(1)), float(m.group(2))
            return "scale", bottom / (top + bottom)
        return "scale", 1.0
    if "1k to ground" in t:      # BTS7960 IS current sense: the IS pin drives the sense voltage
        return "plain", 1.0
    if "diode" in t or re.search(r"\b1n\d{4}|sb5\d0|10sq", t):
        return "diode", 1.0
    return "plain", 1.0


class Netlist:
    def __init__(self, d: dict | None = None):
        self.d = d or wiring.load()
        self.devices = self.d["devices"]
        self.pins = [f"{dev}.{p}" for dev, dv in self.devices.items() for p in dv["pins"]]
        self.removed: set[str] = set()   # wire ids cut (a broken wire, a blown inline fuse)
        self._build_static()
        self.values: dict[str, Level | None] = {}
        self.shorts: set[str] = set()

    def _build_static(self) -> None:
        uf = _UF()
        for p in self.pins:
            uf.find(p)
        self.directed: list[tuple[str, str, str, float, str]] = []   # (from, to, kind, factor, wire id)
        for w in self.d["wires"]:
            if w["id"] in self.removed:
                continue
            a, b = w["from"], w["to"]
            kind, k = via_kind(w.get("via"))
            if kind == "plain":
                uf.union(a, b)
            elif kind in ("diode", "scale"):
                self.directed.append((a, b, kind, k, w["id"]))
        self.static = uf

    def cut(self, wire_id: str) -> None:
        """Cut a wire (or blow its inline fuse)."""
        if not any(w["id"] == wire_id for w in self.d["wires"]):
            raise KeyError(f"no wire {wire_id}")
        self.removed.add(wire_id)
        self._build_static()

    def mend(self, wire_id: str) -> None:
        self.removed.discard(wire_id)
        self._build_static()

    def static_net(self, pin: str) -> str:
        return self.static.find(pin)

    def same_net(self, a: str, b: str) -> bool:
        return self.static.find(a) == self.static.find(b)

    def net_pins(self, pin: str) -> list[str]:
        r = self.static.find(pin)
        return [p for p in self.pins if self.static.find(p) == r]

    # ---------------------------------------------------------------- solve
    def solve(self, models: list, max_iter: int = 40) -> dict[str, Level | None]:
        """Settle every net. ``models`` give contacts and drivers from the last values."""
        values = self.values
        prev_sig = None
        for _ in range(max_iter):
            uf = _UF()
            uf.p = dict(self.static.p)
            drivers: list[tuple[str, Level, bool]] = []
            for m in models:
                contacts, drv = m.step(self.get)
                for a, b in contacts:
                    uf.union(a, b)
                drivers.extend(drv)
            # Diodes and dividers pass on what the sources give them, worked out fresh each
            # pass, so an old level can't keep itself alive round a loop of diodes and contacts.
            extra: list = []
            for _inner in range(30):
                resolved, shorts = self._resolve(uf, drivers + extra)
                nxt = []
                for a, b, kind, k, _wid in self.directed:
                    lv = resolved.get(uf.find(a))
                    if lv is not None and lv.duty > 0 and lv.v > (0.5 if kind == "diode" else 0.0):
                        nxt.append((b, Level(lv.v * k, lv.duty) if kind == "scale" else lv, True))
                if nxt == extra:
                    break
                extra = nxt
            new = {p: resolved.get(uf.find(p)) for p in self.pins}
            sig = tuple(new.values())
            values = new
            self.values = values
            if sig == prev_sig:
                break
            prev_sig = sig
        self.shorts = {p for p in self.pins if uf.find(p) in shorts}
        self.values = values
        self._uf = uf
        return values

    @staticmethod
    def _resolve(uf, drivers):
        groups: dict[str, list[tuple[Level, bool]]] = {}
        for pin, lv, strong in drivers:
            groups.setdefault(uf.find(pin), []).append((lv, strong))
        shorts = set()
        resolved: dict[str, Level | None] = {}
        for root, ds in groups.items():
            strong = [lv for lv, s in ds if s]
            pick = strong or [lv for lv, s in ds]
            top = max(lv.v for lv in pick)
            full_low = any(lv.v < 0.2 and lv.duty >= 0.999 for lv in strong)
            if full_low and any(lv.v >= 1.0 for lv in strong):
                shorts.add(root)   # something drives it high while something else holds it low
                resolved[root] = Level(0.0, 1.0)
            elif top > 0.05:
                resolved[root] = Level(top, max(lv.duty for lv in pick if lv.v == top))
            else:
                resolved[root] = Level(0.0, max(lv.duty for lv in pick))
        return resolved, shorts

    def get(self, pin: str) -> Level | None:
        return self.values.get(pin)
