"""4G remote access: text commands from the owner's phone (docs/remote-access.md).

A 4G USB stick on the Pi with a cheap prepaid SIM. Data is normally OFF. The Teryx never
texts on its own: it only answers a text that came from a number on the list AND has the
secret code in it. Anything else is ignored without a reply, so a stranger can't run up
the credit or even find out there's a modem.

Commands (not case sensitive, the code anywhere after the word):

    WHERE 4821   map link, speed, key, lock state, 12V
    LOCK 4821    remote lock. The control box locks once stopped for 10 s or key off.
                 It never cuts drive on the move (docs/vehicle-lock.md, LOCK_CMD_REMOTE)
    CAMS 4821    data on for 30 min: open the dash over Tailscale for live cameras and clips
    OFF 4821     data off now
    HELP 4821    list of commands

Safety and cost rules:
 - Sender must be on the list (Settings > Remote), compared as +64 numbers.
 - Code checked against a salted PBKDF2 hash. The code itself is never kept.
 - 5 wrong codes from a listed number: everything from anyone is ignored for an hour.
 - At most 10 commands an hour get a reply (each reply is a paid text).
 - Texts older than 3 days are dropped (they sat in the network while the Pi was off).
 - Data turns itself off again after 30 min.

The modem is driven through ModemManager (mmcli) and the data connection through
NetworkManager (nmcli), both on Raspberry Pi OS. FakeModem stands in for it in the
simulator and the tests.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable

from aiohttp import web

CODE_MIN, CODE_MAX = 4, 8
PBKDF2_ROUNDS = 100_000
WRONG_CODE_LIMIT = 5
WRONG_CODE_BLOCK_S = 3600
MAX_REPLIES_PER_HOUR = 10
MAX_AGE_S = 3 * 24 * 3600
DATA_ON_S = 30 * 60
NM_CONNECTION = "teryx-4g"
COMMANDS = ("where", "lock", "cams", "online", "off", "help")
# ONLINE is the same as CAMS: the phone app texts it to bring the 4G data up before it connects.


# ---------------------------------------------------------------- numbers and the code
def normalise_number(raw: str) -> str:
    """NZ numbers to +64 form: '021 123 4567' / '0064211234567' / '+64 21 123 4567' -> '+64211234567'."""
    s = re.sub(r"[^\d+]", "", str(raw or ""))
    if s.startswith("00"):
        s = "+" + s[2:]
    if s.startswith("0"):
        s = "+64" + s[1:]
    if s and not s.startswith("+"):
        s = "+" + s
    return s if re.fullmatch(r"\+\d{7,15}", s) else ""


def hash_code(code: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", code.encode(), salt, PBKDF2_ROUNDS).hex()


@dataclass
class RemoteConfig:
    enabled: bool = False
    numbers: list[str] = field(default_factory=list)   # +64 form
    salt: str = ""                                      # hex
    code_hash: str = ""                                 # hex, PBKDF2-SHA256
    data_on_min: int = DATA_ON_S // 60

    @property
    def code_set(self) -> bool:
        return bool(self.code_hash and self.salt)

    def set_code(self, code: str) -> None:
        code = str(code or "")
        if not code.isdigit() or not CODE_MIN <= len(code) <= CODE_MAX:
            raise ValueError(f"code must be {CODE_MIN} to {CODE_MAX} digits")
        salt = secrets.token_bytes(16)
        self.salt, self.code_hash = salt.hex(), hash_code(code, salt)

    def check_code(self, code: str) -> bool:
        if not self.code_set or not code:
            return False
        return hmac.compare_digest(hash_code(code, bytes.fromhex(self.salt)), self.code_hash)

    def public(self) -> dict:
        """What the dash may show: never the hash."""
        return {"enabled": self.enabled, "numbers": list(self.numbers), "code_set": self.code_set,
                "data_on_min": self.data_on_min}

    @classmethod
    def load(cls, path: Path) -> "RemoteConfig":
        try:
            d = json.loads(path.read_text())
        except (OSError, ValueError):
            return cls()
        cfg = cls()
        cfg.enabled = bool(d.get("enabled", False))
        cfg.numbers = [n for n in (normalise_number(x) for x in d.get("numbers", [])) if n]
        cfg.salt, cfg.code_hash = str(d.get("salt", "")), str(d.get("code_hash", ""))
        cfg.data_on_min = max(5, min(240, int(d.get("data_on_min", cfg.data_on_min))))
        return cfg

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"enabled": self.enabled, "numbers": self.numbers, "salt": self.salt,
                                   "code_hash": self.code_hash, "data_on_min": self.data_on_min}, indent=2))
        os.chmod(tmp, 0o600)   # only the dash's own user can read the hash
        os.replace(tmp, path)


# ---------------------------------------------------------------- the rules
@dataclass
class Sms:
    sender: str
    text: str
    when: float          # unix time the network stamped it


@dataclass
class Outcome:
    """What one incoming text leads to. reply None = say nothing."""
    command: str | None = None
    reply: str | None = None
    ignored: str | None = None     # why it was ignored, for the log only


def maps_link(lat: float, lon: float) -> str:
    return f"https://maps.google.com/?q={lat:.5f},{lon:.5f}"


def where_text(state: dict, now: float) -> str:
    s = state
    parts = []
    if s.get("pi.gps.fix") and s.get("pi.gps.lat") is not None:
        parts.append(f"Teryx at {maps_link(float(s['pi.gps.lat']), float(s['pi.gps.lon']))}")
        gps_age = now - float(s.get("pi.gps.time", now))
        if gps_age > 120:
            parts.append(f"(fix {int(gps_age // 60)} min old)")
    elif s.get("remote.last_fix"):
        lat, lon, t = s["remote.last_fix"]
        parts.append(f"No GPS fix now. Last at {maps_link(lat, lon)}, {int((now - t) // 60)} min ago")
    else:
        parts.append("No GPS fix yet")
    speed = s.get("mc.speed") if s.get("mc.online") else s.get("pi.gps.speed_kmh")
    if speed is not None:
        parts.append(f"{float(speed):.0f} km/h")
    parts.append("key ON" if s.get("in.ignition") else "key off")
    lock = s.get("lock.state", "?")
    if s.get("lock.pending"):
        lock = "lock waiting to stop"
    parts.append(f"lock: {lock}")
    if s.get("an.aux_12v"):
        parts.append(f"12V {float(s['an.aux_12v']):.1f}V")
    return ". ".join(parts)


HELP_TEXT = ("Teryx: WHERE, LOCK, CAMS (or ONLINE), OFF, HELP, each followed by your code. "
             "LOCK waits until it has stopped for 10 s or the key is off.")


@dataclass
class RemoteRules:
    """The decision part, no I/O, so it can be tested on its own."""
    cfg: RemoteConfig
    wrong_codes: int = 0
    blocked_until: float = 0.0
    replies: list[float] = field(default_factory=list)   # times of recent replies

    def code_ok(self, code: str, now: float) -> bool:
        """Check the code. Texts and the phone app share the count: 5 wrong blocks both for an hour."""
        if now < self.blocked_until:
            return False
        if not self.cfg.check_code(code):
            self.wrong_codes += 1
            if self.wrong_codes >= WRONG_CODE_LIMIT:
                self.blocked_until = now + WRONG_CODE_BLOCK_S
                self.wrong_codes = 0
            return False
        self.wrong_codes = 0
        return True

    def handle(self, sms: Sms, now: float) -> Outcome:
        if not self.cfg.enabled:
            return Outcome(ignored="remote access is off")
        if now - sms.when > MAX_AGE_S:
            return Outcome(ignored="too old")
        sender = normalise_number(sms.sender)
        if not sender or sender not in self.cfg.numbers:
            return Outcome(ignored="number not on the list")
        if now < self.blocked_until:
            return Outcome(ignored="blocked after wrong codes")
        words = re.findall(r"[A-Za-z]+|\d+", sms.text or "")
        cmd = words[0].lower() if words and words[0].isalpha() else ""
        code = next((w for w in words[1:] if w.isdigit()), "")
        if cmd not in COMMANDS:
            return Outcome(ignored="not a command")
        if not self.code_ok(code, now):
            return Outcome(ignored="wrong code")
        self.replies = [t for t in self.replies if now - t < 3600]
        if len(self.replies) >= MAX_REPLIES_PER_HOUR:
            # Still do LOCK and OFF (they cost nothing); just don't answer.
            return Outcome(command=cmd if cmd in ("lock", "off") else None, ignored="reply limit")
        self.replies.append(now)
        return Outcome(command=cmd)


# ---------------------------------------------------------------- GPS from the 4G board
# The A7670SA's own GNSS gives the Pi its position (no separate GPS). Field layouts are from
# SIMCom's "A76XX Series GNSS Application Note V1.03", 5.2: AT+CGNSSPWR=1 powers the GNSS up,
# then AT+CGPSINFO answers
#     +CGPSINFO: 3113.343286,N,12121.234064,E,250311,072809.3,44.1,0.0,0
#     lat ddmm.mmmmmm, N/S, lon dddmm.mmmmmm, E/W, date ddmmyy, UTC hhmmss.s, alt m, speed knots, course deg
# and only commas while there's no fix. Through ModemManager the same position comes from
# `mmcli --location-get -K` (keys modem.location.gps.latitude etc, "--" when empty).
KNOTS_TO_KMH = 1.852


def _dm_to_deg(dm: str, hemi: str) -> float:
    """ddmm.mmmm or dddmm.mmmm plus N/S/E/W -> signed degrees."""
    v = float(dm)
    deg = int(v // 100)
    out = deg + (v - deg * 100) / 60
    return -out if hemi.upper() in ("S", "W") else out


def _num(v: str | None) -> float | None:
    try:
        return float(v) if v not in (None, "", "--") else None
    except ValueError:
        return None


def parse_cgpsinfo(text: str, now: float | None = None) -> dict | None:
    """AT+CGPSINFO answer -> pi.gps.* values, or None while there's no fix."""
    m = re.search(r"\+CGPSINFO:\s*([^\r\n]*)", text or "")
    if not m:
        return None
    f = [x.strip() for x in m.group(1).split(",")]
    if len(f) < 4 or not f[0] or not f[2]:
        return None
    try:
        out = {"pi.gps.fix": True, "pi.gps.lat": round(_dm_to_deg(f[0], f[1]), 6),
               "pi.gps.lon": round(_dm_to_deg(f[2], f[3]), 6), "pi.gps.time": now if now is not None else time.time()}
    except ValueError:
        return None
    alt, kn, course = (_num(f[i]) if len(f) > i else None for i in (6, 7, 8))
    if alt is not None:
        out["pi.gps.alt_m"] = round(alt, 1)
    if kn is not None:
        out["pi.gps.speed_kmh"] = round(kn * KNOTS_TO_KMH, 1)
    if course is not None:
        out["pi.gps.heading"] = round(course, 1)
    return out


