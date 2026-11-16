// Basic test screen: shows live state and sends requests, nothing fancy.
const $ = id => document.getElementById(id);
const link = new TeryxLink();
const LIGHTS = ["light.front_1", "light.front_2", "light.front_3", "light.front_4", "light.interior"];
const RELAYS = ["light.rear", "trailer.tail", "trailer.brake", "winch.in", "winch.out", "winch.isolator", "aux.accessory", "power.hold"];
const FAULT_TEXT = {
  over_current: "Motor over current", over_voltage: "Battery voltage too high",
  under_voltage: "Battery voltage too low", motor_over_temp: "Motor too hot",
  controller_over_temp: "Controller too hot", hall_sensor: "Motor position sensor fault",
  throttle: "Throttle fault", comms: "Controller comms fault", battery_over_temp: "Battery too hot",
  precharge: "Precharge fault",
  dash_link: "Control box lost the dash", speed_unknown: "Control box has no speed signal",
  fourwd_timeout: "4WD actuator took too long", fourwd_overcurrent: "4WD actuator over current",
  diff_timeout: "Diff lock actuator took too long", diff_pot_stuck: "Diff lock not moving",
  tray_timeout: "Tray took too long", tray_overcurrent: "Tray over current",
  tray_limit_switch: "Tray limit switch fault", winch_interlock: "Winch remote in use",
  low_12v: "12V supply low", pico_hot: "Control box hot", watchdog_reset: "Control box restarted",
};

// ---- build light controls
const bars = $("bars");
LIGHTS.forEach((id, i) => {
  const d = document.createElement("div");
  d.className = "lb";
  d.innerHTML = `<div>${i < 4 ? "F" + (i + 1) : "INT"}</div><div class="glow" id="g-${i}"></div>
    <input type="range" min="0" max="255" step="5" value="0" id="s-${i}">`;
  bars.appendChild(d);
  d.querySelector("input").addEventListener("input", e => link.request(id, +e.target.value));
});
const relays = $("relays");
RELAYS.forEach(r => { const s = document.createElement("span"); s.id = "r-" + r; s.textContent = r; relays.appendChild(s); });

// ---- controls
$("fourwd").querySelectorAll("button").forEach(b => b.onclick = () => link.request("act.4wd", +b.dataset.v));
$("rear").querySelectorAll("button").forEach(b => b.onclick = () => link.request("light.rear", b.dataset.v));
$("diff").addEventListener("change", e => link.request("act.diff", +e.target.value));
$("effect").addEventListener("change", e => link.request("light.effect", e.target.value));
link.holdButton($("tray-up"), "act.tray", 1);
link.holdButton($("tray-down"), "act.tray", -1);
link.holdButton($("winch-in"), "winch", 1);
link.holdButton($("winch-out"), "winch", -1);
$("winch-arm").onclick = () => link.request("winch.armed", !link.state["winch.armed"]);
$("raw-toggle").onclick = e => { e.preventDefault(); $("raw").classList.toggle("hidden"); };

// ---- helpers
const fmt = (v, d = 0) => (v === undefined || v === null) ? "--" : (+v).toFixed(d);
const pill = (el, on) => { el.classList.toggle("on", !!on); el.classList.toggle("off", !on); };
const width = (el, pct) => el.style.width = Math.max(0, Math.min(100, pct)) + "%";
const tempBar = (bar, t, max) => {
  width(bar, (t / max) * 100);
  bar.style.background = t > max * 0.85 ? "var(--bad)" : t > max * 0.65 ? "var(--warn)" : "var(--ok)";
};
let toastTimer, lastReject = null, editingDiff = false;
$("diff").addEventListener("pointerdown", () => editingDiff = true);
$("diff").addEventListener("pointerup", () => setTimeout(() => editingDiff = false, 600));
function toast(text) {
  const t = $("toast"); t.textContent = text; t.classList.remove("hidden");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.add("hidden"), 3000);
}
link.onConnection(ok => pill($("l-ws"), ok));
link.onError(e => toast(e));

// ---- camera: real device if ?camera=1 (USB or AHD capture stick), else a test pattern
const camParam = new URLSearchParams(location.search).get("camera");
if (camParam && navigator.mediaDevices) {
  navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
    $("cam-video").srcObject = stream; $("cam-video").classList.remove("hidden"); $("cam-canvas").classList.add("hidden");
  }).catch(err => console.warn("camera:", err));
}
function drawCamera(t) {
  const c = $("cam-canvas"), g = c.getContext("2d"), w = c.width, h = c.height;
  g.fillStyle = "#1d2a1d"; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 12; i++) {                       // fake ground texture scrolling
    const y = ((i * 30 + t * 40) % (h + 30)) - 30;
    g.fillStyle = i % 2 ? "#243524" : "#2b3d2b"; g.fillRect(0, y, w, 15);
  }
  g.lineWidth = 4;                                      // guide lines
  [["#3ccf6e", 0.15], ["#ffc23d", 0.45], ["#ff4d4d", 0.75]].forEach(([col, k]) => {
    g.strokeStyle = col; const y = h * (0.35 + k * 0.6), inset = w * (0.3 - k * 0.2);
    g.beginPath(); g.moveTo(inset, y); g.lineTo(w - inset, y); g.stroke();
  });
  g.fillStyle = "#fff"; g.font = "14px sans-serif"; g.fillText("TEST PATTERN (add ?camera=1 for a real camera)", 10, 20);
}

