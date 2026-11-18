// Fun: camp mode, games, streaming, a light show and the easter egg list.
// Everything here only runs when the Teryx is parked (park brake on, stopped). See fun/park.js.
import { el, $, toast, stepper } from "../ui/controls.js";
import { icon } from "../ui/icons.js";
import { Sound, audioContext } from "../sound.js";
import { isParked, whyNotParked } from "../fun/park.js";
import { Campfire } from "../fun/campfire.js";
import { CAMP_DEFAULTS, campLoadW, campBudgetWh, campHoursLeft, fmtHours, restSoc } from "../fun/campcalc.js";
import { FossilDig } from "../fun/dig.js";
import { RoarDuel } from "../fun/duel.js";
import { STREAMS, openStream, closeStream } from "../fun/streams.js";
import { EGGS, isSuesDay, playRoar } from "../fun/eggs.js";
import { featureOn } from "../features.js";

const FRONT = ["light.front_1", "light.front_2", "light.front_3", "light.front_4"];
const LEVELS = { off: 0, low: 64, high: 255 };   // camp light choices (0..255)
const TIMERS = [[0, "Off"], [1, "1 h"], [2, "2 h"], [4, "4 h"], [8, "8 h"]];

export class FunScreen {
  constructor(ctx) {
    this.ctx = ctx; this.id = "fun"; this.label = "Fun"; this.icon = "fun";
    this.view = "home";
    this.camp = null;     // set while camp mode is on
    this.show_ = null;    // light show timer
  }

  cfg() { return { ...CAMP_DEFAULTS, ...(this.ctx.settings.get("fun.camp") || {}) }; }

  mount(root) {
    this.root = root;
    root.innerHTML = `
      <div class="fun">
        <div class="fun-home" id="fn-home">
          <button class="fun-tile ft-camp" data-go="camp"><i class="ft-art"></i>${icon("flame")}<b>Camp mode</b><span>Fire, lights and music. Shows how long the battery lasts.</span></button>
          <button class="fun-tile" data-go="dig"><i class="ft-art bones"></i>${icon("bone")}<b>Fossil Dig</b><span>Find the buried T. rex. One player.</span></button>
          <button class="fun-tile" data-go="duel"><i class="ft-art roar"></i>${icon("fun")}<b>Roar Duel</b><span>Fastest slap after the roar. Two players or solo.</span></button>
          <button class="fun-tile" data-go="watch">${icon("tv")}<b>Watch</b><span>YouTube, Netflix and the rest, parked only.</span></button>
          <button class="fun-tile" data-go="show">${icon("lights")}<b>Light show</b><span>The front bars dance to a beat for 30 s.</span></button>
          <button class="fun-tile eggs" data-go="eggs">${icon("egg")}<b>Easter eggs</b><span id="fn-eggcount">0 of ${EGGS.length} found</span></button>
        </div>
        <div class="fun-view" id="fn-view" hidden>
          <div class="fv-bar"><button class="btn sm" id="fn-back">${icon("back")}Back</button><span class="fv-title" id="fn-title"></span></div>
          <div class="fv-body" id="fn-body"></div>
        </div>
        <div class="fun-lock" id="fn-lock" hidden>
          ${icon("lock")}
          <b>Park up to play</b>
          <span id="fn-why">Put the park brake on</span>
          <small>Games, video and the easter eggs only work with the park brake on and the Teryx stopped.</small>
        </div>
      </div>`;
    root.querySelectorAll("[data-go]").forEach((b) => (b.onclick = () => this.go(b.dataset.go)));
    $(root, "#fn-back").onclick = () => this.go("home");
    if (isSuesDay()) $(root, "#fn-eggcount").textContent = "Happy find-day, Sue!";
    this.paintEggs();
    this.ctx.settings.subscribe((p) => { if (p === "fun.eggs") this.paintEggs(); });
  }

