"""Fun screen back end: the streaming window and screen power for camp mode.

Streaming services (Netflix and the like) won't run inside the dash page, so on the Pi the
server opens each one in its own Chromium/Chrome window, under the dash's top bar, with its own
profile so logins stick. The server shuts that window the moment the Teryx isn't parked
(park brake off, moving, or no speed from the motor controller). The dash page does the same
check, but this one still works if the page is hidden behind the video.

On a laptop or the bench sim there's no window: the dash opens a normal browser tab instead.
TERYX_FUN_WINDOW=1 forces the window on, =0 forces it off.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from aiohttp import web

# Names and links only. Same list as dash/web/js/fun/streams.js. Settings can add more
# (fun.streams: [{id, name, url}]), https only.
STREAMS = {
    "youtube": "https://www.youtube.com/",
    "netflix": "https://www.netflix.com/",
    "disney": "https://www.disneyplus.com/",
    "prime": "https://www.primevideo.com/",
    "neon": "https://www.neontv.co.nz/",
    "tvnz": "https://www.tvnz.co.nz/",
    "threenow": "https://www.threenow.co.nz/",
    "spotify": "https://open.spotify.com/",
}

TOP_BAR_PX = 64          # the dash's top bar stays visible above the video (theme.css --top-h)
SCREEN_W, SCREEN_H = 1280, 800
WATCH_S = 0.25           # how often the parked check runs while a video window is open

FUN_KEY = web.AppKey("teryx_dash_fun", object)
FUN_TASK_KEY = web.AppKey("teryx_dash_fun_task", asyncio.Future)


def is_parked(s: dict) -> bool:
    """Park brake on, stopped, and the speed is known. Matches dash/web/js/fun/park.js."""
    if not s.get("in.park"):
        return False
    if s.get("mc.online") is False or s.get("pico.speed_valid") is False:
        return False
    if s.get("pico.parked") is False:
        return False
    try:
        return abs(float(s.get("mc.speed") or 0)) < 0.5
    except (TypeError, ValueError):
        return False


def why_not(s: dict) -> str:
    if s.get("mc.online") is False or s.get("pico.speed_valid") is False:
        return "No speed from the motor controller."
    if abs(float(s.get("mc.speed") or 0)) >= 0.5:
        return "The Teryx is moving."
    return "Put the park brake on first."


def stream_url(stream_id: str, settings: dict) -> str | None:
    extra = {}
    for s in (settings.get("fun") or {}).get("streams") or []:
        if isinstance(s, dict) and isinstance(s.get("id"), str) and isinstance(s.get("url"), str):
            extra[s["id"]] = s["url"]
    url = extra.get(stream_id) or STREAMS.get(stream_id)
    if not url:
        return None
    u = urlparse(url)
    return url if u.scheme == "https" and u.netloc else None


def find_browser() -> str | None:
    # Google Chrome for Arm64 Linux bundles Widevine; Raspberry Pi OS Chromium may not. See docs/fun.md.
    for b in ("google-chrome-stable", "google-chrome", "chromium", "chromium-browser"):
        p = shutil.which(b)
        if p:
            return p
    return None


def browser_args(browser: str, url: str, profile: Path) -> list[str]:
    return [
        browser, f"--app={url}", f"--user-data-dir={profile}",
        f"--window-position=0,{TOP_BAR_PX}", f"--window-size={SCREEN_W},{SCREEN_H - TOP_BAR_PX}",
        "--no-first-run", "--noerrdialogs", "--disable-infobars", "--disable-translate",
        "--autoplay-policy=no-user-gesture-required", "--password-store=basic",
        "--check-for-update-interval=31536000",
    ]


class StreamWindow:
    """One streaming window at a time."""

    def __init__(self, config_dir: Path, enabled: bool, spawn: Callable[[list[str]], Any] | None = None):
        self.profile = config_dir / "stream-profile"
        self.enabled = enabled
        self.spawn = spawn or (lambda args: subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True))
        self.proc: Any = None
        self.stream_id: str | None = None
        self.closed_why = ""

    @property
    def open(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def launch(self, stream_id: str, url: str) -> bool:
        self.close("another one opened")
        browser = find_browser()
        if not browser:
            raise RuntimeError("No Chrome or Chromium on the Pi.")
        self.profile.mkdir(parents=True, exist_ok=True)
        self.proc = self.spawn(browser_args(browser, url, self.profile))
        self.stream_id = stream_id
        self.closed_why = ""
        return True

    def close(self, why: str = "") -> bool:
        if not self.open:
            self.proc = None
            return False
        try:
            os.killpg(self.proc.pid, signal.SIGTERM)
        except Exception:
            try:
                self.proc.terminate()
            except Exception:
                pass
        self.proc = None
        self.closed_why = why
        return True


def window_wanted(gateway: Any) -> bool:
    want = os.environ.get("TERYX_FUN_WINDOW", "auto")
    if want in ("0", "1"):
        return want == "1"
    bus = str(getattr(gateway, "bus_spec", "") or "")
    return bus.startswith("socketcan") or bus.startswith("can")


async def set_screen(on: bool) -> bool:
    """Turn the HDMI picture off or on (labwc / Wayland on Raspberry Pi OS). Touch keeps working, so a tap wakes it."""
    tool = shutil.which("wlr-randr")
    if not tool:
        return False
    out = os.environ.get("TERYX_SCREEN_OUTPUT", "HDMI-A-1")
    proc = await asyncio.create_subprocess_exec(tool, "--output", out, "--on" if on else "--off",
                                                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    try:
        return (await asyncio.wait_for(proc.wait(), 5)) == 0
    except asyncio.TimeoutError:
        return False


def setup_fun_routes(app: web.Application, gateway: Any, config_dir: Path, settings_file: Callable[[], Path],
                     snapshot: Callable[[], dict], spawn: Callable[[list[str]], Any] | None = None) -> StreamWindow:
    win = StreamWindow(config_dir, window_wanted(gateway), spawn)
    app[FUN_KEY] = win
    r = app.router

    def settings() -> dict:
        try:
            return json.loads(settings_file().read_text())
        except Exception:
            return {}

    async def status(_):
        return web.json_response({"open": win.open, "stream": win.stream_id if win.open else None,
                                  "window": win.enabled, "parked": is_parked(snapshot()), "closed_why": win.closed_why})

    async def watch(req):
        try:
            body = await req.json()
            sid = str(body["id"])
        except Exception:
            return web.json_response({"error": "send {\"id\": \"netflix\"}"}, status=400)
        s = snapshot()
        if not is_parked(s):
            return web.json_response({"error": why_not(s)}, status=409)
        url = stream_url(sid, settings())
        if not url:
            return web.json_response({"error": "Don't know that one."}, status=404)
        if not win.enabled:
            return web.json_response({"ok": True, "window": False, "url": url})
        try:
            win.launch(sid, url)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
        return web.json_response({"ok": True, "window": True, "url": url})

    async def close(_):
        return web.json_response({"ok": True, "closed": win.close("closed from the dash")})

    async def screen(req):
        try:
            on = bool((await req.json())["on"])
        except Exception:
            return web.json_response({"error": "send {\"on\": true|false}"}, status=400)
        done = await set_screen(on) if win.enabled else False
        return web.json_response({"ok": True, "done": done})

    r.add_get("/api/fun", status)
    r.add_post("/api/fun/watch", watch)
    r.add_post("/api/fun/close", close)
    r.add_post("/api/fun/screen", screen)

    async def guard():
        while True:
            await asyncio.sleep(WATCH_S)
            if win.open and not is_parked(snapshot()):
                win.close("not parked")

    async def on_start(_app):
        _app[FUN_TASK_KEY] = asyncio.ensure_future(guard())

    async def on_stop(_app):
        _app[FUN_TASK_KEY].cancel()
        win.close("dash stopping")

    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)
    return win
