// Teryx dash: app shell. Wires the store, the link to the gateway, settings and the screens together.
import { Store } from "./store.js";
import { Link } from "./link.js";
import { Settings } from "./settings.js";
import { icon } from "./ui/icons.js";
import { el, toast } from "./ui/controls.js";
import { REJECTS } from "./text.js";
import { Alerts } from "./alerts.js";
import { Sound } from "./sound.js";
import { autoTheme } from "./theme.js";
import { LookPicker, LOOKS } from "./look.js";
import { NightCabin } from "./nightcabin.js";
import { TripData } from "./tripdata.js";
import { fitToScreen } from "./fit.js";
import { keyboardOpen } from "./ui/keyboard.js";
import { TripsScreen } from "./screens/trips.js";
import { DriveScreen } from "./screens/drive.js";
import { DrivetrainScreen } from "./screens/drivetrain.js";
import { LightsScreen } from "./screens/lights.js";
import { WinchScreen } from "./screens/winch.js";
import { TrayScreen } from "./screens/tray.js";
import { CameraScreen } from "./screens/camera.js";
import { SettingsScreen } from "./screens/settings.js";
import { MediaScreen } from "./screens/media.js";
import { FunScreen } from "./screens/fun.js";
import { wireEggs } from "./fun/eggs.js";
import { MediaHub } from "./media/hub.js";
import { demoPlayer } from "./ui/demoplayer.js";
import { featureOn, featureName } from "./features.js";
import { volumeControl } from "./ui/volume.js";
import { WinchHeat } from "./winchheat.js";
import { ShiftWatch } from "./ui/shift.js";
import { LockScreen } from "./lock.js";

// Fallback limits if the control box settings can't be read (match config/io-map.yaml safety defaults).
const LIMIT_DEFAULTS = { fourwd_max_kmh: 1, diff_max_kmh: 15, tray_overcurrent_da: 10, winch_auto_disarm_s: 120, shift_wait_ms: 10000 };

const store = new Store();
const settings = new Settings();
const link = new Link(store);

const ctx = {
  store, settings, link, current: null, picoSettings: {},
  picoLimit(name, d) { const v = this.picoSettings[name]; return v == null ? (LIMIT_DEFAULTS[name] ?? d) : v; },
  async setPicoSetting(name, value) {
    if (store.get("link.demo")) return;
    try {
      const r = await fetch("/api/pico-settings", { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify({ name, value }) });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || r.status);
      loadPicoLimits();
    } catch (e) { toast(`Control box didn't take that setting (${e.message}).`, "bad"); }
  },
  themeInfo() {
    const prev = document.body.classList.contains("theme-day") ? "day" : "night";
    return autoTheme(store, settings, new Date(), prev);
  },
  // The look (Predator, Fossil or Night Hunt) follows 4WD, lights and the sun. See look.js.
  lookInfo() { return ctx.looks.pick(new Date()); },
  applyTheme() {
    const { look, dark } = ctx.looks.pick(new Date());
    ctx.nightCabin.tick(dark);   // Night mode fades the cabin light down (nightcabin.js)
    const cls = `look-${look} theme-${dark ? "night" : "day"}`;
    if (document.body.className !== cls) {
      document.body.className = cls;
      document.getElementById("tb-look").textContent = LOOKS[look];
    }
  },
  applySound() {
    Sound.enabled = settings.get("sound.enabled") !== false;
    Sound.volume = settings.get("sound.volume") ?? 0.7;
    Sound.clicks = settings.get("sound.clicks") !== false;
  },
  show(id) { show(id); },
};

ctx.looks = new LookPicker(store, settings);
ctx.nightCabin = new NightCabin(ctx);
ctx.alerts = new Alerts(store, settings);
ctx.winchHeat = new WinchHeat();
ctx.shift = new ShiftWatch(ctx);   // safe 4WD / diff changes: spinner, wait, cancel, done
ctx.trips = new TripData(ctx);
ctx.media = new MediaHub(ctx);
// Music dips under every alert sound. Alerts themselves always play at their own volume.
Sound.onPlay = (kind) => ctx.media.mixer.pulse(kind === "bad" ? 4000 : 2500);

