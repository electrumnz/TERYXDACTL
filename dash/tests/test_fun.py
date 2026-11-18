"""Fun screen back end: the parked rule, the streaming window and its guard."""

import asyncio
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from teryx_dash import fun as F

PARKED = {"in.park": True, "mc.speed": 0.0, "mc.online": True}


class Proc:
    def __init__(self, args):
        self.args, self.pid, self.dead = args, 999999, False

    def poll(self):
        return 0 if self.dead else None

    def terminate(self):
        self.dead = True


@pytest.fixture
def state():
    return dict(PARKED)


@pytest.fixture
async def client(tmp_path, state, monkeypatch):
    monkeypatch.setenv("TERYX_FUN_WINDOW", "1")
    monkeypatch.setattr(F, "find_browser", lambda: "/usr/bin/chromium")
    monkeypatch.setattr(F, "WATCH_S", 0.02)
    procs = []

    def spawn(args):
        p = Proc(args)
        procs.append(p)
        return p

    monkeypatch.setattr(F.os, "killpg", lambda pid, sig: [p.terminate() for p in procs if p.pid == pid])
    settings = tmp_path / "dash-settings.json"
    settings.write_text(json.dumps({"fun": {"streams": [{"id": "sky", "name": "Sky Go", "url": "https://www.skygo.co.nz/"},
                                                        {"id": "bad", "name": "Bad", "url": "http://example.com/"}]}}))
    app = web.Application()
    win = F.setup_fun_routes(app, object(), tmp_path, lambda: settings, lambda: state, spawn)
    c = TestClient(TestServer(app))
    await c.start_server()
    c.win, c.procs = win, procs
    yield c
    await c.close()


@pytest.mark.parametrize("s,ok", [
    (PARKED, True),
    ({**PARKED, "in.park": False}, False),
    ({**PARKED, "mc.speed": 3.2}, False),
    ({**PARKED, "mc.speed": -1.0}, False),
    ({**PARKED, "mc.online": False}, False),
    ({**PARKED, "pico.speed_valid": False}, False),
    ({**PARKED, "pico.parked": False}, False),
    ({}, False),
])
def test_parked_rule(s, ok):
    assert F.is_parked(s) is ok


def test_stream_urls_https_only():
    assert F.stream_url("netflix", {}) == "https://www.netflix.com/"
    assert F.stream_url("nope", {}) is None
    extra = {"fun": {"streams": [{"id": "x", "url": "http://a.b/"}, {"id": "y", "url": "https://a.b/"}]}}
    assert F.stream_url("x", extra) is None
    assert F.stream_url("y", extra) == "https://a.b/"


def test_browser_window_sits_under_the_top_bar():
    a = F.browser_args("chromium", "https://www.youtube.com/", Path("/tmp/p"))
    assert "--app=https://www.youtube.com/" in a
    assert f"--window-position=0,{F.TOP_BAR_PX}" in a
    assert f"--window-size=1280,{800 - F.TOP_BAR_PX}" in a


async def test_watch_opens_a_window_when_parked(client):
    r = await client.post("/api/fun/watch", json={"id": "netflix"})
    assert r.status == 200 and (await r.json())["window"] is True
    assert client.win.open and client.procs[0].args[1] == "--app=https://www.netflix.com/"
    st = await (await client.get("/api/fun")).json()
    assert st["open"] and st["stream"] == "netflix"


async def test_watch_refused_unless_parked(client, state):
    state["in.park"] = False
    r = await client.post("/api/fun/watch", json={"id": "youtube"})
    assert r.status == 409 and "park brake" in (await r.json())["error"]
    state["in.park"], state["mc.speed"] = True, 12
    r = await client.post("/api/fun/watch", json={"id": "youtube"})
    assert r.status == 409 and "moving" in (await r.json())["error"]
    assert not client.procs


async def test_extra_streams_from_settings(client):
    assert (await client.post("/api/fun/watch", json={"id": "sky"})).status == 200
    assert (await client.post("/api/fun/watch", json={"id": "bad"})).status == 404
    assert (await client.post("/api/fun/watch", json={})).status == 400


async def test_window_shuts_when_the_park_brake_comes_off(client, state):
    await client.post("/api/fun/watch", json={"id": "youtube"})
    assert client.win.open
    state["in.park"] = False
    for _ in range(50):
        if not client.win.open:
            break
        await asyncio.sleep(0.02)
    assert not client.win.open and client.procs[0].dead
    assert (await (await client.get("/api/fun")).json())["closed_why"] == "not parked"


async def test_one_window_at_a_time_and_close(client):
    await client.post("/api/fun/watch", json={"id": "youtube"})
    await client.post("/api/fun/watch", json={"id": "netflix"})
    assert client.procs[0].dead and not client.procs[1].dead
    r = await (await client.post("/api/fun/close")).json()
    assert r["closed"] and client.procs[1].dead


async def test_no_window_off_the_pi(tmp_path, monkeypatch):
    monkeypatch.delenv("TERYX_FUN_WINDOW", raising=False)
    gw = type("G", (), {"bus_spec": "udp"})()
    assert not F.window_wanted(gw)
    assert F.window_wanted(type("G", (), {"bus_spec": "socketcan:can0"})())
    app = web.Application()
    F.setup_fun_routes(app, gw, tmp_path, lambda: tmp_path / "none.json", lambda: dict(PARKED))
    c = TestClient(TestServer(app))
    await c.start_server()
    try:
        j = await (await c.post("/api/fun/watch", json={"id": "youtube"})).json()
        assert j == {"ok": True, "window": False, "url": "https://www.youtube.com/"}
        assert (await (await c.post("/api/fun/screen", json={"on": False})).json())["done"] is False
    finally:
        await c.close()


@pytest.mark.skipif(not shutil.which("node"), reason="needs node")
def test_dash_fun_js():
    """The camp mode maths and the parked rule in the page (plain node, no browser)."""
    t = Path(__file__).with_name("fun_js.test.mjs")
    r = subprocess.run(["node", str(t)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(not shutil.which("node"), reason="needs node")
def test_dash_telltales_js():
    """Warning lights and the alerts behind them (plain node, no browser)."""
    t = Path(__file__).with_name("telltales_js.test.mjs")
    r = subprocess.run(["node", str(t)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
