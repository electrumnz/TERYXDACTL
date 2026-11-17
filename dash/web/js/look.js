// The dash has three looks, picked by what the Teryx is doing:
//
//   Predator   (std)      everyday driving
//   Fossil     (offroad)  4WD on or the diff lock above 0%
//   Night Hunt (night)    light bars on, or after sunset (see theme.js)
//
// Off-road wins over night, but at night Fossil takes darker colours (body.theme-night).
// Settings > Display can lock one look instead of Auto.
import { autoTheme } from "./theme.js";

export const LOOKS = { std: "Predator", offroad: "Fossil", night: "Night Hunt" };

// Stay in Fossil this long after 4WD and the diff lock both come off, so a quick
// 2WD/4WD flick doesn't make the whole screen flash back and forth.
const OFFROAD_HOLD_MS = 8000;

export class LookPicker {
  constructor(store, settings) {
    this.store = store; this.settings = settings;
    this.offroadUntil = 0;
    this.prevTheme = "night";
    this.sun = null; this.sunAt = 0;
  }

  offroad(st, now) {
    const fw = st.get("act.4wd", "2wd");
    const on = fw === "4wd" || fw === "to_4wd" || Math.round(st.get("an.diff_pos", 0)) > 2;
    if (on) this.offroadUntil = now + OFFROAD_HOLD_MS;
    return on || now < this.offroadUntil;
  }

  lightsOn(st) {
    for (let i = 1; i <= 4; i++) if (st.get(`light.front_${i}`, 0) > 0) return true;
    return false;
  }

  // Settings changed (region, lock): work the sun out again on the next pick.
  refresh() { this.sun = null; }

  /** Returns {look, dark, why}. look is std | offroad | night. */
  pick(date = new Date()) {
    const st = this.store, now = date.getTime();
    // The sun moves slowly: work it out every 30 s, not on every redraw.
    if (!this.sun || now - this.sunAt > 30000 || now < this.sunAt) {
      this.sun = autoTheme(st, this.settings, date, this.prevTheme);
      this.prevTheme = this.sun.theme; this.sunAt = now;
    }
    const sun = this.sun;
    const lights = this.lightsOn(st);
    const dark = sun.theme === "night" || lights;
    const set = this.settings.get("look") || "auto";
    if (set !== "auto" && LOOKS[set]) return { look: set, dark: set === "night" || dark, why: "locked in Settings" };
    if (this.offroad(st, now)) return { look: "offroad", dark, why: "4WD or diff lock on" };
    if (lights) return { look: "night", dark: true, why: "light bars on" };
    if (sun.theme === "night") return { look: "night", dark: true, why: sun.why };
    return { look: "std", dark: false, why: sun.why };
  }
}
