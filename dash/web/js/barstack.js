// Front bar stack: the 4 bars sit one above the other in the grille, bar 1 at the top.
// One slider (0-100) runs them all: each quarter of the slider fills one bar, in fill order.
// With top-down order, 0-25 ramps bar 1 from 0 to 100%, 25-50 ramps bar 2, and so on.
// Low / Med / High are just saved levels for the 4 bars, so they can be anything (docs/lights.md).
// Plain functions, no DOM, so the dash, the phone remote and the tests all share them.

export const BAR_IDS = ["light.front_1", "light.front_2", "light.front_3", "light.front_4"];

// Fill orders, by bar number. Top down is the default: Med (2 bars) then lands on two
// different fuses (1+4 and 2+3 share), so one blown fuse never takes out both lit bars.
export const BAR_ORDERS = {
  top: [1, 2, 3, 4],
  bottom: [4, 3, 2, 1],
  middle: [2, 3, 1, 4],
};

export const BAR_PRESET_DEFAULTS = {
  low:  { "light.front_1": 128, "light.front_2": 0,   "light.front_3": 0,   "light.front_4": 0 },
  med:  { "light.front_1": 255, "light.front_2": 255, "light.front_3": 0,   "light.front_4": 0 },
  high: { "light.front_1": 255, "light.front_2": 255, "light.front_3": 255, "light.front_4": 255 },
};

const orderIds = (order) => (BAR_ORDERS[order] || BAR_ORDERS.top).map((n) => BAR_IDS[n - 1]);

// Slider (0-100) -> level 0-255 for each bar. An on/off-only bar comes on once its
// quarter is half full. dimmable(id) says if a bar can dim (Settings).
export function sliderToLevels(s, order = "top", dimmable = () => true) {
  s = Math.max(0, Math.min(100, +s || 0));
  const out = {};
  orderIds(order).forEach((id, i) => {
    const f = Math.max(0, Math.min(1, (s - i * 25) / 25));
    out[id] = dimmable(id) ? Math.round(f * 255) : (f >= 0.5 ? 255 : 0);
  });
  return out;
}

// Bar levels -> where the slider sits, and whether they fit the stack pattern
// (every bar before the top lit one full, every bar after it off). If they don't
// (set from the Each bar menu), the slider shows the average and `mixed` is true.
export function levelsToSlider(levels, order = "top") {
  const ids = orderIds(order);
  const v = ids.map((id) => Math.max(0, Math.min(255, levels[id] || 0)));
  const total = v.reduce((a, b) => a + b, 0);
  const s = Math.round(((total / 255) * 25) * 10) / 10;
  let last = -1;
  v.forEach((x, i) => { if (x > 0) last = i; });
  const mixed = v.some((x, i) => (i < last && x < 250) || (i > last && x > 0));
  return { slider: s, mixed };
}

// Which preset (low/med/high) these levels match, or "" for none.
export function matchPreset(levels, presets) {
  for (const k of ["low", "med", "high"]) {
    const p = presets?.[k]; if (!p) continue;
    if (BAR_IDS.every((id) => Math.abs((p[id] || 0) - (levels[id] || 0)) <= 3)) return k;
  }
  return "";
}

// Short text for the slider: "Off", "Bar 1 50%", "2 bars", "3 bars + 40%".
export function stackLabel(levels, order = "top") {
  const ids = orderIds(order);
  const lit = ids.filter((id) => (levels[id] || 0) > 0);
  if (!lit.length) return "Off";
  const { mixed } = levelsToSlider(levels, order);
  if (mixed) return `${lit.length} bar${lit.length > 1 ? "s" : ""}, mixed`;
  const full = lit.filter((id) => levels[id] >= 250).length;
  const part = lit.length - full;
  const pctOf = (id) => Math.round((levels[id] / 255) * 100);
  if (lit.length === 1) return `Bar ${BAR_IDS.indexOf(lit[0]) + 1} ${pctOf(lit[0])}%`;
  if (!part) return `${full} bars`;
  return `${full} bar${full > 1 ? "s" : ""} + ${pctOf(lit[lit.length - 1])}%`;
}
