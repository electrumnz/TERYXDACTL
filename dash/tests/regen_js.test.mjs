// Plain node checks for the dash's regen on/off. Run: node dash/tests/regen_js.test.mjs
import assert from "node:assert/strict";
import { regenOn } from "../web/js/regen.js";

const st = (s) => ({ get: (k, d) => (s[k] === undefined ? d : s[k]) });
const coast = { "mc.speed": 30, "mc.throttle": 0 };

// default: speed above 0 and throttle at rest
assert.equal(regenOn(st(coast)), true);
assert.equal(regenOn(st({ ...coast, "mc.throttle": 2 })), true);      // released pedal reading a hair above 0
assert.equal(regenOn(st({ ...coast, "mc.throttle": 20 })), false);
assert.equal(regenOn(st({ ...coast, "mc.speed": 0 })), false);
assert.equal(regenOn(st({ ...coast, "mc.speed": 1 })), true);
assert.equal(regenOn(st({ ...coast, "mc.batt_a": 15 })), true);       // current ignored by default
// the throttle micro switch beats the reading when we have it
assert.equal(regenOn(st({ ...coast, "mc.throttle": 1, "mc.throttle_sw": true })), false);
assert.equal(regenOn(st({ ...coast, "mc.throttle": 5, "mc.throttle_sw": false })), true);
// "current" mode: current back into the pack while moving
assert.equal(regenOn(st({ ...coast, "mc.batt_a": -12 }), "current"), true);
assert.equal(regenOn(st({ ...coast, "mc.batt_a": 3 }), "current"), false);
assert.equal(regenOn(st({ "mc.speed": 30, "mc.throttle": 40, "mc.batt_a": -5 }), "current"), true);   // downhill
assert.equal(regenOn(st({ "mc.speed": 0, "mc.batt_a": -20 }), "current"), false);                     // stopped (charger)
assert.equal(regenOn(st(coast), "current"), true);                    // no current reading yet: throttle rule
// the Shinegle's own flag wins
assert.equal(regenOn(st({ ...coast, "mc.regen": false })), false);
assert.equal(regenOn(st({ "mc.speed": 0, "mc.regen": true })), true);
// controller offline: nothing
assert.equal(regenOn(st({ ...coast, "mc.online": false })), false);
console.log("regen ok");
