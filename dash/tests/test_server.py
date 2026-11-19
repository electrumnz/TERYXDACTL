"""Tests for the dash server extras: settings, control box settings, OTA, safety checks."""

import asyncio
import json
import subprocess
from pathlib import Path

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from teryx_dash import ota as ota_mod
from teryx_dash import routes


class FakeGateway:
    def __init__(self):
        self.state = {"mc.speed": 0.0, "mc.online": True, "an.diff_pos_raw": 1234}
        self.settings = {}
        self.sent = []

    def snapshot(self):
        return dict(self.state)

    async def set_setting(self, key, value):
        self.sent.append((key, value))
        self.settings[key] = value
        return True


@pytest.fixture
def gw():
    return FakeGateway()


@pytest.fixture
async def client(gw, tmp_path, monkeypatch):
    monkeypatch.setattr(routes, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(routes, "SETTINGS_FILE", tmp_path / "dash-settings.json")
    monkeypatch.setenv("TERYX_OTA_ROOT", str(tmp_path / "ota"))
    app = web.Application()
    routes.setup_routes(app, gw)
    c = TestClient(TestServer(app))
    await c.start_server()
    yield c
    await c.close()


async def test_settings_round_trip(client):
    assert await (await client.get("/api/settings")).json() == {}
    r = await client.put("/api/settings", json={"units": "mph", "camera": {"mirror": False}})
    assert r.status == 200
    assert (await (await client.get("/api/settings")).json())["units"] == "mph"


async def test_camera_picks_device_per_camera(client, monkeypatch):
    """Each camera (rear, front, trailer) streams its own /dev/videoN; one not set up says so."""
    from teryx_dash import camera as cam_mod
    seen = []

    async def fake_mjpeg(req, device):
        seen.append(device)
        return web.json_response({"device": device})

    monkeypatch.setattr(cam_mod, "mjpeg_response", fake_mjpeg)
    # Nothing saved yet: rear falls back to the video board's input 0, trailer has no device.
    await client.get("/api/camera.mjpg")
    await client.get("/api/camera.mjpg?cam=trailer")
    assert seen == ["adv:0", ""]
    # Old single-camera settings file: its device is the rear camera.
    await client.put("/api/settings", json={"camera": {"v4l2Device": "/dev/video4"}})
    await client.get("/api/camera.mjpg?cam=rear")
    await client.put("/api/settings", json={"camera": {"cams": {"trailer": {"v4l2Device": "/dev/video2"}}}})
    await client.get("/api/camera.mjpg?cam=trailer")
    assert seen[2:] == ["/dev/video4", "/dev/video2"]


async def test_camera_device_checked(client):
    """No device, or anything that isn't /dev/videoN, is refused before ffmpeg is started."""
    from teryx_dash import camera as cam_mod

    class Req:  # mjpeg_response never touches the request when it refuses
        pass

    assert (await cam_mod.mjpeg_response(Req(), "")).status == 404
    assert (await cam_mod.mjpeg_response(Req(), "/dev/video0/../sda")).status == 400
    assert (await cam_mod.mjpeg_response(Req(), "/etc/passwd")).status == 400
    assert (await cam_mod.mjpeg_response(Req(), "csi2")).status == 400
    assert (await cam_mod.mjpeg_response(Req(), "csi0; reboot")).status == 400


async def test_settings_rejects_junk(client):
    r = await client.put("/api/settings", data="[1,2]")
    assert r.status == 400


async def test_pico_settings_list_and_set(client, gw):
    data = await (await client.get("/api/pico-settings")).json()
    names = {s["name"]: s for s in data["settings"]}
    assert names["fourwd_max_kmh"]["value"] == 1
    assert names["tray_overcurrent_da"]["scale"] == 0.1
    r = await client.put("/api/pico-settings", json={"name": "fourwd_max_kmh", "value": 7})
    assert r.status == 200
    assert gw.sent[-1] == (3, 7)


async def test_pico_setting_out_of_range(client):
    r = await client.put("/api/pico-settings", json={"name": "fourwd_max_kmh", "value": 99})
    assert r.status == 400


async def test_pico_save_sends_save_key(client, gw):
    assert (await client.post("/api/pico-settings/save")).status == 200
    assert gw.sent[-1] == (0xF0, 1)


async def test_diff_calibrate_uses_live_raw(client, gw):
    r = await client.post("/api/diff-calibrate", json={"which": "max"})
    assert (await r.json())["raw"] == 1234
    assert gw.sent[-1] == (15, 1234)


async def test_diff_calibrate_refused_when_moving(client, gw):
    gw.state["mc.speed"] = 12
    r = await client.post("/api/diff-calibrate", json={"which": "min"})
    assert r.status == 400


async def test_shutdown_refused_when_moving(client, gw):
    gw.state["mc.speed"] = 20
    assert (await client.post("/api/system/shutdown")).status == 400


async def test_speed_unknown_counts_as_moving(gw):
    gw.state["mc.online"] = False
    assert routes.is_stopped(gw) is False


# ---------- OTA ----------

def test_tag_order():
    assert ota_mod.newest(["v1.0.0", "v1.2.0", "v1.10.0", "junk"], "stable") == "v1.10.0"
    assert ota_mod.newest(["v1.2.0", "v1.3.0-beta.1"], "stable") == "v1.2.0"
    assert ota_mod.newest(["v1.2.0", "v1.3.0-beta.1"], "beta") == "v1.3.0-beta.1"
    assert ota_mod.newest(["v1.3.0-beta.2", "v1.3.0"], "beta") == "v1.3.0"


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def ota_env(tmp_path):
    """A pretend Pi: a remote repo with two tagged releases, and an OTA root with v1.0.0 installed."""
    remote = tmp_path / "remote"
    remote.mkdir()
    git(remote, "init", "-q", "-b", "main")
    git(remote, "config", "user.email", "test@example.invalid")
    git(remote, "config", "user.name", "test")
    (remote / "app.txt").write_text("one")
    git(remote, "add", ".")
    git(remote, "commit", "-qm", "one")
    git(remote, "tag", "v1.0.0")
    (remote / "app.txt").write_text("two")
    git(remote, "commit", "-qam", "two")
    git(remote, "tag", "-a", "v1.1.0", "-m", "Faster drive screen")
    root = tmp_path / "opt"
    root.mkdir()
    git(tmp_path, "clone", "-q", str(remote), str(root / "repo"))
    git(root / "repo", "worktree", "add", "--detach", str(root / "releases" / "v1.0.0"), "v1.0.0")
    (root / "current").symlink_to(root / "releases" / "v1.0.0")
    cfg = ota_mod.OtaConfig(root=root, restart_cmd="true")
    return cfg


async def wait_idle(o):
    for _ in range(200):
        if o._task is None or o._task.done():
            return
        await asyncio.sleep(0.05)


async def test_check_and_install(ota_env, monkeypatch):
    monkeypatch.setattr(ota_mod, "HEALTHY_AFTER_S", 0)
    o = ota_mod.Ota(cfg=ota_env)
    o.check("stable")
    await wait_idle(o)
    st = o.status()
    assert st["dash"]["current"] == "v1.0.0"
    assert st["dash"]["available"] == "v1.1.0", st
    assert st["dash"]["notes"] == "Faster drive screen"
    o.install()
    await wait_idle(o)
    assert o.state == "restarting", o.message
    assert ota_mod.current_version(ota_env) == "v1.1.0"
    assert (ota_env.current_link / "app.txt").read_text() == "two"
    saved = ota_mod.load_state(ota_env)
    assert saved["previous"] == "v1.0.0" and saved["pending"] == "v1.1.0"
    await o.confirm_when_healthy(lambda: True)
    assert ota_mod.load_state(ota_env)["pending"] is None


async def test_install_refused_when_moving(ota_env):
    o = ota_mod.Ota(cfg=ota_env, is_stopped=lambda: False)
    o.available = "v1.1.0"
    with pytest.raises(RuntimeError):
        o.install()


async def test_bad_update_rolls_back_on_boot(ota_env):
    o = ota_mod.Ota(cfg=ota_env)
    o.check()
    await wait_idle(o)
    o.install()
    await wait_idle(o)
    assert ota_mod.boot_check(ota_env).startswith("pending")
    assert ota_mod.boot_check(ota_env).startswith("pending")
    assert ota_mod.boot_check(ota_env) == "rolled back from v1.1.0"
    assert ota_mod.current_version(ota_env) == "v1.0.0"
    assert ota_mod.boot_check(ota_env) == "ok"


async def test_manual_rollback(ota_env):
    o = ota_mod.Ota(cfg=ota_env)
    o.check(); await wait_idle(o)
    o.install(); await wait_idle(o)
    o.rollback(); await wait_idle(o)
    assert ota_mod.current_version(ota_env) == "v1.0.0"


async def test_parked_flag_from_control_box_wins(gw):
    gw.state["pico.parked"] = False
    assert routes.is_stopped(gw) is False
    gw.state["pico.parked"] = True
    assert routes.is_stopped(gw) is True


async def test_clear_faults_sends_key(client, gw):
    assert (await client.post("/api/pico-settings/clear-faults")).status == 200
    assert gw.sent[-1] == (0xF2, 1)


# ---------- trips ----------

async def test_trips_endpoint_and_reset(client, gw):
    from teryx_dash.routes import TRIPS_KEY
    trips = client.server.app[TRIPS_KEY]
    gw.state.update({"mc.soc": 60, "mc.batt_v": 76, "mc.batt_a": 40, "mc.speed": 30, "in.ignition": True})
    for t in range(1, 200):
        trips.sample(gw.snapshot(), now=t)
    d = await (await client.get("/api/trips")).json()
    assert d["trip_a"]["km"] > 1 and d["range_km"] > 0 and d["pack_kwh"] == 7.5
    await client.put("/api/settings", json={"packKwh": 10})
    d = await (await client.get("/api/trips")).json()
    assert d["pack_kwh"] == 10
    d = await (await client.post("/api/trips/reset/trip-a")).json()
    assert d["trip_a"]["km"] == 0
    assert (await client.post("/api/trips/reset/everything")).status == 404


# ---------- Wi-Fi from the on-screen keyboard ----------

@pytest.fixture
def nmcli(monkeypatch):
    calls = []
    outputs = {}

    async def fake_run(*args, timeout=20, stderr=False):
        calls.append(args)
        for key, out in outputs.items():
            if key in " ".join(args):
                return out
        return ""
    monkeypatch.setattr(routes, "_run", fake_run)
    monkeypatch.setattr(routes.shutil, "which", lambda name: "/usr/bin/" + name)
    return calls, outputs


async def test_wifi_add_passes_args_without_a_shell(client, nmcli):
    calls, outputs = nmcli
    outputs["dev wifi connect"] = "Device 'wlan0' successfully activated"
    r = await client.post("/api/wifi/add", json={"ssid": "Shed; rm -rf /", "password": "pass word 1"})
    assert r.status == 200
    assert calls[-1] == ("nmcli", "dev", "wifi", "connect", "Shed; rm -rf /", "password", "pass word 1")


async def test_wifi_add_checks_input(client, nmcli):
    assert (await client.post("/api/wifi/add", json={"ssid": ""})).status == 400
    assert (await client.post("/api/wifi/add", json={"ssid": "x" * 33})).status == 400
    assert (await client.post("/api/wifi/add", json={"ssid": "Shed", "password": "short"})).status == 400


async def test_wifi_add_reports_failure(client, nmcli):
    _, outputs = nmcli
    outputs["dev wifi connect"] = "Error: Connection activation failed: Secrets were required"
    r = await client.post("/api/wifi/add", json={"ssid": "Shed", "password": "wrongpass"})
    assert r.status == 502


async def test_wifi_scan_parses_and_dedupes(client, nmcli):
    _, outputs = nmcli
    outputs["dev wifi list"] = "Shed:70:WPA2\nShed:40:WPA2\nCafe\\:Free:55:\n:30:WPA2\n"
    d = await (await client.get("/api/wifi/scan")).json()
    assert d["networks"] == [{"ssid": "Shed", "signal": 70, "secure": True},
                             {"ssid": "Cafe:Free", "signal": 55, "secure": False}]


async def test_camera_status(client):
    """The dash asks whether the trailer camera is giving a picture. No board here: not known."""
    r = await client.get("/api/camera/status")
    assert r.status == 200
    j = await r.json()
    assert j["trailer"]["signal"] is None and j["board_watching"] is False
