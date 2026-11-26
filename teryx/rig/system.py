"""The whole Teryx on a PC: real Pico firmware + wiring + fake Shinegle + dash gateway.

    sys = System()                    # builds the firmware if needed, key off, parked
    sys.key(True); sys.run(2)         # turn the key, run 2 s of virtual time
    sys.dash.request("light.front_2", 180); sys.run(0.5)
    sys.lamp("LB2")                   # -> 0.706, the bar really lights through GP17 and the MOSFET

What's real and what's modelled:

* Pico 2: the real ``main_pico.c`` + drivers + core logic, compiled for the PC
  (firmware.py). Its pins, I2C chips and CAN chips are register-level models.
* Every wire, fuse, relay, opto, BTS7960, MOSFET channel, switch and lamp:
  config/wiring.yaml, solved by netlist.py with the models in models.py.
* Shinegle: the existing fake (teryx/sim) on the main CAN bus, its key line
  (KSI) and F-N-R inputs taken from the wiring.
* Pi 5: the real dash gateway (teryx/dash/gateway.py) on the same CAN bus,
  powered from the dash rail through the Pi buck.

Time is virtual. ``run(seconds)`` steps everything in 5 ms steps, so a 30 s
shutdown test takes a few seconds and gives the same answer every time.
"""

from __future__ import annotations

import itertools
import re

import can

from ..canbus import messages as M
from ..canbus.bus import open_bus
from ..config import IO_MAP
from ..eps_toyota import EPS_BITRATE
from ..dash.gateway import Gateway
from ..sim.runner import Simulator
from . import models as MD
from .firmware import DEV_ADS1115, DEV_MCP23017, DEV_PCA9685, Firmware, build
from .netlist import Netlist, is_ground

STEP_S = 0.005
_bus_n = itertools.count()


