// Main drive screen. Each look has its own layout, built from the three mock-ups made at the
// start (project files dash-dino/img/trex-art/mockups):
//
//   Predator   (std)      big speed slab, claw-mark power, a row of fangs for the battery,
//                         and the T. rex head filling the right half (its jaw opens with power).
//   Fossil     (offroad)  a T. rex skull in rock, a round speedo ringed with vertebrae, and stone
//                         cards down the right: battery + range, motor power, 4WD + diff lock, tilt.
//   Night Hunt (night)    the Teryx from above between T. rex footprints in the mud, speed in a notch
//                         at the top, tall claw power meter on the left, one big tooth for the battery
//                         on the right, and a readout by each wheel.
//
// Auto picks one of the three (look.js). The layout is rebuilt when the look changes.
// The warning lights and the "what's on" shortcut buttons show in every look.
import { $ } from "../ui/controls.js";
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

// Right-hand edge of each of the ten fangs in img/dino/teeth.webp, as a share of its width.
// The battery lights whole teeth, never half a tooth: 85% lights 9 of 10.
export const TOOTH_EDGES = [117, 240, 357, 470, 591, 706, 824, 945, 1062, 1200].map((x) => x / 1200);
export function teethLit(soc) { return soc <= 0 ? 0 : Math.min(10, Math.ceil(soc / 10)); }

const clamp01 = (x) => Math.max(0, Math.min(1, x));

// Three claw gouges, Predator power meter: 300 x 64 box, they fill left to right.
const GOUGES = [0, 1, 2].map((i) => {
  const x = 14 + i * 96;
  return `M${x} 60 C${x + 22} 46 ${x + 52} 22 ${x + 84} 3 C${x + 66} 24 ${x + 38} 48 ${x + 12} 63 Z`;
}).join(" ");
// Three tall gouges, Night Hunt power meter: 140 x 420 box, they fill bottom to top.
const GOUGES_TALL = [0, 1, 2].map((i) => {
  const x = 16 + i * 38;
  return `M${x} 410 C${x - 6} 300 ${x + 4} 150 ${x + 36} 8 C${x + 30} 140 ${x + 30} 290 ${x + 24} 414 Z`;
}).join(" ");

// Fossil speedo: 0 sits bottom-left, top speed bottom-right, 270 degrees between.
const DIAL_A0 = -135, DIAL_SWEEP = 270, DIAL_R = 176;
const polar = (deg, r) => { const a = (deg - 90) * Math.PI / 180; return [r * Math.cos(a), r * Math.sin(a)]; };
function arcPath(r, a0, a1) {
  const [x0, y0] = polar(a0, r), [x1, y1] = polar(a1, r);
  return `M${x0.toFixed(1)} ${y0.toFixed(1)} A${r} ${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1.toFixed(1)} ${y1.toFixed(1)}`;
}
function dialFace(max) {
  const step = max > 60 ? 10 : 5, minor = step / 2;
  let ticks = "", nums = "";
  for (let v = 0; v <= max + 0.001; v += minor) {
    const a = DIAL_A0 + (v / max) * DIAL_SWEEP, major = Math.abs(v / step - Math.round(v / step)) < 1e-6;
    const [x0, y0] = polar(a, major ? DIAL_R - 22 : DIAL_R - 12), [x1, y1] = polar(a, DIAL_R);
    ticks += `<line class="${major ? "mj" : "mn"}" x1="${x0.toFixed(1)}" y1="${y0.toFixed(1)}" x2="${x1.toFixed(1)}" y2="${y1.toFixed(1)}"/>`;
    if (major) { const [tx, ty] = polar(a, DIAL_R - 46); nums += `<text x="${tx.toFixed(1)}" y="${(ty + 9).toFixed(1)}">${Math.round(v)}</text>`; }
  }
  return { ticks, nums };
}

// ---------------------------------------------------------------- the three layouts
const TELLS = `<div class="d-tells" id="d-tells" aria-label="Warning lights"></div>`;
const CHIPS = `<div class="d-chips" id="d-chips"></div>`;
// Kept in every look for anything that reads them (tests, the demo player).
const HIDDEN = `<span hidden id="d-soc"></span><span hidden id="d-range"></span>`;

