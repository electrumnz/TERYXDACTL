// Cameras: rear, front, trailer, cabin, and ALL (the combined view). Pick with the buttons along the top.
//
// Where the pictures come from (docs/cameras.md, no USB):
//  - front: Pi Camera Module 3 on the first ribbon port ("csi0"),
//  - rear, trailer (and cabin later): analogue cameras on the video board on the second ribbon
//    port ("adv:N"). That board has one decoder, so only ONE of its cameras can be live at a time.
// Both come through the dash server (/api/camera.mjpg?cam=<id>). A browser camera (getUserMedia)
// still works on the bench.
//
// ALL shows every fitted camera that's useful while driving at once:
//  - no trailer: front and rear side by side,
//  - trailer on: front down the left, trailer and rear on the right. Rear and trailer share the
//    video board, so one is live and the other shows its last picture with "PAUSED". Tap the
//    paused one to swap. With a trailer on, the trailer camera is the live one to start with.
// "Trailer on" means its camera is giving a picture (the server checks the video board, see
// trailercam.py) or, until that's known, the trailer plug's reed switch (in.trailer).
// Settings > Cameras > Trailer detect picks plug only, picture only, or either.
//
// Lights on each picture: front bars on the front, rear floods on the rear, trailer bar (and the
// rear floods) on the trailer, cab light on the cabin. In reverse the rear floods button grows,
// sized for a gloved hand while you're looking over your shoulder. A tap only lasts for this
// reverse: once out of reverse the rear lights go back to what the Lights screen says.
// Pops up on its own in reverse (Settings > Cameras): the trailer camera if a trailer is on,
// otherwise the rear one, or the combined view if that's picked for reverse.
import { $, el, toast } from "../ui/controls.js";
import { icon } from "../ui/icons.js";

export const CAMS = [
  { id: "rear", name: "Rear" },
  { id: "front", name: "Front" },
  { id: "trailer", name: "Trailer" },
  { id: "cabin", name: "Cabin" },
];
// Cameras that go in the combined view, in the order they're laid out.
const COMBO = ["front", "trailer", "rear"];
const FRONT_BARS = ["light.front_1", "light.front_2", "light.front_3", "light.front_4"];

/** Is a trailer with its camera plugged in? Picture check from the server, and/or the reed switch. */
export function trailerOn(settings, store) {
  const mode = settings.get("camera.trailerDetect") || "either";
  const plug = !!store.get("in.trailer"), sig = store.get("cam.trailer_signal");   // true / false / null
  if (mode === "plug") return plug;
  if (mode === "picture") return sig === true;
  // Either: a picture says yes. With no check yet, go by the plug. Plug in but no picture means
  // a trailer with no camera (or its round plug isn't in).
  return sig === true || (plug && sig !== false);
}

/** "ok", "off" (not fitted), "notrailer" or "nopicture" (trailer plugged in, no camera picture). */
export function camState(settings, store, id) {
  if (id === "combo") return comboCams(settings, store).length >= 2 ? "ok" : "few";
  const c = settings.get(`camera.cams.${id}`) || {};
  if (!c.fitted) return "off";
  if (id === "trailer" && !trailerOn(settings, store)) {
    const sig = store.get("cam.trailer_signal");
    return store.get("in.trailer") && sig === false ? "nopicture" : "notrailer";
  }
  return "ok";
}

/** The cameras in the combined view right now. */
export function comboCams(settings, store) { return COMBO.filter((id) => camState(settings, store, id) === "ok"); }

/** Does this camera come off the video board (shared decoder)? */
export function onBoard(settings, id) { return /^adv:\d$/.test((settings.get(`camera.cams.${id}`) || {}).v4l2Device || ""); }

/**
 * What to show: a list of {cam, live}. Only one video board camera is live; the rest show
 * their last picture. `boardPick` is the one the driver tapped (or reverse picked).
 */
