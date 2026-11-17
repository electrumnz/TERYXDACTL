// Trip figures and range. On the Pi these come from the server (/api/trips), which logs
// trips even if the screen restarts. In demo mode (no server) a small copy runs in the page.

// Range learning. Same numbers and maths as dash/server/teryx_dash/trips.py: keep them in step.
const DEFAULT_WH_PER_KM = 180, MIN_WH_PER_KM = 30;
const CHUNK_KM = 0.25, RECENT_KM = 20, HALF_LIFE_KM = 5, PRIOR_KM = 1.5, LEARNT_KM = 5;
const LEARN_KEY = "teryx.demo.rangeLearning";

/** Learnt Wh/km from recent (km, net Wh) chunks, oldest first, pulled toward the lifetime average. */
export function learnWhPerKm(chunks, life) {
  const hasAvg = life.km >= 2;
  const prior = hasAvg ? Math.max(MIN_WH_PER_KM, (life.used_wh - life.regen_wh) / life.km) : DEFAULT_WH_PER_KM;
  let wKm = 0, wWh = 0, back = 0;
  for (let i = chunks.length - 1; i >= 0; i--) {
    const [km, wh] = chunks[i], w = 0.5 ** (back / HALF_LIFE_KM);
    wKm += w * km; wWh += w * wh; back += km;
  }
  if (back < CHUNK_KM) return [prior, hasAvg ? "average" : "guess", back];
  return [Math.max(MIN_WH_PER_KM, (prior * PRIOR_KM + wWh) / (PRIOR_KM + wKm)), back >= LEARNT_KM ? "learnt" : "learning", back];
}

function loadLearning() {
  try {
    const d = JSON.parse(localStorage.getItem(LEARN_KEY) || "null");
    if (d && Array.isArray(d.chunks) && d.life) return d;
  } catch {}
  return { chunks: [], life: { km: 0, used_wh: 0, regen_wh: 0 } };
}
function saveLearning(d) { try { localStorage.setItem(LEARN_KEY, JSON.stringify(d)); } catch {} }

function blank(now, soc) { return { start: now / 1000, end: now / 1000, km: 0, used_wh: 0, regen_wh: 0, max_kmh: 0, moving_s: 0, soc_start: soc, soc_end: soc }; }

function figures(t) {
  if (!t) return null;
  const net = t.used_wh - t.regen_wh;
  return { ...t, net_wh: net, wh_per_km: t.km >= 0.1 ? net / t.km : null, avg_kmh: t.moving_s > 10 ? t.km / (t.moving_s / 3600) : null };
}

/** In-page trip meter for demo mode. Same shape as /api/trips. */
class LocalTrips {
  constructor() {
    const now = Date.now(); this.cur = blank(now); this.a = blank(now); this.last = null;
    // What it's learnt about range is kept in this browser, so the demo keeps learning across reloads.
    this.learn = loadLearning(); this.chunk = [0, 0]; this.savedAt = 0;
  }
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
    const L = this.learn;
    L.life.km += km; if (wh >= 0) L.life.used_wh += wh; else L.life.regen_wh -= wh;
    this.chunk[0] += km; this.chunk[1] += wh;
    if (this.chunk[0] >= CHUNK_KM) {
      L.chunks.push([this.chunk[0], this.chunk[1]]); this.chunk = [0, 0];
      while (L.chunks.reduce((a, c) => a + c[0], 0) - L.chunks[0][0] >= RECENT_KM) L.chunks.shift();
    }
    if (now - this.savedAt > 5000) { this.savedAt = now; saveLearning(L); }
  }
  summary(st, packKwh) {
    const [whk, basis, learnt] = learnWhPerKm(this.learn.chunks, this.learn.life);
    const soc = st.get("mc.soc");
    const left = soc == null ? null : (soc / 100) * packKwh;
    return {
      current: figures(this.cur), trip_a: figures(this.a), lifetime: figures(this.learn.life), history: [],
      wh_per_km: whk, basis, learnt_km: learnt, pack_kwh: packKwh,
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
