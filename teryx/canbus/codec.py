"""Tiny CAN signal codec.

Our own messages are packed little-endian (Intel byte order). Signals can
also be big-endian (Motorola), because a lot of Chinese motor controllers use
that, and the Shinegle layout we decode may need it. Bit numbering follows the
DBC rules exactly, so a .dbc file from SavvyCAN or cantools loads straight in:

    little-endian ("@1"): start = least significant bit, counting up
    big-endian    ("@0"): start = most significant bit, in DBC "sawtooth" order

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
    big_endian: bool = False   # Motorola byte order (DBC "@0")

    def bits(self) -> list[int]:
        """Absolute bit positions (bit 0 = LSB of byte 0), least significant first."""
        if not self.big_endian:
            return list(range(self.start, self.start + self.length))
        out, pos = [], self.start
        for _ in range(self.length):       # walk from the MSB down
            out.append(pos)
            pos = pos + 15 if pos % 8 == 0 else pos - 1
        return out[::-1]

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
            bits = s.bits()
            if min(bits) < 0 or max(bits) >= self.dlc * 8:
                raise ValueError(f"{self.name}.{s.name} does not fit in {self.dlc} bytes")
            mask = sum(1 << b for b in bits)
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
            raw &= (1 << s.length) - 1
            if s.big_endian:
                for i, b in enumerate(s.bits()):
                    word |= ((raw >> i) & 1) << b
            else:
                word |= raw << s.start
        return word.to_bytes(self.dlc, "little")

    def decode(self, data: bytes) -> dict:
        word = int.from_bytes(bytes(data).ljust(self.dlc, b"\0")[: self.dlc], "little")
        out = {}
        for s in self.signals:
            if s.big_endian:
                raw = sum(((word >> b) & 1) << i for i, b in enumerate(s.bits()))
            else:
                raw = (word >> s.start) & ((1 << s.length) - 1)
            if s.signed and raw >= 1 << (s.length - 1):
                raw -= 1 << s.length
            out[s.name] = s.to_phys(raw)
        return out
