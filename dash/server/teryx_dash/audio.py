"""Audio on the Pi: where the sound goes, how loud, Bluetooth phone audio, and ducking.

Two back ends with the same methods:

    PiAudio    the real thing. PipeWire through `pactl` (outputs and volume), BlueZ through
               `bluetoothctl` and `busctl` (pairing, track info, play/pause/skip). No extra Python
               packages, nothing goes through a shell.
    SimAudio   a pretend Pi for the laptop and the simulator: three outputs (HDMI, USB DAC,
               I2S amp HAT) and a fake phone that plays a fake playlist.

Who plays what:
  * Alert sounds, local music, internet radio and CarPlay audio are played by the dash page
    itself (Chromium), so the page does its own ducking for those.
  * Bluetooth audio from a phone goes straight from BlueZ into PipeWire and never passes the
    page, so its level (and ducking) is set here, on its PipeWire stream.
  * The output level is the level of the whole output (the amp feed). Leave it near 100% and
    set the amp's gain once, so alerts are always loud enough.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

ADDR_RE = re.compile(r"^[0-9A-F]{2}(:[0-9A-F]{2}){5}$")
PAIR_WINDOW_S = 120
BT_COMMANDS = ("play", "pause", "next", "previous")
I2S_HINTS = ("hifiberry", "iqaudio", "justboom", "allo", "i2s", "max98357", "pcm5102", "pcm512", "dacplus", "amp2", "amp4")


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def output_kind(name: str, props: dict | None = None) -> str:
    """Guess what sort of output a PipeWire sink is, from its name and properties."""
    props = props or {}
    blob = " ".join([name, str(props.get("alsa.card_name", "")), str(props.get("alsa.long_card_name", "")),
                     str(props.get("device.description", "")), str(props.get("device.product.name", ""))]).lower()
    if props.get("device.api") == "bluez5" or name.startswith("bluez"):
        return "bluetooth"
    if "hdmi" in blob or "vc4hdmi" in blob:
        return "hdmi"
    if props.get("device.bus") == "usb" or "usb" in blob:
        return "usb"
    if any(h in blob for h in I2S_HINTS):
        return "i2s"
    return "other"


KIND_LABEL = {"hdmi": "HDMI", "usb": "USB DAC", "i2s": "I2S amp HAT", "bluetooth": "Bluetooth speaker", "other": "Other"}


@dataclass
class BtState:
    devices: list[dict] = field(default_factory=list)
    player: dict | None = None
    pairing_until: float = 0.0


class AudioBackend:
    name = "base"

    def __init__(self) -> None:
        self.media_level = 0.8       # Bluetooth phone audio level (0..1). The page sets its own for the rest.
        self.ducked = False
        self.duck_to = 0.25
        self.bt = BtState()

    def pairing_left(self) -> int:
        return max(0, int(round(self.bt.pairing_until - time.time())))

    async def status(self) -> dict:
        raise NotImplementedError

    async def set_output(self, sink: str) -> None:
        raise NotImplementedError

    async def set_output_level(self, level: float) -> None:
        raise NotImplementedError

    async def set_media_level(self, level: float) -> None:
        self.media_level = clamp01(level)
        await self._apply_bt_level()

    async def duck(self, on: bool, duck_to: float | None = None) -> None:
        if duck_to is not None:
            self.duck_to = clamp01(duck_to)
        if bool(on) == self.ducked and duck_to is None:
            return
        self.ducked = bool(on)
        await self._apply_bt_level()

    def bt_level(self) -> float:
        return round(self.media_level * (self.duck_to if self.ducked else 1.0), 3)

    async def _apply_bt_level(self) -> None:
        pass

    async def bt_pair(self, on: bool) -> None:
        raise NotImplementedError

    async def bt_command(self, cmd: str) -> None:
        raise NotImplementedError

    async def bt_connect(self, addr: str) -> None:
        raise NotImplementedError

    async def bt_disconnect(self, addr: str) -> None:
        raise NotImplementedError

    async def bt_forget(self, addr: str) -> None:
        raise NotImplementedError

    def common(self) -> dict:
        return {"backend": self.name, "media_level": self.media_level, "ducked": self.ducked,
                "duck_to": self.duck_to, "bt_level": self.bt_level()}


# --------------------------------------------------------------------------- sim

SIM_PLAYLIST = [
    ("Gravel Road", "The Test Pattern", "Bench Sessions", 214),
    ("Ridge Line", "The Test Pattern", "Bench Sessions", 187),
    ("River Crossing", "Low Range", "Mud Season", 242),
    ("Diff Lock Blues", "Low Range", "Mud Season", 205),
]


class SimAudio(AudioBackend):
    """A pretend Pi with a pretend phone, so the Media screen can be tried with no hardware."""
    name = "sim"

    def __init__(self) -> None:
        super().__init__()
        self.outputs = [
            {"id": "sim_hdmi", "label": "HDMI (screen has no speaker)", "kind": "hdmi"},
            {"id": "sim_usb", "label": "USB DAC", "kind": "usb"},
            {"id": "sim_i2s", "label": "I2S amp HAT", "kind": "i2s"},
        ]
        self.default = "sim_usb"
        self.output_level = 1.0
        self.phone = {"addr": "00:11:22:33:44:55", "name": "Test phone (sim)", "paired": True,
                      "connected": False, "trusted": True}
        self.track = 0
        self.playing = False
        self.pos = 0.0
        self._t = time.time()
        self.log: list[tuple] = []   # what was asked, for the tests

    def _tick(self) -> None:
        now = time.time()
        if self.playing and self.phone["connected"]:
            self.pos += now - self._t
            if self.pos >= SIM_PLAYLIST[self.track][3]:
                self.track = (self.track + 1) % len(SIM_PLAYLIST)
                self.pos = 0.0
        self._t = now
        if self.bt.pairing_until and time.time() > self.bt.pairing_until:
            self.bt.pairing_until = 0.0

    async def status(self) -> dict:
        self._tick()
        player = None
        if self.phone["connected"]:
            t, a, al, d = SIM_PLAYLIST[self.track]
            player = {"device": self.phone["name"], "addr": self.phone["addr"],
                      "status": "playing" if self.playing else "paused",
                      "title": t, "artist": a, "album": al, "duration_ms": d * 1000, "position_ms": int(self.pos * 1000)}
        devices = [dict(self.phone)] if self.phone["paired"] else []
        return {**self.common(),
                "outputs": [{**o, "default": o["id"] == self.default} for o in self.outputs],
                "output_level": self.output_level,
                "bt": {"available": True, "pairing": self.pairing_left(), "name": "Teryx",
                       "devices": devices, "player": player}}

    async def set_output(self, sink: str) -> None:
        if sink not in [o["id"] for o in self.outputs]:
            raise ValueError("no such output")
        self.default = sink
        self.log.append(("output", sink))

    async def set_output_level(self, level: float) -> None:
        self.output_level = clamp01(level)

    async def _apply_bt_level(self) -> None:
        self.log.append(("bt_level", self.bt_level()))

    async def bt_pair(self, on: bool) -> None:
        self.bt.pairing_until = time.time() + PAIR_WINDOW_S if on else 0.0
        if on and not self.phone["paired"]:
            # The fake phone "finds" the Teryx and pairs a moment later.
            async def later():
                await asyncio.sleep(2)
                self.phone.update(paired=True, connected=True)
            asyncio.ensure_future(later())

    async def bt_command(self, cmd: str) -> None:
        if cmd not in BT_COMMANDS:
            raise ValueError("unknown command")
        if not self.phone["connected"]:
            raise RuntimeError("no phone connected")
        self._tick()
        if cmd == "play":
            self.playing = True
        elif cmd == "pause":
            self.playing = False
        elif cmd == "next":
            self.track, self.pos = (self.track + 1) % len(SIM_PLAYLIST), 0.0
        elif cmd == "previous":
            if self.pos > 3:
                self.pos = 0.0
            else:
                self.track, self.pos = (self.track - 1) % len(SIM_PLAYLIST), 0.0

    async def bt_connect(self, addr: str) -> None:
        if addr == self.phone["addr"] and self.phone["paired"]:
            self.phone["connected"] = True

    async def bt_disconnect(self, addr: str) -> None:
        if addr == self.phone["addr"]:
            self.phone["connected"] = False
            self.playing = False

    async def bt_forget(self, addr: str) -> None:
        if addr == self.phone["addr"]:
            self.phone.update(paired=False, connected=False)
            self.playing = False

    def sim(self, cmd: dict) -> None:
        """Sim panel controls: {"phone": true|false, "playing": true|false}."""
        if "phone" in cmd:
            on = bool(cmd["phone"])
            self.phone.update(connected=on, paired=self.phone["paired"] or on)
            self.playing = on
            self.pos = 0.0 if on else self.pos
        if "playing" in cmd and self.phone["connected"]:
            self.playing = bool(cmd["playing"])


# --------------------------------------------------------------------------- Pi

Runner = Callable[..., Awaitable[str]]


async def run_cmd(*args: str, timeout: float = 8) -> str:
    proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise
    if proc.returncode:
        raise RuntimeError(f"{args[0]} {args[1] if len(args) > 1 else ''} failed")
    return out.decode(errors="replace")


def unvariant(v: Any) -> Any:
    """busctl --json=short wraps every variant as {"type": "...", "data": ...}. Unwrap them all."""
    if isinstance(v, dict):
        if set(v.keys()) == {"type", "data"}:
            return unvariant(v["data"])
        return {k: unvariant(x) for k, x in v.items()}
    if isinstance(v, list):
        return [unvariant(x) for x in v]
    return v


def parse_bluez(objects: dict) -> tuple[list[dict], dict | None]:
    """Phones and the player from BlueZ's GetManagedObjects (already unwrapped)."""
    devices, players = {}, []
    for path, ifaces in objects.items():
        d = ifaces.get("org.bluez.Device1")
        if d:
            devices[path] = {"addr": d.get("Address", ""), "name": d.get("Alias") or d.get("Name") or d.get("Address", ""),
                             "paired": bool(d.get("Paired")), "connected": bool(d.get("Connected")),
                             "trusted": bool(d.get("Trusted")), "icon": d.get("Icon", "")}
        p = ifaces.get("org.bluez.MediaPlayer1")
        if p:
            players.append((path, p))
    player = None
    # A phone can show more than one player; take the one that's playing, else the first.
    players.sort(key=lambda x: x[1].get("Status") != "playing")
    for path, p in players:
        dev = devices.get(p.get("Device")) or next((v for k, v in devices.items() if path.startswith(k + "/")), {})
        if dev and not dev.get("connected"):
            continue
        tr = p.get("Track") or {}
        player = {"path": path, "device": dev.get("name", ""), "addr": dev.get("addr", ""),
                  "status": p.get("Status", "stopped"), "title": tr.get("Title", ""), "artist": tr.get("Artist", ""),
                  "album": tr.get("Album", ""), "duration_ms": tr.get("Duration"), "position_ms": p.get("Position")}
        break
    devs = sorted((d for d in devices.values() if d["paired"] or d["connected"]), key=lambda d: (not d["connected"], d["name"]))
    return devs, player


