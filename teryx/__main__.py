"""Command line for Teryx OS.

    python -m teryx run                 sim + dash in one program (laptop or Pi)
    python -m teryx sim --bus udp       just the fake Shinegle + control box
    python -m teryx dash --bus udp      just the dash (use socketcan:can0 for the real Teryx)
    python -m teryx monitor --bus udp   print decoded CAN frames
    python -m teryx replay FILE         play a candump/.asc/.blf log onto the bus
    python -m teryx canmap              write docs/CAN_PROTOCOL.md and docs/teryx.dbc
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time


def _serve(gateway, sim, args) -> None:
    from aiohttp import web

    from .dash.server import build_app
    app = build_app(gateway, sim, ui_dir=args.ui, plugins=tuple(args.plugin or ()))
    host = args.host
    print(f"\n  Teryx dash:  http://localhost:{args.port}/")
    if sim is not None:
        print(f"  Sim panel:   http://localhost:{args.port}/sim")
    print(f"  CAN bus:     {gateway.bus_spec}\n  Ctrl+C to stop\n")
    web.run_app(app, host=host, port=args.port, print=None, access_log=None)


def cmd_run(args) -> None:
    from .dash.gateway import Gateway
    from .sim.runner import Simulator
    sim = Simulator(args.bus, args.scenario, controlbox=not args.no_controlbox).start()
    gw = Gateway(args.bus).start()
    try:
        _serve(gw, sim, args)
    finally:
        gw.stop()
        sim.stop()


def cmd_dash(args) -> None:
    from .dash.gateway import Gateway
    gw = Gateway(args.bus).start()
    try:
        _serve(gw, None, args)
    finally:
        gw.stop()


def cmd_sim(args) -> None:
    from aiohttp import web

    from .dash.gateway import Gateway
    from .dash.server import build_app
    from .sim.runner import Simulator
    sim = Simulator(args.bus, args.scenario, controlbox=not args.no_controlbox).start()
    # A small gateway too, so the sim page can show what the bus is doing
    gw = Gateway(args.bus)  # listens only; never started, so it sends nothing
    app = build_app(_ListenOnly(gw), sim)
    print(f"\n  Sim panel:   http://localhost:{args.port}/sim\n  CAN bus:     {args.bus}\n")
    try:
        web.run_app(app, host=args.host, port=args.port, print=None, access_log=None)
    finally:
        sim.stop()
        gw.node.close()


class _ListenOnly:
    """Gateway stand-in for the sim-only server: it has state but never sends."""

    def __init__(self, gw):
        import threading
        self._gw = gw
        self.bus_spec = gw.bus_spec
        self.frame_counts, self.unknown_ids = gw.frame_counts, gw.unknown_ids

        def loop():
            while True:
                for msg, v, raw in gw.node.poll(timeout=0.05):
                    gw._on_frame(msg, v, raw, time.monotonic())
        threading.Thread(target=loop, daemon=True).start()

    def snapshot(self):
        return self._gw.snapshot()

    def request(self, *_a):
        raise ValueError("this is the sim-only server; send requests to the dash")

    hold = set_setting = request


def cmd_monitor(args) -> None:
    from .canbus.bus import open_bus
    from .canbus.node import Node
    node = Node(open_bus(args.bus))
    only = {s.upper() for s in args.only.split(",")} if args.only else None
    print(f"Listening on {args.bus} (Ctrl+C to stop)")
    try:
        while True:
            for msg, v, raw in node.poll(timeout=0.5):
                if msg is None:
                    if not only:
                        print(f"{raw.timestamp:.3f}  {raw.arbitration_id:>8X}  ?  {raw.data.hex(' ')}")
                    continue
                if only and msg.name not in only:
                    continue
                vals = " ".join(f"{s.name}={s.choices.get(v[s.name], v[s.name]) if s.choices else v[s.name]}"
                                for s in msg.signals if s.name != "counter")
                print(f"{raw.timestamp:.3f}  {raw.arbitration_id:>8X}  {msg.name:<18} {vals}")
    except (KeyboardInterrupt, BrokenPipeError):
        pass
    finally:
        node.close()


def cmd_replay(args) -> None:
    import can

    from .canbus.bus import open_bus
    bus = open_bus(args.bus)
    print(f"Replaying {args.file} onto {args.bus} (Ctrl+C to stop)")
    try:
        while True:
            reader = can.LogReader(args.file)
            for msg in can.MessageSync(reader, timestamps=True, gap=0.0001):
                if msg.is_error_frame:
                    continue
                bus.send(msg)
            if not args.loop:
                break
    except KeyboardInterrupt:
        pass
    finally:
        bus.shutdown()


def cmd_canmap(args) -> None:
    from .canbus.docs import write_protocol_doc
    from .canbus.dbc import write_dbc
    print(f"wrote {write_protocol_doc(args.out)}")
    print(f"wrote {write_dbc(args.dbc)}")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="teryx", description="Teryx OS dash and test bench")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    def web_args(sp, port):
        sp.add_argument("--host", default="0.0.0.0", help="0.0.0.0 lets a phone/tablet on the same wifi connect")
        sp.add_argument("--port", type=int, default=port)

    from .sim.scenarios import SCENARIOS
    sp = sub.add_parser("run", help="sim + dash in one program")
    sp.add_argument("--bus", default="virtual")
    sp.add_argument("--scenario", default="idle", choices=list(SCENARIOS))
    sp.add_argument("--no-controlbox", action="store_true", help="don't fake the Pico (use the firmware host build)")
    sp.add_argument("--ui", help="folder to serve as the dash UI (default: basic test screen)")
    sp.add_argument("--plugin", action="append", help="module with setup_routes(app, gateway)")
    web_args(sp, 8080)
    sp.set_defaults(fn=cmd_run)

    sp = sub.add_parser("dash", help="dash only, on a shared or real bus")
    sp.add_argument("--bus", default="udp")
    sp.add_argument("--ui")
    sp.add_argument("--plugin", action="append")
    web_args(sp, 8080)
    sp.set_defaults(fn=cmd_dash)

    sp = sub.add_parser("sim", help="fake Shinegle + control box only, with the sim page")
    sp.add_argument("--bus", default="udp")
    sp.add_argument("--scenario", default="idle", choices=list(SCENARIOS))
    sp.add_argument("--no-controlbox", action="store_true")
    web_args(sp, 8081)
    sp.set_defaults(fn=cmd_sim)

    sp = sub.add_parser("monitor", help="print decoded CAN frames")
    sp.add_argument("--bus", default="udp")
    sp.add_argument("--only", help="comma list of message names, e.g. SG_MOTOR,PICO_STATUS")
    sp.set_defaults(fn=cmd_monitor)

    sp = sub.add_parser("replay", help="play a CAN log file onto the bus")
    sp.add_argument("file")
    sp.add_argument("--bus", default="udp")
    sp.add_argument("--loop", action="store_true")
    sp.set_defaults(fn=cmd_replay)

    sp = sub.add_parser("canmap", help="write the CAN protocol doc and .dbc file")
    sp.add_argument("--out", default="docs/CAN_PROTOCOL.md")
    sp.add_argument("--dbc", default="docs/teryx.dbc")
    sp.set_defaults(fn=cmd_canmap)

    args = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    args.fn(args)


if __name__ == "__main__":
    main()
