"""Runs the fake Shinegle and the fake control box on a CAN bus.

Each fake device gets its own bus connection, exactly like separate boxes on a
real bus. The control box only knows the speed because it hears the Shinegle
frames on the bus, the same as the real Pico will.
"""

from __future__ import annotations

import logging
import threading
import time

from ..canbus import messages as M
from ..canbus import shinegle as SG
from ..canbus.bus import open_bus
from ..canbus.node import Node
from ..canbus.registry import BY_NAME
from .controlbox import ControlBox
from .scenarios import SCENARIOS
from .sensors import FakeSensors
from .vehicle import Vehicle

log = logging.getLogger("teryx.sim")

TICK_HZ = 50


class Simulator:
    def __init__(self, bus_spec: str = "virtual", scenario: str = "idle",
                 controlbox: bool = True):
        self.bus_spec = bus_spec
        self.vehicle = Vehicle()
        self.sg_node = Node(open_bus(bus_spec))
        self.bench_node = Node(open_bus(bus_spec))
        self.cb = ControlBox() if controlbox else None
        self.cb_node = Node(open_bus(bus_spec)) if controlbox else None
        self.links = {"shinegle": True, "controlbox": True}
        self.bench_inputs: dict[str, bool] = {}     # forced Pico inputs (0x7E0)
        self.bench_faults: set[str] = set()         # injected Pico faults (0x7E0)
        self.manual_faults: set[str] = set()        # Shinegle faults ticked on the sim page
        self.scenario = None
        self.scenario_t = 0.0
        self.speed_factor = 1.0
        self.paused = False                        # freezes the scenario and the physics
        self.sensors = FakeSensors()               # tilt + GPS, not fitted yet
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._t0 = time.monotonic()
        self.set_scenario(scenario)

    # ------------------------------------------------------------ control
    def set_scenario(self, name: str) -> None:
        if name not in SCENARIOS:
            raise ValueError(f"unknown scenario '{name}', try: {', '.join(SCENARIOS)}")
        with self._lock:
            if self.scenario and hasattr(self.scenario, "stop"):
                self.scenario.stop(self)
            v = self.vehicle.inp
            v.throttle = v.brake = 0.0
            v.grade_pct = 0.0
            v.mode = "eco"
            v.handbrake = False
            self.paused = False
            self.vehicle.forced_faults = set(self.manual_faults)
            self.scenario = SCENARIOS[name]()
            self.scenario_t = 0.0
            self.scenario.start(self)
            log.info("scenario: %s", name)

    def apply(self, cmd: dict) -> None:
        """Changes from the sim page. Keys are optional."""
        with self._lock:
            v, i = self.vehicle, self.vehicle.inp
            if "scenario" in cmd:
                self.set_scenario(cmd["scenario"])
            if cmd.get("restart"):                  # start the current scenario again
                self.set_scenario(self.scenario.name)
            if "paused" in cmd:
                self.paused = bool(cmd["paused"])
            if "demo_step" in cmd:                  # jump to a step of a scripted scenario
                if not hasattr(self.scenario, "seek_step"):
                    raise ValueError(f"scenario '{self.scenario.name}' has no steps")
                k = int(cmd["demo_step"])
                if not 0 <= k < len(self.scenario.STEPS):
                    k = 0
                self.scenario_t = self.scenario.seek_step(k)
                self.scenario.update(self, self.scenario_t, 0.0)
            for key in ("throttle", "brake", "grade_pct"):
                if key in cmd:
                    setattr(i, key, float(cmd[key]))
                    if self.scenario.name != "manual" and key != "grade_pct":
                        self.set_scenario("manual")
                        setattr(i, key, float(cmd[key]))
            if "direction" in cmd:
                i.direction = cmd["direction"]
            if "mode" in cmd:
                i.mode = cmd["mode"]
            if "soc" in cmd:
                v.soc = float(cmd["soc"])
            if "ambient" in cmd:
                v.ambient = float(cmd["ambient"])
            if "cool_down" in cmd:
                v.motor_temp = v.controller_temp = v.battery_temp = v.ambient + 5
            if "shinegle_fault" in cmd:
                name, on = cmd["shinegle_fault"]
                (self.manual_faults.add if on else self.manual_faults.discard)(name)
                v.forced_faults = set(self.manual_faults)
            if "bench_fault" in cmd:
                name, on = cmd["bench_fault"]
                (self.bench_faults.add if on else self.bench_faults.discard)(name)
            if "input" in cmd:
                name, on = cmd["input"]
                if on is None:
                    self.bench_inputs.pop(name, None)
                else:
                    self.bench_inputs[name] = bool(on)
            if "link" in cmd:
                name, on = cmd["link"]
                self.links[name] = bool(on)
            if "sensor" in cmd:                     # {"sensor": ["gps", false]}
                name, on = cmd["sensor"]
                if name in self.sensors.enabled:
                    self.sensors.enabled[name] = bool(on)
            if "tilt" in cmd:                       # {"tilt": {"roll": 28}} holds a tilt, {"tilt": null} lets go
                self.sensors.hold = dict(cmd["tilt"]) if cmd["tilt"] else None
            if "speed_factor" in cmd:
                self.speed_factor = max(0.1, min(10.0, float(cmd["speed_factor"])))

    def status(self) -> dict:
        with self._lock:
            v = self.vehicle
            return {
                "scenario": self.scenario.name,
                "scenarios": [{"name": c.name, "label": c.label, "help": c.help}
                              for c in SCENARIOS.values()],
                "bus": self.bus_spec,
                "controlbox": self.cb is not None,
                "links": dict(self.links),
                "inputs": dict(self.bench_inputs),
                "bench_faults": sorted(self.bench_faults),
                "manual_faults": sorted(self.manual_faults),
                "speed_factor": self.speed_factor,
                "paused": self.paused,
                "demo": self.demo_info(),
                "sensors": dict(self.sensors.enabled),
                "driver": {"throttle": v.inp.throttle, "brake": v.inp.brake,
                           "direction": v.inp.direction, "mode": v.inp.mode,
                           "grade_pct": v.inp.grade_pct},
                "mc": v.mc(),
                "shinegle_faults": list(SG.FAULT_BITS.values()),
                "bench_fault_names": list(M.BENCH_FAULTS.values()),
                "input_names": list(M.INPUT_BITS.values()),
            }

    def demo_info(self) -> dict | None:
        """Where a scripted scenario is up to (caption, step, progress), or None."""
        with self._lock:
            if not hasattr(self.scenario, "info"):
                return None
            return {**self.scenario.info(self.scenario_t), "paused": self.paused}

    # ------------------------------------------------------------ loop
    def tick(self, dt: float, now: float) -> None:
        with self._lock:
            sdt = 0.0 if self.paused else dt * self.speed_factor
            self.scenario_t += sdt
            if sdt:
                self.scenario.update(self, self.scenario_t, sdt)
                self.vehicle.step(sdt)

            # Fake Shinegle
            self.sg_node.enabled = self.links["shinegle"]
            mc = self.vehicle.mc()
            self.sensors.step(sdt, mc.get("mc.speed", 0.0), self.vehicle.inp.grade_pct, mc.get("mc.direction", "forward"))
            for msg, values in SG.encode(mc):
                self.sg_node.send_due(msg, lambda values=values: values, now)

            # Bench inputs for the Pico (also understood by the firmware's host build)
            mask = M.names_to_bits(self.bench_inputs, M.INPUT_BITS)
            bits = M.names_to_bits([n for n, on in self.bench_inputs.items() if on], M.INPUT_BITS)
            self.bench_node.send_due(M.BENCH_INPUTS, lambda: {
                "inputs": bits, "force_mask": mask,
                "fault_inject": M.names_to_bits(self.bench_faults, M.BENCH_FAULTS)}, now)

            # Fake control box
            if self.cb:
                cb_now = now - self._t0
                for msg, values, _raw in self.cb_node.poll():
                    if msg is not None:
                        self.cb.on_frame(msg.name, values, cb_now)
                self.cb.pedal_raw = self.vehicle.pedal_raw()   # the pedal sensor is wired to the Pico
                self.cb.step(dt, cb_now)
                # ...and the Pico's regen request goes to the Shinegle (how is still TBC)
                self.vehicle.regen_request = self.cb.regen.out.request_pct / 100
                # ...and so does its throttle hold during a shift from a standstill (also TBC)
                self.vehicle.throttle_hold = self.cb.throttle_hold
                self.cb_node.enabled = self.links["controlbox"]
                for name, values in self.cb.frames():
                    self.cb_node.send_due(BY_NAME[name], lambda values=values: values, now)
                while self.cb.acks:
                    self.cb_node.send(M.PICO_SETTINGS_ACK, self.cb.acks.pop(0))

    def run(self) -> None:
        period = 1 / TICK_HZ
        last = time.monotonic()
        while not self._stop.is_set():
            now = time.monotonic()
            try:
                self.tick(now - last, now)
            except Exception:  # keep the bench running, but say what broke
                log.exception("sim tick failed")
            last = now
            self._stop.wait(max(0.0, period - (time.monotonic() - now)))

    def start(self) -> "Simulator":
        self._thread = threading.Thread(target=self.run, name="teryx-sim", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(2)
        for n in (self.sg_node, self.bench_node, self.cb_node):
            if n:
                n.close()
