// Dash-side settings (things the Pi decides: look, units, camera, light names).
// Safety limits live on the control box and are edited through /api/pico-settings.
// Saved on the Pi via /api/settings, with localStorage as a fallback (demo mode, no server).

import { FEATURE_DEFAULTS } from "./features.js";
import { CAMP_DEFAULTS } from "./fun/campcalc.js";
import { NIGHT_CABIN_DEFAULTS } from "./nightcabin.js";
import { BAR_PRESET_DEFAULTS } from "./barstack.js";

export const LIGHTS = [
  { id: "light.front_1", name: "Bar 1", where: "Grille, top", dimmable: true },
  { id: "light.front_2", name: "Bar 2", where: "Grille, 2nd down", dimmable: true },
  { id: "light.front_3", name: "Bar 3", where: "Grille, 3rd down", dimmable: true },
  { id: "light.front_4", name: "Bar 4", where: "Grille, bottom", dimmable: true },
  { id: "light.interior", name: "Interior", where: "7\" cab bar", dimmable: true },
];

export const DEFAULTS = {
  units: "kmh",            // kmh | mph
  batteryShow: "pct",      // drive screen battery: pct (78% big, km small) or km (46 km big, % small). Tap it to swap
  look: "auto",            // auto | std (Predator) | offroad (Fossil) | night (Night Hunt). See look.js
  theme: "auto",           // old day/night setting, no longer used (kept so old settings files load)
  themeRegion: "wellington", // rough area for Auto when there's no GPS fix (see theme.js REGIONS)
  packKwh: 7.5,            // traction pack size for the range estimate (72 V x 105 Ah, TBC)
  sound: { enabled: true, volume: 0.7, clicks: true },
  tilt: { rollWarn: 25, rollBad: 32, pitchWarn: 28, pitchBad: 35 },   // degrees, for the tilt alerts
  service: { dueKm: 0 },    // service reminder light at this odometer reading, 0 = off
  powerMaxKw: 10,          // scale of the power bar (7.5 kW motor, peaks above)
  regenFrom: "throttle",   // how the dash spots regen: throttle (moving + throttle at rest) | current (amps back into the pack). See regen.js
  cells: 24,               // for a voltage-based battery % if the Shinegle doesn't send one (72V pack, TBC)
  lights: Object.fromEntries(LIGHTS.map((l) => [l.id, { name: l.name, dimmable: l.dimmable }])),
  nightCabin: { ...NIGHT_CABIN_DEFAULTS },   // Night mode fades the cabin light to this % (nightcabin.js)
  // Front bars (barstack.js): Low / Med / High are saved levels for the 4 bars ("Save as" in
  // the Each bar menu changes them). barOrder is the order the one slider fills them in:
  // top (1 2 3 4), bottom (4 3 2 1) or middle (2 3 1 4).
  barPresets: structuredClone(BAR_PRESET_DEFAULTS),
  barOrder: "top",
  lightPresets: {
    trail: { "light.front_1": 0, "light.front_2": 255, "light.front_3": 255, "light.front_4": 0 },
    work:  { "light.front_1": 255, "light.front_2": 255, "light.front_3": 255, "light.front_4": 255 },
    spot:  { "light.front_1": 255, "light.front_2": 0, "light.front_3": 0, "light.front_4": 255 },
  },
  camera: {
    source: "auto",        // auto | usb | stream
    streamUrl: "/api/camera.mjpg",
    guideOffset: 0,        // nudge guide lines left/right (px)
    autoOnReverse: true,
    trailerInReverse: true, // in reverse, show the trailer camera if a trailer is plugged in
    // Is a trailer camera there? "either": a picture on its video board input, or (until that's
    // been checked) the trailer plug's reed switch. "plug": reed switch only. "picture": picture only.
    trailerDetect: "either",
    reverseView: "single",  // reverse pops up one big camera ("single") or the combined view ("combo")
    current: "rear",       // last camera picked on the Cameras screen ("combo" = the combined view)
    // Combined view: the video board shows one camera at a time. 0 = the live one follows what
    // you're doing (front driving forward, rear or trailer in reverse) and you tap to swap.
    // 3, 5 or 10 = take turns every that many seconds (not in reverse).
    comboCycle: 0,
    // One entry per camera (see CAMS in screens/camera.js). No USB cameras (docs/cameras.md):
    // all four are car cameras (CVBS/PAL) on the analogue video board on the ribbon port, and
    // v4l2Device "adv:N" is its input N (rear 0, trailer 1, cabin 2, front 3). "csi0"/"csi1" (a
    // Pi ribbon camera) still works. All come through the server stream. deviceId is only for a
    // browser camera on the bench.
    // Rear cameras are usually mirrored so left is left.
    cams: {
      rear:    { fitted: true,  name: "Rear",    deviceId: "", v4l2Device: "adv:0", mirror: true,  guides: true },
      front:   { fitted: true,  name: "Front",   deviceId: "", v4l2Device: "adv:3", mirror: false, guides: false },
      trailer: { fitted: false, name: "Trailer", deviceId: "", v4l2Device: "adv:1", mirror: true,  guides: true },
      // Small analogue camera looking at the seats, on the video board's spare input (later).
      // Takes the face shot when someone tries the key while locked.
      cabin:   { fitted: false, name: "Cabin",   deviceId: "", v4l2Device: "adv:2", mirror: false, guides: false },
    },
  },
  // Sentry and dashcam (docs/sentry.md). Read by the dash server (sentry.py) too.
  sentry: {
    enabled: true,         // watch and record while locked with the key off
    dashcam: true,         // loop recording while the key is on
    maxHours: 12,          // sentry gives up after this long...
    min12v: 12.2,          // ...or when the 12V battery drops under this
    storage: "/mnt/teryx-video",
    eventsPct: 25,         // share of the video drive kept for saved clips
    width: 1280, height: 720, fps: 15, kbps: 2000,
  },
  rc: { allow4g: false },  // remote driving over 4G (docs/rc-beach-launch.md). Off by default, needs the PIN to change
  features: { ...FEATURE_DEFAULTS },   // what's wired up yet; the rest shows greyed out (see features.js)
  updates: { channel: "stable", auto_check: true },
  media: {
    volume: 0.6,           // music level (alerts have their own, under sound.volume)
    duckTo: 0.25,          // music drops to this share of its level while an alert sounds
    quietInReverse: true,  // and while reversing, so you can hear what's behind you
    source: "music",       // last tab picked on the Media screen
    stations: [            // internet radio. RNZ's own stream links (HLS, played through the Pi's ffmpeg)
      { name: "RNZ National", url: "https://rnz.streamguys1.com/national/national/playlist.m3u8" },
      { name: "RNZ Concert", url: "https://rnz.streamguys1.com/concert/concert/playlist.m3u8" },
    ],
    carplay: { autoStart: true, hand: "rhd" },   // NZ is right-hand drive
  },
  fun: {
    eggs: [],              // easter eggs found so far (fun/eggs.js)
    digBest: 0,            // Fossil Dig: most brushes to spare
    duelBestMs: 0,         // Roar Duel solo: quickest reaction
    camp: { ...CAMP_DEFAULTS },   // camp mode battery maths (fun/campcalc.js)
  },
};

