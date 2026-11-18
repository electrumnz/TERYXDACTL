// Cameras: rear, front and trailer. Pick one with the buttons along the top.
// Each camera can be:
//  - a USB camera, or an RCA/AHD camera through a USB AV capture dongle. Both show up as a normal
//    video device, so the browser opens them directly (getUserMedia). This is the fast path.
//  - "stream": an MJPEG stream from the dash server (/api/camera.mjpg?cam=<id>), as a fallback if
//    the browser can't open the device, or for a network camera.
// A camera that isn't fitted (Settings > Cameras) shows greyed out. The trailer camera also greys
// out when no trailer is plugged in (in.trailer, from the reed switch in the 7-pin socket).
// Pops up on its own in reverse (Settings > Cameras): the trailer camera if a trailer is plugged in
// and that camera is fitted, otherwise the rear one.
// In reverse a big rear light bar button shows bottom left, sized for a gloved hand while
// you're looking over your shoulder. A tap only lasts for this reverse: once you're out of
// reverse the rear lights go back to whatever they were set to on the Lights screen.
import { $, toast } from "../ui/controls.js";
import { icon } from "../ui/icons.js";

export const CAMS = [
  { id: "rear", name: "Rear" },
  { id: "front", name: "Front" },
  { id: "trailer", name: "Trailer" },
  { id: "cabin", name: "Cabin" },
];

/** "ok", "off" (not fitted) or "notrailer" (trailer camera with no trailer plugged in). */
export function camState(settings, store, id) {
  const c = settings.get(`camera.cams.${id}`) || {};
  if (!c.fitted) return "off";
  if (id === "trailer" && !store.get("in.trailer")) return "notrailer";
  return "ok";
}

const TAG = { off: "NOT FITTED", notrailer: "NO TRAILER" };

export class CameraScreen {
  constructor(ctx) { this.ctx = ctx; this.id = "camera"; this.label = "Cameras"; this.icon = "camera"; this.stream = null; this.view = null; }

  mount(root) {
    root.style.padding = "0";
    root.innerHTML = `
      <div class="cam">
        <video id="c-video" autoplay muted playsinline></video>
        <img id="c-img" alt="" hidden>
        <canvas id="c-test" class="feed" width="1176" height="740" hidden></canvas>
        <svg class="overlay" id="c-guides" viewBox="0 0 1176 740" preserveAspectRatio="none"></svg>
        <div class="cam-msg" id="c-msg">Starting camera…</div>
        <div class="cam-hud"><span id="c-rev" class="rev" hidden>R</span><span id="c-spd" class="num">0 km/h</span><span id="c-src"></span></div>
        <div class="cam-pick" id="c-pick">
          ${CAMS.map((c) => `<button class="cp-btn" data-cam="${c.id}"><span class="cp-name"></span><i class="cp-tag"></i></button>`).join("")}
        </div>
        <button class="cam-rear" id="c-rear" aria-label="Rear light bar on or off">
          ${icon("lights")}<span class="cr-text"><span class="cr-name">REAR LIGHT BAR</span><span class="cr-state" id="c-rear-state">OFF</span></span>
        </button>
        <div class="cam-tools">
          <button class="btn" id="c-mirror">${icon("mirror")}</button>
          <button class="btn" id="c-grid">${icon("grid")}</button>
        </div>
      </div>`;
    this.root = root;
    const set = this.ctx.settings;
    $(root, "#c-mirror").onclick = () => { const k = `camera.cams.${this.view}.mirror`; set.set(k, !set.get(k)); this.applyLook(); };
    $(root, "#c-grid").onclick = () => { const k = `camera.cams.${this.view}.guides`; set.set(k, !set.get(k)); this.applyLook(); };
    $(root, "#c-rear").onclick = () => this.toggleRear();
    root.querySelectorAll(".cp-btn").forEach((b) => (b.onclick = () => this.pick(b.dataset.cam, true)));
    set.subscribe((p) => {
      if (!p.startsWith("camera.")) return;
      this.paintPick();
      // Only restart the picture if something about how it's opened changed.
      if (/^camera\.(source|streamUrl|cams\.[a-z]+\.(deviceId|fitted|v4l2Device))$/.test(p) || p === "camera.cams") { if (this.started) this.pick(this.view, false, true); }
      else this.applyLook();
    });
    this.view = this.firstOk(set.get("camera.current"));
    this.paintPick();
    this.drawGuides();
    this.applyLook();
  }