export function layoutFor(settings, store, view, boardPick) {
  if (view !== "combo") return [{ cam: view, live: true }];
  const list = comboCams(settings, store);
  const board = list.filter((id) => onBoard(settings, id));
  const live = board.includes(boardPick) ? boardPick : board.includes("trailer") ? "trailer" : board[0];
  return list.map((cam) => ({ cam, live: !onBoard(settings, cam) || cam === live }));
}

const TAG = { off: "NOT FITTED", notrailer: "NO TRAILER", nopicture: "NO PICTURE", few: "NEEDS 2" };
const PICK = [{ id: "combo", name: "All" }, ...CAMS];

/** One picture on the screen, with its own lights. */
class Pane {
  constructor(screen, cam) {
    this.s = screen; this.cam = cam; this.live = false; this.stream = null; this.run = 0;
    this.root = el(`
      <div class="cam-pane" data-cam="${cam}">
        <video autoplay muted playsinline hidden></video>
        <img alt="" hidden>
        <canvas class="feed test" width="1176" height="740" hidden></canvas>
        <canvas class="feed still" hidden></canvas>
        <svg class="overlay" viewBox="0 0 1176 740" preserveAspectRatio="none"></svg>
        <div class="cam-msg"></div>
        <div class="pane-paused" hidden><b>PAUSED</b><span>Tap to show live</span></div>
        <div class="pane-name"></div>
        <div class="pane-lights"></div>
      </div>`);
    this.video = $(this.root, "video"); this.img = $(this.root, "img");
    this.test = $(this.root, "canvas.test"); this.still = $(this.root, "canvas.still");
    this.guides = $(this.root, "svg"); this.msg = $(this.root, ".cam-msg");
    this.root.addEventListener("click", (e) => {
      if (!this.live && !e.target.closest("button")) this.s.showLive(this.cam);
    });
    this.lights = $(this.root, ".pane-lights");
    this.buildLights();
  }

  get ctx() { return this.s.ctx; }
  get cfg() { return this.ctx.settings.get(`camera.cams.${this.cam}`) || {}; }

  buildLights() {
    const L = this.lights;
    if (this.cam === "front") {
      const row = el(`<div class="cam-bars"><span class="cb-name">BARS</span></div>`);
      FRONT_BARS.forEach((id, i) => {
        const b = el(`<button class="cam-light sm" data-light="${id}" aria-label="Front bar ${i + 1}">${i + 1}</button>`);
        b.onclick = () => this.s.toggleLevel(id);
        row.appendChild(b);
      });
      const all = el(`<button class="cam-light sm all" data-light="bars" aria-label="All front bars">ALL</button>`);
      all.onclick = () => this.s.toggleBars();
      row.appendChild(all);
      L.appendChild(row);
    }
    if (this.cam === "rear" || this.cam === "trailer") {
      const b = el(`<button class="cam-rear" data-light="light.rear" aria-label="Rear lights on or off">
          ${icon("lights")}<span class="cr-text"><span class="cr-name">REAR LIGHTS</span><span class="cr-state">OFF</span></span></button>`);
      b.onclick = () => this.s.toggleRear();
      L.appendChild(b);
    }
    if (this.cam === "trailer") {
      const b = el(`<button class="cam-rear" data-light="light.trailer_bar" aria-label="Trailer light bar on or off">
          ${icon("lights")}<span class="cr-text"><span class="cr-name">TRAILER BAR</span><span class="cr-state">OFF</span></span></button>`);
      b.onclick = () => this.s.toggleLevel("light.trailer_bar");
      L.appendChild(b);
    }
    if (this.cam === "cabin") {
      const b = el(`<button class="cam-rear" data-light="light.interior" aria-label="Cab light on or off">
          ${icon("lights")}<span class="cr-text"><span class="cr-name">CAB LIGHT</span><span class="cr-state">OFF</span></span></button>`);
      b.onclick = () => this.s.toggleLevel("light.interior");
      L.appendChild(b);
    }
  }

