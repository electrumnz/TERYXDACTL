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
check(!(await page.$("#splash")), "boot splash has gone once the control box answers");
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
await sleep(300);   // let the page's own copy of the state catch up
const wb = await (await page.$("#w-in")).boundingBox();
await page.mouse.move(wb.x + wb.width / 2, wb.y + wb.height / 2);
await page.mouse.down();
s = await waitFor((s) => s["winch.in"] === true, 2000);
check(s["winch.in"] === true, "winch pulls in while held");
await shot("live-winch-running");
await page.mouse.up();
s = await waitFor((s) => s["winch.in"] === false, 1500);
check(s["winch.in"] === false, "winch stops when released");

// Timed pull: tucked behind a button, pick 5 s, 3-2-1, pulls, stops by itself
await page.click("#w-timed");
check(await page.$eval("#wt", (e) => !e.hidden), "timed pull popup opens");
await page.click('.wt-preset[data-s="5"]');
await shot("live-winch-timed-pick");
await page.click("#wt-go");
await sleep(1200);
check((await state())["winch.in"] === false, "nothing moves during the 3-2-1 countdown");
await shot("live-winch-timed-count");
s = await waitFor((s) => s["winch.in"] === true, 3500);
check(s["winch.in"] === true, "winch pulls once the countdown ends");
const pullAt = Date.now();
await sleep(2000);
await shot("live-winch-timed-pull");
s = await waitFor((s) => s["winch.in"] === false, 5000);
const took = (Date.now() - pullAt) / 1000;
check(s["winch.in"] === false && took > 4 && took < 6.5, `timed pull stops by itself after about 5 s (${took.toFixed(1)} s)`);
await sleep(300);
check(await page.$eval("#wt", (e) => e.dataset.phase) === "done", "popup shows the pull is done");
await shot("live-winch-timed-done");
// STOP part way through
await page.click("#wt-go");
s = await waitFor((s) => s["winch.in"] === true, 5000);
await sleep(500);
await page.click("#wt-x");
s = await waitFor((s) => s["winch.in"] === false, 400);
check(s["winch.in"] === false, "STOP cuts a timed pull straight away");
// Cancel during the countdown
await page.click("#wt-go");
await sleep(800);
await page.click("#wt-x");
await sleep(3000);
check((await state())["winch.in"] === false, "cancel in the countdown means it never starts");
await page.click("#wt-x");   // close
check(await page.$eval("#wt", (e) => e.hidden), "popup closes");
const heat = await page.evaluate(() => teryx.winchHeat.pct);
check(heat > 3, `motor heat counted the pulls (${heat.toFixed(1)}%)`);
await shot("live-winch-after");
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

// Safe drive changes: driving along, ask for 2WD. The control box waits for a stop
// (spinner, hint, countdown, Cancel), Cancel drops it, and a wait that ends in a stop goes through.
await sim({ scenario: "trail" });
s = await waitFor((s) => s["mc.speed"] > 8, 15000);
await nav("drivetrain");
await page.click('#t-seg button[data-v="0"]');
s = await waitFor((s) => s["act.4wd_wait"], 2000);
check(s["act.4wd_wait"] === true, "2WD request waits while moving");
await sleep(400);
const waitTxt = await page.$eval("#t-wait", (e) => (e.hidden ? "" : e.textContent));
check(/stop to shift/i.test(waitTxt) && /cancel/i.test(waitTxt), `hint and Cancel shown while waiting ("${waitTxt}")`);
check(await page.$('#t-seg button[data-v="0"].sh-waiting .spin') !== null, "spinner on the 2WD button");
check(await page.$('#t-presets button[data-p="50"].locked') !== null, "diff lock presets locked meanwhile");
await shot("live-4wd-waiting");
await page.click("#t-cancel");
s = await waitFor((s) => !s["act.4wd_wait"], 2000);
check(!s["act.4wd_wait"] && s["act.4wd"] === "4wd", "Cancel drops the wait, still in 4WD");
const toast = await page.$eval("#toast", (e) => (e.hidden ? "" : e.textContent));
check(/cancel/i.test(toast), `cancel confirmed ("${toast}")`);
await sleep(2000);
await page.click('#t-seg button[data-v="0"]');
s = await waitFor((s) => s["act.4wd_wait"], 2000);
await sim({ scenario: "idle" });          // pull up: it changes by itself once stopped
s = await waitFor((s) => s["act.4wd"] === "2wd", 12000);
check(s["act.4wd"] === "2wd", "2WD goes through once stopped");
await sleep(150);
const done = await page.$('#t-seg button[data-v="0"].sh-done .tick');
check(done !== null, "tick and pulse on the button when done");
const toast2 = await page.$eval("#toast", (e) => (e.hidden ? "" : e.textContent));
check(/2wd/i.test(toast2), `success toast ("${toast2}")`);
await shot("live-4wd-done");
await sim({ scenario: "trail" });
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


