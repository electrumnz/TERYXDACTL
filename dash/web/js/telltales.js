// Warning lights (tell-tales): the row of little lamps every car dash has.
//
// Each lamp has a fixed place in the row, a fixed colour meaning (red = stop or act now,
// amber = take care, green = on and working, blue = high beam), and the usual symbol
// shape, drawn here from scratch. Only lit lamps show, in that fixed order. At key-on
// every lamp lights for a moment (the lamp check), like a real cluster, so you can see
// they all work and learn where each one lives.
//
// The text behind each lamp lives in alerts.js (the banner): the lamp is the glance,
// the banner says what to do. Thresholds come from there too, so they can't disagree.
import { asList } from "./text.js";

export const LAMP_CHECK_MS = 2500;
export const BELT_REMINDER_MS = 10000;   // the stock Teryx belt light: about 10 s at key-on

// Symbols, 24 x 24, stroke drawn in currentColor. Our own drawings of the usual shapes.
const S = {
  ready: '<text x="12" y="16" text-anchor="middle" font-size="9" font-weight="800" fill="currentColor" stroke="none" font-family="Barlow Condensed, sans-serif">READY</text>',
  park: '<circle cx="12" cy="12" r="7"/><path d="M4.5 5.5a10 10 0 0 0 0 13M19.5 5.5a10 10 0 0 1 0 13"/><path d="M10 16V8h2.6a2.2 2.2 0 0 1 0 4.4H10"/>',
  brake: '<circle cx="12" cy="12" r="7"/><path d="M4.5 5.5a10 10 0 0 0 0 13M19.5 5.5a10 10 0 0 1 0 13"/><path d="M12 8.2v4.6"/><path d="M12 15.6v.2"/>',
  belt: '<circle cx="11" cy="4.5" r="1.9"/><path d="M7.5 21v-7.5a3.5 3.5 0 0 1 7 0V21"/><path d="M8 9l8.5 9"/><path d="M15 20.5h4"/>',
  charge12: '<rect x="3" y="7" width="18" height="12" rx="1.5"/><path d="M7 7V5h3v2M14 7V5h3v2"/><path d="M6.5 13h3M16.5 11.5v3M15 13h3"/>',
  evfault: '<path d="M3 15l2-5.5A2 2 0 0 1 6.9 8h10.2a2 2 0 0 1 1.9 1.5L21 15v3H3z"/><path d="M6 18v2M18 18v2"/><path d="M12 9.6v3.2"/><path d="M12 15.2v.2"/>',
  lowbatt: '<rect x="3" y="7" width="16" height="11" rx="1.5"/><path d="M19 10.5h2v4h-2"/><path d="M6 15.5h2.5"/><path d="M13 9.5l-2 3h3l-2 3"/>',
  temp: '<path d="M12 3a2 2 0 0 0-2 2v8.3a4 4 0 1 0 4 0V5a2 2 0 0 0-2-2z"/><path d="M12 9v6.5"/><path d="M15.5 6h3M15.5 9h3"/>',
  turtle: '<path d="M4 15c0-4 3.6-7 8-7s8 3 8 7z"/><path d="M20 13.5h1.5a1.5 1.5 0 0 0 0-3H20"/><path d="M6.5 15v3M17.5 15v3"/><path d="M9 8.6l1.6 3.4M15 8.6l-1.6 3.4M7 12h10"/>',
  steer: '<circle cx="11" cy="12" r="7.5"/><circle cx="11" cy="12" r="2"/><path d="M3.8 10.5l5.4 1M18.2 10.5l-5.4 1M11 14v5.5"/><path d="M21.5 7v5"/><path d="M21.5 15v.2"/>',
  system: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3.5 17.5a1.4 1.4 0 0 0 2 2l5.8-5.8a4 4 0 0 0 5.4-5.4l-2.4 2.4-2-2z"/><path d="M19.5 14v4"/><path d="M19.5 20.6v.2"/>',
  tilt: '<path d="M3 20h18L6 7z"/><path d="M8.5 13.5l2.8-1.2 2.6 1.7"/><circle cx="9.2" cy="15.6" r="1.2"/><circle cx="13.6" cy="15.9" r="1.2"/>',
  fourwd: '<text x="12" y="16" text-anchor="middle" font-size="10" font-weight="800" fill="currentColor" stroke="none" font-family="Barlow Condensed, sans-serif">4WD</text>',
  diff: '<circle cx="6" cy="12" r="2.4"/><circle cx="18" cy="12" r="2.4"/><path d="M8.4 12h7.2"/><path d="M6 4v5.6M6 14.4V20M18 4v5.6M18 14.4V20"/><path d="M11 9.5h2v5h-2z"/>',
  lowbeam: '<path d="M11 5.5c-4 0-6 3-6 6.5s2 6.5 6 6.5h1V5.5z"/><path d="M15 8l5 1.5M15 12l5 1.5M15 16l5 1.5"/>',
  highbeam: '<path d="M11 5.5c-4 0-6 3-6 6.5s2 6.5 6 6.5h1V5.5z"/><path d="M15 7.5h6M15 10.5h6M15 13.5h6M15 16.5h6"/>',
  bars: '<rect x="2.5" y="8" width="11" height="8" rx="1.5"/><path d="M5.5 8v8M8 8v8M10.5 8v8"/><path d="M16 9l5-1.5M16 12h5M16 15l5 1.5"/>',
  beacon: '<path d="M7 18v-6a5 5 0 0 1 10 0v6z"/><path d="M5 20.5h14"/><path d="M12 3v2M4.5 6l1.4 1.4M19.5 6l-1.4 1.4"/>',
  tray: '<path d="M3 18h18"/><path d="M5 18l2-6"/><path d="M6 12.5l13-5 1 3-12.5 4.6z"/><circle cx="16.5" cy="18" r="0.4"/>',
  winch: '<rect x="3" y="8" width="10" height="9" rx="1.5"/><path d="M6 8v9M10 8v9"/><path d="M13 12.5h4.5a2.5 2.5 0 0 1 0 5"/><path d="M21 9.5v3"/>',
  trailer: '<path d="M2.5 16h14V8h-14z"/><path d="M16.5 14h5"/><circle cx="8" cy="17.5" r="1.8"/>',
  hold: '<circle cx="12" cy="12" r="8"/><path d="M9.5 8.5v7M14.5 8.5v7"/>',
  rc: '<text x="12" y="16" text-anchor="middle" font-size="10" font-weight="800" fill="currentColor" stroke="none" font-family="Barlow Condensed, sans-serif">RC</text>',
  service: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3.5 17.5a1.4 1.4 0 0 0 2 2l5.8-5.8a4 4 0 0 0 5.4-5.4l-2.4 2.4-2-2z"/>',
};

