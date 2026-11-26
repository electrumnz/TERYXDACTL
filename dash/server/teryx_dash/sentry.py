"""Sentry and dashcam recording (docs/sentry.md).

Nothing here texts or alerts anyone. Clips are saved on the Teryx, and you look at them when
you want to: on the dash (Settings > Sentry and clips), or from your phone over Tailscale once you've
turned data on with a CAMS text (docs/remote-access.md).

Modes, worked out every second from the live state:

    dashcam   key on: every fitted camera records in 1 minute pieces, oldest deleted first
    sentry    key off and LOCKED: the Pico keeps the Pi on (heartbeat "sentry"), the cameras
              keep recording into the loop and watch for movement. Ends after max_hours, or
              when the 12V drops under min_12v (the Pico also checks this itself, setting 32)
    off       anything else

Events (saved as a clip: 30 s before to 30 s after, from every camera that was recording):

    motion           something moved in front of a camera while in sentry
    attempted_start  the key went on while locked. The cabin camera's picture is the face shot
    manual           the SAVE button on the dash

Video goes to the USB SSD (mounted at /mnt/teryx-video), never the SD card by default: the
SD card holds the system, and a card written to all day wears out. No drive, no recording.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import videoboard
from typing import Any, Callable

from aiohttp import web

SEGMENT_S = 60
PRE_S = 30
POST_S = 30
CAMS = ("rear", "front", "trailer", "cabin")
# All the cameras share the video board's one decoder, so the dashcam and sentry record one of
# them at a time: the first fitted one in this order (the front is the dashcam).
BOARD_ORDER = ("front", "rear", "trailer", "cabin")
DEFAULTS = {
    "enabled": True,        # sentry when locked
    "dashcam": True,        # loop recording with the key on
    "maxHours": 12,         # sentry gives up after this long
    "min12v": 12.2,         # ...or when the 12V battery drops under this (Pico setting 32 too)
    "storage": "/mnt/teryx-video",
    "eventsPct": 25,        # share of the drive kept for saved clips; the loop gets the rest
    "width": 1280, "height": 720, "fps": 15, "kbps": 2000,
}
NAME_RE = re.compile(r"^\d{8}-\d{6}$")
EVENT_RE = re.compile(r"^\d{8}-\d{6}-[a-z_]+$")


def settings_from(dash_settings: dict) -> dict:
    s = dict(DEFAULTS)
    s.update({k: v for k, v in (dash_settings.get("sentry") or {}).items() if k in DEFAULTS})
    return s


def fitted_cams(dash_settings: dict) -> list[str]:
    cams = ((dash_settings.get("camera") or {}).get("cams") or {})
    out = [c for c in CAMS if (cams.get(c) or {}).get("fitted")]
    # Older settings files only had the rear camera, fitted by default.
    if not cams:
        out = ["rear"]
    return out


# ---------------------------------------------------------------- the plan (no I/O)
@dataclass
class SentryPlan:
    mode: str = "off"
    sentry_since: float | None = None
    stop_reason: str | None = None       # why sentry stopped early (until the key goes on)
    key_was_on: bool = False
    tried_start_at: float | None = None

    def wants_hold(self, st: dict, cfg: dict, now: float) -> bool:
        """Heartbeat "sentry": would we want to stay on if the key went off now?
        Sent all the time while it's true, so the Pico already knows at the moment of key-off."""
        if not cfg["enabled"] or st.get("lock.state") != "locked" or self.stop_reason:
            return False
        v = st.get("an.aux_12v")
        if v is not None and float(v) < float(cfg["min12v"]):
            return False
        if self.sentry_since is not None and now - self.sentry_since >= float(cfg["maxHours"]) * 3600:
            return False
        return not st.get("pico.sentry_flat")

    def step(self, st: dict, cfg: dict, now: float) -> list[str]:
        """Update the mode. Returns events that just happened."""
        events = []
        ign = bool(st.get("in.ignition"))
        locked = st.get("lock.state") == "locked"
        if ign:
            self.stop_reason = None
            self.sentry_since = None
            if locked and not self.key_was_on:
                events.append("attempted_start")
                self.tried_start_at = now
            self.mode = "dashcam" if (cfg["dashcam"] or locked) else "off"
        else:
            if locked and st.get("pico.sentry_hold") and not self.stop_reason:
                if self.sentry_since is None:
                    self.sentry_since = now
                if not self.wants_hold(st, cfg, now):
                    self.stop_reason = ("12V low" if st.get("pico.sentry_flat") or
                                        float(st.get("an.aux_12v") or 99) < float(cfg["min12v"]) else "time up")
                    self.mode = "off"
                else:
                    self.mode = "sentry"
            else:
                self.mode = "off"
        self.key_was_on = ign
        return events


