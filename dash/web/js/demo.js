// In-browser demo vehicle, so the dash can be opened with ?demo=drive on any computer with no server.
// The real mock data comes from the simulator (python -m teryx run --ui dash/web). This is a light
// copy of it with the same state keys and a rough copy of the control box's safety rules,
// so refusals and timers can be seen in demo mode too.
//
// Scenarios: ?demo=drive (driving a loop), ?demo=park (stopped, for winch/tray),
//            ?demo=reverse, ?demo=faults

const LIGHT_IDS = ["light.front_1", "light.front_2", "light.front_3", "light.front_4", "light.interior"];

export class DemoVehicle {
  constructor(scenario = "drive") {
    this.scenario = scenario;
    this.t = 0;
    this.req = { lights: Object.fromEntries(LIGHT_IDS.map((k) => [k, 0])), effect: "none", rear: "auto", fourwd: 0, diff: 0, armed: false };
    this.holds = { "act.tray": { v: 0, at: 0 }, winch: { v: 0, at: 0 } };
    this.rejectCount = 0;
    this.s = {
      "mc.online": true, "pico.online": true, "pico.state": "run", "pico.faults": [], "pico.reject": "none", "pico.reject_count": 0,
      "mc.speed": 0, "mc.batt_v": 78.2, "mc.batt_a": 0, "mc.soc": 82, "mc.motor_temp": 38, "mc.ctrl_temp": 33,
      "mc.throttle": 0, "mc.direction": "neutral", "mc.mode": "normal", "mc.faults": [],
      "in.ignition": true, "in.brake": false, "in.reverse": false, "in.tray_down": true, "in.tray_up": false,
      "in.winch_remote": false, "in.park": true,
      "an.diff_pos": 0, "an.aux_12v": 12.9, "an.4wd_current": 0, "an.tray_current": 0, "an.diff_current": 0,
      "light.rear": false, "light.effect": "none", "trailer.tail": false, "trailer.brake": false,
      "winch.in": false, "winch.out": false, "winch.isolator": false, "winch.armed": false,
      "aux.accessory": true, "power.hold": true,
      "act.4wd": "2wd", "act.diff_target": 0, "act.tray": "down", "act.tray_pct": 0,
      "pi.imu.roll": 0, "pi.imu.pitch": 0,
    };
    LIGHT_IDS.forEach((k) => (this.s[k] = 0));
    this.fourwdTimer = 0;
    this.armedIdle = 0;
  }

  start() {
    this.last = performance.now();
    this.timer = setInterval(() => this.step(), 50);
  }

  reject(code) { this.rejectCount++; this.s["pico.reject"] = code; this.s["pico.reject_count"] = this.rejectCount; }

  receive(msg) {
    const s = this.s, spd = s["mc.speed"];
    if (msg.type === "request") {
      const { id, value } = msg;
      if (id.startsWith("light.front") || id === "light.interior") this.req.lights[id] = value;
      else if (id === "light.effect") this.req.effect = value;
      else if (id === "light.rear") this.req.rear = value;
      else if (id === "act.4wd") {
        if (spd >= 5) return this.reject("too_fast");
        if (value !== this.req.fourwd) { this.req.fourwd = value; this.fourwdTimer = 1.4; s["act.4wd"] = value ? "to_4wd" : "to_2wd"; }
      } else if (id === "act.diff") {
        if (spd >= 15) return this.reject("too_fast");
        this.req.diff = value; s["act.diff_target"] = value;
      } else if (id === "winch.armed") {
        if (value && spd > 0.5) return this.reject("not_stopped");
        this.req.armed = !!value; this.armedIdle = 0;
      }
    } else if (msg.type === "hold") {
      const h = this.holds[msg.id]; if (!h) return;
      if (msg.value !== 0) {
        if (spd > 0.5) { if (h.v === 0) this.reject("not_stopped"); h.v = 0; return; }
        if (msg.id === "winch" && !this.req.armed) { if (h.v === 0) this.reject("not_armed"); return; }
      }
      h.v = msg.value; h.at = performance.now();
    }
  }

  scenarioDrive(dt) {
    const s = this.s, t = this.t;
    if (this.scenario === "park" || this.scenario === "faults") {
      s["mc.speed"] = 0; s["mc.direction"] = "neutral"; s["mc.throttle"] = 0; s["in.park"] = true;
      s["mc.batt_a"] = 1.2;
      if (this.scenario === "faults") {
        s["pico.faults"] = ["tray_overcurrent", "low_12v"]; s["mc.faults"] = ["motor_over_temp"];
        s["mc.motor_temp"] = 128; s["an.aux_12v"] = 11.4;
      }
      return;
    }
    if (this.scenario === "reverse") {
      s["mc.direction"] = "reverse"; s["in.reverse"] = true; s["in.park"] = false;
      s["mc.speed"] = 3 + Math.sin(t / 2) * 1.5; s["mc.throttle"] = 12; s["mc.batt_a"] = 18;
      return;
    }
    // A 60 s loop: pull away, cruise, climb, coast with regen, stop.
    const c = t % 60;
    let target, thr;
    if (c < 4) { target = 0; thr = 0; }
    else if (c < 14) { target = 35; thr = 55; }
    else if (c < 26) { target = 42 + Math.sin(c) * 3; thr = 40; }
    else if (c < 36) { target = 18; thr = 70; s["pi.imu.pitch"] = 14; }
    else if (c < 48) { target = 30; thr = 30; s["pi.imu.pitch"] = 0; }
    else if (c < 56) { target = 0; thr = 0; }
    else { target = 0; thr = 0; }
    const spd = s["mc.speed"];
    const a = target > spd ? Math.min(6 * dt * 3, target - spd) : Math.max(-8 * dt * 3, target - spd);
    s["mc.speed"] = Math.max(0, spd + a);
    s["mc.throttle"] = target > spd + 1 ? thr : 0;
    s["mc.direction"] = s["mc.speed"] > 0.3 || target > 0 ? "forward" : "neutral";
    s["in.park"] = s["mc.speed"] < 0.3 && target === 0;
    s["in.brake"] = a < -0.3;
    // Current: draw when accelerating or climbing, regen when slowing.
    const want = a > 0.05 ? 60 + thr * 1.6 : a < -0.05 ? -35 : s["mc.speed"] > 1 ? 25 + thr : 1;
    s["mc.batt_a"] += (want - s["mc.batt_a"]) * Math.min(1, dt * 4);
    s["pi.imu.roll"] = Math.sin(t / 3) * 6;
  }

