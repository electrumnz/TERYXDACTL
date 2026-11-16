"""Plain UDP multicast CAN bus, shared with the Pico firmware's host build.

Lets the simulator, the dash and the host-built firmware share one "bus" on a
laptop with no kernel modules or extra packages (works on Windows, Mac, Linux).

Wire format, one CAN frame per datagram, 16 bytes:
    u32 id (little-endian) | u8 dlc | u8 flags (bit0 extended) | 2 pad | 8 data
Default group 239.0.7.0 port 47000, on loopback.
"""

from __future__ import annotations

import select
import socket
import struct
import time

import can

FMT = struct.Struct("<IBB2x8s")
DEFAULT_GROUP = "239.0.7.0"
DEFAULT_PORT = 47000


class UdpCanBus(can.BusABC):
    def __init__(self, channel: str | None = None, port: int = DEFAULT_PORT,
                 receive_own_messages: bool = False, **kwargs):
        group = channel or DEFAULT_GROUP
        self.channel_info = f"udp {group}:{port}"
        self.group, self.port = group, int(port)
        self.receive_own_messages = receive_own_messages

        rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass
        try:
            rx.bind((group, self.port))     # Linux / Mac: only get this group
        except OSError:
            rx.bind(("", self.port))        # Windows
        mreq = struct.pack("4s4s", socket.inet_aton(group), socket.inet_aton("127.0.0.1"))
        rx.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        rx.setblocking(False)

        tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        tx.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 0)
        tx.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        tx.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton("127.0.0.1"))
        # Learn our own source address so we can drop our own frames
        self._rx, self._tx = rx, tx
        self._own: set = set()
        tx.bind(("127.0.0.1", 0))
        self._own.add(tx.getsockname())
        super().__init__(channel=group, **kwargs)

    def send(self, msg: can.Message, timeout: float | None = None) -> None:
        flags = 1 if msg.is_extended_id else 0
        data = bytes(msg.data).ljust(8, b"\0")[:8]
        self._tx.sendto(FMT.pack(msg.arbitration_id, msg.dlc, flags, data), (self.group, self.port))

    def _recv_internal(self, timeout: float | None):
        end = None if timeout is None else time.monotonic() + timeout
        while True:
            wait = None if end is None else max(0.0, end - time.monotonic())
            ready, _, _ = select.select([self._rx], [], [], wait)
            if not ready:
                return None, False
            try:
                pkt, addr = self._rx.recvfrom(64)
            except BlockingIOError:
                continue
            if len(pkt) != FMT.size:
                continue
            if addr in self._own and not self.receive_own_messages:
                if end is not None and time.monotonic() >= end:
                    return None, False
                continue
            can_id, dlc, flags, data = FMT.unpack(pkt)
            msg = can.Message(timestamp=time.time(), arbitration_id=can_id,
                              is_extended_id=bool(flags & 1), dlc=dlc, data=data[:dlc],
                              channel=self.channel_info)
            return msg, False

    def shutdown(self) -> None:
        super().shutdown()
        self._rx.close()
        self._tx.close()