def parse_mm_location(text: str, now: float | None = None) -> dict | None:
    """`mmcli -m any --location-get -K` -> pi.gps.* values, or None while there's no fix.
    Speed, heading and satellites come from the NMEA RMC/GGA lines when those are switched on."""
    kv = parse_keyvalues(text)
    lat, lon = _num(kv.get("modem.location.gps.latitude")), _num(kv.get("modem.location.gps.longitude"))
    if lat is None or lon is None:
        return None
    out = {"pi.gps.fix": True, "pi.gps.lat": round(lat, 6), "pi.gps.lon": round(lon, 6),
           "pi.gps.time": now if now is not None else time.time()}
    alt = _num(kv.get("modem.location.gps.altitude"))
    if alt is not None:
        out["pi.gps.alt_m"] = round(alt, 1)
    for k, line in kv.items():
        if not k.startswith("modem.location.gps.nmea"):
            continue
        f = line.split("*")[0].split(",")
        if f[0][3:6] == "RMC" and len(f) > 8 and f[2] == "A":
            if _num(f[7]) is not None:
                out["pi.gps.speed_kmh"] = round(_num(f[7]) * KNOTS_TO_KMH, 1)
            if _num(f[8]) is not None:
                out["pi.gps.heading"] = round(_num(f[8]), 1)
        elif f[0][3:6] == "GGA" and len(f) > 7 and _num(f[7]) is not None:
            out["pi.gps.sats"] = int(_num(f[7]))
    return out


