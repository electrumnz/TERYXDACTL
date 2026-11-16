"""aiohttp routes for the dash's settings, updates, Wi-Fi, system and camera."""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import shlex
import shutil
import time
from pathlib import Path
from typing import Any

from aiohttp import web

from . import pico_settings
from .media import setup_media_routes
from .ota import Ota, OtaConfig
from .trips import DEFAULT_PACK_KWH, TripLog

CONFIG_DIR = Path(os.environ.get("TERYX_CONFIG_DIR", Path.home() / ".config" / "teryx"))
SETTINGS_FILE = CONFIG_DIR / "dash-settings.json"
STARTED = time.time()
MAX_SETTINGS_BYTES = 64 * 1024
OTA_KEY = web.AppKey("teryx_dash_ota", Ota)
CONFIRM_KEY = web.AppKey("teryx_dash_confirm", asyncio.Future)
KEYOFF_KEY = web.AppKey("teryx_dash_keyoff", asyncio.Future)
TRIPS_KEY = web.AppKey("teryx_dash_trips", TripLog)
TRIPS_TASK_KEY = web.AppKey("teryx_dash_trips_task", asyncio.Future)


async def maybe_await(v):
    return await v if inspect.isawaitable(v) else v


def snapshot(gateway: Any) -> dict:
    try:
        return gateway.snapshot() or {}
    except Exception:
        return {}


def is_stopped(gateway: Any) -> bool:
    s = snapshot(gateway)
    if "pico.parked" in s:  # the control box's own view wins when it's there
        return bool(s["pico.parked"])
    if s.get("mc.online") is False or s.get("pico.speed_valid") is False:
        return False  # speed unknown counts as moving
    return float(s.get("mc.speed") or 0) < 0.5


def err(msg: str, status: int = 400) -> web.Response:
    return web.json_response({"error": msg}, status=status)


async def set_pico(gateway: Any, setting: pico_settings.Setting | int, value: int) -> Any:
    """Send one 0x704 setting. The gateway may take the name or the numeric key."""
    fn = getattr(gateway, "set_setting", None)
    if fn is None:
        raise RuntimeError("gateway can't send settings")
    key = setting if isinstance(setting, int) else setting.key
    if inspect.iscoroutinefunction(fn):
        return await fn(key, value)
    # The gateway's set_setting blocks until the control box acks (up to 1 s), so run it off the event loop.
    return await asyncio.to_thread(fn, key, value)


