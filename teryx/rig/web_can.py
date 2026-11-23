"""A tiny stand-in for python-can, for the phone sim (Pyodide in a web browser).

Only what Teryx OS uses with the in-process ``virtual`` bus: Message, BusABC,
CanError and Bus(interface="virtual", channel=...). Like python-can's virtual
bus, a frame goes to every other bus on the same channel, not back to the sender.
The worker puts this in ``sys.modules["can"]`` before anything imports ``can``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


class CanError(Exception):
    pass


@dataclass
class Message:
    arbitration_id: int = 0
    data: bytes | bytearray = field(default_factory=bytes)
    is_extended_id: bool = False
    is_error_frame: bool = False
    is_remote_frame: bool = False
    timestamp: float = 0.0
    channel: str | None = None
    dlc: int | None = None

    def __post_init__(self):
        self.data = bytearray(self.data or b"")
        if self.dlc is None:
            self.dlc = len(self.data)


_CHANNELS: dict[str, list["VirtualBus"]] = {}


class BusABC:
    def send(self, msg: Message, timeout=None) -> None:
        raise NotImplementedError

    def recv(self, timeout=None):
        raise NotImplementedError

    def shutdown(self) -> None:
        pass


class VirtualBus(BusABC):
    def __init__(self, channel: str = "teryx"):
        self.channel = channel
        self.queue: deque[Message] = deque(maxlen=10_000)
        _CHANNELS.setdefault(channel, []).append(self)

    def send(self, msg: Message, timeout=None) -> None:
        for bus in _CHANNELS.get(self.channel, ()):
            if bus is not self:
                bus.queue.append(Message(msg.arbitration_id, bytes(msg.data), msg.is_extended_id,
                                         msg.is_error_frame, msg.is_remote_frame, msg.timestamp, self.channel))

    def recv(self, timeout=None):
        return self.queue.popleft() if self.queue else None

    def shutdown(self) -> None:
        buses = _CHANNELS.get(self.channel, [])
        if self in buses:
            buses.remove(self)


def Bus(interface: str = "virtual", channel: str = "teryx", **_kw) -> BusABC:  # noqa: N802
    if interface != "virtual":
        raise CanError(f"only the virtual bus works in the browser, not '{interface}'")
    return VirtualBus(channel)


class interface:  # noqa: N801 - mirrors python-can's can.interface module
    Bus = staticmethod(Bus)
