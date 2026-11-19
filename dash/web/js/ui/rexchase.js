// The T. rex on the Drive screen, as video. Parked: it breathes with its mouth shut. Pull away:
// it roars, turns and runs, and chases the Teryx through the forest. The chase clip changes with
// speed (stalking, trotting, flat-out sprint, and a lunge when you floor it), and plays a bit
// faster or slower to match. Stop: it pulls up and roars, then shuts its mouth again.
//
// Every clip starts and ends on one of three shared frames ("hubs"), so any clip can follow any
// other with no jump:
//   closed  the head side-on, mouth shut (the same picture as img/dino/head-closed.webp)
//   roar    the same head, mouth wide open (head-roar.webp)
//   run     the T. rex mid-stride in the forest with the Teryx ahead
// The list of clips is video/rex/clips.json. If it's missing or a clip won't play, the still
// pictures stay, so the dash never shows a blank hole.

export const HUB = { closed: "closed", roar: "roar", run: "run" };

// Speed bands for the chase, in km/h. `nominal` is the speed the clip was made to look right at;
// the clip plays at speed / nominal, kept within RATE_MIN..RATE_MAX so it never looks silly.
export const BANDS = [
  { id: "stalk", upTo: 12, nominal: 8 },
  { id: "trot", upTo: 30, nominal: 20 },
  { id: "sprint", upTo: Infinity, nominal: 40 },
];
export const RATE_MIN = 0.8, RATE_MAX = 1.3;
export const MOVING_KMH = 2;     // above this the T. rex wakes up and goes
export const STOP_HOLD_MS = 1200; // below MOVING_KMH this long, it pulls up
export const LUNGE_POWER = 0.7;  // fraction of max power that can trigger a lunge in a sprint

export function bandFor(kmh) {
  const s = Math.abs(kmh);
  return BANDS.find((b) => s < b.upTo) || BANDS[BANDS.length - 1];
}

export function rateFor(kmh, band = bandFor(kmh)) {
  const r = Math.abs(kmh) / band.nominal;
  return Math.max(RATE_MIN, Math.min(RATE_MAX, r || RATE_MIN));
}

/**
 * Pick the clip to play next. Pure, so it can be tested without a browser.
 * clips: [{ id, kind, band?, from, to }]. kind is idle | wake | turn | chase | lunge | stop | settle.
 * at: the hub the last clip ended on. moving: is the Teryx going. power: 0..1 of max.
 * recent: ids played lately (newest last), avoided where there's a choice. rand: () => 0..1.
 */
export function pickNext(clips, { at, moving, kmh = 0, power = 0, recent = [], rand = Math.random }) {
  const from = (kinds, pred = () => true) => clips.filter((c) => c.from === at && kinds.includes(c.kind) && pred(c));
  let pool;
  if (at === HUB.closed) pool = moving ? from(["wake"]) : from(["idle"]);
  else if (at === HUB.roar) pool = moving ? from(["turn"]) : from(["settle"]);
  else if (!moving) pool = from(["stop"]);
  else {
    const band = bandFor(kmh).id;
    if (band === "sprint" && power >= LUNGE_POWER && rand() < 0.4) pool = from(["lunge"]);
    if (!pool || !pool.length) pool = from(["chase"], (c) => c.band === band);
    if (!pool.length) pool = from(["chase"]);     // no clip for this band yet: any chase will do
  }
  if (!pool || !pool.length) pool = clips.filter((c) => c.from === at); // last resort: anything that joins up
  if (!pool.length) return null;
  // Avoid the clips played most lately, if there's anything else.
  for (let keep = recent.length; keep >= 0; keep--) {
    const avoid = new Set(recent.slice(recent.length - keep));
    const fresh = pool.filter((c) => !avoid.has(c.id));
    if (fresh.length) return fresh[Math.floor(rand() * fresh.length) % fresh.length];
  }
  return pool[0];
}

// Loading a new src resets playbackRate to defaultPlaybackRate, so set both.
function setRate(v, r) { v.defaultPlaybackRate = r; v.playbackRate = r; }

/** Two <video> layers that take turns, so the next clip is loaded and waiting before this one ends. */
export class RexChase {
  constructor(host, { base = "video/rex/", onReady, onFail } = {}) {
    this.host = host; this.base = base; this.onReady = onReady; this.onFail = onFail;
    this.clips = []; this.recent = [];
    this.at = HUB.closed; this.moving = false; this.kmh = 0; this.power = 0; this.slowSince = null;
    this.vids = [0, 1].map(() => {
      const v = document.createElement("video");
      v.muted = true; v.playsInline = true; v.preload = "auto"; v.disablePictureInPicture = true;
      v.setAttribute("aria-hidden", "true"); v.className = "rex-vid";
      host.appendChild(v);
      return v;
    });
    this.cur = 0; this.playing = null; this.queued = null; this.failed = false;
    this._tick = this._tick.bind(this);
  }

  async load() {
    try {
      const r = await fetch(this.base + "clips.json", { cache: "no-cache" });
      if (!r.ok) throw new Error(r.status);
      const m = await r.json();
      this.clips = (m.clips || []).filter((c) => c.file && c.from && c.to && c.kind);
    } catch { this.clips = []; }
    if (!this.clips.length) { this.failed = true; return false; }
    this.vids.forEach((v) => v.addEventListener("error", () => this._fail()));
    this._start(this._choose());
    return true;
  }