  paintEggs() {
    const n = (this.ctx.settings.get("fun.eggs") || []).length;
    const e = this.root && $(this.root, "#fn-eggcount");
    if (e && !isSuesDay()) e.textContent = `${n} of ${EGGS.length} found`;
  }

  go(view) {
    if (view !== "home" && !isParked(this.ctx.store)) { toast(`${whyNotParked(this.ctx.store)} first.`); return; }
    if (this.game) { this.game.stop(); this.game = null; }
    this.view = view;
    const home = $(this.root, "#fn-home"), v = $(this.root, "#fn-view"), body = $(this.root, "#fn-body");
    home.hidden = view !== "home"; v.hidden = view === "home";
    body.innerHTML = "";
    if (view === "camp") { this.go("home"); this.startCamp(); return; }
    if (view === "show") { this.go("home"); this.lightShow(); return; }
    const titles = { dig: "Fossil Dig", duel: "Roar Duel", watch: "Watch", eggs: "Easter eggs" };
    $(this.root, "#fn-title").textContent = titles[view] || "";
    if (view === "dig") {
      this.game = new FossilDig({ best: this.ctx.settings.get("fun.digBest") || 0, onBest: (s) => this.ctx.settings.set("fun.digBest", s) });
      body.appendChild(this.game.root);
    } else if (view === "duel") {
      this.game = new RoarDuel({ bestMs: this.ctx.settings.get("fun.duelBestMs") || 0, onBest: (ms) => this.ctx.settings.set("fun.duelBestMs", ms) });
      body.appendChild(this.game.root);
    } else if (view === "watch") this.watchView(body);
    else if (view === "eggs") this.eggsView(body);
  }

  // ---------- streaming ----------
  watchView(body) {
    const demo = !!this.ctx.store.get("link.demo");
    const w = el(`<div class="watch">
        <div class="watch-grid"></div>
        <div class="panel watch-note">
          <h3>Good to know</h3>
          <p>Video only plays with the park brake on. It shuts the moment the brake comes off or the Teryx moves.</p>
          <p>YouTube works in any browser. The others need Widevine (the copy protection most paid services use). On a Pi 5 that comes with Google Chrome for Arm64, and quality tops out around 720p to 1080p. Each one gets tested on the bench before we call it working.</p>
          <p>Streaming over a phone hotspot eats data: Netflix says up to 3 GB an hour in HD, 1 GB in SD.</p>
          <button class="btn sm" id="wt-close">${icon("close")}Close the video window</button>
        </div>
      </div>`);
    const grid = w.querySelector(".watch-grid");
    STREAMS.forEach((s) => {
      const b = el(`<button class="watch-tile"><b>${s.name}</b><span>${s.drm ? "Needs Widevine" : "No DRM needed"}</span></button>`);
      b.onclick = async () => {
        if (!isParked(this.ctx.store)) { toast(`${whyNotParked(this.ctx.store)} first.`); return; }
        const r = await openStream(s, demo);
        if (!r.ok) toast(r.why, "bad");
        else if (r.window) { toast(`Opening ${s.name}. Tap Back to dash at the top to come back.`); this.streamChip(s.name); }
        else toast(`${s.name} opened in a new tab.`);
      };
      grid.appendChild(b);
    });
    w.querySelector("#wt-close").onclick = () => { closeStream(); this.streamChip(null); };
    body.appendChild(w);
  }

  /** "Back to dash" chip in the top bar while the video window is open. Watches the server so it goes when the window does. */
  streamChip(name) {
    const chip = document.getElementById("tb-stream");
    clearInterval(this._streamPoll);
    if (!name) { chip.hidden = true; return; }
    chip.innerHTML = `${icon("close")}<span>${name}: back to dash</span>`;
    chip.hidden = false;
    chip.onclick = () => { closeStream(); this.streamChip(null); };
    this._streamPoll = setInterval(async () => {
      try { const j = await (await fetch("/api/fun", { cache: "no-store" })).json(); if (!j.open) this.streamChip(null); } catch {}
    }, 2000);
  }

