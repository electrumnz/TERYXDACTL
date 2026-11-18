"""Tilt sensor: an MPU-6050 board on the Pi's I2C, read into pi.imu.roll / pi.imu.pitch.

The dash's Tilt panel and the tilt warnings (dash/web/js/alerts.js) read these keys. In the
simulator teryx/sim/sensors.py makes them up; on the Pi this reads the real board.

Wiring (config/wiring.yaml, device IMU): VCC to 3.3 V, GND, SDA to GPIO2, SCL to GPIO3 (I2C bus 1).
The DAC+ HAT shares that bus at 0x4C/0x4D, so there's no clash with the MPU-6050 at 0x68.

Register map from InvenSense's "MPU-6000/MPU-6050 Register Map and Descriptions" rev 4.2:
  0x6B PWR_MGMT_1   write 0 to wake it (it starts asleep)
  0x1C ACCEL_CONFIG 0 = +-2 g, 16384 counts per g
  0x3B..0x40        ACCEL_XOUT_H/L, Y, Z, big-endian signed 16-bit
Mount the board flat with its printed X arrow pointing forward and Y to the left (chip side up);
if it has to go another way, fix it with imu.json below. Only the accelerometer is used: roll = atan2(y, z), pitch = atan2(-x, sqrt(y^2 + z^2)), smoothed
so bumps don't make the numbers jump. That's right when parked or driving steady; hard braking or
cornering reads as a bit of extra tilt for a moment, which is fine for a warning.

How it sits in the dash: ~/.config/teryx/imu.json
  {"swap_xy": false, "invert_roll": false, "invert_pitch": false, "roll_zero": 0, "pitch_zero": 0}
POST /api/imu/zero (parked on flat ground) saves the current reading as level.

TERYX_IMU=off turns it off; TERYX_IMU=/dev/i2c-N picks another bus. With no I2C bus it does nothing.
"""

from __future__ import annotations

import asyncio
import fcntl
import json
import math
import os
from pathlib import Path
from typing import Any, Callable

from aiohttp import web

ADDR = 0x68
I2C_SLAVE = 0x0703          # linux/i2c-dev.h
REG_PWR_MGMT_1, REG_ACCEL_CONFIG, REG_ACCEL_XOUT_H = 0x6B, 0x1C, 0x3B
SMOOTH = 0.15               # low-pass per reading (10 a second): about 0.6 s to settle
READ_S = 0.1


def tilt_from_accel(ax: float, ay: float, az: float, cfg: dict) -> tuple[float, float]:
    """Raw accelerometer (any units) -> (roll, pitch) in degrees, with the mounting fixes applied.
    Roll is positive leaning right, pitch positive nose up (same as the sim)."""
    if cfg.get("swap_xy"):
        ax, ay = ay, ax
    roll = math.degrees(math.atan2(ay, az))
    pitch = math.degrees(math.atan2(-ax, math.hypot(ay, az)))
    if cfg.get("invert_roll"):
        roll = -roll
    if cfg.get("invert_pitch"):
        pitch = -pitch
    return roll - float(cfg.get("roll_zero", 0)), pitch - float(cfg.get("pitch_zero", 0))


def _s16(hi: int, lo: int) -> int:
    v = (hi << 8) | lo
    return v - 65536 if v & 0x8000 else v


class Mpu6050:
    """Plain /dev/i2c-N access, so there's nothing extra to install."""

    def __init__(self, dev: str = "/dev/i2c-1", addr: int = ADDR):
        self.fd = os.open(dev, os.O_RDWR)
        fcntl.ioctl(self.fd, I2C_SLAVE, addr)
        os.write(self.fd, bytes([REG_PWR_MGMT_1, 0x00]))
        os.write(self.fd, bytes([REG_ACCEL_CONFIG, 0x00]))

    def accel(self) -> tuple[int, int, int]:
        os.write(self.fd, bytes([REG_ACCEL_XOUT_H]))
        b = os.read(self.fd, 6)
        return _s16(b[0], b[1]), _s16(b[2], b[3]), _s16(b[4], b[5])

    def close(self) -> None:
        os.close(self.fd)


