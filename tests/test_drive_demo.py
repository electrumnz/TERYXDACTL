"""The scripted drive demo: does what its captions say, and pause/restart/skip work."""

import json

import pytest

from teryx.dash.gateway import Gateway
from teryx.dash.server import build_app
from teryx.sim.runner import Simulator
from teryx.sim.scenarios import DriveDemo


def run(sim, seconds, t0=[0.0]):
    for _ in range(int(seconds / 0.02)):
        t0[0] += 0.02
        sim.tick(0.02, t0[0])


@pytest.fixture
def sim(bus_spec):
    s = Simulator(bus_spec, "drive_demo")
    yield s
    s.stop()


def goto(sim, caption_start):
    k = next(i for i, st in enumerate(DriveDemo.STEPS) if st[1].startswith(caption_start))
    sim.apply({"demo_step": k})
    return k


def test_steps_add_up():
    assert DriveDemo.LENGTH == sum(s[0] for s in DriveDemo.STEPS)
    assert DriveDemo.STARTS[0] == 0 and len(DriveDemo.STARTS) == len(DriveDemo.STEPS)
    assert DriveDemo().step_at(DriveDemo.LENGTH + 1) == 0      # loops


def test_handbrake_holds_it_and_the_pico_sees_it(sim):
    goto(sim, "Oops")
    run(sim, 3)
    v = sim.vehicle
    assert v.inp.throttle > 0 and v.inp.handbrake
    assert v.speed_kmh == 0
    assert sim.cb.inp("in.park")


def test_pulls_away_cruises_and_brakes(sim):
    goto(sim, "Handbrake off")
    run(sim, 2)
    assert not sim.cb.inp("in.park")
    goto(sim, "Speeding up")
    run(sim, 15)
    assert 35 < sim.vehicle.speed_kmh < 45
    goto(sim, "Braking hard")
    run(sim, 0.3)
    assert sim.vehicle.mc()["mc.brake"]
    run(sim, 4)
    assert sim.vehicle.speed_kmh == 0


def test_reverse(sim):
    goto(sim, "Backing up")
    run(sim, 4)
    v = sim.vehicle
    assert v.inp.direction == "reverse" and v.speed_ms < 0 and 3 < v.speed_kmh < 7
    assert sim.cb.inp("in.reverse")


def test_pause_freezes_and_restart_starts_over(sim):
    goto(sim, "Cruising")
    run(sim, 1)
    sim.apply({"paused": True})
    t, spd = sim.scenario_t, sim.vehicle.speed_kmh
    run(sim, 2)
    assert sim.scenario_t == t and sim.vehicle.speed_kmh == spd
    assert sim.demo_info()["paused"]
    sim.apply({"restart": True})
    assert not sim.paused and sim.demo_info()["step"] == 0
    sim.apply({"demo_step": 99})                                # past the end wraps to the start
    assert sim.demo_info()["step"] == 0


def test_skip_only_for_scripted_scenarios(bus_spec):
    s = Simulator(bus_spec, "idle")
    try:
        assert s.demo_info() is None
        with pytest.raises(ValueError):
            s.apply({"demo_step": 1})
    finally:
        s.stop()


async def test_demo_info_goes_to_the_dash(aiohttp_client, bus_spec):
    sim = Simulator(bus_spec, "drive_demo").start()
    gw = Gateway(bus_spec).start()
    try:
        client = await aiohttp_client(build_app(gw, sim))
        st = await (await client.post("/api/sim", json={"paused": True})).json()
        assert st["paused"] and st["demo"]["caption"]
        ws = await client.ws_connect("/ws")
        for _ in range(50):
            msg = json.loads((await ws.receive(timeout=2)).data)
            if msg["type"] == "state":
                assert msg["state"]["sim.demo"]["paused"] is True
                assert msg["state"]["sim.paused"] is True
                break
        await ws.close()
    finally:
        gw.stop()
        sim.stop()
