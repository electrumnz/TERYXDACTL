// Front bar stack maths (dash/web/js/barstack.js). Run by tests/test_barstack.py, or: node tests/js/barstack.test.mjs
import assert from "node:assert/strict";
import { sliderToLevels, levelsToSlider, matchPreset, stackLabel, BAR_PRESET_DEFAULTS as P } from "../../dash/web/js/barstack.js";

const L = (a, b, c, d) => ({ "light.front_1": a, "light.front_2": b, "light.front_3": c, "light.front_4": d });

// Each quarter fills one bar, top down.
assert.deepEqual(sliderToLevels(0), L(0, 0, 0, 0));
assert.deepEqual(sliderToLevels(12.5), L(128, 0, 0, 0));
assert.deepEqual(sliderToLevels(25), L(255, 0, 0, 0));
assert.deepEqual(sliderToLevels(37.5), L(255, 128, 0, 0));
assert.deepEqual(sliderToLevels(50), L(255, 255, 0, 0));
assert.deepEqual(sliderToLevels(100), L(255, 255, 255, 255));
// Other fill orders
assert.deepEqual(sliderToLevels(50, "bottom"), L(0, 0, 255, 255));
assert.deepEqual(sliderToLevels(50, "middle"), L(0, 255, 255, 0));
// An on/off bar comes on half way through its quarter
const onoff = (id) => id !== "light.front_2";   // bar 2 is on/off only
assert.deepEqual(sliderToLevels(10, "top", onoff), L(102, 0, 0, 0));
assert.deepEqual(sliderToLevels(35, "top", onoff), L(255, 0, 0, 0));
assert.deepEqual(sliderToLevels(37.5, "top", onoff), L(255, 255, 0, 0));

// Presets put the slider where they belong
assert.deepEqual(levelsToSlider(P.low), { slider: 12.5, mixed: false });
assert.deepEqual(levelsToSlider(P.med), { slider: 50, mixed: false });
assert.deepEqual(levelsToSlider(P.high), { slider: 100, mixed: false });
// Round trip for every slider step
for (let s = 0; s <= 100; s += 2.5) assert.ok(Math.abs(levelsToSlider(sliderToLevels(s)).slider - s) < 0.2, `round trip ${s}`);
// Set bar by bar: not the stack pattern
assert.equal(levelsToSlider(L(0, 255, 0, 255)).mixed, true);
assert.equal(levelsToSlider(L(0, 255, 255, 0), "middle").mixed, false);

assert.equal(matchPreset(P.med, P), "med");
assert.equal(matchPreset(sliderToLevels(12.5), P), "low");
assert.equal(matchPreset(L(0, 0, 0, 255), P), "");

assert.equal(stackLabel(L(0, 0, 0, 0)), "Off");
assert.equal(stackLabel(P.low), "Bar 1 50%");
assert.equal(stackLabel(P.med), "2 bars");
assert.equal(stackLabel(sliderToLevels(60)), "2 bars + 40%");
assert.equal(stackLabel(L(255, 0, 0, 255)), "2 bars, mixed");
console.log("barstack ok");