# ---------------------------------------------------------------- the modem
class FakeModem:
    """Stands in for the 4G stick in the simulator and the tests."""

    def __init__(self):
        self.inbox: list[Sms] = []
        self.sent: list[tuple[str, str]] = []
        self.data_on = False
        self.present = True

    async def read_sms(self) -> list[Sms]:
        msgs, self.inbox = self.inbox, []
        return msgs

    async def send_sms(self, number: str, text: str) -> None:
        self.sent.append((number, text))

    async def set_data(self, on: bool) -> None:
        self.data_on = on

    async def status(self) -> dict:
        return {"present": self.present, "data_on": self.data_on, "signal_pct": 70 if self.present else None,
                "operator": "Sim network" if self.present else None}

    async def location(self) -> dict | None:
        return None   # the sim's fake GPS (teryx/sim/sensors.py) fills pi.gps.* instead


Runner = Callable[..., Awaitable[str]]


async def _run(*args: str, timeout: float = 20) -> str:
    proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.DEVNULL)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise
    if proc.returncode:
        raise RuntimeError(f"{args[0]} failed ({proc.returncode})")
    return out.decode(errors="replace")


def parse_keyvalues(text: str) -> dict[str, str]:
    """mmcli -K output: 'key : value' per line."""
    out = {}
    for line in text.splitlines():
        k, sep, v = line.partition(":")
        if sep:
            out[k.strip()] = v.strip()
    return out