  show() { if (!this.started) this.restart(); }

  /** The camera to show: the one asked for if it's working, else the first that is. */
  firstOk(want) {
    const { settings: s, store: st } = this.ctx;
    if (want && camState(s, st, want) === "ok") return want;
    return (CAMS.find((c) => camState(s, st, c.id) === "ok") || CAMS[0]).id;
  }

  /** Switch camera. byHand: a tap on the picker (remembered, and says why if it's greyed). */
  pick(id, byHand = false, force = false) {
    const state = camState(this.ctx.settings, this.ctx.store, id);
    if (state !== "ok") {
      if (byHand) toast(state === "off" ? `${this.camName(id)} camera isn't fitted. Turn it on in Settings > Cameras.` : "No trailer plugged in.", "warn");
      id = this.firstOk(id);
    }
    if (byHand) this.ctx.settings.set("camera.current", id);
    if (id === this.view && !force && this.started) { this.paintPick(); return; }
    this.view = id;
    this.paintPick();
    this.applyLook();
    if (this.started || force) this.restart();
  }

  camName(id) { return this.ctx.settings.get(`camera.cams.${id}.name`) || (CAMS.find((c) => c.id === id) || { name: id }).name; }

  paintPick() {
    if (!this.root) return;
    this.root.querySelectorAll(".cp-btn").forEach((b) => {
      const id = b.dataset.cam, state = camState(this.ctx.settings, this.ctx.store, id);
      b.querySelector(".cp-name").textContent = this.camName(id).toUpperCase();
      b.querySelector(".cp-tag").textContent = TAG[state] || "";
      b.classList.toggle("on", id === this.view);
      b.classList.toggle("off", state !== "ok");
      b.setAttribute("aria-disabled", state !== "ok" ? "true" : "false");
    });
  }

  async restart() {
    this.started = true;
    this.stopStream();
    const set = this.ctx.settings, cam = set.get(`camera.cams.${this.view}`) || {};
    const src = set.get("camera.source");
    const msg = $(this.root, "#c-msg"), video = $(this.root, "#c-video"), img = $(this.root, "#c-img"), test = $(this.root, "#c-test");
    const run = (this.run = (this.run || 0) + 1);   // a newer restart wins if two overlap
    video.hidden = img.hidden = test.hidden = true; msg.hidden = false; msg.textContent = `Starting ${this.camName(this.view).toLowerCase()} camera…`;
    if (camState(set, this.ctx.store, this.view) !== "ok") { msg.textContent = "No camera fitted. Turn one on in Settings > Cameras."; $(this.root, "#c-src").textContent = ""; return; }
    // Demo mode, or the bench simulator with no camera plugged in: show a fake view instead.
    const fake = () => this.ctx.store.get("link.demo") || this.ctx.store.get("sim.scenario") != null;
    if (this.ctx.store.get("link.demo")) { this.testPattern(); return; }
    // A Raspberry Pi ribbon camera ("csi0") or the analogue video board ("adv:N") can only come
    // through the server stream.
    const csi = /^(csi\d|adv:\d)$/.test(cam.v4l2Device || "");
    if (!csi && (src === "usb" || src === "auto")) {
      try {
        const id = cam.deviceId, size = { width: { ideal: 1280 }, height: { ideal: 720 } };
        // With more than one camera plugged in, "first camera found" is only safe for the rear one.
        if (!id && this.view !== "rear") throw Object.assign(new Error("pick"), { name: "NoDevicePicked" });
        const stream = await navigator.mediaDevices.getUserMedia({ video: id ? { deviceId: { exact: id }, ...size } : size, audio: false });
        if (run !== this.run) { stream.getTracks().forEach((t) => t.stop()); return; }
        this.stream = stream;
        video.srcObject = this.stream; video.hidden = false; msg.hidden = true;
        $(this.root, "#c-src").textContent = "USB";
        return;
      } catch (e) {
        if (run !== this.run) return;
        if (fake()) { this.testPattern(); return; }
        if (src === "usb") {
          msg.textContent = e.name === "NoDevicePicked" ? `Pick which device is the ${this.camName(this.view).toLowerCase()} camera in Settings > Cameras.`
            : `Can't open the camera (${e.name}). Check it's plugged in, or pick another device in Settings > Cameras.`;
          return;
        }
      }
    }
    // Server stream
    img.onload = () => { msg.hidden = true; };
    img.onerror = () => { if (run !== this.run) return; if (fake()) { img.hidden = true; this.testPattern(); return; } msg.hidden = false; msg.textContent = "No camera found. Plug in the USB camera or capture dongle, then check Settings > Cameras."; };
    img.src = `${set.get("camera.streamUrl")}?cam=${this.view}&t=${Date.now()}`;
    img.hidden = false;
    $(this.root, "#c-src").textContent = "STREAM";
  }

