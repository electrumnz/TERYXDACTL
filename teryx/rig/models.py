"""What each device in config/wiring.yaml does electrically, for the system sim.

Every device in wiring.yaml has a model here or a line in NOT_SIMULATED saying
why not. tests/test_system_sim.py checks that, so a new device can't be added to
the diagram without the sim knowing about it.

Each model has ``step(get) -> (contacts, drivers)``:
  contacts  pairs of pins joined right now (a closed relay, a switch, a fuse)
  drivers   (pin, Level, strong) a voltage the device puts on a pin
``get(pin)`` is the pin's level from the last pass of the solver (netlist.py).
Models with moving parts (actuators, the tray, the winch) also have
``advance(dt)``, called once per time step after the solve.
"""

from __future__ import annotations

import re

from .netlist import GND, Level, is_ground, is_high

V_BATT = 12.6
V_DCDC = 13.8


def S(pin, v, duty=1.0):
    return (pin, Level(v, duty), True)


def W(pin, v, duty=1.0):
    return (pin, Level(v, duty), False)


def avg(lv: Level | None) -> float:
    return 0.0 if lv is None else lv.avg


def volts(lv: Level | None) -> float:
    """The level's voltage when it is on (ignores PWM duty)."""
    return 0.0 if lv is None else lv.v


class Model:
    """Base: a device that does nothing electrically (a pass-through)."""

    kind = "passive"

    def __init__(self, dev_id: str, dev: dict):
        self.id = dev_id
        self.dev = dev
        self.pin_names = list(dev["pins"])

    def p(self, name: str) -> str:
        return f"{self.id}.{name}"

    def step(self, get):
        return [], []

    def powered_by(self, get, pos: str, neg: str, vmin: float) -> bool:
        return volts(get(self.p(pos))) >= vmin and is_ground(get(self.p(neg)))

    def report(self, get) -> dict:
        return {}


# ------------------------------------------------------------------ sources
class Battery(Model):
    kind = "battery"

    def __init__(self, dev_id, dev):
        super().__init__(dev_id, dev)
        self.volts = V_BATT
        self.connected = True

    def step(self, get):
        if not self.connected:
            return [], []
        return [], [S(self.p("pos"), self.volts), S(self.p("neg"), 0.0)]


class DcDc(Model):
    """72 V to 12 V. Off by default (the sim doesn't model the pack); turn on to see 13.8 V."""
    kind = "dcdc"

    def __init__(self, dev_id, dev):
        super().__init__(dev_id, dev)
        self.on = False

    def step(self, get):
        if not self.on:
            return [], [S(self.p("out_neg"), 0.0)]
        return [], [S(self.p("out_pos"), V_DCDC), S(self.p("out_neg"), 0.0)]


class Buck(Model):
    """A DC-DC to a fixed voltage, on while its input is above vmin."""
    kind = "buck"

    def __init__(self, dev_id, dev, vout=5.1, vmin=7.0, vin="VIN", out="VOUT", gnd="GND"):
        super().__init__(dev_id, dev)
        self.vout, self.vmin, self.vin, self.out, self.gnd = vout, vmin, vin, out, gnd

    def on(self, get) -> bool:
        return self.powered_by(get, self.vin, self.gnd, self.vmin)

    def step(self, get):
        return [], ([S(self.p(self.out), self.vout)] if self.on(get) else [])

    def report(self, get):
        return {"on": self.on(get)}


# ------------------------------------------------------------------ contacts
class FuseBlock(Model):
    """IN feeds every Fn way through its fuse. ``blown`` holds pulled/blown ways."""
    kind = "fuses"

    def __init__(self, dev_id, dev):
        super().__init__(dev_id, dev)
        self.blown: set[str] = set()

    def step(self, get):
        return [(self.p("IN"), self.p(f)) for f in self.pin_names
                if re.fullmatch(r"F\d+", f) and f not in self.blown], []


class Switch(Model):
    """Two pins joined while ``closed``. ``normally_closed`` flips the sense of ``on``."""
    kind = "switch"

    def __init__(self, dev_id, dev, a, b, on=False, normally_closed=False):
        super().__init__(dev_id, dev)
        self.a, self.b, self.on, self.nc = a, b, on, normally_closed

    @property
    def closed(self) -> bool:
        return self.on != self.nc

    def step(self, get):
        return ([(self.p(self.a), self.p(self.b))] if self.closed else []), []


class Source(Model):
    """A pin that puts 12 V out while ``on`` (a switch whose feed we don't draw)."""
    kind = "source"

    def __init__(self, dev_id, dev, pin, v=12.0, on=False):
        super().__init__(dev_id, dev)
        self.pin, self.v, self.on = pin, v, on

    def step(self, get):
        return [], ([S(self.p(self.pin), self.v)] if self.on else [])


class ChangeOver(Model):
    """Momentary (ON)-OFF-(ON) or F-N-R: COM goes to one side or neither."""
    kind = "changeover"

    def __init__(self, dev_id, dev, com, sides: dict):
        super().__init__(dev_id, dev)
        self.com, self.sides, self.pos = com, sides, None

    def step(self, get):
        pin = self.sides.get(self.pos)
        return ([(self.p(self.com), self.p(pin))] if pin else []), []


