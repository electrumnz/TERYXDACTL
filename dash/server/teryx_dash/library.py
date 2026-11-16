"""Local music: songs in ~/Music on the Pi and on any USB stick plugged in.

Raspberry Pi OS mounts USB sticks under /media/<user>/<stick name>, so those are scanned too.
Set TERYX_MUSIC_DIRS (folders split by ':') to look somewhere else.

Song names come from the MP3's own tags (ID3v2) when it has them, otherwise from the file name
("Artist - Title.mp3"), with the folder as the album. No extra packages needed.

The simulator adds a few made-up demo tunes, generated here as sound waves, so music and
ducking can be tried on a laptop with nothing copied from anywhere.
"""

from __future__ import annotations

import getpass
import hashlib
import io
import math
import os
import struct
import time
import wave
from functools import lru_cache
from pathlib import Path

EXTS = {".mp3", ".m4a", ".aac", ".flac", ".ogg", ".oga", ".opus", ".wav"}
MAX_TRACKS = 5000
MAX_DEPTH = 6
RESCAN_S = 30

DEMO = [
    # id, title, root note (Hz), beats per minute, seconds
    ("demo-1", "Gravel Road", 220.0, 112, 26),
    ("demo-2", "Ridge Line", 261.63, 96, 26),
    ("demo-3", "River Crossing", 196.0, 128, 26),
]


def music_roots() -> list[Path]:
    env = os.environ.get("TERYX_MUSIC_DIRS")
    if env:
        return [Path(p).expanduser() for p in env.split(os.pathsep) if p]
    roots = [Path.home() / "Music"]
    try:
        user = getpass.getuser()
    except Exception:
        user = ""
    for media in (Path("/media") / user, Path("/media")):
        try:
            roots += sorted(p for p in media.iterdir() if p.is_dir() and p.name != user)
        except OSError:
            pass
    return roots


def _synchsafe(b: bytes) -> int:
    return (b[0] << 21) | (b[1] << 14) | (b[2] << 7) | b[3]


def _text(frame: bytes) -> str:
    if not frame:
        return ""
    enc, body = frame[0], frame[1:]
    try:
        if enc == 0:
            s = body.decode("latin-1")
        elif enc == 1:
            s = body.decode("utf-16")
        elif enc == 2:
            s = body.decode("utf-16-be")
        else:
            s = body.decode("utf-8")
    except UnicodeDecodeError:
        s = body.decode("latin-1", errors="replace")
    return s.split("\x00")[0].strip()


def read_id3(path: Path) -> dict:
    """Title, artist and album from an ID3v2.3/2.4 tag at the start of an MP3. {} if there isn't one."""
    try:
        with open(path, "rb") as f:
            head = f.read(10)
            if len(head) < 10 or head[:3] != b"ID3" or head[3] not in (3, 4):
                return {}
            ver, flags, size = head[3], head[5], _synchsafe(head[6:10])
            data = f.read(min(size, 512 * 1024))
    except OSError:
        return {}
    pos = 0
    if flags & 0x40 and len(data) >= 4:  # extended header
        ext = _synchsafe(data[:4]) if ver == 4 else struct.unpack(">I", data[:4])[0] + 4
        pos = ext
    want = {b"TIT2": "title", b"TPE1": "artist", b"TALB": "album"}
    out: dict = {}
    while pos + 10 <= len(data):
        fid = data[pos:pos + 4]
        if fid == b"\x00\x00\x00\x00" or not fid.isalnum():
            break
        fsize = _synchsafe(data[pos + 4:pos + 8]) if ver == 4 else struct.unpack(">I", data[pos + 4:pos + 8])[0]
        body = data[pos + 10:pos + 10 + fsize]
        if fid in want:
            t = _text(body)
            if t:
                out[want[fid]] = t
        pos += 10 + fsize
    return out


