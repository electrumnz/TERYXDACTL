"""Scenarios: scripted situations for testing dash screens.

Each scenario is a class with ``start(sim)`` and ``update(sim, t, dt)``, where
``t`` is seconds since it started. Most of them loop forever.
Add new ones to SCENARIOS at the bottom and they show up on the sim page.
"""

from __future__ import annotations

import math


def drive_to(sim, target_kmh: float, gain: float = 0.12) -> None:
    """Simple driver: throttle or brake to hold a target speed."""
    v = sim.vehicle
    err = target_kmh - v.speed_kmh
    i = v.inp
    if target_kmh <= 0.1 and v.speed_kmh < 0.5:
        i.throttle, i.brake = 0.0, 0.3
        return
    if err > 0:
        i.throttle = max(0.0, min(1.0, err * gain + 0.15 + max(0, i.grade_pct) * 0.02))
        i.brake = 0.0
    else:
        i.throttle = 0.0
        i.brake = max(0.0, min(1.0, -err * 0.08)) if err < -2 else 0.0


class Scenario:
    name = "base"
    label = ""
    help = ""

    def start(self, sim) -> None:
        pass

    def update(self, sim, t: float, dt: float) -> None:
        pass


class Manual(Scenario):
    name, label = "manual", "Manual"
    help = "You drive with the sliders on the sim page."


class Idle(Scenario):
    name, label = "idle", "Parked, ready"
    help = "Key on, stopped, in neutral. Good for testing 4WD, diff, tray and winch."

    def start(self, sim):
        sim.vehicle.inp.direction = "neutral"

    def update(self, sim, t, dt):
        drive_to(sim, 0)


class Trail(Scenario):
    name, label = "trail", "Trail ride"
    help = "Loops a 2 minute trail ride: climbs, descents, stops and a quick blast."
    # (seconds, target km/h, grade %)
    PLAN = [(0, 0, 0), (4, 15, 0), (14, 30, 5), (28, 22, 18), (40, 12, -15), (50, 0, 0),
            (56, 25, 3), (70, 45, 0), (82, 35, -5), (95, 8, 25), (105, 20, 0), (115, 0, 0)]
    LENGTH = 120

    def start(self, sim):
        sim.vehicle.inp.direction = "forward"

    def update(self, sim, t, dt):
        t %= self.LENGTH
        seg = max((p for p in self.PLAN if p[0] <= t), key=lambda p: p[0])
        sim.vehicle.inp.grade_pct = seg[2] + 2 * math.sin(t * 0.7)
        drive_to(sim, seg[1] + 2 * math.sin(t * 0.3) if seg[1] else 0)


class HillClimb(Scenario):
    name, label = "hill_climb", "Long hill climb (overheat)"
    help = "Steep climb in sport mode. Motor and controller heat up, then limp mode kicks in."

    def start(self, sim):
        v = sim.vehicle
        v.inp.direction, v.inp.mode = "forward", "sport"
        v.motor_temp, v.controller_temp = 75, 62

    def update(self, sim, t, dt):
        sim.vehicle.inp.grade_pct = 30
        drive_to(sim, 25)
        if t > 3:
            # speed up the heating so it happens in a minute, not half an hour
            sim.vehicle.motor_temp += 0.8 * dt
            sim.vehicle.controller_temp += 0.5 * dt


class LowBattery(Scenario):
    name, label = "low_battery", "Low battery"
    help = "Starts at 15 % and drains fast. Limp mode under 10 %, then under-voltage."

    def start(self, sim):
        sim.vehicle.soc = 15
        sim.vehicle.inp.direction = "forward"

    def update(self, sim, t, dt):
        sim.vehicle.soc = max(0.0, sim.vehicle.soc - 0.12 * dt)
        drive_to(sim, 30 if sim.vehicle.soc > 3 else 0)


class Reversing(Scenario):
    name, label = "reversing", "Reversing"
    help = "Backs up slowly, stops, drives forward, repeats. Rear pods and camera should come on."

    def update(self, sim, t, dt):
        t %= 24
        i = sim.vehicle.inp
        if t < 3:
            i.direction = "neutral"
            drive_to(sim, 0)
        elif t < 12:
            i.direction = "reverse"
            drive_to(sim, 4 if t < 10 else 0, gain=0.3)
        elif t < 14:
            drive_to(sim, 0)
        else:
            i.direction = "forward"
            drive_to(sim, 8 if t < 22 else 0)


class ShinegleFaults(Scenario):
    name, label = "faults", "Motor controller faults"
    help = "Steps through each Shinegle fault, 5 s on, 2 s clear."

    FAULTS = ["over_current", "over_voltage", "under_voltage", "motor_over_temp",
              "controller_over_temp", "hall_sensor", "throttle", "comms", "precharge"]

    def start(self, sim):
        sim.vehicle.inp.direction = "forward"

    def update(self, sim, t, dt):
        k = int(t // 7) % len(self.FAULTS)
        on = (t % 7) < 5
        sim.vehicle.forced_faults = {self.FAULTS[k]} if on else set()
        drive_to(sim, 15)

    def stop(self, sim):
        sim.vehicle.forced_faults = set()


class ActuatorFaults(Scenario):
    name, label = "actuator_faults", "Jammed actuators"
    help = ("Stopped. Diff and tray actuators jam and 4WD draws too much current. "
            "Try 4WD, diff and tray on the dash to see the faults.")

    def start(self, sim):
        sim.vehicle.inp.direction = "neutral"
        sim.bench_faults = {"jam_diff", "jam_tray", "fourwd_overcurrent"}

    def update(self, sim, t, dt):
        drive_to(sim, 0)

    def stop(self, sim):
        sim.bench_faults = set()


class CommsLoss(Scenario):
    name, label = "comms_loss", "CAN drop-outs"
    help = ("Driving. Every 20 s the Shinegle goes quiet for 4 s, then the control box "
            "goes quiet for 4 s. The dash should show stale/offline, the Pico should "
            "flag speed_unknown.")

    def start(self, sim):
        sim.vehicle.inp.direction = "forward"

    def update(self, sim, t, dt):
        t %= 20
        sim.links["shinegle"] = not (6 <= t < 10)
        sim.links["controlbox"] = not (13 <= t < 17)
        drive_to(sim, 20)

    def stop(self, sim):
        sim.links["shinegle"] = sim.links["controlbox"] = True


class KeyOff(Scenario):
    name, label = "key_off", "Key off / shutdown"
    help = "Stops, then turns the key off. The Pico should hold power for the shutdown wait, then drop it."

    def update(self, sim, t, dt):
        drive_to(sim, 0)
        sim.bench_inputs["in.ignition"] = t < 3

    def stop(self, sim):
        sim.bench_inputs.pop("in.ignition", None)


SCENARIOS: dict[str, type[Scenario]] = {
    c.name: c for c in (Idle, Trail, Reversing, LowBattery, HillClimb, ShinegleFaults,
                        ActuatorFaults, CommsLoss, KeyOff, Manual)
}