class Throttle(Model):
    kind = "throttle"

    def __init__(self, dev_id, dev):
        super().__init__(dev_id, dev)
        self.pedal = 0.0

    def step(self, get):
        feed = get(self.p("V12"))
        if feed is None or feed.v < 5:
            return [], []
        out = [S(self.p("WIPER"), 0.5 + 4.0 * self.pedal)]
        return ([(self.p("V12"), self.p("SW"))] if self.pedal > 0.03 else []), out


# ------------------------------------------------------------------ Shinegle low voltage side
# ASSUMED until Sam's SG1810 programmer shows the real settings (docs/shinegle-sg1810-tables.md):
SG_THROTTLE_START_V = 0.8     # PedSet "throttle starting value": below this the motor does nothing
SG_THROTTLE_FULL_V = 4.2      # full throttle (a hall pedal runs about 0.5 to 4.5 V)
SG_THROTTLE_FAULT_V = 4.8     # above this the wiper is shorted to 5 V or the ground is off: throttle fault
SG_HPD = True                 # high pedal disable: pedal down at key-on = no drive until you lift off


class Shinegle(Model):
    """SG1202 low voltage pins. KSI on J1-1 wakes it; it then feeds J1-25 (+12 V out) to the
    throttle and reads the pedal back on J1-16 (wiper) and J1-9 (pedal micro switch).
    Its CAN frames are the fake controller in teryx/sim, on the PLACEHOLDER layout in
    teryx/canbus/shinegle.dbc (made up until the bench sniff, docs/shinegle-decode.md)."""
    kind = "shinegle"

    def __init__(self, dev_id, dev):
        super().__init__(dev_id, dev)
        self.was_on = False
        self.hpd = False           # pedal was down at key-on: held off until it's lifted

    def ksi(self, get) -> bool:
        return volts(get(self.p("J1-1"))) >= 9.0

    def direction(self, get) -> str:
        if not self.ksi(get):
            return "neutral"
        f, r = volts(get(self.p("J1-22"))) >= 9, volts(get(self.p("J1-33"))) >= 9
        return "forward" if f and not r else "reverse" if r and not f else "neutral"

    def wiper_v(self, get) -> float:
        return volts(get(self.p("J1-16")))

    def pedal(self, get) -> float:
        """0-1 from the wiper volts, before the switch and HPD checks."""
        v = self.wiper_v(get)
        return max(0.0, min(1.0, (v - SG_THROTTLE_START_V) / (SG_THROTTLE_FULL_V - SG_THROTTLE_START_V)))

    def throttle_fault(self, get) -> bool:
        return self.ksi(get) and self.wiper_v(get) > SG_THROTTLE_FAULT_V

    def throttle(self, get) -> float:
        """What the controller acts on: needs KSI, the pedal switch closed, no HPD, no fault."""
        if not self.ksi(get) or self.hpd or self.throttle_fault(get):
            return 0.0
        if volts(get(self.p("J1-9"))) < 9.0:      # micro switch open: pedal up
            return 0.0
        return self.pedal(get)

    def sense(self, get) -> None:
        on = self.ksi(get)
        if on and not self.was_on and SG_HPD and self.pedal(get) > 0.1:
            self.hpd = True
        if self.hpd and (not on or self.pedal(get) < 0.05):
            self.hpd = False
        self.was_on = on

    def step(self, get):
        return [], ([S(self.p("J1-25"), 12.0)] if self.ksi(get) else [])

    def report(self, get):
        return {"ksi": self.ksi(get), "direction": self.direction(get),
                "throttle": round(self.throttle(get), 2), "hpd": self.hpd,
                "throttle_fault": self.throttle_fault(get)}


# ------------------------------------------------------------------ control box chips
class Pico(Model):
    """The Pico's pins come from the running firmware (System fills ``snap``)."""
    kind = "pico"

    def __init__(self, dev_id, dev):
        super().__init__(dev_id, dev)
        self.snap: dict[int, tuple] = {}      # gp -> (mode, value, hz, pull_up)

    def powered(self, get) -> bool:
        return self.powered_by(get, "VSYS", "GND", 4.3)

    def step(self, get):
        if not self.powered(get):
            return [], []
        out = [S(self.p("3V3"), 3.3)]
        for gp, (mode, value, _hz, pull_up) in self.snap.items():
            pin = f"GP{gp}"
            if pin not in self.dev["pins"]:
                continue
            if mode == "out":
                out.append(S(self.p(pin), 3.3 if value else 0.0))
            elif mode == "pwm":
                out.append(S(self.p(pin), 3.3, value) if value > 0 else S(self.p(pin), 0.0))
            elif mode == "input" and pull_up:
                out.append(W(self.p(pin), 3.3))
        return [], out


class Chip(Model):
    """A logic board that is either powered or not (CAN boards, ADC, level shifter...)."""
    kind = "chip"

    def __init__(self, dev_id, dev, vcc=None, gnd="GND", vmin=3.0):
        super().__init__(dev_id, dev)
        self.vcc = vcc or next(p for p in ("VCC", "VDD", "VSYS", "LV", "V5") if p in dev["pins"])
        self.gnd, self.vmin = gnd, vmin

    def powered(self, get) -> bool:
        return self.powered_by(get, self.vcc, self.gnd, self.vmin)

    def report(self, get):
        return {"powered": self.powered(get)}