  eggsView(body) {
    const found = this.ctx.settings.get("fun.eggs") || [];
    const w = el(`<div class="eggs-list"></div>`);
    EGGS.forEach((e) => {
      const got = found.includes(e.id);
      w.appendChild(el(`<div class="egg-row ${got ? "got" : ""}">${icon(got ? "egg" : "lock")}<div><b>${got ? e.name : "Not found yet"}</b><span>${e.hint}</span></div></div>`));
    });
    body.appendChild(w);
  }

  // ---------- light show ----------
  lightShow() {
    if (this.show_) return;
    if (!featureOn(this.ctx.settings, "lights")) { toast("Lights aren't switched on in Settings > Features yet."); return; }
    const st = this.ctx.store, link = this.ctx.link;
    const before = Object.fromEntries(FRONT.map((id) => [id, st.get(`req.${id}`) ?? st.get(id) ?? 0]));
    const a = audioContext();
    // 8 bars of 4 beats at 120 bpm: chase, pairs, all, sparkle, then a roar and everything off
    const pats = [
      (b) => FRONT.map((_, i) => (i === b % 4 ? 255 : 0)),
      (b) => FRONT.map((_, i) => (i === 3 - (b % 4) ? 255 : 0)),
      (b) => FRONT.map((_, i) => ((i < 2) === (b % 2 === 0) ? 255 : 0)),
      (b) => FRONT.map((_, i) => ((i === 0 || i === 3) === (b % 2 === 0) ? 255 : 0)),
      (b) => FRONT.map(() => (b % 2 === 0 ? 255 : 40)),
      (b) => FRONT.map(() => (Math.random() < 0.5 ? 255 : 0)),
      (b) => FRONT.map((_, i) => (i <= b % 4 ? 255 : 0)),
      (b) => FRONT.map(() => (b % 4 === 3 ? 0 : 255)),
    ];
    let beat = 0;
    const tick = () => {
      if (!isParked(st)) { stop(false); return; }
      if (beat >= 60) { stop(true); return; }
      const lv = pats[Math.floor(beat / 8) % pats.length](beat);
      FRONT.forEach((id, i) => link.request(id, lv[i]));
      if (a && Sound.enabled) {   // kick on every beat, a hat on the off beat
        const t = a.currentTime + 0.01, o = a.createOscillator(), g = a.createGain();
        o.frequency.setValueAtTime(140, t); o.frequency.exponentialRampToValueAtTime(40, t + 0.15);
        g.gain.setValueAtTime(0.6, t); g.gain.exponentialRampToValueAtTime(0.001, t + 0.18);
        o.connect(g); g.connect(a.destination); o.start(t); o.stop(t + 0.2);
      }
      beat++;
    };
    const stop = (finale) => {
      clearInterval(this.show_); this.show_ = null;
      if (finale) { FRONT.forEach((id) => link.request(id, 255)); playRoar(); }
      setTimeout(() => FRONT.forEach((id) => link.request(id, before[id])), finale ? 2600 : 0);
      if (!finale) toast("Light show stopped: not parked any more.");
    };
    toast("Light show! Step back and look at the front.");
    this.show_ = setInterval(tick, 500);
    tick();
  }