# ---------------------------------------------------------------- motion (no I/O)
@dataclass
class MotionDetector:
    """Tiny grey frames (64 x 36, 2 a second) from each camera. Movement = enough pixels
    changed a lot compared with a slowly updated background, two frames running."""
    pixel_delta: int = 28          # 0-255 change that counts for one pixel
    area_pct: float = 1.5          # % of pixels that must change
    frames_needed: int = 2
    warmup: int = 4                # ignore the first frames while the camera settles
    bg: bytearray | None = None
    seen: int = 0
    run: int = 0

    def feed(self, frame: bytes) -> bool:
        self.seen += 1
        if self.bg is None or len(self.bg) != len(frame):
            self.bg = bytearray(frame)
            self.run = 0
            return False
        changed = sum(1 for a, b in zip(frame, self.bg) if abs(a - b) > self.pixel_delta)
        # Background follows slow changes (clouds, dusk) but not a person walking past.
        for i, v in enumerate(frame):
            self.bg[i] = (self.bg[i] * 7 + v) // 8
        if self.seen <= self.warmup:
            return False
        if changed * 100 >= self.area_pct * len(frame):
            self.run += 1
        else:
            self.run = 0
        if self.run >= self.frames_needed:
            self.run = 0
            return True
        return False


# ---------------------------------------------------------------- clips on disk
def stamp(t: float) -> str:
    return datetime.fromtimestamp(t).strftime("%Y%m%d-%H%M%S")


def unstamp(s: str) -> float:
    return datetime.strptime(s[:15], "%Y%m%d-%H%M%S").timestamp()