class Mcp23017(Chip):
    kind = "mcp23017"

    def __init__(self, dev_id, dev):
        super().__init__(dev_id, dev, vcc="VDD")
        self.regs = None   # (iodir_a, iodir_b, olat_a, olat_b) from the firmware's chip model

    def step(self, get):
        if not self.powered(get) or self.regs is None:
            return [], []
        out = []
        for port, letter in ((0, "A"), (1, "B")):
            iodir, olat = self.regs[port], self.regs[2 + port]
            for b in range(8):
                pin = f"{letter}{b}"
                if pin in self.dev["pins"] and not iodir & (1 << b):
                    out.append(S(self.p(pin), 3.3 if olat & (1 << b) else 0.0))
        return [], out


class Pca9685(Chip):
    kind = "pca9685"

    def __init__(self, dev_id, dev):
        super().__init__(dev_id, dev, vcc="VCC")
        self.duty: list[float] = [0.0] * 16

    def step(self, get):
        if not self.powered(get):
            return [], []
        return [], [S(self.p(f"PWM{ch}"), 3.3, d) if d > 0 else S(self.p(f"PWM{ch}"), 0.0)
                    for ch, d in enumerate(self.duty) if f"PWM{ch}" in self.dev["pins"]]


class Opto(Chip):
    """PC817 board: 12 V on INn (against COM12) lights the LED, OUTn pulls low."""
    kind = "opto"

    def __init__(self, dev_id, dev):
        super().__init__(dev_id, dev, vcc="VCC")

    def lit(self, get, n: int) -> bool:
        return volts(get(self.p(f"IN{n}"))) >= 6.0 and is_ground(get(self.p("COM12")))

    def step(self, get):
        if not is_ground(get(self.p("GND"))):
            return [], []
        return [], [S(self.p(f"OUT{n}"), 0.0) for n in range(1, 9)
                    if f"IN{n}" in self.dev["pins"] and self.lit(get, n)]


class RelayBoard(Chip):
    """Opto-input relay board. Channel n: INn drives the coil, COMn to NOn (or NCn when off)."""
    kind = "relays"

    def __init__(self, dev_id, dev, active_low=True):
        super().__init__(dev_id, dev, vcc="VCC")
        self.active_low = active_low
        self.channels = sorted(int(m.group(1)) for p in dev["pins"] if (m := re.fullmatch(r"IN(\d+)", p)))

    def coil(self, get, n: int) -> bool:
        if not (self.powered(get) and volts(get(self.p("JDVCC"))) >= 4.5):
            return False
        lv = get(self.p(f"IN{n}"))
        if self.active_low:
            return lv is not None and lv.v < 0.8 and lv.duty >= 0.5   # sinks the opto LED
        return is_high(lv)

    def step(self, get):
        contacts = []
        for n in self.channels:
            on = self.coil(get, n)
            for side in (("NO",) if on else ("NC",)):
                if f"{side}{n}" in self.dev["pins"] and f"COM{n}" in self.dev["pins"]:
                    contacts.append((self.p(f"COM{n}"), self.p(f"{side}{n}")))
        return contacts, []

    def report(self, get):
        return {f"relay{n}": self.coil(get, n) for n in self.channels}


class Bts7960(Chip):
    """Two half bridges. EN high: M+ follows RPWM (supply or ground), M- follows LPWM.
    EN low or floating: both outputs off (high impedance). IS gives 117.6 mV per amp."""
    kind = "bts7960"
    IS_V_PER_A = 0.1176

    def __init__(self, dev_id, dev):
        super().__init__(dev_id, dev, vcc="VCC")
        self.current = 0.0   # set by the load model (actuator) after each step

    def enabled(self, get) -> bool:
        return self.powered(get) and is_ground(get(self.p("B-"))) and is_high(get(self.p("EN")))

    def step(self, get):
        if not self.enabled(get):
            return [], []
        supply = volts(get(self.p("B+")))
        out = []
        for inp, outp in (("RPWM", "M+"), ("LPWM", "M-")):
            lv = get(self.p(inp))
            d = lv.duty if lv is not None and lv.v >= 1.6 else 0.0
            out.append(S(self.p(outp), supply, d) if d > 0 and supply > 1 else S(self.p(outp), 0.0))
        out.append(S(self.p("IS"), self.current * self.IS_V_PER_A))
        return [], out


class Mosfet(Model):
    """Low side MOSFET board: INn high pulls OUTn to ground for the same duty."""
    kind = "mosfet"

    def step(self, get):
        if not is_ground(get(self.p("GND"))):
            return [], []
        out = []
        for n in range(1, 9):
            lv = get(self.p(f"IN{n}"))
            if lv is not None and lv.v >= 2.5 and lv.duty > 0 and f"OUT{n}" in self.dev["pins"]:
                out.append(S(self.p(f"OUT{n}"), 0.0, lv.duty))
        return [], out


