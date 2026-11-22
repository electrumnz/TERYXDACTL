// Main drive screen: speed, gear, power, battery, temps, and a quick look at the drivetrain and lights.
import { el, $ } from "../ui/controls.js";
import { vehicleDiagram } from "../ui/vehicle.js";
import { sensorWidget } from "../ui/sensors.js";
import { fmtKm } from "../tripdata.js";
import { featureOn } from "../features.js";
import { icon } from "../ui/icons.js";
import { TellTales } from "../telltales.js";
import { regenOn } from "../regen.js";

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

// Three claw gouges for the power meter, in a 300 x 64 box. They fill left to right.
const GOUGES = [0, 1, 2].map((i) => {
  const x = 14 + i * 96;
  return `M${x} 60 C${x + 22} 46 ${x + 52} 22 ${x + 84} 3 C${x + 66} 24 ${x + 38} 48 ${x + 12} 63 Z`;
}).join(" ");

export class DriveScreen {
  constructor(ctx) { this.ctx = ctx; this.id = "drive"; this.label = "Drive"; this.icon = "drive"; }

  mount(root) {
    root.innerHTML = `
      <div class="drive2">
        <div class="d-left">
          <div class="panel d-speed">
            <span class="lbl">SPEED</span>
            <div class="spd"><span class="speed num" id="d-speed">0</span><span class="speed-unit" id="d-unit">km/h</span></div>
            <div class="gear-row" id="d-gears"><span data-g="reverse" class="r">R</span><span data-g="neutral">N</span><span data-g="forward" class="d">D</span></div>
          </div>
          <div class="panel d-power">
            <span class="lbl">POWER</span>
            <svg class="claws" id="d-claws" viewBox="0 0 300 64" preserveAspectRatio="none">
              <defs>
                <linearGradient id="lava" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#b8260a"/><stop offset=".5" stop-color="#ff7a1a"/><stop offset="1" stop-color="#ffd27a"/></linearGradient>
                <clipPath id="d-pclip"><rect id="d-prect" x="0" y="0" width="0" height="64"/></clipPath>
              </defs>
              <path class="gouge" d="${GOUGES}"/>
              <path class="lava" d="${GOUGES}" clip-path="url(#d-pclip)"/>
            </svg>
            <div class="power-kw num" id="d-kw">0.0 kW</div>
          </div>
          <div class="panel d-batt" id="d-batt" role="button" aria-label="Battery: tap to swap % and km">
            <span class="lbl">BATTERY</span>
            <div class="fangs"><img class="dead" src="img/dino/teeth.webp" alt=""><img class="lit" src="img/dino/teeth.webp" alt=""></div>
            <div class="bnum"><div class="bmain num" id="d-bmain">--</div><div class="bsub num" id="d-bsub">--</div></div>
          </div>
        </div>
        <div class="d-hero">
          <div class="d-tells" id="d-tells" aria-label="Warning lights"></div>
          <div class="art rex"><div class="breathe">
            <img data-j="closed" src="img/dino/head-closed.webp" alt="">
            <img data-j="snarl" src="img/dino/head-snarl.webp" alt="" style="opacity:0">
            <img data-j="roar" src="img/dino/head-roar.webp" alt="" style="opacity:0">
          </div></div>
          <div class="art fossil"><img src="img/dino/fossil.webp" alt=""></div>
          <div class="d-chips" id="d-chips"></div>
        </div>
        <div class="d-stats">
          <div class="panel">
            <h3>Battery</h3>
            <div class="kv"><span class="k">Pack</span><span class="v num" id="d-v">-- V</span></div>
            <div class="kv"><span class="k">Current</span><span class="v num" id="d-a">-- A</span></div>
            <div class="kv"><span class="k">Pack temp</span><span class="v num" id="d-bt">--</span></div>
            <div class="kv"><span class="k">12V aux</span><span class="v num" id="d-12v">-- V</span></div>
            <div class="kv" hidden><span class="k">Charge</span><span class="v num" id="d-soc">--</span><span id="d-range"></span></div>
          </div>
          <div class="panel">
            <h3>Motor</h3>
            <div class="kv"><span class="k">Motor</span><span class="v num" id="d-mt">--</span></div>
            <div class="temp-bar"><div id="d-mtbar"></div></div>
            <div class="kv"><span class="k">Controller</span><span class="v num" id="d-ct">--</span></div>
            <div class="temp-bar"><div id="d-ctbar"></div></div>
            <div class="kv"><span class="k">Throttle · Mode</span><span class="v num"><span id="d-thr">--</span> · <span id="d-mode">--</span></span></div>
            <div class="kv"><span class="k">Odometer</span><span class="v num" id="d-odo">--</span></div>
          </div>
          <div class="panel" id="d-veh"><h3>Drivetrain</h3></div>
          <div class="panel" id="d-sens"><h3>Tilt and GPS</h3></div>
        </div>
      </div>`;
    this.root = root;
    this.veh = vehicleDiagram();
    this.veh.root.classList.add("small");
    $(root, "#d-veh").appendChild(this.veh.root);
    this.sens = sensorWidget(this.ctx.settings);
    $(root, "#d-sens").appendChild(this.sens.root);
    this.jaws = [...root.querySelectorAll(".rex img")];
    $(root, "#d-batt").onclick = () => {
      const set = this.ctx.settings;
      set.set("batteryShow", set.get("batteryShow") === "km" ? "pct" : "km");
      this.update(this.ctx.store);
    };
  }

