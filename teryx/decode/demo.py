"""Make a practice capture from a made-up "mystery" controller.

    python -m teryx decode demo captures/demo

It walks the whole guided procedure with a pretend Sam, so you can try the
analysis before touching the real Teryx, and the tests can check that the
analysis finds what's hidden in it. The layout below is deliberately NOT the
placeholder layout, and uses the tricks real Chinese controllers use:
extended ids, a big-endian speed, odd throttle scaling, offset temperatures,
packed status bits, a rolling counter and a dash heartbeat.

    0x0CF11E05 (ext, 20 ms)   rpm u16 LE | batt_a i16 LE x0.1 | batt_v u16 LE x0.1 | fault bits | 0
    0x0CF11F05 (ext, 100 ms)  throttle u8 (0-255) | ctrl_temp u8 -40 | motor_temp u8 -40 | 0 |
                              status: gear bits 0-1 (1 F, 2 R, 3 N), brake bit 3, mode bits 4-5
                              (1 eco, 2 normal, 3 sport), ready bit 7 | 0 | 0 | counter
    0x351      (std, 50 ms)   speed u16 BE x0.1 | soc u8 | 0x55 | odometer u16 LE km | 0 | 0
    0x601      (std, 200 ms)  from the Shinegle dash: heartbeat
    0x7A0      (std, 1000 ms) constant ident frame
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from .procedure import STEPS
from .session import Frame, Phase, Reading, StepRecord, format_candump, save_steps

EXPECTED = {   # what the analysis should find, used by the tests
    "rpm": (0x0CF11E05, 0, 16, False, 1.0, 0.0),
    "batt_a": (0x0CF11E05, 16, 16, False, 0.1, 0.0),
    "batt_v": (0x0CF11E05, 32, 16, False, 0.1, 0.0),
    "throttle": (0x0CF11F05, 0, 8, False, 100 / 255, 0.0),
    "ctrl_temp": (0x0CF11F05, 8, 8, False, 1.0, -40.0),
    "motor_temp": (0x0CF11F05, 16, 8, False, 1.0, -40.0),
    "speed": (0x351, 7, 16, True, 0.1, 0.0),
    "soc": (0x351, 16, 8, False, 1.0, 0.0),
    "odometer": (0x351, 32, 16, False, 1.0, 0.0),
    "direction": (0x0CF11F05, 32, 2, False, 1.0, 0.0),
    "brake": (0x0CF11F05, 35, 1, False, 1.0, 0.0),
    "mode": (0x0CF11F05, 36, 2, False, 1.0, 0.0),
    "ready": (0x0CF11F05, 39, 1, False, 1.0, 0.0),
    "fault_throttle": (0x0CF11E05, 50, 1, False, 1.0, 0.0),
}
KMH_PER_RPM = 0.0125
GEAR = {"neutral": 3, "forward": 1, "reverse": 2}
MODE = {"eco": 1, "normal": 2, "sport": 3}


class _Teryx:
    def __init__(self, rng: random.Random):
        self.rng = rng
        self.key = False
        self.ready = False
        self.direction = "neutral"
        self.mode = "normal"
        self.brake = False
        self.throttle = 0.0       # %
        self.rpm = 0.0
        self.batt_a = 0.0
        self.soc = 86.0
        self.charging = False
        self.ctrl_temp = 24.0
        self.motor_temp = 22.0
        self.odometer = 1234
        self.fault_throttle = False
        self.dash = True

    def step(self, dt: float) -> None:
        target = 0.0
        if self.ready and self.direction != "neutral" and not self.brake:
            target = 45 * max(0.0, self.throttle)   # rpm, wheels in the air
        tau = 0.6 if target > self.rpm else 1.5
        self.rpm += (target - self.rpm) * min(1.0, dt / tau)
        if self.charging:
            self.batt_a = -15.0
        elif target > self.rpm + 50:
            self.batt_a = 0.9 * self.throttle + 3
        elif self.rpm > 200 and target < self.rpm - 200:
            self.batt_a = -self.rpm / 4500 * 25      # regen
        else:
            self.batt_a = 2.0 if self.ready else 0.4
        self.batt_a += self.rng.gauss(0, 0.15)
        self.soc = max(0.0, min(100.0, self.soc - self.batt_a * dt / 3600 / 1.5))
        self.ctrl_temp += 0.002 * dt * self.throttle
        self.motor_temp += 0.003 * dt * self.throttle

    @property
    def batt_v(self) -> float:
        return 66 + 0.12 * self.soc - 0.03 * self.batt_a

    @property
    def speed(self) -> float:
        return self.rpm * KMH_PER_RPM

    def frames(self, t: float, ms: int, counters: dict) -> list[Frame]:
        out = []
        if not self.key:
            return out
        rpm = int(max(0, self.rpm))
        b1 = rpm.to_bytes(2, "little") + int(round(self.batt_a * 10)).to_bytes(2, "little", signed=True) \
            + int(round(self.batt_v * 10)).to_bytes(2, "little") + bytes([0x04 if self.fault_throttle else 0, 0])
        status = GEAR[self.direction] | (0x08 if self.brake else 0) | (MODE[self.mode] << 4) | (0x80 if self.ready else 0)
        thr = 0 if self.fault_throttle else int(round(min(100.0, max(0.0, self.throttle)) * 255 / 100))
        c = counters["1f"] = (counters.get("1f", -1) + 1) & 0xFF
        b2 = bytes([thr, int(self.ctrl_temp + 40), int(self.motor_temp + 40), 0, status, 0, 0, c])
        b3 = int(round(self.speed * 10)).to_bytes(2, "big") + bytes([int(self.soc), 0x55]) \
            + self.odometer.to_bytes(2, "little") + b"\0\0"
        def due(period):
            return ms % period == 0
        if due(20):
            out.append(Frame(t, 0x0CF11E05, b1, True))
        if due(100):
            out.append(Frame(t, 0x0CF11F05, b2, True))
        if due(50):
            out.append(Frame(t, 0x351, b3))
        if due(200) and self.dash:
            h = counters["dash"] = (counters.get("dash", -1) + 1) & 0x01
            out.append(Frame(t, 0x601, bytes([0x01, h, 0, 0])))
        if due(1000):
            out.append(Frame(t, 0x7A0, b"SG1202\x00\x01"))
        return out


def _shown(name: str, v: _Teryx) -> float:
    """What the Shinegle dash would display (rounded like a real dash)."""
    return {
        "batt_v": round(v.batt_v, 1), "soc": int(v.soc), "speed": round(v.speed),
        "rpm": int(round(v.rpm, -1)), "batt_a": round(v.batt_a), "motor_temp": int(v.motor_temp),
        "ctrl_temp": int(v.ctrl_temp), "odometer": v.odometer, "throttle": round(v.throttle),
    }[name]


def make_demo(folder: str | Path, seed: int = 1) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    v = _Teryx(rng)
    t0 = 1_763_000_000.0
    t, ms = t0, 0
    dt = 0.01
    counters: dict = {}
    records: list[StepRecord] = []
    with open(folder / "bus.log", "w", encoding="utf-8") as log:
        def run(seconds: float, rec: StepRecord, plan=None):
            nonlocal t, ms
            n = int(round(seconds / dt))
            for i in range(n):
                if plan:
                    plan(i * dt)
                v.step(dt)
                ms += 10
                t = t0 + ms / 1000
                log.writelines(format_candump(f) for f in v.frames(t, ms, counters))

        def phase(rec, label):
            rec.phases.append(Phase(t, label))

        def read(rec, *names):
            for n in names:
                rec.readings.append(Reading(t, n, float(_shown(n, v))))

        for s in STEPS:
            rec = StepRecord(s.id, s.title, t)
            records.append(rec)
            if s.id == "key_off":
                run(10, rec)
            elif s.id == "key_on":
                v.key = True
                run(10, rec)
                read(rec, *s.readings)
                run(10, rec)
            elif s.id == "ready_idle":
                v.ready = True
                run(15, rec)
                read(rec, "batt_v", "soc")
                run(15, rec)
            elif s.id == "dash_unplugged":
                run(5, rec)
                phase(rec, "unplugged")
                v.dash = False
                run(15, rec)
                phase(rec, "plugged back in")
                v.dash = True
                run(10, rec)
            elif s.id == "brake":
                for label in s.phases:
                    run(1.5 + rng.random(), rec)
                    phase(rec, label)
                    v.brake = label == "pressed"
                run(2, rec)
            elif s.id in ("direction", "mode"):
                for label in s.phases:
                    run(2 + rng.random(), rec)
                    phase(rec, label)
                    setattr(v, s.id, label)
                run(3, rec)
                v.direction = "neutral" if s.id == "direction" else v.direction
            elif s.id == "throttle_sweep":
                v.direction = "forward"
                run(2, rec)
                run(30, rec, lambda x: setattr(v, "throttle", 100 * (1 - abs((x % 10) - 5) / 5)))
                v.throttle = 0
                run(4, rec)
            elif s.id == "throttle_hold":
                for label in s.phases:
                    phase(rec, label)
                    target = float(label)
                    run(8, rec, lambda x, target=target: setattr(
                        v, "throttle", target + 1.5 * math.sin(x * 2.1) + rng.gauss(0, 0.4)))
                    if target:
                        read(rec, *s.readings)
                    run(2, rec)
                v.throttle = 0
            elif s.id == "regen":
                for _ in range(3):
                    phase(rec, "spin up")
                    v.throttle = 50
                    run(6, rec)
                    phase(rec, "let go")
                    v.throttle = 0
                    run(1, rec)
                    read(rec, "batt_a")
                    run(5, rec)
            elif s.id == "reverse_drive":
                v.direction = "reverse"
                run(24, rec, lambda x: setattr(v, "throttle", 25 * (1 - abs((x % 8) - 4) / 4)))
                v.throttle = 0
                run(3, rec)
                v.direction = "neutral"
            elif s.id == "charge":
                v.ready = False
                run(5, rec)
                phase(rec, "charger in")
                v.charging = True
                run(40, rec)
                read(rec, "batt_v", "soc", "batt_a")
                run(30, rec)
                phase(rec, "charger out")
                v.charging = False
                run(10, rec)
            elif s.id == "fault_throttle":
                run(5, rec)
                phase(rec, "unplugged")
                v.fault_throttle = True
                run(10, rec)
                phase(rec, "plugged back in")
                v.fault_throttle = False
                rec.notes.append("dash showed E-03")
                run(10, rec)
            elif s.id == "key_off_end":
                v.key = v.ready = False
                read(rec, "odometer")
                run(8, rec)
            else:   # steps the pretend Sam skips (mode switch has no modes? no, drive_flat, programmer)
                rec.skipped = True
                continue
            rec.end = t
    save_steps(folder, records, {"bus": "demo", "bitrate": 250000, "demo": True})
    return folder
