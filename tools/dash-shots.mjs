// Screenshot every dash screen in each look (Predator, Fossil, Night Hunt), at the real screen size (1280x800).
// Used to refresh dash/docs/screens and to compare looks side by side.
//
//   node tools/dash-shots.mjs [out dir] [--scale 2]
//
// Starts the simulator itself (port 8099), drives it into a believable state for each
// screen, pauses it so the numbers hold still, and saves <screen>-<look>.png
// (look = std, offroad or night; LOOKS=std node ... for just one).
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
const LOOKS = (process.env.LOOKS || "std,offroad,night").split(",");
const ONLY = process.env.ONLY ? process.env.ONLY.split(",") : null;
const SHOTS_ALL = [
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
const SHOTS = ONLY ? SHOTS_ALL.filter((s) => ONLY.includes(s.name)) : SHOTS_ALL;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: scale });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.goto(`${BASE}/?screen=drive`);
await sleep(2500);
// Start from the real defaults: winch, tray and media greyed out (not wired up yet).
await page.evaluate(() => { const d = { trips: true, drivetrain: true, lights: true, winch: false, tray: false, camera: true, media: false }; Object.entries(d).forEach(([k, v]) => teryx.settings.set(`features.${k}`, v)); });

for (const s of SHOTS) {
  if (s.sim) { await sim({ paused: false }); await sim(s.sim); await sleep(s.run || 1000); await sim({ paused: true }); }
  await page.evaluate((id) => teryx.show(id), s.screen);
  for (const look of LOOKS) {
    await page.evaluate((l) => { teryx.settings.set("look", l); teryx.looks.refresh(); teryx.applyTheme(); }, look);
    await sleep(1800);   // the looks cross-fade over 1.4 s
    await page.screenshot({ path: `${OUT}/${s.name}-${look}.png` });
  }
  console.log(`saved ${s.name}`);
  // The drive shot shows the real defaults (features not wired up yet are greyed out).
  // Switch everything on for the rest, so every screen can be opened.
  if (s.name === "drive") await page.evaluate(() => Object.keys(teryx.settings.get("features")).forEach((k) => teryx.settings.set(`features.${k}`, true)));
}
await page.evaluate(() => { teryx.settings.set("look", "auto"); ["winch", "tray", "media"].forEach((k) => teryx.settings.set(`features.${k}`, false)); });
await sleep(600);   // let the settings save to the sim before closing
await sim({ paused: false });
await browser.close();
stop();
if (errors.length) { console.error("page errors:\n" + errors.join("\n")); process.exit(1); }