  paint() {
    this.root.querySelector(".pane-name").textContent = this.s.camName(this.cam).toUpperCase();
    $(this.root, ".pane-paused").hidden = this.live;
    this.root.classList.toggle("paused", !this.live);
    // Mirror and guide lines are per camera: a front camera usually wants neither.
    const m = !!this.cfg.mirror;
    [this.video, this.img, this.test, this.still].forEach((x) => (x.style.transform = m ? "scaleX(-1)" : ""));
    this.guides.style.display = this.cfg.guides ? "" : "none";
    this.guides.innerHTML = guideLines(this.ctx.settings.get("camera.guideOffset") || 0);
  }

  /** Keep the last picture on screen (the board is going to another camera). */
  freeze() {
    const src = !this.test.hidden ? this.test : !this.img.hidden ? this.img : !this.video.hidden ? this.video : null;
    if (!src) return;
    const w = src.naturalWidth || src.videoWidth || src.width, h = src.naturalHeight || src.videoHeight || src.height;
    if (!w || !h) return;
    this.still.width = w; this.still.height = h;
    try { this.still.getContext("2d").drawImage(src, 0, 0, w, h); this.still.hidden = false; } catch {}
  }

  stop() {
    this.run++;
    if (this.stream) { this.stream.getTracks().forEach((t) => t.stop()); this.stream = null; }
    this.img.onload = this.img.onerror = null;
    this.img.removeAttribute("src");
    this.fake = false;
    this.video.hidden = this.img.hidden = this.test.hidden = true;
  }

  setLive(live) {
    if (live === this.live && (this.started || !live)) return;
    if (!live && this.live) this.freeze();
    this.live = live;
    this.paint();
    if (live) this.start(); else { this.stop(); if (this.still.hidden) { this.msg.hidden = false; this.msg.textContent = ""; } }
  }

  async start() {
    this.stop();
    this.started = true;
    const run = this.run, set = this.ctx.settings, cam = this.cfg, st = this.ctx.store;
    const src = set.get("camera.source"), name = this.s.camName(this.cam).toLowerCase();
    this.msg.hidden = false; this.msg.textContent = `Starting ${name} camera…`;
    // Demo mode, or the bench simulator with no camera plugged in: show a fake view instead.
    const fake = () => st.get("link.demo") || st.get("sim.scenario") != null;
    const showFake = () => { this.fake = true; this.test.hidden = false; this.still.hidden = true; this.msg.hidden = true; this.s.setSrc(st.get("link.demo") ? "DEMO" : "SIM"); this.s.runFake(); };
    if (st.get("link.demo")) { showFake(); return; }
    // A Raspberry Pi ribbon camera ("csi0") or the video board ("adv:N") only comes through the server stream.
    const csi = /^(csi\d|adv:\d)$/.test(cam.v4l2Device || "");
    if (!csi && (src === "usb" || src === "auto")) {
      try {
        const id = cam.deviceId, size = { width: { ideal: 1280 }, height: { ideal: 720 } };
        // With more than one camera plugged in, "first camera found" is only safe for the rear one.
        if (!id && this.cam !== "rear") throw Object.assign(new Error("pick"), { name: "NoDevicePicked" });
        const stream = await navigator.mediaDevices.getUserMedia({ video: id ? { deviceId: { exact: id }, ...size } : size, audio: false });
        if (run !== this.run) { stream.getTracks().forEach((t) => t.stop()); return; }
        this.stream = stream;
        this.video.srcObject = stream; this.video.hidden = false; this.still.hidden = true; this.msg.hidden = true;
        this.s.setSrc("USB");
        return;
      } catch (e) {
        if (run !== this.run) return;
        if (fake()) { showFake(); return; }
        if (src === "usb") {
          this.msg.textContent = e.name === "NoDevicePicked" ? `Pick which device is the ${name} camera in Settings > Cameras.`
            : `Can't open the camera (${e.name}). Pick another device in Settings > Cameras.`;
          return;
        }
      }
    }
    // Server stream
    this.img.onload = () => { if (run === this.run) { this.msg.hidden = true; this.still.hidden = true; } };
    this.img.onerror = () => {
      if (run !== this.run) return;
      if (fake()) { this.img.hidden = true; showFake(); return; }
      this.msg.hidden = false; this.still.hidden = true;
      this.msg.textContent = this.cam === "front" ? "No front camera picture. Check its ribbon cable."
        : `No ${name} camera picture. Check its lead into the video board.`;
    };
    this.img.src = `${set.get("camera.streamUrl")}?cam=${this.cam}&t=${Date.now()}`;
    this.img.hidden = false;
    this.s.setSrc("STREAM");
  }

