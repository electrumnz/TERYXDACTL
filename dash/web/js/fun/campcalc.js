// Camp mode power maths. Pure functions, no DOM, so they can be tested with plain node.
//
// Every wattage here is a starting guess until it's measured on the bench (see docs/fun.md).
// Change them in Settings > Fun once real numbers are known.

export const CAMP_DEFAULTS = {
  source: "aux",        // aux: the 12V winch battery | pack: the EV pack through the Shinegle DC-DC
  auxAh: 35,            // 12V battery size. NOT KNOWN YET: set it once the battery is checked
  auxChem: "lead",      // lead (flooded/AGM) | lithium (LiFePO4)
  auxCutoffV: 11.9,     // camp mode switches its loads off below this (under load, held for 15 s)
  packFloorPct: 40,     // never use the pack below this %, so there's always enough to drive out
  dcdcEff: 0.88,        // DC-DC converter efficiency (pack mode). Guess
  ctrlW: 15,            // Shinegle controller + contactor awake while the key is on (pack mode). Guess
  piW: 6,               // Pi 5 with the dash open. Raspberry Pi says 4-5 W minimum
  screenW: 12,          // 10.1" screen at full brightness. Guess: measure it
  ampW: 8,              // amp at campsite volume. Guess
  barW: 40,             // each front light bar at full. Guess: check the bar's label
  interiorW: 15,        // 7" interior bar at full. Guess
  timerH: 0,            // auto off after this many hours (0 = no timer)
};

// Share of a 12V battery you can use without hurting it.
// Lead: 50% is the usual deep-cycle limit. LiFePO4: 80% is the usual everyday limit.
export const USABLE = { lead: 0.5, lithium: 0.8 };

// Rough rested-voltage to charge table for a 12V lead battery (AGM sits a little higher).
// Only good when the battery has rested. Under load it reads low, so it's only used once,
// at the start, to guess how full the battery was. Sources in docs/fun.md.
const LEAD_REST = [[12.7, 100], [12.5, 80], [12.4, 70], [12.2, 50], [12.0, 30], [11.8, 10]];
// LiFePO4 is very flat in the middle, so voltage tells you little. Treat it as full above 13.2 V.
const LFP_REST = [[13.4, 100], [13.2, 80], [13.1, 50], [13.0, 30], [12.8, 15], [12.0, 0]];

export function restSoc(volts, chem = "lead") {
  if (volts == null || !isFinite(volts)) return null;
  const t = chem === "lithium" ? LFP_REST : LEAD_REST;
  if (volts >= t[0][0]) return 100;
  const last = t[t.length - 1];
  if (volts <= last[0]) return last[1];
  for (let i = 1; i < t.length; i++) {
    const [v1, p1] = t[i - 1], [v2, p2] = t[i];
    if (volts >= v2) return Math.round(p2 + ((volts - v2) / (v1 - v2)) * (p1 - p2));
  }
  return 0;
}

/**
 * Watts camp mode is pulling right now.
 *   lights: { "light.front_1": 0..255, ..., "light.interior": 0..255 }
 *   screen: 0..1 brightness, audio: true if music or the fire sound is on
 */
export function campLoadW(cfg, { lights = {}, screen = 1, audio = false } = {}) {
  const c = { ...CAMP_DEFAULTS, ...cfg };
  let w = c.piW + c.screenW * Math.max(0.15, screen) + (audio ? c.ampW : 0);
  for (const [id, lvl] of Object.entries(lights)) {
    const f = Math.max(0, Math.min(255, lvl || 0)) / 255;
    w += (id === "light.interior" ? c.interiorW : id.startsWith("light.front") ? c.barW : 0) * f;
  }
  if (c.source === "pack") w = w / c.dcdcEff + c.ctrlW;
  return w;
}

/**
 * Energy (Wh) camp mode can still use.
 *   aux:  battery size x usable share, scaled by how full it was at the start, less what camp mode has used
 *   pack: pack kWh above the floor %
 */
export function campBudgetWh(cfg, { startSoc = 100, usedWh = 0, packSoc = null, packKwh = 7.5 } = {}) {
  const c = { ...CAMP_DEFAULTS, ...cfg };
  if (c.source === "pack") {
    if (packSoc == null) return null;
    return Math.max(0, ((packSoc - c.packFloorPct) / 100) * packKwh * 1000);
  }
  const nominal = c.auxChem === "lithium" ? 12.8 : 12;
  const floor = 100 - USABLE[c.auxChem in USABLE ? c.auxChem : "lead"] * 100;   // e.g. 50% for lead
  const room = Math.max(0, (startSoc ?? 100) - floor) / 100;
  return Math.max(0, c.auxAh * nominal * room - usedWh);
}

/** Hours left at the current draw, or null if it can't be worked out. */
export function campHoursLeft(budgetWh, loadW) {
  if (budgetWh == null || !(loadW > 0)) return null;
  return budgetWh / loadW;
}

export function fmtHours(h) {
  if (h == null) return "--";
  if (h >= 48) return `${Math.round(h / 24)} days`;
  if (h >= 10) return `${Math.round(h)} h`;
  const hh = Math.floor(h), mm = Math.round((h - hh) * 60);
  return mm === 60 ? `${hh + 1} h` : hh ? `${hh} h ${mm} min` : `${mm} min`;
}
