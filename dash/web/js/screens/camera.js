// Reverse camera. Works with either camera type, since we don't know yet which one is fitted:
//  - USB camera, or an RCA/AHD camera through a USB AV capture dongle. Both show up as a normal
//    video device, so the browser opens them directly (getUserMedia). This is the fast path.
//  - "stream": an MJPEG stream from the dash server (/api/camera.mjpg), as a fallback if the
//    browser can't open the device, or for a network camera.
// Pops up on its own in reverse (Settings > Camera).
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
        <div class="cam-tools">
          <button class="btn" id="c-mirror">${icon("mirror")}</button>
          <button class="btn" id="c-grid">${icon("grid")}</button>
        </div>
      </div>`;
    this.root = root;
    const set = this.ctx.settings;
    $(root, "#c-mirror").onclick = () => { set.set("camera.mirror", !set.get("camera.mirror")); this.applyLook(); };
    $(root, "#c-grid").onclick = () => { set.set("camera.guides", !set.get("camera.guides")); this.applyLook(); };
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
    if (this.ctx.store.get("link.demo")) { this.testPattern(); return; }
    if (src === "usb" || src === "auto") {
      try {
        const id = this.ctx.settings.get("camera.deviceId");
        this.stream = await navigator.mediaDevices.getUserMedia({ video: id ? { deviceId: { exact: id }, width: { ideal: 1280 }, height: { ideal: 720 } } : { width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
        video.srcObject = this.stream; video.hidden = false; msg.hidden = true;
        $(this.root, "#c-src").textContent = "USB";
        return;
      } catch (e) {
        if (src === "usb") { msg.textContent = `Can't open the camera (${e.name}). Check it's plugged in, or pick another camera in Settings.`; return; }
      }
    }
    // Server stream
    img.onload = () => { msg.hidden = true; };
    img.onerror = () => { msg.hidden = false; msg.textContent = "No camera found. Plug in the USB camera or capture dongle, then check Settings > Camera."; };
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
    c.hidden = false; msg.hidden = true; $(this.root, "#c-src").textContent = "DEMO";
    const draw = (t) => {
      const W = c.width, H = c.height;
      const sky = g.createLinearGradient(0, 0, 0, H * 0.4); sky.addColorStop(0, "#8fb3c9"); sky.addColorStop(1, "#c9d6d8");
      g.fillStyle = sky; g.fillRect(0, 0, W, H * 0.4);
      g.fillStyle = "#3d5a2e"; g.fillRect(0, H * 0.4, W, H);
      g.fillStyle = "#7a6a55"; g.beginPath(); g.moveTo(W * 0.42, H * 0.4); g.lineTo(W * 0.58, H * 0.4); g.lineTo(W * 0.95, H); g.lineTo(W * 0.05, H); g.fill();
      g.fillStyle = "rgba(0,0,0,.18)";
      for (let i = 0; i < 40; i++) { const y = H * 0.4 + ((i * 37 + t / 20) % (H * 0.6)); const s = (y - H * 0.4) / (H * 0.6); g.fillRect(W / 2 + Math.sin(i * 7) * W * 0.4 * s, y, 6 * s + 1, 3 * s + 1); }
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

  update(st) {
    const rev = st.get("mc.direction") === "reverse" || st.get("in.reverse");
    $(this.root, "#c-rev").hidden = !rev;
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