  /** Paint the lights buttons from the store. */
  update(st) {
    this.lights.querySelectorAll("[data-light]").forEach((b) => {
      const id = b.dataset.light;
      const on = id === "bars" ? FRONT_BARS.some((k) => this.s.level(st, k) > 0)
        : id === "light.rear" ? (st.pending("light.rear") ? this.s.rearMine === "on" : !!st.get("light.rear"))
          : this.s.level(st, id) > 0;
      b.classList.toggle("on", on);
      const state = b.querySelector(".cr-state"); if (state) state.textContent = on ? "ON" : "OFF";
    });
  }
}

function guideLines(offset) {
  // Fixed parking guides: red about 0.5 m, amber 1 m, green 2 m. Nudge sideways in Settings.
  const cx = 588 + offset;
  const lines = [[700, 330, "#ff4b4b"], [560, 270, "#ffad1f"], [430, 215, "#36d67e"]];
  let s = `<path d="M${cx - 420} 740 L${cx - 200} 400 M${cx + 420} 740 L${cx + 200} 400" stroke="#ffad1f" stroke-width="6" fill="none" stroke-linecap="round" opacity=".85"/>`;
  lines.forEach(([y, hw, col]) => (s += `<path d="M${cx - hw} ${y} h80 M${cx + hw} ${y} h-80" stroke="${col}" stroke-width="8" stroke-linecap="round"/>`));
  return s;
}

export class CameraScreen {
  constructor(ctx) {
    this.ctx = ctx; this.id = "camera"; this.label = "Cameras"; this.icon = "camera";
    this.view = null; this.panes = new Map(); this.boardPick = null; this.local = {};
  }

  mount(root) {
    root.style.padding = "0";
    root.innerHTML = `
      <div class="cam">
        <div class="cam-grid n1" id="c-grid-panes"></div>
        <div class="cam-hud"><span id="c-rev" class="rev" hidden>R</span><span id="c-spd" class="num">0 km/h</span><span id="c-src"></span></div>
        <div class="cam-pick" id="c-pick">
          ${PICK.map((c) => `<button class="cp-btn" data-cam="${c.id}"><span class="cp-name"></span><i class="cp-tag"></i></button>`).join("")}
        </div>
        <div class="cam-tools">
          <button class="btn" id="c-mirror" aria-label="Mirror">${icon("mirror")}</button>
          <button class="btn" id="c-grid" aria-label="Guide lines">${icon("grid")}</button>
        </div>
        <button class="btn cam-demo" id="c-demo" hidden></button>
      </div>`;
    this.root = root;
    this.grid = $(root, "#c-grid-panes");
    const set = this.ctx.settings;
    $(root, "#c-mirror").onclick = () => { const k = `camera.cams.${this.view}.mirror`; set.set(k, !set.get(k)); this.paintAll(); };
    $(root, "#c-grid").onclick = () => { const k = `camera.cams.${this.view}.guides`; set.set(k, !set.get(k)); this.paintAll(); };
    $(root, "#c-demo").onclick = () => this.demoTrailer();
    root.querySelectorAll(".cp-btn").forEach((b) => (b.onclick = () => this.pick(b.dataset.cam, true)));
    set.subscribe((p) => {
      if (!p.startsWith("camera.")) return;
      // Only restart pictures if something about how they're opened changed.
      if (/^camera\.(source|streamUrl|trailerDetect|cams\.[a-z]+\.(deviceId|fitted|v4l2Device))$/.test(p) || p === "camera.cams") {
        if (this.started) this.layout(true);
      } else this.paintAll();
      this.paintPick();
    });
    this.view = this.firstOk(set.get("camera.current"));
    this.layout();
    this.paintPick();
    this.pollTrailer();
  }

