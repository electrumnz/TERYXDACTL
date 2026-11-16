// Media mixer: one music level for every source, turned down (ducked) under alerts and in reverse.
//
// Alerts are never touched here: they play at their own volume (Settings > Sounds and alerts), so
// turning the music down or off can never make a warning quieter.
//
// What it controls:
//   * <audio> elements (local music, internet radio)       their .volume, faded
//   * Web Audio gain nodes (CarPlay / Android Auto audio)  gain, faded
//   * Bluetooth phone audio, which goes straight into PipeWire on the Pi, so the server sets it
//     (POST /api/audio/media-level and /api/audio/duck)

const FADE_MS = 250;

export class Mixer {
  constructor({ server = true } = {}) {
    this.level = 0.8;          // the music volume the driver picked
    this.duckTo = 0.25;        // fraction of that while ducked
    this.server = server;
    this.els = new Set();
    this.gains = new Set();
    this.reasons = new Set();  // "alarm", "reverse", ... (held)
    this.pulseUntil = 0;       // a short duck for a one-off beep
    this._pulseTimer = null;
    this._fades = new Map();
    this._sentDuck = null;
    this._levelTimer = null;
    this.subs = new Set();
    this.log = [];             // duck on/off, for the bench tests
  }

  get ducked() { return this.reasons.size > 0 || Date.now() < this.pulseUntil; }
  get effective() { return this.level * (this.ducked ? this.duckTo : 1); }

  attach(el) { this.els.add(el); el.volume = this.effective; }
  detach(el) { this.els.delete(el); }
  attachGain(g) { this.gains.add(g); g.gain.value = this.effective; }
  detachGain(g) { this.gains.delete(g); }
  on(fn) { this.subs.add(fn); }

  setLevel(v, { send = true } = {}) {
    this.level = Math.max(0, Math.min(1, v));
    this.apply(true);
    if (send && this.server) {
      clearTimeout(this._levelTimer);
      this._levelTimer = setTimeout(() => post("audio/media-level", { level: this.level }).catch(() => {}), 150);
    }
  }
  setDuckTo(v) { this.duckTo = Math.max(0, Math.min(1, v)); this.apply(); }

  /** Hold the music down for a reason until released (an alarm that's still sounding, reversing). */
  hold(reason, on) {
    const had = this.reasons.has(reason);
    if (on && !had) this.reasons.add(reason);
    else if (!on && had) this.reasons.delete(reason);
    else return;
    this.apply();
  }

  /** Duck for a short while (a one-off warning beep), then come back up. */
  pulse(ms = 2500) {
    this.pulseUntil = Math.max(this.pulseUntil, Date.now() + ms);
    this.apply();
    clearTimeout(this._pulseTimer);
    this._pulseTimer = setTimeout(() => this.apply(), this.pulseUntil - Date.now() + 20);
  }

  apply(instant = false) {
    const v = this.effective, ducked = this.ducked;
    this.els.forEach((el) => this._fadeEl(el, v, instant ? 0 : FADE_MS));
    this.gains.forEach((g) => {
      try {
        const t = g.context.currentTime;
        g.gain.cancelScheduledValues(t);
        g.gain.setTargetAtTime(v, t, instant ? 0.01 : FADE_MS / 3000);
      } catch { g.gain.value = v; }
    });
    if (ducked !== this._sentDuck) {
      this._sentDuck = ducked;
      this.log.push({ ducked, at: Date.now() }); if (this.log.length > 50) this.log.shift();
      if (this.server) post("audio/duck", { on: ducked, duck_to: this.duckTo }).catch(() => {});
    }
    this.subs.forEach((fn) => fn(this));
  }

  _fadeEl(el, to, ms) {
    clearInterval(this._fades.get(el));
    const from = el.volume;
    if (!ms || Math.abs(from - to) < 0.01) { el.volume = to; return; }
    const t0 = performance.now();
    const id = setInterval(() => {
      const f = Math.min(1, (performance.now() - t0) / ms);
      el.volume = Math.max(0, Math.min(1, from + (to - from) * f));
      if (f >= 1) { clearInterval(id); this._fades.delete(el); }
    }, 30);
    this._fades.set(el, id);
  }
}

export async function post(path, body) {
  try {
    const r = await fetch(`/api/${path}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body || {}) });
    if (!r.ok) { let m = `${r.status}`; try { m = (await r.json()).error || m; } catch {} throw new Error(m); }
    return await r.json();
  } catch (e) { throw e; }
}
