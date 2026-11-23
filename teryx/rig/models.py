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
class Shinegle(Model):
    """SG1202 low voltage pins. KSI on J1-1 wakes it; it then feeds J1-25 (+12 V out)."""
    kind = "shinegle"

    def ksi(self, get) -> bool:
        return volts(get(self.p("J1-1"))) >= 9.0

    def direction(self, get) -> str:
        if not self.ksi(get):
            return "neutral"
        f, r = volts(get(self.p("J1-22"))) >= 9, volts(get(self.p("J1-33"))) >= 9
        return "forward" if f and not r else "reverse" if r and not f else "neutral"

    def step(self, get):
        return [], ([S(self.p("J1-25"), 12.0)] if self.ksi(get) else [])

    def report(self, get):
        return {"ksi": self.ksi(get), "direction": self.direction(get)}


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


class EpsEcu(Model):
    kind = "eps_ecu"

    def awake(self, get) -> bool:
        return (volts(get(self.p("IG"))) >= 9 and volts(get(self.p("B+"))) >= 9
                and is_ground(get(self.p("GND"))))

    def report(self, get):
        return {"awake": self.awake(get)}


class TorqueSensor(Model):
    """Aqua column torque sensor: both signals sit at about 2.5 V with no effort."""
    kind = "torque"

    def step(self, get):
        return [], [S(self.p("TRQ1"), 2.5), S(self.p("TRQ2"), 2.5)]


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
