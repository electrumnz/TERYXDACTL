"""Camera as an MJPEG stream, for when the browser can't open the camera itself.

Works for a USB camera or an RCA/AHD camera on a USB capture dongle (both are /dev/videoN).
Uses ffmpeg, which is on Raspberry Pi OS. One ffmpeg per viewer; the dash only has one viewer.
"""

from __future__ import annotations

import asyncio
import shutil

from aiohttp import web

BOUNDARY = "teryxframe"


async def mjpeg_response(req: web.Request, device: str) -> web.StreamResponse:
    if not shutil.which("ffmpeg"):
        return web.json_response({"error": "ffmpeg not installed"}, status=503)
    if not device.startswith("/dev/video"):
        return web.json_response({"error": "bad camera device"}, status=400)
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-loglevel", "error", "-f", "v4l2", "-input_format", "mjpeg", "-video_size", "1280x720",
        "-i", device, "-f", "mjpeg", "-q:v", "5", "-r", "25", "pipe:1",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    resp = web.StreamResponse(headers={"Content-Type": f"multipart/x-mixed-replace; boundary={BOUNDARY}",
                                       "Cache-Control": "no-store"})
    await resp.prepare(req)
    buf = b""
    try:
        while True:
            chunk = await proc.stdout.read(65536)
            if not chunk:
                break
            buf += chunk
            while True:
                start = buf.find(b"\xff\xd8")
                end = buf.find(b"\xff\xd9", start + 2)
                if start < 0 or end < 0:
                    break
                frame, buf = buf[start:end + 2], buf[end + 2:]
                await resp.write(f"--{BOUNDARY}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(frame)}\r\n\r\n".encode() + frame + b"\r\n")
            if len(buf) > 4_000_000:
                buf = b""
    except (ConnectionResetError, asyncio.CancelledError):
        pass
    finally:
        if proc.returncode is None:
            proc.kill()
    return resp
