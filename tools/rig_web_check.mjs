// CI check for the phone sim: runs dash/web/rig (Pico firmware as WebAssembly + teryx/rig in
// Pyodide) under Node and drives it like the page would. Needs `npm install pyodide@<version
// in dash/web/rig/worker.js>` and teryx-py.zip from tools/build_rig_web.py.
//   node tools/rig_web_check.mjs
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const rigDir = path.join(root, "dash/web/rig");
const { loadPyodide } = require("pyodide");
const { default: factory } = await import(path.join(rigDir, "pico.js"));
const { startRig } = await import(path.join(rigDir, "rig-core.js"));

function check(ok, what) {
  if (!ok) { console.error("FAIL:", what); process.exit(1); }
  console.log("ok:", what);
}

const t0 = Date.now();
process.on("uncaughtException", (e) => { console.error("FAIL:", e.message); process.exit(1); });
process.on("unhandledRejection", (e) => { console.error("FAIL:", e && e.message); process.exit(1); });
const rig = await startRig({ loadPyodide, factory, zipBytes: new Uint8Array(readFileSync(path.join(rigDir, "teryx-py.zip"))),
                             status: (s) => console.log("..", s) });
console.log(`started in ${((Date.now() - t0) / 1000).toFixed(1)} s`);

const run = (secs) => { for (let t = 0; t < secs; t += 0.1) rig.tick(0.1); return rig.out(); };
let w0 = Date.now();
let o = run(4);
const rate = 4 / ((Date.now() - w0) / 1000);
console.log(`sim runs at ${rate.toFixed(1)}x real time here`);
check(o.dash["pico.online"] && o.dash["pico.state"] === "ok", "Pico boots and talks to the dash");
check(o.dash["link.online"] && o.panel.screen_on, "the Pi and screen are on");
check(o.panel.problems.length === 0, "no wiring problems: " + JSON.stringify(o.panel.problems));

rig.ui({ type: "request", id: "light.front_1", value: 255 });
o = run(0.5);
check(o.panel.lights.LB1.bar > 0.9, "dash button lights light bar 1 through the real firmware");

rig.panel({ park: false, fnr: "forward", throttle: 0.6 });
o = run(4);
check(o.dash["mc.speed"] > 8, `drives (${o.dash["mc.speed"]} km/h) through the throttle wires and the Shinegle`);
rig.panel({ throttle: 0, steer: 3 });
o = run(1);
check(o.dash["steer.state"] === "ok" && o.dash["steer.angle"] > 50, "power steering: ECU replies, angle on the dash");
rig.panel({ steer: 0, brake: true });
o = run(4);
rig.panel({ brake: false });

rig.ui({ type: "setting", key: "eps_listen", value: 1 });
o = run(0.5);
check(o.replies.some((r) => r.type === "setting_ack" && r.key === "eps_listen"), "settings get their ack");

rig.panel({ fuse: ["FB.F8", true] });
o = run(1);
check(o.panel.problems.length >= 0, "pulling a fuse doesn't crash the sim");
rig.panel({ fuse: ["FB.F8", false], key: false });
o = run(20);
check(!o.panel.pi_on, "key off: the Pi shuts down");
console.log("all good");
process.exit(0);
