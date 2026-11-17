// Alert sounds, made on the fly with Web Audio (no sound files to ship or licence).
//   bad    three sharp high beeps, repeated until you tap OK or it clears
//   warn   two softer beeps, once
//   info   a short rising chirp
//   reject a low buzz when the control box says no
//   count  one short beep per second of the timed pull countdown, go when it starts
//   done   a timed pull has finished
//   click  a tiny tick on each press, so you know a gloved tap landed
// The kiosk starts Chromium with --autoplay-policy=no-user-gesture-required so sound works
// before the first touch. In a normal browser it starts after the first tap.

let ctx = null, master = null;

/** The one AudioContext the page uses (alerts, and CarPlay audio). Made on first use. */
export function audioContext() { return audio(); }

function audio() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
    master = ctx.createGain();
    master.connect(ctx.destination);
  }
  if (ctx.state === "suspended") ctx.resume().catch(() => {});
  return ctx;
}

// Wake the audio on the first touch, for browsers that need a gesture.
window.addEventListener("pointerdown", () => audio(), { once: true, capture: true });

function tone(freq, start, dur, { type = "sine", vol = 1, slide = 0 } = {}) {
  const a = ctx, o = a.createOscillator(), g = a.createGain();
  o.type = type;
  o.frequency.setValueAtTime(freq, start);
  if (slide) o.frequency.linearRampToValueAtTime(freq + slide, start + dur);
  g.gain.setValueAtTime(0.0001, start);
  g.gain.exponentialRampToValueAtTime(vol, start + 0.01);
  g.gain.exponentialRampToValueAtTime(0.0001, start + dur);
  o.connect(g); g.connect(master);
  o.start(start); o.stop(start + dur + 0.02);
}

const PATTERNS = {
  bad:    (t) => { for (let i = 0; i < 3; i++) tone(1046, t + i * 0.16, 0.11, { type: "square", vol: 0.5 }); },
  warn:   (t) => { tone(784, t, 0.16, { vol: 0.8 }); tone(659, t + 0.22, 0.2, { vol: 0.8 }); },
  info:   (t) => { tone(587, t, 0.14, { vol: 0.6, slide: 300 }); },
  reject: (t) => { tone(196, t, 0.18, { type: "sawtooth", vol: 0.35 }); },
  count:  (t) => { tone(880, t, 0.12, { type: "square", vol: 0.45 }); },
  go:     (t) => { tone(1318, t, 0.35, { type: "square", vol: 0.5 }); },
  done:   (t) => { tone(1046, t, 0.12, { vol: 0.7 }); tone(784, t + 0.15, 0.2, { vol: 0.7 }); },
  click:  (t) => { tone(1800, t, 0.025, { type: "triangle", vol: 0.25 }); },
};

export const Sound = {
  enabled: true,
  volume: 0.7,
  clicks: true,
  log: [],          // what was played, for the bench tests
  onPlay: null,     // the media mixer listens here, to turn music down under alerts
  play(kind) {
    if (!this.enabled || (kind === "click" && !this.clicks)) return false;
    this.log.push({ kind, at: Date.now() }); if (this.log.length > 50) this.log.shift();
    if (kind !== "click" && this.onPlay) { try { this.onPlay(kind); } catch {} }
    const a = audio(); if (!a || !PATTERNS[kind]) return false;
    master.gain.value = Math.max(0, Math.min(1, this.volume));
    PATTERNS[kind](a.currentTime + 0.01);
    return true;
  },
};
