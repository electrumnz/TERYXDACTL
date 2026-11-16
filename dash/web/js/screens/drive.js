// Main drive screen: speed, gear, power, battery, temps, and a quick look at the drivetrain and lights.
import { el, $ } from "../ui/controls.js";
import { vehicleDiagram } from "../ui/vehicle.js";
import { sensorWidget } from "../ui/sensors.js";
import { fmtKm } from "../tripdata.js";

export function socFromVolts(v, cells) {
  // Rough lithium curve per cell. Only used if the Shinegle doesn't send a state of charge.
  const pts = [[3.0, 0], [3.3, 5], [3.5, 15], [3.6, 30], [3.7, 50], [3.8, 65], [3.9, 78], [4.0, 88], [4.1, 96], [4.15, 100]];
  const c = v / cells;
  if (c <= pts[0][0]) return 0;
  for (let i = 1; i < pts.length; i++) if (c <= pts[i][0]) {
    const [a, pa] = pts[i - 1], [b, pb] = pts[i];
    return pa + ((c - a) / (b - a)) * (pb - pa);
  }
  return 100;
}

export function tempClass(t, warn, bad) { return t >= bad ? "bad" : t >= warn ? "warn" : "ok"; }

export class DriveScreen {
  constructor(ctx) { this.ctx = ctx; this.id = "drive"; this.label = "Drive"; this.icon = "drive"; }

  mount(root) {
    root.innerHTML = `
      <div class="drive">
        <div class="col">
          <div class="panel">
            <h3>Battery</h3>
            <div class="batt-big"><span class="big-val num" id="d-soc">--</span><span class="unit">%</span></div>
            <div class="batt-bar"><div id="d-socbar"></div></div>
            <div class="kv"><span class="k">Range</span><span class="v num" id="d-range">--</span></div>
            <div class="kv"><span class="k">Pack</span><span class="v num" id="d-v">-- V</span></div>
            <div class="kv"><span class="k">Current</span><span class="v num" id="d-a">-- A</span></div>
            <div class="kv"><span class="k">Pack temp</span><span class="v num" id="d-bt">--</span></div>
            <div class="kv"><span class="k">12V aux</span><span class="v num" id="d-12v">-- V</span></div>
          </div>
          <div class="panel grow">
            <h3>Motor</h3>
            <div class="kv"><span class="k">Motor</span><span class="v num" id="d-mt">--</span></div>
            <div class="temp-bar"><div id="d-mtbar"></div></div>
            <div class="kv"><span class="k">Controller</span><span class="v num" id="d-ct">--</span></div>
            <div class="temp-bar"><div id="d-ctbar"></div></div>
            <div class="kv"><span class="k">Throttle</span><span class="v num" id="d-thr">--</span></div>
            <div class="kv"><span class="k">Mode</span><span class="v" id="d-mode">--</span></div>
            <div class="kv"><span class="k">Odometer</span><span class="v num" id="d-odo">--</span></div>
          </div>
        </div>
        <div class="centre">
          <div class="speed num" id="d-speed">0</div>
          <div class="speed-unit" id="d-unit">KM/H</div>
          <div class="gear-row" id="d-gears"><span data-g="reverse" class="r">R</span><span data-g="neutral">N</span><span data-g="forward" class="d">D</span></div>
          <div class="power-bar">
            <div class="power-track"><div class="power-zero" id="d-zero"></div><div class="power-fill" id="d-pfill"></div></div>
            <div class="power-labels"><span>REGEN</span><span>POWER</span></div>
            <div class="power-kw" id="d-kw">0.0 kW</div>
          </div>
          <div class="row" style="margin-top:18px;gap:10px" id="d-chips"></div>
        </div>
        <div class="col">
          <div class="panel" id="d-veh"><h3>Drivetrain</h3></div>
          <div class="panel grow" id="d-sens"><h3>Tilt and GPS</h3></div>
        </div>
      </div>`;
    this.root = root;
    this.veh = vehicleDiagram();
    this.veh.root.classList.add("small");
    $(root, "#d-veh").appendChild(this.veh.root);
    this.sens = sensorWidget(this.ctx.settings);
    $(root, "#d-sens").appendChild(this.sens.root);
  }

