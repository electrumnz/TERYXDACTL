#!/usr/bin/env python3
"""Turn the raw Higgsfield T. rex clips into small dash clips that join up with no jump.

    python3 tools/rex_clips.py RAW_DIR [--keyframes DIR] [--out dash/web/video/rex]

RAW_DIR holds the downloaded clips named <id>.mp4 plus clips.json (the same list the dash reads,
see dash/web/video/rex/README.md). For each clip this:
  1. eases the first and last quarter second onto the exact hub picture (closed, roar or run),
     so whatever the video model did at the ends, every clip starts and ends on the same frame
  2. scales to 960x540 (the dash shows it 911x512) and drops the sound
  3. encodes H.264, no B-frames, a keyframe every second, fast start, about 1 MB per 5 s
  4. checks the first and last frames against the hub pictures and prints how close they are

Needs ffmpeg and Pillow. The Pi 5 has no H.264 hardware decoder, but 960x540 at 24 fps is light
work for its CPU in Chromium; 1080p would not be.
"""
import argparse, json, shutil, subprocess, sys, tempfile
from pathlib import Path

W, H, FPS, EASE = 960, 540, 24, 0.25
HUBS = {"closed": "head-closed-169.png", "roar": "head-roar-169.png", "run": "hub-run.png"}


def dur(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def encode(src, hub_in, hub_out, dst, trim=None):
    d = dur(src)
    start, end = (trim or [0, d])
    end = min(end, d)
    length = end - start
    fc = (
        f"[0:v]trim={start}:{end},setpts=PTS-STARTPTS,fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},format=rgba[v];"
        f"[1:v]scale={W}:{H},format=rgba,fade=out:st={1 / FPS:.3f}:d={EASE}:alpha=1[a];"
        f"[2:v]scale={W}:{H},format=rgba,fade=in:st={length - EASE - 2 / FPS:.3f}:d={EASE}:alpha=1[b];"
        f"[v][a]overlay=shortest=1[va];[va][b]overlay=shortest=1,format=yuv420p[o]"
    )
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-i", str(src),
        "-loop", "1", "-t", f"{length:.3f}", "-framerate", str(FPS), "-i", str(hub_in),
        "-loop", "1", "-t", f"{length:.3f}", "-framerate", str(FPS), "-i", str(hub_out),
        "-filter_complex", fc, "-map", "[o]", "-an",
        "-c:v", "libx264", "-profile:v", "main", "-preset", "slow", "-crf", "27", "-bf", "0",
        "-g", str(FPS), "-movflags", "+faststart", str(dst),
    ], check=True)


def frame(p, at, out):
    args = ["ffmpeg", "-v", "error", "-y"]
    args += (["-sseof", "-0.05"] if at == "last" else []) + ["-i", str(p), "-frames:v", "1", str(out)]
    subprocess.run(args, check=True)


def diff(a, b):
    from PIL import Image, ImageChops, ImageStat
    ia = Image.open(a).convert("RGB").resize((240, 135))
    ib = Image.open(b).convert("RGB").resize((240, 135))
    return sum(ImageStat.Stat(ImageChops.difference(ia, ib)).mean) / 3


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw")
    ap.add_argument("--keyframes", default=None, help="folder with the hub pictures (default RAW/keyframes)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "dash/web/video/rex"))
    a = ap.parse_args()
    raw, out = Path(a.raw), Path(a.out)
    kf = Path(a.keyframes) if a.keyframes else raw / "keyframes"
    m = json.loads((raw / "clips.json").read_text())
    out.mkdir(parents=True, exist_ok=True)
    bad = 0
    with tempfile.TemporaryDirectory() as t:
        for c in m["clips"]:
            src = raw / c.get("raw", c["id"] + ".mp4")
            dst = out / c["file"]
            encode(src, kf / HUBS[c["from"]], kf / HUBS[c["to"]], dst, c.get("trim"))
            f0, f1 = Path(t) / "f0.png", Path(t) / "f1.png"
            frame(dst, "first", f0); frame(dst, "last", f1)
            d0, d1 = diff(f0, kf / HUBS[c["from"]]), diff(f1, kf / HUBS[c["to"]])
            ok = d0 < 6 and d1 < 6
            bad += not ok
            print(f"{c['id']:<14} {c['kind']:<7} {c['from']:>6} -> {c['to']:<6} {dur(dst):4.1f}s "
                  f"{dst.stat().st_size / 1e6:4.2f} MB  seam diff {d0:4.1f} / {d1:4.1f} {'ok' if ok else 'CHECK'}")
    shutil.copy(raw / "clips.json", out / "clips.json")
    total = sum(f.stat().st_size for f in out.glob("*.mp4")) / 1e6
    print(f"{len(m['clips'])} clips, {total:.1f} MB in {out}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
