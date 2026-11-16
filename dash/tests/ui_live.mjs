// End-to-end check of the dash UI against the simulator.
// Start the sim first:  python -m teryx run --scenario idle --ui dash/web --port 8080
// Then:                 node dash/tests/ui_live.mjs [http://localhost:8080] [screenshot dir]
// Drives the real UI with a mouse (as a finger), then checks what the simulated control box did.
import { createRequire } from "module";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const BASE = process.argv[2] || "http://localhost:8080";
const SHOTS = process.argv[3] || "";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const state = async () => (await fetch(`${BASE}/api/state`)).json();
const sim = (cmd) => fetch(`${BASE}/api/sim`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(cmd) });
let failed = 0;
const check = (ok, what) => { console.log(`${ok ? "PASS" : "FAIL"}  ${what}`); if (!ok) failed++; };

async function waitFor(fn, ms = 5000) {
  const end = Date.now() + ms;
  while (Date.now() < end) { const s = await state(); if (fn(s)) return s; await sleep(100); }
  return state();
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
const shot = async (name) => { if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}.png` }); };
const nav = (id) => page.click(`.nav-btn[data-id="${id}"]`);

await sim({ scenario: "idle" });
await page.goto(`${BASE}/?screen=drive`);
await page.evaluate(() => { teryx.settings.set("theme", "night"); teryx.applyTheme(); });
await sleep(1500);
check(await page.$eval("#tb-link", (e) => e.classList.contains("ok")), "control box shows online");
await shot("live-drive-idle");

// Lights
await nav("lights");
await page.click('.light-tile[data-id="light.front_2"] .lt-big');
let s = await waitFor((s) => s["light.front_2"] === 255);
check(s["light.front_2"] === 255, "bar 2 turns on");
await page.click('[data-g="work"]');
s = await waitFor((s) => s["light.front_1"] === 255 && s["light.front_4"] === 255);
check(s["light.front_4"] === 255, "work preset turns all four bars on");
check(s["trailer.tail"] === true, "trailer tail follows front bars");
await shot("live-lights");

// 4WD and diff
await nav("drivetrain");
await page.click('#t-seg button[data-v="1"]');
s = await waitFor((s) => s["act.4wd"] === "4wd", 6000);
check(s["act.4wd"] === "4wd", "4WD engages when stopped");
await page.click("#t-presets button:nth-child(3)");
s = await waitFor((s) => Math.abs(s["an.diff_pos"] - 50) <= 2, 8000);
check(Math.abs(s["an.diff_pos"] - 50) <= 2, `diff lock reaches 50% (got ${s["an.diff_pos"]})`);
await shot("live-4wd");

// Winch: slide to arm, then hold IN
await nav("winch");
const knob = await page.$("#w-arm .knob");
const kb = await knob.boundingBox(), ab = await (await page.$("#w-arm")).boundingBox();
await page.mouse.move(kb.x + kb.width / 2, kb.y + kb.height / 2);
await page.mouse.down();
await page.mouse.move(ab.x + ab.width - 20, kb.y + kb.height / 2, { steps: 10 });
await page.mouse.up();
s = await waitFor((s) => s["winch.armed"] === true);
check(s["winch.armed"] === true, "winch arms by sliding");
const wb = await (await page.$("#w-in")).boundingBox();
await page.mouse.move(wb.x + wb.width / 2, wb.y + wb.height / 2);
await page.mouse.down();
s = await waitFor((s) => s["winch.in"] === true, 2000);
check(s["winch.in"] === true, "winch pulls in while held");
await shot("live-winch-running");
await page.mouse.up();
s = await waitFor((s) => s["winch.in"] === false, 1500);
check(s["winch.in"] === false, "winch stops when released");
await page.click("#w-arm");
s = await waitFor((s) => s["winch.armed"] === false);
check(s["winch.armed"] === false, "tap disarms the winch");

// Tray: hold up for 2 s
await nav("tray");
const tb = await (await page.$("#tr-up")).boundingBox();
await page.mouse.move(tb.x + tb.width / 2, tb.y + tb.height / 2);
await page.mouse.down();
await sleep(2000);
s = await state();
check(s["act.tray"] === "raising", `tray raises while held (${s["act.tray"]})`);
await shot("live-tray");
await page.mouse.up();
s = await waitFor((s) => s["act.tray"] !== "raising", 1500);
check(s["act.tray"] !== "raising", "tray stops when released");
check(s["act.tray_pct"] > 0, `tray moved (${s["act.tray_pct"]}%)`);

// Lockout: driving along, ask for 2WD, the control box refuses and we say why
await sim({ scenario: "trail" });
s = await waitFor((s) => s["mc.speed"] > 8, 15000);
await nav("drivetrain");
await page.click('#t-seg button[data-v="0"]');
await sleep(1200);
const toast = await page.$eval("#toast", (e) => (e.hidden ? "" : e.textContent));
check(/slow/i.test(toast), `refusal explained when too fast ("${toast}")`);
s = await state();
check(s["act.4wd"] === "4wd", "still in 4WD after refusal");
await nav("drive");
await sleep(500);
await shot("live-drive-trail");

// Reverse pops up the camera
await sim({ scenario: "reversing" });
await page.waitForFunction(() => teryx.current && teryx.current.id === "camera", null, { timeout: 15000 }).catch(() => {});
check(await page.evaluate(() => teryx.current.id) === "camera", "camera pops up in reverse");
await shot("live-camera");

// Faults show a banner
await sim({ scenario: "faults" });
await page.waitForSelector("#fault-banner:not([hidden])", { timeout: 15000 }).catch(() => {});
check(await page.$eval("#fault-banner", (e) => !e.hidden), "fault banner shows");
await nav("drive");
await sleep(800);
await shot("live-faults");
await nav("settings");
await page.click('#s-nav button[data-k="limits"]');
await sleep(800);
check((await page.$$("#s-body .stepper")).length >= 10, "safety limits load from the control box");
await shot("live-settings-limits");
await page.click('#s-nav button[data-k="faults"]');
await sleep(400);
await shot("live-settings-faults");

check(errors.length === 0, `no page errors ${errors.join(" | ")}`);
await sim({ scenario: "idle" });
await browser.close();
console.log(failed ? `\n${failed} failed` : "\nall passed");
process.exit(failed ? 1 : 0);
