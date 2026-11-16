// Rear tray lift: hold UP or DOWN. Only works when stopped. Stops at the limit switches,
// on high current, or after the time limit, all decided by the control box.
import { $, holdButton, toast } from "../ui/controls.js";
import { icon } from "../ui/icons.js";

export class TrayScreen {
  constructor(ctx) { this.ctx = ctx; this.id = "tray"; this.label = "Tray"; this.icon = "tray"; }

  mount(root) {
    root.innerHTML = `
      <div class="row" style="height:100%">
        <div class="col" style="width:360px">
          <button class="hold-btn fill" id="tr-up">${icon("up")}TRAY UP<span class="hint">Hold to raise</span></button>
          <button class="hold-btn fill" id="tr-down">${icon("down")}TRAY DOWN<span class="hint">Hold to lower</span></button>
        </div>
        <div class="col grow">
          <div class="panel tray-pic grow" style="display:flex;align-items:center">
            <svg viewBox="0 0 520 220">
              <line x1="20" y1="190" x2="500" y2="190" stroke="var(--line)" stroke-width="4"/>
              <rect x="40" y="120" width="180" height="50" rx="10" fill="var(--panel-2)" stroke="var(--line)" stroke-width="3"/>
              <circle cx="90" cy="180" r="24" fill="var(--dim)"/><circle cx="400" cy="180" r="24" fill="var(--dim)"/>
              <rect x="220" y="140" width="260" height="20" rx="4" fill="var(--panel-2)" stroke="var(--line)" stroke-width="3"/>
              <g id="tr-bed" style="transform-origin:470px 140px"><rect class="bed" x="230" y="100" width="250" height="40" rx="6"/></g>
              <text id="tr-pcttxt" x="350" y="40" text-anchor="middle" font-size="34" font-weight="900" fill="currentColor">0%</text>
            </svg>
          </div>
          <div class="panel">
            <div class="kv"><span class="k">State</span><span class="v" id="tr-state">--</span></div>
            <div class="kv"><span class="k">Down switch</span><span class="v" id="tr-ld">--</span></div>
            <div class="kv"><span class="k">Up switch</span><span class="v" id="tr-lu">--</span></div>
            <div class="kv"><span class="k">Current</span><span class="v num" id="tr-cur">--</span></div>
          </div>
          <div class="lockout" id="tr-lock"></div>
        </div>
      </div>`;
    this.root = root;
    const link = this.ctx.link, st = this.ctx.store;
    const can = () => {
      if (st.get("mc.speed", 0) > 0.5 || st.get("mc.online") === false) { toast("Stop the Teryx before moving the tray."); return false; }
      return true;
    };
    holdButton($(root, "#tr-up"), { canStart: can, onStart: () => link.holdStart("act.tray", 1), onStop: () => link.holdStop("act.tray") });
    holdButton($(root, "#tr-down"), { canStart: can, onStart: () => link.holdStart("act.tray", -1), onStop: () => link.holdStop("act.tray") });
  }

  hide() { this.ctx.link.holdStop("act.tray"); }

  update(st) {
    const q = (s) => $(this.root, s);
    const state = st.get("act.tray", "down");
    const words = { down: "Down", up: "Fully up", mid: "Part way", raising: "Raising…", lowering: "Lowering…", fault: "Fault" };
    q("#tr-state").textContent = words[state] || state;
    q("#tr-state").className = `v ${state === "fault" ? "bad" : state === "raising" || state === "lowering" ? "info" : ""}`;
    let pct = st.get("act.tray_pct");
    if (pct == null) pct = state === "up" ? 100 : state === "down" ? 0 : 50;
    q("#tr-bed").style.transform = `rotate(${-(pct / 100) * 40}deg)`;
    q("#tr-pcttxt").textContent = `${Math.round(pct)}%`;
    q("#tr-ld").textContent = st.get("in.tray_down") ? "Pressed" : "Open";
    q("#tr-lu").textContent = st.get("in.tray_up") ? "Pressed" : "Open";
    const cur = st.get("an.tray_current", 0), lim = this.ctx.picoLimit("tray_overcurrent_da", 10);
    q("#tr-cur").textContent = `${cur.toFixed(1)} A of ${lim} A`;
    q("#tr-cur").className = `v num ${cur > lim * 0.8 ? "warn" : ""}`;
    const moving = st.get("mc.speed", 0) > 0.5 || st.get("mc.online") === false;
    q("#tr-up").classList.toggle("locked", moving || state === "up");
    q("#tr-down").classList.toggle("locked", moving || state === "down");
    const l = q("#tr-lock");
    l.textContent = moving ? "Locked out: the Teryx must be stopped" : "Ready. Hold a button to move the tray.";
    l.className = `lockout ${moving ? "warn" : ""}`;
  }
}