  // Pictures only run while the screen is showing: a video board camera on screen takes the board
  // off the dashcam (one decoder), so it must let go when you leave.
  show() {
    this.hadTrailer = camState(this.ctx.settings, this.ctx.store, "trailer");
    this.view = this.firstOk(this.view);
    this.started = true;
    this.layout(true);
    this.paintPick();
  }

  // ---- trailer camera picture check (server) ---------------------------------------------------
  pollTrailer() {
    const tick = async () => {
      const st = this.ctx.store;
      if (st.get("link.demo") || !st.get("link.online")) return;
      try {
        const r = await fetch("/api/camera/status", { cache: "no-store" });
        if (!r.ok) return;
        const j = await r.json(), t = j.trailer || {};
        if (st.get("cam.trailer_signal") !== t.signal) st.set({ "cam.trailer_signal": t.signal ?? null });
      } catch {}
    };
    clearInterval(this._poll);
    this._poll = setInterval(tick, 3000);
    tick();
  }

  // Demo only (the online sim): plug a trailer in and out to try the combined view.
  demoTrailer() {
    const d = this.ctx.link.demo; if (!d) return;
    const s = d.s, plug = !!s["in.trailer"], sig = s["cam.trailer_signal"];
    // off -> trailer with camera -> trailer with no camera -> off
    if (!plug) {
      s["in.trailer"] = true; s["cam.trailer_signal"] = true;
      if (!this.ctx.settings.get("camera.cams.trailer.fitted")) this.ctx.settings.set("camera.cams.trailer.fitted", true);
    }
    else if (sig !== false) { s["cam.trailer_signal"] = false; }
    else { s["in.trailer"] = false; s["cam.trailer_signal"] = null; }
    this.ctx.store.set({ "in.trailer": s["in.trailer"], "cam.trailer_signal": s["cam.trailer_signal"] });
  }

  paintDemo(st) {
    const b = $(this.root, "#c-demo");
    b.hidden = !st.get("link.demo");
    if (b.hidden) return;
    const plug = !!st.get("in.trailer"), sig = st.get("cam.trailer_signal");
    b.textContent = !plug ? "DEMO: PLUG IN TRAILER" : sig === false ? "DEMO: UNPLUG TRAILER" : "DEMO: PULL TRAILER CAM PLUG";
  }

  // ---- picking ---------------------------------------------------------------------------------
  /** The view to show: the one asked for if it's working, else the first that is. */
  firstOk(want) {
    const { settings: s, store: st } = this.ctx;
    if (want && camState(s, st, want) === "ok") return want;
    return (CAMS.find((c) => camState(s, st, c.id) === "ok") || CAMS[0]).id;
  }

  /** Switch view. byHand: a tap on the picker (remembered, and says why if it's greyed). */
  pick(id, byHand = false) {
    const state = camState(this.ctx.settings, this.ctx.store, id);
    if (state !== "ok") {
      if (byHand) toast(state === "off" ? `${this.camName(id)} camera isn't fitted. Turn it on in Settings > Cameras.`
        : state === "few" ? "The combined view needs at least two cameras fitted."
          : state === "nopicture" ? "Trailer's plugged in but there's no picture from its camera. Check the round plug." : "No trailer plugged in.", "warn");
      id = this.firstOk(id);
    }
    if (byHand) this.ctx.settings.set("camera.current", id);
    if (id !== this.view) { this.view = id; this.layout(); }
    this.paintPick();
  }