function predatorHTML() {
  return `
  <div class="dv pv">
    <div class="pv-left">
      <div class="panel pv-speed">
        <span class="lbl">SPEED</span>
        <div class="spd"><span class="speed num" id="d-speed">0</span><span class="speed-unit" id="d-unit">km/h</span></div>
      </div>
      <div class="panel pv-power">
        <span class="lbl">POWER</span>
        <svg class="claws" viewBox="0 0 300 64" preserveAspectRatio="none">
          <defs>
            <linearGradient id="lava" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#b8260a"/><stop offset=".5" stop-color="#ff7a1a"/><stop offset="1" stop-color="#ffd27a"/></linearGradient>
            <clipPath id="d-pclip"><rect id="d-prect" x="0" y="0" width="0" height="64"/></clipPath>
          </defs>
          <path class="gouge" d="${GOUGES}"/>
          <path class="lava" d="${GOUGES}" clip-path="url(#d-pclip)"/>
        </svg>
        <div class="power-kw num" id="d-kw">0.0 kW</div>
      </div>
      <div class="panel pv-batt" data-batt role="button" aria-label="Battery: tap to swap % and km">
        <span class="lbl">${icon("bolt")}BATTERY</span>
        <div class="fangs"><img class="dead" src="img/dino/teeth.webp" alt=""><img class="lit" id="d-teeth" src="img/dino/teeth-lit.webp" alt=""></div>
        <div class="bnum"><div class="bmain num" id="d-bmain">--</div><div class="bsub num" id="d-bsub">--</div></div>
      </div>
    </div>
    <div class="pv-hero">
      <div class="rex"><div class="breathe">
        <img data-j="closed" src="img/dino/head-closed.webp" alt="">
        <img data-j="snarl" src="img/dino/head-snarl.webp" alt="" style="opacity:0">
        <img data-j="roar" src="img/dino/head-roar.webp" alt="" style="opacity:0">
      </div></div>
      ${TELLS}${CHIPS}
    </div>
    ${HIDDEN}
  </div>`;
}

