"""The whole-Teryx sim behind a dash screen with working buttons (dash/web/rig/).

``WebRig`` wraps :class:`teryx.rig.System` for a web page. The same code runs:

* on GitHub Pages, in Pyodide in a web worker, with the WebAssembly build of the
  Pico firmware (dash/web/rig/worker.js), so it works on a phone with nothing else on;
* on a PC under plain Python (tests, and ``python -m teryx rig-web``) with the
  normal compiled firmware.

The dash screen talks to it with the same messages it sends the Pi's server over
its websocket (docs/DASH_API.md): request, hold, lock, setting. The control panel
next to the screen sends ``panel`` commands: the key, pedals, F-N-R, the steering
wheel, the winch switches, pulling fuses, cutting wires, faults.
"""

from __future__ import annotations

import re

from . import models as MD
from .system import STEP_S, System

LIGHTS = ("LB1", "LB2", "LB3", "LB4", "LB_INT", "HEAD_L", "HEAD_R", "TAIL_L", "TAIL_R",
          "FLOOD_L", "FLOOD_R", "BEACON", "LB_TRL")
ACTUATORS = ("ACT_4WD", "ACT_DIFF", "ACT_TRAY")
MAX_STEP_S = 0.25          # never catch up more than this in one go (a phone tab that was asleep)