const screens = [DriveScreen, TripsScreen, DrivetrainScreen, LightsScreen, WinchScreen, TrayScreen, CameraScreen, MediaScreen, FunScreen, SettingsScreen].map((C) => new C(ctx));
const byId = Object.fromEntries(screens.map((s) => [s.id, s]));

function buildNav() {
  const nav = document.getElementById("nav"), main = document.getElementById("screens");
  screens.forEach((s) => {
    const b = el(`<button class="nav-btn" data-id="${s.id}">${icon(s.icon)}<span>${s.label}</span></button>`);
    b.onclick = () => show(s.id);
    if (s.id !== "drive" && s.id !== "settings" && s.id !== "fun") b.appendChild(el(`<i class="soon-tag">SOON</i>`));
    nav.appendChild(b);
    const root = el(`<section class="screen" id="screen-${s.id}"></section>`);
    main.appendChild(root);
    s.mount(root);
    s.el = root;
  });
}

// Grey out the nav buttons for features that aren't wired up yet (Settings > Features).
function markFeatures() {
  document.querySelectorAll(".nav-btn").forEach((b) => b.classList.toggle("soon", !featureOn(settings, b.dataset.id)));
}

function show(id) {
  const next = byId[id]; if (!next || next === ctx.current) return;
  if (!featureOn(settings, id)) {
    toast(`${featureName(id)} isn't wired up yet. Switch it on in Settings > Features once it's fitted.`);
    return;
  }
  if (ctx.current) { ctx.current.el.classList.remove("active"); ctx.current.hide && ctx.current.hide(); }
  ctx.current = next;
  next.el.classList.add("active");
  next.show && next.show();
  next.update(store);
  document.querySelectorAll(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.id === id));
  try { localStorage.setItem("teryx.screen", id); } catch {}
}

// ---- top bar, alerts, reverse camera ----
let beforeReverse = null, reverseOffTimer = null;

function topbar(st) {
  const g = document.getElementById("tb-gear");
  const dir = st.get("mc.direction", "neutral");
  g.textContent = dir === "forward" ? "D" : dir === "reverse" ? "R" : "N";
  g.className = `gear-chip ${dir === "forward" ? "d" : dir === "reverse" ? "r" : ""}`;
  document.getElementById("tb-hb").hidden = !st.get("in.park");
  document.getElementById("tb-mode").textContent = String(st.get("mc.mode", "normal")).toUpperCase();
  const fw = st.get("act.4wd", "2wd"), c4 = document.getElementById("tb-4wd");
  c4.textContent = fw === "4wd" || fw === "to_4wd" ? "4WD" : "2WD";
  c4.className = `tb-chip ${fw === "4wd" ? "on" : fw.startsWith("to_") || st.get("act.4wd_wait") ? "busy" : ""}`;
  const d = Math.round(st.get("an.diff_pos", 0)), cd = document.getElementById("tb-diff");
  cd.textContent = `DIFF ${d}%`; cd.className = `tb-chip ${d > 2 ? "on" : ""}`;
  const v12 = st.get("an.aux_12v");
  const e12 = document.getElementById("tb-12v");
  e12.textContent = v12 == null ? "--" : `${v12.toFixed(1)}V`;
  e12.style.color = v12 != null && v12 < 11.8 ? "var(--bad)" : "";
  const ok = st.get("link.online") && st.get("pico.online");
  const dot = document.getElementById("tb-link");
  dot.className = `tb-dot ${ok ? "ok" : ""}`;
  dot.title = !st.get("link.online") ? "No link to the dash server" : !st.get("pico.online") ? "Control box offline" : "Control box online";
  const wifi = st.get("pi.wifi");
  document.getElementById("tb-wifi").innerHTML = icon(wifi === false ? "wifioff" : "wifi");
  document.getElementById("tb-wifi").style.color = wifi === false ? "var(--dim)" : "var(--muted)";

  let alert = "";
  if (!st.get("link.online")) alert = "NO LINK TO DASH SERVER";
  else if (!st.get("pico.online")) alert = "CONTROL BOX OFFLINE";
  else if (st.get("mc.online") === false) alert = "NO DATA FROM MOTOR CONTROLLER";
  else if (st.get("link.demo")) alert = "DEMO MODE";
  document.getElementById("tb-alert").textContent = alert;
  document.getElementById("tb-alert").style.color = st.get("link.demo") && alert === "DEMO MODE" ? "var(--info)" : "";
}

