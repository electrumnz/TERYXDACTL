// Winch: slide to arm, then hold IN or OUT. Lifting your finger stops it.
// The control box only lets it run when armed and stopped, never both ways at once,
// and disarms it after 2 minutes idle. The XBull handheld remote still works as a backup.
import { el, $, holdButton, slideToArm, toast } from "../ui/controls.js";
import { icon } from "../ui/icons.js";

export class WinchScreen {
  constructor(ctx) { this.ctx = ctx; this.id = "winch"; this.label = "Winch"; this.icon = "winch"; }

  mount(root) {
    root.innerHTML = `
      <div class="row" style="height:100%">
        <div class="col grow">
          <div class="arm-slide" id="w-arm"><div class="txt">SLIDE TO ARM WINCH</div><div class="knob">${icon("unlock")}</div></div>
          <div class="hold-wrap fill">
            <button class="hold-btn" id="w-in">${icon("in")}WINCH IN<span class="hint">Hold to pull in</span></button>
            <button class="hold-btn" id="w-out">${icon("out")}WINCH OUT<span class="hint">Hold to pay out</span></button>
          </div>
          <div class="panel"><div class="row" style="align-items:center;justify-content:space-between">
            <div><div class="muted small" style="font-weight:800;letter-spacing:.1em">RUNNING</div><div class="big-val" id="w-run">STOPPED</div></div>
            <div style="text-align:right"><div class="muted small" style="font-weight:800;letter-spacing:.1em">AUTO DISARM IN</div><div class="big-val num" id="w-idle">--</div></div>
          </div></div>
        </div>
        <div class="panel" style="width:330px">
          <h3>Checks</h3>
          <div class="status-list" id="w-checks"></div>
          <div class="muted small" style="margin-top:16px">The handheld remote still works if the dash is down. Keep clear of the rope. Never step over a loaded line.</div>
        </div>
      </div>`;
    this.root = root;
    const link = this.ctx.link, st = this.ctx.store;
    slideToArm($(root, "#w-arm"), {
      isArmed: () => !!st.get("winch.armed"),
      onArm: () => {
        if (st.get("mc.speed", 0) > 0.5) toast("Stop the Teryx before arming the winch.");
        link.request("winch.armed", true);
      },
      onDisarm: () => link.request("winch.armed", false),
    });
    const can = () => {
      if (!st.get("winch.armed")) { toast("Slide to arm the winch first."); return false; }
      return true;
    };
    holdButton($(root, "#w-in"), { canStart: can, onStart: () => link.holdStart("winch", 1), onStop: () => link.holdStop("winch") });
    holdButton($(root, "#w-out"), { canStart: can, onStart: () => link.holdStart("winch", -1), onStop: () => link.holdStop("winch") });
  }

  hide() { this.ctx.link.holdStop("winch"); }

  update(st) {
    const q = (s) => $(this.root, s);
    const armed = !!st.get("winch.armed");
    const arm = q("#w-arm");
    arm.classList.toggle("armed", armed);
    arm.querySelector(".txt").textContent = armed ? "ARMED. TAP TO DISARM" : "SLIDE TO ARM WINCH";
    arm.querySelector(".knob").style.left = armed ? `calc(100% - 75px)` : "";
    q("#w-in").classList.toggle("locked", !armed);
    q("#w-out").classList.toggle("locked", !armed);
    const wi = st.get("winch.in"), wo = st.get("winch.out");
    q("#w-run").textContent = wi ? "PULLING IN" : wo ? "PAYING OUT" : "STOPPED";
    q("#w-run").className = `big-val ${wi || wo ? "warn" : ""}`;
    const limit = this.ctx.picoLimit("winch_auto_disarm_s", 120);
    // Use the control box's idle timer if it sends one, else keep our own rough copy.
    let idle = st.get("winch.idle_s");
    if (idle == null) {
      if (!armed || wi || wo) this._idleFrom = Date.now();
      idle = (Date.now() - (this._idleFrom || Date.now())) / 1000;
    }
    q("#w-idle").textContent = armed && idle != null ? `${Math.max(0, Math.ceil(limit - idle))} s` : "--";

    const spd = st.get("mc.speed", 0);
    const checks = [
      [st.get("pico.online", false), "Control box online"],
      [st.get("mc.online") !== false && spd < 0.5, "Stopped"],
      [armed, "Armed"],
      [!!st.get("winch.isolator"), "Winch power on"],
      [st.get("an.aux_12v", 13) >= 11.8, `12V battery ${st.get("an.aux_12v", 0).toFixed(1)} V`],
      [!st.get("in.winch_remote"), st.get("in.winch_remote") ? "Handheld remote in use" : "Handheld remote idle"],
    ];
    const html = checks.map(([ok, t]) => `<div class="check ${ok ? "ok" : ""}"><i></i>${t}</div>`).join("");
    if (html !== this._c) { q("#w-checks").innerHTML = html; this._c = html; }
  }
}
