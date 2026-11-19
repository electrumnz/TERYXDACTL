"""The analogue video board on the Pi's second camera ribbon port (ADV7280-M / ADV7282-M).

No USB (Sam). The rear and trailer cameras (and a cabin camera later) run in CVBS/PAL
mode into one board, which shows up as a single V4L2 capture device. It has several
analogue inputs but only one decoder, so only one of them can be shown or recorded
at a time: the input is picked with `v4l2-ctl --set-input=N` before each start.

A camera's device is written "adv:N" (N = the board's input, 0 = rear, 1 = trailer,
2 = cabin). The capture node defaults to /dev/video0 and can be changed with the
TERYX_VIDEO_BOARD environment variable once the board is on the bench (Pi 5 support
for these boards isn't proven yet, see docs/cameras.md).
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import time

PATTERN = re.compile(r"adv:(\d)")


def parse(device: str) -> int | None:
    m = PATTERN.fullmatch(device or "")
    return int(m.group(1)) if m else None


def node() -> str:
    return os.environ.get("TERYX_VIDEO_BOARD", "/dev/video0")


def select_cmd(inp: int) -> list[str]:
    return ["v4l2-ctl", "-d", node(), f"--set-input={inp}"]


def ffmpeg_source() -> list[str]:
    """ffmpeg input args: PAL, interlaced, raw YUV from the board."""
    return ["-f", "v4l2", "-standard", "PAL", "-i", node()]


DEINTERLACE = "yadif"


def uses_board(cmd: list[str]) -> bool:
    """Is this a command made with shell_prefix (so it reads the video board)?"""
    return any("--set-input=" in c and node() in c for c in cmd)


def shell_prefix(inp: int) -> str:
    """For `sh -c` commands: pick the input first."""
    return " ".join(select_cmd(inp)) + " >/dev/null 2>&1; "


# ---------------------------------------------------------------------------------------------
# Who has the board. One decoder, so one ffmpeg at a time: a live view on the screen wins over
# the dashcam (the recorder leaves the board alone while someone is watching one of its cameras),
# and a newer live view replaces an older one (the combined view swaps rear and trailer this way).

class Board:
    def __init__(self) -> None:
        self.viewer: asyncio.subprocess.Process | None = None
        self.recorder: asyncio.subprocess.Process | None = None
        self.lock = asyncio.Lock()
        # Last trailer camera check: True picture, False no picture, None not known.
        self.signal: dict[int, tuple[bool | None, float]] = {}

    @staticmethod
    def _alive(p) -> bool:
        return p is not None and p.returncode is None

    def watching(self) -> bool:
        return self._alive(self.viewer)

    def busy(self) -> bool:
        return self._alive(self.viewer) or self._alive(self.recorder)

    async def _stop(self, p) -> None:
        if self._alive(p):
            p.kill()
            try:
                await asyncio.wait_for(p.wait(), 3)
            except asyncio.TimeoutError:
                pass

    async def take_for_viewer(self) -> None:
        """Before a live view starts: stop the old live view and the dashcam's use of the board."""
        await self._stop(self.viewer)
        await self._stop(self.recorder)
        self.viewer = self.recorder = None

    def note(self, inp: int, ok: bool | None, now: float | None = None) -> None:
        self.signal[inp] = (ok, time.time() if now is None else now)


BOARD = Board()


def subdev() -> str:
    """Where to ask "is there a picture?". On the Pi 5 the decoder may only answer on its
    /dev/v4l-subdevN node (media controller), so it can be set apart from the capture node."""
    return os.environ.get("TERYX_VIDEO_SUBDEV") or node()


def querystd_cmd() -> list[str]:
    return ["v4l2-ctl", "-d", subdev(), "--get-detected-standard"]


def parse_std(out: str) -> bool | None:
    """v4l2-ctl prints "Video Standard = 0x000000ff" when the decoder has locked onto a
    picture, and 0x00000000 (V4L2_STD_UNKNOWN) when nothing is coming in (adv7180 driver)."""
    m = re.search(r"Video Standard = 0x([0-9a-fA-F]+)", out or "")
    return None if not m else int(m.group(1), 16) != 0


async def probe(inp: int) -> bool | None:
    """Is there a picture on input `inp`? Only when nobody is using the board (switching input
    under a live view or the dashcam would glitch it). None = couldn't check."""
    if BOARD.busy() or not shutil.which("v4l2-ctl") or not os.path.exists(node()):
        return None
    async with BOARD.lock:
        if BOARD.busy():
            return None
        try:
            sel = await asyncio.create_subprocess_exec(*select_cmd(inp), stdout=asyncio.subprocess.DEVNULL,
                                                       stderr=asyncio.subprocess.DEVNULL)
            await sel.wait()
            await asyncio.sleep(SETTLE_S)
            q = await asyncio.create_subprocess_exec(*querystd_cmd(), stdout=asyncio.subprocess.PIPE,
                                                     stderr=asyncio.subprocess.DEVNULL)
            out, _ = await asyncio.wait_for(q.communicate(), 3)
        except (OSError, asyncio.TimeoutError):
            return None
        return parse_std(out.decode(errors="replace"))


# Analog Devices AN-1337: up to 250 ms to lock after an input change in fast switch mode,
# over 500 ms with autodetect. The driver's querystd waits 100 ms itself.
SETTLE_S = 0.3
