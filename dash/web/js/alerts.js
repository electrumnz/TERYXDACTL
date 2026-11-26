// Alerts and warnings: control box and motor controller faults, plus things the dash watches
// itself (battery low, temps, 12V, tilt, lost link). Worst one shows as a banner along the
// bottom with a sound. "bad" alerts beep again every few seconds until you tap OK.
import { PICO_FAULTS, MC_FAULTS, faultText, asList } from "./text.js";
import { SHINEGLE_CODES } from "./shinegle-codes.js";
import { Sound } from "./sound.js";

export const SEV_RANK = { bad: 3, warn: 2, info: 1 };
const REPEAT_BAD_MS = 6000;
const LINK_GRACE_MS = 3000;   // don't shout about a blip in the link
const DCDC_HOLD_MS = 20000;   // 12V has to sit low this long while READY before we blame the DC-DC
const DCDC_MIN_V = 12.9;      // a DC-DC that's working holds the 12V battery up around 13.5-14.4 V

// Something has to be true for a while before it counts (a winch pull or a big load can
// pull the 12V down for a few seconds). timers keeps when each one started.
function held(timers, key, cond, now, ms) {
  if (!cond) { timers.delete(key); return false; }
  if (!timers.has(key)) timers.set(key, now);
  return now - timers.get(key) >= ms;
}

// A threshold with a little gap before it clears, so a value sitting on the line doesn't
// make the alert flick on and off.
function over(active, v, limit, gap) { return v != null && (active ? v > limit - gap : v >= limit); }
function under(active, v, limit, gap) { return v != null && (active ? v < limit + gap : v <= limit); }