  // ---------- camp mode ----------
  startCamp() {
    if (this.camp) return;
    const st = this.ctx.store, c = this.cfg();
    const before = Object.fromEntries([...FRONT, "light.interior"].map((id) => [id, st.get(`req.${id}`) ?? st.get(id) ?? 0]));
    this.camp = {
      before, at: Date.now(), last: Date.now(), usedWh: 0, lowSince: 0, screen: true, dim: 0,
      startSoc: restSoc(st.get("an.aux_12v"), c.auxChem),
      interior: "low", bars: "off", fire: true, timerH: c.timerH || 0, ui: true,
    };
    const o = el(`<div class="camp" id="camp">
        <canvas class="camp-fire" width="640" height="400"></canvas>
        <div class="camp-dim"></div>
        <div class="camp-ui">
          <div class="camp-top">
            <div class="camp-title">${icon("flame")}<b>Camp mode</b></div>
            <div class="camp-stats">
              <div><span>Battery left for</span><b id="cp-hours">--</b></div>
              <div><span>Drawing</span><b id="cp-watts">--</b></div>
              <div><span id="cp-srcl">12V battery</span><b id="cp-src">--</b></div>
              <div><span>Timer</span><b id="cp-timer">Off</b></div>
            </div>
            <button class="btn danger" id="cp-exit">${icon("close")}End</button>
          </div>
          <div class="camp-note" id="cp-note"></div>
          <div class="camp-ctl">
            <div class="cc"><span>Cab light</span><div class="seg" id="cp-int"><button data-v="off">Off</button><button data-v="low">Low</button><button data-v="high">Full</button></div></div>
            <div class="cc"><span>Front bars</span><div class="seg" id="cp-bars"><button data-v="off">Off</button><button data-v="low">Low</button><button data-v="high">Full</button></div></div>
            <div class="cc"><span>Fire sound</span><div class="seg" id="cp-snd"><button data-v="on">On</button><button data-v="off">Off</button></div></div>
            <div class="cc"><span>Auto off</span><div class="seg" id="cp-tmr">${TIMERS.map(([h, l]) => `<button data-v="${h}">${l}</button>`).join("")}</div></div>
            <div class="cc"><span>Screen</span><div class="seg" id="cp-scr"><button data-v="0">Bright</button><button data-v="1">Dim</button><button data-v="off">Off</button></div></div>
            <button class="btn sm" id="cp-setup">${icon("settings")}Battery setup</button>
          </div>
        </div>
        <div class="camp-setup" id="cp-setupbox" hidden></div>
      </div>`);
    document.getElementById("app").appendChild(o);
    this.campEl = o;
    const q = (s) => o.querySelector(s);
    this.fire = new Campfire(q(".camp-fire"));
    this.fire.start();
    const seg = (sel, key, fn) => q(sel).querySelectorAll("button").forEach((b) => (b.onclick = (e) => { e.stopPropagation(); fn(b.dataset.v); this.paintCamp(); }));
    seg("#cp-int", "interior", (v) => { this.camp.interior = v; this.campLights(); });
    seg("#cp-bars", "bars", (v) => { this.camp.bars = v; this.campLights(); });
    seg("#cp-snd", "fire", (v) => { this.camp.fire = v === "on"; this.fire.sound(this.camp.fire && Sound.enabled, 0.5); });
    seg("#cp-tmr", "timer", (v) => { this.camp.timerH = +v; this.camp.timerFrom = Date.now(); });
    seg("#cp-scr", "screen", (v) => {
      if (v === "off") { this.screenPower(false); return; }
      this.camp.dim = +v;
      o.classList.toggle("dim", this.camp.dim === 1);
    });
    q("#cp-exit").onclick = (e) => { e.stopPropagation(); this.endCamp("user"); };
    q("#cp-setup").onclick = (e) => { e.stopPropagation(); this.campSetup(); };
    // Tap the fire to hide or show the buttons
    q(".camp-fire").onclick = () => { this.camp.ui = !this.camp.ui; o.classList.toggle("bare", !this.camp.ui); };
    this.camp.timerFrom = Date.now();
    this.campLights();
    this.fire.sound(this.camp.fire && Sound.enabled, 0.5);
    this.campTick = setInterval(() => this.tickCamp(), 1000);
    this.paintCamp();
    this.tickCamp();
  }

  campLights() {
    const link = this.ctx.link, c = this.camp, s = this.ctx.settings;
    if (featureOn(s, "lights")) {
      link.request("light.interior", LEVELS[c.interior]);
      FRONT.forEach((id) => link.request(id, LEVELS[c.bars] && !s.light(id).dimmable ? 255 : LEVELS[c.bars]));
    }
  }

