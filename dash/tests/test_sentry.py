"""Sentry and dashcam (docs/sentry.md): when it records, motion, clips on disk, and the routes."""

import json
import os
import time

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from teryx_dash import sentry as S
from teryx_dash.sentry import ClipStore, MotionDetector, SentryPlan, record_command, settings_from, stamp

CFG = settings_from({})


def test_plan_modes():
    p = SentryPlan()
    # Key on, unlocked: dashcam.
    assert p.step({"in.ignition": True, "lock.state": "unlocked"}, CFG, 0) == []
    assert p.mode == "dashcam"
    # Key off, unlocked: off. Locked but the Pico isn't holding power: off.
    p.step({"in.ignition": False, "lock.state": "unlocked"}, CFG, 1)
    assert p.mode == "off"
    st = {"in.ignition": False, "lock.state": "locked", "an.aux_12v": 12.7}
    assert p.wants_hold(st, CFG, 2)                 # heartbeat says "sentry" before key-off
    p.step(st, CFG, 2)
    assert p.mode == "off"
    st["pico.sentry_hold"] = True
    p.step(st, CFG, 3)
    assert p.mode == "sentry"
    # Time up after maxHours: stops, and stays stopped until the key goes on.
    p.step(st, CFG, 3 + 12 * 3600)
    assert p.mode == "off" and p.stop_reason == "time up" and not p.wants_hold(st, CFG, 3 + 12 * 3600)
    p.step({**st, "in.ignition": True}, CFG, 50000)
    assert p.stop_reason is None


def test_plan_battery_and_attempted_start():
    p = SentryPlan()
    st = {"in.ignition": False, "lock.state": "locked", "an.aux_12v": 12.6, "pico.sentry_hold": True}
    p.step(st, CFG, 0)
    assert p.mode == "sentry"
    p.step({**st, "an.aux_12v": 12.1}, CFG, 10)
    assert p.mode == "off" and p.stop_reason == "12V low"
    p = SentryPlan()
    p.step({**st, "pico.sentry_flat": True}, CFG, 0)
    assert p.mode == "off" and p.stop_reason == "12V low"
    # Someone turns the key while it's locked: one event per key-on, and the cameras record.
    p = SentryPlan()
    p.step(st, CFG, 0)
    assert p.step({**st, "in.ignition": True}, CFG, 1) == ["attempted_start"]
    assert p.mode == "dashcam"
    assert p.step({**st, "in.ignition": True}, CFG, 2) == []
    # Sentry off in settings: never holds.
    assert not SentryPlan().wants_hold(st, {**CFG, "enabled": False}, 0)


def test_motion_detector():
    m = MotionDetector()
    still = bytes([80]) * (64 * 36)
    for _ in range(10):
        assert not m.feed(still)
    # A little noise and a slow brightening (dusk): nothing.
    import random
    rnd = random.Random(1)
    for i in range(20):
        assert not m.feed(bytes(min(255, 80 + i + rnd.randint(-5, 5)) for _ in range(64 * 36)))
    # Someone walks in: a block of 12 x 12 pixels changes a lot, two frames running.
    m = MotionDetector()
    for _ in range(6):
        m.feed(still)
    person = bytearray(still)
    for y in range(10, 22):
        for x in range(20, 32):
            person[y * 64 + x] = 220
    assert not m.feed(bytes(person))
    assert m.feed(bytes(person))


def touch_segment(store, cam, t, size=1000):
    d = store.loop / cam
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{stamp(t)}.mp4"
    p.write_bytes(b"x" * size)
    return p


def test_clips_link_before_and_after(tmp_path):
    store = ClipStore(tmp_path)
    t0 = time.mktime((2026, 11, 18, 10, 0, 0, 0, 0, -1))
    for i in range(5):
        touch_segment(store, "rear", t0 + i * 60)
        touch_segment(store, "cabin", t0 + i * 60)
    ev = store.new_event("motion", t0 + 125, snapshot=b"\xff\xd8jpeg")
    files = sorted(p.name for p in (store.events / ev).iterdir())
    assert "cabin.jpg" in files and f"rear-{stamp(t0 + 120)}.mp4" in files and f"rear-{stamp(t0 + 60)}.mp4" in files
    # The piece after the event turns up later and gets added.
    touch_segment(store, "rear", t0 + 300)
    store.finish(t0 + 300)
    ev_list = store.list_events()
    assert ev_list[0]["reason"] == "motion" and ev_list[0]["id"] == ev
    # Hard links: deleting the loop piece leaves the clip.
    (store.loop / "rear" / f"{stamp(t0 + 120)}.mp4").unlink()
    assert (store.events / ev / f"rear-{stamp(t0 + 120)}.mp4").exists()
    # Paths are checked.
    assert store.event_file(ev, "../../etc/passwd") is None
    assert store.event_file("../x", "cabin.jpg") is None
    assert store.event_file(ev, "cabin.jpg") is not None