def parse_sinks(sinks: list[dict], default: str) -> list[dict]:
    out = []
    for s in sinks:
        name = s.get("name", "")
        props = s.get("properties") or {}
        kind = output_kind(name, props)
        label = s.get("description") or props.get("device.description") or name
        out.append({"id": name, "label": label, "kind": kind, "default": name == default})
    return out


def sink_volume(sink: dict) -> float | None:
    vols = []
    for ch in (sink.get("volume") or {}).values():
        try:
            vols.append(float(str(ch.get("value_percent", "")).rstrip("%")) / 100)
        except (TypeError, ValueError):
            pass
    return round(sum(vols) / len(vols), 3) if vols else None


def bluetooth_streams(inputs: list[dict]) -> list[int]:
    """PipeWire streams that are phone audio coming in over Bluetooth (A2DP)."""
    out = []
    for si in inputs:
        p = si.get("properties") or {}
        blob = " ".join(str(p.get(k, "")) for k in ("device.api", "node.name", "media.name", "application.name", "api.bluez5.address"))
        if p.get("device.api") == "bluez5" or "bluez" in blob.lower() or p.get("api.bluez5.address"):
            out.append(int(si["index"]))
    return out


class PiAudio(AudioBackend):
    name = "pi"

    def __init__(self, run: Runner = run_cmd) -> None:
        super().__init__()
        self.run = run

    async def _json(self, *args: str) -> Any:
        return json.loads(await self.run(*args))

    async def status(self) -> dict:
        outputs, level = [], None
        try:
            default = (await self.run("pactl", "get-default-sink")).strip()
            sinks = await self._json("pactl", "-f", "json", "list", "sinks")
            outputs = parse_sinks(sinks, default)
            level = next((sink_volume(s) for s in sinks if s.get("name") == default), None)
        except Exception:
            pass
        bt: dict = {"available": False, "pairing": self.pairing_left(), "devices": [], "player": None}
        try:
            raw = await self._json("busctl", "--json=short", "call", "org.bluez", "/",
                                   "org.freedesktop.DBus.ObjectManager", "GetManagedObjects")
            objs = unvariant(raw)[0]
            devices, player = parse_bluez(objs)
            if player:
                player.pop("path", None)
            bt.update(available=True, devices=devices, player=player,
                      name=next((v["org.bluez.Adapter1"].get("Alias") for v in objs.values() if "org.bluez.Adapter1" in v), "Teryx"))
            await self._after_pairing(devices)
        except Exception:
            pass
        return {**self.common(), "outputs": outputs, "output_level": level, "bt": bt}

    async def _after_pairing(self, devices: list[dict]) -> None:
        # Trust a phone that paired during the window so it reconnects on its own next time.
        if self.bt.pairing_until:
            for d in devices:
                if d["paired"] and not d["trusted"] and ADDR_RE.match(d["addr"]):
                    await self.run("bluetoothctl", "trust", d["addr"])
            if time.time() > self.bt.pairing_until:
                self.bt.pairing_until = 0.0
                await self.run("bluetoothctl", "pairable", "off")

    async def set_output(self, sink: str) -> None:
        sinks = await self._json("pactl", "-f", "json", "list", "sinks")
        if sink not in [s.get("name") for s in sinks]:
            raise ValueError("no such output")
        await self.run("pactl", "set-default-sink", sink)
        # Move anything already playing (phone audio) across too.
        try:
            for si in await self._json("pactl", "-f", "json", "list", "sink-inputs"):
                await self.run("pactl", "move-sink-input", str(int(si["index"])), sink)
        except Exception:
            pass

    async def set_output_level(self, level: float) -> None:
        await self.run("pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{round(clamp01(level) * 100)}%")

    async def _apply_bt_level(self) -> None:
        try:
            inputs = await self._json("pactl", "-f", "json", "list", "sink-inputs")
        except Exception:
            return
        for idx in bluetooth_streams(inputs):
            await self.run("pactl", "set-sink-input-volume", str(idx), f"{round(self.bt_level() * 100)}%")

    async def bt_pair(self, on: bool) -> None:
        if on:
            await self.run("bluetoothctl", "power", "on")
            await self.run("bluetoothctl", "discoverable-timeout", str(PAIR_WINDOW_S))
            await self.run("bluetoothctl", "pairable", "on")
            await self.run("bluetoothctl", "discoverable", "on")
            self.bt.pairing_until = time.time() + PAIR_WINDOW_S
        else:
            self.bt.pairing_until = 0.0
            await self.run("bluetoothctl", "discoverable", "off")
            await self.run("bluetoothctl", "pairable", "off")

    async def _player_path(self) -> str:
        raw = await self._json("busctl", "--json=short", "call", "org.bluez", "/",
                               "org.freedesktop.DBus.ObjectManager", "GetManagedObjects")
        _, player = parse_bluez(unvariant(raw)[0])
        if not player:
            raise RuntimeError("no phone playing over Bluetooth")
        return player["path"]

    async def bt_command(self, cmd: str) -> None:
        if cmd not in BT_COMMANDS:
            raise ValueError("unknown command")
        path = await self._player_path()
        if not path.startswith("/org/bluez/"):
            raise RuntimeError("odd player path")
        await self.run("busctl", "call", "org.bluez", path, "org.bluez.MediaPlayer1", cmd.capitalize())

    async def bt_connect(self, addr: str) -> None:
        if not ADDR_RE.match(addr):
            raise ValueError("bad address")
        await self.run("bluetoothctl", "connect", addr, timeout=20)

    async def bt_disconnect(self, addr: str) -> None:
        if not ADDR_RE.match(addr):
            raise ValueError("bad address")
        await self.run("bluetoothctl", "disconnect", addr)

    async def bt_forget(self, addr: str) -> None:
        if not ADDR_RE.match(addr):
            raise ValueError("bad address")
        await self.run("bluetoothctl", "remove", addr)


def pick_backend(gateway: Any = None) -> AudioBackend:
    """TERYX_AUDIO=pi|sim picks one. Otherwise: the real thing on a real CAN bus, the sim on anything else."""
    want = os.environ.get("TERYX_AUDIO", "auto").lower()
    if want == "sim":
        return SimAudio()
    if want == "pi":
        return PiAudio()
    bus = str(getattr(gateway, "bus_spec", "") or "")
    real = bus.startswith("socketcan") or bus.startswith("can")
    if real and sys.platform.startswith("linux") and shutil.which("pactl"):
        return PiAudio()
    return SimAudio()