  step() {
    const now = performance.now(), dt = Math.min(0.2, (now - this.last) / 1000); this.last = now; this.t += dt;
    const s = this.s, r = this.req;
    this.scenarioDrive(dt);

    // Battery
    s["mc.batt_v"] = 78.5 - s["mc.batt_a"] * 0.03 - (100 - s["mc.soc"]) * 0.05;
    s["mc.soc"] = Math.max(5, s["mc.soc"] - Math.max(0, s["mc.batt_a"]) * dt * 0.00012);
    if (this.scenario !== "faults") {
      s["mc.motor_temp"] += ((40 + Math.abs(s["mc.batt_a"]) * 0.35) - s["mc.motor_temp"]) * dt * 0.05;
      s["mc.ctrl_temp"] += ((32 + Math.abs(s["mc.batt_a"]) * 0.2) - s["mc.ctrl_temp"]) * dt * 0.05;
      s["an.aux_12v"] = 12.9 + Math.sin(this.t / 5) * 0.05;
    }

    // Lights with effects
    const fx = r.effect, ph = this.t;
    LIGHT_IDS.forEach((k, i) => {
      let v = r.lights[k];
      if (v > 0 && k !== "light.interior") {
        if (fx === "strobe") v = Math.floor(ph * 8) % 2 ? v : 0;
        else if (fx === "chase") v = Math.floor(ph * 6) % 4 === i ? v : 0;
        else if (fx === "breathe") v = Math.round(v * (0.35 + 0.65 * (0.5 + 0.5 * Math.sin(ph * 4))));
        else if (fx === "outside_only") v = i === 0 || i === 3 ? v : 0;
        else if (fx === "inside_only") v = i === 1 || i === 2 ? v : 0;
      }
      s[k] = v;
    });
    s["light.effect"] = fx;
    s["light.rear"] = r.rear === "on" || (r.rear === "auto" && s["in.reverse"]);
    s["trailer.tail"] = LIGHT_IDS.slice(0, 4).some((k) => r.lights[k] > 0);
    s["trailer.brake"] = s["in.brake"];

    // 4WD actuator runs to its end stop
    if (this.fourwdTimer > 0) {
      this.fourwdTimer -= dt; s["an.4wd_current"] = 3.2;
      if (this.fourwdTimer <= 0) { s["act.4wd"] = r.fourwd ? "4wd" : "2wd"; s["an.4wd_current"] = 0; }
    }

    // Diff closes in on its target at ~40 %/s
    const dp = s["an.diff_pos"], dtgt = r.diff;
    if (Math.abs(dtgt - dp) > 0.5) { s["an.diff_pos"] = dp + Math.sign(dtgt - dp) * Math.min(40 * dt, Math.abs(dtgt - dp)); s["an.diff_current"] = 2.1; }
    else { s["an.diff_pos"] = dtgt; s["an.diff_current"] = 0; }

    // Hold-to-run: stops after 300 ms of silence
    for (const h of Object.values(this.holds)) if (h.v && now - h.at > 300) h.v = 0;
    const moving = s["mc.speed"] > 0.5;
    if (moving) { this.holds["act.tray"].v = 0; this.holds.winch.v = 0; }

    // Tray
    const tv = this.holds["act.tray"].v; let pct = s["act.tray_pct"];
    if (tv > 0 && pct < 100) { pct = Math.min(100, pct + 9 * dt); s["act.tray"] = "raising"; s["an.tray_current"] = 6.5; }
    else if (tv < 0 && pct > 0) { pct = Math.max(0, pct - 11 * dt); s["act.tray"] = "lowering"; s["an.tray_current"] = 3.0; }
    else { s["act.tray"] = pct >= 100 ? "up" : pct <= 0 ? "down" : "mid"; s["an.tray_current"] = 0; }
    s["act.tray_pct"] = pct; s["in.tray_up"] = pct >= 100; s["in.tray_down"] = pct <= 0;

    // Winch
    if (r.armed && moving) { r.armed = false; this.reject("not_stopped"); }
    const wv = this.holds.winch.v;
    if (r.armed) { this.armedIdle = wv ? 0 : this.armedIdle + dt; if (this.armedIdle > 120) r.armed = false; }
    s["winch.armed"] = r.armed; s["winch.isolator"] = r.armed;
    s["winch.in"] = r.armed && wv > 0; s["winch.out"] = r.armed && wv < 0;
    s["winch.idle_s"] = this.armedIdle;

    this.onState && this.onState({ ...s });
  }
}
