// CarPlay and Android Auto through a Carlinkit USB adapter, drawn inside the dash.
//
// Uses node-carplay (MIT, dash/web/lib/node-carplay.js) over WebUSB, so it runs in the dash page
// itself: the top bar, nav and alert banner stay on screen, and its sound goes through the
// media mixer so it ducks under alerts like everything else.
//
// Adapter: a Carlinkit CPC200-CCPA (wireless and wired) or CPC200-Autokit. NOT the kind that turns
// a car's wired CarPlay into wireless; those need a car, not a screen.
//
//   video  H.264 from the adapter, decoded with WebCodecs and drawn on a canvas
//   sound  16-bit PCM from the adapter, played with Web Audio through a mixer gain node
//   touch  finger on the canvas is sent back as touches (0..1 of the picture)
//
// No adapter (laptop, simulator)? startTest() draws a test picture instead, so the layout,
// touches and alerts on top can still be tried.

import { audioContext } from "../sound.js";

const VENDOR = "../../lib/node-carplay.js";
export const PHONE_TYPES = { 3: "CarPlay", 5: "Android Auto", 1: "Android mirror", 4: "iPhone mirror" };

export class CarPlay {
  constructor(mixer, getConfig) {
    this.mixer = mixer;
    this.getConfig = getConfig;    // () => ({ width, height, hand, nightMode, autoStart })
    this.state = "off";            // off | no_webusb | no_adapter | starting | waiting | connected | test | error
    this.error = "";
    this.phone = "";
    this.media = {};               // title, artist, album, art (data: URL), playing
    this.canvas = null;
    this.visible = false;
    this.subs = new Set();
    this.lib = null;
    this.cp = null;
    this.decoder = null;
    this.needKey = true;
    this.ts = 0;
    this.q = {};
    this.gain = null;
    this.frames = 0;
    this.touches = [];             // test picture: recent touches
    this._usbHooked = false;
  }

  on(fn) { this.subs.add(fn); }
  emit() { this.subs.forEach((fn) => fn(this)); }
  set(state, error = "") { this.state = state; this.error = error; this.emit(); }

  get active() { return this.state === "connected" || this.state === "test"; }

  async load() {
    if (!this.lib) this.lib = await import(VENDOR);
    return this.lib;
  }

  /** Start with an adapter that's already been allowed (kiosk policy, or picked once before). */
  async start({ pick = false } = {}) {
    if (this.cp || this.state === "starting") return;
    if (!("usb" in navigator)) return this.set("no_webusb", "This browser can't talk to USB devices (WebUSB). Use Chromium.");
    this.set("starting");
    let lib;
    try { lib = await this.load(); } catch (e) { return this.set("error", `Couldn't load the CarPlay driver (${e.message}).`); }
    this.hookUsb(lib);
    let dev = await lib.findDevice();
    if (!dev && pick) dev = await lib.requestDevice();
    if (!dev) return this.set("no_adapter");
    const c = this.getConfig();
    const cp = new lib.CarplayWeb({
      width: c.width, height: c.height, fps: 25, dpi: 160, boxName: "Teryx",
      hand: c.hand === "lhd" ? lib.HandDriveType.LHD : lib.HandDriveType.RHD,
      nightMode: !!c.nightMode, mediaDelay: 300,
    });
    cp.onmessage = (m) => this.message(m);
    this.cp = cp;
    try {
      await cp.start(dev);
      this.set("waiting");
    } catch (e) {
      this.cp = null;
      this.set("error", `The adapter didn't start (${e.message || e}). Unplug it, wait 5 s and plug it back in.`);
    }
  }

  async stop() {
    const cp = this.cp; this.cp = null;
    this.closeDecoder();
    this.media = {};
    this.phone = "";
    if (cp) { try { await cp.stop(); } catch {} }
    if (this.state !== "no_webusb") this.set("off");
  }

  hookUsb(lib) {
    if (this._usbHooked) return;
    this._usbHooked = true;
    navigator.usb.addEventListener("connect", (e) => {
      if (lib.isCarplayDongle(e.device) && this.getConfig().autoStart && !this.cp) setTimeout(() => this.start(), 1500);
    });
    navigator.usb.addEventListener("disconnect", (e) => {
      if (lib.isCarplayDongle(e.device) && this.cp) { this.stop().then(() => this.set("no_adapter")); }
    });
  }

  message(m) {
    switch (m.type) {
      case "plugged": this.phone = PHONE_TYPES[m.phoneType] || "Phone"; this.needKey = true; this.set("connected"); this.command("frame"); break;
      case "unplugged": this.phone = ""; this.media = {}; this.closeDecoder(); this.set("waiting"); break;
      case "video": if (this.state !== "connected") this.set("connected"); this.video(m.message); break;
      case "audio": this.audio(m.message); break;
      case "media": this.mediaData(m.message.payload); break;
      case "failure": this.cp = null; this.closeDecoder(); this.set("error", "Lost the CarPlay adapter. Check its USB lead."); break;
      default: break;
    }
  }