def test_prune_oldest_first_and_keeps_kept(tmp_path):
    store = ClipStore(tmp_path)
    t0 = time.mktime((2026, 11, 18, 10, 0, 0, 0, 0, -1))
    for i in range(20):
        touch_segment(store, "rear", t0 + i * 60, size=1000)
    store.prune(total_bytes=13_334, events_pct=25)   # loop budget just over 10 000 bytes
    left = store.segments("rear")
    assert len(left) == 10 and left[0][0] == t0 + 10 * 60
    # Events over their share go oldest first, except kept ones.
    a = store.new_event("manual", t0 + 1000)
    b = store.new_event("motion", t0 + 1100)
    (store.events / a / "keep").touch()
    for name in (a, b):
        (store.events / name / "rear-20261118-100000.mp4").write_bytes(b"x" * 400_000)
    store.prune(total_bytes=1_000_000, events_pct=25)
    ids = [e["id"] for e in store.list_events()]
    assert a in ids and b not in ids


def test_record_commands():
    cmd = record_command("rear", "/dev/video0", S.Path("/v/loop/rear"), CFG)
    s = " ".join(cmd)
    assert "libx264" in s and "ultrafast" in s and "-segment_time 60" in s and "2000k" in s
    assert "scale=64:36" in s and s.endswith("pipe:1")
    copy = " ".join(record_command("rear", "/dev/video0", S.Path("/v"), CFG, h264_camera=True))
    assert "libx264" not in copy and "-c:v copy" in copy and "-input_format h264" in copy
    csi = record_command("cabin", "csi1", S.Path("/v"), CFG)
    assert csi[0] == "sh" and "rpicam-vid" in csi[2] and "--camera 1" in csi[2]


class Gw:
    def __init__(self):
        self.state = {"in.ignition": False, "lock.state": "locked", "an.aux_12v": 12.7}
        self.sentry = None

    def snapshot(self):
        return dict(self.state)

    def set_sentry(self, on):
        self.sentry = on


async def test_service_and_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("TERYX_VIDEO_DIR", str(tmp_path / "video"))
    settings = tmp_path / "dash-settings.json"
    settings.write_text(json.dumps({"camera": {"cams": {"cabin": {"fitted": True, "v4l2Device": "csi1"}}}}))
    gw = Gw()
    app = web.Application()
    svc = S.setup_sentry_routes(app, gw, lambda: settings, gw.snapshot, tick_s=3600)
    svc.recorder = None   # no cameras here
    c = TestClient(TestServer(app))
    await c.start_server()
    try:
        await svc.tick()
        assert gw.sentry is True and svc.plan.mode == "off"   # not held yet
        gw.state["pico.sentry_hold"] = True
        await svc.tick()
        assert svc.plan.mode == "sentry"
        svc.motion("front")
        await svc.tick()
        d = await (await c.get("/api/sentry")).json()
        assert d["events"][0]["reason"] == "motion"
        ev = d["events"][0]["id"]
        # Movement straight after doesn't make another clip.
        svc.motion("front")
        await svc.tick()
        assert len((await (await c.get("/api/sentry")).json())["events"]) == 1
        assert (await c.post(f"/api/clips/{ev}/keep")).status == 200
        assert (await c.post("/api/sentry/save")).status == 200
        assert (await c.delete(f"/api/clips/{ev}")).status == 200
        assert (await c.get(f"/api/clips/{ev}/cabin.jpg")).status == 404
        assert (await c.get("/api/clips/x/..%2F..%2Fetc%2Fpasswd")).status == 404
        # Turn sentry off in settings: the heartbeat stops asking.
        settings.write_text(json.dumps({"sentry": {"enabled": False}}))
        await svc.tick()
        assert gw.sentry is False
    finally:
        await c.close()


async def test_no_drive_no_recording(tmp_path, monkeypatch):
    monkeypatch.delenv("TERYX_VIDEO_DIR", raising=False)
    settings = tmp_path / "s.json"
    settings.write_text(json.dumps({"sentry": {"storage": str(tmp_path / "missing")}}))
    gw = Gw()
    gw.state.update({"in.ignition": True, "lock.state": "unlocked"})
    svc = S.SentryService(gw, gw.snapshot, lambda: json.loads(settings.read_text()))
    st = await svc.tick()
    assert st["mode"] == "dashcam" and st["recording"] == [] and "No video drive" in st["problem"]
    assert not os.path.exists(tmp_path / "missing")
