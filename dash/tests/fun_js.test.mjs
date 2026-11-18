// Plain node checks for the Fun screen's pure code. Run: node dash/tests/fun_js.test.mjs
import assert from "node:assert/strict";
import { campLoadW, campBudgetWh, campHoursLeft, fmtHours, restSoc, CAMP_DEFAULTS } from "../web/js/fun/campcalc.js";
import { isParked, whyNotParked } from "../web/js/fun/park.js";

const st = (s) => ({ get: (k, d) => (s[k] === undefined ? d : s[k]) });

// parked rule (same as teryx_dash/fun.py)
assert.equal(isParked(st({ "in.park": true, "mc.speed": 0 })), true);
assert.equal(isParked(st({ "in.park": false, "mc.speed": 0 })), false);
assert.equal(isParked(st({ "in.park": true, "mc.speed": 4 })), false);
assert.equal(isParked(st({ "in.park": true, "mc.speed": 0, "mc.online": false })), false);
assert.equal(isParked(st({ "in.park": true, "mc.speed": 0, "pico.parked": false })), false);
assert.match(whyNotParked(st({ "in.park": false, "mc.speed": 0 })), /park brake/);

// load: Pi + screen only, then with the cab light at full and two bars at half
const base = campLoadW({}, {});
assert.equal(base, CAMP_DEFAULTS.piW + CAMP_DEFAULTS.screenW);
const lit = campLoadW({}, { lights: { "light.interior": 255, "light.front_1": 128, "light.front_2": 127 }, audio: true });
assert.ok(Math.abs(lit - (base + CAMP_DEFAULTS.interiorW + CAMP_DEFAULTS.barW + CAMP_DEFAULTS.ampW)) < 0.01);
// screen off counts for 15% of it (standby)
assert.ok(campLoadW({}, { screen: 0 }) < base);
// pack mode adds the DC-DC loss and the controller
assert.ok(campLoadW({ source: "pack" }, {}) > base / CAMP_DEFAULTS.dcdcEff + 1);

// budget: 35 Ah lead, full = 35 x 12 x 0.5 = 210 Wh
assert.equal(campBudgetWh({ auxAh: 35, auxChem: "lead" }, { startSoc: 100 }), 210);
assert.equal(campBudgetWh({ auxAh: 35, auxChem: "lead" }, { startSoc: 100, usedWh: 10 }), 200);
assert.equal(campBudgetWh({ auxAh: 35, auxChem: "lead" }, { startSoc: 40 }), 0);       // already below half
assert.equal(Math.round(campBudgetWh({ auxAh: 50, auxChem: "lithium" }, { startSoc: 100 })), 512);
// pack: 7.5 kWh at 80% keeping 40% = 3000 Wh
assert.equal(campBudgetWh({ source: "pack", packFloorPct: 40 }, { packSoc: 80, packKwh: 7.5 }), 3000);
assert.equal(campBudgetWh({ source: "pack", packFloorPct: 40 }, { packSoc: 30 }), 0);
assert.equal(campBudgetWh({ source: "pack" }, {}), null);

assert.equal(campHoursLeft(210, 21), 10);
assert.equal(campHoursLeft(null, 21), null);
assert.equal(fmtHours(10), "10 h");
assert.equal(fmtHours(2.5), "2 h 30 min");
assert.equal(fmtHours(0.25), "15 min");
assert.equal(fmtHours(100), "4 days");

// rested voltage to charge
assert.equal(restSoc(12.8), 100);
assert.equal(restSoc(12.2), 50);
assert.equal(restSoc(12.3), 60);
assert.equal(restSoc(11.0), 10);
assert.equal(restSoc(null), null);
assert.equal(restSoc(13.5, "lithium"), 100);

console.log("fun js: all good");