// ---------- polish for real use ----------
const SIZE_MIN = 60;  // px at 1280x800 on a 10.1" screen = about 10 mm, the least for a gloved finger
async function smallTargets() {
  return page.evaluate((min) => {
    const s = window.__teryxScale || 1, out = [];
    document.querySelectorAll("#app button, #app select, #app .lt-big, #app .slider, #app .arm-slide .knob").forEach((e) => {
      if (!e.offsetParent) return;
      const r = e.getBoundingClientRect(); if (!r.width) return;
      const w = r.width / s, h = r.height / s;
      if (Math.min(w, h) < min) out.push(`${e.className || e.tagName} "${e.textContent.trim().slice(0, 12)}" ${Math.round(w)}x${Math.round(h)}`);
    });
    return out;
  }, SIZE_MIN);
}
await sim({ scenario: "idle", soc: 85 });
const small = [];
for (const id of ["drive", "trips", "drivetrain", "lights", "winch", "tray", "camera"]) { await nav(id); await sleep(300); small.push(...(await smallTargets())); }
await nav("settings");
for (const k of ["display", "sounds", "lights", "camera", "limits", "diff", "faults", "updates", "wifi", "about"]) {
  await page.click(`#s-nav button[data-k="${k}"]`); await sleep(500); small.push(...(await smallTargets()));
}
check(small.length === 0, `every button is at least ${SIZE_MIN} px (about 10 mm) ${small.join(", ")}`);

// On-screen keyboard: name a light bar by tapping keys
await page.click('#s-nav button[data-k="lights"]');
await sleep(300);
await page.selectOption("#s-body select.big >> nth=0", "__type");
await page.waitForSelector(".kb-overlay");
await shot("live-keyboard");
const tap = async (k) => page.click(`.kb-key[data-k="${k}"]`);
for (let i = 0; i < 12; i++) await tap("back");
await tap("shift"); await tap("s"); await tap("p"); await tap("o"); await tap("t"); await tap("space");
await tap("123"); await tap("1"); await tap("done");
await sleep(500);
const lname = await page.evaluate(() => teryx.settings.light("light.front_1").name);
check(lname === "Spot 1", `typed a light name on the keyboard ("${lname}")`);
check(!(await page.$(".kb-overlay")), "keyboard closes on Done");
await page.selectOption("#s-body select.big >> nth=0", "__type");
await page.waitForSelector(".kb-overlay");
await page.click(".kb-cancel");
check((await page.evaluate(() => teryx.settings.light("light.front_1").name)) === "Spot 1", "cancel leaves the name alone");
await page.evaluate(() => teryx.settings.set("lights.light.front_1.name", "Bar 1"));

// Wi-Fi page copes with no NetworkManager on the bench
await page.click('#s-nav button[data-k="wifi"]');
await sleep(800);
check(/Wi-Fi status|Connected to/.test(await page.$eval("#s-body", (e) => e.textContent)), "Wi-Fi page loads (or says why not)");

// Trips: drive a bit, then check the trip and range
await sim({ scenario: "trail" });
await sleep(8000);
let trips = await (await fetch(`${BASE}/api/trips`)).json();
check(trips.current && trips.current.km > 0.01, `trip logs distance (${trips.current && trips.current.km} km)`);
check(trips.current.used_wh > 0, `trip logs energy (${trips.current.used_wh} Wh)`);
check(trips.range_km > 0, `range estimate (${trips.range_km} km at ${trips.wh_per_km} Wh/km)`);
await nav("trips");
await sleep(3500);
check(/km/.test(await page.$eval("#tr-range-u", (e) => e.textContent)) && (await page.$eval("#tr-range", (e) => e.textContent)) !== "--", "trips screen shows range");
await shot("live-trips");
await page.click("#tr-reset"); await page.click("#tr-reset");
await sleep(400);
trips = await (await fetch(`${BASE}/api/trips`)).json();
check(trips.trip_a.km < 0.01, "trip A resets with two taps");
await nav("drive");
await sleep(500);
check(/km/.test(await page.$eval("#d-range", (e) => e.textContent)), "range shows on the drive screen");

