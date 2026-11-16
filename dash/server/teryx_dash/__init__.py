"""Teryx dash: server-side extras for the dash UI.

The gateway (the `teryx` package from the test environment work) serves the UI and the
live /ws feed. It calls `setup_routes(app, gateway)` from here to add the /api/ routes the
settings screens need:

    GET/PUT  /api/settings              dash settings (look, units, camera, light names)
    GET/PUT  /api/pico-settings         control box limits (sent over CAN 0x704)
    POST     /api/pico-settings/save    ask the control box to save to flash
    POST     /api/pico-settings/reset   ask the control box to go back to defaults
    POST     /api/diff-calibrate        set diff pot open/locked points from the live reading
    GET      /api/ota/status            update state
    POST     /api/ota/check|install|rollback
    GET      /api/wifi, POST /api/wifi/connect
    GET      /api/wifi/scan, POST /api/wifi/add|forget   join new networks from the on-screen keyboard
    GET      /api/trips, POST /api/trips/reset/trip-a|history   trip log and range estimate
    GET      /api/system, POST /api/system/restart|shutdown
    GET      /api/camera.mjpg           camera as an MJPEG stream (fallback for the camera screen)
    GET/POST /api/audio/...             audio outputs, volume, ducking, Bluetooth phone (see media.py)
    GET      /api/media/...             music on the Pi and USB sticks, internet radio relay

Nothing personal is stored in the repo: settings live in ~/.config/teryx/ on the Pi.
"""

from .routes import setup_routes  # noqa: F401

__version__ = "0.1.0"
