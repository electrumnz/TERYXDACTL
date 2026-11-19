"""Is the trailer camera plugged in? Checked from its picture, so it needs no extra wire.

Two plugs go to the trailer: the flat 7-pin for the lights (its reed switch gives in.trailer)
and the round EU 7-pin for the camera and light bar. A trailer can be on with the lights
plugged in but no camera (or a trailer with no camera at all), so the dash also asks the video
board whether there's a picture on the trailer input (videoboard.probe).

The board can only look at one input at a time, so the check only runs while nobody is using
it. It runs straight away when the trailer plug goes in or out, then every PERIOD_S. If the
board is busy (dashcam recording, or someone watching the rear camera) it tries again
shortly and, until then, says "not known" and the dash goes by the trailer plug alone.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from . import videoboard

PERIOD_S = 10
RETRY_S = 2


class TrailerWatch:
    def __init__(self, device: Callable[[], str], plugged: Callable[[], bool],
                 probe: Callable[[int], Awaitable[bool | None]] = videoboard.probe,
                 clock: Callable[[], float] = time.time):
        self.device, self.plugged, self.probe, self.clock = device, plugged, probe, clock
        self.plug: bool | None = None
        self.signal: bool | None = None
        self.checked: float | None = None
        self.next = 0.0

    async def step(self) -> dict:
        now, plug = self.clock(), bool(self.plugged())
        if plug != self.plug:
            # Plugged in or out: what we knew about the picture is out of date. Look now.
            self.plug, self.signal, self.checked, self.next = plug, None, None, 0.0
        inp = videoboard.parse(self.device())
        if inp is None:
            self.signal = None
        elif now >= self.next:
            ok = await self.probe(inp)
            if ok is None:
                self.next = now + RETRY_S
            else:
                self.signal, self.checked, self.next = ok, now, now + PERIOD_S
                videoboard.BOARD.note(inp, ok, now)
        return self.status()

    def status(self) -> dict:
        return {"plug": bool(self.plug), "signal": self.signal, "checked": self.checked}