// ---- render state
link.onState(s => {
  pill($("l-mc"), s["mc.online"]); pill($("l-pico"), s["pico.online"]);
  $("scenario").textContent = s["sim.scenario"] ? "SIM: " + s["sim.scenario"] : "";
  $("bus").textContent = "bus " + s["dash.bus"];
  $("clock").textContent = new Date().toLocaleTimeString("en-NZ", { hour: "2-digit", minute: "2-digit" });

  // drive
  $("speed").textContent = s["mc.online"] ? fmt(s["mc.speed"]) : "--";
  $("dir").textContent = { forward: "D", reverse: "R", neutral: "N" }[s["mc.direction"]] || "-";
  $("mode").textContent = (s["mc.mode"] || "--").toUpperCase();
  $("ready").classList.toggle("bad", !s["mc.ready"]);
  $("ready").textContent = s["mc.ready"] ? "READY" : "NOT READY";
  $("limp").classList.toggle("hidden", !s["mc.limp"]);
  const kw = (s["mc.batt_v"] || 0) * (s["mc.batt_a"] || 0) / 1000;
  $("power").textContent = fmt(kw, 1) + " kW";
  const pb = $("powbar");                         // scale: -5 kW .. +15 kW, zero at 25 %
  if (kw >= 0) { pb.style.left = "25%"; width(pb, kw / 15 * 75); }
  else { const w = Math.min(25, -kw / 5 * 25); pb.style.left = (25 - w) + "%"; pb.style.width = w + "%"; }

  // battery
  $("soc").textContent = fmt(s["mc.soc"]);
  width($("socbar"), s["mc.soc"] || 0);
  $("socbar").style.background = s["mc.soc"] < 15 ? "var(--bad)" : s["mc.soc"] < 30 ? "var(--warn)" : "var(--ok)";
  $("volt").textContent = fmt(s["mc.batt_v"], 1) + " V";
  $("amps").textContent = fmt(s["mc.batt_a"], 1) + " A";
  $("aux").textContent = fmt(s["an.aux_12v"], 2) + " V";
  $("odo").textContent = fmt(s["mc.odometer"], 1) + " km";

  // temps
  $("tmotor").textContent = fmt(s["mc.motor_temp"]) + "°"; tempBar($("tmotor-bar"), s["mc.motor_temp"] || 0, 150);
  $("tctrl").textContent = fmt(s["mc.ctrl_temp"]) + "°"; tempBar($("tctrl-bar"), s["mc.ctrl_temp"] || 0, 100);
  $("tbatt").textContent = fmt(s["mc.batt_temp"]) + "°"; tempBar($("tbatt-bar"), s["mc.batt_temp"] || 0, 65);

  // faults
  const faults = [...(s["mc.faults"] || []).map(f => [f, ""]), ...(s["pico.faults"] || []).map(f => [f, "pico"])];
  if (!s["mc.online"]) faults.unshift(["Motor controller offline", ""]);
  if (!s["pico.online"]) faults.unshift(["Control box offline", "pico"]);
  $("faults").innerHTML = faults.length
    ? faults.map(([f, c]) => `<li class="${c}">${FAULT_TEXT[f] || f}</li>`).join("")
    : `<li class="ok">All good</li>`;

  // drivetrain
  const fw = s["act.4wd"] || "--";
  $("fourwd").querySelectorAll("button").forEach(b => b.classList.toggle("on", +b.dataset.v === s["req.act.4wd"]));
  $("fourwd-state").textContent = "Actual: " + fw.toUpperCase().replace("_", " ") + "  ·  " + fmt(s["an.4wd_current"], 1) + " A";
  $("diff-val").textContent = fmt(s["an.diff_pos"]) + "%";
  width($("diff-bar"), s["an.diff_pos"] || 0);
  $("diff-target").style.left = (s["act.diff_target"] || 0) + "%";
  if (!editingDiff) $("diff").value = s["req.act.diff"] ?? 0;

  // tray + winch
  $("tray-state").textContent = (s["act.tray"] || "--").toUpperCase() + " " + fmt(s["act.tray_pct"]) + "%";
  $("tray-fill").style.height = (s["act.tray_pct"] || 0) + "%";
  $("winch-arm").classList.toggle("on", !!s["winch.armed"]);
  $("winch-arm").textContent = s["winch.armed"] ? "ARMED" : "ARM";
  $("winch-state").textContent = s["winch.in"] ? "IN" : s["winch.out"] ? "OUT" : s["winch.armed"] ? "ARMED" : "OFF";

  // lights
  LIGHTS.forEach((id, i) => {
    const lvl = s[id] || 0, g = $("g-" + i);
    g.style.background = lvl ? `rgba(255,240,200,${0.25 + lvl / 340})` : "#222";
    g.style.boxShadow = lvl ? `0 0 ${lvl / 12}px rgba(255,240,200,.8)` : "none";
    const sl = $("s-" + i);
    if (document.activeElement !== sl) sl.value = s["req." + id] ?? 0;
  });
  if (document.activeElement !== $("effect")) $("effect").value = s["req.light.effect"] || "none";
  $("rear").querySelectorAll("button").forEach(b => b.classList.toggle("on", b.dataset.v === s["req.light.rear"]));
  RELAYS.forEach(r => $("r-" + r).classList.toggle("on", !!s[r]));

  // camera in reverse (or when the rear pods are on)
  $("camera").classList.toggle("hidden", !s["in.reverse"]);

  // refused requests
  if (lastReject !== null && s["pico.reject_count"] !== lastReject && s["pico.reject"] !== "none")
    toast("Refused: " + (s["pico.reject_text"] || s["pico.reject"]));
  lastReject = s["pico.reject_count"];

  if (!$("raw").classList.contains("hidden")) $("raw").textContent = JSON.stringify(s, null, 1);
});

(function loop(t) { if (!$("camera").classList.contains("hidden")) drawCamera(t / 1000); requestAnimationFrame(loop); })(0);