  update(st) {
    const r = this.root, set = this.ctx.settings;
    const q = (s) => $(r, s);
    const mph = set.get("units") === "mph";
    const spd = st.get("mc.speed", 0) * (mph ? 0.621371 : 1);
    const mcOn = st.get("mc.online", true) !== false;
    q("#d-speed").textContent = mcOn ? Math.round(spd) : "--";
    q("#d-unit").textContent = mph ? "mph" : "km/h";

    const dir = st.get("mc.direction", "neutral");
    r.querySelectorAll("#d-gears span").forEach((e) => e.classList.toggle("on", e.dataset.g === dir));

    // Power: the claws fill with power. Regen is just on or off (the Shinegle decides how
    // much): the battery teeth glow green and pulse while it's putting charge back.
    const v = st.get("mc.batt_v", 0), a = st.get("mc.batt_a", 0);
    const kw = st.get("mc.power_kw") ?? (v * a) / 1000;
    const pmax = set.get("powerMaxKw");
    const regen = regenOn(st, set.get("regenFrom"));
    q("#d-prect").setAttribute("width", (regen ? 0 : Math.max(0, Math.min(kw / pmax, 1)) * 300).toFixed(1));
    q("#d-kw").textContent = regen ? "REGEN" : `${Math.max(0, kw).toFixed(1)} kW`;
    q("#d-kw").className = `power-kw num ${regen ? "ok" : ""}`;
    q("#d-batt").classList.toggle("regen", regen);

    // The T. rex opens its jaw as you put the power down.
    const p = kw > 0 ? Math.min(kw / pmax, 1) : 0;
    const clamp = (x) => Math.max(0, Math.min(1, x));
    const snarl = clamp((p - 0.2) / 0.25), roar = clamp((p - 0.6) / 0.25);
    // Cross-fade so only one head shows once a change is done. The head pictures are
    // see-through round the jaw, so a head left at full strength underneath shows through the open mouth.
    const want = [1 - snarl, snarl * (1 - roar), roar];
    this.jaws.forEach((j, i) => { const o = +want[i].toFixed(3); if (j._o !== o) { j.style.opacity = o; j._o = o; } });

    // Battery: fangs lit to the charge level. % and km, tap to swap which is big.
    let soc = st.get("mc.soc");
    if (soc == null) soc = socFromVolts(v, set.get("cells"));
    const tr = this.ctx.trips && this.ctx.trips.data;
    const rk = tr && tr.range_km;
    const pctTxt = mcOn ? `${Math.round(soc)}%` : "--%";
    const kmTxt = rk == null || !mcOn ? "-- km" : `${tr.basis === "guess" ? "~" : ""}${fmtKm(rk, mph)}`;
    const kmFirst = set.get("batteryShow") === "km";
    const socCls = soc < 15 ? "bad" : soc < 30 ? "warn" : "";
    const kmCls = rk != null && rk < 5 ? "bad" : rk != null && rk < 15 ? "warn" : "";
    q("#d-bmain").textContent = kmFirst ? kmTxt : pctTxt;
    q("#d-bsub").textContent = kmFirst ? pctTxt : kmTxt;
    q("#d-bmain").className = `bmain num ${kmFirst ? kmCls : socCls}`;
    q("#d-bsub").className = `bsub num ${kmFirst ? socCls : kmCls}`;
    q("#d-batt").style.setProperty("--soc", `${Math.max(0, Math.min(100, soc))}%`);
    q("#d-batt").classList.toggle("low", soc < 15);
    q("#d-soc").textContent = mcOn ? Math.round(soc) : "--";
    q("#d-range").textContent = kmTxt;

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

    // What's on right now, as big shortcuts: tap one to jump to its screen.
    const on = (id) => featureOn(set, id);
    // Warning lights: lamps from the same alert list the banner uses.
    this.tells = this.tells || new TellTales();
    const keys = new Set((this.ctx.alerts?.active || []).map((a) => a.key));
    const lamps = this.tells.render(this.tells.tick(st, set, keys));
    if (lamps !== this._lamps) { q("#d-tells").innerHTML = lamps; this._lamps = lamps; }

    const chips = [];
    const chip = (screen, cls, ic, txt) => chips.push(`<button class="act-chip ${cls}" data-go="${screen || ""}">${ic ? icon(ic) : ""}<span>${txt}</span></button>`);
    // Ready, handbrake, limp etc are warning lights now (telltales.js), so no chips for them.
    const fw = st.get("act.4wd", "2wd");
    const w4 = st.get("act.4wd_wait");
    if (fw !== "2wd" || w4) chip("drivetrain", fw === "4wd" && !w4 ? "on" : fw === "fault" ? "alert" : "busy", "fourwd", w4 ? (fw === "4wd" ? "2WD when stopped" : "4WD when stopped") : fw === "4wd" ? "4WD" : fw === "to_4wd" ? "→ 4WD" : fw === "to_2wd" ? "→ 2WD" : "4WD fault");
    const d = Math.round(st.get("an.diff_pos", 0));
    if (d > 2) chip("drivetrain", "on", "lock", `Diff ${d}%`);
    if (on("lights")) {
      let bars = 0; for (let i = 1; i <= 4; i++) if (st.get(`light.front_${i}`, 0) > 0) bars++;
      if (bars) chip("lights", "on", "lights", `${bars === 4 ? "All bars" : `${bars} bar${bars > 1 ? "s" : ""}`} on`);
      if (st.get("light.interior", 0) > 0) chip("lights", "on", "lights", "Cab light");
      if (st.get("light.rear")) chip("lights", "on", "lights", "Rear lights");
    }
    if (on("winch")) {
      if (st.get("winch.in") || st.get("winch.out")) chip("winch", "alert", "winch", `Winch ${st.get("winch.in") ? "in" : "out"}`);
      else if (st.get("winch.armed")) chip("winch", "alert", "winch", "Winch armed");
    }
    if (on("tray")) {
      const tray = st.get("act.tray", "down");
      if (tray !== "down") chip("tray", "on", "tray", tray === "up" ? "Tray up" : `Tray ${Math.round(st.get("act.tray_pct", 0))}%`);
    }
    if (on("media") && this.ctx.media) {
      const np = this.ctx.media.nowPlaying();
      if (np.title && np.playing) chip("media", "on", "music", np.title.replace(/</g, "&lt;").slice(0, 28));
    }
    const html = chips.join("");
    if (html !== this._chips) {
      q("#d-chips").innerHTML = html; this._chips = html;
      q("#d-chips").querySelectorAll("[data-go]").forEach((b) => { if (b.dataset.go) b.onclick = () => this.ctx.show(b.dataset.go); });
    }

    this.sens.update(st);
  }
}
