// Touch controls built for gloves and bumpy tracks: big targets, drag sliders, hold-to-run buttons.

export function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

export const $ = (root, sel) => root.querySelector(sel);
export const $$ = (root, sel) => [...root.querySelectorAll(sel)];

export function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

/** How much the 1280x800 layout is scaled to fit the real screen (see fit.js). */
export function screenScale() { return window.__teryxScale || 1; }

/**
 * Horizontal drag slider. onChange(value, final) fires while dragging (throttled) and once on release.
 * setActual(v) shows what the control box reports, as a thin marker, so you can see it catching up.
 */
export class Slider {
  constructor({ min = 0, max = 100, step = 1, value = 0, label = "", fmt = (v) => `${v}`, onChange }) {
    Object.assign(this, { min, max, step, value, fmt, onChange });
    this.root = el(`<div class="slider"><div class="fill"></div><div class="ghost"></div><div class="label"><span>${label}</span><span class="sv num"></span></div></div>`);
    this.fill = this.root.querySelector(".fill");
    this.ghost = this.root.querySelector(".ghost");
    this.sv = this.root.querySelector(".sv");
    this.dragging = false;
    this.locked = false;
    this.lastSent = 0;
    const toVal = (x) => {
      const r = this.root.getBoundingClientRect();
      const f = clamp((x - r.left) / r.width, 0, 1);
      return Math.round((min + f * (max - min)) / step) * step;
    };
    this.root.addEventListener("pointerdown", (e) => {
      if (this.locked) { this.onLocked && this.onLocked(); return; }
      this.dragging = true; this.root.setPointerCapture(e.pointerId);
      this.update(toVal(e.clientX), false);
    });
    this.root.addEventListener("pointermove", (e) => { if (this.dragging) this.update(toVal(e.clientX), false); });
    const end = (e) => { if (!this.dragging) return; this.dragging = false; this.update(toVal(e.clientX), true); };
    this.root.addEventListener("pointerup", end);
    this.root.addEventListener("pointercancel", () => { this.dragging = false; });
    this.render();
  }
  update(v, final) {
    this.value = clamp(v, this.min, this.max);
    this.render();
    const now = performance.now();
    if (final || now - this.lastSent > 120) { this.lastSent = now; this.onChange && this.onChange(this.value, final); }
  }
  set(v) { if (!this.dragging) { this.value = v; this.render(); } }
  setActual(v) {
    if (v == null) { this.ghost.style.display = "none"; return; }
    this.ghost.style.display = "";
    this.ghost.style.left = `${((v - this.min) / (this.max - this.min)) * 100}%`;
  }
  setLocked(b) { this.locked = b; this.root.classList.toggle("locked", b); }
  render() {
    const f = (this.value - this.min) / (this.max - this.min);
    this.fill.style.width = `${f * 100}%`;
    this.sv.textContent = this.fmt(this.value);
  }
}

/**
 * Hold-to-run button. Runs only while a finger is on it. Lifting, sliding off, or losing the
 * touch all stop it straight away. The control box also stops it if the repeats stop arriving.
 */
export function holdButton(btn, { onStart, onStop, canStart }) {
  let held = false;
  const start = (e) => {
    e.preventDefault();
    if (canStart && !canStart()) return;
    held = true; btn.classList.add("held");
    try { btn.setPointerCapture(e.pointerId); } catch {}
    onStart();
  };
  const stop = () => { if (!held) return; held = false; btn.classList.remove("held"); onStop(); };
  btn.addEventListener("pointerdown", start);
  btn.addEventListener("pointerup", stop);
  btn.addEventListener("pointercancel", stop);
  btn.addEventListener("lostpointercapture", stop);
  btn.addEventListener("pointerleave", stop);
  btn.addEventListener("contextmenu", (e) => e.preventDefault());
  document.addEventListener("visibilitychange", stop);
  window.addEventListener("blur", stop);
  return { stop, get held() { return held; } };
}

/** Slide-to-arm, so a bump or a knee can't arm the winch. */
export function slideToArm(root, { onArm, onDisarm, isArmed }) {
  const knob = root.querySelector(".knob");
  let startX = 0, dx = 0, dragging = false;
  const max = () => root.clientWidth - knob.offsetWidth - 10;
  knob.addEventListener("pointerdown", (e) => {
    if (isArmed()) return;
    dragging = true; startX = e.clientX; dx = 0; knob.setPointerCapture(e.pointerId); knob.style.transition = "none";
  });
  knob.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    dx = clamp((e.clientX - startX) / screenScale(), 0, max());
    knob.style.left = `${5 + dx}px`;
  });
  const end = () => {
    if (!dragging) return; dragging = false; knob.style.transition = "left .2s";
    if (dx > max() * 0.85) onArm();
    knob.style.left = "";
  };
  knob.addEventListener("pointerup", end);
  knob.addEventListener("pointercancel", end);
  root.addEventListener("click", () => { if (isArmed()) onDisarm(); });
}

let toastTimer;
export function toast(msg, kind = "") {
  const t = document.getElementById("toast");
  t.textContent = msg; t.className = `toast ${kind}`; t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), 3500);
}

export function stepper(value, { step = 1, min = -Infinity, max = Infinity, fmt = (v) => v, onChange }) {
  const root = el(`<div class="stepper"><button>−</button><div class="sv num"></div><button>+</button></div>`);
  const [minus, plus] = root.querySelectorAll("button");
  const sv = root.querySelector(".sv");
  let v = value;
  const show = () => (sv.textContent = fmt(v));
  const bump = (d) => { v = clamp(Math.round((v + d) / step) * step, min, max); show(); onChange(v); };
  minus.onclick = () => bump(-step);
  plus.onclick = () => bump(step);
  show();
  return { root, set(nv) { v = nv; show(); } };
}

export function toggle(on, onChange) {
  const sw = el(`<button class="switch" aria-pressed="false"></button>`);
  const set = (b) => { on = b; sw.classList.toggle("on", b); sw.setAttribute("aria-pressed", b); };
  sw.onclick = () => { set(!on); onChange(on); };
  set(on);
  return { root: sw, set };
}
