"""Dash gateway: the Pi side of the CAN bus.

* Reads every frame, decodes it and keeps one flat state dict keyed by the
  io-map ids (mc.speed, an.diff_pos, light.front_1, pico.faults ...).
* Turns UI requests into 0x700-0x704 frames, with the agreed timing:
  heartbeat 10 Hz, lights/drive on change + every 1 s, hold-to-run 10 Hz while
  held (stops sending 300 ms after the UI goes quiet), settings on change.

The UI never touches CAN directly, so the same UI runs on the sim, on vcan
or on the real bus.
"""

from __future__ import annotations

import logging
import threading
import time

from ..canbus import messages as M
from ..canbus import shinegle as SG
from ..canbus.bus import open_bus
from ..canbus.node import Node
from ..lights import LAMPS, LIGHT_SHOW
from ..vehicle_lock import encode_digits

log = logging.getLogger("teryx.dash")

ONLINE_TIMEOUT_S = 1.0
HOLD_TIMEOUT_S = 0.3
SETTINGS_RESEND_S = 5.0

LIGHT_IDS = {"light.front_1": "front_1", "light.front_2": "front_2", "light.front_3": "front_3",
             "light.front_4": "front_4", "light.interior": "interior"}
# 0x706 levels, 0-255 (docs/lights.md)
LIGHT2_LEVELS = {"light.head_level": 255, "light.tail": 0, "light.rear_level": 0,
                 "light.trailer_bar": 0, "light.beacon": 0, "light.beacon_white": 0}


