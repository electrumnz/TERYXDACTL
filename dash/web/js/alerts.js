// Alerts and warnings: control box and motor controller faults, plus things the dash watches
// itself (battery low, temps, 12V, tilt, lost link). Worst one shows as a banner along the
// bottom with a sound. "bad" alerts beep again every few seconds until you tap OK.
import { PICO_FAULTS, MC_FAULTS, faultText, asList } from "./text.js";
import { Sound } from "./sound.js";

export const SEV_RANK = { bad: 3, warn: 2, info: 1 };
const REPEAT_BAD_MS = 6000;
const LINK_GRACE_MS = 3000;   // don't shout about a blip in the link

// A threshold with a little gap before it clears, so a value sitting on the line doesn't
// make the alert flick on and off.
function over(active, v, limit, gap) { return v != null && (active ? v > limit - gap : v >= limit); }
function under(active, v, limit, gap) { return v != null && (active ? v < limit + gap : v <= limit); }

/** Work out which alerts are on right now. Pure, so it's easy to test. */
export function evaluate(st, settings, prev = new Set(), now = Date.now(), linkLostAt = null) {
  const out = [];
  const add = (key, sev, text, code = key) => out.push({ key, sev, text, code });
  const was = (k) => prev.has(k);

  asList(st.get("pico.faults")).forEach((c) => add(`p:${c}`, (PICO_FAULTS[c] || {}).sev || "bad", faultText(c, PICO_FAULTS), c));
  asList(st.get("mc.faults")).forEach((c) => add(`m:${c}`, (MC_FAULTS[c] || {}).sev || "bad", faultText(c, MC_FAULTS), c));

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

  // Handbrake left on: only worth a shout once you try to drive with it.
  const moving = (st.get("mc.speed") || 0) > 2 || (st.get("mc.throttle") || 0) > 5;
  if (st.get("in.park") && st.get("mc.direction") !== "neutral" && moving)
    add("a:handbrake", "warn", "Handbrake is still on. Let it off before you drive.");

  const v12 = st.get("an.aux_12v");
  if (!asList(st.get("pico.faults")).includes("low_12v") && st.get("pico.online") !== false && under(was("a:12v"), v12, 11.8, 0.3))
    add("a:12v", "warn", `12V battery low (${v12.toFixed(1)} V). Check the DC-DC.`);

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
  }
  on(fn) { this.subs.add(fn); }

  tick(st, now = Date.now()) {
    const linkOk = st.get("link.online") && st.get("pico.online");
    if (linkOk) this.linkLostAt = null; else if (this.linkLostAt == null) this.linkLostAt = now;
    const list = evaluate(st, this.settings, this.keys, now, this.linkLostAt);
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