  // ---------- video ----------
  attach(canvas) {
    this.canvas = canvas;
    this.ctx2d = canvas.getContext("2d");
    this.bindTouch(canvas);
  }
  setVisible(v) {
    if (v === this.visible) return;
    this.visible = v;
    // Frames aren't decoded while nobody can see them (saves the Pi). Ask for a fresh key frame on return.
    if (v) { this.needKey = true; this.command("frame"); if (this.state === "test") this.drawTest(); }
  }

  closeDecoder() {
    try { if (this.decoder && this.decoder.state !== "closed") this.decoder.close(); } catch {}
    this.decoder = null; this.needKey = true;
  }

  video(v) {
    if (!this.visible || !this.canvas || !v.data) return;
    const data = v.data instanceof Uint8Array ? v.data : new Uint8Array(v.data);
    const { key, sps } = scanNals(data);
    if (!this.decoder) {
      if (!sps || typeof VideoDecoder === "undefined") return;
      this.decoder = new VideoDecoder({
        output: (frame) => { try { this.ctx2d.drawImage(frame, 0, 0, this.canvas.width, this.canvas.height); this.frames++; } finally { frame.close(); } },
        error: () => { this.closeDecoder(); this.command("frame"); },
      });
      try { this.decoder.configure({ codec: avcCodec(sps), optimizeForLatency: true }); }
      catch { this.closeDecoder(); return; }
    }
    if (this.needKey && !key) return;
    this.needKey = false;
    if (this.decoder.decodeQueueSize > 6) { this.needKey = true; this.command("frame"); return; }   // falling behind: skip ahead
    this.ts += 40000;
    try { this.decoder.decode(new EncodedVideoChunk({ type: key ? "key" : "delta", timestamp: this.ts, data })); }
    catch { this.closeDecoder(); }
  }

  // ---------- sound ----------
  audio(a) {
    if (!a.data || !this.lib) return;
    const fmt = this.lib.decodeTypeMap[a.decodeType]; if (!fmt) return;
    const ac = audioContext(); if (!ac) return;
    if (!this.gain) { this.gain = ac.createGain(); this.gain.connect(ac.destination); this.mixer.attachGain(this.gain); }
    const ch = fmt.channel, n = Math.floor(a.data.length / ch);
    if (!n) return;
    const buf = ac.createBuffer(ch, n, fmt.frequency);
    for (let c = 0; c < ch; c++) {
      const out = buf.getChannelData(c);
      for (let i = 0; i < n; i++) out[i] = a.data[i * ch + c] / 32768;
    }
    const key = `${a.audioType}/${a.decodeType}`;
    const q = this.q[key] || (this.q[key] = { t: 0 });
    const now = ac.currentTime;
    if (q.t < now + 0.02 || q.t > now + 0.6) q.t = now + 0.08;   // small cushion against USB hiccups, no big lag
    const src = ac.createBufferSource();
    src.buffer = buf; src.connect(this.gain); src.start(q.t);
    q.t += buf.duration;
  }

  mediaData(p) {
    if (!p) return;
    if (p.base64Image) this.media.art = `data:image/jpeg;base64,${p.base64Image}`;
    if (p.media) {
      const m = p.media;
      if (m.MediaSongName != null) this.media.title = m.MediaSongName;
      if (m.MediaArtistName != null) this.media.artist = m.MediaArtistName;
      if (m.MediaAlbumName != null) this.media.album = m.MediaAlbumName;
      if (m.MediaSongDuration != null) this.media.duration_ms = m.MediaSongDuration;
      if (m.MediaSongPlayTime != null) this.media.position_ms = m.MediaSongPlayTime;
      if (m.MediaPlayStatus != null) this.media.playing = !!m.MediaPlayStatus;
    }
    this.emit();
  }

