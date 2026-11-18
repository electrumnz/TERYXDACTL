// Campfire for camp mode: drawn live on a canvas (no video file), with a crackle made
// with Web Audio (no sound file). Kept light so the Pi stays cool: about 30 fps, small canvas
// scaled up, and it stops completely when camp mode closes.
import { audioContext } from "../sound.js";

export class Campfire {
  constructor(canvas) {
    this.cv = canvas;
    this.g = canvas.getContext("2d");
    this.sparks = [];
    this.flames = [];
    this.t = 0;
    this.running = false;
    this.heat = 1;          // 0..1, how big the fire is
  }

  start() {
    if (this.running) return;
    this.running = true;
    let last = performance.now(), acc = 0;
    const step = (now) => {
      if (!this.running) return;
      acc += now - last; last = now;
      if (acc >= 33) { this.frame(Math.min(acc, 100) / 1000); acc = 0; }
      this.raf = requestAnimationFrame(step);
    };
    this.raf = requestAnimationFrame(step);
  }

  stop() { this.running = false; cancelAnimationFrame(this.raf); this.sound(false); }

  frame(dt) {
    const { g, cv } = this, W = cv.width, H = cv.height;
    this.t += dt;
    const base = H * 0.78, cx = W / 2;
    // Night sky with a warm glow that breathes with the fire
    const flick = 0.85 + 0.15 * Math.sin(this.t * 7.3) * Math.sin(this.t * 3.1 + 1);
    const sky = g.createRadialGradient(cx, base, 10, cx, base, W * 0.7);
    sky.addColorStop(0, `rgba(255,120,30,${0.35 * flick * this.heat})`);
    sky.addColorStop(0.35, "rgba(70,25,8,0.6)");
    sky.addColorStop(1, "rgba(5,3,2,1)");
    g.fillStyle = sky; g.fillRect(0, 0, W, H);
    // Ground
    g.fillStyle = "#0d0805"; g.fillRect(0, base + 18, W, H - base);
    // Stones ring
    for (let i = 0; i < 9; i++) {
      const a = Math.PI * (i / 8);
      const x = cx - Math.cos(a) * W * 0.17, y = base + 22 - Math.sin(a) * 6;
      g.fillStyle = i % 2 ? "#3a3129" : "#2c251f";
      g.beginPath(); g.ellipse(x, y, 16, 10, 0, 0, Math.PI * 2); g.fill();
    }
    // Logs
    g.lineCap = "round";
    [[-1, "#4a2c18"], [1, "#3b2312"]].forEach(([d, c]) => {
      g.strokeStyle = c; g.lineWidth = 18;
      g.beginPath(); g.moveTo(cx - d * W * 0.13, base + 18); g.lineTo(cx + d * W * 0.07, base - 4); g.stroke();
    });
    g.strokeStyle = `rgba(255,${90 + 60 * flick | 0},20,.8)`; g.lineWidth = 3;
    g.beginPath(); g.moveTo(cx - W * 0.05, base + 6); g.lineTo(cx + W * 0.04, base + 2); g.stroke();
    // Flames: blobs that rise, shrink and cool from white-yellow to red
    const n = Math.round(10 * this.heat) + 2;
    for (let i = 0; i < n; i++) {
      this.flames.push({ x: cx + (Math.random() - 0.5) * W * 0.16, y: base, r: 18 + Math.random() * 26 * this.heat, life: 0, max: 0.7 + Math.random() * 0.6, vx: (Math.random() - 0.5) * 20 });
    }
    g.globalCompositeOperation = "lighter";
    this.flames = this.flames.filter((f) => {
      f.life += dt; if (f.life > f.max) return false;
      const k = f.life / f.max;
      f.y -= (90 + 70 * (1 - k)) * dt * (H / 400);
      f.x += (f.vx + Math.sin(this.t * 3 + f.y * 0.05) * 25) * dt + (cx - f.x) * dt * 1.6;
      const r = f.r * (1 - k * 0.85);
      const col = k < 0.15 ? [255, 220, 130] : k < 0.55 ? [255, 150, 40] : [220, 60, 15];
      const grd = g.createRadialGradient(f.x, f.y, 0, f.x, f.y, r);
      grd.addColorStop(0, `rgba(${col[0]},${col[1]},${col[2]},${0.42 * (1 - k)})`);
      grd.addColorStop(1, "rgba(0,0,0,0)");
      g.fillStyle = grd; g.beginPath(); g.arc(f.x, f.y, r, 0, Math.PI * 2); g.fill();
      return true;
    });
    // Sparks
    if (Math.random() < 0.35 * this.heat) this.sparks.push({ x: cx + (Math.random() - 0.5) * 40, y: base - 20, vx: (Math.random() - 0.5) * 40, vy: -80 - Math.random() * 120, life: 0, max: 1 + Math.random() * 1.5 });
    this.sparks = this.sparks.filter((s) => {
      s.life += dt; if (s.life > s.max) return false;
      s.x += s.vx * dt + Math.sin(this.t * 4 + s.y * 0.03) * 0.6; s.y += s.vy * dt;
      g.fillStyle = `rgba(255,${180 - 100 * (s.life / s.max) | 0},60,${1 - s.life / s.max})`;
      g.fillRect(s.x, s.y, 2.2, 2.2);
      return true;
    });
    g.globalCompositeOperation = "source-over";
  }

  /** Fire crackle: soft brown-noise roar plus random pops. Goes through its own gain so it can be muted. */
  sound(on, volume = 0.5) {
    if (!on) {
      if (this.snd) { try { this.snd.src.stop(); this.snd.gain.disconnect(); } catch {} clearTimeout(this.snd.pop); this.snd = null; }
      return;
    }
    if (this.snd) { this.snd.gain.gain.value = volume; return; }
    const a = audioContext(); if (!a) return;
    const len = a.sampleRate * 4, buf = a.createBuffer(1, len, a.sampleRate), d = buf.getChannelData(0);
    let last = 0;
    for (let i = 0; i < len; i++) { last = (last + 0.02 * (Math.random() * 2 - 1)) / 1.02; d[i] = last * 3.2; }
    const src = a.createBufferSource(); src.buffer = buf; src.loop = true;
    const lp = a.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 600;
    const gain = a.createGain(); gain.gain.value = volume;
    src.connect(lp); lp.connect(gain); gain.connect(a.destination);
    src.start();
    this.snd = { src, gain };
    const pop = () => {
      if (!this.snd) return;
      const t = a.currentTime, n = a.createBufferSource(), pb = a.createBuffer(1, a.sampleRate * 0.03, a.sampleRate), pd = pb.getChannelData(0);
      for (let i = 0; i < pd.length; i++) pd[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / pd.length, 3);
      n.buffer = pb;
      const hp = a.createBiquadFilter(); hp.type = "highpass"; hp.frequency.value = 1500 + Math.random() * 2500;
      const pg = a.createGain(); pg.gain.value = 0.3 + Math.random() * 0.6;
      n.connect(hp); hp.connect(pg); pg.connect(gain); n.start(t);
      this.snd.pop = setTimeout(pop, 80 + Math.random() * (Math.random() < 0.2 ? 200 : 1400));
    };
    pop();
  }
}
