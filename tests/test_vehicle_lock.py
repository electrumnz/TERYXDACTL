"""Vehicle lock (docs/vehicle-lock.md): rules, the control box emulator and the whole pipeline."""

import time

import pytest

from teryx.canbus import messages as M
from teryx.dash.gateway import Gateway
from teryx.sim.runner import Simulator
from teryx.vehicle_lock import (FREE_TRIES, VehicleLock, decode_digits, encode_digits, lock_hash)

from test_controlbox import Bench


def test_hash_matches_firmware():
    # Same vector as test_lock_hash in firmware/control-box/tests/test_controller.c
    assert lock_hash(bytes(range(16)), "1234").hex() == \
        "97ddbcf2cb504922480796891327ead84d3a26b65429411b513a9480e49a3e29"


def test_digits_round_trip():
    v = encode_digits("482109")
    assert v["n_digits"] == 6 and v["d0"] == 0x48 and v["d1"] == 0x21 and v["d2"] == 0x09
    assert decode_digits(v) == "482109"
    assert decode_digits(encode_digits("12")) is None   # too short
    assert decode_digits({"n_digits": 4, "d0": 0xA1, "d1": 0, "d2": 0, "d3": 0}) is None
    with pytest.raises(ValueError):
        encode_digits("12ab")


def test_pin_never_stored():
    lk = VehicleLock()
    assert lk.command("set_pin", "4821", True, 0) == "ok"
    blob = repr(lk.stored())
    assert "4821" not in blob and b"4821" not in lk.pin_hash


def test_rules():
    lk = VehicleLock()
    assert lk.command("lock", None, True, 0) == "no_pin"
    assert lk.command("set_pin", "4821", True, 0) == "ok"
    assert lk.command("set_puk", "11223344", True, 1) == "ok"
    assert lk.command("lock", None, False, 2) == "not_parked"
    assert lk.command("lock", None, True, 3) == "ok" and lk.locked
    assert lk.command("set_pin", "0000", True, 4) == "not_allowed"
    assert lk.command("remove", None, True, 4) == "not_allowed"
    # wrong tries, lockout, doubling
    for _ in range(FREE_TRIES):
        assert lk.command("unlock", "0000", True, 5) == "wrong"
    assert lk.command("unlock", "4821", True, 6) == "lockout" and lk.locked
    f = lk.frame(6, True)
    assert f["lockout"] == 1 and f["tries_left"] == 0 and 29 <= f["lockout_s"] <= 30
    # power cut: count kept, lockout starts over
    lk = VehicleLock.restore(lk.stored(), now=100)
    assert lk.locked and lk.lockout_until == 130
    assert lk.command("unlock", "9999", True, 131) == "wrong" and lk.lockout_until == 131 + 60
    assert lk.command("unlock", "4821", True, 200) == "ok" and not lk.locked and lk.fails == 0
    # change PIN needs the old one first, and drops the recovery code
    assert lk.command("set_pin", "5555", True, 201) == "not_allowed"
    assert lk.command("verify", "4821", True, 202) == "ok"
    assert lk.command("set_pin", "555555", True, 203) == "ok" and lk.puk_hash is None
    assert lk.command("set_puk", "87654321", True, 204) == "ok"
    # recovery code: unlocks and wipes
    assert lk.command("lock", None, True, 300) == "ok"
    assert lk.command("unlock", "87654321", True, 301) == "recovered"
    assert not lk.locked and not lk.pin_set and lk.puk_hash is None
    # window runs out
    assert lk.command("set_pin", "2468", True, 302) == "ok"
    assert lk.command("remove", None, True, 302 + 61) == "not_allowed"
    assert lk.command("verify", "2468", True, 400) == "ok"
    assert lk.command("remove", None, True, 401) == "ok" and lk.state() == "off"


def lock_frame(cmd, digits=None):
    return {"cmd": {v: k for k, v in M.LOCK_CMD.items()}[cmd], **encode_digits(digits or ""), "counter": 0}


@pytest.fixture
def b():
    bench = Bench()
    bench.run(0.2)
    bench.drive_req(0, 0)
    bench.run(1.5)
    return bench