  /** Combined view: make this video board camera the live one. */
  showLive(cam) { this.boardPick = cam; this.layout(); }

  camName(id) {
    if (id === "combo") return "All";
    return this.ctx.settings.get(`camera.cams.${id}.name`) || (CAMS.find((c) => c.id === id) || { name: id }).name;
  }

  paintPick() {
    if (!this.root) return;
    const { settings: s, store: st } = this.ctx;
    this.root.querySelectorAll(".cp-btn").forEach((b) => {
      const id = b.dataset.cam, state = camState(s, st, id);
      b.querySelector(".cp-name").textContent = this.camName(id).toUpperCase();
      b.querySelector(".cp-tag").textContent = id === "combo" && state === "ok" ? `${comboCams(s, st).length} CAMS` : TAG[state] || "";
      b.classList.toggle("on", id === this.view);
      b.classList.toggle("off", state !== "ok");
      b.setAttribute("aria-disabled", state !== "ok" ? "true" : "false");
    });
  }

  /** Build (or update) the panes for the current view. force: restart every picture. */
  layout(force = false) {
    if (!this.root) return;
    const want = layoutFor(this.ctx.settings, this.ctx.store, this.view, this.boardPick);
    const key = want.map((w) => `${w.cam}:${w.live ? 1 : 0}`).join(",");
    if (key === this.layoutKey && !force) return;
    this.layoutKey = key;
    // Panes going away first, then anything going from live to paused, so the video board is
    // free before the next camera on it starts.
    for (const [cam, p] of this.panes) if (!want.some((w) => w.cam === cam)) { p.stop(); p.root.remove(); this.panes.delete(cam); }
    want.filter((w) => !w.live).forEach((w) => this.paneFor(w.cam).setLive(false));
    want.filter((w) => w.live).forEach((w) => {
      const p = this.paneFor(w.cam);
      if (!this.started) { p.live = true; p.paint(); return; }   // starts when the screen is first shown
      if (force) { p.live = true; p.paint(); p.start(); } else p.setLive(true);
    });
    want.forEach((w, i) => { const p = this.panes.get(w.cam); p.root.dataset.slot = i; this.grid.appendChild(p.root); });
    this.grid.className = `cam-grid n${want.length}${want.length > 1 && want.some((w) => w.cam === "rear") ? " has-rear" : ""}`;
    this.root.querySelector(".cam").classList.toggle("combo", this.view === "combo");
    this.paintAll();
    this.runFake();
  }

  paneFor(cam) {
    if (!this.panes.has(cam)) this.panes.set(cam, new Pane(this, cam));
    return this.panes.get(cam);
  }

  paintAll() {
    this.panes.forEach((p) => p.paint());
    const single = this.view !== "combo", cam = this.ctx.settings.get(`camera.cams.${this.view}`) || {};
    $(this.root, ".cam-tools").hidden = !single;
    $(this.root, "#c-mirror").classList.toggle("on", single && !!cam.mirror);
    $(this.root, "#c-grid").classList.toggle("on", single && !!cam.guides);
  }

  setSrc(t) { $(this.root, "#c-src").textContent = t; }

  // ---- demo picture -----------------------------------------------------------------------------
  runFake() {
    // A fake view of a gravel track so the overlay can be checked without a camera. Front looks
    // ahead; rear and trailer look back. The trailer one has the trailer's tailgate along the
    // bottom, the cabin one a seat, so you can tell them apart. Moves with the real speed.
    if (this._raf) return;
    let last = performance.now();
    const draw = (now) => {
      const dt = Math.min(0.1, (now - last) / 1000); last = now;
      const st = this.ctx.store, kmh = st.get("mc.speed", 0) || 0, fwd = st.get("mc.direction") === "forward";
      let any = false;
      this.panes.forEach((p) => {
        if (!p.fake || p.test.hidden) return;
        any = true;
        p.scroll = (p.scroll || 0) + kmh * (fwd ? -1 : 1) * (p.cam === "front" ? -1 : 1) * dt * 60;
        drawTrack(p.test, p.cam, p.scroll * 20);
      });
      this._raf = any ? requestAnimationFrame(draw) : 0;
    };
    this._raf = requestAnimationFrame(draw);
  }