function fossilHTML(max, unit) {
  const f = dialFace(max);
  return `
  <div class="dv fv">
    <div class="fv-art"><img src="img/dino/fossil-dial.webp" alt=""></div>
    <svg class="fv-dial" viewBox="-200 -200 400 400" aria-hidden="true">
      <defs>
        <radialGradient id="fv-face" cx="0" cy="0" r="1"><stop offset="0" stop-color="rgba(20,14,9,.35)"/><stop offset="1" stop-color="rgba(10,7,4,.7)"/></radialGradient>
        <linearGradient id="fv-ndl" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#b8520c"/><stop offset="1" stop-color="#ffc46a"/></linearGradient>
      </defs>
      <circle r="196" fill="url(#fv-face)"/>
      <path class="track" d="${arcPath(DIAL_R + 6, DIAL_A0, DIAL_A0 + DIAL_SWEEP)}"/>
      <path class="lit" id="fv-arc" d="${arcPath(DIAL_R + 6, DIAL_A0, DIAL_A0 + 0.01)}"/>
      <g class="ticks">${f.ticks}</g>
      <g class="nums">${f.nums}</g>
      <g id="fv-needle" class="needle"><path d="M-5 14 L-2.2 -168 L0 -176 L2.2 -168 L5 14 Z" fill="url(#fv-ndl)"/></g>
      <circle class="hub" r="15"/>
      <text class="spd num" id="d-speed" x="0" y="104">0</text>
      <text class="unit" id="d-unit" x="0" y="140">${unit}</text>
    </svg>
    <div class="fv-cards">
      <div class="panel stone fv-batt" data-batt role="button" aria-label="Battery: tap to swap % and km">
        <div class="fv-cell"><div class="batt-ico"><i id="fv-cells"></i></div></div>
        <div class="fv-cell"><span class="lbl" id="fv-blbl">BATTERY</span><span class="val num" id="d-bmain">--</span></div>
        <div class="fv-cell sep"><span class="lbl" id="fv-slbl">RANGE</span><span class="val num acc" id="d-bsub">--</span></div>
      </div>
      <div class="panel stone fv-motor">
        <div class="fv-cell">${icon("bolt", "big-ico")}</div>
        <div class="fv-cell grow"><span class="lbl">MOTOR POWER</span><span class="val num acc" id="d-kw">0.0 kW</span></div>
        <div class="fv-cell sep"><span class="lbl">MOTOR</span><span class="val small num" id="fv-mt">--</span></div>
      </div>
      <button class="panel stone fv-drive" data-go="drivetrain" aria-label="4WD and diff lock: open the 4WD screen">
        <div class="fv-cell">${icon("fourwd", "big-ico")}</div>
        <div class="fv-cell grow">
          <div class="fv-row"><span class="lbl">DRIVE MODE</span><span class="lbl">DIFF LOCK</span></div>
          <div class="fv-row"><span class="val num acc" id="fv-4wd">2WD</span><span class="val num acc" id="fv-diff">0%</span></div>
          <div class="fv-slide"><i id="fv-dbar"></i><b id="fv-dknob"></b></div>
        </div>
      </button>
      <div class="panel stone fv-tilt">
        <div class="fv-tilt-top"><span class="lbl">${icon("tilt")}INCLINOMETER</span><span class="val num acc" id="fv-pitch">--</span></div>
        <div class="fv-tilt-pic"><i class="ground"></i><img id="fv-buggy" src="img/dino/buggy-side.webp" alt=""></div>
        <div class="fv-tilt-roll"><span class="lbl">SIDE TO SIDE</span><span class="val small num" id="fv-roll">--</span></div>
      </div>
    </div>
    ${TELLS}${CHIPS}
    ${HIDDEN}
  </div>`;
}

function nightHTML() {
  const call = (id, side, lbl) => `<div class="nv-call ${side}" id="nv-${id}"><span class="lbl">${lbl}</span><span class="val num" id="nv-${id}-v">--</span></div>`;
  return `
  <div class="dv nv">
    <div class="nv-art"><img src="img/dino/nighthunt.webp" alt=""><i class="nv-beams" id="nv-beams"></i>
      <i class="nv-wheel fl" id="nv-wfl"></i><i class="nv-wheel fr" id="nv-wfr"></i><i class="nv-wheel rl" id="nv-wrl"></i><i class="nv-wheel rr" id="nv-wrr"></i>
    </div>
    <div class="nv-speed"><span class="speed num" id="d-speed">0</span><span class="speed-unit" id="d-unit">km/h</span></div>
    <div class="panel nv-side nv-power">
      <span class="lbl">POWER</span>
      <svg class="claws-tall" viewBox="0 0 140 420" preserveAspectRatio="none">
        <defs>
          <linearGradient id="lava-v" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#9a1e06"/><stop offset=".55" stop-color="#ff6a12"/><stop offset="1" stop-color="#ffd27a"/></linearGradient>
          <clipPath id="nv-pclip"><rect id="nv-prect" x="0" y="420" width="140" height="0"/></clipPath>
        </defs>
        <path class="gouge" d="${GOUGES_TALL}"/>
        <path class="lava" d="${GOUGES_TALL}" clip-path="url(#nv-pclip)"/>
      </svg>
      <div class="nv-num"><span class="big num" id="d-kw">0.0 kW</span><span class="sub num" id="nv-ppct">0%</span></div>
    </div>
    <div class="panel nv-side nv-batt" data-batt role="button" aria-label="Battery: tap to swap % and km">
      <span class="lbl">BATTERY</span>
      <div class="tooth"><img class="dead" src="img/dino/tooth.webp" alt=""><img class="lit" id="nv-tooth" src="img/dino/tooth.webp" alt=""></div>
      <div class="nv-num"><span class="big num" id="d-bmain">--</span><span class="sub num" id="d-bsub">--</span></div>
    </div>
    ${call("fl", "left top", "FRONT DRIVE")}${call("fr", "right top", "DIFF LOCK")}
    ${call("rl", "left bot", "MOTOR")}${call("rr", "right bot", "CONTROLLER")}
    ${TELLS}${CHIPS}
    ${HIDDEN}
  </div>`;
}