class System:
    def __init__(self, scenario: str = "manual", relay_active_low: bool = True,
                 bus_spec: str | None = None, wiring_data: dict | None = None):
        self.lib = build()
        self.net = Netlist(wiring_data)
        self.m = MD.build(self.net.devices, relay_active_low)
        self.models = list(self.m.values())
        self.t = 0.0
        self.problems: list[str] = []          # wiring / firmware problems the sim found
        self.eps_frames: dict[int, int] = {}   # frames heard on the steering bus
        self.bench_inputs = {}                 # 0x7E0 from a sim page (live mode)
        # The Pi's own key-off handling (dash/server routes.py watch_key_off): it sees the
        # shutdown request within a second, runs poweroff, and stops talking this long after.
        self.pi_poweroff_s = 6.0
        self.pi_halted = False
        self._pi_shutdown_at: float | None = None
        self._pi_was_on = False

        # One CAN bus: the fake Shinegle, the Pi's gateway and our bridge to the Pico.
        import yaml
        self.main_bitrate = int(yaml.safe_load(IO_MAP.read_text(encoding="utf-8"))["can"]["bitrate"])
        self.bus_spec = bus_spec or f"virtual:rig{next(_bus_n)}"
        self.sim = Simulator(self.bus_spec, scenario, controlbox=False)
        self.sim._t0 = 0.0
        self.dash = Gateway(self.bus_spec, clock=lambda: self.t)
        self._bus = open_bus(self.bus_spec)
        self._map_pico()
        self.fw: Firmware | None = None
        self._flash: bytes | None = None
        self._pico_on = False
        self._settle()

    # ------------------------------------------------------------------ wiring -> firmware
    def _map_pico(self) -> None:
        """Work out from the wiring which Pico pins, chips and CAN boards are connected."""
        pico = self.net.devices["PICO"]["pins"]

        def gp_with(desc):
            for p, spec in pico.items():
                if desc in str(spec.get("desc", "")):
                    return int(p[2:])
            raise KeyError(f"no Pico pin says '{desc}' in wiring.yaml")

        self._gp_list = [int(p[2:]) for p in pico if re.fullmatch(r"GP\d+", p)]
        self.spi_pins = (gp_with("SPI0 SCK"), gp_with("SPI0 MOSI"), gp_with("SPI0 MISO"))
        self.i2c_pins = (gp_with("I2C1 SDA"), gp_with("I2C1 SCL"))
        sda, scl = (f"PICO.GP{g}" for g in self.i2c_pins)
        self.i2c_devs = []     # (dev id, kind, addr)
        for dev_id, model in self.m.items():
            kind = {MD.Mcp23017: DEV_MCP23017, MD.Pca9685: DEV_PCA9685}.get(type(model))
            if kind is None and "ADS1115" in model.dev.get("name", "") and isinstance(model, MD.Chip):
                kind = DEV_ADS1115
            if kind is None:
                continue
            on_bus = self.net.same_net(f"{dev_id}.SDA", sda) and self.net.same_net(f"{dev_id}.SCL", scl)
            addr = MD.i2c_address(model.dev)
            if not on_bus:
                self.problems.append(f"{dev_id} is not on the Pico's I2C (GP{self.i2c_pins[0]}/GP{self.i2c_pins[1]})")
            elif addr is None:
                self.problems.append(f"{dev_id}: no (0xNN) address in its name")
            else:
                self.i2c_devs.append((dev_id, kind, addr))
        sck, mosi, miso = (f"PICO.GP{g}" for g in self.spi_pins)
        self.can_chips = []    # (dev id, cs gp)
        for dev_id, dev in self.net.devices.items():
            if "MCP2515" not in dev.get("name", "") or "CS" not in dev["pins"]:
                continue
            cs = [p for p in self.net.net_pins(f"{dev_id}.CS") if p.startswith("PICO.GP")]
            if not cs:
                continue   # another box's CAN board (the Pi's, the RC box's)
            if not (self.net.same_net(f"{dev_id}.SCK", sck) and self.net.same_net(f"{dev_id}.SI", mosi)
                    and self.net.same_net(f"{dev_id}.SO", miso)):
                self.problems.append(f"{dev_id}: SPI wires don't go to the Pico's SPI0 pins")
            self.can_chips.append((dev_id, int(cs[0].split("GP")[1])))

    def _boot_pico(self, watchdog: bool = False, keep_regs: dict | None = None) -> None:
        fw = Firmware(self.lib)
        fw.set_pins(spi=self.spi_pins, i2c=self.i2c_pins)
        fw.watchdog_reboot(watchdog)
        self.i2c_index = {d: fw.add_i2c(kind, addr) for d, kind, addr in self.i2c_devs}
        self.can_index = {d: fw.add_can(cs) for d, cs in self.can_chips}
        if self._flash is not None:
            fw.load_flash(self._flash)
        if keep_regs is not None:   # a Pico reset: the chips kept power and their registers
            for d, i in self.i2c_index.items():
                fw.i2c_power(i, True)
                for r, v in enumerate(keep_regs[d]):
                    fw.set_reg(i, r, v)
        self.fw = fw
        self._push_inputs()
        fw.start()

    def _halt_pico(self) -> None:
        if self.fw is not None:
            self._flash = self.fw.flash()
            self.problems.extend(e for e in self.fw.errors if e not in self.problems)
            self.fw.close()
            self.fw = None

    # ------------------------------------------------------------------ one step
    def _snap_outputs(self) -> None:
        pico: MD.Pico = self.m["PICO"]
        fw = self.fw
        if fw is None:
            pico.snap = {}
            for d in self.i2c_index if hasattr(self, "i2c_index") else []:
                if isinstance(self.m[d], MD.Mcp23017):
                    self.m[d].regs = None
            return
        pico.snap = fw.pins(self._gp_list)
        for d, i in self.i2c_index.items():
            mdl = self.m[d]
            if isinstance(mdl, MD.Mcp23017):
                mdl.regs = (fw.reg(i, 0x00), fw.reg(i, 0x01), fw.reg(i, 0x14), fw.reg(i, 0x15))
            elif isinstance(mdl, MD.Pca9685):
                mdl.duty = fw.pca_all(i)

    _STATE_ATTRS = ("on", "pos", "pedal", "plugged", "remote", "present", "volts", "connected",
                    "broken", "jammed", "current", "regs", "active_low", "driver_nm", "trq2_broken")

    def _state_key(self) -> tuple:
        """Everything a solve depends on. Same key as last time = same answer, skip the solve."""
        parts = [tuple(sorted(self.net.removed)), tuple(sorted(self.m["PICO"].snap.items()))]
        for mdl in self.models:
            for a in self._STATE_ATTRS:
                if a in mdl.__dict__:
                    parts.append(mdl.__dict__[a])
            if isinstance(mdl, (MD.FuseBlock,)):
                parts.append(tuple(sorted(mdl.blown)))
            elif isinstance(mdl, MD.Pca9685):
                parts.append(tuple(mdl.duty))
        return tuple(parts)

    def _settle(self) -> None:
        self._snap_outputs()
        key = self._state_key()
        if key != getattr(self, "_last_key", None):
            self.net.solve(self.models)
            self._last_key = key
        get = self.net.get
        for mdl in self.models:
            if isinstance(mdl, (MD.Actuator, MD.EpsEcu, MD.Shinegle)):
                mdl.sense(get)
        if self.net.shorts:
            self._problem("short circuit on " + ", ".join(sorted(self.net.shorts)[:6]))
        if self.m["WINCH_SOL"].report(get)["both"]:
            self._problem("both winch coils on at once (in and out together)")
        # Pico power: boot when it comes up, stop when it goes
        on = self.m["PICO"].powered(get)
        if on and not self._pico_on:
            self._boot_pico()
            self._snap_outputs()
            self.net.solve(self.models)
            self._last_key = None
        elif not on and self._pico_on:
            self._halt_pico()
        self._pico_on = on
        if self.fw is not None:
            self._push_inputs()

    def _problem(self, msg: str) -> None:
        if msg not in self.problems:
            self.problems.append(msg)

    def _push_inputs(self) -> None:
        """Net levels -> what the firmware's chips and pins see."""
        fw, get = self.fw, self.net.get
        for d, i in self.i2c_index.items():
            mdl = self.m[d]
            fw.i2c_power(i, mdl.powered(get))
            if isinstance(mdl, MD.Mcp23017):
                for port, letter in ((0, "A"), (1, "B")):
                    mask = level = 0
                    for b in range(8):
                        lv = get(f"{d}.{letter}{b}") if f"{letter}{b}" in mdl.dev["pins"] else None
                        if lv is not None:
                            mask |= 1 << b
                            if lv.v >= 1.6 and lv.duty >= 0.5:
                                level |= 1 << b
                    fw.mcp_in(i, port, mask, level)
            elif not isinstance(mdl, MD.Pca9685):   # ADS1115
                for ch in range(4):
                    fw.ads_mv(i, ch, MD.avg(get(f"{d}.A{ch}")) * 1000.0)
        for d, i in self.can_index.items():
            fw.can_power(i, self.m[d].powered(get))
        for chip, want, listener in (("PICO_CAN", self.main_bitrate, self._main_bus_has_listener()),
                                     ("EPS_CAN", EPS_BITRATE, self._eps_listening())):
            if chip not in self.can_index:
                continue
            i = self.can_index[chip]
            rate_ok = fw.can_mode(i) != 0 or fw.can_bitrate(i) == want
            if not rate_ok:
                self._problem(f"{chip} runs at {fw.can_bitrate(i)} bit/s, its bus is {want}")
            fw.can_acked(i, listener and rate_ok)
        pico = self.m["PICO"]
        for p in pico.dev["pins"]:
            if not re.fullmatch(r"GP\d+", p):
                continue
            gp = int(p[2:])
            lv = get(f"PICO.{p}")
            if 26 <= gp <= 29:
                fw.adc_mv(gp - 26, MD.avg(lv) * 1000.0)
            fw.pin_in(gp, None if lv is None else lv.v >= 1.6)

    def _main_bus(self) -> set[str]:
        """Devices whose CAN H is on the same net as the control box CAN board's."""
        return {p.split(".")[0] for p in self.net.net_pins("PICO_CAN.CANH")}

    def pi_powered(self) -> bool:
        return self.m["PI5"].powered(self.net.get)

    def pi_on(self) -> bool:
        """The Pi is up and on the main CAN bus."""
        return (self.pi_powered() and not self.pi_halted and "PI_CAN" in self._main_bus()
                and self.m["PI_CAN"].powered(self.net.get))

    def shinegle_on(self) -> bool:
        return self.m["SG1202"].ksi(self.net.get) and "SG1202" in self._main_bus()

    def _main_bus_has_listener(self) -> bool:
        return self.pi_on() or self.shinegle_on()

    def _eps_listening(self) -> bool:
        return (self.net.same_net("EPS_CAN.CANH", "EPS_ECU.CANH") and self.m["EPS_ECU"].awake(self.net.get))

    def _can_exchange(self) -> None:
        # Pico -> bus
        if self.fw is not None and "PICO_CAN" in self.can_index:
            for cid, ext, data in self.fw.can_pop(self.can_index["PICO_CAN"]):
                self._bus.send(can.Message(arbitration_id=cid, is_extended_id=ext, data=data))
        ecu: MD.EpsEcu = self.m["EPS_ECU"]
        wired = self._eps_listening()
        if self.fw is not None and "EPS_CAN" in self.can_index:
            for cid, ext, data in self.fw.can_pop(self.can_index["EPS_CAN"]):
                self.eps_frames[cid] = self.eps_frames.get(cid, 0) + 1
                if wired and not ext:
                    ecu.on_frame(cid, data)
        for cid, data in ecu.take():      # the Aqua ECU's replies (ASSUMED frames, models.py)
            if wired and self.fw is not None and "EPS_CAN" in self.can_index:
                self.fw.can_push(self.can_index["EPS_CAN"], cid, data, False)
        # bus -> Pico (the gateway and the fake Shinegle sent onto the same virtual bus)
        while (msg := self._bus.recv(0)) is not None:
            if msg.arbitration_id == M.BENCH_INPUTS.can_id and not msg.is_extended_id:
                self._bench_frame(msg.data)
                continue
            if self.fw is not None and "PICO_CAN" in self.can_index:
                self.fw.can_push(self.can_index["PICO_CAN"], msg.arbitration_id, bytes(msg.data),
                                 msg.is_extended_id)

    def _bench_frame(self, data: bytes) -> None:
        """A sim page's 'force input' ticks (0x7E0) flip the real switches in the wiring."""
        v = M.BENCH_INPUTS.decode(bytes(data))
        for bit, name in M.INPUT_BITS.items():
            if int(v["force_mask"]) & (1 << bit):
                self.bench_inputs[name] = bool(int(v["inputs"]) & (1 << bit))
        b = self.bench_inputs
        if "in.ignition" in b:
            self.key(b["in.ignition"])
        if "in.brake" in b:
            self.brake(b["in.brake"])
        if "in.park" in b:
            self.park(b["in.park"])
        if "in.trailer" in b:
            self.trailer(b["in.trailer"])
        if "in.reverse" in b:
            self.fnr("reverse" if b["in.reverse"] else "neutral")
        if "in.winch_remote" in b:
            self.winch_switch("cab", "in" if b["in.winch_remote"] else None)

    def _tick_pi_and_shinegle(self) -> None:
        get = self.net.get
        sg: MD.Shinegle = self.m["SG1202"]
        veh = self.sim.vehicle
        if self.sim.scenario.name == "manual":
            veh.inp.direction = sg.direction(get)
            veh.inp.throttle = sg.throttle(get)      # through the pedal wires (models.Shinegle)
            veh.inp.brake = 1.0 if self.m["BRAKE_SW"].on else 0.0
            veh.inp.handbrake = self.m["PARK_SW"].on   # foot pedal park brake: a cable, the switch only senses it
            # a shorted or open-ground throttle wire is the controller's own throttle fault
            veh.forced_faults = set(self.sim.manual_faults) | ({"throttle"} if sg.throttle_fault(get) else set())
        else:   # a scripted drive: the F-N-R switch follows it
            self.m["FNR"].pos = veh.inp.direction if veh.inp.direction != "neutral" else None
        veh.drive_inhibit = not sg.ksi(get)
        self.m["EPS_ECU"].road_kmh = veh.speed_kmh
        self.sim.links["shinegle"] = self.shinegle_on()
        self.sim.tick(STEP_S, self.t)
        powered = self.pi_powered()
        if powered and not self._pi_was_on and self.t > 0:   # power back: the Pi boots afresh
            self.dash.node.close()
            self.dash = Gateway(self.bus_spec, clock=lambda: self.t)
        if not powered:
            self.pi_halted = False
            self._pi_shutdown_at = None
        self._pi_was_on = powered
        pi = self.pi_on()
        if pi and self.dash.snapshot().get("pico.shutdown_request"):
            if self._pi_shutdown_at is None:
                self._pi_shutdown_at = self.t + 1.0 + self.pi_poweroff_s
            elif self.t >= self._pi_shutdown_at:
                self.pi_halted = True
                pi = False
        elif pi:
            self._pi_shutdown_at = None
        self.dash.node.enabled = pi
        for msg, v, raw in self.dash.node.poll():
            if pi:
                self.dash._on_frame(msg, v, raw, self.t)
        if pi:
            self.dash._send_periodic(self.t)

    def step(self) -> None:
        """5 ms of everything."""
        if self.fw is not None:
            alive = self.fw.run_us(int(STEP_S * 1e6))
            if not alive:
                reason = self.fw.exit_reason
                if reason == "watchdog":
                    self.problems.append("Pico watchdog reset")
                    old = self.fw
                    self._flash = old.flash()
                    regs = {d: [old.reg(i, r) for r in range(256)] for d, i in self.i2c_index.items()}
                    old.close()     # the browser has one copy of the firmware: stop it before the reboot
                    self._boot_pico(watchdog=True, keep_regs=regs)
                else:
                    self._halt_pico()
                    self._pico_on = False
        self._can_exchange()
        self._tick_pi_and_shinegle()
        self._can_exchange()
        self._settle()
        for mdl in self.models:
            if hasattr(mdl, "advance"):
                mdl.advance(STEP_S)
        self.t += STEP_S

    def run(self, seconds: float, until=None) -> bool:
        """Run for up to ``seconds`` of virtual time; stop early once ``until()`` is true."""
        for _ in range(max(1, round(seconds / STEP_S))):
            self.step()
            if until is not None and until():
                return True
        return until is None or bool(until())

    def close(self) -> None:
        self._halt_pico()
        self.dash.node.close()
        for n in (self.sim.sg_node, self.sim.bench_node):
            n.close()
        self._bus.shutdown()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ------------------------------------------------------------------ hands on the Teryx
    def key(self, on: bool) -> None:
        self.m["KEY"].on = on
        self.m["KIT_KEY"].on = on      # assumed the same key (wiring.yaml KIT_KEY check)

    def brake(self, on: bool) -> None:
        self.m["BRAKE_SW"].on = on

    def park(self, on: bool) -> None:
        self.m["PARK_SW"].on = on

    def fnr(self, pos: str) -> None:
        self.m["FNR"].pos = None if pos == "neutral" else pos

    def throttle(self, pedal: float) -> None:
        self.m["THROTTLE"].pedal = max(0.0, min(1.0, pedal))

    def steer(self, nm: float) -> None:
        """How hard the driver turns the wheel, Nm (+ = right). 0 = hands off."""
        self.m["EPS_COL"].driver_nm = float(nm)

    def backup_lights(self, on: bool) -> None:
        self.m["LIMP_SW"].on = on

    def estop(self, pressed: bool) -> None:
        self.m["ESTOP"].on = pressed

    def trailer(self, plugged: bool) -> None:
        self.m["TRAILER"].plugged = plugged
        self.m["LB_TRL"].present = plugged

    def winch_switch(self, where: str, pos: str | None) -> None:
        """where: 'cab' or 'winch'; pos: 'in', 'out' or None (let go)."""
        self.m["HSW_CAB" if where == "cab" else "HSW_WINCH"].pos = pos

    def winch_remote(self, pos: str | None) -> None:
        self.m["WINCH_SOL"].remote = pos

    def winch_breaker(self, on: bool) -> None:
        self.m["BRK_WINCH"].on = not on      # the model's `on` means tripped (normally closed)

    def battery(self, volts: float) -> None:
        self.m["BAT12"].volts = volts

    def pull_fuse(self, ref: str, pulled: bool = True) -> None:
        """'FB.F8' pulls a fuse block way; a wire id ('P08') cuts that wire / its inline fuse."""
        if "." in ref:
            dev, way = ref.split(".")
            (self.m[dev].blown.add if pulled else self.m[dev].blown.discard)(way)
        elif pulled:
            self.net.cut(ref)
        else:
            self.net.mend(ref)

    # ------------------------------------------------------------------ what you'd see
    def lamp(self, dev: str, part: str | None = None) -> float:
        return self.m[dev].level(self.net.get, part)

    def trailer_pin(self, pin: str) -> float:
        return self.m["TRAILER"].level(self.net.get, pin)

    def relay(self, n: int) -> bool:
        board, ch = ("RELAYS", n) if n <= 8 else ("RELAYS2", n - 8)
        return self.m[board].coil(self.net.get, ch)

    def powered(self, dev: str) -> bool:
        mdl = self.m[dev]
        if hasattr(mdl, "powered"):
            return mdl.powered(self.net.get)
        if hasattr(mdl, "on"):
            return mdl.on(self.net.get)
        raise TypeError(f"{dev} has no power state")

    def volts(self, pin: str) -> float:
        return MD.volts(self.net.get(pin))

    def level(self, pin: str):
        return self.net.get(pin)

    def eps(self) -> dict:
        """The Aqua ECU: mode (manual, booting, normal, limp, fault), assist, column angle."""
        return self.m["EPS_ECU"].report(self.net.get)

    def actuator(self, dev: str) -> MD.Actuator:
        return self.m[dev]

    def report(self) -> dict:
        get = self.net.get
        return {d: r for d, mdl in self.m.items() if (r := mdl.report(get))}

    def ground_ok(self, dev: str, pin: str = "GND") -> bool:
        return is_ground(self.net.get(f"{dev}.{pin}"))