  // ---- lights ----------------------------------------------------------------------------------
  level(st, id) {
    const mine = this.local[id];
    if (mine && st.pending(id) && Date.now() - mine.at < 1500) return mine.v;
    const v = st.get(id);
    return (v === undefined || v === null ? st.get(`req.${id}`) : v) || 0;
  }

  toggleLevel(id) {
    const st = this.ctx.store, v = this.level(st, id) > 0 ? 0 : 255;
    this.local[id] = { v, at: Date.now() };
    this.ctx.link.request(id, v);
    this.updateLights();
  }

  toggleBars() {
    const st = this.ctx.store, v = FRONT_BARS.some((k) => this.level(st, k) > 0) ? 0 : 255;
    FRONT_BARS.forEach((id) => { this.local[id] = { v, at: Date.now() }; this.ctx.link.request(id, v); });
    this.updateLights();
  }

  // Rear floods from the camera screen. Flips what the lights are doing right now, and
  // remembers the Lights screen setting so it can go back to it after this reverse.
  toggleRear() {
    const st = this.ctx.store, on = !!st.get("light.rear");
    if (this.rearBefore == null) this.rearBefore = st.get("req.light.rear") || "auto";
    this.rearMine = on ? "off" : "on";
    this.ctx.link.request("light.rear", this.rearMine);
    this.updateLights();
  }

  restoreRear() {
    if (this.rearBefore == null) return;
    this.ctx.link.request("light.rear", this.rearBefore);
    this.rearBefore = this.rearMine = null;
  }

  updateLights() { this.panes.forEach((p) => p.update(this.ctx.store)); }

  hide() {
    this.restoreRear(); this.wasRev = false;
    this.started = false;
    this.panes.forEach((p) => { p.stop(); p.started = false; });
  }

  /** Which camera to pop up in reverse. */
  reverseCam() {
    const { settings: s, store: st } = this.ctx;
    if (s.get("camera.reverseView") === "combo" && camState(s, st, "combo") === "ok") return "combo";
    if (s.get("camera.trailerInReverse") !== false && camState(s, st, "trailer") === "ok") return "trailer";
    return camState(s, st, "rear") === "ok" ? "rear" : this.firstOk(this.view);
  }

  update(st) {
    const set = this.ctx.settings;
    const rev = st.get("mc.direction") === "reverse" || st.get("in.reverse");
    // Trailer on or off (plug or picture), or a camera fitted or not: grey the buttons, and move
    // off a camera that just went away. The combined view adds or drops the trailer picture.
    const trailer = trailerOn(set, st), tState = camState(set, st, "trailer");
    if (tState !== this.hadTrailer) {
      const first = this.hadTrailer === undefined, was = this.hadTrailer;
      this.hadTrailer = tState;
      if (!first) {
        if (tState === "ok") toast("Trailer camera ready.");
        else if (tState === "nopicture") toast("Trailer plugged in, but no picture from its camera.", "warn");
        else if (was === "ok" && this.view === "trailer") toast("Trailer camera gone. Back to the rear camera.", "warn");
      }
      if (trailer && !first) this.boardPick = null;   // a trailer just went on: show its camera live
      if (this.view === "trailer" && tState !== "ok") this.pick("rear");
      else this.layout();
      this.paintPick();
    }
    // Into reverse: pop up the reverse view. In the combined view, stay there and make the
    // camera behind you live (trailer if one's on).
    if (rev && !this.wasRev) {
      if (this.view === "combo" && set.get("camera.reverseView") !== "single") {
        this.boardPick = set.get("camera.trailerInReverse") !== false && camState(set, st, "trailer") === "ok" ? "trailer" : "rear";
        this.layout();
      } else if (set.get("camera.autoOnReverse")) this.pick(this.reverseCam());
    }
    $(this.root, "#c-rev").hidden = !rev;
    // Big rear lights button in reverse, on a single rear or trailer picture.
    this.root.querySelectorAll(".cam-rear[data-light='light.rear']").forEach((b) => b.classList.toggle("big", !!rev && this.view !== "combo"));
    this.updateLights();
    if (!rev && this.wasRev) this.restoreRear();
    this.wasRev = !!rev;
    this.paintDemo(st);
    const mph = set.get("units") === "mph";
    $(this.root, "#c-spd").textContent = `${Math.round(st.get("mc.speed", 0) * (mph ? 0.621371 : 1))} ${mph ? "mph" : "km/h"}`;
  }
}

