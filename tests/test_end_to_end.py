"""Sim + gateway on one fake bus: the whole pipeline the dash UI sees."""

import time

import pytest

from teryx.dash.gateway import Gateway
from teryx.sim.runner import Simulator


def wait_for(fn, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if fn():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def rig(bus_spec):
    sim = Simulator(bus_spec, "idle").start()
    gw = Gateway(bus_spec).start()
    yield sim, gw
    gw.stop()
    sim.stop()


def test_dash_sees_both_boxes(rig):
    _sim, gw = rig
    assert wait_for(lambda: gw.snapshot()["mc.online"] and gw.snapshot()["pico.online"])
    assert wait_for(lambda: gw.snapshot()["pico.state"] == "ok")
    s = gw.snapshot()
    assert 80 <= s["mc.soc"] <= 90
    assert s["mc.direction"] == "neutral"


def test_requests_round_trip(rig):
    _sim, gw = rig
    assert wait_for(lambda: gw.snapshot()["pico.online"])
    gw.request("light.front_2", 180)
    gw.request("light.rear", "on")
    gw.request("act.4wd", 1)
    assert wait_for(lambda: gw.snapshot().get("light.front_2") == 180)
    assert wait_for(lambda: gw.snapshot().get("light.rear") is True)
    assert wait_for(lambda: gw.snapshot().get("act.4wd") == "4wd")


def test_hold_to_run_tray(rig):
    _sim, gw = rig
    assert wait_for(lambda: gw.snapshot()["pico.online"])
    for _ in range(15):
        gw.hold("act.tray", 1)
        time.sleep(0.1)
    assert gw.snapshot()["act.tray"] == "raising"
    gw.hold("act.tray", 0)
    assert wait_for(lambda: gw.snapshot()["act.tray"] == "mid")


def test_refused_request_snaps_back(rig):
    sim, gw = rig
    assert wait_for(lambda: gw.snapshot()["pico.online"])
    sim.set_scenario("trail")
    assert wait_for(lambda: gw.snapshot()["mc.speed"] > 10, timeout=15)
    assert gw.set_setting("shift_wait_ms", 600)
    gw.request("act.4wd", 1)
    assert wait_for(lambda: gw.snapshot()["act.4wd_wait"])        # spinner on the dash
    assert wait_for(lambda: gw.snapshot()["pico.reject"] == "wait_timeout")
    assert wait_for(lambda: gw.snapshot()["req.act.4wd"] == 0)


def test_waiting_request_can_be_cancelled(rig):
    sim, gw = rig
    assert wait_for(lambda: gw.snapshot()["pico.online"])
    sim.set_scenario("trail")
    assert wait_for(lambda: gw.snapshot()["mc.speed"] > 10, timeout=15)
    gw.request("act.4wd", 1)
    assert wait_for(lambda: gw.snapshot()["act.4wd_wait"])
    gw.request("act.4wd", 0)
    assert wait_for(lambda: not gw.snapshot()["act.4wd_wait"])
    assert gw.snapshot()["pico.reject"] == "none"


def test_settings_ack(rig):
    _sim, gw = rig
    assert wait_for(lambda: gw.snapshot()["pico.online"])
    assert gw.set_setting("diff_max_kmh", 10)
    assert gw.settings["diff_max_kmh"] == 10


def test_shinegle_drop_out(rig):
    sim, gw = rig
    assert wait_for(lambda: gw.snapshot()["mc.online"])
    sim.links["shinegle"] = False
    assert wait_for(lambda: not gw.snapshot()["mc.online"])
    assert wait_for(lambda: "speed_unknown" in gw.snapshot()["pico.faults"])


@pytest.mark.parametrize("name", ["trail", "reversing", "low_battery", "hill_climb", "faults",
                                  "actuator_faults", "comms_loss", "key_off", "manual", "idle",
                                  "drive_demo"])
def test_every_scenario_runs(bus_spec, name):
    sim = Simulator(bus_spec, name)
    now = time.monotonic()
    for k in range(1500):            # 30 s of sim time
        sim.tick(0.02, now + k * 0.02)
    mc = sim.vehicle.mc()
    assert 0 <= mc["mc.soc"] <= 100
    assert mc["mc.speed"] < 80
    sim.stop()