def parse_mm_time(s: str) -> float:
    """ModemManager timestamps look like 2026-11-18T19:04:11+13. Unknown -> now."""
    s = (s or "").strip()
    m = re.fullmatch(r"(.*[+-]\d\d)$", s)
    if m:
        s += ":00"
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return time.time()


class MmcliModem:
    """The real 4G stick, through ModemManager (texts) and NetworkManager (data)."""

    def __init__(self, run: Runner = _run, nm_connection: str = NM_CONNECTION):
        self.run = run
        self.nm = nm_connection

    async def read_sms(self) -> list[Sms]:
        kv = parse_keyvalues(await self.run("mmcli", "-m", "any", "--messaging-list-sms", "-K"))
        paths = [v for k, v in kv.items() if k.startswith("modem.messaging.sms.value")]
        out = []
        for path in paths:
            idx = path.rsplit("/", 1)[-1]
            if not idx.isdigit():
                continue
            s = parse_keyvalues(await self.run("mmcli", "-s", idx, "-K"))
            if s.get("sms.properties.state") != "received":
                continue
            out.append(Sms(s.get("sms.content.number", ""), s.get("sms.content.text", ""),
                           parse_mm_time(s.get("sms.properties.timestamp", ""))))
            # Delete once read, so the SIM's small store never fills up.
            await self.run("mmcli", "-m", "any", f"--messaging-delete-sms={idx}")
        return out

    async def send_sms(self, number: str, text: str) -> None:
        number = normalise_number(number)
        text = re.sub(r"[',\\]", " ", text)[:300]   # mmcli's own quoting can't take these
        made = await self.run("mmcli", "-m", "any", f"--messaging-create-sms=number='{number}',text='{text}'")
        m = re.search(r"/SMS/(\d+)", made)
        if not m:
            raise RuntimeError("mmcli did not make the text")
        try:
            await self.run("mmcli", "-s", m.group(1), "--send", timeout=60)
        finally:
            await self.run("mmcli", "-m", "any", f"--messaging-delete-sms={m.group(1)}")

    async def set_data(self, on: bool) -> None:
        await self.run("nmcli", "connection", "up" if on else "down", self.nm, timeout=60)

    async def status(self) -> dict:
        try:
            kv = parse_keyvalues(await self.run("mmcli", "-m", "any", "-K"))
        except Exception:
            return {"present": False, "data_on": False, "signal_pct": None, "operator": None}
        try:
            active = await self.run("nmcli", "-t", "-f", "NAME", "connection", "show", "--active")
            data_on = self.nm in active.split()
        except Exception:
            data_on = False
        sig = kv.get("modem.generic.signal-quality.value")
        return {"present": True, "data_on": data_on, "signal_pct": int(sig) if (sig or "").isdigit() else None,
                "operator": kv.get("modem.3gpp.operator-name") or None}

    async def location(self) -> dict | None:
        """GPS through ModemManager. Raw + NMEA have to be switched on before the GNSS engine runs.
        If this ModemManager can't drive the A7670's GNSS, it just never gets a fix (see
        docs/remote-access.md, "GPS"): run the module with TERYX_MODEM=at:... instead."""
        if not getattr(self, "_gps_on", False):
            await self.run("mmcli", "-m", "any", "--location-enable-gps-raw", "--location-enable-gps-nmea")
            self._gps_on = True
        return parse_mm_location(await self.run("mmcli", "-m", "any", "--location-get", "-K"))


