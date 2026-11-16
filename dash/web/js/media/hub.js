// Media hub: every sound source in one place, so the Media screen, the top bar and the steering
// of play/pause/skip all agree on what's playing.
//
//   phone    Bluetooth audio from a phone (A2DP). Played by the Pi, controlled through /api/audio
//   music    songs on the Pi or a USB stick, played here in an <audio> element
//   radio    internet radio, played here (HLS streams go through the Pi's ffmpeg relay)
//   carplay  CarPlay / Android Auto through a USB adapter, drawn and played here
//
// Only one plays at a time: starting one pauses the others.

import { Mixer, post } from "./mixer.js";
import { CarPlay } from "./carplay.js";

export const SOURCES = [["phone", "Phone"], ["music", "Music"], ["radio", "Radio"], ["carplay", "CarPlay"]];

/** Streams Chromium can't play by itself (HLS, playlists) go through the Pi's ffmpeg relay. */
export function needsRelay(url) { return /\.(m3u8|m3u|pls)(\?|#|$)/i.test(String(url)); }

export class Player {
  constructor(mixer) {
    this.a = new Audio();
    this.a.preload = "auto";
    mixer.attach(this.a);
    this.kind = null;            // music | radio
    this.queue = []; this.i = -1;
    this.station = null; this.stationNo = -1;
    this.shuffle = false;
    this.error = "";
    this.subs = new Set();
    const emit = () => this.emit();
    ["play", "pause", "loadedmetadata", "durationchange", "playing", "waiting"].forEach((e) => this.a.addEventListener(e, emit));
    this.a.addEventListener("ended", () => (this.kind === "music" ? this.next(true) : this.emit()));
    this.a.addEventListener("error", () => {
      this.error = this.kind === "radio" ? "Can't reach that station. Check Wi-Fi or the phone hotspot." : "Can't play that song.";
      this.emit();
      if (this.kind === "music" && this.queue.length > 1) setTimeout(() => this.next(true), 1500);
    });
  }
  on(fn) { this.subs.add(fn); }
  emit() { this.subs.forEach((fn) => fn(this)); }

  get playing() { return !this.a.paused && !this.a.ended && !!this.a.src; }
  get track() { return this.kind === "music" ? this.queue[this.i] : null; }

  playTracks(list, i) { this.kind = "music"; this.queue = list.slice(); this.i = i; this.load(); }
  playStation(st, n, demo = false) {
    this.kind = "radio"; this.station = st; this.stationNo = n;
    if (needsRelay(st.url) && demo) { this.error = "This station needs the Pi (its stream goes through the Pi)."; this.a.removeAttribute("src"); this.emit(); return; }
    this.error = "";
    this.a.src = needsRelay(st.url) ? `/api/media/radio/${n}?t=${Date.now()}` : st.url;
    this.a.play().catch(() => {});
    this.emit();
  }
  load() {
    const t = this.queue[this.i]; if (!t) return this.stop();
    this.error = "";
    this.a.src = t.url;
    this.a.play().catch(() => {});
    this.emit();
  }
  play() {
    if (this.kind === "radio" && this.station) return this.playStation(this.station, this.stationNo);   // radio: rejoin live, not where we paused
    if (this.a.src) this.a.play().catch(() => {});
  }
  pause() { this.a.pause(); }
  toggle() { this.playing ? this.pause() : this.play(); }
  next(auto = false) {
    if (this.kind !== "music" || !this.queue.length) return;
    if (this.shuffle && this.queue.length > 1) { let j; do j = Math.floor(Math.random() * this.queue.length); while (j === this.i); this.i = j; }
    else this.i = (this.i + 1) % this.queue.length;
    if (auto && !this.shuffle && this.i === 0) { this.a.pause(); this.emit(); return; }   // end of the list
    this.load();
  }
  prev() {
    if (this.kind !== "music" || !this.queue.length) return;
    if (this.a.currentTime > 3) { this.a.currentTime = 0; return; }
    this.i = (this.i - 1 + this.queue.length) % this.queue.length; this.load();
  }
  seek(f) { if (this.kind === "music" && isFinite(this.a.duration)) this.a.currentTime = f * this.a.duration; }
  stop() { this.a.pause(); this.a.removeAttribute("src"); this.a.load(); this.kind = null; this.emit(); }
}

export class MediaHub {
  constructor(ctx) {
    this.ctx = ctx;
    const s = ctx.settings;
    this.demo = () => !!ctx.store.get("link.demo");
    this.mixer = new Mixer({ server: true });
    this.mixer.level = s.get("media.volume") ?? 0.6;
    this.mixer.duckTo = s.get("media.duckTo") ?? 0.25;
    this.player = new Player(this.mixer);
    this.carplay = new CarPlay(this.mixer, () => ({
      width: 1176, height: 736, hand: s.get("media.carplay.hand"), autoStart: s.get("media.carplay.autoStart") !== false,
      nightMode: document.body.classList.contains("theme-night"),
    }));
    this.source = s.get("media.source") || "music";
    this.audio = null;           // last /api/audio status
    this.audioErr = "";
    this.subs = new Set();
    this.player.on(() => this.emit());
    this.carplay.on(() => this.emit());
    this.mixer.on(() => this.emit());
  }

  on(fn) { this.subs.add(fn); }
  emit() { this.subs.forEach((fn) => fn(this)); }

  /** After settings have loaded from the Pi. */
  applySettings() {
    const s = this.ctx.settings;
    this.mixer.level = s.get("media.volume") ?? 0.6;
    this.mixer.duckTo = s.get("media.duckTo") ?? 0.25;
    this.source = s.get("media.source") || "music";
    this.mixer.apply(true);
  }

  start() {
    this.mixer.server = !this.demo();
    if (!this.demo()) post("audio/media-level", { level: this.mixer.level }).catch(() => {});
    this.poll();
    // The adapter may already be plugged in (and allowed by the kiosk policy).
    if (this.ctx.settings.get("media.carplay.autoStart") !== false && "usb" in navigator) this.carplay.start().catch(() => {});
  }

  async poll() {
    clearTimeout(this._poll);
    this.mixer.server = !this.demo();
    if (!this.demo()) {
      try {
        const r = await fetch("/api/audio", { cache: "no-store" });
        if (!r.ok) throw new Error(r.status);
        const was = this.phone && this.phone.status;
        this.audio = await r.json(); this.audioErr = "";
        // Pressed play on the phone itself: it wins, so pause the music or radio here.
        if (this.phone && this.phone.status === "playing" && was !== "playing" && this.player.playing) this.player.pause();
      } catch (e) { this.audioErr = `${e.message}`; }
      this.emit();
    }
    this._poll = setTimeout(() => this.poll(), this.fast ? 1000 : 3000);
  }

  setSource(src) {
    this.source = src;
    this.ctx.settings.set("media.source", src);
    this.emit();
  }

  get phone() { return this.audio && this.audio.bt && this.audio.bt.player; }

  /** Before something new starts playing, quieten everything else. */
  async exclusive(keep) {
    if (keep !== "music" && keep !== "radio" && this.player.playing) this.player.pause();
    if ((keep === "music" || keep === "radio") && this.player.playing && this.player.kind !== keep) this.player.pause();
    if (keep !== "phone" && this.phone && this.phone.status === "playing") await this.bt("pause").catch(() => {});
    if (keep !== "carplay" && this.carplay.state === "connected" && this.carplay.media.playing) this.carplay.command("pause");
  }

  async bt(cmd) {
    const j = await post(`audio/bt/${cmd}`);
    this.audio = j; this.emit();
    return j;
  }

  playTracks(list, i) { this.exclusive("music"); this.player.playTracks(list, i); this.setSource("music"); }
  playStation(st, n) { this.exclusive("radio"); this.player.playStation(st, n, this.demo()); this.setSource("radio"); }

  /** What's playing right now, for the top bar and the Now Playing panel. */
  nowPlaying() {
    const p = this.player, ph = this.phone, cp = this.carplay;
    if ((p.kind === "music" || p.kind === "radio") && (p.playing || this.source === p.kind)) {
      if (p.kind === "music" && p.track) return { source: "music", title: p.track.title, artist: p.track.artist, album: p.track.album, playing: p.playing, pos: p.a.currentTime, dur: p.a.duration, error: p.error };
      if (p.kind === "radio" && p.station) return { source: "radio", title: p.station.name, artist: "Internet radio", album: "", playing: p.playing, live: true, error: p.error };
    }
    if (ph && (ph.status === "playing" || this.source === "phone"))
      return { source: "phone", title: ph.title || "Phone audio", artist: ph.artist, album: ph.album, playing: ph.status === "playing", pos: ph.position_ms / 1000, dur: ph.duration_ms / 1000, device: ph.device };
    if (cp.state === "connected" && (cp.media.playing || this.source === "carplay"))
      return { source: "carplay", title: cp.media.title || cp.phone, artist: cp.media.artist, album: cp.media.album, playing: !!cp.media.playing, art: cp.media.art, pos: (cp.media.position_ms || 0) / 1000, dur: (cp.media.duration_ms || 0) / 1000 };
    return { source: this.source, title: "", artist: "", album: "", playing: false };
  }

  // Buttons on the Now Playing panel act on whatever is playing.
  async toggle() {
    const np = this.nowPlaying();
    if (np.source === "phone") { await this.exclusive("phone"); return this.bt(np.playing ? "pause" : "play").catch((e) => this.fail(e)); }
    if (np.source === "carplay") return this.carplay.command(np.playing ? "pause" : "play");
    if (np.source === "music" || np.source === "radio") { if (!np.playing) await this.exclusive(np.source); return this.player.toggle(); }
  }
  next() {
    const s = this.nowPlaying().source;
    if (s === "phone") return this.bt("next").catch((e) => this.fail(e));
    if (s === "carplay") return this.carplay.command("next");
    this.player.next();
  }
  prev() {
    const s = this.nowPlaying().source;
    if (s === "phone") return this.bt("previous").catch((e) => this.fail(e));
    if (s === "carplay") return this.carplay.command("prev");
    this.player.prev();
  }
  setVolume(v) { this.mixer.setLevel(v); this.ctx.settings.set("media.volume", Math.round(v * 100) / 100); }
  fail(e) { this.lastError = e.message; this.emit(); }
}
