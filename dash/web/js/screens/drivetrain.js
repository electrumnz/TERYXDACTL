// 2WD / 4WD and front diff lock (%). The dash asks; the control box checks speed and runs the actuators.
// If it's too fast to change yet, the control box waits (spinner, hint, countdown, Cancel here)
// and changes once the speed is right, or gives up after shift_wait_ms (docs/drive-changes.md).
import { el, $, Slider, toast } from "../ui/controls.js";
import { vehicleDiagram } from "../ui/vehicle.js";
import { waitHint } from "../ui/shift.js";

const SPIN = `<span class="spin" aria-hidden="true"></span>`;
const TICK = `<span class="tick" aria-hidden="true">✓</span>`;
const PHASES = ["asked", "waiting", "moving", "done", "timeout", "cancelled", "failed"];

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
          <div class="seg shiftable" id="t-seg"><button data-v="0"><span class="lbl">2WD</span></button><button data-v="1"><span class="lbl">4WD</span></button></div>
          <div class="shift-wait" id="t-wait" hidden><span class="sw-text"></span><button class="btn sm sw-cancel" id="t-cancel">Cancel</button></div>
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
          <div class="shift-wait" id="d-wait" hidden><span class="sw-text"></span><button class="btn sm sw-cancel" id="d-cancel">Cancel</button></div>
          <div class="lockout" id="d-lock"></div>
          <div class="muted small" id="d-4wd"></div>
          <div class="muted small">0% is fully open, 100% is fully locked. Add lock under <b id="d-lim">15</b> km/h, ideally with the wheels straight. Unlock any time.</div>
        </div>
      </div>`;
    this.root = root;
    this.veh = vehicleDiagram(); this.veh.root.classList.add("small"); $(root, "#t-veh").appendChild(this.veh.root);
    root.querySelectorAll("#t-seg button").forEach((b) => (b.onclick = () => this.ask4wd(+b.dataset.v)));
    this.slider = new Slider({ label: "TARGET", fmt: (v) => `${v}%`, step: 5, onChange: (v, final) => { if (final) this.askDiff(v); } });
    // Over the limit the box will wait, so the slider stays usable. It's only locked while
    // a 4WD change is going (one change at a time) or with no speed signal.
    this.slider.onLocked = () => toast(this.ctx.shift.active("fourwd") ? "Wait for the 4WD change to finish. OPEN still works." : "Speed unknown, so diff lock is locked out.");
    $(root, "#t-cancel").onclick = () => this.ctx.shift.cancel("fourwd");
    $(root, "#d-cancel").onclick = () => this.ctx.shift.cancel("diff");
    $(root, "#t-slider").appendChild(this.slider.root);
    const pr = $(root, "#t-presets");
    [0, 25, 50, 75, 100].forEach((p) => {
      const b = el(`<button class="btn sm" data-p="${p}">${p === 0 ? "OPEN" : p === 100 ? "LOCK" : p + "%"}</button>`);
      b.onclick = () => {
        if (p > 0 && this.ctx.shift.active("fourwd")) { toast("Wait for the 4WD change to finish. OPEN still works."); return; }
        this.slider.set(p); this.askDiff(p);
      };
      pr.appendChild(b);
    });
  }

  lim(name, d) { return this.ctx.picoLimit(name, d); }

  ask4wd(v) {
    const sh = this.ctx.shift;
    if (sh.active("diff")) { toast("Wait for the diff lock change to finish."); return; }
    if (sh.get("fourwd").phase === "waiting") { sh.cancel("fourwd"); return; }  // tap again = cancel
    sh.ask4wd(v);
  }

  askDiff(v) {
    const sh = this.ctx.shift, st = this.ctx.store;
    if (v > st.get("an.diff_pos", 0) + 2 && sh.active("fourwd")) { toast("Wait for the 4WD change to finish."); return; }
    sh.askDiff(v);
  }

  // A button's look for a phase: spinner while asked / waiting / moving, tick + pulse when done,
  // amber for timed out, grey for cancelled, red for failed (see .sh-* in dash.css).
  paint(b, phase, label) {
    PHASES.forEach((c) => b.classList.toggle(`sh-${c}`, phase === c));
    const extra = ["asked", "waiting", "moving"].includes(phase) ? SPIN : phase === "done" ? TICK : "";
    const html = `${extra}<span class="lbl">${label}</span>`;
    if (b._look !== html) { b.innerHTML = html; b._look = html; }
  }

  // The line under the buttons: hint + countdown + Cancel while waiting, or how it ended.
  waitLine(name, box) {
    const sh = this.ctx.shift, ph = sh.get(name).phase, left = sh.secsLeft(name);
    const txt = ph === "waiting" ? `${waitHint(this.ctx, name)}${left != null ? ` · ${left}s` : ""}`
      : ph === "timeout" ? "Timed out. Tap again to retry."
      : ph === "cancelled" ? "Cancelled" : "";
    box.hidden = !txt;
    box.className = `shift-wait ${ph}`;
    box.querySelector(".sw-text").textContent = txt;
    box.querySelector(".sw-cancel").hidden = ph !== "waiting";
  }

  update(st) {
    const q = (s) => $(this.root, s);
    const fw = st.get("act.4wd", "2wd");
    const words = { "2wd": "2WD, at end stop", "4wd": "4WD, at end stop", to_4wd: "Moving to 4WD…", to_2wd: "Moving to 2WD…", fault: "Fault", unknown: "Not known yet (tap 2WD or 4WD)" };
    q("#t-state").textContent = words[fw] || fw;
    q("#t-state").className = `v ${fw === "fault" ? "bad" : fw.startsWith("to_") ? "info" : ""}`;
    q("#t-cur").textContent = `${st.get("an.4wd_current", 0).toFixed(1)} A`;
    const sh = this.ctx.shift, f = sh.get("fourwd");
    const want = fw === "4wd" || fw === "to_4wd" ? 1 : 0;
    const shiftTo = f.phase === "idle" ? null : f.target;
    this.root.querySelectorAll("#t-seg button").forEach((b) => {
      const v = +b.dataset.v;
      b.classList.toggle("on", v === want);
      b.classList.toggle("locked", sh.active("diff"));
      this.paint(b, v === shiftTo ? f.phase : "idle", v ? "4WD" : "2WD");
    });
    this.waitLine("fourwd", q("#t-wait"));
    const spd = st.get("mc.speed", 0);
    const fl = this.lim("fourwd_max_kmh", 1), dl = this.lim("diff_max_kmh", 15);
    q("#t-lim").textContent = fl; q("#d-lim").textContent = dl;
    const unknown = st.get("mc.online") === false || st.get("pico.speed_valid") === false;
    const l4 = q("#t-lock");
    const held = st.get("pico.throttle_hold");
    l4.textContent = unknown ? "Speed unknown: locked out" : held ? "Shifting. Throttle held until it's done"
      : sh.active("diff") ? "Diff lock is changing" : f.phase === "waiting" ? "Waiting for you to stop"
      : spd >= fl ? "Tap and it'll change once you stop" : "Ready";
    l4.className = `lockout ${unknown ? "warn" : held || sh.active("diff") ? "info" : ""}`;

    const pos = st.get("an.diff_pos", 0), tgt = st.get("act.diff_target", pos);
    q("#t-arc").setAttribute("d", arc(Math.max(pos, 0.1)));
    q("#t-arc").style.opacity = pos > 0.5 ? 1 : 0;
    this.veh.update(st);
    q("#t-pct").textContent = `${Math.round(pos)}%`;
    q("#t-tgt").textContent = Math.abs(tgt - pos) > 1 ? `moving to ${Math.round(tgt)}%` : `${st.get("an.diff_current", 0) > 0.2 ? "holding" : "set"}`;
    this.slider.set(Math.round(tgt / 5) * 5);
    this.slider.setActual(pos);
    const dlocked = unknown || sh.active("fourwd");
    this.slider.setLocked(dlocked);
    // The preset that was tapped (or nearest the slider target) carries the spinner / tick.
    const d = sh.get("diff");
    const dTo = d.target == null ? null : [0, 25, 50, 75, 100].reduce((a, b) => (Math.abs(b - d.target) < Math.abs(a - d.target) ? b : a));
    this.root.querySelectorAll("#t-presets button").forEach((b) => {
      const p = +b.dataset.p;
      b.classList.toggle("locked", p > 0 && sh.active("fourwd"));
      this.paint(b, p === dTo ? d.phase : "idle", p === 0 ? "OPEN" : p === 100 ? "LOCK" : `${p}%`);
    });
    this.waitLine("diff", q("#d-wait"));
    q("#t-tgt").textContent = d.phase === "waiting" ? `waiting to go to ${Math.round(tgt)}%` : q("#t-tgt").textContent;
    const ld = q("#d-lock");
    ld.textContent = unknown ? "Speed unknown: locked out" : sh.active("fourwd") ? "4WD is changing (OPEN still works)"
      : spd >= dl ? `Over ${dl} km/h: more lock waits till you slow down (OPEN works now)` : "Ready";
    q("#d-4wd").textContent = fw === "4wd" ? "" : "In 2WD the front diff lock does nothing. Switch to 4WD first.";
    ld.className = `lockout ${unknown ? "warn" : sh.active("fourwd") ? "info" : ""}`;
  }
}