# ---------------------------------------------------------------- the service
@dataclass
class RemoteService:
    modem: Any
    cfg_path: Path
    gateway: Any
    snapshot: Callable[[], dict]
    clock: Callable[[], float] = time.time
    rules: RemoteRules = None
    data_off_at: float | None = None
    last_fix: tuple[float, float, float] | None = None
    log: list[dict] = field(default_factory=list)   # last 50 commands, for Settings > Remote

    def __post_init__(self):
        if self.rules is None:
            self.rules = RemoteRules(RemoteConfig.load(self.cfg_path))

    @property
    def cfg(self) -> RemoteConfig:
        return self.rules.cfg

    def save(self) -> None:
        self.cfg.save(self.cfg_path)

    def _state(self) -> dict:
        s = dict(self.snapshot() or {})
        now = self.clock()
        if s.get("pi.gps.fix") and s.get("pi.gps.lat") is not None:
            self.last_fix = (float(s["pi.gps.lat"]), float(s["pi.gps.lon"]), now)
        if self.last_fix:
            s["remote.last_fix"] = self.last_fix
        return s

    async def poll(self) -> None:
        """Read new texts and act on them. Called every few seconds."""
        now = self.clock()
        state = self._state()
        if self.data_off_at is not None and now >= self.data_off_at:
            self.data_off_at = None
            await self.modem.set_data(False)
        for sms in await self.modem.read_sms():
            out = self.rules.handle(sms, now)
            self._log(sms, out, now)
            if out.command:
                reply = await self._do(out.command, state, now)
                if out.reply is None and out.ignored is None:
                    out.reply = reply
            if out.reply:
                await self.modem.send_sms(sms.sender, out.reply)

    async def _do(self, cmd: str, state: dict, now: float) -> str:
        if cmd == "where":
            return where_text(state, now)
        if cmd == "lock":
            if state.get("lock.state") == "off":
                return "No PIN set on the dash, so it can't lock. Set one in Settings > Vehicle lock."
            if state.get("lock.state") == "locked":
                return "Already locked."
            self.gateway.lock("remote")
            return ("Lock sent. It locks once it has been stopped for 10 s or the key is off, "
                    "never while moving. Text WHERE to check.")
        if cmd in ("cams", "online"):
            if not getattr(self.modem, "can_data", True):
                return ("Texts work, but this module has no 4G data set up (UART without ModemManager). "
                        "See docs/remote-access.md.")
            mins = await self.data_on(now)
            return (f"Data on for {mins} min. On your phone open Tailscale, then http://teryx:8080 "
                    "for live cameras and saved clips. Text OFF to stop sooner.")
        if cmd == "off":
            await self.data_off()
            return "Data off."
        return HELP_TEXT

    async def data_on(self, now: float, minutes: int | None = None) -> int:
        mins = max(5, min(240, int(minutes or self.cfg.data_on_min)))
        await self.modem.set_data(True)
        self.data_off_at = now + mins * 60
        return mins

    async def data_off(self) -> None:
        self.data_off_at = None
        await self.modem.set_data(False)

    def link(self) -> dict:
        """4G link state for the dash and other plugins (RC over 4G reads this). No secrets in here."""
        now = self.clock()
        up = self.data_off_at is not None and now < self.data_off_at
        return {"up": up, "minutes_left": round((self.data_off_at - now) / 60, 1) if up else 0,
                "off_at": self.data_off_at if up else None, "enabled": self.cfg.enabled}

    def _log(self, sms: Sms, out: Outcome, now: float) -> None:
        # Never log the code: just the command word and what happened.
        word = (re.findall(r"[A-Za-z]+", sms.text or "") or ["?"])[0].upper()
        self.log.append({"t": now, "from": normalise_number(sms.sender) or "unknown",
                         "word": word[:8], "done": out.command, "ignored": out.ignored})
        del self.log[:-50]


