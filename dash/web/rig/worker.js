// Web worker for the whole-Teryx sim page (rig/index.html).
// Runs the real Pico firmware (pico.wasm) and teryx/rig (Python, in Pyodide) off the page's
// main thread, in real time, and swaps messages with the page:
//   in:  {type:"ui", msg}     a dash screen message (request, hold, lock, setting)
//        {type:"panel", cmd}  the hands-on panel (key, pedals, F-N-R, wheel, fuses, faults)
//        {type:"wiring", on}  send the live wiring state (every pin's level) while on
//   out: {type:"status", text} while loading, {type:"error", text},
//        {type:"out", dash, panel, replies, speed} about 10 times a second
//        {type:"wiring", state} about 3 times a second while the wiring drawing is open
// A module worker: Pyodide no longer runs in classic workers.
import TeryxPico from "./pico.js";
import { startRig } from "./rig-core.js";

// Keep the npm version in .github/workflows/rig-web.yml the same. ?pyodide=<url> (on the page)
// loads it from somewhere else instead, e.g. a copy on the laptop for use with no internet.
const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";
const PYODIDE = new URL(self.location.href).searchParams.get("pyodide") || PYODIDE_CDN;
const TICK_MS = 50;
const OUT_MS = 100;

let rig = null, wiringOn = false;
const queue = [];
const WIRING_MS = 300;

self.onmessage = (ev) => {
  if (rig) handle(ev.data); else queue.push(ev.data);
};

function handle(m) {
  if (m.type === "wiring") { wiringOn = !!m.on; return; }
  try {
    if (m.type === "ui") rig.ui(m.msg);
    else if (m.type === "panel") rig.panel(m.cmd);
  } catch (e) {
    self.postMessage({ type: "warn", text: String(e.message || e).split("\n").slice(-2).join(" ") });
  }
}

(async () => {
  try {
    const v = new URL(self.location.href).searchParams.get("v") || "";
    const q = v ? `?v=${v}` : "";
    const { loadPyodide } = await import(PYODIDE + "pyodide.mjs");
    const status = (text) => self.postMessage({ type: "status", text });
    status("Downloading Teryx OS");
    const zip = new Uint8Array(await (await fetch("teryx-py.zip" + q)).arrayBuffer());
    rig = await startRig({ loadPyodide, indexURL: PYODIDE, factory: TeryxPico, zipBytes: zip, status });
    while (queue.length) handle(queue.shift());
    status("Running");
    loop();
  } catch (e) {
    self.postMessage({ type: "error", text: String(e.message || e) });
  }
})();

function loop() {
  let last = performance.now(), lastOut = 0, lastWiring = 0, simT = 0, wallT = 0;
  const step = () => {
    const now = performance.now();
    const dt = Math.min((now - last) / 1000, 0.25);   // a tab that was asleep doesn't race to catch up
    last = now;
    const t0 = performance.now();
    try { rig.tick(dt); } catch (e) {
      self.postMessage({ type: "error", text: String(e.message || e) });
      return;
    }
    const busy = performance.now() - t0;
    simT += dt; wallT += Math.max(dt, busy / 1000);
    if (now - lastOut >= OUT_MS) {
      lastOut = now;
      const o = rig.out();
      self.postMessage({ type: "out", ...o, speed: wallT ? simT / wallT : 1 });
      simT = wallT = 0;
    }
    if (wiringOn && now - lastWiring >= WIRING_MS) {
      lastWiring = now;
      try { self.postMessage({ type: "wiring", state: rig.wiring() }); } catch (e) { /* keep running */ }
    }
    setTimeout(step, Math.max(0, TICK_MS - busy));
  };
  step();
}
