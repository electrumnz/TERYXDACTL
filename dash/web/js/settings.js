// Dash-side settings (things the Pi decides: look, units, camera, light names).
// Safety limits live on the control box and are edited through /api/pico-settings.
// Saved on the Pi via /api/settings, with localStorage as a fallback (demo mode, no server).

import { FEATURE_DEFAULTS } from "./features.js";

export const LIGHTS = [
  { id: "light.front_1", name: "Bar 1", where: "Front far left", dimmable: true },
  { id: "light.front_2", name: "Bar 2", where: "Front inner left", dimmable: true },
  { id: "light.front_3", name: "Bar 3", where: "Front inner right", dimmable: true },
  { id: "light.front_4", name: "Bar 4", where: "Front far right", dimmable: true },
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
  powerMaxKw: 10,          // scale of the power bar (7.5 kW motor, peaks above)
  regenMaxKw: 4,
  cells: 24,               // for a voltage-based battery % if the Shinegle doesn't send one (72V pack, TBC)
  lights: Object.fromEntries(LIGHTS.map((l) => [l.id, { name: l.name, dimmable: l.dimmable }])),
  lightPresets: {
    trail: { "light.front_1": 0, "light.front_2": 255, "light.front_3": 255, "light.front_4": 0 },
    work:  { "light.front_1": 255, "light.front_2": 255, "light.front_3": 255, "light.front_4": 255 },
    spot:  { "light.front_1": 255, "light.front_2": 0, "light.front_3": 0, "light.front_4": 255 },
  },
  camera: {
    source: "auto",        // auto | usb | stream
    deviceId: "",          // which video device (USB camera or USB AV capture dongle)
    streamUrl: "/api/camera.mjpg",
    mirror: true,          // rear cameras are usually mirrored so left is left
    guides: true,
    guideOffset: 0,        // nudge guide lines left/right (px)
    autoOnReverse: true,
  },
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
};

function merge(a, b) {
  const out = Array.isArray(a) ? [...a] : { ...a };
  for (const [k, v] of Object.entries(b || {})) {
    out[k] = v && typeof v === "object" && !Array.isArray(v) && a && typeof a[k] === "object" ? merge(a[k], v) : v;
  }
  return out;
}

export class Settings {
  constructor() { this.v = structuredClone(DEFAULTS); this.subs = new Set(); this.server = false; }
  async load() {
    try {
      const r = await fetch("/api/settings", { cache: "no-store" });
      if (r.ok) { this.v = merge(DEFAULTS, await r.json()); this.server = true; return; }
    } catch {}
    try { const j = localStorage.getItem("teryx.settings"); if (j) this.v = merge(DEFAULTS, JSON.parse(j)); } catch {}
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
