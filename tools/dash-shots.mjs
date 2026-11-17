// Screenshot every dash screen in night and day, at the real screen size (1280x800).
// Used to refresh dash/docs/screens and to compare looks side by side.
//
//   node tools/dash-shots.mjs [out dir] [--scale 2]
//
// Starts the simulator itself (port 8099), drives it into a believable state for each
// screen, pauses it so the numbers hold still, and saves <screen>-<theme>.png.
// Needs Python deps (pip install -e . -e dash/server) and Playwright.
import { spawn } from "child_process";
import { createRequire } from "module";
import { mkdirSync } from "fs";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const args = process.argv.slice(2);
const scale = args.includes("--scale") ? Number(args[args.indexOf("--scale") + 1]) : 1;
const OUT = args.find((a, i) => !a.startsWith("--") && args[i - 1] !== "--scale") || "dash/docs/screens/all";
mkdirSync(OUT, { recursive: true });
const PORT = 8099, BASE = `http://localhost:${PORT}`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const sim = (cmd) => fetch(`${BASE}/api/sim`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(cmd) });

const server = spawn("python", ["-m", "teryx", "run", "--scenario", "idle", "--ui", "dash/web", "--port", String(PORT)], {
  stdio: "ignore", env: { ...process.env, PYTHONPATH: ["dash/server", process.env.PYTHONPATH].filter(Boolean).join(":") },
});
const stop = () => { try { server.kill(); } catch {} };
process.on("exit", stop);

for (let i = 0; i < 100; i++) { try { if ((await fetch(`${BASE}/api/state`)).ok) break; } catch {} await sleep(200); }

// Each shot: which screen, what the sim should be doing first, and how long to let it run.
const SHOTS = [
  { name: "drive", screen: "drive", sim: { scenario: "trail" }, run: 9000 },
  { name: "trips", screen: "trips" },
  { name: "4wd", screen: "drivetrain", sim: { scenario: "idle" }, run: 1500 },
  { name: "lights", screen: "lights" },
  { name: "winch", screen: "winch" },
  { name: "tray", screen: "tray" },
  { name: "camera", screen: "camera", sim: { scenario: "reversing" }, run: 4000 },
  { name: "media", screen: "media", sim: { scenario: "idle" }, run: 1500 },
  { name: "settings", screen: "settings" },
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: scale });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.goto(`${BASE}/?screen=drive`);
await sleep(2500);

for (const s of SHOTS) {
  if (s.sim) { await sim({ paused: false }); await sim(s.sim); await sleep(s.run || 1000); await sim({ paused: true }); }
  await page.evaluate((id) => teryx.show(id), s.screen);
  for (const theme of ["night", "day"]) {
    await page.evaluate((t) => { teryx.settings.set("theme", t); teryx.applyTheme(); }, theme);
    await sleep(700);
    await page.screenshot({ path: `${OUT}/${s.name}-${theme}.png` });
  }
  console.log(`saved ${s.name}`);
}
await sim({ paused: false });
await browser.close();
stop();
if (errors.length) { console.error("page errors:\n" + errors.join("\n")); process.exit(1); }