# ---------------------------------------------------------------- bare module on the Pi's UART, no ModemManager
Transact = Callable[..., Awaitable[str]]


def parse_at_time(s: str) -> float:
    """+CMGL times look like 26/11/18,19:04:11+52 (the zone is in quarter hours). Unknown -> now."""
    m = re.fullmatch(r"(\d\d)/(\d\d)/(\d\d),(\d\d):(\d\d):(\d\d)([+-])(\d+)", (s or "").strip())
    if not m:
        return time.time()
    yy, mo, dd, hh, mi, ss, sign, q = m.groups()
    mins = int(q) * 15 * (1 if sign == "+" else -1)
    iso = f"20{yy}-{mo}-{dd}T{hh}:{mi}:{ss}{'+' if mins >= 0 else '-'}{abs(mins) // 60:02d}:{abs(mins) % 60:02d}"
    try:
        return datetime.fromisoformat(iso).timestamp()
    except ValueError:
        return time.time()


def parse_cmgl(text: str) -> list[tuple[int, Sms]]:
    """Text-mode AT+CMGL answer -> [(index, Sms)]. Each header line is followed by the text."""
    out: list[tuple[int, Sms]] = []
    lines = text.replace("\r", "").split("\n")
    i = 0
    while i < len(lines):
        m = re.match(r'\+CMGL:\s*(\d+),"([^"]*)","([^"]*)",(?:"[^"]*")?,?"?([^"]*)"?', lines[i])
        if m:
            body = []
            i += 1
            while i < len(lines) and not lines[i].startswith("+CMGL:") and lines[i].strip() != "OK":
                body.append(lines[i])
                i += 1
            out.append((int(m.group(1)), Sms(m.group(3), "\n".join(body).strip(), parse_at_time(m.group(4)))))
            continue
        i += 1
    return out


class SerialAt:
    """One AT command at a time over a serial port (pyserial, run off the event loop)."""

    def __init__(self, port: str, baud: int = 115200):
        self.port, self.baud = port, baud
        self._ser = None
        self._lock = asyncio.Lock()

    def _open(self):
        if self._ser is None:
            import serial   # pyserial; only needed on the Pi
            self._ser = serial.Serial(self.port, self.baud, timeout=0.2)
        return self._ser

    def _xfer(self, cmd: str, body: str | None, timeout: float) -> str:
        ser = self._open()
        ser.reset_input_buffer()
        ser.write((cmd + "\r").encode())
        buf, end = b"", time.monotonic() + timeout
        while time.monotonic() < end:
            buf += ser.read(256)
            if body is not None and buf.endswith(b"> "):
                ser.write(body.encode("ascii", "replace") + b"\x1a")   # Ctrl-Z sends it
                body = None
                continue
            if re.search(rb"\r\n(OK|ERROR|\+CM[SE] ERROR:[^\r]*)\r\n$", buf):
                break
        return buf.decode("ascii", "replace")

    async def __call__(self, cmd: str, body: str | None = None, timeout: float = 5) -> str:
        async with self._lock:
            return await asyncio.to_thread(self._xfer, cmd, body, timeout)


