"""Vehicle lock: the control box's rules, in plain Python (docs/vehicle-lock.md).

The firmware (firmware/control-box/src/core/lock.c) is the real thing; the
simulator's control box uses this file, and tests check the two match (same
hash, same answers). The dash never decides anything: it asks over 0x705 and
shows what 0x716 says.

Rules:
 1. No PIN set -> lock is off. Setting the first PIN needs nothing else.
 2. Lock only with a PIN set, stopped (known speed under 0.5 km/h, or key off),
    park brake on and nothing moving.
 3. Locked: no drive (drive inhibit), no 4WD / diff changes, no tray, no winch
    (disarmed), all lights off, no setting changes, no firmware update.
 4. Unlock with the PIN, or with the 8 digit recovery code (that also wipes the
    PIN and the code, so a new PIN has to be set).
 5. 5 wrong tries in a row -> 30 s lockout, then double for each further wrong
    try, up to 15 min. The count is kept over power cuts, and a lockout starts
    over after a reboot. The right PIN is refused during a lockout.
 6. Change PIN, set the recovery code or remove the lock: only while unlocked
    and within 60 s of entering the PIN (VERIFY). Setting a PIN also drops the
    old recovery code.
 7. Only a salted hash of the PIN and code is kept, never the digits.
 8. Remote lock (a text from the owner's phone, checked by the Pi): needs a PIN set,
    but no PIN in the command. It never cuts drive on the move: it waits ("pending",
    kept over power cuts) until known stopped for 10 s with the winch not pulling, or
    key off. The right PIN cancels a pending remote lock. docs/remote-access.md
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

from .canbus.messages import LOCK_RESULT, LOCK_STATE

_RESULT_CODE = {v: k for k, v in LOCK_RESULT.items()}
_STATE_CODE = {v: k for k, v in LOCK_STATE.items()}

PIN_MIN, PIN_MAX, PUK_LEN = 4, 6, 8
FREE_TRIES = 5
FIRST_WAIT_S = 30
MAX_WAIT_S = 900
WINDOW_S = 60
HASH_ROUNDS = 512
REMOTE_STOP_S = 10


def lock_hash(salt: bytes, digits: str) -> bytes:
    """Same as vlock_hash() in lock.c."""
    h = hashlib.sha256(salt + digits.encode()).digest()
    for _ in range(HASH_ROUNDS - 1):
        h = hashlib.sha256(h + salt).digest()
    return h


def encode_digits(digits: str) -> dict:
    """PIN or code -> the n_digits / d0-d3 signals of PI_LOCK (BCD, first digit high nibble)."""
    digits = str(digits or "")
    if not digits.isdigit() and digits:
        raise ValueError("digits only")
    if len(digits) > 8:
        raise ValueError("at most 8 digits")
    b = [0, 0, 0, 0]
    for i, ch in enumerate(digits):
        v = int(ch)
        b[i // 2] |= v << 4 if i % 2 == 0 else v
    return {"n_digits": len(digits), "d0": b[0], "d1": b[1], "d2": b[2], "d3": b[3]}


def decode_digits(v: dict) -> str | None:
    n = int(v.get("n_digits", 0))
    if n < PIN_MIN or n > 8:
        return None
    b = [int(v.get(f"d{i}", 0)) for i in range(4)]
    out = ""
    for i in range(n):
        x = b[i // 2] >> 4 if i % 2 == 0 else b[i // 2] & 0xF
        if x > 9:
            return None
        out += str(x)
    return out


def _wait_s(fails: int) -> int:
    s = FIRST_WAIT_S
    for _ in range(FREE_TRIES, fails):
        if s >= MAX_WAIT_S:
            break
        s *= 2
    return min(s, MAX_WAIT_S)


@dataclass
class VehicleLock:
    # What the Pico keeps in its flash sector
    pin_hash: bytes | None = None
    puk_hash: bytes | None = None
    salt: bytes = b""
    locked: bool = False
    fails: int = 0
    pending: bool = False             # remote lock waiting for the Teryx to stop
    # RAM only
    lockout_until: float | None = None
    window_until: float | None = None
    result: str = "none"
    result_count: int = 0
    saves: int = 0                    # flash writes, for tests
    _t: float = field(default=0.0, repr=False)

    def __post_init__(self):
        if self.fails >= FREE_TRIES:
            self.lockout_until = self._t + _wait_s(self.fails)

    # --------------------------------------------------------- state
    @property
    def pin_set(self) -> bool:
        return self.pin_hash is not None

    def state(self) -> str:
        return "locked" if self.locked else "unlocked" if self.pin_set else "off"

    def tick(self, now: float) -> None:
        self._t = now
        if self.lockout_until is not None and now >= self.lockout_until:
            self.lockout_until = None
        if self.window_until is not None and now >= self.window_until:
            self.window_until = None

    def stored(self) -> dict:
        """What survives a power cut."""
        return {"pin_hash": self.pin_hash, "puk_hash": self.puk_hash, "salt": self.salt,
                "locked": self.locked, "fails": self.fails, "pending": self.pending}

    @classmethod
    def restore(cls, stored: dict, now: float) -> "VehicleLock":
        return cls(**stored, _t=now)

    def _save(self) -> None:
        self.saves += 1

    def _wrong(self, now: float) -> str:
        self.fails = min(255, self.fails + 1)
        self._save()
        if self.fails >= FREE_TRIES:
            self.lockout_until = now + _wait_s(self.fails)
        return "wrong"

    def _open_window(self, now: float) -> None:
        self.window_until = now + WINDOW_S

    # --------------------------------------------------------- commands
    def command(self, cmd: str, digits: str | None, can_lock: bool, now: float) -> str:
        self.tick(now)
        r = self._handle(cmd, digits, can_lock, now)
        self.result = r
        self.result_count = (self.result_count + 1) & 0xFF
        return r

    def remote_check(self, safe: bool) -> bool:
        """Every tick. safe = key off, or stopped 10 s and the winch not pulling. True if it locked."""
        if not self.pending or not safe:
            return False
        self.pending = False
        self.locked = True
        self.window_until = None
        self._save()
        return True

    def _handle(self, cmd: str, digits: str | None, can_lock: bool, now: float) -> str:
        window = self.window_until is not None
        if cmd == "remote":
            if not self.pin_set:
                return "no_pin"
            if self.locked:
                return "ok"
            if not self.pending:
                self.pending = True
                self._save()
            return "pending"
        if cmd == "lock":
            if not self.pin_set:
                return "no_pin"
            if self.locked:
                return "ok"
            if not can_lock:
                return "not_parked"
            self.locked = True
            self.window_until = None
            self._save()
            return "ok"
        if cmd in ("unlock", "verify"):
            if not self.pin_set:
                return "no_pin"
            if self.lockout_until is not None:
                return "lockout"
            if digits is None:
                return "bad_digits"
            if len(digits) == PUK_LEN and cmd == "unlock" and self.puk_hash is not None:
                if lock_hash(self.salt, digits) != self.puk_hash:
                    return self._wrong(now)
                self.pin_hash = self.puk_hash = None
                self.salt = b""
                self.locked = self.pending = False
                self.fails = 0
                self._save()
                self._open_window(now)
                return "recovered"
            if len(digits) > PIN_MAX:
                return "bad_digits"
            if lock_hash(self.salt, digits) != self.pin_hash:
                return self._wrong(now)
            if self.fails:
                self.fails = 0
                self._save()
            if cmd == "unlock":
                if self.locked or self.pending:
                    self.locked = self.pending = False
                    self._save()
                return "ok"
            if self.locked:
                return "not_allowed"
            self._open_window(now)
            return "ok"
        if cmd == "set_pin":
            if self.locked or (self.pin_set and not window):
                return "not_allowed"
            if digits is None or len(digits) > PIN_MAX:
                return "bad_digits"
            self.salt = os.urandom(16)
            self.pin_hash = lock_hash(self.salt, digits)
            self.puk_hash = None
            self.fails = 0
            self.pending = False
            self._save()
            self._open_window(now)
            return "ok"
        if cmd == "set_puk":
            if self.locked or not self.pin_set or not window:
                return "not_allowed"
            if digits is None or len(digits) != PUK_LEN:
                return "bad_digits"
            self.puk_hash = lock_hash(self.salt, digits)
            self._save()
            return "ok"
        if cmd == "remove":
            if self.locked or not window:
                return "not_allowed"
            self.pin_hash = self.puk_hash = None
            self.salt = b""
            self.pending = False
            self.window_until = None
            self._save()
            return "ok"
        return "not_allowed"

    def workshop_reset(self) -> None:
        """Debug UART inside the control box: wipe and unlock."""
        self.pin_hash = self.puk_hash = None
        self.salt = b""
        self.locked = self.pending = False
        self.fails = 0
        self.lockout_until = self.window_until = None
        self._save()

    def frame(self, now: float, inhibit: bool) -> dict:
        """PICO_LOCK signal values."""
        self.tick(now)
        lockout = self.lockout_until is not None
        left = max(0, int(-(-(self.lockout_until - now) // 1))) if lockout else 0
        tries = 0 if lockout else (FREE_TRIES - self.fails if self.fails < FREE_TRIES else 1)
        return {
            "state": _STATE_CODE[self.state()],
            "tries_left": tries, "lockout_s": left,
            "window": int(self.window_until is not None), "puk_set": int(self.puk_hash is not None),
            "inhibit": int(inhibit), "lockout": int(lockout), "pending": int(self.pending),
            "result": _RESULT_CODE[self.result],
            "result_count": self.result_count, "fails": min(255, self.fails),
        }
