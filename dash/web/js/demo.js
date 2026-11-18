// In-browser demo vehicle, so the dash can be opened with ?demo=drive on any computer with no server.
// The real mock data comes from the simulator (python -m teryx run --ui dash/web). This is a light
// copy of it with the same state keys and a rough copy of the control box's safety rules,
// so refusals and timers can be seen in demo mode too.
//
// Scenarios: ?demo=drive (driving a loop), ?demo=park (stopped, for winch/tray),
//            ?demo=reverse, ?demo=faults. Add &trailer=1 for a trailer plugged in.

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
      // Trailer plugged in: add &trailer=1 to the URL to try the trailer camera.
      "in.trailer": (() => { try { return new URLSearchParams(location.search).has("trailer"); } catch { return false; } })(),
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

  diffBusy() { return !!this.waitD || Math.abs(this.req.diff - this.s["an.diff_pos"]) > 0.5; }
  start4wd(value) { this.req.fourwd = value; this.fourwdTimer = 1.4; this.s["act.4wd"] = value ? "to_4wd" : "to_2wd"; }

  reject(code) { this.rejectCount++; this.s["pico.reject"] = code; this.s["pico.reject_count"] = this.rejectCount; }

  receive(msg) {
    const s = this.s, spd = s["mc.speed"];
    if (msg.type === "request") {
      const { id, value } = msg;
      if (id.startsWith("light.front") || id === "light.interior") this.req.lights[id] = value;
      else if (id === "light.effect") this.req.effect = value;
      else if (id === "light.rear") this.req.rear = value;
      else if (id === "act.4wd") {
        // Like the control box: too fast = wait (up to 10 s) for a stop; asking for what's there cancels
        this.wait4 = null; s["act.4wd_wait"] = false;
        if (value === this.req.fourwd) return;
        if (this.diffBusy()) return this.reject("busy");
        if (spd >= 1) { this.wait4 = { value, at: this.t }; s["act.4wd_wait"] = true; return; }
        this.start4wd(value);
      } else if (id === "act.diff") {
        this.waitD = null; s["act.diff_wait"] = false;
        const adding = value > s["an.diff_pos"] + 2;
        if (adding && (this.fourwdTimer > 0 || this.wait4)) return this.reject("busy");
        if (adding && spd >= 15) { this.waitD = { value, at: this.t }; s["act.diff_wait"] = true; s["act.diff_target"] = value; return; }
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
      // Timed winch pull: like the control box, stop on time even if the holds keep coming.
      if (msg.id === "winch") {
        const secs = msg.value ? (msg.secs || 0) : 0;
        if (msg.value !== h.v || !secs) { h.secs = secs; h.from = null; h.done = false; }
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

    // Waiting 4WD / diff changes: go once the speed is right, give up after 10 s
    const spd = s["mc.speed"];
    if (this.wait4) {
      if (spd < 1 && !this.diffBusy()) { this.start4wd(this.wait4.value); this.wait4 = null; s["act.4wd_wait"] = false; }
      else if (this.t - this.wait4.at > 10) { this.wait4 = null; s["act.4wd_wait"] = false; this.reject("wait_timeout"); }
    }
    if (this.waitD) {
      if (spd < 15) { r.diff = this.waitD.value; this.waitD = null; s["act.diff_wait"] = false; }
      else if (this.t - this.waitD.at > 10) { this.waitD = null; s["act.diff_wait"] = false; s["act.diff_target"] = r.diff; this.reject("wait_timeout"); }
    }
    // Throttle held while 4WD shifts from a standstill
    s["pico.throttle_hold"] = this.fourwdTimer > 0 && spd < 0.5;

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
    const wh = this.holds.winch;
    if (wh.secs && wh.v && !wh.done) {
      if (wh.from == null) wh.from = now;
      if (now - wh.from >= Math.min(wh.secs, 30) * 1000) wh.done = true;
    }
    const wv = wh.secs && wh.done ? 0 : wh.v;
    if (r.armed) { this.armedIdle = wv ? 0 : this.armedIdle + dt; if (this.armedIdle > 120) r.armed = false; }
    s["winch.armed"] = r.armed; s["winch.isolator"] = r.armed;
    s["winch.in"] = r.armed && wv > 0; s["winch.out"] = r.armed && wv < 0;
    s["winch.idle_s"] = this.armedIdle;
    // The 12V battery sags while the winch pulls (roughly what the sim does)
    const wa = s["winch.in"] ? 180 : s["winch.out"] ? 60 : 0;
    if (wa || this.scenario === "park") {
      const v12 = s["an.aux_12v"] ?? 12.9;
      s["an.aux_12v"] = v12 + ((12.9 - wa * 0.006) - v12) * Math.min(1, dt * 5);
    }

    this.onState && this.onState({ ...s });
  }
}
