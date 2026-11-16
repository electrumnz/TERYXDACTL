"""/api/audio and /api/media routes: outputs, volume, ducking, Bluetooth phone, music and radio.

    GET  /api/audio                       outputs, levels, Bluetooth phones and what's playing
    POST /api/audio/output {id}           send sound to this output (HDMI, USB DAC, I2S amp HAT)
    POST /api/audio/output-level {level}  0..1, the whole output (amp feed)
    POST /api/audio/media-level {level}   0..1, phone (Bluetooth) audio
    POST /api/audio/duck {on, duck_to}    turn phone audio down under an alert, and back up
    POST /api/audio/bt/pair {on}          open (or close) a 2 minute window to pair a phone
    POST /api/audio/bt/play|pause|next|previous
    POST /api/audio/bt/connect|disconnect|forget {addr}
    POST /api/audio/sim {phone, playing}  simulator only: plug in or pull out the fake phone
    GET  /api/media/library               songs on the Pi and on USB sticks
    GET  /api/media/file/{id}             one song (supports seeking)
    GET  /api/media/radio/{n}             station n from settings, passed through ffmpeg (for HLS
                                          streams like RNZ's, which Chromium can't play itself)
"""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any, Callable

from aiohttp import web

from .audio import AudioBackend, SimAudio, pick_backend
from .library import Library, demo_wav

AUDIO_KEY = web.AppKey("teryx_dash_audio", AudioBackend)
LIBRARY_KEY = web.AppKey("teryx_dash_library", Library)


def _err(msg: str, status: int = 400) -> web.Response:
    return web.json_response({"error": msg}, status=status)


def setup_media_routes(app: web.Application, gateway: Any, settings_file: Callable[[], Path]) -> AudioBackend:
    audio = pick_backend(gateway)
    lib = Library(demo=isinstance(audio, SimAudio))
    app[AUDIO_KEY], app[LIBRARY_KEY] = audio, lib
    r = app.router

    async def body(req) -> dict:
        try:
            b = await req.json() if req.can_read_body else {}
            return b if isinstance(b, dict) else {}
        except Exception:
            return {}

    async def guarded(fn, *a):
        try:
            await fn(*a)
        except ValueError as e:
            return _err(str(e))
        except Exception as e:
            return _err(str(e) or "that didn't work", 502)
        return web.json_response(await audio.status())

    async def status(_):
        return web.json_response(await audio.status())

    async def output(req):
        return await guarded(audio.set_output, str((await body(req)).get("id", "")))

    def level(b: dict) -> float:
        try:
            return float(b["level"])
        except Exception:
            raise ValueError("need level 0 to 1")

    async def output_level(req):
        b = await body(req)
        try:
            v = level(b)
        except ValueError as e:
            return _err(str(e))
        return await guarded(audio.set_output_level, v)

    async def media_level(req):
        b = await body(req)
        try:
            v = level(b)
        except ValueError as e:
            return _err(str(e))
        return await guarded(audio.set_media_level, v)

    async def duck(req):
        b = await body(req)
        dt = b.get("duck_to")
        try:
            await audio.duck(bool(b.get("on")), None if dt is None else float(dt))
        except Exception as e:
            return _err(str(e), 502)
        return web.json_response({"ok": True, "ducked": audio.ducked, "bt_level": audio.bt_level()})

    async def bt_pair(req):
        return await guarded(audio.bt_pair, bool((await body(req)).get("on", True)))

    async def bt_cmd(req):
        return await guarded(audio.bt_command, req.match_info["cmd"])

    async def bt_dev(req):
        action = req.match_info["action"]
        addr = str((await body(req)).get("addr", "")).upper()
        fn = {"connect": audio.bt_connect, "disconnect": audio.bt_disconnect, "forget": audio.bt_forget}.get(action)
        if not fn:
            return _err("unknown", 404)
        return await guarded(fn, addr)

    async def sim(req):
        if not isinstance(audio, SimAudio):
            return _err("not running the simulator", 404)
        audio.sim(await body(req))
        return web.json_response(await audio.status())

    async def library(req):
        tracks = await asyncio.to_thread(lib.scan, req.query.get("rescan") == "1")
        return web.json_response({"tracks": tracks, "roots": [str(p) for p in lib.roots]})

    async def media_file(req):
        tid = req.match_info["id"]
        if tid.startswith("demo-") and lib.demo:
            data = await asyncio.to_thread(demo_wav, tid)
            if data is None:
                raise web.HTTPNotFound()
            return web.Response(body=data, content_type="audio/wav", headers={"Cache-Control": "max-age=3600"})
        p = await asyncio.to_thread(lib.path, tid)
        if not p:
            raise web.HTTPNotFound()
        return web.FileResponse(p)

    async def radio(req):
        try:
            n = int(req.match_info["n"])
            stations = json.loads(settings_file().read_text()).get("media", {}).get("stations", [])
            url = str(stations[n]["url"])
        except Exception:
            return _err("no such station", 404)
        # Only stations saved in settings, only http(s), never through a shell.
        if not url.startswith(("http://", "https://")):
            return _err("station address must start with http:// or https://")
        if not shutil.which("ffmpeg"):
            return _err("ffmpeg not installed", 503)
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-loglevel", "error", "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5",
            "-i", url, "-vn", "-c:a", "libmp3lame", "-b:a", "160k", "-f", "mp3", "pipe:1",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        resp = web.StreamResponse(headers={"Content-Type": "audio/mpeg", "Cache-Control": "no-store"})
        await resp.prepare(req)
        try:
            while True:
                chunk = await proc.stdout.read(16384)
                if not chunk:
                    break
                await resp.write(chunk)
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            if proc.returncode is None:
                proc.kill()
        return resp

    r.add_get("/api/audio", status)
    r.add_post("/api/audio/output", output)
    r.add_post("/api/audio/output-level", output_level)
    r.add_post("/api/audio/media-level", media_level)
    r.add_post("/api/audio/duck", duck)
    r.add_post("/api/audio/bt/pair", bt_pair)
    r.add_post("/api/audio/bt/{cmd:play|pause|next|previous}", bt_cmd)
    r.add_post("/api/audio/bt/{action:connect|disconnect|forget}", bt_dev)
    r.add_post("/api/audio/sim", sim)
    r.add_get("/api/media/library", library)
    r.add_get("/api/media/file/{id}", media_file)
    r.add_get("/api/media/radio/{n}", radio)
    return audio