function drawTrack(c, view, t) {
  const g = c.getContext("2d"), W = c.width, H = c.height;
  const sky = g.createLinearGradient(0, 0, 0, H * 0.4); sky.addColorStop(0, "#8fb3c9"); sky.addColorStop(1, "#c9d6d8");
  g.fillStyle = sky; g.fillRect(0, 0, W, H * 0.4);
  g.fillStyle = "#3d5a2e"; g.fillRect(0, H * 0.4, W, H);
  g.fillStyle = "#7a6a55"; g.beginPath(); g.moveTo(W * 0.42, H * 0.4); g.lineTo(W * 0.58, H * 0.4); g.lineTo(W * 0.95, H); g.lineTo(W * 0.05, H); g.fill();
  g.fillStyle = "rgba(0,0,0,.18)";
  const span = H * 0.6;
  for (let i = 0; i < 40; i++) { const y = H * 0.4 + ((((i * 37 + t / 20) % span) + span) % span); const s = (y - H * 0.4) / (H * 0.6); g.fillRect(W / 2 + Math.sin(i * 7) * W * 0.4 * s, y, 6 * s + 1, 3 * s + 1); }
  if (view === "trailer") {
    g.fillStyle = "#2b2b2b"; g.fillRect(0, H * 0.8, W, H * 0.2);
    g.fillStyle = "#c0392b"; g.fillRect(W * 0.03, H * 0.82, W * 0.1, H * 0.06); g.fillRect(W * 0.87, H * 0.82, W * 0.1, H * 0.06);
  } else if (view === "rear") {
    // the tray's back edge and the tow bar
    g.fillStyle = "#26221d"; g.fillRect(0, H * 0.9, W, H * 0.1);
    g.fillStyle = "#555"; g.fillRect(W * 0.47, H * 0.84, W * 0.06, H * 0.08);
  } else if (view === "front") {
    g.fillStyle = "#1d1d1d"; g.beginPath(); g.moveTo(0, H); g.lineTo(0, H * 0.86); g.quadraticCurveTo(W / 2, H * 0.74, W, H * 0.86); g.lineTo(W, H); g.fill();
  } else if (view === "cabin") {
    g.fillStyle = "#222"; g.fillRect(0, 0, W, H);
    g.fillStyle = "#3a3a3a"; g.fillRect(W * 0.12, H * 0.3, W * 0.3, H * 0.7); g.fillRect(W * 0.58, H * 0.3, W * 0.3, H * 0.7);
  }
}

/** List the video devices the browser can see (bench cameras). */
export async function listCameras() {
  try {
    // Labels only show once permission has been given, so ask briefly first.
    const s = await navigator.mediaDevices.getUserMedia({ video: true }); s.getTracks().forEach((t) => t.stop());
  } catch {}
  try { return (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "videoinput"); } catch { return []; }
}
