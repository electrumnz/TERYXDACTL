"""Tilt sensor (dash/server/teryx_dash/imu.py)."""

import asyncio

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from teryx_dash import imu as I


def test_tilt_maths():
    assert I.tilt_from_accel(0, 0, 16384, {}) == pytest.approx((0, 0))
    r, p = I.tilt_from_accel(0, 16384 * 0.5, 16384 * 0.866, {})   # right side down 30 deg
    assert r == pytest.approx(30, abs=0.1) and p == pytest.approx(0, abs=0.1)
    r, p = I.tilt_from_accel(-16384 * 0.5, 0, 16384 * 0.866, {})  # nose up 30 deg
    assert p == pytest.approx(30, abs=0.1) and r == pytest.approx(0, abs=0.1)
    r, p = I.tilt_from_accel(-16384 * 0.5, 0, 16384 * 0.866, {"swap_xy": True, "invert_roll": True})
    assert r == pytest.approx(30, abs=0.1)
    assert I.tilt_from_accel(0, 0, 16384, {"roll_zero": 2, "pitch_zero": -1}) == pytest.approx((-2, 1))
    assert I._s16(0xFF, 0xFF) == -1 and I._s16(0x40, 0x00) == 16384


class FakeSensor:
    def __init__(self, xyz):
        self.xyz = xyz

    def accel(self):
        return self.xyz

    def close(self):
        pass


class Gw:
    def __init__(self):
        self.local = {}

    def set_local(self, v):
        self.local.update(v)


async def test_service_publishes_and_zeroes(tmp_path):
    gw = Gw()
    app = web.Application()
    stopped = {"v": False}
    svc = I.setup_imu_routes(app, gw, lambda: tmp_path, lambda: stopped["v"],
                             sensor=FakeSensor((0, 16384 * 0.0872, 16384 * 0.9962)))   # 5 deg right side down
    async with TestClient(TestServer(app)) as c:
        for _ in range(100):
            await asyncio.sleep(0.01)
            if abs(gw.local.get("pi.imu.roll", 0) - 5) < 0.2:
                break
        assert gw.local["pi.imu.roll"] == pytest.approx(5, abs=0.2) and gw.local["pi.imu.ok"]
        assert (await c.post("/api/imu/zero")).status == 409   # only when stopped
        stopped["v"] = True
        r = await c.post("/api/imu/zero")
        assert r.status == 200 and (await r.json())["roll_zero"] == pytest.approx(5, abs=0.2)
        assert (tmp_path / "imu.json").exists()
        await asyncio.sleep(0.25)
        assert gw.local["pi.imu.roll"] == pytest.approx(0, abs=0.2)
    assert svc.cfg["roll_zero"] == pytest.approx(5, abs=0.2)


def test_no_i2c_no_service(tmp_path, monkeypatch):
    monkeypatch.setenv("TERYX_IMU", str(tmp_path / "no-such-bus"))
    assert I.setup_imu_routes(web.Application(), Gw(), lambda: tmp_path, lambda: True) is None
    monkeypatch.setenv("TERYX_IMU", "off")
    assert I.setup_imu_routes(web.Application(), Gw(), lambda: tmp_path, lambda: True, sensor=FakeSensor((0, 0, 1))) is None
