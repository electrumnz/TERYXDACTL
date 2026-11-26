"""Fake Shinegle controller + simple Teryx physics.

Rough numbers, good enough to make the dash move like the real thing:
7.5 kW motor, 72 V lithium pack, ~700 kg with driver, top speed about 55 km/h.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


MASS_KG = 700.0
WHEEL_RADIUS_M = 0.33        # 26" tyres
MOTOR_RPM_PER_KMH = 95.0     # motor rpm per km/h through the transfer case (guess)
PEAK_POWER_W = 15_000.0      # short-term peak, the 7.5 kW is continuous
CONT_POWER_W = 7_500.0
MAX_SPEED_KMH = {"eco": 40.0, "normal": 50.0, "sport": 55.0}
PACK_AH = 105.0
PACK_R_OHM = 0.06
DCDC_LOAD_W = 120.0          # lights, dash, Pi etc on the 12 V side
AMBIENT_C = 18.0


def ocv(soc: float) -> float:
    """Open circuit voltage for a 72 V (20S LiFePO4-ish curve, stretched) pack."""
    s = max(0.0, min(1.0, soc / 100))
    # Steep at both ends, flat in the middle
    return 60.0 + 16.0 * s + 4.0 * (1 - math.exp(-12 * s)) + 4.0 * math.exp(-12 * (1 - s)) - 2.0


@dataclass
class DriverInput:
    throttle: float = 0.0      # 0..1
    brake: float = 0.0         # 0..1
    direction: str = "neutral" # neutral / forward / reverse
    mode: str = "eco"          # eco / normal / sport
    grade_pct: float = 0.0     # + = uphill
    extra_load_w: float = 0.0  # winch etc on the 12 V side
    handbrake: bool = False    # holds the wheels (the drive demo pulls it on and off)


@dataclass
class Vehicle:
    soc: float = 85.0
    speed_ms: float = 0.0          # signed, - = reversing
    motor_temp: float = AMBIENT_C + 10
    controller_temp: float = AMBIENT_C + 8
    battery_temp: float = AMBIENT_C + 4
    ambient: float = AMBIENT_C
    odometer_km: float = 1234.5
    pack_current: float = 0.0
    pack_voltage: float = 0.0
    power_w: float = 0.0
    torque_nm: float = 0.0
    forced_faults: set = field(default_factory=set)   # injected by scenarios / sim page
    throttle_hold: bool = False    # control box holds throttle while a shift runs from a standstill
    drive_inhibit: bool = False    # vehicle locked: the control box asks for no drive at all
    park_block: bool = False       # park brake on: the control box opens the pedal switch (no drive)
    inp: DriverInput = field(default_factory=DriverInput)

    # ----------------------------------------------------------- derived
    @property
    def speed_kmh(self) -> float:
        return abs(self.speed_ms) * 3.6

    @property
    def faults(self) -> set[str]:
        f = set(self.forced_faults)
        if self.motor_temp > 140:
            f.add("motor_over_temp")
        if self.controller_temp > 90:
            f.add("controller_over_temp")
        if self.battery_temp > 60:
            f.add("battery_over_temp")
        if self.pack_voltage and self.pack_voltage < 58:
            f.add("under_voltage")
        if self.pack_voltage > 86:
            f.add("over_voltage")
        return f

    @property
    def limp(self) -> bool:
        return self.soc < 10 or self.motor_temp > 120 or self.controller_temp > 80 or bool(self.faults)

    @property
    def ready(self) -> bool:
        hard = {"hall_sensor", "throttle", "over_current", "under_voltage", "precharge"}
        return not (self.faults & hard) and self.soc > 0

    def power_limit_w(self) -> float:
        lim = PEAK_POWER_W
        if self.limp:
            lim = CONT_POWER_W * 0.4
        if self.soc < 5:
            lim = CONT_POWER_W * 0.15
        return lim

    # ----------------------------------------------------------- physics
    def step(self, dt: float) -> None:
        i = self.inp
        direction = {"forward": 1, "reverse": -1}.get(i.direction, 0)
        vmax = MAX_SPEED_KMH.get(i.mode, 40) / 3.6
        if direction < 0:
            vmax = min(vmax, 15 / 3.6)

        v = self.speed_ms
        speed = abs(v)
        # Drive force from throttle, capped by power and top speed
        f_drive = 0.0
        held = self.throttle_hold and speed < 0.5 / 3.6   # never cut once moving
        if direction and self.ready and i.throttle > 0 and not held and not self.drive_inhibit and not self.park_block:
            max_force = 3200.0 if i.mode == "sport" else 2600.0
            p_lim = self.power_limit_w()
            f_drive = min(max_force, p_lim / max(speed, 0.5)) * i.throttle
            if speed > vmax:
                f_drive *= max(0.0, 1 - (speed - vmax) * 2)
            f_drive *= direction
        # Resistances
        sign = 1 if v > 0 else -1 if v < 0 else 0
        f_roll = 0.03 * MASS_KG * 9.81 * sign
        f_aero = 0.5 * 1.2 * 1.6 * v * v * sign
        f_grade = MASS_KG * 9.81 * math.sin(math.atan(i.grade_pct / 100))
        f_brake = 6000.0 * i.brake * sign
        if i.handbrake:
            f_brake += 3500.0 * sign
        # Regen when coasting with no throttle (only with a gear in)
        f_regen = 0.0
        if direction and i.throttle == 0 and speed > 1.5:
            f_regen = 400.0 * sign
        f_total = f_drive - f_roll - f_aero - f_grade - f_brake - f_regen
        a = f_total / MASS_KG
        nv = v + a * dt
        # Stop cleanly instead of rocking back and forth around zero
        if abs(nv) < 0.05 and f_drive == 0 and abs(f_grade) < abs(f_roll) + abs(f_brake) + 50:
            nv = 0.0
        # Handbrake on: the wheels don't turn from a standstill unless the motor beats it
        if i.handbrake and v == 0 and abs(f_drive - f_grade) < 3500.0:
            nv = 0.0
        if direction == 0 and v != 0 and (nv > 0) != (v > 0):
            nv = 0.0
        self.speed_ms = nv
        self.odometer_km += abs(nv) * dt / 1000

        # Electrical
        mech_w = (f_drive - f_regen * 0.7) * nv
        eff = 0.88 if mech_w >= 0 else 1 / 0.75
        motor_w = mech_w / eff
        aux_w = DCDC_LOAD_W + i.extra_load_w
        self.power_w = motor_w + aux_w
        self.torque_nm = (f_drive - f_regen) * WHEEL_RADIUS_M / 6.0  # ~6:1 reduction
        v_oc = ocv(self.soc)
        # Solve I from P = (Voc - I R) I, take the smaller root
        disc = v_oc * v_oc - 4 * PACK_R_OHM * self.power_w
        current = (v_oc - math.sqrt(max(disc, 0.0))) / (2 * PACK_R_OHM)
        self.pack_current = current
        self.pack_voltage = v_oc - current * PACK_R_OHM
        self.soc = max(0.0, min(100.0, self.soc - current * dt / 3600 / PACK_AH * 100))

        # Thermal: heat goes up with current squared, cools toward ambient
        heat = current * current
        self.motor_temp += (heat * 0.00002 - (self.motor_temp - self.ambient) * 0.004) * dt
        self.controller_temp += (heat * 0.000021 - (self.controller_temp - self.ambient) * 0.006) * dt
        self.battery_temp += (heat * 0.000003 - (self.battery_temp - self.ambient) * 0.002) * dt

    # ----------------------------------------------------------- io-map values
    def mc(self) -> dict:
        """Current values under their io-map names (what the Shinegle adapter encodes)."""
        i = self.inp
        return {
            "mc.speed": self.speed_kmh,
            "mc.rpm": self.speed_ms * 3.6 * MOTOR_RPM_PER_KMH,
            "mc.direction": i.direction,
            "mc.mode": i.mode,
            "mc.throttle": i.throttle * 100,
            "mc.brake": i.brake > 0.05,
            "mc.ready": self.ready,
            "mc.limp": self.limp,
            "mc.batt_v": self.pack_voltage or ocv(self.soc),
            "mc.batt_a": self.pack_current,
            "mc.soc": self.soc,
            "mc.motor_temp": self.motor_temp,
            "mc.ctrl_temp": self.controller_temp,
            "mc.batt_temp": self.battery_temp,
            "mc.faults": sorted(self.faults),
            "mc.odometer": self.odometer_km,
        }
