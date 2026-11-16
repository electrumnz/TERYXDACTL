// Teryx dash: app shell. Wires the store, the link to the gateway, settings and the screens together.
import { Store } from "./store.js";
import { Link } from "./link.js";
import { Settings } from "./settings.js";
import { icon } from "./ui/icons.js";
import { el, toast } from "./ui/controls.js";
import { PICO_FAULTS, MC_FAULTS, REJECTS, faultText, asList } from "./text.js";
import { DriveScreen } from "./screens/drive.js";
import { DrivetrainScreen } from "./screens/drivetrain.js";
import { LightsScreen } from "./screens/lights.js";
import { WinchScreen } from "./screens/winch.js";
import { TrayScreen } from "./screens/tray.js";
import { CameraScreen } from "./screens/camera.js";
import { SettingsScreen } from "./screens/settings.js";

// Fallback limits if the control box settings can't be read (match config/io-map.yaml safety defaults).
const LIMIT_DEFAULTS = { fourwd_max_kmh: 5, diff_max_kmh: 15, tray_overcurrent_da: 10, winch_auto_disarm_s: 120 };

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
  applyTheme() {
    let t = settings.get("theme");
    if (t === "auto") { const h = new Date().getHours(); t = h >= 7 && h < 19 ? "day" : "night"; }
    document.body.className = `theme-${t}`;
  },
  show(id) { show(id); },
};

const screens = [DriveScreen, DrivetrainScreen, LightsScreen, WinchScreen, TrayScreen, CameraScreen, SettingsScreen].map((C) => new C(ctx));
const byId = Object.fromEntries(screens.map((s) => [s.id, s]));

function buildNav() {
  const nav = document.getElementById("nav"), main = document.getElementById("screens");
  screens.forEach((s) => {
    const b = el(`<button class="nav-btn" data-id="${s.id}">${icon(s.icon)}<span>${s.label}</span></button>`);
    b.onclick = () => show(s.id);
    nav.appendChild(b);
    const root = el(`<section class="screen" id="screen-${s.id}"></section>`);
    main.appendChild(root);
    s.mount(root);
    s.el = root;
  });
}

function show(id) {
  const next = byId[id]; if (!next || next === ctx.current) return;
  if (ctx.current) { ctx.current.el.classList.remove("active"); ctx.current.hide && ctx.current.hide(); }
  ctx.current = next;
  next.el.classList.add("active");
  next.show && next.show();
  next.update(store);
  document.querySelectorAll(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.id === id));
  try { localStorage.setItem("teryx.screen", id); } catch {}
}

// ---- top bar, faults, reverse camera ----
let lastFaults = new Set();
let beforeReverse = null, reverseOffTimer = null;

function topbar(st) {
  const g = document.getElementById("tb-gear");
  const dir = st.get("mc.direction", "neutral");
  g.textContent = dir === "forward" ? "D" : dir === "reverse" ? "R" : "N";
  g.className = `gear-chip ${dir === "forward" ? "d" : dir === "reverse" ? "r" : ""}`;
  document.getElementById("tb-mode").textContent = String(st.get("mc.mode", "normal")).toUpperCase();
  const fw = st.get("act.4wd", "2wd"), c4 = document.getElementById("tb-4wd");
  c4.textContent = fw === "4wd" || fw === "to_4wd" ? "4WD" : "2WD";
  c4.className = `tb-chip ${fw === "4wd" ? "on" : fw.startsWith("to_") ? "busy" : ""}`;
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

function faults(st) {
  const now = [
    ...asList(st.get("pico.faults")).map((c) => ({ key: `p:${c}`, code: c, text: faultText(c, PICO_FAULTS), sev: (PICO_FAULTS[c] || {}).sev || "bad" })),
    ...asList(st.get("mc.faults")).map((c) => ({ key: `m:${c}`, code: c, text: faultText(c, MC_FAULTS), sev: (MC_FAULTS[c] || {}).sev || "bad" })),
  ];
  const keys = new Set(now.map((f) => f.key));
  const fresh = now.filter((f) => !lastFaults.has(f.key));
  lastFaults = keys;
  if (fresh.length) store.emit("faults-changed", fresh);
  const banner = document.getElementById("fault-banner");
  const worst = now.find((f) => f.sev === "bad") || now[0];
  if (!worst || (ctx.dismissed && ctx.dismissed === [...keys].sort().join())) { banner.hidden = true; }
  else {
    banner.hidden = false;
    banner.style.background = worst.sev === "bad" ? "var(--bad)" : "var(--warn)";
    banner.style.color = worst.sev === "bad" ? "#fff" : "#1a1200";
    const more = now.length > 1 ? ` (+${now.length - 1} more)` : "";
    const html = `<span>${worst.text}${more}</span><span><button data-a="view">VIEW</button> <button data-a="hide">HIDE</button></span>`;
    if (banner._h !== html) {
      banner.innerHTML = html; banner._h = html;
      banner.querySelector('[data-a="view"]').onclick = () => { show("settings"); byId.settings.open("faults"); };
      banner.querySelector('[data-a="hide"]').onclick = () => { ctx.dismissed = [...keys].sort().join(); banner.hidden = true; };
    }
  }
  const badge = document.querySelector('.nav-btn[data-id="settings"] .badge');
  if (now.length && !badge) document.querySelector('.nav-btn[data-id="settings"]').appendChild(el(`<span class="badge"></span>`));
  if (!now.length && badge) badge.remove();
}

function reverseCamera(st) {
  const rev = st.get("mc.direction") === "reverse" || !!st.get("in.reverse");
  if (!settings.get("camera.autoOnReverse")) return;
  if (rev) {
    clearTimeout(reverseOffTimer); reverseOffTimer = null;
    if (ctx.current.id !== "camera") { beforeReverse = ctx.current.id; show("camera"); }
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
async function main() {
  await settings.load();
  ctx.applyTheme();
  setInterval(() => ctx.applyTheme(), 60000);
  buildNav();
  let first = "drive";
  try { first = new URLSearchParams(location.search).get("screen") || localStorage.getItem("teryx.screen") || "drive"; } catch {}
  show(byId[first] ? first : "drive");

  store.on("reject", (code) => toast(REJECTS[code] || `Control box said no (${code}).`, "bad"));
  store.subscribe((st) => {
    topbar(st); faults(st); reverseCamera(st);
    // Only the screen on show is redrawn, to keep the Pi cool.
    if (ctx.current) ctx.current.update(st);
    // Anything moving stops if we navigate away (each screen's hide() also does this).
  });
  setInterval(() => {
    const d = new Date();
    document.getElementById("tb-clock").textContent = d.toLocaleTimeString("en-NZ", { hour: "2-digit", minute: "2-digit", hour12: false });
  }, 1000);
  store.loop();
  link.start();

  loadPicoLimits();
  window.addEventListener("blur", () => link.stopAllHolds());
}

window.teryx = ctx; // handy from the browser console on the bench
main();
