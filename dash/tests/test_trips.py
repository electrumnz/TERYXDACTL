"""Trip logging: distance, energy, trips starting and ending, range estimate."""

from teryx_dash.trips import DEFAULT_WH_PER_KM, TripLog


def drive(log, t0, seconds, kmh, volts=76.0, amps=40.0, soc=80.0, ign=True, odo=None):
    t = t0
    for _ in range(seconds):
        t += 1
        s = {"in.ignition": ign, "mc.online": True, "mc.speed": kmh, "mc.batt_v": volts,
             "mc.batt_a": amps, "mc.soc": soc}
        if odo is not None:
            odo += kmh / 3600
            s["mc.odometer"] = odo
        log.sample(s, now=t)
    return t


def test_distance_and_energy_from_speed():
    log = TripLog()
    t = drive(log, 1000, 1, 0)                     # first sample just starts the trip
    drive(log, t, 360, 36)                         # 36 km/h for 6 minutes = 3.6 km
    cur = log.summary({})["current"]
    assert abs(cur["km"] - 3.6) < 0.05
    assert abs(cur["used_wh"] - 76 * 40 * 360 / 3600) < 1   # 304 Wh
    assert cur["max_kmh"] == 36
    assert cur["avg_kmh"] == 36


def test_regen_counts_separately():
    log = TripLog()
    t = drive(log, 0, 1, 0)
    t = drive(log, t, 60, 30, amps=50)
    drive(log, t, 30, 20, amps=-20)
    cur = log.summary({})["current"]
    assert cur["regen_wh"] > 0
    assert abs(cur["net_wh"] - (cur["used_wh"] - cur["regen_wh"])) < 0.2


def test_coarse_odometer_doesnt_lose_distance():
    log = TripLog()
    t = 0
    for i in range(121):     # odometer only counts in 0.1 km steps
        t += 1
        log.sample({"mc.speed": 30, "mc.batt_v": 76, "mc.batt_a": 10, "mc.odometer": round(100 + i * 30 / 3600, 1)}, now=t)
    assert abs(log.summary({})["current"]["km"] - 1.0) < 0.02


def test_no_motor_data_adds_nothing():
    log = TripLog()
    t = drive(log, 0, 1, 0)
    for i in range(60):
        t += 1
        log.sample({"mc.online": False, "mc.speed": 30, "mc.batt_v": 76, "mc.batt_a": 10}, now=t)
    assert log.summary({})["current"]["km"] == 0


def test_key_off_ends_trip_and_short_trips_are_dropped():
    log = TripLog()
    t = drive(log, 0, 1, 0)
    t = drive(log, t, 120, 30)                     # 1 km
    t = drive(log, t, 2, 0, ign=False)
    assert log.current is None and len(log.history) == 1
    t = drive(log, t, 3, 0)                        # key on, not moving
    t = drive(log, t, 2, 0, ign=False)
    assert len(log.history) == 1                   # the 0 km trip isn't kept


def test_long_gap_starts_new_trip():
    log = TripLog()
    t = drive(log, 0, 1, 0)
    t = drive(log, t, 120, 30)
    drive(log, t + 3600, 5, 30)
    assert len(log.history) == 1
    assert log.current["km"] < 0.1


def test_trip_a_survives_trips_and_resets():
    log = TripLog()
    t = drive(log, 0, 1, 0)
    t = drive(log, t, 120, 30)
    t = drive(log, t, 2, 0, ign=False)
    t = drive(log, t, 1, 0)
    t = drive(log, t, 120, 30)
    assert abs(log.trip_a["km"] - 2.0) < 0.05
    log.reset_trip_a(now=t)
    assert log.trip_a["km"] == 0


def test_range_estimate():
    log = TripLog()
    assert log.wh_per_km() == (DEFAULT_WH_PER_KM, "guess")
    t = drive(log, 0, 1, 0)
    # 36 km/h at 76 V x 50 A = 3.8 kW -> 105.6 Wh/km
    drive(log, t, 300, 36, amps=50)
    whk, basis = log.wh_per_km()
    assert basis == "learning" and abs(whk - 105.6) < 2
    r = log.summary({"mc.soc": 50}, pack_kwh=7.5)
    assert abs(r["range_km"] - 3750 / whk) < 0.5
    assert log.summary({})["range_km"] is None


def test_saves_and_loads(tmp_path):
    p = tmp_path / "trips.json"
    log = TripLog(p)
    t = drive(log, 0, 1, 0)
    t = drive(log, t, 120, 30)
    drive(log, t, 2, 0, ign=False)
    log.save()
    again = TripLog(p)
    assert len(again.history) == 1 and abs(again.lifetime["km"] - 1.0) < 0.05


def test_range_learns_and_settles_on_new_driving():
    """Drive gently for a while, then hard: the figure moves to the new use, newest counting most."""
    log = TripLog()
    t = drive(log, 0, 1, 0)
    t = drive(log, t, 1000, 36, amps=40)           # 10 km at 76 V x 40 A / 36 km/h = 84.4 Wh/km
    gentle, basis = log.wh_per_km()
    assert basis == "learnt" and abs(gentle - 84.4) < 2
    t = drive(log, t, 200, 36, amps=100)           # 2 km of hard going, 211 Wh/km
    mid, _ = log.wh_per_km()
    assert gentle < mid < 211
    drive(log, t, 1000, 36, amps=100)              # 10 more km of it
    hard, _ = log.wh_per_km()
    assert hard > mid and hard > 180               # mostly learnt the new figure
    assert hard < 211                              # still pulled a little toward the lifetime average


def test_one_short_climb_doesnt_swing_range():
    log = TripLog()
    t = drive(log, 0, 1, 0)
    t = drive(log, t, 1000, 36, amps=40)           # 10 km steady
    before, _ = log.wh_per_km()
    drive(log, t, 30, 36, amps=150)                # 0.3 km steep climb at 316 Wh/km
    after, _ = log.wh_per_km()
    assert after - before < 25


def test_learning_carries_on_after_restart(tmp_path):
    p = tmp_path / "trips.json"
    log = TripLog(p)
    t = drive(log, 0, 1, 0)
    drive(log, t, 800, 36, amps=60)
    log.save()
    whk, basis = log.wh_per_km()
    again = TripLog(p)
    assert again.wh_per_km() == (whk, basis)
    assert again.summary({"mc.soc": 50})["learnt_km"] == log.summary({"mc.soc": 50})["learnt_km"]


def test_fresh_pack_uses_first_guess():
    log = TripLog()
    r = log.summary({"mc.soc": 100}, pack_kwh=7.5)
    assert r["basis"] == "guess" and r["wh_per_km"] == DEFAULT_WH_PER_KM
    assert abs(r["range_km"] - 7500 / DEFAULT_WH_PER_KM) < 0.1
