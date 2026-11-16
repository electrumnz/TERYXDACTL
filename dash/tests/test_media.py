"""Audio and media: the sim and Pi back ends, the music library, and the /api/audio routes."""

import json
import struct

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from teryx_dash import audio as A
from teryx_dash import library as L
from teryx_dash import routes


class Gw:
    bus_spec = "udp"

    def snapshot(self):
        return {"mc.speed": 0.0}


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setattr(routes, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(routes, "SETTINGS_FILE", tmp_path / "dash-settings.json")
    monkeypatch.setenv("TERYX_OTA_ROOT", str(tmp_path / "ota"))
    monkeypatch.setenv("TERYX_MUSIC_DIRS", str(tmp_path / "music"))
    monkeypatch.delenv("TERYX_AUDIO", raising=False)
    app = web.Application()
    routes.setup_routes(app, Gw())
    c = TestClient(TestServer(app))
    await c.start_server()
    yield c
    await c.close()


# ---------------- picking a back end ----------------

def test_sim_on_a_laptop_bus(monkeypatch):
    monkeypatch.delenv("TERYX_AUDIO", raising=False)
    assert isinstance(A.pick_backend(Gw()), A.SimAudio)


def test_env_wins(monkeypatch):
    monkeypatch.setenv("TERYX_AUDIO", "pi")
    assert isinstance(A.pick_backend(Gw()), A.PiAudio)
    monkeypatch.setenv("TERYX_AUDIO", "sim")
    assert isinstance(A.pick_backend(type("G", (), {"bus_spec": "socketcan:can0"})()), A.SimAudio)


def test_output_kinds():
    assert A.output_kind("alsa_output.platform-107c701400.hdmi.hdmi-stereo") == "hdmi"
    assert A.output_kind("alsa_output.usb-C-Media_USB_Audio-00.analog-stereo", {"device.bus": "usb"}) == "usb"
    assert A.output_kind("alsa_output.platform-soc_sound.stereo-fallback", {"alsa.card_name": "snd_rpi_hifiberry_dacplus"}) == "i2s"
    assert A.output_kind("bluez_output.AA_BB", {"device.api": "bluez5"}) == "bluetooth"


# ---------------- the sim ----------------

async def test_sim_phone_plays_and_skips():
    s = A.SimAudio()
    st = await s.status()
    assert st["bt"]["player"] is None and len(st["outputs"]) == 3
    s.sim({"phone": True})
    st = await s.status()
    assert st["bt"]["player"]["status"] == "playing"
    first = st["bt"]["player"]["title"]
    await s.bt_command("next")
    assert (await s.status())["bt"]["player"]["title"] != first
    await s.bt_command("pause")
    assert (await s.status())["bt"]["player"]["status"] == "paused"
    with pytest.raises(ValueError):
        await s.bt_command("rm -rf")


async def test_duck_sets_phone_level():
    s = A.SimAudio()
    await s.set_media_level(0.8)
    await s.duck(True, 0.25)
    assert s.bt_level() == pytest.approx(0.2)
    await s.duck(False)
    assert s.bt_level() == pytest.approx(0.8)
    assert ("bt_level", 0.2) in s.log


# ---------------- the Pi back end, with pretend commands ----------------

SINKS = [
    {"index": 55, "name": "alsa_output.platform-hdmi.hdmi-stereo", "description": "Built-in Audio Digital Stereo (HDMI)",
     "properties": {"device.api": "alsa"}, "volume": {"front-left": {"value_percent": "100%"}, "front-right": {"value_percent": "100%"}}},
    {"index": 61, "name": "alsa_output.usb-dac.analog-stereo", "description": "USB Audio Analog Stereo",
     "properties": {"device.api": "alsa", "device.bus": "usb"}, "volume": {"front-left": {"value_percent": "80%"}, "front-right": {"value_percent": "80%"}}},
]
INPUTS = [
    {"index": 90, "properties": {"media.name": "chromium", "application.name": "Chromium"}},
    {"index": 91, "properties": {"node.name": "bluez_input.AA_BB_CC_DD_EE_FF.2", "device.api": "bluez5", "api.bluez5.address": "AA:BB:CC:DD:EE:FF"}},
]


def v(t, d):
    return {"type": t, "data": d}


BLUEZ = {"type": "a{oa{sa{sv}}}", "data": [{
    "/org/bluez/hci0": {"org.bluez.Adapter1": {"Alias": v("s", "Teryx"), "Powered": v("b", True)}},
    "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF": {"org.bluez.Device1": {
        "Address": v("s", "AA:BB:CC:DD:EE:FF"), "Name": v("s", "Phone"), "Alias": v("s", "Test phone"),
        "Paired": v("b", True), "Connected": v("b", True), "Trusted": v("b", False)}},
    "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF/player0": {"org.bluez.MediaPlayer1": {
        "Status": v("s", "playing"), "Position": v("u", 61000), "Device": v("o", "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF"),
        "Track": v("a{sv}", {"Title": v("s", "A Song"), "Artist": v("s", "A Band"), "Album": v("s", "LP"), "Duration": v("u", 200000)})}},
    "/org/bluez/hci0/dev_11_22_33_44_55_66": {"org.bluez.Device1": {
        "Address": v("s", "11:22:33:44:55:66"), "Name": v("s", "Headphones"), "Paired": v("b", False), "Connected": v("b", False)}},
}]}


class FakeRun:
    def __init__(self):
        self.calls = []

    async def __call__(self, *args, timeout=8):
        self.calls.append(args)
        if args[:2] == ("pactl", "get-default-sink"):
            return "alsa_output.usb-dac.analog-stereo\n"
        if args[:4] == ("pactl", "-f", "json", "list") and args[4] == "sinks":
            return json.dumps(SINKS)
        if args[:4] == ("pactl", "-f", "json", "list") and args[4] == "sink-inputs":
            return json.dumps(INPUTS)
        if args[0] == "busctl" and "GetManagedObjects" in args:
            return json.dumps(BLUEZ)
        return ""


async def test_pi_status_reads_pipewire_and_bluez():
    run = FakeRun()
    p = A.PiAudio(run)
    st = await p.status()
    assert [o["kind"] for o in st["outputs"]] == ["hdmi", "usb"]
    assert [o["default"] for o in st["outputs"]] == [False, True]
    assert st["output_level"] == pytest.approx(0.8)
    bt = st["bt"]
    assert bt["available"] and bt["name"] == "Teryx"
    assert [d["name"] for d in bt["devices"]] == ["Test phone"]   # unpaired headphones left out
    assert bt["player"]["title"] == "A Song" and bt["player"]["position_ms"] == 61000
    assert "path" not in bt["player"]


async def test_pi_ducks_only_the_bluetooth_stream():
    run = FakeRun()
    p = A.PiAudio(run)
    await p.set_media_level(1.0)
    await p.duck(True, 0.3)
    vols = [c for c in run.calls if c[:2] == ("pactl", "set-sink-input-volume")]
    assert vols[-1] == ("pactl", "set-sink-input-volume", "91", "30%")
    assert all(c[2] == "91" for c in vols)   # never the browser's own stream


async def test_pi_commands_go_to_the_player():
    run = FakeRun()
    p = A.PiAudio(run)
    await p.bt_command("next")
    assert run.calls[-1] == ("busctl", "call", "org.bluez", "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF/player0", "org.bluez.MediaPlayer1", "Next")
    with pytest.raises(ValueError):
        await p.bt_forget("AA:BB; reboot")
    await p.bt_forget("AA:BB:CC:DD:EE:FF")
    assert run.calls[-1] == ("bluetoothctl", "remove", "AA:BB:CC:DD:EE:FF")


async def test_pi_output_must_exist():
    run = FakeRun()
    p = A.PiAudio(run)
    with pytest.raises(ValueError):
        await p.set_output("nope")
    await p.set_output("alsa_output.platform-hdmi.hdmi-stereo")
    assert ("pactl", "set-default-sink", "alsa_output.platform-hdmi.hdmi-stereo") in run.calls


async def test_pairing_trusts_new_phone_and_closes():
    run = FakeRun()
    p = A.PiAudio(run)
    await p.bt_pair(True)
    assert ("bluetoothctl", "discoverable", "on") in run.calls
    await p.status()
    assert ("bluetoothctl", "trust", "AA:BB:CC:DD:EE:FF") in run.calls
    p.bt.pairing_until = 1.0   # long gone
    await p.status()
    assert ("bluetoothctl", "pairable", "off") in run.calls and p.pairing_left() == 0


# ---------------- music library ----------------

def id3(title, artist, album):
    def frame(fid, text):
        body = b"\x03" + text.encode()
        return fid + struct.pack(">I", len(body)) + b"\x00\x00" + body
    frames = frame(b"TIT2", title) + frame(b"TPE1", artist) + frame(b"TALB", album)
    size = len(frames)
    ss = bytes([(size >> 21) & 0x7F, (size >> 14) & 0x7F, (size >> 7) & 0x7F, size & 0x7F])
    return b"ID3\x03\x00\x00" + ss + frames + b"\xff\xfb" + b"\x00" * 64


def test_library_reads_tags_and_names(tmp_path, monkeypatch):
    m = tmp_path / "music" / "Road Trip"
    m.mkdir(parents=True)
    (m / "tagged.mp3").write_bytes(id3("Real Title", "Real Band", "Real Album"))
    (m / "Some Band - Some Song.ogg").write_bytes(b"OggS")
    (m / "01 - Intro.flac").write_bytes(b"fLaC")
    (m / "notes.txt").write_text("not music")
    monkeypatch.setenv("TERYX_MUSIC_DIRS", str(tmp_path / "music"))
    lib = L.Library()
    tracks = {t["title"]: t for t in lib.scan(force=True)}
    assert set(tracks) == {"Real Title", "Some Song", "Intro"}
    assert tracks["Real Title"]["artist"] == "Real Band" and tracks["Real Title"]["album"] == "Real Album"
    assert tracks["Some Song"]["artist"] == "Some Band" and tracks["Some Song"]["album"] == "Road Trip"
    assert tracks["Intro"]["artist"] == ""
    assert lib.path(tracks["Intro"]["id"]).name == "01 - Intro.flac"
    assert lib.path("../../etc/passwd") is None


def test_demo_tunes_are_wav():
    data = L.demo_wav("demo-1")
    assert data[:4] == b"RIFF" and data[8:12] == b"WAVE" and len(data) > 100_000
    assert L.demo_wav("nope") is None


# ---------------- routes ----------------

async def test_audio_routes(client):
    st = await (await client.get("/api/audio")).json()
    assert st["backend"] == "sim"
    r = await client.post("/api/audio/output", json={"id": "sim_i2s"})
    assert r.status == 200 and [o["id"] for o in (await r.json())["outputs"] if o["default"]] == ["sim_i2s"]
    assert (await client.post("/api/audio/output", json={"id": "bogus"})).status == 400
    assert (await client.post("/api/audio/media-level", json={"level": "loud"})).status == 400
    r = await client.post("/api/audio/duck", json={"on": True, "duck_to": 0.5})
    assert (await r.json())["ducked"] is True
    assert (await client.post("/api/audio/bt/next")).status == 502          # no phone yet
    await client.post("/api/audio/sim", json={"phone": True})
    r = await client.post("/api/audio/bt/pause")
    assert (await r.json())["bt"]["player"]["status"] == "paused"
    assert (await client.post("/api/audio/bt/reboot")).status in (404, 405)


async def test_library_route_and_files(client, tmp_path):
    (tmp_path / "music").mkdir()
    (tmp_path / "music" / "Band - Tune.mp3").write_bytes(b"\xff\xfb" + b"\x00" * 100)
    tracks = (await (await client.get("/api/media/library?rescan=1")).json())["tracks"]
    titles = [t["title"] for t in tracks]
    assert "Tune" in titles and "Gravel Road" in titles     # real file plus the sim's demo tunes
    t = next(t for t in tracks if t["title"] == "Tune")
    r = await client.get(t["url"])
    assert r.status == 200 and len(await r.read()) == 102
    assert (await client.get("/api/media/file/ffffffffffffffff")).status == 404


async def test_radio_relay_only_plays_saved_stations(client, tmp_path):
    assert (await client.get("/api/media/radio/0")).status == 404
    (tmp_path / "dash-settings.json").write_text(json.dumps({"media": {"stations": [{"name": "x", "url": "file:///etc/passwd"}]}}))
    assert (await client.get("/api/media/radio/0")).status == 400
