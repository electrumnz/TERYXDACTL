// Plain node checks for the camera screen's choices. Run: node dash/tests/camera_js.test.mjs
import assert from "node:assert/strict";
import { trailerOn, camState, comboCams, layoutFor } from "../web/js/screens/camera.js";
import { migrate, DEFAULTS } from "../web/js/settings.js";

const store = (s) => ({ get: (k, d) => (s[k] === undefined ? d : s[k]) });
const CAMS = {
  rear: { fitted: true, v4l2Device: "adv:0" }, front: { fitted: true, v4l2Device: "adv:3" },
  trailer: { fitted: true, v4l2Device: "adv:1" }, cabin: { fitted: false, v4l2Device: "adv:2" },
};
const settings = (cam = {}, cams = CAMS) => ({ get: (p) => p.split(".").reduce((o, k) => (o == null ? o : o[k]), { camera: { cams, ...cam } }) });
const S = settings();

// Trailer: picture wins, then the plug. Plug in with no picture = trailer with no camera.
assert.equal(trailerOn(S, store({})), false);
assert.equal(trailerOn(S, store({ "in.trailer": true })), true);                       // not checked yet: go by the plug
assert.equal(trailerOn(S, store({ "in.trailer": true, "cam.trailer_signal": false })), false);
assert.equal(trailerOn(S, store({ "cam.trailer_signal": true })), true);               // picture, reed switch not seen
assert.equal(trailerOn(settings({ trailerDetect: "plug" }), store({ "in.trailer": true, "cam.trailer_signal": false })), true);
assert.equal(trailerOn(settings({ trailerDetect: "picture" }), store({ "in.trailer": true })), false);
assert.equal(camState(S, store({ "in.trailer": true, "cam.trailer_signal": false }), "trailer"), "nopicture");
assert.equal(camState(S, store({}), "trailer"), "notrailer");

// Combined view: front + rear with no trailer, front + trailer + rear with one.
assert.deepEqual(comboCams(S, store({})), ["front", "rear"]);
assert.deepEqual(comboCams(S, store({ "in.trailer": true })), ["front", "trailer", "rear"]);
assert.equal(camState(S, store({}), "combo"), "ok");
assert.equal(camState(settings({}, { ...CAMS, front: { fitted: false } }), store({}), "combo"), "few");

// All on the video board: only one camera is live. Driving forward the front, in reverse the
// one behind you (trailer if it's on), or the one tapped.
const live = (l) => l.filter((x) => x.live).map((x) => x.cam);
const REV = { "mc.direction": "reverse" };
assert.deepEqual(live(layoutFor(S, store({}), "combo", null)), ["front"]);
assert.deepEqual(live(layoutFor(S, store({ "in.trailer": true }), "combo", null)), ["front"]);
assert.deepEqual(live(layoutFor(S, store({ ...REV }), "combo", null)), ["rear"]);
assert.deepEqual(live(layoutFor(S, store({ ...REV, "in.trailer": true }), "combo", null)), ["trailer"]);
assert.deepEqual(live(layoutFor(S, store({ "in.reverse": true, "in.trailer": true }), "combo", null)), ["trailer"]);
assert.deepEqual(live(layoutFor(S, store({ "in.trailer": true }), "combo", "rear")), ["rear"]);
// A tapped camera that's gone falls back.
assert.deepEqual(live(layoutFor(S, store({}), "combo", "trailer")), ["front"]);
// A single camera is always live.
assert.deepEqual(layoutFor(S, store({}), "rear", null), [{ cam: "rear", live: true }]);
// Rear and trailer both on the board, no front: one live, one paused.
const noFront = settings({}, { ...CAMS, front: { fitted: false } });
assert.deepEqual(live(layoutFor(noFront, store({ "in.trailer": true }), "combo", null)), ["trailer"]);
// A Pi ribbon camera on the front (older setup) stays live alongside one board camera.
const csiFront = settings({}, { ...CAMS, front: { fitted: true, v4l2Device: "csi0" } });
assert.deepEqual(live(layoutFor(csiFront, store({}), "combo", null)), ["front", "rear"]);
assert.deepEqual(live(layoutFor(csiFront, store({ "in.trailer": true }), "combo", "rear")), ["front", "rear"]);

// Old saved settings with the Pi camera on the front move to video board input 3.
const old = { camera: { cams: { rear: {}, front: { v4l2Device: "csi0" } } } };
assert.equal(migrate(old).camera.cams.front.v4l2Device, "adv:3");
assert.equal(DEFAULTS.camera.cams.front.v4l2Device, "adv:3");

console.log("camera ok");
