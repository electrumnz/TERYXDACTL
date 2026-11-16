// Trip figures and range. On the Pi these come from the server (/api/trips), which logs
// trips even if the screen restarts. In demo mode (no server) a small copy runs in the page.

const DEFAULT_WH_PER_KM = 180;

function blank(now, soc) { return { start: now / 1000, end: now / 1000, km: 0, used_wh: 0, regen_wh: 0, max_kmh: 0, moving_s: 0, soc_start: soc, soc_end: soc }; }

function figures(t) {
  if (!t) return null;
  const net = t.used_wh - t.regen_wh;
  return { ...t, net_wh: net, wh_per_km: t.km >= 0.1 ? net / t.km : null, avg_kmh: t.moving_s > 10 ? t.km / (t.moving_s / 3600) : null };
}

/** In-page trip meter for demo mode. Same shape as /api/trips. */
class LocalTrips {
  constructor() { const now = Date.now(); this.cur = blank(now); this.a = blank(now); this.last = null; }
  sample(st) {
    const now = Date.now();
    if (this.last == null) { this.last = now; this.cur.soc_start = st.get("mc.soc"); return; }
    const dt = (now - this.last) / 1000; this.last = now;
    if (dt <= 0 || dt > 5) return;
    const spd = st.get("mc.speed", 0), km = (spd * dt) / 3600;
    const wh = (st.get("mc.batt_v", 0) * st.get("mc.batt_a", 0) * dt) / 3600;
    for (const t of [this.cur, this.a]) {
      t.km += km; if (wh >= 0) t.used_wh += wh; else t.regen_wh -= wh;
      t.end = now / 1000; if (spd > 0.5) t.moving_s += dt; t.max_kmh = Math.max(t.max_kmh, spd);
    }
    this.cur.soc_end = st.get("mc.soc");
  }
  summary(st, packKwh) {
    const net = this.cur.used_wh - this.cur.regen_wh;
    const whk = this.cur.km >= 0.5 ? Math.max(30, net / this.cur.km) : DEFAULT_WH_PER_KM;
    const soc = st.get("mc.soc");
    const left = soc == null ? null : (soc / 100) * packKwh;
    return {
      current: figures(this.cur), trip_a: figures(this.a), lifetime: null, history: [],
      wh_per_km: whk, basis: this.cur.km >= 0.5 ? "recent" : "guess", pack_kwh: packKwh,
      kwh_left: left, range_km: left == null ? null : (left * 1000) / whk, local: true,
    };
  }
  reset() { this.a = blank(Date.now()); }
}

export class TripData {
  constructor(ctx) { this.ctx = ctx; this.data = null; this.local = null; this.subs = new Set(); }
  on(fn) { this.subs.add(fn); }
  start() {
    setInterval(() => this.refresh(), 3000);
    setInterval(() => { if (this.local) this.local.sample(this.ctx.store); }, 500);
    this.refresh();
  }
  async refresh() {
    const st = this.ctx.store;
    if (st.get("link.demo")) {
      this.local ??= new LocalTrips();
      this.set(this.local.summary(st, this.ctx.settings.get("packKwh")));
      return;
    }
    try {
      const r = await fetch("/api/trips", { cache: "no-store" });
      if (r.ok) this.set(await r.json());
    } catch {}
  }
  set(d) { this.data = d; this.subs.forEach((fn) => fn(d)); }
  async reset(what) {
    if (this.local) { if (what === "trip-a") this.local.reset(); return this.refresh(); }
    const r = await fetch(`/api/trips/reset/${what}`, { method: "POST" });
    if (!r.ok) throw new Error(`${r.status}`);
    this.set(await r.json());
  }
}

// ---- formatting, shared by the trips and drive screens ----
export function fmtKm(km, mph) { if (km == null) return "--"; const v = mph ? km * 0.621371 : km; return `${v < 10 ? v.toFixed(1) : Math.round(v)} ${mph ? "mi" : "km"}`; }
export function fmtKwh(wh) { return wh == null ? "--" : `${(wh / 1000).toFixed(2)} kWh`; }
export function fmtWhKm(w, mph) { return w == null ? "--" : mph ? `${Math.round(w / 0.621371)} Wh/mi` : `${Math.round(w)} Wh/km`; }
export function fmtDur(s) { if (!s) return "0m"; const h = Math.floor(s / 3600), m = Math.round((s % 3600) / 60); return h ? `${h}h ${m}m` : `${m}m`; }