function merge(a, b) {
  const out = Array.isArray(a) ? [...a] : { ...a };
  for (const [k, v] of Object.entries(b || {})) {
    out[k] = v && typeof v === "object" && !Array.isArray(v) && a && typeof a[k] === "object" ? merge(a[k], v) : v;
  }
  return out;
}

/** Older settings files had one camera (camera.deviceId, .mirror, .guides, .v4l2Device). Those are the rear camera now.
 *  Before 26 Nov the front was a Pi Camera Module 3 on csi0; it's a car camera on video board input 3 now. */
export function migrate(v) {
  const c = v.camera || {};
  for (const k of ["deviceId", "mirror", "guides", "v4l2Device"]) {
    if (k in c) { if (c[k] !== "" && c[k] != null) c.cams.rear[k] = c[k]; delete c[k]; }
  }
  if (c.cams && c.cams.front && c.cams.front.v4l2Device === "csi0") c.cams.front.v4l2Device = "adv:3";
  return v;
}

export class Settings {
  constructor() { this.v = structuredClone(DEFAULTS); this.subs = new Set(); this.server = false; }
  async load() {
    try {
      const r = await fetch("/api/settings", { cache: "no-store" });
      if (r.ok) { this.v = migrate(merge(DEFAULTS, await r.json())); this.server = true; return; }
    } catch {}
    try { const j = localStorage.getItem("teryx.settings"); if (j) this.v = migrate(merge(DEFAULTS, JSON.parse(j))); } catch {}
  }
  get(path) { return path.split(".").reduce((o, k) => (o == null ? o : o[k]), this.v); }
  set(path, value) {
    const keys = path.split(".");
    let o = this.v;
    // Keys like "lights.light.front_1.name" contain dots in the id, so join the middle back up.
    if (keys[0] === "lights" && keys.length > 3) { o = o.lights[keys.slice(1, -1).join(".")]; o[keys.at(-1)] = value; }
    else { keys.slice(0, -1).forEach((k) => (o = o[k] ??= {})); o[keys.at(-1)] = value; }
    this.save();
    [...this.subs].forEach((fn) => fn(path, value));   // copy, so a subscriber added now isn't called in this round
  }
  light(id) { return this.v.lights[id] || { name: id, dimmable: true }; }
  subscribe(fn) { this.subs.add(fn); }
  save() {
    clearTimeout(this._t);
    this._t = setTimeout(async () => {
      try { localStorage.setItem("teryx.settings", JSON.stringify(this.v)); } catch {}
      if (this.server) {
        try { await fetch("/api/settings", { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify(this.v) }); } catch {}
      }
    }, 300);
  }
}