// Fixed order, left to right: driving-critical red ones first, then amber, then "on" lamps.
// col is the colour the lamp normally lights in; a state can ask for another.
export const LAMPS = [
  { id: "ready",    col: "ok",   name: "Ready to drive" },
  { id: "park",     col: "bad",  name: "Park brake on" },
  { id: "brake",    col: "bad",  name: "Brake system fault" },
  { id: "belt",     col: "bad",  name: "Seat belts" },
  { id: "charge12", col: "bad",  name: "12V battery not charging or low" },
  { id: "evfault",  col: "bad",  name: "Motor controller fault" },
  { id: "temp",     col: "bad",  name: "Motor, controller or battery hot" },
  { id: "lowbatt",  col: "warn", name: "Traction battery low" },
  { id: "turtle",   col: "warn", name: "Power cut back" },
  { id: "steer",    col: "warn", name: "Power steering off" },
  { id: "system",   col: "warn", name: "Control box fault" },
  { id: "tilt",     col: "warn", name: "Steep slope" },
  { id: "tray",     col: "warn", name: "Tray not down" },
  { id: "service",  col: "warn", name: "Service due" },
  { id: "fourwd",   col: "ok",   name: "4WD" },
  { id: "diff",     col: "warn", name: "Front diff lock" },
  { id: "hold",     col: "ok",   name: "Throttle held for a shift" },
  { id: "winch",    col: "warn", name: "Winch armed" },
  { id: "rc",       col: "warn", name: "RC mode" },
  { id: "lowbeam",  col: "ok",   name: "Headlights" },
  { id: "highbeam", col: "hi",   name: "High beam" },
  { id: "bars",     col: "ok",   name: "Light bars" },
  { id: "beacon",   col: "warn", name: "Beacon" },
  { id: "trailer",  col: "ok",   name: "Trailer plugged in" },
];