  stopStream() {
    if (this.stream) { this.stream.getTracks().forEach((t) => t.stop()); this.stream = null; }
    if (this._raf) cancelAnimationFrame(this._raf);
    const img = this.root && $(this.root, "#c-img"); if (img) img.removeAttribute("src");
  }

  testPattern() {
    // Demo mode: a fake view of a gravel track so the overlay can be checked without a camera.
    // Front looks ahead (the track comes towards you going forward); rear and trailer look back.
    // The trailer one has the trailer's tailgate along the bottom so you can tell it apart.
    const c = $(this.root, "#c-test"), g = c.getContext("2d"), msg = $(this.root, "#c-msg"), view = this.view;
    c.hidden = false; msg.hidden = true; $(this.root, "#c-src").textContent = this.ctx.store.get("link.demo") ? "DEMO" : "SIM";
    if (this._raf) cancelAnimationFrame(this._raf);
    // The gravel moves with the real speed: backing up, the track runs away from the camera.
    let scroll = 0, last = performance.now();
    const draw = (now) => {
      const dt = Math.min(0.1, (now - last) / 1000); last = now;
      const st = this.ctx.store, kmh = st.get("mc.speed", 0) || 0, dir = (st.get("mc.direction") === "forward" ? -1 : 1) * (view === "front" ? -1 : 1);
      scroll += kmh * dir * dt * 60;
      const t = scroll * 20;
      const W = c.width, H = c.height;
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
      } else if (view === "front") {
        g.fillStyle = "#1d1d1d"; g.beginPath(); g.moveTo(0, H); g.lineTo(0, H * 0.86); g.quadraticCurveTo(W / 2, H * 0.74, W, H * 0.86); g.lineTo(W, H); g.fill();
      }
      this._raf = requestAnimationFrame(draw);
    };
    this._raf = requestAnimationFrame(draw);
  }

  applyLook() {
    // Mirror and guide lines are per camera: a front camera usually wants neither.
    const set = this.ctx.settings, cam = set.get(`camera.cams.${this.view}`) || {}, m = !!cam.mirror, gl = !!cam.guides;
    ["#c-video", "#c-img", "#c-test"].forEach((s) => ($(this.root, s).style.transform = m ? "scaleX(-1)" : ""));
    $(this.root, "#c-guides").style.display = gl ? "" : "none";
    $(this.root, "#c-mirror").classList.toggle("on", m);
    $(this.root, "#c-grid").classList.toggle("on", gl);
    this.drawGuides();
  }

  drawGuides() {
    // Fixed parking guides: red about 0.5 m, amber 1 m, green 2 m. Nudge sideways in Settings.
    const o = this.ctx.settings.get("camera.guideOffset") || 0, cx = 588 + o;
    const lines = [[700, 330, "#ff4b4b"], [560, 270, "#ffad1f"], [430, 215, "#36d67e"]];
    let s = `<path d="M${cx - 420} 740 L${cx - 200} 400 M${cx + 420} 740 L${cx + 200} 400" stroke="#ffad1f" stroke-width="6" fill="none" stroke-linecap="round" opacity=".85"/>`;
    lines.forEach(([y, hw, col]) => (s += `<path d="M${cx - hw} ${y} h80 M${cx + hw} ${y} h-80" stroke="${col}" stroke-width="8" stroke-linecap="round"/>`));
    $(this.root, "#c-guides").innerHTML = s;
  }

  // Rear light bar from the camera screen. Flips what the lights are doing right now, and
  // remembers the Lights screen setting so it can go back to it after this reverse.
  toggleRear() {
    const st = this.ctx.store, on = !!st.get("light.rear");
    if (this.rearBefore == null) this.rearBefore = st.get("req.light.rear") || "auto";
    this.rearMine = on ? "off" : "on";
    this.ctx.link.request("light.rear", this.rearMine);
    this.paintRear(!on);
  }

  paintRear(on) {
    const b = $(this.root, "#c-rear");
    b.classList.toggle("on", on);
    $(this.root, "#c-rear-state").textContent = on ? "ON" : "OFF";
  }

  restoreRear() {
    if (this.rearBefore == null) return;
    this.ctx.link.request("light.rear", this.rearBefore);
    this.rearBefore = this.rearMine = null;
  }

  hide() { this.restoreRear(); this.wasRev = false; }

  /** Which camera to pop up in reverse. */
  reverseCam() {
    const { settings: s, store: st } = this.ctx;
    if (s.get("camera.trailerInReverse") !== false && camState(s, st, "trailer") === "ok") return "trailer";
    return camState(s, st, "rear") === "ok" ? "rear" : this.firstOk(this.view);
  }

  update(st) {
    const rev = st.get("mc.direction") === "reverse" || st.get("in.reverse");
    // Trailer plugged in or out, or a camera fitted or not: grey the buttons, and move off a
    // camera that just went away.
    const trailer = !!st.get("in.trailer");
    if (trailer !== this.hadTrailer) {
      const first = this.hadTrailer === undefined;
      this.hadTrailer = trailer;
      if (!first && trailer && camState(this.ctx.settings, st, "trailer") === "ok") toast("Trailer plugged in. Trailer camera ready.");
      if (this.view === "trailer" && !trailer) { if (!first) toast("Trailer unplugged. Back to the rear camera.", "warn"); this.pick("rear"); }
      else this.paintPick();
    }
    // Into reverse: show the trailer camera if there's a trailer on, else the rear one.
    if (rev && !this.wasRev && this.ctx.settings.get("camera.autoOnReverse")) this.pick(this.reverseCam());
    $(this.root, "#c-rev").hidden = !rev;
    const rb = $(this.root, "#c-rear");
    rb.classList.toggle("big", !!rev);
    if (!st.pending("light.rear")) this.paintRear(!!st.get("light.rear"));
    if (!rev && this.wasRev) this.restoreRear();
    this.wasRev = !!rev;
    const mph = this.ctx.settings.get("units") === "mph";
    $(this.root, "#c-spd").textContent = `${Math.round(st.get("mc.speed", 0) * (mph ? 0.621371 : 1))} ${mph ? "mph" : "km/h"}`;
  }
}

/** List the video devices the browser can see (USB cameras and capture dongles). */
export async function listCameras() {
  try {
    // Labels only show once permission has been given, so ask briefly first.
    const s = await navigator.mediaDevices.getUserMedia({ video: true }); s.getTracks().forEach((t) => t.stop());
  } catch {}
  try { return (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "videoinput"); } catch { return []; }
}