/** Work out which alerts are on right now. Pure, so it's easy to test. */
export function evaluate(st, settings, prev = new Set(), now = Date.now(), linkLostAt = null, timers = new Map()) {
  const out = [];
  const add = (key, sev, text, code = key) => out.push({ key, sev, text, code });
  const was = (k) => prev.has(k);

  asList(st.get("pico.faults")).forEach((c) => add(`p:${c}`, (PICO_FAULTS[c] || {}).sev || "bad", faultText(c, PICO_FAULTS), c));
  asList(st.get("mc.faults")).forEach((c) => add(`m:${c}`, (MC_FAULTS[c] || {}).sev || "bad", faultText(c, MC_FAULTS), c));
  // The controller's own ErrorCode (LED flash count), in the words of its manual.
  const ec = st.get("mc.error_code") || 0;
  if (ec > 1 && st.get("mc.online") !== false) {
    const row = SHINEGLE_CODES[ec];
    add(`m:code${ec}`, "bad", row ? `Motor controller code ${ec}: ${row.text}.${row.fix ? ` ${row.fix}` : ""}` : `Motor controller code ${ec}.`, `code${ec}`);
  }

  const demo = st.get("link.demo");
  if (!demo && linkLostAt != null && now - linkLostAt > LINK_GRACE_MS) {
    if (!st.get("link.online")) add("a:no_server", "bad", "Lost the dash server. Controls on this screen won't work until it's back.");
    else if (!st.get("pico.online")) add("a:no_pico", "bad", "Control box isn't answering. 4WD, diff, lights, tray and winch won't respond.");
  }
  const mcOn = st.get("mc.online") !== false;

  if (mcOn) {
    const soc = st.get("mc.soc");
    if (under(was("a:soc_crit"), soc, 10, 2)) add("a:soc_crit", "bad", `Battery very low (${Math.round(soc)}%). Head home now.`);
    else if (under(was("a:soc_low"), soc, 20, 2)) add("a:soc_low", "warn", `Battery low (${Math.round(soc)}%). Time to head back.`);

    const mt = st.get("mc.motor_temp");
    if (over(was("a:motor_hot"), mt, 120, 5)) add("a:motor_hot", "bad", `Motor very hot (${Math.round(mt)}°C). Stop and let it cool.`);
    else if (over(was("a:motor_warm"), mt, 105, 5)) add("a:motor_warm", "warn", `Motor getting hot (${Math.round(mt)}°C). Go easy for a bit.`);
    const ct = st.get("mc.ctrl_temp");
    if (over(was("a:ctrl_hot"), ct, 85, 4)) add("a:ctrl_hot", "bad", `Motor controller very hot (${Math.round(ct)}°C). Stop and let it cool.`);
    else if (over(was("a:ctrl_warm"), ct, 75, 4)) add("a:ctrl_warm", "warn", `Motor controller getting hot (${Math.round(ct)}°C).`);
    const bt = st.get("mc.batt_temp");
    if (over(was("a:batt_hot"), bt, 55, 3)) add("a:batt_hot", "bad", `Traction battery very hot (${Math.round(bt)}°C). Stop and let it cool.`);
    else if (over(was("a:batt_warm"), bt, 47, 3)) add("a:batt_warm", "warn", `Traction battery warm (${Math.round(bt)}°C).`);
    if (st.get("mc.limp")) add("a:limp", "warn", "Motor controller has cut power back (limp mode).");
  }

  // Park brake (docs/park-brake.md): a foot pedal with a switch, no actuator. With it on the
  // control box blocks drive (relay 6 opens the pedal switch), so picking F or R is the
  // "trying to drive" moment: chime once and flash the lamp. Moving with it on (pulled on the
  // move, or the interlock turned off) gets the same shout.
  const moving = (st.get("mc.speed") || 0) > 2 || (st.get("mc.throttle") || 0) > 5;
  const dir = st.get("mc.direction");
  const inGear = (dir != null && dir !== "neutral") || st.get("in.reverse");
  if (st.get("in.park") && (inGear || moving)) {
    if (st.get("pico.park_block") && !moving)
      add("a:handbrake", "warn", "Release park brake. Drive is blocked while it's on.");
    else
      add("a:handbrake", "warn", "Park brake is still on. Let it off before you drive.");
  }

  const v12 = st.get("an.aux_12v");
  if (!asList(st.get("pico.faults")).includes("low_12v") && st.get("pico.online") !== false && under(was("a:12v"), v12, 11.8, 0.3))
    add("a:12v", "warn", `12V battery low (${v12.toFixed(1)} V). Check the DC-DC.`);
  // The car "battery light": READY, but the 12V isn't being charged. Not while the winch runs.
  const winching = st.get("winch.in") || st.get("winch.out") || st.get("in.winch_remote");
  const dcdcLow = mcOn && st.get("mc.ready") && !winching && st.get("pico.online") !== false && under(was("a:dcdc"), v12, DCDC_MIN_V, 0.2);
  if (held(timers, "dcdc", dcdcLow, now, DCDC_HOLD_MS) && !out.some((a) => a.key === "a:12v"))
    add("a:dcdc", "warn", `12V isn't charging (${v12.toFixed(1)} V while READY). Check the DC-DC and its fuse.`);

  // Tray up while driving: like a door open on the move.
  const tray = st.get("act.tray", "down");
  if (tray !== "down" && (st.get("mc.speed") || 0) > 3) add("a:tray_moving", "bad", "Tray isn't down and you're moving. Stop and lower it.");

  // Power steering (docs/power-steering-aqua.md): the control box powers the column with the key on.
  // steer.state comes from 0x718; older firmware only sends steer.on.
  const steerKey = st.get("in.ignition") !== false && st.get("pico.online") !== false && st.get("lock.state") !== "locked";
  const steer = st.get("steer.state");
  if (steerKey && steer === "manual")
    add("a:steer_off", "warn", "Power steering is turned off in settings, so steering is heavy.");
  else if (steerKey && steer === "ecu_fault")
    add("a:steer_fault", "bad", "Power steering has a fault and may be heavy. Stop, turn the key off and on. If it stays, check the column.");
  else if (steerKey && steer === "no_reply")
    add("a:steer_quiet", "warn", "Power steering isn't answering. Expect heavier steering. Check the steering fuse and its CAN plug.");
  else if (steerKey && steer === "bus_error")
    add("a:steer_bus", "warn", "Control box can't reach the power steering. Steering may be heavier. Check the steering CAN board.");
  else if (steerKey && steer === "limp")
    add("a:steer_limp", "info", "Power steering in limp mode (set in settings): assist on, not speed sensitive.");
  else if (steerKey && st.get("steer.on") === false)
    add("a:steer_off", "warn", "Power steering is off, so steering will be heavy. Check relay 9 and the steering fuse.");
  if (steerKey && st.get("steer.mode_pending"))
    add("a:steer_pending", "info", "Power steering change waits until you stop.");

  // Service reminder from the odometer (Settings > Display). 0 = off.
  const due = settings.get("service.dueKm") || 0, odo = st.get("mc.odometer");
  if (due > 0 && odo != null && odo >= due) add("a:service", "info", `Service due (${Math.round(due)} km). Set the next one in Settings > Display.`);

  // Winch motor heat: the dash's own guess (winchheat.js), as there's no sensor on the winch.
  const wh = st.get("dash.winch_heat");
  if (wh && wh.state === "rest") add("a:winch_rest", "bad", `Winch motor needs a rest. Leave it about ${Math.ceil(wh.restS / 60)} min to cool.`);
  else if (wh && wh.state === "warm") add("a:winch_warm", "warn", "Winch motor getting hot. Give it a rest soon.");

  // RC mode (docs/rc-beach-launch.md). With a Bluetooth pad paired to the Pi there's no
  // screen in your hand, so this banner is the remote's screen: state, gear and why it stopped.
  const rcs = st.get("rc.state");
  if (rcs && rcs !== "off") {
    const pad = st.get("rc.link") === "bt";
    const who = pad ? "gamepad" : { wifi: "phone", "4g": "phone over 4G", radio: "handheld" }[st.get("rc.link")] || "remote";
    const gear = { 1: "forward", "-1": "reverse", 0: "neutral" }[st.get("rc.dir") ?? 0];
    const cap = st.get("rc.cap_kmh");
    const why = { radio_lost: pad ? "gamepad lost, stopped on the brake" : "signal lost, stopped on the brake",
      deadman: pad ? "hold LB to drive" : "thumb on the stick to drive", estop: "E-STOP. Turn RC off and on to reset",
      recentre: "let the stick back to the middle", wheelspin: "digging in, stopped. Try 4WD and diff lock",
      stalled: "stuck, stopped", water: "water at the limit, no more reverse", control_box_lost: "control box not answering" }[st.get("rc.reason")] || st.get("rc.reason");
    const state = { armed: "ready", driving: "driving", hold: "holding", fault: "FAULT" }[rcs] || rcs;
    const text = `RC on (${who}): ${state}, ${gear}${cap ? `, ${cap} km/h max` : ""}${why ? `. ${why[0].toUpperCase()}${why.slice(1)}` : ""}.`;
    const lost = st.get("rc.reason") === "radio_lost" || rcs === "fault" || st.get("rc.reason") === "estop";
    add(lost ? "a:rc_stop" : "a:rc", lost ? "bad" : rcs === "hold" ? "warn" : "info", text);
  }

  const roll = st.get("pi.imu.roll"), pitch = st.get("pi.imu.pitch");
  const rw = settings.get("tilt.rollWarn"), rb = settings.get("tilt.rollBad");
  const pw = settings.get("tilt.pitchWarn"), pb = settings.get("tilt.pitchBad");
  if (roll != null) {
    const r = Math.abs(roll), side = roll > 0 ? "right" : "left";
    if (over(was("a:roll_bad"), r, rb, 2)) add("a:roll_bad", "bad", `Rollover risk: leaning ${Math.round(r)}° to the ${side}. Steer downhill.`);
    else if (over(was("a:roll_warn"), r, rw, 2)) add("a:roll_warn", "warn", `Steep side slope: ${Math.round(r)}° to the ${side}.`);
  }
  if (pitch != null) {
    const p = Math.abs(pitch), dir = pitch > 0 ? "nose up" : "nose down";
    if (over(was("a:pitch_bad"), p, pb, 2)) add("a:pitch_bad", "bad", `Very steep: ${Math.round(p)}° ${dir}.`);
    else if (over(was("a:pitch_warn"), p, pw, 2)) add("a:pitch_warn", "warn", `Steep: ${Math.round(p)}° ${dir}.`);
  }
  return out.sort((a, b) => SEV_RANK[b.sev] - SEV_RANK[a.sev]);
}

