"""Web server for the dash: serves the UI and streams live state over a websocket.

    /            the UI (the basic test screen, or any folder given with --ui)
    /sim         simulator control page (only when the sim is running here)
    /virtual     3D virtual Teryx driven by the live state
    /ws          websocket: state out at 20 Hz, requests and holds in
    /api/state   one-off state snapshot (handy for curl)
    /api/sim     GET sim status, POST changes (only when the sim is running here)
    /api/bus     frame counts and unknown CAN ids (handy when sniffing)

Plugins: any module with ``setup_routes(app, gateway)`` passed with --plugin,
plus ``teryx_dash`` if it can be imported (the full dash UI's server side).
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import time
from pathlib import Path

from aiohttp import WSMsgType, web

from ..canbus import messages as M
from ..canbus import shinegle as SG
from ..canbus.registry import ALL_MESSAGES
from .gateway import Gateway

log = logging.getLogger("teryx.server")

WEB = Path(__file__).resolve().parent.parent / "web"
PUSH_HZ = 20

GATEWAY = web.AppKey("gateway", Gateway)
SIM = web.AppKey("sim", object)
SOCKETS = web.AppKey("sockets", set)
PUSHER = web.AppKey("pusher", asyncio.Task)


def _json(obj) -> str:
    return json.dumps(obj, separators=(",", ":"), default=str)


def build_app(gateway: Gateway, sim=None, ui_dir: str | Path | None = None,
              plugins: tuple[str, ...] = ()) -> web.Application:
    app = web.Application()
    app[GATEWAY], app[SIM] = gateway, sim
    app[SOCKETS] = set()
    ui = Path(ui_dir).resolve() if ui_dir else WEB / "test"

    async def index(_req):
        return web.FileResponse(ui / "index.html")

    async def sim_page(_req):
        if sim is None:
            raise web.HTTPNotFound(text="Simulator is not running in this process")
        return web.FileResponse(WEB / "sim" / "index.html")

    async def virtual_page(_req):
        return web.FileResponse(WEB / "virtual" / "index.html")

    async def api_state(_req):
        return web.json_response(_with_sim(gateway.snapshot(), sim), dumps=_json)

    async def api_bus(_req):
        return web.json_response({
            "bus": gateway.bus_spec,
            "frames": gateway.frame_counts,
            "unknown_ids": {hex(k): n for k, n in sorted(gateway.unknown_ids.items())},
        })

    async def api_canmap(_req):
        return web.json_response({
            "placeholder_shinegle": SG.PLACEHOLDER,
            "messages": [{
                "name": m.name, "id": hex(m.can_id), "sender": m.sender, "period_ms": m.period_ms,
                "comment": m.comment,
                "signals": [{"name": s.name, "start": s.start, "length": s.length, "scale": s.scale,
                             "offset": s.offset, "signed": s.signed, "unit": s.unit,
                             "choices": s.choices} for s in m.signals],
            } for m in ALL_MESSAGES],
            "settings": {k: {"name": n, "unit": u, "default": d, "min": lo, "max": hi}
                         for k, (n, u, d, lo, hi) in M.SETTINGS.items()},
            "fault_bits": M.FAULT_BITS, "reject_reasons": M.REJECT_REASON,
            "reject_text": M.REJECT_TEXT, "shinegle_faults": SG.FAULT_BITS,
            "shinegle_fault_text": SG.FAULT_TEXT,
        })

    async def api_sim_get(_req):
        if sim is None:
            raise web.HTTPNotFound(text="Simulator is not running in this process")
        return web.json_response(sim.status(), dumps=_json)

    async def api_sim_post(req):
        if sim is None:
            raise web.HTTPNotFound(text="Simulator is not running in this process")
        try:
            sim.apply(await req.json())
        except (ValueError, KeyError, TypeError) as e:
            return web.json_response({"ok": False, "error": str(e)}, status=400)
        return web.json_response({"ok": True, **sim.status()}, dumps=_json)

    async def ws_handler(req):
        ws = web.WebSocketResponse(heartbeat=10)
        await ws.prepare(req)
        app[SOCKETS].add(ws)
        try:
            async for m in ws:
                if m.type != WSMsgType.TEXT:
                    continue
                try:
                    data = json.loads(m.data)
                    kind = data.get("type")
                    if kind == "request":
                        gateway.request(data["id"], data["value"])
                    elif kind == "hold":
                        gateway.hold(data["id"], data["value"], data.get("secs", 0))
                    elif kind == "lock":
                        gateway.lock(data["cmd"], data.get("digits"))
                    elif kind == "setting":
                        ok = await asyncio.to_thread(gateway.set_setting, data["key"], data["value"])
                        await ws.send_str(_json({"type": "setting_ack", "key": data["key"], "ok": ok}))
                    elif kind == "sim" and sim is not None:
                        sim.apply(data.get("cmd", {}))
                    else:
                        raise ValueError(f"unknown message type {kind}")
                except Exception as e:  # tell the UI, keep the socket open
                    await ws.send_str(_json({"type": "error", "error": str(e)}))
        finally:
            app[SOCKETS].discard(ws)
        return ws

    async def pusher(app_):
        period = 1 / PUSH_HZ
        while True:
            await asyncio.sleep(period)
            if not app_[SOCKETS]:
                continue
            msg = _json({"type": "state", "t": round(time.time(), 3),
                         "state": _with_sim(gateway.snapshot(), sim)})
            for ws in list(app_[SOCKETS]):
                try:
                    await ws.send_str(msg)
                except (ConnectionResetError, RuntimeError):
                    app_[SOCKETS].discard(ws)

    async def on_startup(app_):
        app_[PUSHER] = asyncio.create_task(pusher(app_))

    async def on_cleanup(app_):
        app_[PUSHER].cancel()
        for ws in list(app_[SOCKETS]):
            await ws.close()

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    app.router.add_get("/ws", ws_handler)
    app.router.add_get("/api/state", api_state)
    app.router.add_get("/api/bus", api_bus)
    app.router.add_get("/api/canmap", api_canmap)
    app.router.add_get("/api/sim", api_sim_get)
    app.router.add_post("/api/sim", api_sim_post)
    app.router.add_get("/sim", sim_page)
    app.router.add_static("/sim-static/", WEB / "sim")
    app.router.add_static("/common/", WEB / "common")
    app.router.add_static("/vendor/", WEB / "vendor")
    app.router.add_get("/virtual", virtual_page)
    app.router.add_static("/virtual-static/", WEB / "virtual")

    _load_plugins(app, gateway, plugins)

    app.router.add_get("/", index)
    app.router.add_static("/", ui, show_index=False)
    return app


def _with_sim(state: dict, sim) -> dict:
    if sim is not None:
        state["sim.scenario"] = sim.scenario.name
        state["sim.links"] = dict(sim.links)
        state["sim.grade_pct"] = round(sim.vehicle.inp.grade_pct, 1)
        state["sim.paused"] = sim.paused
        demo = sim.demo_info()
        if demo:
            state["sim.demo"] = demo
        # The fake tilt sensor and GPS stand in for the Pi's own sensor service (not fitted yet).
        for k, v in sim.sensors.state().items():
            state.setdefault(k, v)
    return state


def _load_plugins(app, gateway, plugins) -> None:
    names = list(plugins)
    try:
        importlib.import_module("teryx_dash")
        if "teryx_dash" not in names:
            names.append("teryx_dash")
    except ImportError:
        pass
    for name in names:
        mod = importlib.import_module(name)
        mod.setup_routes(app, gateway)
        log.info("plugin loaded: %s", name)