@dataclass
class ClipStore:
    """root/loop/<cam>/<start>.mp4 (1 minute pieces), root/events/<start>-<reason>/<cam>-<start>.mp4.

    Saved clips are hard links to the loop pieces, so saving costs no space or time, and
    deleting old loop pieces doesn't touch them."""
    root: Path
    pending: list[tuple[float, str]] = field(default_factory=list)   # (event time, folder)

    @property
    def loop(self) -> Path:
        return self.root / "loop"

    @property
    def events(self) -> Path:
        return self.root / "events"

    def segments(self, cam: str) -> list[tuple[float, Path]]:
        d = self.loop / cam
        out = []
        for p in d.glob("*.mp4") if d.is_dir() else []:
            if NAME_RE.match(p.stem):
                out.append((unstamp(p.stem), p))
        return sorted(out)

    def new_event(self, reason: str, t: float, snapshot: bytes | None = None) -> str:
        name = f"{stamp(t)}-{reason}"
        d = self.events / name
        d.mkdir(parents=True, exist_ok=True)
        if snapshot:
            (d / "cabin.jpg").write_bytes(snapshot)
        (d / "info.json").write_text(json.dumps({"reason": reason, "t": t}))
        self.pending.append((t, name))
        self._link(t, name)
        return name

    def _link(self, t: float, name: str) -> None:
        d = self.events / name
        lo, hi = t - PRE_S, t + POST_S
        for cam in CAMS:
            for start, p in self.segments(cam):
                if start <= hi and start + SEGMENT_S >= lo:
                    dst = d / f"{cam}-{p.name}"
                    if not dst.exists():
                        try:
                            os.link(p, dst)
                        except OSError:
                            shutil.copy2(p, dst)

    def finish(self, now: float) -> None:
        """Pick up the pieces recorded after the event. Call every few seconds."""
        keep = []
        for t, name in self.pending:
            # A piece is complete once the next one has started.
            self._link(t, name)
            if now < t + POST_S + SEGMENT_S + 5:
                keep.append((t, name))
        self.pending = keep

    def list_events(self) -> list[dict]:
        out = []
        for d in sorted(self.events.glob("*"), reverse=True) if self.events.is_dir() else []:
            if not d.is_dir() or not EVENT_RE.match(d.name):
                continue
            files = sorted(p.name for p in d.iterdir() if p.suffix in (".mp4", ".jpg"))
            out.append({"id": d.name, "t": unstamp(d.name), "reason": d.name[16:],
                        "kept": (d / "keep").exists(), "files": files,
                        "mb": round(sum(p.stat().st_size for p in d.iterdir()) / 1e6, 1)})
        return out

    def event_file(self, event: str, name: str) -> Path | None:
        if not EVENT_RE.match(event) or not re.fullmatch(r"[a-z]+-\d{8}-\d{6}\.mp4|cabin\.jpg", name):
            return None
        p = self.events / event / name
        return p if p.is_file() else None

    def delete_event(self, event: str) -> bool:
        if not EVENT_RE.match(event) or not (self.events / event).is_dir():
            return False
        shutil.rmtree(self.events / event)
        return True

    def prune(self, total_bytes: int, events_pct: float) -> None:
        """Oldest loop pieces go first. Saved clips go oldest-first only when they're over
        their share, and never ones marked keep."""
        def size(p: Path) -> int:
            try:
                return p.stat().st_size
            except OSError:
                return 0
        ev_budget = total_bytes * events_pct / 100
        loop_budget = total_bytes - ev_budget
        segs = sorted((s, p) for cam in CAMS for s, p in self.segments(cam))
        used = sum(size(p) for _s, p in segs)
        for _s, p in segs[:-len(CAMS)]:          # never the pieces being written now
            if used <= loop_budget:
                break
            used -= size(p)
            p.unlink(missing_ok=True)
        evs = [e for e in reversed(self.list_events()) if not e["kept"]]
        ev_used = sum(int(e["mb"] * 1e6) for e in self.list_events())
        for e in evs:
            if ev_used <= ev_budget:
                break
            ev_used -= int(e["mb"] * 1e6)
            self.delete_event(e["id"])


# ---------------------------------------------------------------- recording processes
def record_command(cam: str, device: str, out_dir: Path, cfg: dict, h264_camera: bool = False) -> list[str]:
    """One process per camera: 1 minute MP4 pieces, plus tiny grey frames on stdout for motion.

    The Pi 5 has no H.264 encoder chip, so this is software x264 at its fastest setting
    ("ultrafast", like rpicam-vid's low-latency mode). A camera that sends H.264 itself
    (h264_camera) is just copied, which costs next to nothing."""
    w, h, fps, kbps = int(cfg["width"]), int(cfg["height"]), int(cfg["fps"]), int(cfg["kbps"])
    seg = ["-f", "segment", "-segment_time", str(SEGMENT_S), "-segment_format", "mp4",
           "-reset_timestamps", "1", "-strftime", "1", str(out_dir / "%Y%m%d-%H%M%S.mp4")]
    motion = ["-map", "0:v", "-vf", "fps=2,scale=64:36,format=gray", "-f", "rawvideo", "pipe:1"]
    enc = ["-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-b:v", f"{kbps}k",
           "-maxrate", f"{kbps}k", "-bufsize", f"{kbps * 2}k", "-g", str(fps * 2), "-pix_fmt", "yuv420p"]
    adv = videoboard.parse(device)
    if adv is not None:
        # Analogue camera on the video board: pick its input, raw PAL in, x264 out.
        src = " ".join(videoboard.ffmpeg_source())
        return ["sh", "-c", videoboard.shell_prefix(adv) + f"exec ffmpeg -loglevel error {src} -map 0:v "
                f"-vf {videoboard.DEINTERLACE} " + " ".join(enc) + " " + " ".join(seg) + " " + " ".join(motion)]
    if re.fullmatch(r"csi[01]", device):
        # Ribbon camera: rpicam-vid encodes (in software on the Pi 5), ffmpeg only cuts it up.
        return ["sh", "-c",
                f"rpicam-vid -n -t 0 --camera {device[-1]} --width {w} --height {h} --framerate {fps} "
                f"--codec h264 --inline --low-latency -b {kbps * 1000} -o - | "
                "ffmpeg -loglevel error -f h264 -i - -map 0:v -c:v copy " + " ".join(seg) + " " + " ".join(motion)]
    if h264_camera:
        src = ["-f", "v4l2", "-input_format", "h264", "-video_size", f"{w}x{h}", "-framerate", str(fps), "-i", device]
        return ["ffmpeg", "-loglevel", "error", *src, "-map", "0:v", "-c:v", "copy", *seg, *motion]
    src = ["-f", "v4l2", "-input_format", "mjpeg", "-video_size", f"{w}x{h}", "-framerate", str(fps), "-i", device]
    return ["ffmpeg", "-loglevel", "error", *src, "-map", "0:v", *enc, *seg, *motion]


