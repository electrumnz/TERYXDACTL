// Reverse camera. Works with either camera type, since we don't know yet which one is fitted:
//  - USB camera, or an RCA/AHD camera through a USB AV capture dongle. Both show up as a normal
//    video device, so the browser opens them directly (getUserMedia). This is the fast path.
//  - "stream": an MJPEG stream from the dash server (/api/camera.mjpg), as a fallback if the
//    browser can't open the device, or for a network camera.
// Pops up on its own in reverse (Settings > Camera).
// In reverse a big rear light bar button shows bottom left, sized for a gloved hand while
// you're looking over your shoulder. A tap only lasts for this reverse: once you're out of
// reverse the rear lights go back to whatever they were set to on the Lights screen.
import { $, toast } from "../ui/controls.js";
import { icon } from "../ui/icons.js";

export class CameraScreen {
  constructor(ctx) { this.ctx = ctx; this.id = "camera"; this.label = "Camera"; this.icon = "camera"; this.stream = null; }

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
    $(root, "#c-mirror").onclick = () => { set.set("camera.mirror", !set.get("camera.mirror")); this.applyLook(); };
    $(root, "#c-grid").onclick = () => { set.set("camera.guides", !set.get("camera.guides")); this.applyLook(); };
    $(root, "#c-rear").onclick = () => this.toggleRear();
    set.subscribe((p) => { if (p.startsWith("camera.")) { if (p === "camera.source" || p === "camera.deviceId" || p === "camera.streamUrl") this.restart(); else this.applyLook(); } });
    this.drawGuides();
    this.applyLook();
  }

  show() { if (!this.started) this.restart(); }

  async restart() {
    this.started = true;
    this.stopStream();
    const src = this.ctx.settings.get("camera.source");
    const msg = $(this.root, "#c-msg"), video = $(this.root, "#c-video"), img = $(this.root, "#c-img"), test = $(this.root, "#c-test");
    video.hidden = img.hidden = test.hidden = true; msg.hidden = false; msg.textContent = "Starting camera…";
    // Demo mode, or the bench simulator with no camera plugged in: show a fake track instead.
    const fake = () => this.ctx.store.get("link.demo") || this.ctx.store.get("sim.scenario") != null;
    if (this.ctx.store.get("link.demo")) { this.testPattern(); return; }
    if (src === "usb" || src === "auto") {
      try {
        const id = this.ctx.settings.get("camera.deviceId");
        this.stream = await navigator.mediaDevices.getUserMedia({ video: id ? { deviceId: { exact: id }, width: { ideal: 1280 }, height: { ideal: 720 } } : { width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
        video.srcObject = this.stream; video.hidden = false; msg.hidden = true;
        $(this.root, "#c-src").textContent = "USB";
        return;
      } catch (e) {
        if (fake()) { this.testPattern(); return; }
        if (src === "usb") { msg.textContent = `Can't open the camera (${e.name}). Check it's plugged in, or pick another camera in Settings.`; return; }
      }
    }
    // Server stream
    img.onload = () => { msg.hidden = true; };
    img.onerror = () => { if (fake()) { img.hidden = true; this.testPattern(); return; } msg.hidden = false; msg.textContent = "No camera found. Plug in the USB camera or capture dongle, then check Settings > Camera."; };
    img.src = `${this.ctx.settings.get("camera.streamUrl")}?t=${Date.now()}`;
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
    const c = $(this.root, "#c-test"), g = c.getContext("2d"), msg = $(this.root, "#c-msg");
    c.hidden = false; msg.hidden = true; $(this.root, "#c-src").textContent = this.ctx.store.get("link.demo") ? "DEMO" : "SIM";
    if (this._raf) cancelAnimationFrame(this._raf);
    // The gravel moves with the real speed: backing up, the track runs away from the camera.
    let scroll = 0, last = performance.now();
    const draw = (now) => {
      const dt = Math.min(0.1, (now - last) / 1000); last = now;
      const st = this.ctx.store, kmh = st.get("mc.speed", 0) || 0, dir = st.get("mc.direction") === "forward" ? -1 : 1;
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
      this._raf = requestAnimationFrame(draw);
    };
    this._raf = requestAnimationFrame(draw);
  }

  applyLook() {
    const set = this.ctx.settings, m = set.get("camera.mirror");
    ["#c-video", "#c-img", "#c-test"].forEach((s) => ($(this.root, s).style.transform = m ? "scaleX(-1)" : ""));
    $(this.root, "#c-guides").style.display = set.get("camera.guides") ? "" : "none";
    $(this.root, "#c-mirror").classList.toggle("on", m);
    $(this.root, "#c-grid").classList.toggle("on", set.get("camera.guides"));
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

  hide() { this.restoreRear(); }

  update(st) {
    const rev = st.get("mc.direction") === "reverse" || st.get("in.reverse");
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