  /** Feed it the latest speed (km/h) and power (0..1 of max). Cheap: call it on every update. */
  set(kmh, power, now = performance.now()) {
    this.kmh = kmh; this.power = power;
    if (Math.abs(kmh) >= MOVING_KMH) { this.moving = true; this.slowSince = null; }
    else if (this.moving) {
      if (this.slowSince == null) this.slowSince = now;
      else if (now - this.slowSince >= STOP_HOLD_MS) this.moving = false;
    }
    const p = this.playing;
    if (!p) return;
    // Pulled up mid-chase, or took off while it dozes: don't wait for the clip to finish.
    const wrongWay = (this.moving && p.kind === "idle") || (!this.moving && (p.kind === "chase" || p.kind === "lunge"));
    if (wrongWay && !this._cutting) this._cut();
    const pl = this.playing;
    if (pl.kind === "chase" || pl.kind === "lunge") {
      const r = rateFor(kmh, BANDS.find((b) => b.id === pl.band) || bandFor(kmh));
      const v = this.vids[this.cur];
      if (Math.abs(v.playbackRate - r) > 0.02) setRate(v, r);
    }
  }

  _choose(at = this.at) {
    return pickNext(this.clips, { at, moving: this.moving, kmh: this.kmh, power: this.power, recent: this.recent });
  }

  _src(c) { return this.base + c.file; }

  _start(clip) {
    if (!clip) return;
    const v = this.vids[this.cur];
    if (!v.src.endsWith(clip.file)) v.src = this._src(clip);
    v.currentTime = 0;
    this._show(this.cur);
    this._play(v, clip);
  }

  _play(v, clip) {
    // The other layer may still be running (after a cut): stop it so its end can't move us on.
    const old = this.vids[1 - this.cur];
    if (old !== v) { old.onended = null; old.pause(); }
    setRate(v, clip.kind === "chase" || clip.kind === "lunge" ? rateFor(this.kmh) : 1);
    this.playing = clip; this.queued = null;
    this.recent.push(clip.id); if (this.recent.length > 3) this.recent.shift();
    v.onended = () => this._next();
    const go = v.play();
    if (go && go.catch) go.catch(() => this._fail());
    cancelAnimationFrame(this._raf); this._raf = requestAnimationFrame(this._tick);
    if (this.onReady) { this.onReady(); this.onReady = null; }
  }

  _show(i) {
    this.vids.forEach((v, j) => v.classList.toggle("on", j === i));
  }

  // Near the end of a clip, load the next one into the hidden layer so the swap is instant.
  _tick() {
    const v = this.vids[this.cur], p = this.playing;
    if (p && !this.queued && v.duration && v.duration - v.currentTime < 1.2 * Math.max(1, v.playbackRate)) {
      this.queued = this._choose(p.to);
      if (this.queued) {
        const nv = this.vids[1 - this.cur];
        if (!nv.src.endsWith(this.queued.file)) { nv.src = this._src(this.queued); nv.load(); }
      }
    }
    this._raf = requestAnimationFrame(this._tick);
  }

  _next() {
    if (!this.playing) return;
    this.at = this.playing.to;
    let clip = this.queued;
    // Things may have changed since it was queued (stopped, or into a new speed band).
    const fresh = this._choose();
    if (!clip || clip.from !== this.at || fresh?.kind !== clip.kind || (clip.band && clip.band !== bandFor(this.kmh).id)) clip = fresh;
    if (!clip) return;
    this.cur = 1 - this.cur;
    const v = this.vids[this.cur];
    if (!v.src.endsWith(clip.file)) v.src = this._src(clip);
    v.currentTime = 0;
    this._show(this.cur);
    this._play(v, clip);
  }

  // Break off the current clip with a short cross-fade (no shared frame here, so fade over it).
  _cut() {
    const p = this.playing;
    if (!p) return;
    // An idle clip ends on closed, a chase on run: pretend we got there, then pick from that hub.
    this.at = p.to;
    const clip = this._choose();
    if (!clip || clip.id === p.id) return;
    this._cutting = true;
    this.cur = 1 - this.cur;
    const v = this.vids[this.cur];
    v.src = this._src(clip); v.currentTime = 0;
    this.host.classList.add("cut");
    this._show(this.cur);
    this._play(v, clip);
    setTimeout(() => { this.host.classList.remove("cut"); this._cutting = false; }, 400);
  }

  _fail() {
    if (this.failed) return;
    this.failed = true; this.playing = null;
    cancelAnimationFrame(this._raf);
    this.vids.forEach((v) => { v.pause(); v.removeAttribute("src"); v.classList.remove("on"); });
    this.host.classList.add("failed");
    if (this.onFail) this.onFail();
  }

  /** Off screen (another page, screen off): stop decoding to save the Pi. */
  pause() { this.vids.forEach((v) => v.pause()); cancelAnimationFrame(this._raf); }
  resume() {
    if (this.failed || !this.playing) return;
    const v = this.vids[this.cur]; const go = v.play(); if (go && go.catch) go.catch(() => {});
    this._raf = requestAnimationFrame(this._tick);
  }
}