# ------------------------------------------------------------------ loads
def lamp_level(hi: Level | None, lo: Level | None) -> float:
    """How bright a lamp between two nets is, 0-1 (12 V nominal, PWM duty counts)."""
    if hi is None or lo is None or hi.v < 9.0 or lo.v > 1.0:
        return 0.0
    return round(min(1.0, hi.duty * lo.duty), 3)


class Lamp(Model):
    """A lamp or filament between two of its own pins (``pairs``: name -> (pos, neg))."""
    kind = "lamp"

    def __init__(self, dev_id, dev, pairs: dict[str, tuple[str, str]]):
        super().__init__(dev_id, dev)
        self.pairs = pairs
        self.present = True

    def level(self, get, name: str | None = None) -> float:
        if not self.present:
            return 0.0
        pos, neg = self.pairs[name or next(iter(self.pairs))]
        return lamp_level(get(self.p(pos)), get(self.p(neg)))

    def report(self, get):
        return {k: self.level(get, k) for k in self.pairs}


class Load(Model):
    """Something that needs power to work (a camera, the screen, the amp)."""
    kind = "load"

    def __init__(self, dev_id, dev, pos, neg, vmin):
        super().__init__(dev_id, dev)
        self.pos, self.neg, self.vmin = pos, neg, vmin

    def powered(self, get) -> bool:
        return self.powered_by(get, self.pos, self.neg, self.vmin)

    def report(self, get):
        return {"powered": self.powered(get)}


class Pi5(Load):
    kind = "pi5"

    def __init__(self, dev_id, dev):
        super().__init__(dev_id, dev, "5V", "GND", 4.6)

    def step(self, get):
        if not self.powered(get):
            return [], []
        return [], [S(self.p(p), 3.3) for p in ("P1_3V3", "P17_3V3")] + [S(self.p("P2_5V"), 5.0)]


class Actuator(Model):
    """Linear actuator: position 0 (retracted) to 1 (extended), its own end limit switches.
    Moves at full speed for 12 V across M+ / M-, slower for less (PWM)."""
    kind = "actuator"

    def __init__(self, dev_id, dev, travel_s, run_a, bts: Bts7960 | None = None, pos=0.0):
        super().__init__(dev_id, dev)
        self.travel_s, self.run_a, self.bts, self.pos = travel_s, run_a, bts, pos
        self.drive = 0.0      # -1..1 from the last solve
        self.jammed = False

    def step(self, get):
        out = []
        if "POT_W" in self.dev["pins"]:
            hi, lo = get(self.p("POT_HI")), get(self.p("POT_LO"))
            if hi is not None and is_ground(lo):
                out.append(S(self.p("POT_W"), hi.v * (0.05 + 0.9 * self.pos)))
        return [], out

    def sense(self, get) -> None:
        a, b = get(self.p("M+")), get(self.p("M-"))
        if a is None or b is None:
            self.drive = 0.0
        else:
            self.drive = max(-1.0, min(1.0, (a.avg - b.avg) / 12.0))
        at_end = (self.drive > 0 and self.pos >= 1.0) or (self.drive < 0 and self.pos <= 0.0)
        moving = abs(self.drive) > 0.05 and not at_end
        amps = self.run_a * abs(self.drive) if moving else 0.0
        if self.jammed and abs(self.drive) > 0.05 and not at_end:
            amps = self.run_a * 4
        if self.bts:
            self.bts.current = amps

    def advance(self, dt: float) -> None:
        if self.jammed:
            return
        self.pos = max(0.0, min(1.0, self.pos + self.drive * dt / self.travel_s))

    def report(self, get):
        return {"pos": round(self.pos, 3), "drive": round(self.drive, 2)}


class LimitSwitch(Model):
    """Roller limit switch, normally closed: C to NC except at the limit."""
    kind = "limit"

    def __init__(self, dev_id, dev, at_limit):
        super().__init__(dev_id, dev)
        self.at_limit = at_limit       # callable -> bool
        self.broken = False

    def step(self, get):
        return ([] if self.at_limit() or self.broken else [(self.p("C"), self.p("NC"))]), []


class WinchSolenoid(Model):
    """XBull solenoid box: 12 V on COIL_IN winds in (B+ to M1, M2 to ground), COIL_OUT out.
    The handheld remote energises the same coils from inside the box."""
    kind = "winch_sol"

    def __init__(self, dev_id, dev):
        super().__init__(dev_id, dev)
        self.remote = None   # "in" / "out" / None

    def coils(self, get) -> tuple[bool, bool]:
        gnd = is_ground(get(self.p("GND")))
        return (gnd and volts(get(self.p("COIL_IN"))) >= 8, gnd and volts(get(self.p("COIL_OUT"))) >= 8)

    def step(self, get):
        out = []
        if self.remote in ("in", "out") and volts(get(self.p("B+"))) >= 9:
            out.append(S(self.p("REM_IN" if self.remote == "in" else "REM_OUT"), volts(get(self.p("B+")))))
        cin, cout = self.coils(get)
        contacts = []
        if cin and not cout:
            contacts = [(self.p("B+"), self.p("M1")), (self.p("M2"), self.p("GND"))]
        elif cout and not cin:
            contacts = [(self.p("B+"), self.p("M2")), (self.p("M1"), self.p("GND"))]
        return contacts, out

    def report(self, get):
        cin, cout = self.coils(get)
        return {"coil_in": cin, "coil_out": cout, "both": cin and cout}


