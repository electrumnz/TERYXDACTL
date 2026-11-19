// Plain node checks for the T. rex chase clip picker. Run: node dash/tests/rexchase_js.test.mjs
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { pickNext, bandFor, rateFor, RATE_MIN, RATE_MAX, HUB } from "../web/js/ui/rexchase.js";

const c = (id, kind, from, to, band) => ({ id, kind, from, to, band, file: id + ".mp4" });
const CLIPS = [
  c("idle-1", "idle", "closed", "closed"), c("idle-2", "idle", "closed", "closed"),
  c("wake-1", "wake", "closed", "roar"), c("settle-1", "settle", "roar", "closed"),
  c("turn-1", "turn", "roar", "run"), c("stop-1", "stop", "run", "roar"),
  c("stalk-1", "chase", "run", "run", "stalk"), c("stalk-2", "chase", "run", "run", "stalk"),
  c("trot-1", "chase", "run", "run", "trot"), c("sprint-1", "chase", "run", "run", "sprint"),
  c("sprint-2", "chase", "run", "run", "sprint"), c("lunge-1", "lunge", "run", "run", "sprint"),
];
const pick = (o) => pickNext(CLIPS, { rand: () => 0, ...o });

// The story: parked idles, pulling away roars then turns and runs, stopping roars then shuts.
assert.equal(pick({ at: HUB.closed, moving: false }).kind, "idle");
assert.equal(pick({ at: HUB.closed, moving: true }).kind, "wake");
assert.equal(pick({ at: HUB.roar, moving: true }).kind, "turn");
assert.equal(pick({ at: HUB.roar, moving: false }).kind, "settle");
assert.equal(pick({ at: HUB.run, moving: false }).kind, "stop");

// The chase clip follows speed.
assert.equal(pick({ at: HUB.run, moving: true, kmh: 6 }).band, "stalk");
assert.equal(pick({ at: HUB.run, moving: true, kmh: 20 }).band, "trot");
assert.equal(pick({ at: HUB.run, moving: true, kmh: 45 }).band, "sprint");
assert.equal(pick({ at: HUB.run, moving: true, kmh: -6 }).band, "stalk"); // reversing counts as speed

// Floor it at sprint speed and sometimes it lunges, never at low power.
assert.equal(pick({ at: HUB.run, moving: true, kmh: 45, power: 0.9 }).kind, "lunge");
assert.equal(pick({ at: HUB.run, moving: true, kmh: 45, power: 0.3 }).kind, "chase");
assert.equal(pick({ at: HUB.run, moving: true, kmh: 45, power: 0.9, rand: () => 0.9 }).kind, "chase");

// It doesn't repeat itself when there's another take.
assert.equal(pick({ at: HUB.run, moving: true, kmh: 6, recent: ["stalk-1"] }).id, "stalk-2");
assert.equal(pick({ at: HUB.closed, moving: false, recent: ["idle-1"] }).id, "idle-2");
// ...but plays the only one there is rather than nothing.
assert.equal(pick({ at: HUB.run, moving: true, kmh: 20, recent: ["trot-1"] }).id, "trot-1");

// Every clip picked starts where the last one ended, over a long random drive.
let at = HUB.closed, recent = [], seed = 7;
const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
for (let i = 0; i < 2000; i++) {
  const kmh = (i % 200) < 40 ? 0 : (i * 7) % 60;
  const nx = pickNext(CLIPS, { at, moving: kmh > 2, kmh, power: rand(), recent, rand });
  assert.ok(nx, `nothing to play at ${at}`);
  assert.equal(nx.from, at);
  at = nx.to; recent = [...recent, nx.id].slice(-3);
}

// A band with no clips yet falls back to any chase clip, so a half-made set still works.
assert.equal(pickNext(CLIPS.filter((x) => x.band !== "trot"), { at: HUB.run, moving: true, kmh: 20, rand: () => 0 }).kind, "chase");
assert.equal(pickNext([], { at: HUB.run, moving: true }), null);

// Speed bands and playback rate stay in range.
assert.equal(bandFor(0).id, "stalk");
assert.equal(bandFor(29.9).id, "trot");
assert.equal(bandFor(200).id, "sprint");
for (const k of [0, 1, 5, 8, 15, 20, 35, 40, 80, 150]) {
  const r = rateFor(k);
  assert.ok(r >= RATE_MIN && r <= RATE_MAX, `rate ${r} at ${k}`);
}
assert.equal(rateFor(8), 1);   // at the clip's own speed it plays as made
assert.equal(rateFor(40), 1);

// The real clip list, once it's in: every hub has a way out for both moving and parked.
const man = new URL("../web/video/rex/clips.json", import.meta.url);
if (existsSync(man)) {
  const clips = JSON.parse(readFileSync(man, "utf8")).clips;
  for (const x of clips) assert.ok(existsSync(new URL("../web/video/rex/" + x.file, import.meta.url)), `missing ${x.file}`);
  for (const h of Object.values(HUB)) for (const moving of [true, false]) {
    const nx = pickNext(clips, { at: h, moving, kmh: moving ? 20 : 0 });
    assert.ok(nx && nx.from === h, `no clip out of ${h} when ${moving ? "moving" : "parked"}`);
  }
}
console.log("rexchase ok");