export class DriveScreen {
  constructor(ctx) { this.ctx = ctx; this.id = "drive"; this.label = "Drive"; this.icon = "drive"; }

  mount(root) {
    this.root = root;
    this.look = null;
    this.tells = new TellTales();
  }

  currentLook() {
    const c = document.body.classList;
    return c.contains("look-offroad") ? "offroad" : c.contains("look-night") ? "night" : "std";
  }

  build(look) {
    const set = this.ctx.settings, mph = set.get("units") === "mph";
    this.look = look; this.mph = mph;
    this.root.innerHTML = look === "offroad" ? fossilHTML(mph ? 50 : 80, mph ? "mph" : "km/h")
      : look === "night" ? nightHTML() : predatorHTML();
    this._lamps = this._chips = null;
    this.jaws = [...this.root.querySelectorAll(".rex img")];
    this.root.querySelectorAll("[data-batt]").forEach((b) => b.onclick = () => {
      set.set("batteryShow", set.get("batteryShow") === "km" ? "pct" : "km");
      this.update(this.ctx.store);
    });
    this.root.querySelectorAll(".dv > [data-go], .fv-cards [data-go]").forEach((b) => b.onclick = () => this.ctx.show(b.dataset.go));
  }

  // Everything the three layouts show, worked out once.
  model(st) {
    const set = this.ctx.settings;
    const mph = set.get("units") === "mph";
    const v = st.get("mc.batt_v", 0), a = st.get("mc.batt_a", 0);
    const kw = st.get("mc.power_kw") ?? (v * a) / 1000;
    const pmax = set.get("powerMaxKw");
    const mcOn = st.get("mc.online", true) !== false;
    let soc = st.get("mc.soc");
    if (soc == null) soc = socFromVolts(v, set.get("cells"));
    soc = Math.max(0, Math.min(100, soc));
    const tr = this.ctx.trips && this.ctx.trips.data;
    const rk = tr && tr.range_km;
    return {
      mph, mcOn, v, a, kw, pmax,
      spd: st.get("mc.speed", 0) * (mph ? 0.621371 : 1),
      p: kw > 0 ? clamp01(kw / pmax) : 0,
      regen: regenOn(st, set.get("regenFrom")),
      soc, rk,
      pctTxt: mcOn ? `${Math.round(soc)}%` : "--%",
      kmTxt: rk == null || !mcOn ? "-- km" : `${tr.basis === "guess" ? "~" : ""}${fmtKm(rk, mph)}`,
      kmFirst: set.get("batteryShow") === "km",
      socCls: soc < 15 ? "bad" : soc < 30 ? "warn" : "",
      kmCls: rk != null && rk < 5 ? "bad" : rk != null && rk < 15 ? "warn" : "",
      fw: st.get("act.4wd", "2wd"), w4: st.get("act.4wd_wait"),
      diff: Math.round(st.get("an.diff_pos", 0)),
      mt: st.get("mc.motor_temp", 0), ct: st.get("mc.ctrl_temp", 0),
      pitch: st.get("pi.imu.pitch"), roll: st.get("pi.imu.roll"),
    };
  }