class WinchMotor(Model):
    kind = "winch_motor"

    def turning(self, get) -> str | None:
        a, b = volts(get(self.p("M1"))), volts(get(self.p("M2")))
        if a >= 9 and b < 1:
            return "in"
        if b >= 9 and a < 1:
            return "out"
        return None

    def report(self, get):
        return {"turning": self.turning(get)}


# ------------------------------------------------------------------ Aqua power steering
# EVERYTHING BELOW IS ASSUMED until the bench test (docs/power-steering-aqua.md). The frame
# layouts are the ones in teryx/eps_toyota.py (opendbc's Toyota EPS frames); the numbers that
# make it feel like power steering (sensor volts per Nm, assist map, how heavy the Teryx is to
# turn) are rough guesses, each a named constant so the bench result is a one-line change.
TRQ_CENTRE_V = 2.5        # ASSUMED: torque sensor output with hands off
TRQ_V_PER_NM = 0.25       # ASSUMED: both outputs move the same way, 0.25 V per Nm
TRQ_MATCH_V = 0.4         # ASSUMED: the ECU calls a sensor fault if the two outputs differ by this
TRQ_RANGE_V = (0.5, 4.5)  # ASSUMED: outside this = sensor wire off or shorted
ECU_BOOT_S = 0.4          # ASSUMED: ECU starts talking this long after IG
ECU_TORQUE_PERIOD_S = 0.020   # ASSUMED: 0x260 at 50 Hz (Toyota EPS in opendbc)
ECU_STATUS_PERIOD_S = 0.040   # ASSUMED: 0x262 at 25 Hz
ECU_FRAMES_TIMEOUT_S = 1.0    # ASSUMED: no 0x0B4 + 0x2C4 for this long = limp mode
RPM_RUNNING_MIN = 400         # ASSUMED: "engine running" if 0x2C4 says at least this
ASSIST_LIMP = 1.0             # ASSUMED: assist ratio in the ECU's own fail-safe
ASSIST_MAP = ((0, 3.0), (16.3, 3.0), (60, 1.2), (100, 0.6), (200, 0.6))  # ASSUMED: told km/h -> ratio
COLUMN_LOCK_DEG = 450.0       # ASSUMED: lock to lock 2.5 turns through the Teryx rack
COLUMN_FRICTION_NM = 6.0      # ASSUMED: torque at the wheel to start turning when stopped
COLUMN_DEG_PER_NM_S = 60.0    # ASSUMED: how fast it turns per Nm over the friction
SELF_CENTRE_NM_PER_DEG_KMH = 0.0004   # ASSUMED: rolling, the tyres pull it back straight


def _interp(pts, x):
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


