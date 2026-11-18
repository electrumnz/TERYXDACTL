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

import os
import re

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


def shell_prefix(inp: int) -> str:
    """For `sh -c` commands: pick the input first."""
    return " ".join(select_cmd(inp)) + " >/dev/null 2>&1; "