// Tilt and GPS widget (fake sensors in the sim)
check(/°/.test(await page.$eval("#sn-roll", (e) => e.textContent)), "tilt widget shows roll");
check(/[NSEW]+ \d+°/.test(await page.$eval("#sn-head", (e) => e.textContent)), "GPS widget shows heading");

// Alerts with sound: a steep side slope
await sim({ scenario: "idle" });
await page.evaluate(() => teryx.alerts.acked.clear());
await sim({ tilt: { roll: 34 } });
await page.waitForFunction(() => /Rollover/.test(document.getElementById("fault-banner").textContent), null, { timeout: 5000 }).catch(() => {});
const banner = await page.$eval("#fault-banner", (e) => ({ hidden: e.hidden, text: e.textContent, sev: e.dataset.sev }));
check(!banner.hidden && banner.sev === "bad" && /Rollover/.test(banner.text), `tilt alarm shows ("${banner.text.slice(0, 50)}")`);
const played = await page.evaluate(() => (window.teryxSound || { log: [] }).log.map((x) => x.kind));
check(played.includes("bad"), `alarm sound played (${played.slice(-4).join(",")})`);
await shot("live-alert-tilt");
await page.click('#fault-banner [data-a="hide"]');
check(await page.$eval("#fault-banner", (e) => e.hidden), "OK hides the alarm");
await sim({ tilt: { roll: 27 } });
await sleep(1200);
check(/side slope/i.test(await page.$eval("#fault-banner", (e) => e.textContent)), "drops to a warning when less steep");
await sim({ tilt: null });
await sleep(1200);
check(await page.$eval("#fault-banner", (e) => e.hidden), "alert clears when level again");
await sim({ soc: 15 });
await page.waitForFunction(() => /Battery low/.test(document.getElementById("fault-banner").textContent), null, { timeout: 5000 }).catch(() => {});
check(/Battery low/.test(await page.$eval("#fault-banner", (e) => e.textContent)), "low battery warning");
await sim({ soc: 85 });

// Day/night by the sun
const sun = await page.evaluate(async () => {
  const t = await import("/js/theme.js");
  const st = { get: () => undefined }, set = { get: (k) => (k === "themeRegion" ? "canterbury" : undefined) };
  return {
    noon: t.autoTheme(st, set, new Date("2026-12-21T00:00:00Z")).theme,      // 1 pm NZDT
    midnight: t.autoTheme(st, set, new Date("2026-12-21T12:00:00Z")).theme,  // 1 am NZDT
    gps: t.autoTheme({ get: (k) => ({ "pi.gps.fix": true, "pi.gps.lat": 51.5, "pi.gps.lon": 0 })[k] }, set, new Date("2026-12-21T12:00:00Z")).theme, // London midday
  };
});
check(sun.noon === "day" && sun.midnight === "night", `auto theme follows the sun (${sun.noon}/${sun.midnight})`);
check(sun.gps === "day", "auto theme uses the GPS position when there's a fix");

// Fits other screen sizes: 1024x600, and slide-to-arm still works when scaled
const small600 = await browser.newPage({ viewport: { width: 1024, height: 600 } });
small600.on("pageerror", (e) => errors.push(e.message));
await small600.goto(`${BASE}/?screen=winch`);
await sleep(1500);
const fit = await small600.evaluate(() => { const r = document.getElementById("app").getBoundingClientRect(); return { w: r.width, h: r.height, x: r.left, y: r.top, s: window.__teryxScale }; });
check(fit.w <= 1024 && fit.h <= 600 && fit.x >= 0 && fit.y >= 0, `dash fits a 1024x600 screen (${Math.round(fit.w)}x${Math.round(fit.h)} at ${fit.s})`);
const k2 = await (await small600.$("#w-arm .knob")).boundingBox(), a2 = await (await small600.$("#w-arm")).boundingBox();
await small600.mouse.move(k2.x + k2.width / 2, k2.y + k2.height / 2);
await small600.mouse.down();
await small600.mouse.move(a2.x + a2.width - 12, k2.y + k2.height / 2, { steps: 10 });
await small600.mouse.up();
s = await waitFor((s) => s["winch.armed"] === true);
check(s["winch.armed"] === true, "slide to arm works on a scaled screen");
if (SHOTS) await small600.screenshot({ path: `${SHOTS}/live-1024x600.png` });
await small600.click("#w-arm");
await waitFor((s) => s["winch.armed"] === false);
await small600.close();