class EpsEcu(Model):
    """Toyota Aqua EPS ECU (89650-52B51): reads the torque sensor, turns the column, and
    talks on the steering CAN bus. ASSUMED behaviour, see the constants above.

    * Asleep without IG + B+ + ground: the column is a plain manual one.
    * Awake with the Pico's 0x2C4 (engine running) and 0x0B4 (speed) frames: full assist,
      less as the told speed goes up (ASSIST_MAP).
    * Awake but no frames for ECU_FRAMES_TIMEOUT_S: limp mode (its own fixed, lighter assist).
    * Torque sensor fault: no assist, and EPS_STATUS says permanent fault.
    * Sends 0x260 (driver torque, angle, EPS torque) and 0x262 (status) back.
    """
    kind = "eps_ecu"

    def __init__(self, dev_id, dev):
        super().__init__(dev_id, dev)
        self.t = 0.0
        self.awake_since: float | None = None
        self.last_speed_t = self.last_rpm_t = -1e9
        self.told_kmh = 0.0
        self.rpm = 0
        self.trq_v = (TRQ_CENTRE_V, TRQ_CENTRE_V)
        self.is_awake = False
        self.driver_nm = 0.0      # what the torque sensor says, worked out from TRQ1
        self.assist_nm = 0.0
        self.angle_deg = 0.0      # the column (shared with EPS_COL)
        self.road_kmh = 0.0       # real speed, for self-centring (the System sets it)
        self.silent = False       # sim switch: the ECU never talks (wrong frames guessed, dead ECU)
        self.force_fault = False  # sim switch: the ECU reports a permanent fault
        self._next_torque = self._next_status = 0.0
        self.outbox: list[tuple[int, bytes]] = []
        self.counts: dict[int, int] = {}

    def awake(self, get) -> bool:
        return (volts(get(self.p("IG"))) >= 9 and volts(get(self.p("B+"))) >= 9
                and is_ground(get(self.p("GND"))))

    # ---- what it hears from the Pico
    def on_frame(self, can_id: int, data: bytes) -> None:
        from ..eps_toyota import RPM_ID, SPEED_ID, SPEED_LSB_KMH, toyota_checksum
        self.counts[can_id] = self.counts.get(can_id, 0) + 1
        if len(data) != 8 or data[-1] != toyota_checksum(can_id, data):
            return
        if can_id == SPEED_ID:
            self.told_kmh = ((data[5] << 8) | data[6]) * SPEED_LSB_KMH
            self.last_speed_t = self.t
        elif can_id == RPM_ID:
            self.rpm = (data[0] << 8) | data[1]
            self.last_rpm_t = self.t

    # ---- what it's doing
    def sensor_fault(self) -> bool:
        a, b = self.trq_v
        lo, hi = TRQ_RANGE_V
        return not (lo <= a <= hi and lo <= b <= hi) or abs(a - b) > TRQ_MATCH_V

    def mode(self) -> str:
        if not self.is_awake:
            return "manual"
        if self.force_fault or self.sensor_fault():
            return "fault"
        if self.awake_since is not None and self.t - self.awake_since < ECU_BOOT_S:
            return "booting"
        fresh = (self.t - self.last_speed_t <= ECU_FRAMES_TIMEOUT_S
                 and self.t - self.last_rpm_t <= ECU_FRAMES_TIMEOUT_S and self.rpm >= RPM_RUNNING_MIN)
        return "normal" if fresh else "limp"

    def ratio(self) -> float:
        m = self.mode()
        if m == "normal":
            return _interp(ASSIST_MAP, self.told_kmh)
        if m == "limp":
            return ASSIST_LIMP
        return 0.0

    def sense(self, get) -> None:
        """After each solve: wake up or sleep, and read the torque sensor at our own pins."""
        awake = self.awake(get)
        if awake and not self.is_awake:
            self.awake_since = self.t
            self._next_torque = self._next_status = self.t + ECU_BOOT_S
        if not awake:
            self.awake_since = None
        self.is_awake = awake
        self.trq_v = (volts(get(self.p("TRQ1"))), volts(get(self.p("TRQ2"))))
        self.driver_nm = 0.0 if self.sensor_fault() else (self.trq_v[0] - TRQ_CENTRE_V) / TRQ_V_PER_NM

    def advance(self, dt: float) -> None:
        from ..eps_toyota import STATUS_ID, TORQUE_ID, toyota_checksum
        self.t += dt
        self.assist_nm = self.driver_nm * self.ratio()
        total = self.driver_nm + self.assist_nm - SELF_CENTRE_NM_PER_DEG_KMH * self.angle_deg * self.road_kmh * 10
        over = max(0.0, abs(total) - COLUMN_FRICTION_NM)
        self.angle_deg += (1 if total > 0 else -1) * over * COLUMN_DEG_PER_NM_S * dt
        self.angle_deg = max(-COLUMN_LOCK_DEG, min(COLUMN_LOCK_DEG, self.angle_deg))
        if not self.is_awake or self.mode() == "booting" or self.silent:
            return
        if self.t >= self._next_torque:
            self._next_torque = self.t + ECU_TORQUE_PERIOD_S
            drv = max(-32768, min(32767, round(self.driver_nm * 100)))   # ASSUMED: 0.01 Nm per bit
            eps = max(-32768, min(32767, round(self.assist_nm * 100)))
            ang = max(-32768, min(32767, round(self.angle_deg / 0.0573)))
            init = self.t - (self.awake_since or 0) < 1.0
            b = bytearray(8)
            b[0] = (0x01 if abs(self.driver_nm) > 3.0 else 0) | (0x08 if init else 0)
            b[1:3] = drv.to_bytes(2, "big", signed=True)
            b[3:5] = ang.to_bytes(2, "big", signed=True)
            b[5:7] = eps.to_bytes(2, "big", signed=True)
            b[7] = toyota_checksum(TORQUE_ID, b)
            self.outbox.append((TORQUE_ID, bytes(b)))
        if self.t >= self._next_status:
            self._next_status = self.t + ECU_STATUS_PERIOD_S
            from ..eps_toyota import STATUS_PERMANENT_FAULT
            lka = STATUS_PERMANENT_FAULT if self.mode() == "fault" else (5 if self.mode() == "normal" else 1)
            b = bytearray(5)
            b[3] = (lka & 0x7F) << 1
            b[4] = toyota_checksum(STATUS_ID, b)
            self.outbox.append((STATUS_ID, bytes(b)))

    def take(self) -> list[tuple[int, bytes]]:
        out, self.outbox = self.outbox, []
        return out

    def report(self, get):
        return {"awake": self.awake(get), "mode": self.mode(), "assist_ratio": round(self.ratio(), 2),
                "told_kmh": round(self.told_kmh, 1), "driver_nm": round(self.driver_nm, 2),
                "angle_deg": round(self.angle_deg, 1)}


class TorqueSensor(Model):
    """Aqua column torque sensor: 2.5 V hands off, ASSUMED 0.25 V per Nm, both outputs alike.
    ``driver_nm`` is how hard the driver is turning the wheel (+ = right)."""
    kind = "torque"

    def __init__(self, dev_id, dev):
        super().__init__(dev_id, dev)
        self.driver_nm = 0.0
        self.trq2_broken = False    # sim switch: one sensor output gone (wire off)

    def step(self, get):
        v = max(0.3, min(4.7, TRQ_CENTRE_V + TRQ_V_PER_NM * self.driver_nm))
        return [], [S(self.p("TRQ1"), v), S(self.p("TRQ2"), 0.0 if self.trq2_broken else v)]