// Alerts banner: the worst alert not yet OK'd, along the bottom.
function alertBanner(st) {
  ctx.alerts.tick(st);
  const now = ctx.alerts.active, open = ctx.alerts.unacked();
  const banner = document.getElementById("fault-banner");
  const worst = open[0];
  if (!worst) banner.hidden = true;
  else {
    banner.hidden = false;
    banner.dataset.sev = worst.sev;
    const more = open.length > 1 ? ` (+${open.length - 1} more)` : "";
    const html = `<span class="fb-text">${worst.text}${more}</span><span class="fb-btns"><button class="fb-btn" data-a="view">VIEW</button><button class="fb-btn" data-a="hide">OK</button></span>`;
    if (banner._h !== html) {
      banner.innerHTML = html; banner._h = html;
      banner.querySelector('[data-a="view"]').onclick = () => { show("settings"); byId.settings.open("faults"); };
      banner.querySelector('[data-a="hide"]').onclick = () => { ctx.alerts.ack(); banner.hidden = true; };
    }
  }
  // Keep the music down while a serious alarm is still waiting for OK.
  ctx.media.mixer.hold("alarm", open.some((a) => a.sev === "bad"));
  const bad = now.some((a) => a.sev === "bad"), any = now.length > 0;
  const badge = document.querySelector('.nav-btn[data-id="settings"] .badge');
  if (any && !badge) document.querySelector('.nav-btn[data-id="settings"]').appendChild(el(`<span class="badge"></span>`));
  if (!any && badge) badge.remove();
  const b2 = document.querySelector('.nav-btn[data-id="settings"] .badge');
  if (b2) b2.classList.toggle("warn", !bad);
}

function reverseCamera(st) {
  const rev = st.get("mc.direction") === "reverse" || !!st.get("in.reverse");
  ctx.media.mixer.hold("reverse", rev && settings.get("media.quietInReverse") !== false);
  if (!settings.get("camera.autoOnReverse")) return;
  if (rev) {
    clearTimeout(reverseOffTimer); reverseOffTimer = null;
    if (ctx.current.id !== "camera" && !keyboardOpen()) { beforeReverse = ctx.current.id; show("camera"); }
  } else if (beforeReverse && !reverseOffTimer) {
    // Stay on the camera for a few seconds after leaving reverse (handy for shuffling back and forth).
    reverseOffTimer = setTimeout(() => { if (ctx.current.id === "camera") show(beforeReverse); beforeReverse = null; reverseOffTimer = null; }, 3000);
  }
}

// Control box limits, for lockout hints. The control box is still the one that enforces them.
async function loadPicoLimits() {
  try {
    const r = await fetch("/api/pico-settings", { cache: "no-store" });
    if (r.ok) (await r.json()).settings.forEach((x) => (ctx.picoSettings[x.name] = x.scale ? x.value * x.scale : x.value));
  } catch {}
}

// ---- start up ----
function soundButton() {
  const b = document.getElementById("tb-sound");
  const draw = () => { b.innerHTML = icon(settings.get("sound.enabled") === false ? "belloff" : "bell"); b.classList.toggle("off", settings.get("sound.enabled") === false); };
  b.onclick = () => {
    // One tap: OK any beeping alarm. If nothing is beeping, mute or unmute.
    if (ctx.alerts.unacked().length) { ctx.alerts.ack(); document.getElementById("fault-banner").hidden = true; return; }
    settings.set("sound.enabled", settings.get("sound.enabled") === false); ctx.applySound(); draw();
    toast(settings.get("sound.enabled") ? "Sounds on." : "Sounds off. Alerts still show on screen.");
  };
  settings.subscribe((path) => { if (path.startsWith("sound")) draw(); });
  draw();
}

