"""Helpers shared by every node on the bus (dash, sim, control box)."""

from __future__ import annotations

import time

import can

from .codec import Message
from .registry import BY_ID


class Node:
    """Wraps a python-can bus with encode/decode and periodic send timers."""

    def __init__(self, bus: can.BusABC):
        self.bus = bus
        self._counters: dict[int, int] = {}
        self._last_sent: dict[int, float] = {}
        self.enabled = True     # set False to fake a dead node (comms loss)

    def send(self, msg: Message, values: dict) -> None:
        if not self.enabled:
            return
        c = (self._counters.get(msg.can_id, -1) + 1) & 0xFF
        self._counters[msg.can_id] = c
        data = msg.encode({**values, "counter": c})
        try:
            self.bus.send(can.Message(arbitration_id=msg.can_id, data=data,
                                      is_extended_id=msg.extended))
        except can.CanError:
            pass  # bus full or down; the next period will try again

    def send_due(self, msg: Message, values_fn, now: float | None = None) -> bool:
        """Send ``msg`` if its period has passed. ``values_fn`` is only called when due."""
        now = time.monotonic() if now is None else now
        last = self._last_sent.get(msg.can_id, 0.0)
        if now - last >= msg.period_ms / 1000:
            self._last_sent[msg.can_id] = now
            self.send(msg, values_fn())
            return True
        return False

    def poll(self, timeout: float = 0.0):
        """Yield (Message, decoded values, raw can.Message) for every known frame waiting."""
        while True:
            raw = self.bus.recv(timeout)
            if raw is None:
                return
            timeout = 0.0
            msg = BY_ID.get(raw.arbitration_id)
            if msg is None or raw.is_error_frame:
                yield None, None, raw
                continue
            yield msg, msg.decode(raw.data), raw

    def close(self):
        self.bus.shutdown()