class DpdtRelay(Model):
    """RC changeover relay: off = COMn to NCn (the real torque sensor)."""
    kind = "dpdt"

    def on(self, get) -> bool:
        return (volts(get(self.p("VCC"))) >= 4.5 and is_ground(get(self.p("GND")))
                and is_high(get(self.p("IN"))))

    def step(self, get):
        side = "NO" if self.on(get) else "NC"
        return [(self.p("COM1"), self.p(f"{side}1")), (self.p("COM2"), self.p(f"{side}2"))], []

    def report(self, get):
        return {"rc_steering": self.on(get)}


class Trailer(Model):
    """The flat 7-pin socket: reed switch closes with a plug in; trailer lamps load the pins."""
    kind = "trailer"

    def __init__(self, dev_id, dev):
        super().__init__(dev_id, dev)
        self.plugged = False

    def step(self, get):
        return ([(self.p("REED_A"), self.p("REED_B"))] if self.plugged else []), []

    def level(self, get, pin: str) -> float:
        return lamp_level(get(self.p(pin)), get(self.p("P3_EARTH"))) if self.plugged else 0.0

    def report(self, get):
        return {"plugged": self.plugged, **{p: self.level(get, p) for p in ("P2_REV", "P6_STOP", "P7_TAIL")}}


class Generic(Model):
    """Kept in the diagram, nothing to simulate (see NOT_SIMULATED for why)."""
    kind = "generic"


# Devices with no electrical model, and why. Everything else in wiring.yaml must have one.
NOT_SIMULATED = {
    "PACK": "72 V traction side: the sim starts at the 12 V system",
    "HV_ISO": "72 V traction side",
    "CONTACTOR": "72 V traction side (coil wiring unknown)",
    "MOTOR": "the fake Shinegle (teryx/sim) does the driving",
    "SPEEDO": "speed pulse only, the dash reads speed over CAN",
    "PROG": "setup tool, plugged in on the bench only",
    "TVS": "clamps spikes; no spikes in a switch-level sim",
    "RAIL": "a bus bar: just a net",
    "GND_STAR": "a bus bar: just a net",
    "DEBUG": "the firmware's UART console is read directly (Firmware.uart_take)",
    "AIHAT": "placeholder, not bought",
    "CAM_FRONT": "camera ribbon only, no power wiring",
    "TCAM_DONGLE": "video only",
    "TCAM_PLUG": "a plug: its pins are nets",
    "CARPLAY": "USB only",
    "SPEAKERS": "audio only",
    "SUB": "audio only",
    "RC_LVL": "level shifter: passes I2C, which the RC box (no firmware yet) doesn't run",
    "RC_DAC": "RC box chip: no RC firmware yet",
    "RC_ADC": "RC box chip: no RC firmware yet",
    "RC_ANGLE": "RC box sensor: no RC firmware yet",
}

# (pos, neg, vmin) for things that only need to be powered
LOADS = {
    "SCREEN": ("DC_IN", "GND", 10.0),
    "AMP": ("B+", "GND", 9.0),
    "GLOVE_USB": ("VIN", "GND", 9.0),
    "CAM_REAR": ("V12", "GND", 9.0),
    "CAM_TRAILER": ("V12", "GND", 9.0),
    "MODEM_4G": ("V", "G", 4.5),
    "DAC_HAT": ("V5", "GND", 4.5),
    "IMU": ("VCC", "GND", 3.0),
}

LAMPS = {
    "LB1": {"bar": ("pos", "neg")}, "LB2": {"bar": ("pos", "neg")}, "LB3": {"bar": ("pos", "neg")},
    "LB4": {"bar": ("pos", "neg")}, "LB_INT": {"bar": ("pos", "neg")}, "LB_TRL": {"bar": ("pos", "neg")},
    "FLOOD_L": {"flood": ("pos", "neg")}, "FLOOD_R": {"flood": ("pos", "neg")},
    "HEAD_L": {"low": ("LO", "GND"), "high": ("HI", "GND")},
    "HEAD_R": {"low": ("LO", "GND"), "high": ("HI", "GND")},
    "TAIL_L": {"tail": ("TAIL", "GND"), "stop": ("STOP", "GND")},
    "TAIL_R": {"tail": ("TAIL", "GND"), "stop": ("STOP", "GND")},
    "BEACON": {"amber": ("AMBER", "GND"), "white": ("WHITE", "GND")},
}


def i2c_address(dev: dict) -> int | None:
    m = re.search(r"\(0x([0-9a-fA-F]{2})", dev.get("name", ""))
    return int(m.group(1), 16) if m else None