class Gateway:
    def __init__(self, bus_spec: str = "virtual"):
        self.bus_spec = bus_spec
        self.node = Node(open_bus(bus_spec))
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.started = time.monotonic()
        # Start from defaults so the UI never sees a missing mc.* value, even if
        # the real Shinegle turns out not to send some of them.
        self.state: dict = dict(SG.MC_DEFAULTS)
        self.last_shinegle = -1e9
        self.seen: dict[str, float] = {}        # message name -> monotonic time
        self.frame_counts: dict[str, int] = {}
        self.unknown_ids: dict[int, int] = {}   # handy when sniffing the real Shinegle
        # What the dash is asking for
        self.req = {
            "light.front_1": 0, "light.front_2": 0, "light.front_3": 0, "light.front_4": 0,
            "light.interior": 0, "light.effect": "none", "light.rear": "auto",
            "light.head": "off", **LIGHT2_LEVELS, "light.show": "none",
            "act.4wd": 0, "act.diff": 0, "winch.armed": False,
        }
        self.holds = {"act.tray": (0, 0.0), "winch": (0, 0.0)}
        self._hold_active = False
        self.winch_timed_s = 0   # timed pull length for the current winch hold, 0 = plain hold
        self._dirty = {"lights": True, "lights2": True, "drive": True}
        self._last_reject_count = None
        self._lock_counter = 0
        # Sentry (docs/sentry.md): the heartbeat says "sentry" so the Pico keeps power on after key-off
        self.sentry = False
        # Settings: what we want the Pico to use, and what it has acked
        self.wanted_settings = M.default_settings()
        self.settings: dict[str, int] = {}
        self._acks: dict[int, threading.Event] = {}
        self._last_settings_push = -1e9
        self.last_ack: dict | None = None
        self.listeners: list = []   # callables(frame_name, values) for plugins / logging

    # ------------------------------------------------------------ public API
    def snapshot(self) -> dict:
        now = time.monotonic()
        with self._lock:
            s = dict(self.state)
            s["mc.online"] = now - self.last_shinegle < ONLINE_TIMEOUT_S
            s["pico.online"] = now - self.seen.get("PICO_STATUS", -1e9) < ONLINE_TIMEOUT_S
            for k, v in self.req.items():
                s[f"req.{k}"] = v
            s["req.act.tray"] = self.holds["act.tray"][0]
            s["req.winch"] = self.holds["winch"][0]
            s["dash.bus"] = self.bus_spec
            s["dash.uptime_s"] = round(now - self.started, 1)
            s["dash.settings"] = dict(self.settings)
            return s

    def request(self, id: str, value) -> None:
        """A tap on the dash. See docs/DASH_API.md for ids and values."""
        with self._lock:
            if id in LIGHT_IDS:
                self.req[id] = max(0, min(255, int(value)))
                self._dirty["lights"] = True
            elif id == "light.effect":
                if value not in M.LIGHT_EFFECT.values():
                    raise ValueError(f"unknown effect {value}")
                self.req[id] = value
                self._dirty["lights"] = True
            elif id == "light.rear":
                if value not in ("off", "on", "auto"):
                    raise ValueError("light.rear must be off, on or auto")
                self.req[id] = value
                self._dirty["lights"] = True
            elif id == "light.head":
                if value not in ("off", "low", "high"):
                    raise ValueError("light.head must be off, low or high")
                self.req[id] = value
                self._dirty["lights2"] = True
            elif id in LIGHT2_LEVELS:
                self.req[id] = max(0, min(255, int(value)))
                self._dirty["lights2"] = True
            elif id == "light.show":
                if value not in LIGHT_SHOW.values():
                    raise ValueError(f"unknown light show {value}")
                self.req[id] = value
                self._dirty["lights2"] = True
            elif id == "act.4wd":
                self.req[id] = 1 if value in (1, True, "4wd", "1") else 0
                self._dirty["drive"] = True
            elif id == "act.diff":
                self.req[id] = max(0, min(100, int(value)))
                self._dirty["drive"] = True
            elif id == "winch.armed":
                self.req[id] = bool(value)
                self._send_hold(force=True)
            else:
                raise ValueError(f"unknown request id {id}")

    def hold(self, id: str, value: int, secs: int = 0) -> None:
        """Hold-to-run. Call every ~100 ms while the button is down; 0 to release.

        For the winch, ``secs`` > 0 makes it a timed pull: the dash keeps calling this
        for the whole pull and the control box stops the winch after ``secs`` by itself.
        """
        if id not in self.holds:
            raise ValueError(f"unknown hold id {id}")
        value = max(-1, min(1, int(value)))
        with self._lock:
            if id == "winch":
                self.winch_timed_s = max(0, min(255, int(secs or 0))) if value else 0
            self.holds[id] = (value, time.monotonic())
            if value == 0:
                self._send_hold(force=True)

    def lock(self, cmd: str, digits: str | None = None) -> None:
        """Vehicle lock (docs/vehicle-lock.md). cmd: lock, unlock, verify, set_pin, set_puk, remove,
        remote (docs/remote-access.md: locks once stopped 10 s or key off).

        The control box decides and answers on 0x716 (lock.* in the state). The PIN only
        passes through here; nothing on the Pi keeps it.
        """
        codes = {v: k for k, v in M.LOCK_CMD.items()}
        if cmd not in codes:
            raise ValueError(f"unknown lock command {cmd}")
        with self._lock:
            self._lock_counter = (self._lock_counter + 1) & 0xFF
            self.node.send(M.PI_LOCK, {"cmd": codes[cmd], **encode_digits(digits or ""),
                                       "counter": self._lock_counter})

    def set_sentry(self, on: bool) -> None:
        """Ask the Pico to keep power on after key-off (docs/sentry.md). It still cuts power
        if the 12V stays under setting 32, whatever this says."""
        self.sentry = bool(on)

    def set_setting(self, key, value: int, timeout: float = 1.0) -> bool:
        """Send one 0x704 setting and wait for the 0x714 ack. Key is a number or a name."""
        k = M.SETTING_KEYS.get(key, key)
        ev = threading.Event()
        self._acks[int(k)] = ev
        if k in M.SETTINGS:
            self.wanted_settings[M.SETTINGS[k][0]] = int(value)
        self.node.send(M.PI_SETTINGS, {"key": int(k), "value": int(value)})
        return ev.wait(timeout)

    def send_frame(self, name: str, values: dict) -> None:
        from ..canbus.registry import BY_NAME
        self.node.send(BY_NAME[name], values)

    # ------------------------------------------------------------ sending
    def _lights_values(self) -> dict:
        r = self.req
        return {**{LIGHT_IDS[k]: r[k] for k in LIGHT_IDS},
                "effect": M.enum_value(M.LIGHT_EFFECT, r["light.effect"]),
                "rear_on": int(r["light.rear"] == "on"),
                "rear_auto": int(r["light.rear"] == "auto")}

    def _lights2_values(self) -> dict:
        r = self.req
        lvl = r["light.head_level"] or 255
        return {"head_low": lvl if r["light.head"] == "low" else 0,
                "head_high": lvl if r["light.head"] == "high" else 0,
                "tail": r["light.tail"], "rear": r["light.rear_level"],
                "trailer_bar": r["light.trailer_bar"], "beacon": r["light.beacon"], "beacon_white": r["light.beacon_white"],
                "show": M.enum_value(LIGHT_SHOW, r["light.show"])}

    def _drive_values(self) -> dict:
        return {"fourwd_req": self.req["act.4wd"], "diff_target": self.req["act.diff"]}

    def _send_hold(self, force: bool = False) -> None:
        now = time.monotonic()
        tray, t_at = self.holds["act.tray"]
        winch, w_at = self.holds["winch"]
        tray = tray if now - t_at < HOLD_TIMEOUT_S else 0
        winch = winch if now - w_at < HOLD_TIMEOUT_S else 0
        active = bool(tray or winch)
        if active or force or self._hold_active:
            # One last zero frame when released, then go quiet
            self.node.send(M.PI_HOLD, {"tray": tray, "winch": winch,
                                       "winch_armed": int(self.req["winch.armed"]),
                                       "winch_timed_s": self.winch_timed_s if winch else 0})
        self._hold_active = active

    def _send_periodic(self, now: float) -> None:
        with self._lock:
            self.node.send_due(M.PI_HEARTBEAT, lambda: {"dash_state": 3 if self.sentry else 1}, now)
            if self._dirty["lights"]:
                self._dirty["lights"] = False
                self.node.send(M.PI_LIGHTS, self._lights_values())
                self.node._last_sent[M.PI_LIGHTS.can_id] = now
            else:
                self.node.send_due(M.PI_LIGHTS, self._lights_values, now)
            if self._dirty["lights2"]:
                self._dirty["lights2"] = False
                self.node.send(M.PI_LIGHTS2, self._lights2_values())
                self.node._last_sent[M.PI_LIGHTS2.can_id] = now
            else:
                self.node.send_due(M.PI_LIGHTS2, self._lights2_values, now)
            if self._dirty["drive"]:
                self._dirty["drive"] = False
                self.node.send(M.PI_DRIVE, self._drive_values())
                self.node._last_sent[M.PI_DRIVE.can_id] = now
            else:
                self.node.send_due(M.PI_DRIVE, self._drive_values, now)
            if now - self.node._last_sent.get(M.PI_HOLD.can_id, 0) >= 0.1:
                self.node._last_sent[M.PI_HOLD.can_id] = now
                self._send_hold()
            # Pico says it is on defaults: push our settings again (rate-limited)
            if self.state.get("pico.on_defaults") and now - self._last_settings_push > SETTINGS_RESEND_S:
                self._last_settings_push = now
                defaults = M.default_settings()
                for key, (name, *_rest) in M.SETTINGS.items():
                    if self.wanted_settings[name] != defaults[name]:
                        self.node.send(M.PI_SETTINGS, {"key": key, "value": self.wanted_settings[name]})

    # ------------------------------------------------------------ receiving
    def _on_frame(self, msg, v: dict, raw, now: float) -> None:
        with self._lock:
            if msg is None:
                self.unknown_ids[raw.arbitration_id] = self.unknown_ids.get(raw.arbitration_id, 0) + 1
                return
            self.seen[msg.name] = now
            self.frame_counts[msg.name] = self.frame_counts.get(msg.name, 0) + 1
            st = self.state
            if msg.sender == "shinegle":
                self.last_shinegle = now
                SG.merge(st, msg, v)
            elif msg.name == "PICO_STATUS":
                st["pico.faults"] = M.bits_to_names(v["fault_bits"], M.FAULT_BITS)
                for bit, name in M.INPUT_BITS.items():
                    st[name] = bool(int(v["inputs"]) & (1 << bit))
                st["pico.state"] = M.PICO_STATE[v["state"]]
                st["pico.on_defaults"] = bool(v["on_defaults"])
                st["pico.reject"] = M.REJECT_REASON.get(v["reject_reason"], "none")
                st["pico.reject_text"] = M.REJECT_TEXT.get(st["pico.reject"], "")
                if st["pico.reject"] == "interlock" and st.get("lock.state") == "locked":
                    st["pico.reject_text"] = "Vehicle is locked"
                st["pico.reject_count"] = v["reject_count"]
                st["winch.armed"] = bool(v["winch_armed"])
                st["pico.speed"] = None if v["speed"] == 255 else v["speed"]
                st["pico.speed_valid"] = bool(v["speed_valid"])
                st["pico.parked"] = bool(v["parked"])
                st["pico.shutdown_request"] = bool(v["shutdown_request"])
                st["act.4wd_wait"] = bool(v.get("fourwd_wait", 0))
                st["act.diff_wait"] = bool(v.get("diff_wait", 0))
                st["pico.throttle_hold"] = bool(v.get("throttle_hold", 0))
                st["pico.sentry_hold"] = bool(v.get("sentry_hold", 0))
                st["pico.sentry_flat"] = bool(v.get("sentry_flat", 0))
                if self._last_reject_count is not None and v["reject_count"] != self._last_reject_count:
                    self._resync_requests()
                self._last_reject_count = v["reject_count"]
                if not v["winch_armed"] and self.req["winch.armed"] and not self.holds["winch"][0]:
                    # Pico disarmed it (timeout or lost link); follow it
                    self.req["winch.armed"] = False
            elif msg.name == "PICO_OUTPUTS":
                for bit, name in M.RELAY_BITS.items():
                    st[name] = bool(int(v["relays"]) & (1 << bit))
                for k, short in LIGHT_IDS.items():
                    st[k] = v[short]
                st["light.effect"] = M.LIGHT_EFFECT.get(v["effect"], "none")
            elif msg.name == "PICO_LIGHTS2":
                for k in LAMPS:
                    st[f"lamp.{k}"] = int(v[k]) * 17          # 0-15 back to 0-255
                st["light.trailer_bar"] = st["lamp.trailer_bar"]
                st["light.show_running"] = bool(v["show_running"])
                st["light.show_blocked"] = bool(v["show_blocked"])
                st["light.pwm_ok"] = bool(v["pwm_ok"])
            elif msg.name == "PICO_ACTUATORS":
                st["an.diff_pos"] = v["diff_pct"]
                st["act.diff_target"] = v["diff_target"]
                st["act.4wd"] = M.FOURWD_STATE.get(v["fourwd"], "fault")
                st["act.tray"] = M.TRAY_STATE.get(v["tray"], "fault")
                st["act.tray_pct"] = v["tray_pct"]
                st["an.diff_current"] = v["diff_current"]
                st["an.4wd_current"] = v["fourwd_current"]
                st["an.tray_current"] = v["tray_current"]
            elif msg.name == "PICO_POWER":
                st["an.aux_12v"] = v["aux_12v"]
                st["pico.temp"] = v["pico_temp"]
                st["an.diff_pos_raw"] = v["diff_pot_raw"]
                st["pico.version"] = f'{v["fw_major"]}.{v["fw_minor"]}'
                st["winch.idle_s"] = v["winch_idle_s"]
            elif msg.name == "PICO_REGEN":
                st["regen.pedal_pct"] = v["pedal_pct"]
                st["regen.request_pct"] = v["request_pct"]
                st["regen.state"] = M.REGEN_STATE.get(v["state"], "off")
                st["regen.limit"] = M.REGEN_LIMIT.get(v["limit"], "none")
                st["an.brake_pedal_raw"] = v["pedal_raw"]
            elif msg.name == "PICO_LOCK":
                st["lock.state"] = M.LOCK_STATE.get(v["state"], "off")
                st["lock.tries_left"] = v["tries_left"]
                st["lock.lockout_s"] = v["lockout_s"]
                st["lock.window"] = bool(v["window"])
                st["lock.puk_set"] = bool(v["puk_set"])
                st["lock.inhibit"] = bool(v["inhibit"])
                st["lock.lockout"] = bool(v["lockout"])
                st["lock.pending"] = bool(v.get("pending", 0))
                st["lock.result"] = M.LOCK_RESULT.get(v["result"], "none")
                st["lock.result_text"] = M.LOCK_RESULT_TEXT.get(st["lock.result"], "")
                st["lock.result_count"] = v["result_count"]
                st["lock.fails"] = v["fails"]
            elif msg.name == "PICO_SETTINGS_ACK":
                key = int(v["key"])
                self.last_ack = {"key": key, "status": v["status"], "value": int(v["value"])}
                if key in M.SETTINGS and v["status"] not in (1, 3):
                    self.settings[M.SETTINGS[key][0]] = int(v["value"])
                ev = self._acks.pop(key, None)
                if ev:
                    ev.set()
        for fn in list(self.listeners):
            try:
                fn(msg.name, v)
            except Exception:
                log.exception("listener failed")

    def _resync_requests(self) -> None:
        """A request was refused: snap the dash's request back to what the box is doing."""
        st = self.state
        # Leave a request alone while the box is still waiting on it (a refusal of
        # something else, like the tray, must not cancel a waiting 4WD change).
        if "act.4wd" in st and st["act.4wd"] in ("2wd", "4wd") and not st.get("act.4wd_wait"):
            self.req["act.4wd"] = 1 if st["act.4wd"] == "4wd" else 0
        if "act.diff_target" in st and not st.get("act.diff_wait"):
            self.req["act.diff"] = int(st["act.diff_target"])
        self.node.send(M.PI_DRIVE, self._drive_values())

    # ------------------------------------------------------------ loop
    def run(self) -> None:
        while not self._stop.is_set():
            for msg, v, raw in self.node.poll(timeout=0.01):
                self._on_frame(msg, v, raw, time.monotonic())
            self._send_periodic(time.monotonic())

    def start(self) -> "Gateway":
        self._thread = threading.Thread(target=self.run, name="teryx-gateway", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(2)
        self.node.close()
