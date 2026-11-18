// Easter eggs. All original, all T. rex. They only work when parked (park.js), so nothing
// pops up while driving. Found ones are remembered in settings (fun.eggs) and counted on the Fun screen.
//
//   Roar          tap the TERYX badge (top left) 5 times quickly
//   Extinction    press and hold the look name (Predator / Fossil / Night Hunt) for 2 s
//   Sue's day     12 August: the splash and Fun screen wish Sue a happy find-day
//                 (SUE, the Field Museum's T. rex, found 12 Aug 1990)
//   Tiny arms     tap the clock 7 times quickly
import { audioContext } from "../sound.js";
import { el, toast } from "../ui/controls.js";
import { isParked } from "./park.js";

export const EGGS = [
  { id: "roar", name: "Roar", hint: "Something in the top left doesn't like being poked." },
  { id: "meteor", name: "Extinction", hint: "Hold on to your look." },
  { id: "arms", name: "Tiny arms", hint: "Time is hard to reach." },
  { id: "sue", name: "Sue's day", hint: "Comes round once a year, in winter." },
];

const ARMS = [
  "Tiny arms. Can't reach the clock.",
  "Tried to set an alarm. Arms too short.",
  "Big head, big teeth, small reach.",
  "Can't do up the seatbelt either.",
  "Waving. You just can't see it.",
];

/** Synth roar: a deep growl that swells then drops, with a rasp on top. No sound file. */
export function roarSound(vol = 0.9) {
  const a = audioContext(); if (!a) return;
  const t = a.currentTime + 0.02, dur = 2.2;
  const out = a.createGain(); out.gain.setValueAtTime(0.0001, t);
  out.gain.exponentialRampToValueAtTime(vol, t + 0.25);
  out.gain.setValueAtTime(vol, t + 1.3);
  out.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  out.connect(a.destination);
  // growl: two detuned saws, falling in pitch, through a wobbling low-pass
  const lp = a.createBiquadFilter(); lp.type = "lowpass"; lp.Q.value = 6;
  lp.frequency.setValueAtTime(300, t); lp.frequency.linearRampToValueAtTime(900, t + 0.6); lp.frequency.linearRampToValueAtTime(220, t + dur);
  lp.connect(out);
  [70, 73.5, 140].forEach((f, i) => {
    const o = a.createOscillator(); o.type = "sawtooth";
    o.frequency.setValueAtTime(f * 1.3, t); o.frequency.linearRampToValueAtTime(f, t + 0.5); o.frequency.linearRampToValueAtTime(f * 0.7, t + dur);
    const g = a.createGain(); g.gain.value = i === 2 ? 0.25 : 0.5;
    const lfo = a.createOscillator(), lg = a.createGain(); lfo.frequency.value = 23 + i * 4; lg.gain.value = f * 0.06;
    lfo.connect(lg); lg.connect(o.frequency); lfo.start(t); lfo.stop(t + dur);
    o.connect(g); g.connect(lp); o.start(t); o.stop(t + dur);
  });
  // rasp: noise through a band-pass
  const len = a.sampleRate * dur, buf = a.createBuffer(1, len, a.sampleRate), d = buf.getChannelData(0);
  for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
  const n = a.createBufferSource(); n.buffer = buf;
  const bp = a.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 700; bp.Q.value = 1.2;
  const ng = a.createGain(); ng.gain.value = 0.35;
  n.connect(bp); bp.connect(ng); ng.connect(out); n.start(t);
}

/** Full-screen T. rex head that wakes up and roars, and the dash shakes. */
export function playRoar(app = document.getElementById("app")) {
  if (document.querySelector(".egg-roar")) return;
  const o = el(`<div class="egg-roar" aria-hidden="true">
      <img class="er-closed" src="img/dino/head-closed.webp" alt="">
      <img class="er-snarl" src="img/dino/head-snarl.webp" alt="">
      <img class="er-roar" src="img/dino/head-roar.webp" alt="">
    </div>`);
  app.appendChild(o);
  requestAnimationFrame(() => o.classList.add("in"));
  setTimeout(() => o.classList.add("snarl"), 500);
  setTimeout(() => { o.classList.add("roar"); app.classList.add("egg-shake"); roarSound(); }, 900);
  setTimeout(() => app.classList.remove("egg-shake"), 1900);
  setTimeout(() => o.classList.add("out"), 2900);
  setTimeout(() => o.remove(), 3500);
}