  async screenPower(on) {
    const c = this.camp; if (!c) return;
    c.screen = on;
    this.campEl.classList.toggle("screen-off", !on);
    try { await fetch("/api/fun/screen", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ on }) }); } catch {}
    if (!on) {
      toast("Screen off. Touch it to wake.");
      // Any touch wakes it (the touch panel keeps working with the picture off)
      setTimeout(() => document.addEventListener("pointerdown", () => this.screenPower(true), { once: true, capture: true }), 400);
    }
  }

  campSetup() {
    const box = this.campEl.querySelector("#cp-setupbox");
    if (!box.hidden) { box.hidden = true; return; }
    const s = this.ctx.settings, c = this.cfg();
    const put = (k, v) => { s.set(`fun.camp.${k}`, v); this.tickCamp(); };
    box.innerHTML = `<h3>Camp mode battery setup</h3><p class="muted small">These start as guesses. Put real numbers in once the battery and loads are measured on the bench.</p>`;
    const row = (label, ctl) => { const r = el(`<div class="cs-row"><span>${label}</span></div>`); r.appendChild(ctl); box.appendChild(r); };
    const segOf = (opts, val, fn) => {
      const g = el(`<div class="seg">${opts.map(([v, l]) => `<button data-v="${v}" class="${v === val ? "on" : ""}">${l}</button>`).join("")}</div>`);
      g.querySelectorAll("button").forEach((b) => (b.onclick = () => { g.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b)); fn(b.dataset.v); }));
      return g;
    };
    row("Power from", segOf([["aux", "12V battery"], ["pack", "EV pack"]], c.source, (v) => put("source", v)));
    row("12V battery type", segOf([["lead", "Lead / AGM"], ["lithium", "Lithium"]], c.auxChem, (v) => put("auxChem", v)));
    const st = (k, step, min, max, unit) => stepper(c[k], { step, min, max, fmt: (v) => `${v}${unit}`, onChange: (v) => put(k, v) }).root;
    row("12V battery size", st("auxAh", 5, 5, 300, " Ah"));
    row("Keep in the EV pack", st("packFloorPct", 5, 10, 90, " %"));
    row("Each front bar at full", st("barW", 5, 5, 300, " W"));
    row("Cab light at full", st("interiorW", 1, 1, 100, " W"));
    row("Screen", st("screenW", 1, 1, 60, " W"));
    row("Pi", st("piW", 1, 2, 30, " W"));
    row("Amp", st("ampW", 1, 0, 100, " W"));
    const done = el(`<button class="btn sm">Done</button>`); done.onclick = () => (box.hidden = true); box.appendChild(done);
    box.hidden = false;
  }

  campLoad() {
    const st = this.ctx.store, c = this.camp;
    const lights = Object.fromEntries([...FRONT, "light.interior"].map((id) => [id, st.get(id) ?? 0]));
    const audio = c.fire || !!this.ctx.media.nowPlaying().playing;
    return campLoadW(this.cfg(), { lights, audio, screen: c.screen ? 1 : 0 });
  }

  tickCamp() {
    const c = this.camp; if (!c) return;
    const st = this.ctx.store, cfg = this.cfg(), now = Date.now();
    const w = this.campLoad();
    c.usedWh += (w * (now - c.last)) / 3600000; c.last = now;
    c.w = w;
    c.budget = campBudgetWh(cfg, { startSoc: c.startSoc ?? 100, usedWh: c.usedWh, packSoc: st.get("mc.soc"), packKwh: this.ctx.settings.get("packKwh") || 7.5 });
    c.hours = campHoursLeft(c.budget, w);
    // Low 12V: lights and sound off, keep the battery for the winch and the next start
    const v12 = st.get("an.aux_12v");
    if (v12 != null && v12 < cfg.auxCutoffV) {
      c.lowSince = c.lowSince || now;
      if (now - c.lowSince > 15000 && !c.lowDone) {
        c.lowDone = true; c.interior = "off"; c.bars = "off"; c.fire = false;
        this.campLights(); this.fire.sound(false);
        Sound.play("warn"); toast(`12V battery low (${v12.toFixed(1)} V). Camp lights and sound off to save it.`, "bad");
      }
    } else c.lowSince = 0;
    // Timer
    if (c.timerH && now - c.timerFrom > c.timerH * 3600000) { this.endCamp("timer"); return; }
    this.paintCamp();
  }

  paintCamp() {
    const c = this.camp; if (!c || !this.campEl) return;
    const q = (s) => this.campEl.querySelector(s), cfg = this.cfg(), st = this.ctx.store;
    const pick = (sel, v) => q(sel).querySelectorAll("button").forEach((b) => b.classList.toggle("on", b.dataset.v === String(v)));
    pick("#cp-int", c.interior); pick("#cp-bars", c.bars); pick("#cp-snd", c.fire ? "on" : "off"); pick("#cp-tmr", c.timerH); pick("#cp-scr", c.screen ? c.dim : "off");
    q("#cp-hours").textContent = fmtHours(c.hours);
    q("#cp-watts").textContent = c.w == null ? "--" : `${Math.round(c.w)} W`;
    if (cfg.source === "pack") { q("#cp-srcl").textContent = "EV pack"; q("#cp-src").textContent = `${Math.round(st.get("mc.soc") ?? 0)}%`; }
    else { const v = st.get("an.aux_12v"); q("#cp-srcl").textContent = "12V battery"; q("#cp-src").textContent = v == null ? "--" : `${v.toFixed(1)} V`; }
    if (c.timerH) { const left = c.timerH * 3600000 - (Date.now() - c.timerFrom); q("#cp-timer").textContent = fmtHours(Math.max(0, left) / 3600000); }
    else q("#cp-timer").textContent = "Off";
    const notes = [];
    if (cfg.source === "aux") notes.push(`Based on a ${cfg.auxAh} Ah ${cfg.auxChem === "lithium" ? "lithium" : "lead"} battery, only using the safe ${cfg.auxChem === "lithium" ? "80" : "50"}%. Check the size in Battery setup.`);
    else notes.push(`Keeps ${cfg.packFloorPct}% in the pack for the drive out. Needs the key on so the DC-DC runs: check that on the bench.`);
    if (c.lowDone) notes.unshift("12V battery got low, so camp lights and sound were switched off.");
    if (!featureOn(this.ctx.settings, "lights")) notes.push("Lights aren't switched on in Settings > Features, so camp mode won't touch them.");
    q("#cp-note").textContent = notes.join(" ");
  }

  endCamp(why) {
    const c = this.camp; if (!c) return;
    clearInterval(this.campTick);
    this.fire.stop();
    if (!c.screen) this.screenPower(true);
    if (why === "moving") {
      // Driving off: leave the lights as they are. Switching lights off on the move isn't safe.
      toast("Camp mode ended: the Teryx is moving. Lights left as they are.");
    } else if (featureOn(this.ctx.settings, "lights")) {
      // Put the lights back how they were before camp mode
      Object.entries(c.before).forEach(([id, v]) => this.ctx.link.request(id, why === "timer" ? 0 : v));
      if (why === "timer") toast("Camp mode timer finished. Lights off.");
    }
    this.campEl.remove(); this.campEl = null; this.camp = null;
  }

  // ---------- each frame ----------
  hide() { if (this.game) this.game.stop(); }

  update(st) {
    const parked = isParked(st);
    const lock = $(this.root, "#fn-lock");
    lock.hidden = parked;
    if (!parked) {
      $(this.root, "#fn-why").textContent = whyNotParked(st);
      if (this.game) { this.game.stop(); }
    }
    this.root.querySelector(".fun").classList.toggle("locked", !parked);
  }

  /** Called on every state change, whichever screen is showing: camp mode and the light show run in the background. */
  background(st) {
    if (this.camp && !isParked(st)) this.endCamp("moving");
    if (this.game && !isParked(st)) { this.game.stop(); if (this.ctx.current !== this) this.go("home"); }
  }
}