export function lampSvg(id) {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${S[id] || ""}</svg>`;
}

/**
 * Which lamps are lit. Pure, so it's easy to test.
 * alertKeys: keys of the alerts on right now (alerts.js), so thresholds live in one place.
 * keyOnAt: when the key last went on (ms), for the lamp check and the belt reminder.
 * Returns { id: { col, flash } } for each lit lamp.
 */
export function lampStates(st, settings, alertKeys = new Set(), now = Date.now(), keyOnAt = null) {
  const on = {};
  const lit = (id, col, flash = false) => { on[id] = { col: col || LAMPS.find((l) => l.id === id).col, flash }; };
  const has = (k) => alertKeys.has(k);
  const pf = asList(st.get("pico.faults"));
  const picoOn = st.get("pico.online") !== false && st.get("link.online") !== false;
  const keyOn = st.get("in.ignition") !== false;

  if (keyOnAt != null && now - keyOnAt < LAMP_CHECK_MS) {
    LAMPS.forEach((l) => lit(l.id, l.col));
    return on;
  }

  if (st.get("mc.ready")) lit("ready");
  if (st.get("in.park")) lit("park", "bad", has("a:handbrake"));
  if (pf.includes("brake_pedal") || st.get("regen.state") === "sensor_fault") lit("brake");
  if (keyOnAt != null && now - keyOnAt < BELT_REMINDER_MS) lit("belt");
  if (has("a:12v") || has("a:dcdc") || pf.includes("low_12v")) lit("charge12");
  const mcf = asList(st.get("mc.faults"));
  if (mcf.length || (st.get("mc.error_code") || 0) > 1) lit("evfault");
  if (["a:motor_hot", "a:ctrl_hot", "a:batt_hot"].some(has)) lit("temp", "bad", true);
  else if (["a:motor_warm", "a:ctrl_warm", "a:batt_warm"].some(has)) lit("temp", "warn");
  if (has("a:soc_crit")) lit("lowbatt", "bad", true);
  else if (has("a:soc_low")) lit("lowbatt", "warn");
  if (st.get("mc.limp")) lit("turtle");
  if (keyOn && picoOn && st.get("steer.on") === false && st.get("lock.state") !== "locked") lit("steer");
  if (!picoOn || st.get("pico.state") === "failsafe") lit("system", "bad", true);
  else if (pf.some((f) => !["low_12v", "brake_pedal"].includes(f))) lit("system", "warn");   // own lamps for those two
  if (has("a:roll_bad") || has("a:pitch_bad")) lit("tilt", "bad", true);
  else if (has("a:roll_warn") || has("a:pitch_warn")) lit("tilt", "warn");
  const tray = st.get("act.tray", "down");
  if (tray !== "down") lit("tray", tray === "fault" || has("a:tray_moving") ? "bad" : "warn", has("a:tray_moving") || tray === "raising" || tray === "lowering");
  if (has("a:service")) lit("service");

  const fw = st.get("act.4wd", "2wd");
  if (fw === "fault") lit("fourwd", "warn", true);
  else if (fw.startsWith("to_") || st.get("act.4wd_wait")) lit("fourwd", "ok", true);
  else if (fw === "4wd") lit("fourwd", "ok");
  const d = st.get("an.diff_pos", 0) || 0;
  if (d > 2 || st.get("act.diff_wait")) lit("diff", "warn", !!st.get("act.diff_wait") || Math.abs((st.get("act.diff_target") ?? d) - d) > 3);
  if (st.get("pico.throttle_hold")) lit("hold");
  if (st.get("winch.armed") || st.get("winch.in") || st.get("winch.out") || st.get("in.winch_remote"))
    lit("winch", "warn", !!(st.get("winch.in") || st.get("winch.out") || st.get("in.winch_remote")));
  const rcs = st.get("rc.state");
  if (rcs && rcs !== "off") lit("rc", rcs === "fault" ? "bad" : "warn", rcs === "driving");

  // Lights: what the control box says is actually lit, falling back to what we asked for.
  const lamp = (k) => st.get(`lamp.${k}`);
  const head = st.get("light.head", "off");
  const low = ["head_l_low", "head_r_low"].some((k) => lamp(k) > 0) || (lamp("head_l_low") == null && head === "low");
  const high = ["head_l_high", "head_r_high"].some((k) => lamp(k) > 0) || (lamp("head_l_high") == null && head === "high");
  if (low) lit("lowbeam");
  if (high) lit("highbeam");
  if (["light.front_1", "light.front_2", "light.front_3", "light.front_4"].some((k) => (st.get(k) || 0) > 0)) lit("bars");
  if ((st.get("light.beacon") || 0) > 0 || (st.get("light.beacon_white") || 0) > 0) lit("beacon");
  if (st.get("in.trailer")) lit("trailer");
  return on;
}

/** Keeps the key-on time and turns lampStates into HTML for the drive screen. */
export class TellTales {
  constructor() { this.keyOnAt = null; this.wasOn = false; this.html = ""; }

  tick(st, settings, alertKeys, now = Date.now()) {
    const keyOn = st.get("in.ignition") !== false;
    if (keyOn && !this.wasOn) this.keyOnAt = now;   // first update after boot counts as key-on
    this.wasOn = keyOn;
    return lampStates(st, settings, alertKeys, now, this.keyOnAt);
  }

  render(states) {
    return LAMPS.filter((l) => states[l.id]).map((l) => {
      const s = states[l.id];
      return `<span class="tt tt-${s.col}${s.flash ? " tt-flash" : ""}" data-lamp="${l.id}" title="${l.name}">${lampSvg(l.id)}</span>`;
    }).join("");
  }
}