class AtModem:
    """A bare 4G module (A7670SA etc) on the Pi's UART, spoken to with plain AT commands.

    Texts only: 4G data over a UART needs PPP, which ModemManager does for you (docs/remote-access.md,
    "Bare module on the UART"). Use this only if ModemManager won't take the port."""
    can_data = False

    def __init__(self, transact: Transact):
        self.at = transact
        self._ready = False

    async def _setup(self) -> None:
        if not self._ready:
            await self.at("ATE0")
            await self.at("AT+CMGF=1")          # text mode
            await self.at('AT+CSCS="GSM"')
            self._ready = True

    async def read_sms(self) -> list[Sms]:
        await self._setup()
        got = parse_cmgl(await self.at('AT+CMGL="REC UNREAD"', timeout=10))
        for idx, _ in got:
            await self.at(f"AT+CMGD={idx}")      # delete once read, the SIM only holds a few
        return [sms for _, sms in got]

    async def send_sms(self, number: str, text: str) -> None:
        await self._setup()
        number = normalise_number(number)
        text = re.sub(r"[^\x20-\x7e\n]", " ", text)[:160]
        reply = await self.at(f'AT+CMGS="{number}"', body=text, timeout=60)
        if "+CMGS:" not in reply:
            raise RuntimeError("the module did not send the text")

    async def set_data(self, on: bool) -> None:
        return None   # no data on this setup; RemoteService says so in the reply

    async def status(self) -> dict:
        try:
            csq = await self.at("AT+CSQ")
            cops = await self.at("AT+COPS?")
        except Exception:
            return {"present": False, "data_on": False, "signal_pct": None, "operator": None}
        m = re.search(r"\+CSQ:\s*(\d+)", csq)
        rssi = int(m.group(1)) if m else 99
        op = re.search(r'\+COPS:\s*\d+,\d+,"([^"]+)"', cops)
        return {"present": bool(m), "data_on": False, "texts_only": True,
                "signal_pct": None if rssi == 99 else round(min(rssi, 31) * 100 / 31),
                "operator": op.group(1) if op else None}

    async def location(self) -> dict | None:
        if not getattr(self, "_gps_on", False):
            await self.at("AT+CGNSSPWR=1", timeout=10)   # GNSS power on (A76XX GNSS app note, 5.2)
            self._gps_on = True
        return parse_cgpsinfo(await self.at("AT+CGPSINFO"))


REMOTE_KEY = web.AppKey("teryx_dash_remote", RemoteService)
REMOTE_TASK_KEY = web.AppKey("teryx_dash_remote_task", asyncio.Future)
GPS_TASK_KEY = web.AppKey("teryx_dash_gps_task", asyncio.Future)


def make_modem() -> Any:
    """TERYX_MODEM picks it: fake (the sim, and the default off the Pi), mmcli (the default on the Pi,
    for a USB stick or a UART module ModemManager has taken), or at:/dev/ttyAMA0[:115200] for a bare
    module on the UART spoken to directly (texts only)."""
    kind = os.environ.get("TERYX_MODEM") or ("mmcli" if Path("/usr/bin/mmcli").exists() else "fake")
    if kind.startswith("at:"):
        parts = kind.split(":")
        return AtModem(SerialAt(parts[1], int(parts[2]) if len(parts) > 2 else 115200))
    return MmcliModem() if kind == "mmcli" else FakeModem()