def setup_routes(app: web.Application, gateway: Any) -> None:
    ota = Ota(cfg=OtaConfig(), is_stopped=lambda: is_stopped(gateway),
              pico_version=lambda: snapshot(gateway).get("pico.version"))
    app[OTA_KEY] = ota
    trips = TripLog(CONFIG_DIR / "trips.json")
    app[TRIPS_KEY] = trips
    r = app.router
    # Audio, Bluetooth phone, music and radio (media.py).
    setup_media_routes(app, gateway, lambda: SETTINGS_FILE)

    # ---------- dash settings ----------
    async def get_settings(_):
        try:
            return web.json_response(json.loads(SETTINGS_FILE.read_text()))
        except FileNotFoundError:
            return web.json_response({})
        except Exception:
            return web.json_response({})

    async def put_settings(req):
        body = await req.read()
        if len(body) > MAX_SETTINGS_BYTES:
            return err("settings too big", 413)
        try:
            data = json.loads(body)
            assert isinstance(data, dict)
        except Exception:
            return err("settings must be a JSON object")
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        tmp = SETTINGS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        os.replace(tmp, SETTINGS_FILE)
        return web.json_response({"ok": True})

    # ---------- control box settings ----------
    async def get_pico(_):
        return web.json_response({"settings": pico_settings.listing(gateway)})

    async def put_pico(req):
        try:
            body = await req.json()
            name, value = body["name"], int(body["value"])
        except Exception:
            return err("need {name, value}")
        s = pico_settings.by_name(name)
        if not s:
            return err(f"unknown setting {name}")
        if not (s.min <= value <= s.max):
            return err(f"{s.label} must be {s.min} to {s.max}")
        try:
            ack = await set_pico(gateway, s, value)
        except Exception as e:
            return err(str(e), 502)
        if ack is False:
            return err("the control box didn't confirm", 504)
        return web.json_response({"ok": True})

    async def pico_cmd(key):
        try:
            await set_pico(gateway, key, 1)
        except Exception as e:
            return err(str(e), 502)
        return web.json_response({"ok": True})

    async def pico_save(_):
        return await pico_cmd(pico_settings.SAVE_KEY)

    async def pico_reset(_):
        return await pico_cmd(pico_settings.RESET_KEY)

    async def pico_clear(_):
        return await pico_cmd(pico_settings.CLEAR_FAULTS_KEY)

    async def diff_cal(req):
        try:
            which = (await req.json())["which"]
            assert which in ("min", "max")
        except Exception:
            return err("which must be min or max")
        if not is_stopped(gateway):
            return err("stop the Teryx first")
        raw = snapshot(gateway).get("an.diff_pos_raw")
        if raw is None:
            return err("no raw diff position from the control box")
        s = pico_settings.by_name("diff_pot_min_raw" if which == "min" else "diff_pot_max_raw")
        try:
            await set_pico(gateway, s, int(raw))
        except Exception as e:
            return err(str(e), 502)
        return web.json_response({"ok": True, "raw": int(raw)})

    # ---------- OTA ----------
    async def ota_status(_):
        return web.json_response(ota.status())

    async def ota_action(req):
        action = req.match_info["action"]
        try:
            body = await req.json() if req.can_read_body else {}
        except Exception:
            body = {}
        try:
            if action == "check":
                ota.check(channel=_channel())
            elif action == "install":
                ota.install(target=body.get("target", "dash"))
            elif action == "rollback":
                ota.rollback()
            else:
                return err("unknown action", 404)
        except RuntimeError as e:
            return err(str(e), 409)
        await asyncio.sleep(0.05)
        return web.json_response(ota.status())

    def _channel() -> str:
        try:
            return json.loads(SETTINGS_FILE.read_text()).get("updates", {}).get("channel", "stable")
        except Exception:
            return "stable"

    # ---------- Wi-Fi (NetworkManager) ----------
    async def wifi(_):
        if not shutil.which("nmcli"):
            return err("nmcli not found (NetworkManager)", 503)
        out = await _run("nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL", "dev", "wifi")
        connected = None
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[0] == "yes":
                connected = {"ssid": parts[1], "signal": int(parts[2] or 0)}
        saved = []
        for line in (await _run("nmcli", "-t", "-f", "NAME,TYPE", "con", "show")).splitlines():
            name, _, kind = line.rpartition(":")
            if kind.endswith("wireless"):
                saved.append(name.replace("\\:", ":"))
        ip = ""
        try:
            ip = (await _run("hostname", "-I")).split()[0]
        except Exception:
            pass
        return web.json_response({"connected": bool(connected), "ssid": connected and connected["ssid"],
                                  "signal": connected and connected["signal"], "ip": ip, "saved": saved})

    async def wifi_connect(req):
        try:
            ssid = (await req.json())["ssid"]
        except Exception:
            return err("need ssid")
        # Only saved networks, and never through a shell.
        saved = (await _run("nmcli", "-t", "-f", "NAME", "con", "show")).splitlines()
        if ssid not in [s.replace("\\:", ":") for s in saved]:
            return err("not a saved network")
        asyncio.ensure_future(_run("nmcli", "con", "up", "id", ssid))
        return web.json_response({"ok": True})

    async def wifi_scan(_):
        if not shutil.which("nmcli"):
            return err("nmcli not found (NetworkManager)", 503)
        out = await _run("nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list", "--rescan", "auto")
        nets: dict[str, dict] = {}
        for line in out.splitlines():
            parts = _split_nmcli(line)
            if len(parts) < 3 or not parts[0]:
                continue
            ssid, sig, sec = parts[0], int(parts[1] or 0), parts[2]
            if ssid not in nets or nets[ssid]["signal"] < sig:
                nets[ssid] = {"ssid": ssid, "signal": sig, "secure": bool(sec and sec != "--")}
        return web.json_response({"networks": sorted(nets.values(), key=lambda n: -n["signal"])})

    async def wifi_add(req):
        """Join a new network, typed on the on-screen keyboard. Never goes through a shell."""
        try:
            body = await req.json()
            ssid, password = str(body["ssid"]), str(body.get("password") or "")
        except Exception:
            return err("need ssid")
        if not 1 <= len(ssid.encode()) <= 32 or "\n" in ssid or "\0" in ssid:
            return err("network name must be 1 to 32 characters")
        if password and not 8 <= len(password) <= 63:
            return err("Wi-Fi passwords are 8 to 63 characters")
        if not shutil.which("nmcli"):
            return err("nmcli not found (NetworkManager)", 503)
        args = ["nmcli", "dev", "wifi", "connect", ssid]
        if password:
            args += ["password", password]
        if body.get("hidden"):
            args += ["hidden", "yes"]
        try:
            out = await _run(*args, timeout=45, stderr=True)
        except asyncio.TimeoutError:
            return err("timed out joining the network", 504)
        if "successfully" not in out.lower():
            return err("couldn't join. Check the name and password", 502)
        return web.json_response({"ok": True})

    async def wifi_forget(req):
        try:
            ssid = (await req.json())["ssid"]
        except Exception:
            return err("need ssid")
        saved = (await _run("nmcli", "-t", "-f", "NAME", "con", "show")).splitlines()
        if ssid not in [x.replace("\\:", ":") for x in saved]:
            return err("not a saved network")
        await _run("nmcli", "con", "delete", "id", ssid)
        return web.json_response({"ok": True})

    # ---------- trips ----------
    def _pack_kwh() -> float:
        try:
            v = float(json.loads(SETTINGS_FILE.read_text()).get("packKwh") or DEFAULT_PACK_KWH)
            return v if 0.5 <= v <= 100 else DEFAULT_PACK_KWH
        except Exception:
            return DEFAULT_PACK_KWH

    async def trips_get(_):
        return web.json_response(trips.summary(snapshot(gateway), _pack_kwh()))

    async def trips_reset(req):
        what = req.match_info["what"]
        if what == "trip-a":
            trips.reset_trip_a()
        elif what == "history":
            trips.clear_history()
        else:
            return err("unknown", 404)
        return web.json_response(trips.summary(snapshot(gateway), _pack_kwh()))

    async def log_trips():
        while True:
            try:
                s = snapshot(gateway)
                if s:
                    trips.sample(s)
            except Exception:
                pass
            await asyncio.sleep(1)

    # ---------- system ----------
    async def system(_):
        temp = None
        try:
            temp = round(int(Path("/sys/class/thermal/thermal_zone0/temp").read_text()) / 1000)
        except Exception:
            pass
        up = int(time.time() - STARTED)
        return web.json_response({"version": ota.status()["dash"]["current"], "uptime": f"{up // 3600}h {up // 60 % 60}m", "temp": temp})

    async def sys_restart(_):
        asyncio.ensure_future(_run(*shlex.split(ota.cfg.restart_cmd)))
        return web.json_response({"ok": True})

    async def sys_shutdown(_):
        if not is_stopped(gateway):
            return err("stop the Teryx first")
        asyncio.ensure_future(_run("sudo", "-n", "systemctl", "poweroff"))
        return web.json_response({"ok": True})

    # ---------- camera as MJPEG ----------
    async def camera(req):
        from .camera import mjpeg_response
        return await mjpeg_response(req, _camera_device())

    def _camera_device() -> str:
        try:
            return json.loads(SETTINGS_FILE.read_text()).get("camera", {}).get("v4l2Device") or "/dev/video0"
        except Exception:
            return "/dev/video0"

    r.add_get("/api/settings", get_settings)
    r.add_put("/api/settings", put_settings)
    r.add_get("/api/pico-settings", get_pico)
    r.add_put("/api/pico-settings", put_pico)
    r.add_post("/api/pico-settings/save", pico_save)
    r.add_post("/api/pico-settings/reset", pico_reset)
    r.add_post("/api/pico-settings/clear-faults", pico_clear)
    r.add_post("/api/diff-calibrate", diff_cal)
    r.add_get("/api/ota/status", ota_status)
    r.add_post("/api/ota/{action}", ota_action)
    r.add_get("/api/wifi", wifi)
    r.add_post("/api/wifi/connect", wifi_connect)
    r.add_get("/api/wifi/scan", wifi_scan)
    r.add_post("/api/wifi/add", wifi_add)
    r.add_post("/api/wifi/forget", wifi_forget)
    r.add_get("/api/trips", trips_get)
    r.add_post("/api/trips/reset/{what}", trips_reset)
    r.add_get("/api/system", system)
    r.add_post("/api/system/restart", sys_restart)
    r.add_post("/api/system/shutdown", sys_shutdown)
    r.add_get("/api/camera.mjpg", camera)

    async def watch_key_off():
        """Key off: the control box asks the Pi to shut down, then cuts power after its wait."""
        while True:
            await asyncio.sleep(1)
            if snapshot(gateway).get("pico.shutdown_request") and os.environ.get("TERYX_NO_SHUTDOWN") != "1":
                await _run("sudo", "-n", "systemctl", "poweroff")
                return

    async def on_start(_app):
        _app[CONFIRM_KEY] = asyncio.ensure_future(
            ota.confirm_when_healthy(lambda: bool(snapshot(gateway))))
        _app[KEYOFF_KEY] = asyncio.ensure_future(watch_key_off())
        _app[TRIPS_TASK_KEY] = asyncio.ensure_future(log_trips())

    async def on_stop(_app):
        _app[TRIPS_TASK_KEY].cancel()
        try:
            trips.save()
        except OSError:
            pass

    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)


async def _run(*args: str, timeout: float = 20, stderr: bool = False) -> str:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT if stderr else asyncio.subprocess.DEVNULL)
    out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    return out.decode(errors="replace")


def _split_nmcli(line: str) -> list[str]:
    """Split nmcli -t output on ':' but not on escaped '\\:'."""
    parts, cur, esc = [], "", False
    for ch in line:
        if esc:
            cur += ch
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == ":":
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts
