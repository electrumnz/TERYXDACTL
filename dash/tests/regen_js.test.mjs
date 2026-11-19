// Plain node checks for the dash's regen on/off. Run: node dash/tests/regen_js.test.mjs
import assert from "node:assert/strict";
import { regenOn } from "../web/js/regen.js";

const st = (s) => ({ get: (k, d) => (s[k] === undefined ? d : s[k]) });
const coast = { "mc.speed": 30, "mc.throttle": 0, "mc.direction": "forward" };

// no current reading: moving, off the throttle, in gear
assert.equal(regenOn(st(coast)), true);
assert.equal(regenOn(st({ ...coast, "mc.throttle": 20 })), false);
assert.equal(regenOn(st({ ...coast, "mc.direction": "neutral" })), false);
assert.equal(regenOn(st({ ...coast, "mc.speed": 1 })), false);
assert.equal(regenOn(st({ ...coast, "mc.direction": "reverse" })), true);
// with a current reading, that decides it
assert.equal(regenOn(st({ ...coast, "mc.batt_a": -12 })), true);
assert.equal(regenOn(st({ ...coast, "mc.batt_a": 3 })), false);
assert.equal(regenOn(st({ "mc.speed": 30, "mc.throttle": 40, "mc.batt_a": -5 })), true);   // downhill
assert.equal(regenOn(st({ "mc.speed": 0, "mc.batt_a": -20 })), false);                     // stopped (charger)
// the Shinegle's own flag wins
assert.equal(regenOn(st({ ...coast, "mc.regen": false })), false);
assert.equal(regenOn(st({ "mc.speed": 0, "mc.regen": true })), true);
// controller offline: nothing
assert.equal(regenOn(st({ ...coast, "mc.online": false })), false);
console.log("regen ok");