  update(st) {
    const look = this.currentLook();
    const mph = this.ctx.settings.get("units") === "mph";
    if (look !== this.look || mph !== this.mph) this.build(look);
    const r = this.root, q = (s) => $(r, s);
    const m = this.model(st);

    // ---- shared by every look
    q("#d-speed").textContent = m.mcOn ? Math.round(m.spd) : "--";
    if (look !== "offroad") q("#d-unit").textContent = m.mph ? "mph" : "km/h";
    const kwEl = q("#d-kw");
    kwEl.textContent = m.regen ? "REGEN" : `${Math.max(0, m.kw).toFixed(1)} kW`;
    kwEl.classList.toggle("ok", m.regen);
    const main = q("#d-bmain"), sub = q("#d-bsub");
    main.textContent = m.kmFirst ? m.kmTxt : m.pctTxt;
    sub.textContent = m.kmFirst ? m.pctTxt : m.kmTxt;
    main.classList.remove("warn", "bad"); sub.classList.remove("warn", "bad");
    const mc = m.kmFirst ? m.kmCls : m.socCls, sc = m.kmFirst ? m.socCls : m.kmCls;
    if (mc) main.classList.add(mc);
    if (sc) sub.classList.add(sc);
    const batt = q("[data-batt]");
    batt.classList.toggle("regen", m.regen);
    batt.classList.toggle("low", m.soc < 15);
    q("#d-soc").textContent = m.mcOn ? Math.round(m.soc) : "--";
    q("#d-range").textContent = m.kmTxt;

    if (look === "std") this.updPredator(m, q);
    else if (look === "offroad") this.updFossil(m, q);
    else this.updNight(m, q);

    // Warning lights: lamps from the same alert list the banner uses.
    const keys = new Set((this.ctx.alerts?.active || []).map((x) => x.key));
    const lamps = this.tells.render(this.tells.tick(st, this.ctx.settings, keys));
    if (lamps !== this._lamps) { q("#d-tells").innerHTML = lamps; this._lamps = lamps; }
    this.chips(st, m, q);
  }

  updPredator(m, q) {
    q("#d-prect").setAttribute("width", (m.regen ? 0 : m.p * 300).toFixed(1));
    // The T. rex opens its jaw as you put the power down. Cross-fade so only one head shows once
    // a change is done: the pictures are see-through round the jaw.
    const snarl = clamp01((m.p - 0.2) / 0.25), roar = clamp01((m.p - 0.6) / 0.25);
    const want = [1 - snarl, snarl * (1 - roar), roar];
    this.jaws.forEach((j, i) => { const o = +want[i].toFixed(3); if (j._o !== o) { j.style.opacity = o; j._o = o; } });
    // Whole teeth light up, and only the teeth (the gum stays as it is).
    const n = teethLit(m.mcOn ? m.soc : 0);
    q("#d-teeth").style.clipPath = `inset(0 ${n ? (100 - TOOTH_EDGES[n - 1] * 100).toFixed(2) : 100}% 0 0)`;
  }

  updFossil(m, q) {
    const max = m.mph ? 50 : 80;
    const a = DIAL_A0 + clamp01((m.mcOn ? m.spd : 0) / max) * DIAL_SWEEP;
    q("#fv-needle").setAttribute("transform", `rotate(${a.toFixed(1)})`);
    q("#fv-arc").setAttribute("d", arcPath(DIAL_R + 6, DIAL_A0, Math.max(DIAL_A0 + 0.01, a)));
    q("#fv-blbl").textContent = m.kmFirst ? "RANGE" : "BATTERY";
    q("#fv-slbl").textContent = m.kmFirst ? "BATTERY" : "RANGE";
    q("#fv-cells").style.width = `${m.soc}%`;
    q("#fv-cells").className = m.regen ? "regen" : m.socCls;
    const mt = q("#fv-mt"); mt.textContent = `${Math.round(m.mt)}°C`; mt.className = `val small num ${tempClass(m.mt, 100, 120)}`;
    q("#fv-4wd").textContent = m.w4 ? "WAIT" : m.fw === "4wd" ? "4WD" : m.fw === "to_4wd" ? "→4WD" : m.fw === "to_2wd" ? "→2WD" : m.fw === "fault" ? "FAULT" : "2WD";
    q("#fv-diff").textContent = `${Math.max(0, m.diff)}%`;
    q("#fv-dbar").style.width = `${clamp01(m.diff / 100) * 100}%`;
    q("#fv-dknob").style.left = `${clamp01(m.diff / 100) * 100}%`;
    const imu = m.pitch != null;
    q("#fv-pitch").textContent = imu ? `${Math.round(Math.abs(m.pitch))}°` : "--";
    q("#fv-roll").textContent = m.roll == null ? "--" : `${Math.round(Math.abs(m.roll))}° ${m.roll > 0.5 ? "R" : m.roll < -0.5 ? "L" : ""}`;
    // The picture is drawn about 11 degrees nose up already. Nose up = turn it anticlockwise.
    const pitch = Math.max(-40, Math.min(40, imu ? m.pitch : 0));
    q("#fv-buggy").style.transform = `rotate(${(11.4 - pitch).toFixed(1)}deg)`;
  }