export class Alerts {
  constructor(store, settings) {
    this.store = store; this.settings = settings;
    this.active = [];
    this.keys = new Set();
    this.acked = new Set();
    this.lastBeep = 0;
    this.linkLostAt = null;
    this.subs = new Set();
    this.timers = new Map();
  }
  on(fn) { this.subs.add(fn); }

  tick(st, now = Date.now()) {
    const linkOk = st.get("link.online") && st.get("pico.online");
    if (linkOk) this.linkLostAt = null; else if (this.linkLostAt == null) this.linkLostAt = now;
    const list = evaluate(st, this.settings, this.keys, now, this.linkLostAt, this.timers);
    const keys = new Set(list.map((a) => a.key));
    const fresh = list.filter((a) => !this.keys.has(a.key));
    for (const k of this.acked) if (!keys.has(k)) this.acked.delete(k);   // cleared, so it can come back loud
    this.active = list; this.keys = keys;

    if (fresh.length) {
      const worst = fresh[0];
      Sound.play(worst.sev);
      this.lastBeep = now;
      this.subs.forEach((fn) => fn(fresh));
    } else {
      const loud = list.find((a) => a.sev === "bad" && !this.acked.has(a.key));
      if (loud && now - this.lastBeep > REPEAT_BAD_MS) { Sound.play("bad"); this.lastBeep = now; }
    }
  }

  /** Alerts not yet OK'd, worst first. */
  unacked() { return this.active.filter((a) => !this.acked.has(a.key)); }
  ack() { this.active.forEach((a) => this.acked.add(a.key)); }
}
