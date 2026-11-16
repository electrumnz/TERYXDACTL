"""Open a CAN bus. This is the one place that knows about real vs fake CAN.

Bus specs are strings so they fit on the command line:

    virtual              in-process fake bus (default for `teryx run`)
    udp                  UDP multicast 239.0.7.0:47000 on loopback. Lets the sim,
                         dash and Pico host build run as separate programs on any
                         laptop (Windows, Mac, Linux)
    udp:239.0.7.1:47001  same, other group/port
    socketcan:vcan0      Linux virtual CAN
    socketcan:can0       the real bus (CAN HAT on the Pi)

Anything else python-can supports works too, e.g. ``slcan:/dev/ttyACM0@250000``
or ``pcan:PCAN_USBBUS1@250000``.
"""

from __future__ import annotations

import can

from .udpbus import DEFAULT_PORT, UdpCanBus

DEFAULT_BITRATE = 250_000  # IO list: match the Shinegle, likely 250k (TBC)


def open_bus(spec: str = "virtual", listen_only: bool = False) -> can.BusABC:
    """Open a bus from a spec string. ``listen_only`` asks the adaptor never to
    send or ACK (slcan adaptors like the Teryx sniffer do this with the "L"
    command; for socketcan it's set with ``ip link``, see setup_can_pi.sh)."""
    spec = spec.strip()
    iface, _, rest = spec.partition(":")
    if iface == "udp":
        group, _, port = rest.partition(":")
        return UdpCanBus(group or None, int(port or DEFAULT_PORT))
    channel, _, bitrate = rest.partition("@")
    if iface == "virtual":
        return can.Bus(interface="virtual", channel=channel or "teryx")
    if not channel:
        raise ValueError(f"bus spec '{spec}' needs a channel, e.g. socketcan:vcan0")
    kwargs = {"interface": iface, "channel": channel}
    if bitrate:
        kwargs["bitrate"] = int(bitrate)
    elif iface not in ("socketcan",):
        kwargs["bitrate"] = DEFAULT_BITRATE
    if listen_only and iface == "slcan":
        kwargs["listen_only"] = True
    if iface == "slcan":
        kwargs.setdefault("sleep_after_open", 0.5)
    return can.Bus(**kwargs)
