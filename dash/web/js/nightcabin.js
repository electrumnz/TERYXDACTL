// Night mode fades the cabin light down (and back up in the morning).
//
// When the dash goes dark (Night Hunt, or any look with the night colours) and the
// cabin bar is brighter than the night level in Settings, it fades down to that level
// over a few seconds, so it doesn't glare off the screen and the windscreen. When it
// goes light again it fades back to where it was, unless someone moved it meanwhile.
// Off stays off: this never turns the cabin light on. docs/lights.md
export const NIGHT_CABIN_DEFAULTS = { on: true, pct: 15, fadeMs: 3000 };

const STEPS = 12;
const ID = "light.interior";

export class NightCabin {
  constructor(ctx) {
    this.ctx = ctx;
    this.dark = null;        // last dark/light seen, null until the first tick
    this.before = null;      // level before the night fade, to go back to
    this.ours = null;        // level we last asked for (so we can tell if someone moved it)
    this.timer = null;
  }

  cfg() { return { ...NIGHT_CABIN_DEFAULTS, ...(this.ctx.settings.get("nightCabin") || {}) }; }

  level() {
    const st = this.ctx.store;
    const req = st.get(`req.${ID}`);
    return req != null ? req : st.get(ID, 0);
  }

  fade(from, to, ms) {
    clearInterval(this.timer);
    let i = 0;
    this.timer = setInterval(() => {
      i++;
      const v = Math.round(from + ((to - from) * i) / STEPS);
      this.ours = v;
      this.ctx.link.request(ID, v);
      if (i >= STEPS) { clearInterval(this.timer); this.timer = null; }
    }, Math.max(20, ms / STEPS));
  }

  /** Call whenever the look is picked. dark = night colours on. */
  tick(dark) {
    if (this.dark === null) { this.dark = dark; return; }
    if (dark === this.dark) return;
    this.dark = dark;
    const c = this.cfg();
    if (!c.on) return;
    const now = this.level();
    const night = Math.round((c.pct / 100) * 255);
    if (dark) {
      if (now > night) { this.before = now; this.fade(now, night, c.fadeMs); }
      else this.before = null;
    } else if (this.before != null) {
      if (now === this.ours && now > 0) this.fade(now, this.before, c.fadeMs);   // only if nobody touched it
      this.before = null;
    }
  }
}
