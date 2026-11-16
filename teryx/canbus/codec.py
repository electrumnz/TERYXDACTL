"""Tiny CAN signal codec.

Signals are packed little-endian (Intel byte order, same as most DBC files),
so the definitions here can be turned into a .dbc file later if we want to use
tools like SavvyCAN or cantools.

    raw = (value - offset) / scale        physical = raw * scale + offset
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Signal:
    name: str
    start: int          # start bit (0 = LSB of byte 0)
    length: int         # bits
    scale: float = 1.0
    offset: float = 0.0
    signed: bool = False
    unit: str = ""
    choices: dict[int, str] | None = None  # optional enum labels
    comment: str = ""

    @property
    def raw_min(self) -> int:
        return -(1 << (self.length - 1)) if self.signed else 0

    @property
    def raw_max(self) -> int:
        return (1 << (self.length - 1)) - 1 if self.signed else (1 << self.length) - 1

    def to_raw(self, value: float) -> int:
        raw = round((value - self.offset) / self.scale)
        return max(self.raw_min, min(self.raw_max, raw))

    def to_phys(self, raw: int) -> float | int:
        value = raw * self.scale + self.offset
        if self.scale == 1 and self.offset == int(self.offset):
            return int(value)
        return round(value, 6)


@dataclass(frozen=True)
class Message:
    name: str
    can_id: int
    sender: str           # "shinegle", "controlbox" or "dash"
    period_ms: int        # how often it is sent (0 = on change only)
    signals: tuple[Signal, ...]
    dlc: int = 8
    extended: bool = False
    comment: str = ""
    placeholder: bool = False   # True until the real layout is decoded
    _by_name: dict = field(default_factory=dict, compare=False, repr=False)

    def __post_init__(self):
        self._by_name.update({s.name: s for s in self.signals})
        used = 0
        for s in self.signals:
            mask = ((1 << s.length) - 1) << s.start
            if s.start + s.length > self.dlc * 8:
                raise ValueError(f"{self.name}.{s.name} does not fit in {self.dlc} bytes")
            if used & mask:
                raise ValueError(f"{self.name}.{s.name} overlaps another signal")
            used |= mask

    def signal(self, name: str) -> Signal:
        return self._by_name[name]

    def encode(self, values: dict) -> bytes:
        word = 0
        for s in self.signals:
            raw = s.to_raw(float(values.get(s.name, s.offset)))
            if raw < 0:
                raw += 1 << s.length
            word |= (raw & ((1 << s.length) - 1)) << s.start
        return word.to_bytes(self.dlc, "little")

    def decode(self, data: bytes) -> dict:
        word = int.from_bytes(bytes(data).ljust(self.dlc, b"\0")[: self.dlc], "little")
        out = {}
        for s in self.signals:
            raw = (word >> s.start) & ((1 << s.length) - 1)
            if s.signed and raw >= 1 << (s.length - 1):
                raw -= 1 << s.length
            out[s.name] = s.to_phys(raw)
        return out