  update(st) {
    const r = this.root, set = this.ctx.settings;
    const q = (s) => $(r, s);
    const mph = set.get("units") === "mph";
    const spd = st.get("mc.speed", 0) * (mph ? 0.621371 : 1);
    const mcOn = st.get("mc.online", true) !== false;
    q("#d-speed").textContent = mcOn ? Math.round(spd) : "--";
    q("#d-unit").textContent = mph ? "MPH" : "KM/H";

    const dir = st.get("mc.direction", "neutral");
    r.querySelectorAll("#d-gears span").forEach((e) => e.classList.toggle("on", e.dataset.g === dir));

    const v = st.get("mc.batt_v", 0), a = st.get("mc.batt_a", 0);
    const kw = st.get("mc.power_kw") ?? (v * a) / 1000;
    const pmax = set.get("powerMaxKw"), rmax = set.get("regenMaxKw");
    const zero = (rmax / (pmax + rmax)) * 100;
    q("#d-zero").style.left = `${zero}%`;
    const fill = q("#d-pfill");
    if (kw >= 0) { fill.style.left = `${zero}%`; fill.style.width = `${Math.min(kw / pmax, 1) * (100 - zero)}%`; fill.style.background = "var(--draw)"; }
    else { const w = Math.min(-kw / rmax, 1) * zero; fill.style.left = `${zero - w}%`; fill.style.width = `${w}%`; fill.style.background = "var(--regen)"; }
    q("#d-kw").textContent = `${kw >= 0 ? "" : "−"}${Math.abs(kw).toFixed(1)} kW`;
    q("#d-kw").className = `power-kw ${kw < -0.05 ? "ok" : ""}`;

    let soc = st.get("mc.soc");
    if (soc == null) soc = socFromVolts(v, set.get("cells"));
    q("#d-soc").textContent = mcOn ? Math.round(soc) : "--";
    const bar = q("#d-socbar");
    bar.style.width = `${soc}%`;
    bar.style.background = soc < 15 ? "var(--bad)" : soc < 30 ? "var(--warn)" : "var(--good)";
    q("#d-v").textContent = `${v.toFixed(1)} V`;
    q("#d-a").textContent = `${a.toFixed(0)} A`;
    const v12 = st.get("an.aux_12v", 0);
    q("#d-12v").textContent = `${v12.toFixed(1)} V`;
    q("#d-12v").className = `v num ${v12 < 11.8 ? "bad" : v12 < 12.2 ? "warn" : ""}`;

    const mt = st.get("mc.motor_temp", 0), ct = st.get("mc.ctrl_temp", 0);
    q("#d-mt").innerHTML = `${Math.round(mt)}°C`; q("#d-mt").className = `v num ${tempClass(mt, 100, 120)}`;
    q("#d-ct").innerHTML = `${Math.round(ct)}°C`; q("#d-ct").className = `v num ${tempClass(ct, 70, 85)}`;
    const tb = (id, t, max, w, b) => { const e = q(id); e.style.width = `${Math.min(100, (t / max) * 100)}%`; e.style.background = `var(--${tempClass(t, w, b) === "ok" ? "good" : tempClass(t, w, b)})`; };
    tb("#d-mtbar", mt, 150, 100, 120); tb("#d-ctbar", ct, 100, 70, 85);

    this.veh.update(st);
    q("#d-thr").textContent = `${Math.round(st.get("mc.throttle", 0))}%`;
    q("#d-mode").textContent = String(st.get("mc.mode", "--")).toUpperCase();
    const odo = st.get("mc.odometer");
    q("#d-odo").textContent = odo == null ? "--" : `${(odo * (mph ? 0.621371 : 1)).toFixed(1)} ${mph ? "mi" : "km"}`;
    const bt = st.get("mc.batt_temp");
    q("#d-bt").textContent = bt == null ? "--" : `${Math.round(bt)}°C`;
    q("#d-bt").className = `v num ${bt == null ? "" : tempClass(bt, 45, 55)}`;

    const chips = [];
    if (st.get("mc.ready") === false) chips.push(`<span class="tb-chip" style="color:var(--warn);border-color:var(--warn)">NOT READY</span>`);
    if (st.get("mc.limp")) chips.push(`<span class="tb-chip" style="color:var(--bad);border-color:var(--bad)">LIMP MODE</span>`);
    const fw = st.get("act.4wd", "2wd");
    chips.push(`<span class="tb-chip ${fw === "4wd" ? "on" : fw.startsWith("to_") ? "busy" : ""}">${fw === "4wd" ? "4WD" : fw === "to_4wd" ? "→ 4WD" : fw === "to_2wd" ? "→ 2WD" : fw === "fault" ? "4WD FAULT" : "2WD"}</span>`);
    const d = Math.round(st.get("an.diff_pos", 0));
    if (d > 2) chips.push(`<span class="tb-chip on">DIFF ${d}%</span>`);
    if (st.get("light.rear")) chips.push(`<span class="tb-chip on">REAR LIGHTS</span>`);
    if (st.get("winch.armed")) chips.push(`<span class="tb-chip" style="color:var(--bad);border-color:var(--bad)">WINCH ARMED</span>`);
    if (st.get("in.brake")) chips.push(`<span class="tb-chip" style="color:var(--bad);border-color:var(--bad)">BRAKE</span>`);
    const html = chips.join("");
    if (html !== this._chips) { q("#d-chips").innerHTML = html; this._chips = html; }

    this.sens.update(st);
    const tr = this.ctx.trips && this.ctx.trips.data;
    const rk = tr && tr.range_km;
    q("#d-range").textContent = rk == null || !mcOn ? "--" : `${tr.basis === "guess" ? "about " : ""}${fmtKm(rk, mph)}`;
    q("#d-range").className = `v num ${rk != null && rk < 5 ? "bad" : rk != null && rk < 15 ? "warn" : ""}`;
  }
}