def build(devices: dict, relay_active_low: bool = True) -> dict[str, Model]:
    """A model for every device in wiring.yaml (or Generic for the NOT_SIMULATED ones)."""
    m: dict[str, Model] = {}
    for dev_id, dev in devices.items():
        name = dev.get("name", "")
        if dev_id in NOT_SIMULATED:
            m[dev_id] = Generic(dev_id, dev)
        elif dev_id == "BAT12":
            m[dev_id] = Battery(dev_id, dev)
        elif dev_id == "DCDC":
            m[dev_id] = DcDc(dev_id, dev)
        elif dev_id in ("PI_BUCK", "PICO_BUCK"):
            m[dev_id] = Buck(dev_id, dev, vout=5.1, vmin=8.0 if dev_id == "PI_BUCK" else 6.5)
        elif dev_id == "SCREEN_PSU":
            m[dev_id] = Buck(dev_id, dev, vout=12.0, vmin=5.0)
        elif dev_id in ("FB", "FB2"):
            m[dev_id] = FuseBlock(dev_id, dev)
        elif dev_id == "KEY":
            m[dev_id] = Switch(dev_id, dev, "BAT", "IGN")
        elif dev_id == "KIT_KEY":
            m[dev_id] = Source(dev_id, dev, "out")   # its feed (KIT_KEY.in) isn't drawn yet; follows the key
        elif dev_id == "ESTOP":
            m[dev_id] = Switch(dev_id, dev, "in", "out", normally_closed=True)
        elif dev_id == "BRK_WINCH":
            m[dev_id] = Switch(dev_id, dev, "in", "out", normally_closed=True)
        elif dev_id == "LIMP_SW":
            m[dev_id] = Switch(dev_id, dev, "IN", "OUT")
        elif dev_id == "BRAKE_SW":
            m[dev_id] = Switch(dev_id, dev, "IN", "OUT")
        elif dev_id == "PARK_SW":
            m[dev_id] = Source(dev_id, dev, "OUT")   # TBC: 12 V or ground switching
        elif dev_id == "FNR":
            m[dev_id] = ChangeOver(dev_id, dev, "COM", {"forward": "F", "reverse": "R"})
        elif dev_id.startswith("HSW_"):
            m[dev_id] = ChangeOver(dev_id, dev, "FEED", {"in": "IN", "out": "OUT"})
        elif dev_id == "THROTTLE":
            m[dev_id] = Throttle(dev_id, dev)
        elif dev_id == "SG1202":
            m[dev_id] = Shinegle(dev_id, dev)
        elif dev_id in ("PICO",):
            m[dev_id] = Pico(dev_id, dev)
        elif dev_id == "RC_PICO":
            m[dev_id] = Chip(dev_id, dev, vcc="VSYS", vmin=4.3)   # no RC firmware yet: powered or not
        elif "MCP23017" in name:
            m[dev_id] = Mcp23017(dev_id, dev)
        elif "PCA9685" in name:
            m[dev_id] = Pca9685(dev_id, dev)
        elif "ADS1115" in name or "MCP2515" in name:
            m[dev_id] = Chip(dev_id, dev)
        elif dev_id == "OPTO":
            m[dev_id] = Opto(dev_id, dev)
        elif dev_id in ("RELAYS", "RELAYS2"):
            m[dev_id] = RelayBoard(dev_id, dev, relay_active_low)
        elif "BTS7960" in name:
            m[dev_id] = Bts7960(dev_id, dev)
        elif dev_id == "MOSFET":
            m[dev_id] = Mosfet(dev_id, dev)
        elif dev_id in LAMPS:
            m[dev_id] = Lamp(dev_id, dev, LAMPS[dev_id])
        elif dev_id in LOADS:
            m[dev_id] = Load(dev_id, dev, *LOADS[dev_id])
        elif dev_id == "PI5":
            m[dev_id] = Pi5(dev_id, dev)
        elif dev_id == "WINCH_SOL":
            m[dev_id] = WinchSolenoid(dev_id, dev)
        elif dev_id == "WINCH_MOTOR":
            m[dev_id] = WinchMotor(dev_id, dev)
        elif dev_id == "WINCH_REMOTE":
            m[dev_id] = Model(dev_id, dev)   # pressing it is WinchSolenoid.remote
        elif dev_id == "EPS_ECU":
            m[dev_id] = EpsEcu(dev_id, dev)
        elif dev_id == "EPS_COL":
            m[dev_id] = TorqueSensor(dev_id, dev)
        elif dev_id == "RC_REL":
            m[dev_id] = DpdtRelay(dev_id, dev)
        elif dev_id == "TRAILER":
            m[dev_id] = Trailer(dev_id, dev)
        else:
            continue   # no model: tests/test_system_sim.py says which
    # moving parts, joined to the bridge that drives them
    bts = {d: m[d] for d in m if isinstance(m[d], Bts7960)}
    for act, (travel, amps, drv) in {"ACT_DIFF": (2.5, 2.0, "BTS1"), "ACT_4WD": (1.5, 2.5, "BTS2"),
                                     "ACT_TRAY": (15.0, 4.0, "BTS3")}.items():
        if act in devices:
            m[act] = Actuator(act, devices[act], travel, amps, bts.get(drv))
    tray = m.get("ACT_TRAY")
    if tray is not None:
        if "LIM_DN" in devices:
            m["LIM_DN"] = LimitSwitch("LIM_DN", devices["LIM_DN"], lambda: tray.pos <= 0.005)
        if "LIM_UP" in devices:
            m["LIM_UP"] = LimitSwitch("LIM_UP", devices["LIM_UP"], lambda: tray.pos >= 0.995)
    return m