class Recorder:
    """Starts and stops the per-camera processes. Feeds motion frames to the detectors."""

    def __init__(self, on_motion: Callable[[str], None]):
        self.procs: dict[str, asyncio.subprocess.Process] = {}
        self.readers: dict[str, asyncio.Task] = {}
        self.on_motion = on_motion
        self.detectors: dict[str, MotionDetector] = {}
        self.watch_motion = False
        self.retry_at: dict[str, float] = {}   # a camera that dropped out waits before trying again

    @staticmethod
    def available() -> bool:
        return bool(shutil.which("ffmpeg"))

    async def ensure(self, wanted: dict[str, list[str]]) -> list[str]:
        """Start what's wanted, stop the rest. Returns the cameras actually recording."""
        now = time.monotonic()
        for cam in list(self.procs):
            dead = self.procs[cam].returncode is not None
            if cam not in wanted or dead:
                await self.stop(cam)
                if dead:
                    self.retry_at[cam] = now + 15
        for cam, cmd in wanted.items():
            if cam not in self.procs and now >= self.retry_at.get(cam, 0):
                self.detectors[cam] = MotionDetector()
                proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE,
                                                            stderr=asyncio.subprocess.DEVNULL)
                self.procs[cam] = proc
                if videoboard.uses_board(cmd):
                    videoboard.BOARD.recorder = proc   # so a live view can take the board over
                self.readers[cam] = asyncio.ensure_future(self._read(cam, proc))
        return sorted(self.procs)

    async def _read(self, cam: str, proc) -> None:
        size = 64 * 36
        try:
            while True:
                frame = await proc.stdout.readexactly(size)
                if self.watch_motion and self.detectors[cam].feed(frame):
                    self.on_motion(cam)
        except (asyncio.IncompleteReadError, asyncio.CancelledError):
            pass

    async def stop(self, cam: str) -> None:
        proc = self.procs.pop(cam, None)
        task = self.readers.pop(cam, None)
        if task:
            task.cancel()
        if proc and proc.returncode is None:
            proc.terminate()   # ffmpeg closes the current piece cleanly on SIGTERM
            try:
                await asyncio.wait_for(proc.wait(), 5)
            except asyncio.TimeoutError:
                proc.kill()

    async def stop_all(self) -> None:
        for cam in list(self.procs):
            await self.stop(cam)