// Small "now playing" chip in the top bar. Tap it to go to Media.
function nowPlayingChip() {
  const chip = document.getElementById("tb-media");
  chip.onclick = () => show("media");
  const draw = () => {
    const np = ctx.media.nowPlaying();
    const on = !!(np.title && np.playing);
    chip.hidden = !on;
    if (!on) return;
    const html = `${icon(ctx.media.mixer.ducked ? "volume" : "music")}<span>${np.title.replace(/</g, "&lt;")}</span>`;
    if (chip._h !== html) { chip.innerHTML = html; chip._h = html; }
    chip.classList.toggle("ducked", ctx.media.mixer.ducked);
  };
  ctx.media.on(draw);
  setInterval(draw, 2000);
  draw();
}

// Splash: shows from the first paint (it's in index.html) until the first live state arrives.
function hideSplash() {
  const sp = document.getElementById("splash"); if (!sp || sp.classList.contains("gone")) return;
  sp.classList.add("gone");
  setTimeout(() => sp.remove(), 400);
}

async function main() {
  fitToScreen();
  const splashMsg = document.getElementById("splash-msg");
  if (splashMsg) splashMsg.textContent = "Loading settings";
  await settings.load();
  ctx.applySound();
  ctx.media.applySettings();
  ctx.applyTheme();
  setInterval(() => ctx.applyTheme(), 2000);
  buildNav();
  markFeatures();
  settings.subscribe((path) => { if (path.startsWith("features")) markFeatures(); });
  soundButton();
  wireEggs(ctx);
  volumeControl(ctx, document.getElementById("tb-vol"));
  const player = demoPlayer();
  document.getElementById("app").appendChild(player.root);
  let first = "drive";
  try { first = new URLSearchParams(location.search).get("screen") || localStorage.getItem("teryx.screen") || "drive"; } catch {}
  show(byId[first] ? first : "drive");

  store.on("reject", (code) => {
    Sound.play("reject");
    const locked = store.get("lock.state") === "locked" && code === "interlock";
    toast(locked ? "The Teryx is locked." : REJECTS[code] || `Control box said no (${code}).`, "bad");
  });
  ctx.lock = new LockScreen(ctx);
  ctx.alerts.on((fresh) => store.emit("faults-changed", fresh));
  // A tick on every press, so a gloved tap is felt (heard) even if nothing moves yet.
  document.addEventListener("pointerdown", (e) => { if (e.target.closest("button, .lt-big, .slider, select")) Sound.play("click"); }, true);
  let firstState = true;
  store.subscribe((st) => {
    if (firstState && (st.get("pico.online") || st.get("link.demo"))) { firstState = false; hideSplash(); }
    const wh = ctx.winchHeat.tick(st);
    st.s["dash.winch_heat"] = { pct: wh.pct, state: wh.state, restS: wh.restLeftS() };  // read by the alerts
    ctx.applyTheme();
    ctx.shift.update(st);
    topbar(st); alertBanner(st); reverseCamera(st); player.update(st);
    ctx.lock.update(st);
    byId.fun.background(st);   // camp mode and games stop by themselves if the Teryx moves
    // Only the screen on show is redrawn, to keep the Pi cool.
    if (ctx.current) ctx.current.update(st);
    // Anything moving stops if we navigate away (each screen's hide() also does this).
  });
  // Keep the winch cooling (and its alerts clearing) even when nothing else changes.
  setInterval(() => { store._dirty = true; }, 1000);
  setInterval(() => {
    const d = new Date();
    document.getElementById("tb-clock").textContent = d.toLocaleTimeString("en-NZ", { hour: "2-digit", minute: "2-digit", hour12: false });
  }, 1000);
  store.loop();
  if (splashMsg) splashMsg.textContent = "Connecting to the control box";
  link.start();
  ctx.trips.start();
  ctx.media.start();
  nowPlayingChip();
  // Don't hold the screen hostage: after a few seconds show the dash anyway (the top bar says what's missing).
  setTimeout(hideSplash, 4000);

  loadPicoLimits();
  window.addEventListener("blur", () => link.stopAllHolds());
}

window.teryx = ctx; // handy from the browser console on the bench
window.teryxSound = Sound;
window.teryxMedia = ctx.media;
main();