class TiltService:
    def __init__(self, cfg_path: Path, publish: Callable[[dict], None], sensor: Any = None):
        self.cfg_path = cfg_path
        self.publish = publish
        self.sensor = sensor
        self.roll: float | None = None
        self.pitch: float | None = None
        self.raw: tuple[float, float] | None = None   # before the zero, for /api/imu/zero
        self.cfg = self.load()

    def load(self) -> dict:
        try:
            d = json.loads(self.cfg_path.read_text())
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def save(self) -> None:
        self.cfg_path.parent.mkdir(parents=True, exist_ok=True)
        self.cfg_path.write_text(json.dumps(self.cfg, indent=1))

    def step(self, ax: float, ay: float, az: float) -> dict:
        r0, p0 = tilt_from_accel(ax, ay, az, {**self.cfg, "roll_zero": 0, "pitch_zero": 0})
        if self.raw is None:
            self.raw = (r0, p0)
        else:
            self.raw = (self.raw[0] + SMOOTH * (r0 - self.raw[0]), self.raw[1] + SMOOTH * (p0 - self.raw[1]))
        self.roll = self.raw[0] - float(self.cfg.get("roll_zero", 0))
        self.pitch = self.raw[1] - float(self.cfg.get("pitch_zero", 0))
        out = {"pi.imu.roll": round(self.roll, 1), "pi.imu.pitch": round(self.pitch, 1), "pi.imu.ok": True}
        self.publish(out)
        return out

    def zero(self) -> dict:
        if self.raw is None:
            raise RuntimeError("no reading from the tilt sensor yet")
        self.cfg["roll_zero"], self.cfg["pitch_zero"] = round(self.raw[0], 2), round(self.raw[1], 2)
        self.save()
        return {"roll_zero": self.cfg["roll_zero"], "pitch_zero": self.cfg["pitch_zero"]}


IMU_KEY = web.AppKey("teryx_dash_imu", TiltService)
IMU_TASK_KEY = web.AppKey("teryx_dash_imu_task", asyncio.Future)


def setup_imu_routes(app: web.Application, gateway: Any, config_dir: Callable[[], Path],
                     is_stopped: Callable[[], bool], sensor: Any = None) -> TiltService | None:
    publish = getattr(gateway, "set_local", None)
    dev = os.environ.get("TERYX_IMU", "/dev/i2c-1")
    if publish is None or dev == "off" or (sensor is None and not Path(dev).exists()):
        return None   # no I2C (laptop, sim): the sim's fake tilt shows instead
    svc = TiltService(config_dir() / "imu.json", publish, sensor)
    app[IMU_KEY] = svc

    async def loop():
        fails = 0
        while True:
            try:
                if svc.sensor is None:
                    svc.sensor = await asyncio.to_thread(Mpu6050, dev)
                svc.step(*await asyncio.to_thread(svc.sensor.accel))
                fails = 0
                await asyncio.sleep(READ_S)
            except asyncio.CancelledError:
                raise
            except Exception:
                fails += 1
                if svc.sensor is not None and fails >= 5:
                    try:
                        svc.sensor.close()
                    except Exception:
                        pass
                    svc.sensor = None
                if fails == 5:
                    publish({"pi.imu.ok": False})   # board missing or a loose wire
                await asyncio.sleep(5 if fails >= 5 else READ_S)

    async def zero(_req):
        if not is_stopped():
            return web.json_response({"error": "stop on flat ground first"}, status=409)
        try:
            return web.json_response(svc.zero())
        except RuntimeError as e:
            return web.json_response({"error": str(e)}, status=503)

    async def status(_req):
        return web.json_response({"roll": svc.roll, "pitch": svc.pitch, "config": svc.cfg})

    async def on_start(_app):
        _app[IMU_TASK_KEY] = asyncio.ensure_future(loop())

    async def on_stop(_app):
        _app[IMU_TASK_KEY].cancel()

    app.router.add_get("/api/imu", status)
    app.router.add_post("/api/imu/zero", zero)
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)
    return svc