/** A meteor streaks across, a flash, then "Still here." */
export function playMeteor(app = document.getElementById("app")) {
  if (document.querySelector(".egg-meteor")) return;
  const o = el(`<div class="egg-meteor" aria-hidden="true"><i class="em-rock"></i><i class="em-flash"></i><b class="em-text">Still here.</b></div>`);
  app.appendChild(o);
  requestAnimationFrame(() => o.classList.add("go"));
  const a = audioContext();
  if (a) {   // a low whoosh then a thump
    const t = a.currentTime + 0.05, len = a.sampleRate * 1.6, buf = a.createBuffer(1, len, a.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.min(1, i / (len * 0.7)) * (i > len * 0.78 ? Math.exp(-(i - len * 0.78) / 4000) * 3 : 1);
    const s = a.createBufferSource(); s.buffer = buf;
    const lp = a.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.setValueAtTime(400, t); lp.frequency.linearRampToValueAtTime(1800, t + 1.2); lp.frequency.linearRampToValueAtTime(120, t + 1.6);
    const g = a.createGain(); g.gain.value = 0.6;
    s.connect(lp); lp.connect(g); g.connect(a.destination); s.start(t);
  }
  setTimeout(() => app.classList.add("egg-shake"), 1250);
  setTimeout(() => app.classList.remove("egg-shake"), 1900);
  setTimeout(() => o.remove(), 4200);
}

export function isSuesDay(d = new Date()) { return d.getMonth() === 7 && d.getDate() === 12; }

/** Wire the hidden triggers to the top bar. Call once at start up. */
export function wireEggs(ctx) {
  const found = (id) => {
    const list = ctx.settings.get("fun.eggs") || [];
    if (!list.includes(id)) {
      ctx.settings.set("fun.eggs", [...list, id]);
      setTimeout(() => toast(`Easter egg found: ${EGGS.find((e) => e.id === id).name} (${list.length + 1} of ${EGGS.length})`), 3000);
    }
  };
  const ok = () => isParked(ctx.store);
  ctx.eggFound = found;

  // Roar: 5 taps on the badge within 2.5 s
  const badge = document.querySelector(".tb-brand");
  if (badge) {
    let taps = [];
    badge.addEventListener("pointerdown", () => {
      const now = Date.now(); taps = taps.filter((t) => now - t < 2500); taps.push(now);
      if (taps.length >= 5) { taps = []; if (ok()) { playRoar(); found("roar"); } }
    });
  }
  // Extinction: hold the look name for 2 s
  const look = document.getElementById("tb-look");
  if (look) {
    let timer = null;
    const cancel = () => { clearTimeout(timer); timer = null; };
    look.addEventListener("pointerdown", () => { cancel(); timer = setTimeout(() => { if (ok()) { playMeteor(); found("meteor"); } }, 2000); });
    ["pointerup", "pointerleave", "pointercancel"].forEach((e) => look.addEventListener(e, cancel));
  }
  // Tiny arms: 7 taps on the clock within 4 s
  const clock = document.getElementById("tb-clock");
  if (clock) {
    let taps = [], n = 0;
    clock.addEventListener("pointerdown", () => {
      const now = Date.now(); taps = taps.filter((t) => now - t < 4000); taps.push(now);
      if (taps.length >= 7) { taps = []; if (ok()) { toast(ARMS[n++ % ARMS.length]); found("arms"); } }
    });
  }
  // Sue's day: the splash says so, and it counts as found if the dash is on that day
  if (isSuesDay()) {
    const m = document.getElementById("splash-msg"); if (m) m.textContent = "Happy find-day, Sue";
    found("sue");
  }
}