def setup_remote_routes(app: web.Application, gateway: Any, config_dir: Callable[[], Path],
                        snapshot: Callable[[], dict], modem: Any = None, poll_s: float = 5.0,
                        gps_s: float = 2.0) -> RemoteService:
    svc = RemoteService(modem or make_modem(), config_dir() / "remote.json", gateway, snapshot)
    app[REMOTE_KEY] = svc

    def unlocked() -> bool:
        return (snapshot() or {}).get("lock.state") != "locked"

    async def get_remote(_):
        st = await svc.modem.status()
        return web.json_response({**svc.cfg.public(), "modem": st, "log": svc.log[-20:],
                                  "data_off_at": svc.data_off_at,
                                  "simulated": isinstance(svc.modem, FakeModem)})

    async def put_remote(req):
        if not unlocked():
            return web.json_response({"error": "unlock the Teryx first"}, status=403)
        try:
            d = await req.json()
            assert isinstance(d, dict)
        except Exception:
            return web.json_response({"error": "expected a JSON object"}, status=400)
        cfg = svc.cfg
        if "numbers" in d:
            nums = [normalise_number(n) for n in d["numbers"] if str(n).strip()]
            if any(not n for n in nums) or len(nums) > 3:
                return web.json_response({"error": "up to 3 phone numbers, like 021 123 4567"}, status=400)
            cfg.numbers = nums
        if "code" in d:
            try:
                cfg.set_code(str(d["code"]))
            except ValueError as e:
                return web.json_response({"error": str(e)}, status=400)
        if "enabled" in d:
            if d["enabled"] and not (cfg.code_set and cfg.numbers):
                return web.json_response({"error": "add your number and a code first"}, status=400)
            cfg.enabled = bool(d["enabled"])
        if "data_on_min" in d:
            cfg.data_on_min = max(5, min(240, int(d["data_on_min"])))
        svc.save()
        return web.json_response(cfg.public())

    async def get_link(_):
        return web.json_response(svc.link())

    async def post_link(req):
        """For the phone app over Tailscale: keep the 4G data up longer, or turn it off.
        Needs the same code as the texts, and shares the wrong-code block."""
        try:
            d = await req.json()
            assert isinstance(d, dict)
        except Exception:
            return web.json_response({"error": "expected a JSON object"}, status=400)
        now = svc.clock()
        if not svc.cfg.enabled:
            return web.json_response({"error": "remote access is off"}, status=403)
        if not svc.rules.code_ok(str(d.get("code", "")), now):
            return web.json_response({"error": "wrong code, or blocked after wrong codes"}, status=403)
        if d.get("off"):
            await svc.data_off()
        elif not getattr(svc.modem, "can_data", True):
            return web.json_response({"error": "this 4G module has no data set up (texts only)"}, status=409)
        else:
            try:
                await svc.data_on(now, int(d.get("minutes") or 0) or None)
            except (TypeError, ValueError):
                return web.json_response({"error": "minutes must be a number"}, status=400)
        return web.json_response(svc.link())

    async def sim_text(req):
        """Simulator only: pretend a text arrived, and see what the Teryx would send back."""
        if not isinstance(svc.modem, FakeModem):
            return web.json_response({"error": "only in the simulator"}, status=404)
        d = await req.json()
        svc.modem.inbox.append(Sms(str(d.get("from", "")), str(d.get("text", ""))[:160],
                                   svc.clock() - float(d.get("age_s", 0) or 0)))
        before = len(svc.modem.sent)
        await svc.poll()
        return web.json_response({"replies": [t for _n, t in svc.modem.sent[before:]],
                                  "data_on": svc.modem.data_on})

    async def poll_loop():
        while True:
            try:
                await svc.poll()
            except asyncio.CancelledError:
                raise
            except Exception:
                pass   # modem unplugged or busy: try again next time
            await asyncio.sleep(poll_s)

    async def gps_loop():
        """Read the 4G board's GPS every few seconds into pi.gps.* (Gateway.set_local)."""
        publish = getattr(gateway, "set_local", None)
        if publish is None or not hasattr(svc.modem, "location"):
            return
        had_fix = False
        while True:
            wait = gps_s
            try:
                fix = await svc.modem.location()
            except asyncio.CancelledError:
                raise
            except Exception:
                fix, wait = None, max(gps_s, 30.0)   # modem busy, unplugged, or no GNSS: back off
            if fix:
                publish(fix)
                had_fix = True
            elif had_fix:
                publish({"pi.gps.fix": False})   # keep the last position, just say it's old
                had_fix = False
            await asyncio.sleep(wait)

    async def on_start(_app):
        _app[REMOTE_TASK_KEY] = asyncio.ensure_future(poll_loop())
        _app[GPS_TASK_KEY] = asyncio.ensure_future(gps_loop())

    async def on_stop(_app):
        _app[REMOTE_TASK_KEY].cancel()
        _app[GPS_TASK_KEY].cancel()

    app.router.add_get("/api/remote", get_remote)
    app.router.add_put("/api/remote", put_remote)
    app.router.add_get("/api/remote/link", get_link)
    app.router.add_post("/api/remote/link", post_link)
    app.router.add_post("/api/remote/sim-text", sim_text)
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)
    return svc