async def cabin_snapshot(device: str) -> bytes | None:
    """One JPEG from the cabin camera (the face shot for an attempted start)."""
    if not device:
        return None
    if re.fullmatch(r"csi[01]", device):
        cmd = ["rpicam-still", "-n", "--camera", device[-1], "-t", "500", "--width", "1280", "--height", "960",
               "-e", "jpg", "-o", "-"]
    elif (adv := videoboard.parse(device)) is not None:
        cmd = ["sh", "-c", videoboard.shell_prefix(adv) + "exec ffmpeg -loglevel error "
               + " ".join(videoboard.ffmpeg_source()) + " -vf yadif -frames:v 1 -f mjpeg pipe:1"]
    else:
        cmd = ["ffmpeg", "-loglevel", "error", "-f", "v4l2", "-i", device, "-frames:v", "1", "-f", "mjpeg", "pipe:1"]
    if not shutil.which(cmd[0]):
        return None
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(proc.communicate(), 10)
        return out or None
    except Exception:
        return None


# ---------------------------------------------------------------- service and routes
@dataclass
class SentryService:
    gateway: Any
    snapshot: Callable[[], dict]
    dash_settings: Callable[[], dict]
    clock: Callable[[], float] = time.time
    plan: SentryPlan = field(default_factory=SentryPlan)
    recorder: Recorder | None = None
    motion_hits: list[tuple[float, str]] = field(default_factory=list)
    last_motion_event: float = -1e9
    status_text: str = ""

    def cfg(self) -> dict:
        return settings_from(self.dash_settings())

    def store(self) -> ClipStore | None:
        # TERYX_VIDEO_DIR: somewhere else for the simulator and tests.
        env = os.environ.get("TERYX_VIDEO_DIR")
        root = Path(env or self.cfg()["storage"])
        if env:
            root.mkdir(parents=True, exist_ok=True)
        if not root.is_dir() or not os.access(root, os.W_OK):
            return None
        if not env and root == Path(DEFAULTS["storage"]) and not os.path.ismount(root):
            return None   # the SSD isn't plugged in: don't fill the SD card underneath
        if not hasattr(self, "_store") or self._store.root != root:
            self._store = ClipStore(root)
        return self._store

    def motion(self, cam: str) -> None:
        self.motion_hits.append((self.clock(), cam))

    def _device(self, cam: str) -> tuple[str, bool]:
        c = ((self.dash_settings().get("camera") or {}).get("cams") or {}).get(cam) or {}
        dev = c.get("v4l2Device") or ("adv:0" if cam == "rear" else "")
        return dev, bool(c.get("h264"))

    async def tick(self) -> dict:
        st, cfg, now = self.snapshot() or {}, self.cfg(), self.clock()
        events = self.plan.step(st, cfg, now)
        set_sentry = getattr(self.gateway, "set_sentry", None)
        if set_sentry:
            set_sentry(self.plan.wants_hold(st, cfg, now))
        store = self.store()
        recording = []
        if self.plan.mode in ("dashcam", "sentry") and store and self.recorder and self.recorder.available():
            wanted = {}
            board_used = False   # the video board has one decoder: one of its cameras at a time
            for cam in sorted(fitted_cams(self.dash_settings()), key=BOARD_ORDER.index):
                dev, h264 = self._device(cam)
                if dev.startswith("adv:"):
                    # Someone watching a video board camera on the screen has the board.
                    if board_used or videoboard.BOARD.watching() or not Path(videoboard.node()).exists():
                        continue
                    board_used = True
                    out = store.loop / cam
                    out.mkdir(parents=True, exist_ok=True)
                    wanted[cam] = record_command(cam, dev, out, cfg, h264)
                elif dev and ((dev.startswith("csi") and shutil.which("rpicam-vid")) or Path(dev).exists()):
                    out = store.loop / cam
                    out.mkdir(parents=True, exist_ok=True)
                    wanted[cam] = record_command(cam, dev, out, cfg, h264)
            recording = await self.recorder.ensure(wanted)
            self.recorder.watch_motion = self.plan.mode == "sentry"
        elif self.recorder:
            await self.recorder.stop_all()
        # events
        if self.plan.mode == "sentry":
            for t, _cam in self.motion_hits:
                if t - self.last_motion_event > POST_S:     # one clip per burst of movement
                    events.append("motion")
                    self.last_motion_event = t
        self.motion_hits.clear()
        for ev in events:
            snap = await cabin_snapshot(self._device("cabin")[0]) if ev == "attempted_start" else None
            if store:
                store.new_event(ev, now, snap)
        if store:
            store.finish(now)
            try:
                total = shutil.disk_usage(store.root).total
                store.prune(int(total * 0.9), float(cfg["eventsPct"]))
            except OSError:
                pass
        why = ("" if store else "No video drive. Plug in the SSD (docs/sentry.md)."
               if self.plan.mode != "off" else "")
        self.status_text = why
        return {"mode": self.plan.mode, "recording": recording, "stop_reason": self.plan.stop_reason,
                "hold": self.plan.wants_hold(st, cfg, now), "problem": why}

    def save_now(self) -> str | None:
        store = self.store()
        return store.new_event("manual", self.clock()) if store else None