// Media: music plays, dips under an alert and in reverse, the phone takes over, CarPlay test picture
const audio = (cmd) => fetch(`${BASE}/api/audio/sim`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(cmd) }).then((r) => r.json());
const audioState = () => fetch(`${BASE}/api/audio`).then((r) => r.json());
await audio({ phone: false });
await sim({ scenario: "idle" });
await nav("media");
await page.click('#md-tabs button[data-k="music"]');
await page.waitForSelector(".md-track", { timeout: 5000 });
await page.click('.md-track[data-i="0"]');
await sleep(2000);
const mp = await page.evaluate(() => ({ playing: teryxMedia.player.playing, vol: teryxMedia.player.a.volume, level: teryxMedia.mixer.level }));
check(mp.playing, "a demo tune plays from the Pi");
check(Math.abs(mp.vol - mp.level) < 0.02, `music plays at the volume set (${mp.vol.toFixed(2)})`);
check(await page.$eval("#tb-media", (e) => !e.hidden && e.textContent.includes("Gravel Road")), "top bar shows what's playing");
await shot("live-media-music");
await page.evaluate(() => teryxSound.play("warn"));
await sleep(500);
let md = await page.evaluate(() => ({ ducked: teryxMedia.mixer.ducked, vol: teryxMedia.player.a.volume, level: teryxMedia.mixer.level, to: teryxMedia.mixer.duckTo }));
check(md.ducked && md.vol < md.level * md.to + 0.02, `music dips under an alert sound (${md.vol.toFixed(2)})`);
check((await audioState()).ducked === true, "phone audio on the Pi is told to dip too");
await sleep(3200);
md = await page.evaluate(() => ({ ducked: teryxMedia.mixer.ducked, vol: teryxMedia.player.a.volume, level: teryxMedia.mixer.level }));
check(!md.ducked && Math.abs(md.vol - md.level) < 0.02, "music comes back up after the alert");
await sim({ direction: "reverse" });
await sleep(1200);
check(await page.evaluate(() => teryxMedia.mixer.reasons.has("reverse")), "music drops while reversing");
await sim({ scenario: "idle" });
await sleep(4500);
await nav("media");
check(await page.evaluate(() => !teryxMedia.mixer.reasons.has("reverse")), "and comes back up out of reverse");
// Bluetooth phone (the sim's pretend phone)
await page.click('#md-tabs button[data-k="phone"]');
await audio({ phone: true });
await sleep(2500);
const ph = await page.evaluate(() => ({ np: teryxMedia.nowPlaying(), music: teryxMedia.player.playing }));
check(ph.np.source === "phone" && ph.np.playing, `phone audio shows as playing ("${ph.np.title}")`);
check(!ph.music, "music here pauses when the phone starts playing");
await page.click("#md-next");
await sleep(600);
check((await audioState()).bt.player.title !== ph.np.title, "next track button skips on the phone");
await page.click("#md-play");
await sleep(600);
check((await audioState()).bt.player.status === "paused", "pause button pauses the phone");
await shot("live-media-phone");
await audio({ phone: false });
// CarPlay with no adapter: the test picture fills the screen, nav and alerts stay
await page.click('#md-tabs button[data-k="carplay"]');
await page.click('#cp-body button[data-a="test"]');
await sleep(300);
check(await page.$eval("#md-cp", (e) => !e.hidden), "CarPlay test picture fills the media screen");
check(await page.$eval("#nav", (e) => e.getBoundingClientRect().width > 50), "nav still shows over CarPlay");
await page.click("#md-cp-back");
check(await page.$eval("#md-cp", (e) => e.hidden), "back to the Media tabs from CarPlay");
await page.evaluate(() => { teryxMedia.carplay.stopTest(); teryxMedia.player.stop(); });
await nav("settings");
await page.click('#s-nav button[data-k="audio"]');
await sleep(800);
check((await page.$$("#s-body .btn.sm")).length >= 3, "Settings > Audio lists the outputs");
await shot("live-settings-audio");

// The virtual Teryx runs off the same feed
const v = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const verr = []; v.on("pageerror", (e) => verr.push(e.message));
await v.goto(`${BASE}/virtual`);
await sleep(2500);
check(verr.length === 0 && (await v.$("canvas")) !== null, `virtual Teryx runs alongside the dash ${verr.join(" | ")}`);
await v.close();

check(errors.length === 0, `no page errors ${errors.join(" | ")}`);
await sim({ scenario: "idle" });
await browser.close();
console.log(failed ? `\n${failed} failed` : "\nall passed");
process.exit(failed ? 1 : 0);