  updNight(m, q) {
    q("#nv-prect").setAttribute("y", (420 * (1 - (m.regen ? 0 : m.p))).toFixed(1));
    q("#nv-prect").setAttribute("height", (420 * (m.regen ? 0 : m.p)).toFixed(1));
    q("#nv-ppct").textContent = m.regen ? "charging" : `${Math.round(m.p * 100)}% power`;
    // The tooth fills from the tip up. Only the tooth is coloured, never the panel round it.
    q("#nv-tooth").style.clipPath = `inset(${(100 - (m.mcOn ? m.soc : 0)).toFixed(1)}% 0 0 0)`;
    const st = this.ctx.store;
    let bars = 0; for (let i = 1; i <= 4; i++) if (st.get(`light.front_${i}`, 0) > 0) bars++;
    q("#nv-beams").classList.toggle("on", bars > 0);
    const four = m.fw === "4wd" || m.fw === "to_4wd";
    const fl = q("#nv-fl-v"); fl.textContent = m.fw === "4wd" ? "4WD" : m.fw === "to_4wd" ? "→ 4WD" : m.fw === "to_2wd" ? "→ 2WD" : m.fw === "fault" ? "FAULT" : "2WD";
    fl.className = `val num ${m.fw === "fault" ? "bad" : four ? "acc" : ""}`;
    const fr = q("#nv-fr-v"); fr.textContent = `${Math.max(0, m.diff)}%`; fr.className = `val num ${m.diff > 2 ? "acc" : ""}`;
    const rl = q("#nv-rl-v"); rl.textContent = `${Math.round(m.mt)}°C`; rl.className = `val num ${tempClass(m.mt, 100, 120)}`;
    const rr = q("#nv-rr-v"); rr.textContent = `${Math.round(m.ct)}°C`; rr.className = `val num ${tempClass(m.ct, 70, 85)}`;
    // Driven wheels glow: the rear always, the front in 4WD. The front pair glows harder with the diff locked.
    const drive = m.p > 0.02 || m.regen;
    ["rl", "rr"].forEach((w) => q(`#nv-w${w}`).classList.toggle("on", drive));
    ["fl", "fr"].forEach((w) => { const e = q(`#nv-w${w}`); e.classList.toggle("on", drive && four); e.classList.toggle("lock", four && m.diff > 2); });
  }

  // What's on right now, as big shortcuts: tap one to jump to its screen.
  chips(st, m, q) {
    const set = this.ctx.settings, on = (id) => featureOn(set, id);
    const chips = [];
    const chip = (screen, cls, ic, txt) => chips.push(`<button class="act-chip ${cls}" data-go="${screen || ""}">${ic ? icon(ic) : ""}<span>${txt}</span></button>`);
    // Ready, handbrake, limp etc are warning lights (telltales.js), so no chips for them.
    // Fossil shows 4WD and the diff on its own card, so no chips for those there.
    if (this.look !== "offroad") {
      const { fw, w4 } = m;
      if (fw !== "2wd" || w4) chip("drivetrain", fw === "4wd" && !w4 ? "on" : fw === "fault" ? "alert" : "busy", "fourwd", w4 ? (fw === "4wd" ? "2WD when stopped" : "4WD when stopped") : fw === "4wd" ? "4WD" : fw === "to_4wd" ? "→ 4WD" : fw === "to_2wd" ? "→ 2WD" : "4WD fault");
      if (m.diff > 2 && this.look !== "night") chip("drivetrain", "on", "lock", `Diff ${m.diff}%`);
    }
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
  }
}