def test_emulator_lock_needs_park_brake_and_stopped(b):
    cb = b.cb
    cb.on_frame("PI_LOCK", lock_frame("set_pin", "4821"), b.t)
    cb.on_frame("PI_LOCK", lock_frame("lock"), b.t)
    assert cb.lock.result == "not_parked" and not cb.locked
    cb.forced["in.park"] = True
    b.speed = 10
    b.run(0.3)
    cb.on_frame("PI_LOCK", lock_frame("lock"), b.t)
    assert cb.lock.result == "not_parked"
    b.speed = 0
    b.run(0.3)
    cb.on_frame("PI_LOCK", lock_frame("lock"), b.t)
    assert cb.locked and cb.drive_inhibit
    assert dict(cb.frames())["PICO_LOCK"]["state"] == 2


def test_emulator_locked_blocks_everything(b):
    cb = b.cb
    cb.forced["in.park"] = True
    cb.on_frame("PI_LIGHTS", {"front_1": 255, "front_2": 0, "front_3": 0, "front_4": 0, "interior": 100,
                              "effect": 0, "rear_on": 1, "rear_auto": 0}, b.t)
    b.hold = (0, 0, 1)
    b.run(0.3)
    assert cb.winch_armed and cb.lights_out["front_1"] == 255
    cb.on_frame("PI_LOCK", lock_frame("set_pin", "4821"), b.t)
    cb.on_frame("PI_LOCK", lock_frame("lock"), b.t)
    b.run(0.3)
    assert cb.locked and not cb.winch_armed
    assert all(v == 0 for k, v in cb.lights_out.items() if k.startswith(("front", "interior")))
    assert not cb.relays()["light.rear"]
    b.hold = (1, 0, 0)
    b.run(1.0)
    assert not cb.tray.moving and cb.reject_reason == "interlock"
    b.hold = None
    b.drive_req(1, 40)
    b.run(1.0)
    assert cb.fourwd_state() == "2wd" and cb.diff.target == 0
    cb.on_frame("PI_SETTINGS", {"key": 30, "value": 5000}, b.t)
    assert cb.acks[-1]["status"] == 3 and cb.settings["shift_wait_ms"] == 10000
    cb.on_frame("PI_LOCK", lock_frame("unlock", "4821"), b.t)
    b.run(0.5)
    assert not cb.locked and cb.fourwd_state() == "2wd"   # nothing done by surprise


def wait_for(fn, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if fn():
            return True
        time.sleep(0.05)
    return False


def test_end_to_end_lock_stops_driving(bus_spec):
    sim = Simulator(bus_spec, "idle").start()
    gw = Gateway(bus_spec).start()
    try:
        assert wait_for(lambda: gw.snapshot()["pico.online"] and gw.snapshot().get("lock.state") == "off")
        assert wait_for(lambda: gw.snapshot().get("act.4wd") == "2wd")   # 4WD homed after boot
        gw.lock("set_pin", "4821")
        assert wait_for(lambda: gw.snapshot()["lock.state"] == "unlocked")
        gw.lock("lock")
        assert wait_for(lambda: gw.snapshot()["lock.result"] == "not_parked")
        sim.apply({"input": ["in.park", True]})
        time.sleep(0.3)
        gw.lock("lock")
        assert wait_for(lambda: gw.snapshot()["lock.state"] == "locked" and gw.snapshot()["lock.inhibit"])
        # Foot down: nothing happens
        sim.apply({"input": ["in.park", None], "direction": "forward", "throttle": 1.0})
        time.sleep(1.5)
        assert gw.snapshot()["mc.speed"] < 0.5
        # Wrong PIN
        gw.lock("unlock", "0000")
        assert wait_for(lambda: gw.snapshot()["lock.result"] == "wrong" and gw.snapshot()["lock.tries_left"] == 4)
        gw.lock("unlock", "4821")
        assert wait_for(lambda: gw.snapshot()["lock.state"] == "unlocked")
        assert wait_for(lambda: gw.snapshot()["mc.speed"] > 2, timeout=5)
    finally:
        gw.stop()
        sim.stop()