  // ---------- touch and buttons ----------
  bindTouch(canvas) {
    const pos = (e) => { const r = canvas.getBoundingClientRect(); return [(e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height]; };
    let down = false;
    canvas.addEventListener("pointerdown", (e) => { down = true; canvas.setPointerCapture(e.pointerId); this.touch(...pos(e), "Down"); });
    canvas.addEventListener("pointermove", (e) => { if (down) this.touch(...pos(e), "Move"); });
    const up = (e) => { if (!down) return; down = false; this.touch(...pos(e), "Up"); };
    canvas.addEventListener("pointerup", up);
    canvas.addEventListener("pointercancel", up);
  }

  touch(x, y, action) {
    x = Math.max(0, Math.min(1, x)); y = Math.max(0, Math.min(1, y));
    if (this.state === "test") { this.testTouch(x, y, action); return; }
    if (!this.cp || !this.lib) return;
    this.cp.dongleDriver.send(new this.lib.SendTouch(x, y, this.lib.TouchAction[action])).catch?.(() => {});
  }

  /** play | pause | next | prev | home | siri | frame | enableNightMode | disableNightMode */
  command(name) {
    if (!this.cp || !this.lib) return;
    try { const p = this.cp.dongleDriver.send(new this.lib.SendCommand(name)); p && p.catch && p.catch(() => {}); } catch {}
  }

  // ---------- test picture (no adapter) ----------
  startTest() {
    this.closeDecoder();
    this.phone = "Test picture";
    this.media = { title: "Test picture", artist: "No adapter fitted", album: "" };
    this.testHit = -1;
    this.set("test");
    this.drawTest();
  }
  stopTest() { if (this.state === "test") { this.media = {}; this.phone = ""; this.set("off"); } }

  testTouch(x, y, action) {
    this.touches.push({ x, y, at: performance.now(), action });
    if (this.touches.length > 40) this.touches.shift();
    if (action === "Down") this.testHit = hitTile(x, y, this.canvas.width, this.canvas.height);
    if (action === "Up") this.testHit = -1;
    this.drawTest();
  }

  drawTest() {
    const c = this.canvas; if (!c || this.state !== "test") return;
    const g = this.ctx2d, W = c.width, H = c.height;
    g.fillStyle = "#101418"; g.fillRect(0, 0, W, H);
    // Side strip like a phone projection has, with a home dot.
    g.fillStyle = "#1c232a"; g.fillRect(0, 0, 96, H);
    g.fillStyle = "#e8eef2"; g.beginPath(); g.arc(48, H - 60, 22, 0, Math.PI * 2); g.fill();
    g.font = "bold 22px DejaVu Sans, sans-serif"; g.textAlign = "center";
    g.fillText(new Date().toLocaleTimeString("en-NZ", { hour: "2-digit", minute: "2-digit", hour12: false }), 48, 44);
    const cols = ["#ff6b4a", "#ffb02e", "#3ecf6e", "#33b6ff", "#9b7bff", "#ff5fa8", "#20d3c2", "#c0c7cc"];
    for (let i = 0; i < 8; i++) {
      const r = tileRect(i, W, H);
      g.fillStyle = cols[i]; g.globalAlpha = this.testHit === i ? 0.55 : 1;
      roundRect(g, r.x, r.y, r.w, r.h, 26); g.fill(); g.globalAlpha = 1;
      g.fillStyle = "#fff"; g.font = "bold 22px DejaVu Sans, sans-serif";
      g.fillText(`App ${i + 1}`, r.x + r.w / 2, r.y + r.h + 30);
    }
    g.fillStyle = "#8b959b"; g.font = "18px DejaVu Sans, sans-serif";
    g.fillText("Test picture: no CarPlay adapter. Touches show as dots.", W / 2 + 48, H - 24);
    const now = performance.now();
    for (const t of this.touches) {
      const age = (now - t.at) / 1500; if (age > 1) continue;
      g.fillStyle = `rgba(255,173,31,${1 - age})`; g.beginPath(); g.arc(t.x * W, t.y * H, 14, 0, Math.PI * 2); g.fill();
    }
    if (this.touches.some((t) => now - t.at < 1500)) requestAnimationFrame(() => this.drawTest());
  }
}

function tileRect(i, W, H) {
  const left = 140, gap = 40, cols = 4, w = Math.min(150, (W - left - gap * (cols + 1)) / cols), h = w;
  const col = i % cols, row = Math.floor(i / cols);
  const total = cols * w + (cols - 1) * gap;
  const x0 = 96 + (W - 96 - total) / 2;
  const y0 = (H - (2 * h + 70 + gap)) / 2;
  return { x: x0 + col * (w + gap), y: y0 + row * (h + 70 + gap), w, h };
}
function hitTile(x, y, W, H) {
  for (let i = 0; i < 8; i++) { const r = tileRect(i, W, H); if (x * W >= r.x && x * W <= r.x + r.w && y * H >= r.y && y * H <= r.y + r.h) return i; }
  return -1;
}
function roundRect(g, x, y, w, h, r) {
  g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
}

/** Find NAL unit types in an Annex B H.264 chunk: is it a key frame, and the SPS if there is one. */
export function scanNals(d) {
  let key = false, sps = null;
  for (let i = 0; i + 3 < d.length; i++) {
    if (d[i] === 0 && d[i + 1] === 0 && (d[i + 2] === 1 || (d[i + 2] === 0 && d[i + 3] === 1))) {
      const s = d[i + 2] === 1 ? i + 3 : i + 4;
      const t = d[s] & 0x1f;
      if (t === 5) key = true;
      if (t === 7) { key = true; sps = d.subarray(s, s + 4); }
      i = s;
    }
  }
  return { key, sps };
}

/** "avc1.PPCCLL" from an SPS (profile, constraints, level). */
export function avcCodec(sps) {
  const h = (b) => b.toString(16).padStart(2, "0");
  return `avc1.${h(sps[1])}${h(sps[2])}${h(sps[3])}`;
}