SENTRY_KEY = web.AppKey("teryx_dash_sentry", SentryService)
SENTRY_TASK_KEY = web.AppKey("teryx_dash_sentry_task", asyncio.Future)


def setup_sentry_routes(app: web.Application, gateway: Any, settings_file: Callable[[], Path],
                        snapshot: Callable[[], dict], tick_s: float = 1.0) -> SentryService:
    def dash_settings() -> dict:
        try:
            return json.loads(settings_file().read_text())
        except Exception:
            return {}

    svc = SentryService(gateway, snapshot, dash_settings)
    svc.recorder = Recorder(svc.motion)
    app[SENTRY_KEY] = svc
    last = {"status": {"mode": "off", "recording": [], "stop_reason": None, "hold": False, "problem": ""}}

    async def status(_):
        store = svc.store()
        disk = None
        if store:
            u = shutil.disk_usage(store.root)
            disk = {"total_gb": round(u.total / 1e9, 1), "free_gb": round(u.free / 1e9, 1)}
        return web.json_response({**last["status"], "settings": svc.cfg(), "disk": disk,
                                  "simulated": bool(os.environ.get("TERYX_VIDEO_DIR")),
                                  "events": store.list_events()[:200] if store else []})

    async def clip_file(req):
        store = svc.store()
        p = store.event_file(req.match_info["event"], req.match_info["name"]) if store else None
        if not p:
            return web.json_response({"error": "no such clip"}, status=404)
        return web.FileResponse(p)

    async def clip_delete(req):
        store = svc.store()
        ok = bool(store) and store.delete_event(req.match_info["event"])
        return web.json_response({"ok": ok}, status=200 if ok else 404)

    async def clip_keep(req):
        store = svc.store()
        ev = req.match_info["event"]
        if not store or not EVENT_RE.match(ev) or not (store.events / ev).is_dir():
            return web.json_response({"error": "no such clip"}, status=404)
        (store.events / ev / "keep").touch()
        return web.json_response({"ok": True})

    async def save(_):
        name = svc.save_now()
        if not name:
            return web.json_response({"error": "no video drive"}, status=409)
        return web.json_response({"ok": True, "id": name})

    async def sim_motion(req):
        """Simulator: pretend a camera saw movement."""
        cam = (await req.json()).get("cam", "front")
        svc.motion(str(cam))
        return web.json_response({"ok": True})

    async def loop():
        while True:
            try:
                last["status"] = await svc.tick()
            except asyncio.CancelledError:
                raise
            except Exception as e:   # keep going: a camera unplugged mustn't stop the rest
                last["status"] = {**last["status"], "problem": f"sentry error: {e}"}
            await asyncio.sleep(tick_s)

    async def on_start(_app):
        _app[SENTRY_TASK_KEY] = asyncio.ensure_future(loop())

    async def on_stop(_app):
        _app[SENTRY_TASK_KEY].cancel()
        if svc.recorder:
            await svc.recorder.stop_all()

    r = app.router
    r.add_get("/api/sentry", status)
    r.add_post("/api/sentry/save", save)
    r.add_post("/api/sentry/sim-motion", sim_motion)
    r.add_get("/api/clips/{event}/{name}", clip_file)
    r.add_delete("/api/clips/{event}", clip_delete)
    r.add_post("/api/clips/{event}/keep", clip_keep)
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)
    return svc
