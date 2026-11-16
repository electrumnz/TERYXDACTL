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


class DriveDemo(Scenario):
    """A scripted drive to watch the dash (and the virtual Teryx) react.

    Each step is (seconds, caption, what the driver does). The caption shows on the dash's
    demo player, which can pause, restart or skip a step (see Simulator.apply).
    Driver keys: dir, target (km/h, held with drive_to), throttle / brake (fixed, 0..1),
    hb (handbrake), mode, grade (%).
    """

    name, label = "drive_demo", "Drive demo (scripted)"
    help = ("About 100 s of normal driving: handbrake, pull away, speed up, cruise, regen, "
            "hard braking, reverse with the camera, a hill up and down, then park. Loops.")

    STEPS = [
        (5, "Parked. Key on, handbrake on, in neutral.", dict(dir="neutral", hb=True, target=0)),
        (3, "Into drive. Handbrake is still on.", dict(dir="forward", hb=True, target=0)),
        (4, "Oops, throttle with the handbrake on. The dash warns you.",
         dict(dir="forward", hb=True, throttle=0.35)),
        (2, "Handbrake off.", dict(dir="forward", target=0)),
        (8, "Pulling away gently.", dict(dir="forward", target=15)),
        (9, "Speeding up to 40 km/h in normal mode.", dict(dir="forward", mode="normal", target=40)),
        (8, "Cruising at 40.", dict(dir="forward", mode="normal", target=40)),
        (6, "Off the throttle. Regen puts some charge back.", dict(dir="forward", throttle=0, brake=0)),
        (5, "Braking hard. Brake lights on.", dict(dir="forward", brake=0.4)),
        (3, "Stopped, foot on the brake.", dict(dir="forward", brake=0.3)),
        (3, "Handbrake on, back to neutral.", dict(dir="neutral", hb=True, target=0)),
        (3, "Into reverse, handbrake off. Reverse camera pops up.", dict(dir="reverse", brake=0.3)),
        (9, "Backing up slowly. Tap the big button to flick the rear light bar.",
         dict(dir="reverse", target=5)),
        (3, "Braking.", dict(dir="reverse", brake=0.4)),
        (4, "Handbrake on, neutral. Camera stays 3 s, then goes back.",
         dict(dir="neutral", hb=True, target=0)),
        (3, "Into drive, handbrake off.", dict(dir="forward", target=0)),
        (10, "Up a steep hill. Watch the power and the motor temp.",
         dict(dir="forward", target=20, grade=18)),
        (8, "Down the other side. Regen holds it back.", dict(dir="forward", target=15, grade=-15)),
        (6, "Easing to a stop.", dict(dir="forward", brake=0.15)),
        (5, "Parked. Handbrake on, neutral. Starting again soon.", dict(dir="neutral", hb=True, target=0)),
    ]

    def step_at(self, t: float) -> int:
        t %= self.LENGTH
        return max(k for k, s0 in enumerate(self.STARTS) if s0 <= t)

    def start(self, sim):
        self.update(sim, 0.0, 0.0)

    def update(self, sim, t, dt):
        k = self.step_at(t)
        do = self.STEPS[k][2]
        v, i = sim.vehicle, sim.vehicle.inp
        i.direction = do.get("dir", "neutral")
        i.mode = do.get("mode", "normal")
        i.grade_pct = float(do.get("grade", 0))
        i.handbrake = bool(do.get("hb", False))
        sim.bench_inputs["in.park"] = i.handbrake      # handbrake switch, as the Pico would see it
        if "target" in do:
            drive_to(sim, do["target"], gain=0.3 if i.direction == "reverse" else 0.12)
            if do["target"] == 0 and v.speed_kmh < 0.5:
                i.brake = 0.0 if i.handbrake else i.brake
        else:
            i.throttle = float(do.get("throttle", 0.0))
            i.brake = float(do.get("brake", 0.0)) if v.speed_kmh > 0.2 or do.get("brake") else 0.0

    def info(self, t: float) -> dict:
        k = self.step_at(t)
        tl = t % self.LENGTH
        return {"step": k, "steps": len(self.STEPS), "caption": self.STEPS[k][1],
                "next": self.STEPS[(k + 1) % len(self.STEPS)][1],
                "t": round(tl, 1), "length": self.LENGTH,
                "step_left": round(self.STARTS[k] + self.STEPS[k][0] - tl, 1)}

    def seek_step(self, k: int) -> float:
        """Scenario time for the start of step k (wraps)."""
        return float(self.STARTS[k % len(self.STEPS)])

    def stop(self, sim):
        sim.vehicle.inp.handbrake = False
        sim.bench_inputs.pop("in.park", None)


DriveDemo.STARTS = [sum(st[0] for st in DriveDemo.STEPS[:k]) for k in range(len(DriveDemo.STEPS))]
DriveDemo.LENGTH = sum(st[0] for st in DriveDemo.STEPS)


SCENARIOS: dict[str, type[Scenario]] = {
    c.name: c for c in (Idle, DriveDemo, Trail, Reversing, LowBattery, HillClimb, ShinegleFaults,
                        ActuatorFaults, CommsLoss, KeyOff, Manual)
}
