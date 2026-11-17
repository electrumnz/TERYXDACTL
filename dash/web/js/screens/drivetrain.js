// 2WD / 4WD and front diff lock (%). The dash asks; the control box checks speed and runs the actuators.
import { el, $, Slider, toast } from "../ui/controls.js";
import { vehicleDiagram } from "../ui/vehicle.js";

function arc(pct) {
  // Semi-circle gauge from 180° to 0°.
  const a = Math.PI * (1 - pct / 100), r = 100, cx = 130, cy = 130;
  const x = cx + r * Math.cos(a), y = cy - r * Math.sin(a);
  return `M30 130 A100 100 0 0 1 ${x.toFixed(1)} ${y.toFixed(1)}`;
}

export class DrivetrainScreen {
  constructor(ctx) { this.ctx = ctx; this.id = "drivetrain"; this.label = "4WD"; this.icon = "fourwd"; }

  mount(root) {
    root.innerHTML = `
      <div class="dt">
        <div class="panel col" style="gap:14px">
          <h3>Drive</h3>
          <div class="seg" id="t-seg"><button data-v="0">2WD</button><button data-v="1">4WD</button></div>
          <div class="kv"><span class="k">Actuator</span><span class="v" id="t-state">--</span></div>
          <div class="kv"><span class="k">Current</span><span class="v num" id="t-cur">-- A</span></div>
          <div class="lockout" id="t-lock"></div>
          <div id="t-veh" class="grow" style="min-height:0"></div>
          <div class="muted small">Stop before changing 2WD/4WD (under <b id="t-lim">1</b> km/h). It finishes engaging as you roll off slowly. The control box checks your speed and stops the actuator at its end stop.</div>
        </div>
        <div class="panel col" style="gap:12px">
          <h3>Front diff lock</h3>
          <div class="diff-gauge"><svg viewBox="0 0 260 150">
            <path d="M30 130 A100 100 0 0 1 230 130" fill="none" stroke="var(--panel-2)" stroke-width="22" stroke-linecap="round"/>
            <path id="t-arc" d="" fill="none" stroke="var(--accent)" stroke-width="22" stroke-linecap="round"/>
            <text id="t-pct" x="130" y="118" text-anchor="middle" font-size="54" font-weight="900" fill="currentColor">0%</text>
            <text id="t-tgt" x="130" y="146" text-anchor="middle" font-size="16" font-weight="700" fill="var(--muted)"></text>
          </svg></div>
          <div id="t-slider"></div>
          <div class="presets" id="t-presets"></div>
          <div class="lockout" id="d-lock"></div>
          <div class="muted small" id="d-4wd"></div>
          <div class="muted small">0% is fully open, 100% is fully locked. Add lock under <b id="d-lim">15</b> km/h, ideally with the wheels straight. Unlock any time.</div>
        </div>
      </div>`;
    this.root = root;
    this.veh = vehicleDiagram(); this.veh.root.classList.add("small"); $(root, "#t-veh").appendChild(this.veh.root);
    root.querySelectorAll("#t-seg button").forEach((b) => (b.onclick = () => this.ask4wd(+b.dataset.v)));
    this.slider = new Slider({ label: "TARGET", fmt: (v) => `${v}%`, step: 5, onChange: (v, final) => { if (final) this.askDiff(v); } });
    this.slider.onLocked = () => toast(`Diff lock only adds lock under ${this.lim("diff_max_kmh", 15)} km/h. Use OPEN to unlock.`);
    $(root, "#t-slider").appendChild(this.slider.root);
    const pr = $(root, "#t-presets");
    [0, 25, 50, 75, 100].forEach((p) => {
      const b = el(`<button class="btn sm">${p === 0 ? "OPEN" : p === 100 ? "LOCK" : p + "%"}</button>`);
      b.onclick = () => { this.slider.set(p); this.askDiff(p); };
      pr.appendChild(b);
    });
  }

  lim(name, d) { return this.ctx.picoLimit(name, d); }

  ask4wd(v) {
    const st = this.ctx.store;
    if (st.get("mc.speed", 0) >= this.lim("fourwd_max_kmh", 1)) toast("Stop first to change 2WD/4WD.");
    this.ctx.link.request("act.4wd", v);
  }

  askDiff(v) {
    const st = this.ctx.store;
    if (v > st.get("an.diff_pos", 0) + 2 && st.get("mc.speed", 0) >= this.lim("diff_max_kmh", 15)) toast(`Slow to under ${this.lim("diff_max_kmh", 15)} km/h to add diff lock.`);
    this.ctx.link.request("act.diff", v);
  }

  update(st) {
    const q = (s) => $(this.root, s);
    const fw = st.get("act.4wd", "2wd");
    const words = { "2wd": "2WD, at end stop", "4wd": "4WD, at end stop", to_4wd: "Moving to 4WD…", to_2wd: "Moving to 2WD…", fault: "Fault", unknown: "Not known yet (tap 2WD or 4WD)" };
    q("#t-state").textContent = words[fw] || fw;
    q("#t-state").className = `v ${fw === "fault" ? "bad" : fw.startsWith("to_") ? "info" : ""}`;
    q("#t-cur").textContent = `${st.get("an.4wd_current", 0).toFixed(1)} A`;
    const want = fw === "4wd" || fw === "to_4wd" ? 1 : 0;
    this.root.querySelectorAll("#t-seg button").forEach((b) => {
      b.classList.toggle("on", +b.dataset.v === want);
      b.classList.toggle("busy", fw.startsWith("to_") && +b.dataset.v === want);
    });
    const spd = st.get("mc.speed", 0);
    const fl = this.lim("fourwd_max_kmh", 1), dl = this.lim("diff_max_kmh", 15);
    q("#t-lim").textContent = fl; q("#d-lim").textContent = dl;
    const unknown = st.get("mc.online") === false || st.get("pico.speed_valid") === false;
    const l4 = q("#t-lock");
    l4.textContent = unknown ? "Speed unknown: locked out" : spd >= fl ? "Stop to change" : "Ready";
    l4.className = `lockout ${unknown || spd >= fl ? "warn" : ""}`;

    const pos = st.get("an.diff_pos", 0), tgt = st.get("act.diff_target", pos);
    q("#t-arc").setAttribute("d", arc(Math.max(pos, 0.1)));
    q("#t-arc").style.opacity = pos > 0.5 ? 1 : 0;
    this.veh.update(st);
    q("#t-pct").textContent = `${Math.round(pos)}%`;
    q("#t-tgt").textContent = Math.abs(tgt - pos) > 1 ? `moving to ${Math.round(tgt)}%` : `${st.get("an.diff_current", 0) > 0.2 ? "holding" : "set"}`;
    this.slider.set(Math.round(tgt / 5) * 5);
    this.slider.setActual(pos);
    const dlocked = unknown || spd >= dl;
    this.slider.setLocked(dlocked);
    const ld = q("#d-lock");
    ld.textContent = unknown ? "Speed unknown: locked out" : spd >= dl ? `No more lock above ${dl} km/h (OPEN works)` : "Ready";
    q("#d-4wd").textContent = fw === "4wd" ? "" : "In 2WD the front diff lock does nothing. Switch to 4WD first.";
    ld.className = `lockout ${dlocked ? "warn" : ""}`;
  }
}
