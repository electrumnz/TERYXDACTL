// Winch motor heat, a rough guess worked out on the dash. There's no temperature or current
// sensor on the winch, so this counts how long it has run and lets it cool over time.
//
// Small 12V winches like the XBull 5000 are only rated for short pulls. Makers put it as a
// duty cycle: about 5% at full load on some (45 s on, then 14 min rest), and Superwinch
// say about 5 min at full pull then 30 min rest. Most ATV pulls are well under full load,
// so the numbers below sit in between:
//   - about 60 s of hard pulling in from cold fills it (paying out counts much less)
//   - it cools from full to cold in about 10 minutes
//   - warn at 70%, "rest now" at 100%, and say it's OK again once it's back under 40%
// Pulls from the handheld remote or the hand switches (in.winch_remote) count as pulling in,
// since the dash can't tell which way they're going.
// It's only advice: the dash shows it, warns and blocks a new timed pull when it's too hot.
// Hold-to-run still works, because sometimes you just have to finish the pull.

export const HEAT = {
  fullAfterS: 60,     // seconds of hard pulling in, from cold, to reach 100%
  outRate: 0.3,       // paying out heats it this much compared to pulling in
  coolS: 600,         // seconds to cool from 100% to 0%
  warnPct: 70,
  restPct: 100,
  okPct: 40,
};

const KEY = "teryx.winchHeat";

export class WinchHeat {
  constructor(now = Date.now()) {
    this.pct = 0;
    this.resting = false;   // hit 100%: stays true until it cools back under okPct
    this.pullS = 0;         // how long the current (or last) pull has run
    this.running = 0;       // +1 in, -1 out, 0 stopped
    this.at = now;
    this._saved = 0;
    // Pick up where we left off, so a dash restart mid-job doesn't forget a hot winch.
    try {
      const s = JSON.parse(localStorage.getItem(KEY) || "null");
      if (s && typeof s.pct === "number" && typeof s.at === "number") {
        this.pct = s.pct; this.resting = !!s.resting; this.at = s.at;
        this.tick(null, now);
      }
    } catch {}
  }

  /** Move the model on to `now`. st is the live store (or null to just cool). */
  tick(st, now = Date.now()) {
    const dt = Math.max(0, Math.min(3600, (now - this.at) / 1000));
    this.at = now;
    let dir = 0;
    if (st) {
      if (st.get("winch.in")) dir = 1;
      else if (st.get("winch.out")) dir = -1;
      else if (st.get("in.winch_remote")) dir = 1;
    }
    if (dir && !this.running) this.pullS = 0;
    if (dir) this.pullS += dt;
    this.running = dir;
    const heat = dir === 1 ? 100 / HEAT.fullAfterS : dir === -1 ? (100 / HEAT.fullAfterS) * HEAT.outRate : 0;
    this.pct += (heat - 100 / HEAT.coolS) * dt;
    this.pct = Math.max(0, Math.min(120, this.pct));
    if (this.pct >= HEAT.restPct) this.resting = true;
    else if (this.pct < HEAT.okPct) this.resting = false;
    if (now - this._saved > 5000) {
      this._saved = now;
      try { localStorage.setItem(KEY, JSON.stringify({ pct: this.pct, resting: this.resting, at: now })); } catch {}
    }
    return this;
  }

  get state() { return this.resting ? "rest" : this.pct >= HEAT.warnPct ? "warm" : "ok"; }

  /** Seconds of rest until it's OK to pull again (back under okPct). 0 if it's fine now. */
  restLeftS() { return this.resting ? Math.max(0, Math.ceil(((this.pct - HEAT.okPct) * HEAT.coolS) / 100)) : 0; }

  /** Roughly how hot a pull of `secs` would leave it. */
  after(secs) { return this.pct + (secs * 100) / HEAT.fullAfterS; }
}

export function mmss(s) {
  s = Math.max(0, Math.round(s));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