class WebRig:
    def __init__(self, key_on: bool = True):
        self.s = System()
        self.s.park(True)
        self.s.key(key_on)
        self._acks: dict[int, tuple] = {}        # setting key -> (name the dash used, ack event)
        self.replies: list[dict] = []
        self.inputs = {"key": key_on, "park": True, "brake": False, "fnr": "neutral", "throttle": 0.0,
                       "steer": 0.0, "estop": False, "trailer": False, "backup_lights": False,
                       "winch_cab": None, "winch_remote": None, "battery": MD.V_BATT,
                       "mode": "eco", "ecu_silent": False, "trq_wire_off": False}
        self.fuses = self._fuse_list()

    # ------------------------------------------------------------------ time
    def tick(self, seconds: float) -> None:
        self.s.run(max(STEP_S, min(seconds, MAX_STEP_S)))
        for k, (name, ev) in list(self._acks.items()):
            if ev.is_set():
                self.replies.append({"type": "setting_ack", "key": name, "ok": True})
                del self._acks[k]

    # ------------------------------------------------------------------ the dash screen
    def ui(self, msg: dict) -> None:
        """A message from the dash screen, exactly as it sends it to the Pi's websocket."""
        g = self.s.dash
        kind = msg.get("type")
        if not (self.s.pi_on() and self.s.powered("SCREEN")):
            return                                 # the screen is off: you can't press anything
        if kind == "request":
            g.request(msg["id"], msg["value"])
        elif kind == "hold":
            g.hold(msg["id"], msg["value"], msg.get("secs", 0))
        elif kind == "lock":
            g.lock(msg["cmd"], msg.get("digits"))
        elif kind == "setting":
            from ..canbus import messages as M
            k = int(M.SETTING_KEYS.get(msg["key"], msg["key"]))
            g.set_setting(k, int(msg["value"]), timeout=0)
            self._acks[k] = (msg["key"], g._acks[k])
        elif kind == "sim":
            self.s.sim.apply(msg.get("cmd", {}))

    def dash_state(self) -> dict:
        """What the Pi's server would push to the screen."""
        st = self.s.dash.snapshot()
        for k, v in self.s.sim.sensors.state().items():
            st.setdefault(k, v)
        st["link.online"] = self.s.pi_on()
        st["link.rig"] = True
        return st

    # ------------------------------------------------------------------ the hands-on panel
    def panel(self, cmd: dict) -> None:
        s, i = self.s, self.inputs
        for name, value in cmd.items():
            if name == "key":
                s.key(bool(value))
            elif name == "park":
                s.park(bool(value))
            elif name == "brake":
                s.brake(bool(value))
            elif name == "fnr":
                if value not in ("forward", "neutral", "reverse"):
                    raise ValueError(f"F-N-R is forward, neutral or reverse, not {value}")
                s.fnr(value)
            elif name == "throttle":
                value = max(0.0, min(1.0, float(value)))
                s.throttle(value)
            elif name == "steer":
                value = max(-10.0, min(10.0, float(value)))
                s.steer(value)
            elif name == "estop":
                s.estop(bool(value))
            elif name == "trailer":
                s.trailer(bool(value))
            elif name == "backup_lights":
                s.backup_lights(bool(value))
            elif name == "winch_cab":
                s.winch_switch("cab", value or None)
            elif name == "winch_remote":
                s.winch_remote(value or None)
            elif name == "battery":
                value = max(9.0, min(14.8, float(value)))
                s.battery(value)
            elif name == "mode":
                s.sim.vehicle.inp.mode = value
            elif name == "ecu_silent":
                s.m["EPS_ECU"].silent = bool(value)
            elif name == "trq_wire_off":
                s.m["EPS_COL"].trq2_broken = bool(value)
            elif name == "shinegle_fault":            # [name, on]
                s.sim.apply({"shinegle_fault": value})
                continue
            elif name == "fuse":                      # [ref, pulled]
                ref, pulled = value
                s.pull_fuse(ref, bool(pulled))
                self.fuses[ref]["pulled"] = bool(pulled)
                continue
            elif name == "restart":
                self.__init__(key_on=True)
                return
            else:
                raise ValueError(f"unknown panel control {name}")
            i[name] = value

    def _fuse_list(self) -> dict:
        """Every fuse you can pull: fuse block ways and inline fuses, with what they feed."""
        out = {}
        devs = self.s.net.devices
        for blk in ("FB", "FB2"):
            for pin, spec in devs.get(blk, {}).get("pins", {}).items():
                if re.fullmatch(r"F\d+", pin) and isinstance(spec, dict):
                    out[f"{blk}.{pin}"] = {"what": spec.get("desc", ""), "amps": spec.get("fuse_a"), "pulled": False}
        for w in self.s.net.d["wires"]:
            if w.get("fuse") and not w["from"].startswith(("FB.", "FB2.")):
                out[w["id"]] = {"what": f"{w['from'].split('.')[0]} to {w['to'].split('.')[0]}",
                                "amps": w["fuse"], "pulled": False}
        return dict(sorted(out.items(), key=lambda kv: (not kv[0].startswith("FB"), kv[0])))

    def panel_state(self) -> dict:
        s = self.s
        get = s.net.get
        snap = s.dash.snapshot()
        lights = {}
        for d in LIGHTS:
            if d in s.m:
                lights[d] = {k: round(v, 2) for k, v in s.m[d].report(get).items() if isinstance(v, float)}
        relays = {n: s.relay(n) for n in range(1, 11)}
        acts = {d: round(s.m[d].pos, 3) for d in ACTUATORS if d in s.m}
        win = s.m["WINCH_SOL"].report(get)
        return {
            "t": round(s.t, 2),
            "inputs": self.inputs,
            "pico_on": s.fw is not None,
            "pi_on": s.pi_on(),
            "screen_on": s.powered("SCREEN") and s.pi_on(),
            "shinegle": s.m["SG1202"].report(get),
            "eps": s.eps(),
            "speed_kmh": round(s.sim.vehicle.speed_kmh, 1),
            "soc": round(s.sim.vehicle.soc, 1),
            "lights": lights,
            "relays": relays,
            "actuators": acts,
            "winch": "in" if win.get("coil_in") else "out" if win.get("coil_out") else None,
            "fuses": self.fuses,
            "shinegle_faults": sorted(s.sim.manual_faults),
            "shinegle_fault_names": list(s.sim.status()["shinegle_faults"]),
            "mc_faults": snap.get("mc.faults", []),
            "pico_faults": snap.get("pico.faults", []),
            "problems": list(s.problems)[-8:],
        }

    def close(self) -> None:
        self.s.close()
