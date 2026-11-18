/* Teryx Remote: the handheld screen for RC launching (docs/rc-beach-launch.md).
 *
 * On the real thing this page talks to the Pi over the remote's own link and the
 * RC box Pico makes every safety call (teryx/rc_mode.py). Here, with no Teryx,
 * it runs a pretend one using the same rules so it can be tried on a phone:
 * a sloping beach, a trailer, the sea coming up as you back down.
 *
 * Inputs: the on-screen sticks by default (thumb on the left stick is the dead-man),
 * or an optional gamepad (left stick Y = forward/back, right stick X = steer, R2 go,
 * L2 brake, L1 dead-man, A/Cross = winch in, B/Circle = winch out), or keyboard
 * (W/S, A/D, Space dead-man).
 */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);

  // ---- settings: same names and values as DEFAULTS in teryx/rc_mode.py ----
  const S = { allow_4g: false, cap_4g_kmh: 2, link_timeout_4g_s: 0.5, link_timeout_s: 0.2, fwd_cap_kmh: 5, rev_cap_kmh: 3, overspeed_brake_kmh: 1.5,
    stopped_kmh: 0.5, spin_motor_kmh: 3, spin_ground_kmh: 0.5, spin_s: 1.5, stall_throttle: 0.5, stall_s: 3 };
  const F = 1, N = 0, R = -1;
  const App = window.TeryxApp || null;   // set when running inside the Android app

  // ---- inputs -----------------------------------------------------------
  const inp = { drive: 0, steer: 0, go: 0, brake: 0, dead: false, winch: 0, estop: false };
  const touch = { drive: 0, steer: 0 };
  const keys = new Set();
  addEventListener("keydown", (e) => { keys.add(e.code); if (e.code === "Space") e.preventDefault(); });

  // ---- iPhone and Android: no zoom, no scrolling, screen stays on ------------------
  // iOS Safari ignores user-scalable=no, so block its pinch and double-tap zoom here,
  // and stop the page dragging about. The sticks use pointer events, so this doesn't touch them.
  ["gesturestart", "gesturechange", "gestureend"].forEach((t) => document.addEventListener(t, (e) => e.preventDefault()));
  document.addEventListener("dblclick", (e) => e.preventDefault());
  document.addEventListener("touchmove", (e) => { if (!e.target.closest("input, .setbox")) e.preventDefault(); }, { passive: false });
  document.addEventListener("contextmenu", (e) => e.preventDefault());

  // Keep the screen awake while the remote is open. Screen Wake Lock works in Safari 16.4+,
  // and in a home-screen app from iOS 18.4. It drops when the app is hidden, so take it again.
  let wake = null;
  async function keepAwake() {
    if (!("wakeLock" in navigator) || document.visibilityState !== "visible" || wake) return;
    try { wake = await navigator.wakeLock.request("screen"); wake.addEventListener("release", () => { wake = null; phoneInfo(); }); }
    catch (_) { wake = null; }
    phoneInfo();
  }
  document.addEventListener("visibilitychange", keepAwake);
  addEventListener("pointerdown", keepAwake);       // some browsers only allow it after a tap
  function phoneInfo() {
    const el = document.getElementById("phoneInfo"); if (!el) return;
    const ios = /iP(hone|ad|od)/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    const app = matchMedia("(display-mode: fullscreen), (display-mode: standalone)").matches || navigator.standalone === true;
    const bits = [];
    if (App) bits.push(`Teryx Remote app ${App.version()}${App.kiosk() ? ", locked kiosk" : ""}.`);
    else bits.push(app ? "Running as an app." : ios ? "Add to Home Screen (Share, then Add to Home Screen) for full screen." : "Install it (browser menu, Add to Home screen) for full screen.");
    bits.push(wake || App ? "Screen stays on." : "wakeLock" in navigator ? "Tap anywhere to keep the screen on." : "Can't keep the screen on here: set Auto-Lock to Never while launching.");
    bits.push(navigator.getGamepads ? (window.isSecureContext ? "Gamepads OK." : "Gamepads need the secure (https) page.") : "No gamepad support in this browser.");
    el.textContent = bits.join(" ");
  }
  addEventListener("keyup", (e) => keys.delete(e.code));

  // A palm or the side of a hand makes a big contact patch: ignore those, only fingertips count.
  const isPalm = (e) => e.pointerType === "touch" && (e.width > 70 || e.height > 70);
  const held = { drive: false, steer: false };
  function stickPad(el, axis, key) {
    const knob = el.querySelector("i");
    let id = null;
    const move = (e) => {
      const r = el.getBoundingClientRect();
      let v = axis === "x" ? (e.clientX - r.left) / r.width * 2 - 1 : -((e.clientY - r.top) / r.height * 2 - 1);
      v = Math.max(-1, Math.min(1, v * 1.25));
      touch[key] = Math.abs(v) < 0.08 ? 0 : v;
      knob.style.transform = axis === "x" ? `translateX(${v * (r.width / 2 - 36)}px)` : `translateY(${-v * (r.height / 2 - 36)}px)`;
    };
    el.addEventListener("pointerdown", (e) => {
      if (id !== null || isPalm(e)) return;          // one thumb per stick, no palms
      id = e.pointerId; el.setPointerCapture(id); held[key] = true; el.classList.add("held"); move(e);
    });
    el.addEventListener("pointermove", (e) => { if (e.pointerId === id) move(e); });
    const up = (e) => { if (e.pointerId !== id) return; id = null; held[key] = false; el.classList.remove("held"); touch[key] = 0; knob.style.transform = ""; };
    el.addEventListener("pointerup", up); el.addEventListener("pointercancel", up); el.addEventListener("lostpointercapture", up);
  }
  stickPad($("driveStick"), "y", "drive");
  stickPad($("steerStick"), "x", "steer");

  function holdButton(el, on, off) {
    el.addEventListener("pointerdown", (e) => { el.setPointerCapture(e.pointerId); el.classList.add("on"); on(); });
    const up = () => { el.classList.remove("on"); off(); };
    el.addEventListener("pointerup", up); el.addEventListener("pointercancel", up);
  }
  let touchWinch = 0;
  holdButton($("winchIn"), () => (touchWinch = 1), () => (touchWinch = 0));
  holdButton($("winchOut"), () => (touchWinch = -1), () => (touchWinch = 0));
  $("estop").addEventListener("click", () => {
    inp.estop = !inp.estop;
    $("estop").classList.toggle("on", inp.estop);
    $("estop").textContent = inp.estop ? "RESET" : "STOP";
    if (!inp.estop && box.state !== "off") box.state = "hold";
  });
  // Hardware STOP: the Samsung XCover key, sent in by the Android app. Only ever turns
  // the e-stop on (never off), so a double press can't undo it. Reset with the RESET button.
  addEventListener("teryx-hardstop", () => {
    if (!inp.estop) $("estop").click();
    flash("XCOVER KEY: E-STOP", true);
  });

  const dz = (v, d = 0.08) => (Math.abs(v) < d ? 0 : v);
  function readInputs() {
    const pads = navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : [];
    const gp = pads[0];
    padSwap(!!gp);
    // Thumb on the drive stick = dead-man held. Lift it off and the RC box stops and holds.
    let drive = touch.drive, steer = touch.steer, dead = held.drive, winch = touchWinch;
    if (gp) {
      drive = 0; steer = 0; winch = 0;                // the on-screen controls are hidden now
      dead = false;
      const b = (i) => !!(gp.buttons[i] && gp.buttons[i].pressed);
      const bv = (i) => (gp.buttons[i] ? gp.buttons[i].value : 0);
      drive = dz(-(gp.axes[1] || 0));
      const trig = bv(7) - bv(6);                     // R2 go, L2 brake/back
      if (Math.abs(trig) > Math.abs(drive)) drive = dz(trig);
      steer = dz(gp.axes[2] || 0);
      dead = dead || b(4);
      winch = b(0) ? 1 : b(1) ? -1 : winch;
    }
    if (keys.has("KeyW") || keys.has("ArrowUp")) drive = 1;
    if (keys.has("KeyS") || keys.has("ArrowDown")) drive = -1;
    if (keys.has("KeyA") || keys.has("ArrowLeft")) steer = -1;
    if (keys.has("KeyD") || keys.has("ArrowRight")) steer = 1;
    if (keys.has("Space")) dead = true;
    if (keys.has("KeyI")) winch = 1;
    if (keys.has("KeyO")) winch = -1;
    inp.drive = drive; inp.steer = steer; inp.dead = dead; inp.winch = winch;
    $("padDead").classList.toggle("on", dead);
    $("padDead").textContent = dead ? "L1 HELD" : "HOLD L1 TO DRIVE";
  }

  // Gamepad plugged in or pulled out: swap layouts, and if RC is on, stop and hold.
  // Whatever was being held on the old controls is let go, and driving again needs the
  // stick centred and the new dead-man held (same rule as after a lost signal).
  let padOn = false;
  function padSwap(on) {
    if (on === padOn) return;
    padOn = on;
    document.body.classList.toggle("has-pad", on);
    touch.drive = touch.steer = 0; touchWinch = 0;
    held.drive = held.steer = false;
    document.querySelectorAll(".stick").forEach((el) => { el.classList.remove("held"); el.querySelector("i").style.transform = ""; });
    if (box.state !== "off") { box.state = "hold"; box.reason = on ? "deadman" : "pad_lost"; box.recentre = true; }
    flash(on ? "GAMEPAD CONNECTED: HOLD L1 TO DRIVE" : "GAMEPAD GONE: STOPPED. ON-SCREEN STICKS ARE BACK", !on);
  }

  // ---- remote settings: 4G driving, behind the PIN --------------------------
  // On the real Teryx the PIN goes to the control box ({"type":"lock","cmd":"verify"}) and
  // only then does rc.allow4g change. This works over 4G as well, so it can be switched on
  // when the dash is out of reach. The demo takes any 4 to 6 digits.
  let link = "wifi";
  const panel = $("setPanel");
  const show4g = () => { $("allow4g").textContent = S.allow_4g ? "ON" : "OFF"; $("allow4g").classList.toggle("on", S.allow_4g); };
  $("setBtn").addEventListener("click", () => (panel.hidden = false));
  $("setClose").addEventListener("click", () => (panel.hidden = true));
  let pinThen = null;
  $("allow4g").addEventListener("click", () => {
    $("pinWhy").textContent = S.allow_4g ? "PIN to turn 4G driving off" : "PIN to allow driving over 4G";
    $("pin").value = ""; $("pinBox").hidden = false; $("pin").focus();
    pinThen = () => { S.allow_4g = !S.allow_4g; show4g(); if (!S.allow_4g && link === "4g") setLink("wifi"); };
  });
  $("pinCancel").addEventListener("click", () => { $("pinBox").hidden = true; pinThen = null; });
  $("pinOk").addEventListener("click", () => {
    if (!/^\d{4,6}$/.test($("pin").value)) return flash("A PIN is 4 to 6 digits", true);
    $("pinBox").hidden = true; if (pinThen) pinThen(); pinThen = null;
  });
  function setLink(l) {
    if (l === "4g" && !S.allow_4g) return flash("4G driving is off. Turn it on first (PIN)", true);
    link = l;
    document.querySelectorAll("[data-link]").forEach((b) => b.classList.toggle("on", b.dataset.link === l));
    $("linkType").textContent = l === "4g" ? "4G" : "WI-FI";
    if (box.state !== "off") { box.state = "hold"; box.reason = "deadman"; box.recentre = true; }
  }
  document.querySelectorAll("[data-link]").forEach((b) => b.addEventListener("click", () => setLink(b.dataset.link)));
  show4g();

  // ---- inside the Android app (android/): a couple of extra buttons -------------
  if (App) {
    $("appKeys").hidden = false;
    $("appWifi").addEventListener("click", () => App.wifiSettings());
    $("appSettings").addEventListener("click", () => {
      $("pinWhy").textContent = "PIN to leave the remote for the phone's settings";
      $("pin").value = ""; $("pinBox").hidden = false; $("pin").focus();
      pinThen = () => App.phoneSettings();
    });
  }
  // Taken out of the glove box (charger pulled): the app wakes the screen and tells us.
  addEventListener("teryx-unplugged", () => { keepAwake(); flash("READY. PRESS ARM RC WHEN YOU'RE SET", true); });
  phoneInfo(); keepAwake();

  // ---- pretend Teryx --------------------------------------------------------
  const veh = { kmh: 0, ground: 0, pos: 0, heading: 0, wet: 0, soc: 82, fourwd: false, diff: 0, lights: false,
    winchRope: 0, soft: false, signal: true, lastPacket: 0 };
  const WATER_AT = 6;    // metres back down the beach to the water's edge
  const AXLE_AT = 9;  // where the water reaches the bottom of the axle caps (the Kawasaki limit)

  // ---- RC box rules (a port of teryx/rc_mode.py, stick mode) ----------------
  const box = { state: "off", reason: "", dir: N, centred: true, spin: 0, stall: 0, recentre: false };
  function arm() {
    if (box.state !== "off") { box.state = "off"; return; }
    if (Math.abs(inp.drive) > 0.05) return flash("Let go of the stick first", true);
    if (inp.dead) return flash("Take your thumb off the stick first", true);
    if (veh.kmh > 0.1) return flash("Stop first", true);
    Object.assign(box, { state: "armed", reason: "", dir: N, centred: true, spin: 0, stall: 0, recentre: false });
  }
  $("arm").addEventListener("click", arm);

  function rcTick(now, dt) {
    const o = { thr: 0, brk: 1, dir: N, winch: 0, warn: "" };
    if (box.state === "off") return o;
    const stop = (why) => { box.state = "hold"; box.reason = why; box.recentre = true; return o; };
    const on4g = link === "4g";
    const linkOk = veh.signal && now - veh.lastPacket <= (on4g ? S.link_timeout_4g_s : S.link_timeout_s);
    if (!linkOk) return stop("radio_lost");
    if (on4g && !S.allow_4g) return stop("4g_off");
    if (inp.estop) return stop("estop");
    if (!inp.dead) return stop("deadman");
    if (box.recentre) { if (Math.abs(inp.drive) > 0.05) { if (box.reason === "deadman") box.reason = "recentre"; return o; } box.recentre = false; }
    box.state = "driving"; box.reason = "";
    const moving = veh.kmh >= S.stopped_kmh;
    const v = inp.drive, want = v > 0.05 ? F : v < -0.05 ? R : N;
    let thr = 0, brk = 0;
    if (Math.abs(v) <= 0.05) box.centred = true;
    else if (moving && box.dir !== N && want !== box.dir) { brk = Math.abs(v); box.centred = false; }
    else if (want === box.dir) thr = Math.abs(v);
    else if (!moving && box.centred) { box.dir = want; thr = Math.abs(v); }
    else brk = Math.abs(v);
    if (inp.winch) {
      if (!moving && thr === 0) { o.winch = inp.winch; o.dir = N; return o; }
      o.warn = "Stop to use the winch";
    }
    o.dir = box.dir;
    if (box.dir === R && veh.wet >= 1) { thr = 0; o.warn = veh.wet >= 2 ? "TOO DEEP" : "Water at the limit, no more reverse"; }
    const cap = Math.min(box.dir === F ? S.fwd_cap_kmh : S.rev_cap_kmh, on4g ? S.cap_4g_kmh : 99);
    const over = veh.kmh - cap;
    if (over > 0) thr = 0;   // speed cap: shown as "cap 3 km/h" under the speed, no banner
    box.spin = thr > 0.2 && veh.kmh >= S.spin_motor_kmh && veh.ground < S.spin_ground_kmh ? box.spin + dt : 0;
    box.stall = thr >= S.stall_throttle && veh.kmh < 0.3 && veh.ground < 0.3 ? box.stall + dt : 0;
    if (box.spin >= S.spin_s) { box.spin = 0; return stop("wheelspin"); }
    if (box.stall >= S.stall_s) { box.stall = 0; return stop("stalled"); }
    o.thr = thr;
    o.brk = Math.max(brk, over > S.overspeed_brake_kmh ? 0.6 : thr === 0 && !moving ? 1 : 0);
    return o;
  }

  const WHY = { radio_lost: "SIGNAL LOST: STOPPED ON THE BRAKE", estop: "E-STOP", deadman: "THUMB ON THE LEFT STICK TO DRIVE",
    pad_lost: "GAMEPAD GONE: STOPPED. THUMB ON THE LEFT STICK TO DRIVE",
    "4g_off": "4G DRIVING IS OFF", wheelspin: "DIGGING IN: STOPPED. TRY 4WD + DIFF LOCK", stalled: "STUCK: STOPPED. LET GO, THEN TRY AGAIN", recentre: "LET GO OF THE STICK" };

  // ---- dash-side buttons (these go to the main Pico, same rules as the dash) ----
  document.querySelectorAll(".fnr .key").forEach((b) => b.addEventListener("click", () => {
    const d = +b.dataset.dir;
    if (veh.kmh > S.stopped_kmh) return flash("Stop to change direction", true);
    box.dir = d; box.centred = true;
  }));
  $("fourwd").addEventListener("click", () => {
    if (veh.kmh >= 1) return flash("4WD waits until you've stopped", true);   // Kawasaki: shift stopped
    veh.fourwd = !veh.fourwd;
  });
  $("diff").addEventListener("input", (e) => {
    const want = +e.target.value;
    if (want > veh.diff && veh.kmh >= 15) { e.target.value = veh.diff; return flash("Diff lock only under 15 km/h", true); }
    veh.diff = want;
  });
  // ---- lights sheet: sliders for every light (docs/lights.md) ----------------------
  // On the Teryx (page served by the Pi) these go to the dash over its websocket, as the same
  // requests the dash's own Lights screen sends. On github.io they only light up the pretend Teryx.
  let dashWs = null;
  const onTeryx = /^https?:$/.test(location.protocol) && !/github\.io$/.test(location.hostname);
  function dashSend(id, value) {
    if (!onTeryx) return;
    if (!dashWs || dashWs.readyState > 1) {
      try { dashWs = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`); } catch (_) { dashWs = null; return; }
    }
    const msg = JSON.stringify({ type: "request", id, value });
    if (dashWs.readyState === 1) dashWs.send(msg);
    else dashWs.addEventListener("open", () => dashWs.send(msg), { once: true });
  }
  const lights = { bars: 0, head: 100, headMode: "off", cabin: 0, rear: 0, trailer: 0, beacon: 0, white: 0 };
  const to255 = (pct) => Math.round((pct / 100) * 255);
  function lightsSend(which) {
    if (which === "bars") ["light.front_1", "light.front_2", "light.front_3", "light.front_4"].forEach((id) => dashSend(id, to255(lights.bars)));
    if (which === "cabin") dashSend("light.interior", to255(lights.cabin));
    if (which === "head") { dashSend("light.head_level", to255(lights.head)); dashSend("light.head", lights.headMode); }
    if (which === "rear") { dashSend("light.rear_level", to255(lights.rear)); dashSend("light.rear", lights.rear ? "on" : "auto"); }
    if (which === "trailer") dashSend("light.trailer_bar", to255(lights.trailer));
    if (which === "beacon") dashSend("light.beacon", to255(lights.beacon));
    if (which === "white") dashSend("light.beacon_white", to255(lights.white));
    veh.lights = lights.bars > 0 || lights.headMode !== "off" || lights.rear > 0;
  }
  document.querySelectorAll("[data-light]").forEach((r) => r.addEventListener("input", () => {
    const k = r.dataset.light;
    lights[k] = +r.value;
    $(`lv-${k}`).textContent = `${r.value}%`;
    lightsSend(k);
  }));
  document.querySelectorAll("[data-head]").forEach((b) => b.addEventListener("click", () => {
    lights.headMode = b.dataset.head;
    document.querySelectorAll("[data-head]").forEach((x) => x.classList.toggle("on", x === b));
    lightsSend("head");
  }));
  $("lights").addEventListener("click", () => ($("lightPanel").hidden = false));
  $("lightClose").addEventListener("click", () => ($("lightPanel").hidden = true));
  $("drop").addEventListener("click", () => {
    veh.signal = !veh.signal;
    $("drop").classList.toggle("on", !veh.signal);
    $("drop").textContent = veh.signal ? "DROP SIGNAL" : "SIGNAL BACK";
  });
  $("dig").addEventListener("click", () => {
    veh.soft = !veh.soft;
    $("dig").classList.toggle("on", veh.soft);
  });
  let cam = "rear";
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => {
    cam = t.dataset.cam;
    document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("on", x === t));
  }));

  let flashMsg = "", flashUntil = 0, flashWarn = false;
  function flash(msg, warn) { flashMsg = msg; flashWarn = warn; flashUntil = performance.now() + 1800; }

  // ---- physics, very rough --------------------------------------------------
  function physics(o, dt) {
    const grip = veh.soft ? (veh.fourwd ? 0.55 + veh.diff / 250 : 0.2) : 1;
    const signed = o.dir * o.thr;
    const target = signed > 0 ? signed * 7 : signed * 4.5;          // wheel speed it heads for, km/h
    let wheel = veh.kmh * (veh.dirMoving || 1);
    wheel += (target - wheel) * Math.min(1, dt * 1.8);
    if (o.brk > 0) wheel -= Math.sign(wheel) * Math.min(Math.abs(wheel), o.brk * 12 * dt);
    if (o.thr === 0 && Math.abs(wheel) < 0.2) wheel = 0;
    veh.dirMoving = wheel >= 0 ? 1 : -1;
    veh.kmh = Math.abs(wheel);
    const groundTarget = Math.abs(wheel) * grip;
    veh.ground += (groundTarget - veh.ground) * Math.min(1, dt * 3);
    if (o.brk > 0.5 && veh.kmh === 0) veh.ground = 0;
    veh.pos -= veh.dirMoving * veh.ground / 3.6 * dt;                // + is further down the beach
    veh.pos = Math.max(0, veh.pos);
    veh.wet = veh.pos > AXLE_AT + 1.5 ? 2 : veh.pos > AXLE_AT ? 1 : 0;
    veh.heading += inp.steer * veh.ground * dt * 0.05 * -veh.dirMoving;
    if (o.winch) veh.winchRope = Math.max(0, Math.min(1, veh.winchRope - o.winch * dt * 0.1));
  }

  // ---- the "camera": a drawn beach, since there's no real camera here ---------
  const cv = $("view"), g = cv.getContext("2d");
  function draw(o) {
    const W = cv.width, H = cv.height;
    const front = cam === "front";
    const sea = front ? 0 : Math.max(0, Math.min(1, (veh.pos - WATER_AT + 6) / 10));
    const sky = g.createLinearGradient(0, 0, 0, H * 0.4);
    sky.addColorStop(0, veh.lights ? "#0b1220" : "#7fb2d8"); sky.addColorStop(1, veh.lights ? "#1d2a3a" : "#cfe3ee");
    g.fillStyle = sky; g.fillRect(0, 0, W, H);
    const horizon = H * 0.38;
    // sea band, closer as you back down
    const seaTop = horizon, seaBottom = horizon + (H - horizon) * (front ? 0.02 : 0.15 + sea * 0.85);
    g.fillStyle = "#2c6f8f"; g.fillRect(0, seaTop, W, seaBottom - seaTop);
    const t = performance.now() / 700;
    g.strokeStyle = "rgba(255,255,255,.55)"; g.lineWidth = 3;
    for (let i = 0; i < 3; i++) {
      const y = seaBottom - 4 - i * 9 + Math.sin(t + i) * 3;
      g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke();
    }
    const sand = g.createLinearGradient(0, seaBottom, 0, H);
    sand.addColorStop(0, sea > 0.6 ? "#8f7b5c" : "#d9c294"); sand.addColorStop(1, "#b89c6a");
    g.fillStyle = sand; g.fillRect(0, seaBottom, W, H - seaBottom);
    // trailer / jet ski in the rear views
    if (!front) {
      const sx = W / 2 + veh.heading * 400;
      g.fillStyle = "#333"; g.fillRect(sx - 130, H - 120, 260, 22);
      g.fillStyle = cam === "trailer" ? "#d84a1b" : "#ececec";
      g.beginPath(); g.ellipse(sx, H - 140, cam === "trailer" ? 170 : 120, 36, 0, 0, Math.PI * 2); g.fill();
    } else {
      g.fillStyle = "#6c8a52"; g.fillRect(0, horizon, W, H * 0.12);
    }
    // guide lines that bend with the steering
    const bend = inp.steer * 120;
    const lines = [["#ff3d2e", 0.92], ["#ffb020", 0.75], ["#8bd65e", 0.58]];
    g.lineWidth = 6;
    lines.forEach(([c, y]) => {
      g.strokeStyle = c;
      const yy = H * y, half = W * (0.12 + (y - 0.5) * 0.45);
      g.beginPath(); g.moveTo(W / 2 - half + bend * (1 - y), yy); g.lineTo(W / 2 + half + bend * (1 - y), yy); g.stroke();
    });
    g.strokeStyle = "rgba(255,255,255,.75)"; g.lineWidth = 4;
    [-1, 1].forEach((s) => {
      g.beginPath(); g.moveTo(W / 2 + s * W * 0.32, H);
      g.quadraticCurveTo(W / 2 + s * W * 0.2 + bend * 0.5, H * 0.75, W / 2 + s * W * 0.1 + bend, H * 0.55); g.stroke();
    });
    // water depth marker on the rear view
    if (!front && veh.wet) {
      g.fillStyle = veh.wet >= 2 ? "rgba(255,61,46,.35)" : "rgba(255,176,32,.25)";
      g.fillRect(0, H - 40, W, 40);
    }
    g.fillStyle = "rgba(0,0,0,.45)"; g.fillRect(W - 210, H - 34, 200, 26);
    g.fillStyle = "#fff"; g.font = "600 16px Inter, sans-serif";
    g.fillText(`${cam.toUpperCase()} CAM  ${(veh.pos).toFixed(1)} m`, W - 200, H - 15);
  }

  // ---- screen ---------------------------------------------------------------
  function render(o) {
    const st = inp.estop ? "estop" : box.state;
    $("state").textContent = { off: "RC OFF", armed: "ARMED", driving: "DRIVING", hold: "HOLD", estop: "E-STOP" }[st] || st;
    $("state").className = "pill " + st;
    $("arm").textContent = box.state === "off" ? "ARM RC" : "RC OFF";
    $("arm").classList.toggle("on", box.state !== "off");
    $("spd").textContent = veh.kmh.toFixed(1);
    $("cap").textContent = `cap ${Math.min(box.dir === F ? S.fwd_cap_kmh : S.rev_cap_kmh, link === "4g" ? S.cap_4g_kmh : 99)} km/h`;
    const ok = veh.signal;
    $("link").textContent = ok ? "GOOD" : "LOST"; $("link").className = ok ? "" : "bad";
    $("water").textContent = ["DRY", "LIMIT", "DEEP"][veh.wet]; $("water").className = ["", "warn", "bad"][veh.wet];
    $("soc").textContent = Math.round(veh.soc) + "%";
    $("fourwd").textContent = veh.fourwd ? "4WD" : "2WD"; $("fourwd").classList.toggle("on", veh.fourwd);
    $("diffv").textContent = veh.diff + "%";
    $("lights").classList.toggle("on", veh.lights);
    document.querySelectorAll(".fnr .key").forEach((b) => b.classList.toggle("on", +b.dataset.dir === box.dir));
    $("thr").style.width = o.thr * 100 + "%"; $("thrv").textContent = Math.round(o.thr * 100) + "%";
    $("brk").style.width = o.brk * 100 + "%"; $("brkv").textContent = Math.round(o.brk * 100) + "%";
    $("str").style.left = 50 + inp.steer * 46 + "%";
    $("winchIn").classList.toggle("on", o.winch === 1);
    $("winchOut").classList.toggle("on", o.winch === -1);
    const b = $("banner");
    let msg = "", warn = false;
    if (performance.now() < flashUntil) { msg = flashMsg; warn = flashWarn; }
    else if (box.state === "hold" && box.reason) {
      msg = box.reason === "deadman" && padOn ? "HOLD L1 TO DRIVE" : WHY[box.reason] || box.reason;
      warn = box.reason === "deadman";
    }
    else if (o.warn) { msg = o.warn; warn = true; }
    else if (box.state === "off") { msg = "PRESS ARM RC TO START"; warn = true; }
    b.textContent = msg; b.className = "banner" + (msg ? " show" : "") + (warn ? " warn" : "");
    document.body.className = document.body.className.replace(/look-\w+/, veh.lights ? "look-night" : veh.fourwd || veh.diff ? "look-offroad" : "look-std");
  }

  let last = performance.now();
  function loop(now) {
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    readInputs();
    if (veh.signal) veh.lastPacket = now / 1000;
    const o = rcTick(now / 1000, dt);
    physics(o, dt);
    draw(o);
    render(o);
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
})();
