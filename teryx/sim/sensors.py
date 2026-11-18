"""Fake tilt sensor (IMU) and GPS for the simulator.

These give the dash's tilt and GPS widget something to show in the sim. On the Pi the real
ones publish the same keys (dash/server/teryx_dash/imu.py for the MPU-6050, and the 4G board's
GPS in dash/server/teryx_dash/remote.py) and win over these:

    pi.imu.roll, pi.imu.pitch          degrees (+ roll = right side down, + pitch = nose up)
    pi.gps.fix                         bool
    pi.gps.lat, pi.gps.lon             degrees
    pi.gps.alt_m, pi.gps.heading       metres, degrees from north
    pi.gps.speed_kmh, pi.gps.sats      km/h, satellites in use

The fake track starts near the middle of New Zealand (a made-up spot, not anyone's place)
and turns gently so the compass moves.
"""

from __future__ import annotations

import math

START_LAT = -41.27
START_LON = 173.28
EARTH_R = 6_371_000.0


class FakeSensors:
    def __init__(self) -> None:
        self.t = 0.0
        self.lat = START_LAT
        self.lon = START_LON
        self.alt = 120.0
        self.heading = 30.0
        self.enabled = {"imu": True, "gps": True}
        self.hold: dict | None = None   # bench override, e.g. {"roll": 28}

    def step(self, dt: float, speed_kmh: float, grade_pct: float, direction: str = "forward") -> None:
        self.t += dt
        v = speed_kmh / 3.6 * (-1 if direction == "reverse" else 1)
        if abs(v) > 0.1:
            self.heading = (self.heading + 4.0 * math.sin(self.t / 9) * dt) % 360
        h = math.radians(self.heading)
        d = v * dt
        self.lat += math.degrees(d * math.cos(h) / EARTH_R)
        self.lon += math.degrees(d * math.sin(h) / (EARTH_R * math.cos(math.radians(self.lat))))
        self.alt += d * grade_pct / 100
        self._speed = abs(speed_kmh)
        self._grade = grade_pct

    def state(self) -> dict:
        s: dict = {}
        if self.enabled["imu"]:
            pitch = math.degrees(math.atan(getattr(self, "_grade", 0.0) / 100))
            roll = 3.0 * math.sin(self.t / 4) + 1.5 * math.sin(self.t * 1.7) * min(1.0, getattr(self, "_speed", 0) / 20)
            s["pi.imu.pitch"] = round(pitch, 1)
            s["pi.imu.roll"] = round(roll, 1)
            for k, v in (self.hold or {}).items():
                if k in ("roll", "pitch"):
                    s[f"pi.imu.{k}"] = float(v)
        if self.enabled["gps"]:
            s.update({
                "pi.gps.fix": True,
                "pi.gps.lat": round(self.lat, 6),
                "pi.gps.lon": round(self.lon, 6),
                "pi.gps.alt_m": round(self.alt, 1),
                "pi.gps.heading": round(self.heading, 1),
                "pi.gps.speed_kmh": round(getattr(self, "_speed", 0.0), 1),
                "pi.gps.sats": 9,
            })
        return s
