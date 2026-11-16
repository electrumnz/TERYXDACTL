// Media: CarPlay / Android Auto, Bluetooth audio from a phone, songs on the Pi or a USB stick,
// and internet radio. One volume for all of them; alerts always play over the top (and the
// music dips under them), see js/media/mixer.js.
import { el, $, $$, toast, Slider } from "../ui/controls.js";
import { icon } from "../ui/icons.js";
import { keyboard } from "../ui/keyboard.js";
import { SOURCES } from "../media/hub.js";

const esc = (t) => String(t ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const mmss = (s) => (s == null || !isFinite(s) ? "--:--" : `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`);
const SRC_ICON = { phone: "bluetooth", music: "music", radio: "radio", carplay: "carplay" };

const CP_TEXT = {
  off: ["CarPlay and Android Auto", "Plug the CarPlay adapter into a USB port on the Pi, then tap Start."],
  no_webusb: ["Can't use USB here", "This browser can't talk to the adapter. The dash on the Pi (Chromium) can."],
  no_adapter: ["No CarPlay adapter found", "Plug a Carlinkit CPC200-CCPA (or Autokit) into the Pi. If it's plugged in, tap Find adapter once to allow it."],
  starting: ["Starting the adapter", "This takes a few seconds."],
  waiting: ["Adapter ready, waiting for a phone", "iPhone: plug it into the adapter with a cable, or for wireless, pair with the adapter in your phone's Bluetooth (it shows as \"Teryx\" or \"AutoKit\") the first time. Android Auto works the same way."],
  error: ["Adapter problem", ""],
};

export class MediaScreen {
  constructor(ctx) { this.ctx = ctx; this.id = "media"; this.label = "Media"; this.icon = "music"; this.tracks = null; }

  get hub() { return this.ctx.media; }

  mount(root) {
    root.innerHTML = `
      <div class="media">
        <div class="seg md-tabs" id="md-tabs">${SOURCES.map(([k, l]) => `<button data-k="${k}">${icon(SRC_ICON[k])}<span>${l}</span></button>`).join("")}</div>
        <div class="md-body">
          <div class="panel md-now">
            <div class="md-art" id="md-art">${icon("music")}</div>
            <div class="md-src muted small" id="md-src"></div>
            <div class="md-title" id="md-title">Nothing playing</div>
            <div class="md-artist muted" id="md-artist"></div>
            <div class="md-prog"><div class="md-bar" id="md-bar"><div></div></div><div class="md-times num muted small"><span id="md-pos"></span><span id="md-dur"></span></div></div>
            <div class="md-ctl">
              <button class="btn md-btn" id="md-prev" aria-label="Previous">${icon("prev")}</button>
              <button class="btn md-btn md-play" id="md-play" aria-label="Play or pause">${icon("play")}</button>
              <button class="btn md-btn" id="md-next" aria-label="Next">${icon("next")}</button>
            </div>
            <div id="md-vol"></div>
            <div class="md-duck muted small" id="md-duck"></div>
          </div>
          <div class="panel md-side" id="md-side"></div>
        </div>
        <div class="md-cp" id="md-cp" hidden>
          <canvas id="md-canvas" width="1176" height="736"></canvas>
          <button class="md-cp-back" id="md-cp-back" aria-label="Back to Media">${icon("back")}<span>Media</span></button>
        </div>
      </div>`;
    this.root = root;
    $$(root, "#md-tabs button").forEach((b) => (b.onclick = () => this.pick(b.dataset.k)));
    $(root, "#md-play").onclick = () => this.hub.toggle();
    $(root, "#md-next").onclick = () => this.hub.next();
    $(root, "#md-prev").onclick = () => this.hub.prev();
    $(root, "#md-bar").onclick = (e) => {
      const r = e.currentTarget.getBoundingClientRect();
      if (this.hub.nowPlaying().source === "music") this.hub.player.seek((e.clientX - r.left) / r.width);
    };
    this.vol = new Slider({ min: 0, max: 100, step: 1, value: Math.round(this.hub.mixer.level * 100), label: "Volume", fmt: (v) => `${v}%`, onChange: (v) => this.hub.setVolume(v / 100) });
    $(root, "#md-vol").appendChild(this.vol.root);
    this.hub.carplay.attach($(root, "#md-canvas"));
    $(root, "#md-cp-back").onclick = () => { this.cpFull = false; this.render(); };
    this.cpFull = true;
    this.hub.on(() => { if (this.ctx.current === this) this.render(); });
    this.hub.carplay.on((cp) => {
      // A phone plugged in while on this screen: go straight to its picture.
      if (cp.state === "connected" && this._cpWas !== "connected" && this.hub.source === "carplay") this.cpFull = true;
      this._cpWas = cp.state;
    });
    this.sideFor = null;
  }

  show() {
    this.hub.fast = true; this.hub.poll(); this.render(true);
    clearInterval(this._tick); this._tick = setInterval(() => this.render(), 500);   // song position
  }
  hide() { this.hub.fast = false; clearInterval(this._tick); this.hub.carplay.setVisible(false); }

  pick(k) {
    this.hub.setSource(k);
    if (k === "carplay") this.cpFull = true;
    this.render(true);
  }

  render(force = false) {
    const h = this.hub, r = this.root, src = h.source, cp = h.carplay;
    $$(r, "#md-tabs button").forEach((b) => b.classList.toggle("on", b.dataset.k === src));
    const full = src === "carplay" && cp.active && this.cpFull;
    $(r, "#md-cp").hidden = !full;
    cp.setVisible(full && this.ctx.current === this);
    if (full && cp.state === "test") cp.drawTest();

    // Now playing
    const np = h.nowPlaying();
    $(r, "#md-src").innerHTML = np.title ? `${icon(SRC_ICON[np.source])}<span>${esc({ phone: np.device ? `Bluetooth: ${np.device}` : "Bluetooth", music: "Music", radio: "Radio", carplay: cp.phone || "CarPlay" }[np.source])}</span>` : "";
    $(r, "#md-title").textContent = np.title || "Nothing playing";
    $(r, "#md-artist").textContent = np.error || [np.artist, np.album].filter(Boolean).join(" · ");
    $(r, "#md-artist").classList.toggle("bad", !!np.error);
    const art = $(r, "#md-art");
    const artHtml = np.art ? `<img src="${np.art}" alt="">` : icon(SRC_ICON[np.source] || "music");
    if (art._h !== artHtml) { art.innerHTML = artHtml; art._h = artHtml; }
    const f = np.dur > 0 && np.pos != null ? Math.min(1, np.pos / np.dur) : 0;
    $(r, "#md-bar div").style.width = np.live ? "100%" : `${f * 100}%`;
    $(r, "#md-bar").classList.toggle("live", !!np.live);
    $(r, "#md-pos").textContent = np.live ? "LIVE" : np.title ? mmss(np.pos) : "";
    $(r, "#md-dur").textContent = np.live || !np.title ? "" : mmss(np.dur);
    const pb = $(r, "#md-play"), want = np.playing ? "pause" : "play";
    if (pb._i !== want) { pb.innerHTML = icon(want); pb._i = want; }
    $(r, "#md-prev").disabled = $(r, "#md-next").disabled = np.source === "radio" || !np.title;
    this.vol.set(Math.round(h.mixer.level * 100));
    const m = h.mixer;
    $(r, "#md-duck").textContent = m.ducked ? `Turned down to ${Math.round(m.duckTo * 100)}% ${m.reasons.has("reverse") ? "while reversing" : "for an alert"}.` : "";

    // Side panel for the chosen source
    const side = $(r, "#md-side");
    if (force || this.sideFor !== src) { side.innerHTML = ""; this.sideFor = src; this[`side_${src}`](side, true); }
    else this[`side_${src}`](side, false);
  }

  // ---------- Phone (Bluetooth) ----------
  side_phone(side, build) {
    const h = this.hub, a = h.audio, demo = h.demo();
    if (build) {
      side.innerHTML = `<h3>Phone over Bluetooth</h3><div id="ph-body"></div>`;
    }
    const body = $(side, "#ph-body");
    let html;
    if (demo) html = `<div class="muted">Bluetooth needs the Pi. Not available in demo mode.</div>`;
    else if (!a) html = `<div class="muted">${h.audioErr ? `Can't reach the Pi's audio (${esc(h.audioErr)}).` : "Checking…"}</div>`;
    else if (!a.bt.available) html = `<div class="muted">Bluetooth isn't running on the Pi. Run <b>sudo bash scripts/audio-setup.sh</b> on the Pi once.</div>`;
    else {
      const bt = a.bt, ph = bt.player;
      const pairing = bt.pairing > 0
        ? `<div class="md-pair on"><div><b>Pairing is open for ${mmss(bt.pairing)}</b><div class="muted small">On your phone: Settings, Bluetooth, then tap <b>${esc(bt.name || "Teryx")}</b>.</div></div><button class="btn sm" data-a="pair-off">Stop</button></div>`
        : `<button class="btn md-wide" data-a="pair-on">${icon("bluetooth")}<span>Pair a phone</span></button>`;
      const devs = bt.devices.length ? bt.devices.map((d) => `
        <div class="md-row ${d.connected ? "on" : ""}">
          <div class="md-row-main">${icon("phone")}<div><b>${esc(d.name)}</b><div class="muted small">${d.connected ? (ph && ph.addr === d.addr ? (ph.status === "playing" ? "Connected, playing" : "Connected") : "Connected") : "Paired"}</div></div></div>
          <div class="md-row-btns">
            ${d.connected ? `<button class="btn sm" data-a="disconnect" data-addr="${esc(d.addr)}">Disconnect</button>` : `<button class="btn sm" data-a="connect" data-addr="${esc(d.addr)}">Connect</button>`}
            <button class="btn sm" data-a="forget" data-addr="${esc(d.addr)}">Forget</button>
          </div>
        </div>`).join("") : `<div class="muted" style="padding:10px 0">No phones paired yet.</div>`;
      html = `${pairing}<div class="md-list">${devs}</div>
        <div class="muted small" style="margin-top:10px">Once paired, the phone connects by itself when you get in. Song names and the buttons on the left work with most music apps.${a.backend === "sim" ? " <b>Simulator:</b> the phone is pretend. Plug it in from the sim panel, or tap Connect." : ""}</div>`;
    }
    if (body._h === html) return;
    body._h = html; body.innerHTML = html;
    $$(body, "button[data-a]").forEach((b) => (b.onclick = () => this.phoneAction(b)));
  }

  async phoneAction(b) {
    const a = b.dataset.a, addr = b.dataset.addr, h = this.hub;
    const { post } = await import("../media/mixer.js");
    try {
      if (a === "pair-on") h.audio = await post("audio/bt/pair", { on: true });
      else if (a === "pair-off") h.audio = await post("audio/bt/pair", { on: false });
      else if (a === "forget") {
        if (b.dataset.armed !== "1") { b.dataset.armed = "1"; b.classList.add("danger"); b.textContent = "Tap again"; setTimeout(() => { b.dataset.armed = ""; b.classList.remove("danger"); b.textContent = "Forget"; }, 3000); return; }
        h.audio = await post("audio/bt/forget", { addr });
      } else h.audio = await post(`audio/bt/${a}`, { addr });
      h.emit();
    } catch (e) { toast(`Bluetooth didn't do that (${e.message}).`, "bad"); }
  }

  // ---------- Music (Pi and USB) ----------
  side_music(side, build) {
    const h = this.hub;
    if (build) {
      side.innerHTML = `
        <div class="row" style="justify-content:space-between;align-items:center;margin-bottom:10px">
          <h3 style="margin:0">Music on the Pi and USB</h3>
          <div class="row" style="gap:10px">
            <button class="btn sm" id="mu-shuffle">${icon("shuffle")}<span>Shuffle</span></button>
            <button class="btn sm" id="mu-rescan">${icon("usb")}<span>Look again</span></button>
          </div>
        </div>
        <div class="md-list md-scroll" id="mu-list"></div>`;
      $(side, "#mu-shuffle").onclick = () => { h.player.shuffle = !h.player.shuffle; this.side_music(side, false); };
      $(side, "#mu-rescan").onclick = () => this.loadTracks(true);
      if (!this.tracks || this.tracks.stale) this.loadTracks(false);
    }
    $(side, "#mu-shuffle").classList.toggle("on", h.player.shuffle);
    const list = $(side, "#mu-list");
    const cur = h.player.kind === "music" && h.player.track ? h.player.track.id : null;
    let html;
    if (h.demo()) html = `<div class="muted">Music on the Pi isn't available in demo mode.</div>`;
    else if (!this.tracks) html = `<div class="muted">Looking for music…</div>`;
    else if (this.tracks.error) html = `<div class="muted">Couldn't list the music (${esc(this.tracks.error)}).</div>`;
    else if (!this.tracks.list.length) html = `<div class="muted">No music found. Put songs in the Music folder on the Pi, or plug in a USB stick and tap Look again. MP3, M4A, FLAC, OGG and WAV all work.</div>`;
    else html = this.tracks.list.map((t, i) => `
      <button class="md-row md-track ${t.id === cur ? "on" : ""}" data-i="${i}">
        <div class="md-row-main">${icon(t.id === cur && h.player.playing ? "volume" : t.source === "usb" ? "usb" : "music")}<div><b>${esc(t.title)}</b><div class="muted small">${esc([t.artist, t.album].filter(Boolean).join(" · "))}</div></div></div>
      </button>`).join("");
    if (list._h === html) return;
    list._h = html; list.innerHTML = html;
    $$(list, ".md-track").forEach((b) => (b.onclick = () => h.playTracks(this.tracks.list, +b.dataset.i)));
  }

  async loadTracks(rescan) {
    if (this.hub.demo()) return;
    try {
      const r = await fetch(`/api/media/library${rescan ? "?rescan=1" : ""}`, { cache: "no-store" });
      if (!r.ok) throw new Error(r.status);
      this.tracks = { list: (await r.json()).tracks };
      if (rescan) toast(`Found ${this.tracks.list.length} song${this.tracks.list.length === 1 ? "" : "s"}.`, "good");
    } catch (e) { this.tracks = { list: [], error: e.message }; }
    if (this.hub.source === "music" && this.ctx.current === this) this.side_music($(this.root, "#md-side"), false);
  }

  // ---------- Radio ----------
  side_radio(side, build) {
    const h = this.hub, s = this.ctx.settings;
    if (build) {
      side.innerHTML = `
        <div class="row" style="justify-content:space-between;align-items:center;margin-bottom:10px">
          <h3 style="margin:0">Internet radio</h3>
          <button class="btn sm" id="rd-add">${icon("plus")}<span>Add station</span></button>
        </div>
        <div class="md-list md-scroll" id="rd-list"></div>
        <div class="muted small" style="margin-top:10px">Needs internet: Wi-Fi, or a hotspot from your phone. For radio with no signal at all, see the FM add-on in the audio guide.</div>`;
      $(side, "#rd-add").onclick = () => this.addStation();
    }
    const list = $(side, "#rd-list"), st = s.get("media.stations") || [];
    const cur = h.player.kind === "radio" ? h.player.stationNo : -1;
    const html = st.length ? st.map((x, i) => `
      <div class="md-row ${i === cur ? "on" : ""}">
        <button class="md-row-main md-station" data-i="${i}">${icon(i === cur && h.player.playing ? "volume" : "radio")}<div><b>${esc(x.name)}</b><div class="muted small md-url">${esc(x.url)}</div></div></button>
        <div class="md-row-btns"><button class="btn sm" data-del="${i}" aria-label="Remove ${esc(x.name)}">${icon("close")}</button></div>
      </div>`).join("") : `<div class="muted">No stations yet. Tap Add station.</div>`;
    if (list._h === html) return;
    list._h = html; list.innerHTML = html;
    $$(list, ".md-station").forEach((b) => (b.onclick = () => h.playStation(st[+b.dataset.i], +b.dataset.i)));
    $$(list, "button[data-del]").forEach((b) => (b.onclick = () => {
      if (b.dataset.armed !== "1") { b.dataset.armed = "1"; b.classList.add("danger"); setTimeout(() => { b.dataset.armed = ""; b.classList.remove("danger"); }, 3000); return; }
      const i = +b.dataset.del;
      if (h.player.kind === "radio" && h.player.stationNo === i) h.player.stop();
      s.set("media.stations", st.filter((_, j) => j !== i));
      this.side_radio(side, false);
    }));
  }

  async addStation() {
    const name = await keyboard({ title: "Station name", maxLength: 32 });
    if (!name || !name.trim()) return;
    const url = await keyboard({ title: `Stream address for ${name.trim()}`, value: "https://", maxLength: 300, hint: "The station's stream link (often ends in .mp3, .aac or .m3u8)" });
    if (!url || !/^https?:\/\/\S+\.\S+/.test(url.trim())) { if (url) toast("That doesn't look like a web address.", "bad"); return; }
    const st = [...(this.ctx.settings.get("media.stations") || []), { name: name.trim(), url: url.trim() }];
    this.ctx.settings.set("media.stations", st);
    toast(`Added ${name.trim()}.`, "good");
    this.side_radio($(this.root, "#md-side"), false);
  }

  // ---------- CarPlay / Android Auto ----------
  side_carplay(side, build) {
    const cp = this.hub.carplay;
    if (build) side.innerHTML = `<h3>CarPlay and Android Auto</h3><div id="cp-body"></div>`;
    const body = $(side, "#cp-body");
    let html;
    if (cp.active) {
      html = `<div class="md-pair on"><div><b>${esc(cp.phone)} is on</b><div class="muted small">Its screen fills the Media screen. The top bar, alerts and the other screens stay where they are.</div></div></div>
        <div class="row" style="gap:10px;margin-top:12px;flex-wrap:wrap">
          <button class="btn" data-a="show">${icon("carplay")}<span>Show it</span></button>
          ${cp.state === "test" ? `<button class="btn" data-a="test-off">Stop test picture</button>` : `<button class="btn" data-a="stop">Stop</button>`}
        </div>`;
    } else {
      const [t, d] = CP_TEXT[cp.state] || CP_TEXT.off;
      const startBtn = ["off", "error", "no_adapter"].includes(cp.state) ? `<button class="btn" data-a="start">${icon("power")}<span>Start</span></button>` : "";
      const findBtn = ["no_adapter", "off", "error"].includes(cp.state) && "usb" in navigator ? `<button class="btn" data-a="find">${icon("usb")}<span>Find adapter</span></button>` : "";
      html = `<div class="md-pair"><div><b>${esc(t)}</b><div class="muted small">${esc(cp.error || d)}</div></div></div>
        <div class="row" style="gap:10px;margin-top:12px;flex-wrap:wrap">${startBtn}${findBtn}
          <button class="btn" data-a="test">${icon("grid")}<span>Test picture</span></button>
          ${cp.state === "waiting" ? `<button class="btn" data-a="stop">Stop</button>` : ""}
        </div>
        <div class="muted small" style="margin-top:14px">Needs a Carlinkit CPC200-CCPA or Autokit USB adapter (the kind made for aftermarket screens). If the phone won't connect, Bluetooth audio on the Phone tab is the backup.</div>`;
    }
    if (body._h === html) return;
    body._h = html; body.innerHTML = html;
    $$(body, "button[data-a]").forEach((b) => (b.onclick = () => {
      const a = b.dataset.a;
      if (a === "start") cp.start();
      else if (a === "find") cp.start({ pick: true });
      else if (a === "stop") cp.stop();
      else if (a === "test") { cp.startTest(); this.cpFull = true; this.render(); }
      else if (a === "test-off") cp.stopTest();
      else if (a === "show") { this.cpFull = true; this.render(); }
    }));
  }

  update() { /* media has its own timers; nothing to do on vehicle state */ }
}
