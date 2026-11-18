// Plain node checks for the warning lights and the new alerts. Run: node dash/tests/telltales_js.test.mjs
import assert from "node:assert/strict";
import { lampStates, LAMPS, LAMP_CHECK_MS, BELT_REMINDER_MS, TellTales } from "../web/js/telltales.js";
globalThis.window = { addEventListener() {} };   // sound.js hooks the first tap; no page here
const { evaluate } = await import("../web/js/alerts.js");

const st = (s) => ({ get: (k, d) => (s[k] === undefined ? d : s[k]) });
const settings = (s = {}) => ({ get: (p) => p.split(".").reduce((o, k) => (o == null ? o : o[k]),
  { tilt: { rollWarn: 25, rollBad: 32, pitchWarn: 28, pitchBad: 35 }, service: { dueKm: 0 }, ...s }) });
const base = { "link.online": true, "pico.online": true, "mc.online": true, "in.ignition": true, "steer.on": true, "an.aux_12v": 13.8 };
const lamps = (s, keys = [], now = 100000, keyOnAt = 0) => lampStates(st({ ...base, ...s }), settings(), new Set(keys), now, keyOnAt);
const keys = (s, set = {}, now = 0, timers = new Map()) => evaluate(st({ ...base, ...s }), settings(set), new Set(), now, null, timers).map((a) => a.key);

// ids are unique and each has a colour
assert.equal(new Set(LAMPS.map((l) => l.id)).size, LAMPS.length);

// lamp check: every lamp lit just after key-on, then only the real ones
assert.equal(Object.keys(lampStates(st(base), settings(), new Set(), 1000, 0)).length, LAMPS.length);
assert.deepEqual(Object.keys(lamps({})), []);

// belt reminder: on for 10 s after key-on (after the lamp check), like the stock Teryx
assert.ok(lamps({}, [], LAMP_CHECK_MS + 100, 0).belt);
assert.ok(!lamps({}, [], BELT_REMINDER_MS + 1, 0).belt);

// the basics
assert.equal(lamps({ "mc.ready": true }).ready.col, "ok");
assert.equal(lamps({ "in.park": true }).park.flash, false);
assert.equal(lamps({ "in.park": true }, ["a:handbrake"]).park.flash, true);
assert.ok(lamps({ "pico.faults": ["brake_pedal"] }).brake);
assert.ok(lamps({}, ["a:dcdc"]).charge12);
assert.ok(lamps({ "mc.error_code": 7 }).evfault);
assert.ok(!lamps({ "mc.error_code": 1 }).evfault);
assert.equal(lamps({}, ["a:motor_hot"]).temp.col, "bad");
assert.equal(lamps({}, ["a:batt_warm"]).temp.col, "warn");
assert.equal(lamps({}, ["a:soc_crit"]).lowbatt.flash, true);
assert.ok(lamps({ "mc.limp": true }).turtle);
assert.ok(lamps({ "steer.on": false }).steer);
assert.ok(!lamps({ "steer.on": false, "lock.state": "locked" }).steer);
assert.ok(!lamps({ "steer.on": undefined }).steer);                 // old firmware: no lamp
assert.equal(lamps({ "pico.online": false }).system.col, "bad");
assert.equal(lamps({ "pico.faults": ["tray_timeout"] }).system.col, "warn");
assert.equal(lamps({ "act.tray": "up" }).tray.col, "warn");
assert.equal(lamps({ "act.tray": "up" }, ["a:tray_moving"]).tray.col, "bad");
assert.ok(lamps({ "act.4wd": "4wd" }).fourwd);
assert.equal(lamps({ "act.4wd": "to_4wd" }).fourwd.flash, true);
assert.ok(lamps({ "an.diff_pos": 50, "act.diff_target": 50 }).diff);
assert.ok(lamps({ "lamp.head_l_low": 255, "lamp.head_l_high": 0 }).lowbeam);
assert.ok(lamps({ "lamp.head_r_high": 255 }).highbeam);
assert.equal(lamps({ "lamp.head_r_high": 255 }).highbeam.col, "hi");
assert.ok(lamps({ "light.head": "high" }).highbeam);                // no lamp echo yet: what we asked for
assert.ok(lamps({ "light.front_2": 128 }).bars);
assert.ok(lamps({ "light.beacon": 255 }).beacon);
assert.ok(lamps({ "in.trailer": true }).trailer);
assert.ok(lamps({ "winch.armed": true }).winch);
assert.ok(lamps({ "rc.state": "armed" }).rc);
assert.ok(lamps({ "pico.throttle_hold": true }).hold);

// render keeps the fixed order
const tt = new TellTales();
const html = tt.render(lamps({ "in.trailer": true, "mc.ready": true, "in.park": true }));
assert.ok(html.indexOf('data-lamp="ready"') < html.indexOf('data-lamp="park"'));
assert.ok(html.indexOf('data-lamp="park"') < html.indexOf('data-lamp="trailer"'));

// new alerts
assert.ok(keys({ "mc.error_code": 13 }).includes("m:code13"));
const code = evaluate(st({ ...base, "mc.error_code": 13 }), settings(), new Set(), 0).find((a) => a.key === "m:code13");
assert.match(code.text, /code 13: Main contactor or brake fault/);
assert.ok(!keys({ "mc.error_code": 1 }).some((k) => k.startsWith("m:code")));
assert.ok(keys({ "act.tray": "up", "mc.speed": 10 }).includes("a:tray_moving"));
assert.ok(!keys({ "act.tray": "up", "mc.speed": 0 }).includes("a:tray_moving"));
assert.ok(keys({ "steer.on": false }).includes("a:steer_off"));
assert.ok(keys({ "mc.odometer": 1000 }, { service: { dueKm: 1000 } }).includes("a:service"));
assert.ok(!keys({ "mc.odometer": 999 }, { service: { dueKm: 1000 } }).includes("a:service"));
assert.ok(!keys({ "mc.odometer": 5000 }).includes("a:service"));            // 0 = off
// DC-DC: READY with the 12V low has to last 20 s, and not while winching
const timers = new Map(), low = { "mc.ready": true, "an.aux_12v": 12.4 };
assert.ok(!keys(low, {}, 0, timers).includes("a:dcdc"));
assert.ok(!keys(low, {}, 19000, timers).includes("a:dcdc"));
assert.ok(keys(low, {}, 21000, timers).includes("a:dcdc"));
const t2 = new Map();
keys({ ...low, "winch.in": true }, {}, 0, t2);
assert.ok(!keys({ ...low, "winch.in": true }, {}, 30000, t2).includes("a:dcdc"));
assert.ok(!keys({ "mc.ready": true, "an.aux_12v": 13.9 }, {}, 30000, new Map()).includes("a:dcdc"));
// brake pedal fault has proper words now
const bp = evaluate(st({ ...base, "pico.faults": ["brake_pedal"] }), settings(), new Set(), 0).find((a) => a.key === "p:brake_pedal");
assert.match(bp.text, /brakes still work/);

console.log("telltales ok");