def describe(path: Path, root: Path) -> dict:
    tags = read_id3(path) if path.suffix.lower() == ".mp3" else {}
    stem = path.stem
    artist, title = "", stem
    if " - " in stem:
        artist, title = (x.strip() for x in stem.split(" - ", 1))
        # "01 - Title" is a track number, not an artist
        if artist.isdigit():
            artist = ""
    album = path.parent.name if path.parent != root else root.name
    return {"title": tags.get("title") or title, "artist": tags.get("artist") or artist,
            "album": tags.get("album") or album}


class Library:
    def __init__(self, demo: bool = False) -> None:
        self.demo = demo
        self.paths: dict[str, Path] = {}
        self.tracks: list[dict] = []
        self.roots: list[Path] = []
        self.scanned = 0.0

    def scan(self, force: bool = False) -> list[dict]:
        if not force and time.time() - self.scanned < RESCAN_S:
            return self.tracks
        paths: dict[str, Path] = {}
        tracks: list[dict] = []
        self.roots = [r for r in music_roots() if r.is_dir()]
        for root in self.roots:
            usb = str(root).startswith("/media/")
            for dirpath, dirnames, files in os.walk(root):
                depth = len(Path(dirpath).relative_to(root).parts)
                dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and depth < MAX_DEPTH)
                for fn in sorted(files):
                    p = Path(dirpath) / fn
                    if p.suffix.lower() not in EXTS or fn.startswith("."):
                        continue
                    tid = hashlib.sha1(str(p).encode()).hexdigest()[:16]
                    paths[tid] = p
                    tracks.append({"id": tid, **describe(p, root), "source": "usb" if usb else "pi",
                                   "url": f"/api/media/file/{tid}"})
                    if len(tracks) >= MAX_TRACKS:
                        break
        if self.demo:
            for tid, title, *_ in DEMO:
                tracks.append({"id": tid, "title": title, "artist": "Teryx test tones", "album": "Made by the sim",
                               "source": "demo", "url": f"/api/media/file/{tid}"})
        self.paths, self.tracks, self.scanned = paths, tracks, time.time()
        return tracks

    def path(self, tid: str) -> Path | None:
        if tid not in self.paths:
            self.scan(force=True)
        p = self.paths.get(tid)
        # Only ever hand out files that are still under one of the music folders.
        if p and any(_inside(p, r) for r in self.roots) and p.is_file():
            return p
        return None


def _inside(p: Path, root: Path) -> bool:
    try:
        p.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


@lru_cache(maxsize=4)
def demo_wav(tid: str) -> bytes | None:
    """A short made-up tune: a chord pattern with a bass line, as a WAV. Generated, so nothing to licence."""
    spec = next((d for d in DEMO if d[0] == tid), None)
    if not spec:
        return None
    _, _, root, bpm, secs = spec
    rate = 22050
    beat = 60 / bpm
    prog = [0, 5, 7, 3] if tid != "demo-2" else [0, 9, 5, 7]   # semitones from the root
    major = [0, 4, 7, 12]
    n = int(rate * secs)
    buf = bytearray()
    for i in range(n):
        t = i / rate
        b = int(t / beat)
        bar = (b // 4) % len(prog)
        base = root * 2 ** (prog[bar] / 12)
        step = int(t / (beat / 2)) % 4
        note = base * 2 ** (major[step] / 12) * 2
        tb = t % (beat / 2)
        env = math.exp(-tb * 7)
        v = 0.32 * env * math.sin(2 * math.pi * note * t) + 0.08 * env * math.sin(4 * math.pi * note * t)
        v += 0.25 * math.sin(2 * math.pi * base / 2 * t) * (0.6 + 0.4 * math.exp(-(t % beat) * 4))
        if b % 2 == 1 and (t % beat) < 0.03:   # a tick on the off beat
            v += 0.15 * math.sin(2 * math.pi * 3000 * t) * (1 - (t % beat) / 0.03)
        fade = min(1.0, t / 0.5, (secs - t) / 1.5)
        buf += struct.pack("<h", int(max(-1, min(1, v * fade)) * 26000))
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(buf))
    return out.getvalue()
