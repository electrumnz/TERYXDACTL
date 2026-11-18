// Winch: slide to arm, then hold IN or OUT. Lifting your finger stops it.
// The control box only lets it run when armed and stopped, never both ways at once,
// and disarms it after 2 minutes idle. The XBull handheld remote and the hand switches
// still work as a backup.
//
// Timed pull (tucked behind a small button): pick 3, 5 or 10 s, a 3-2-1 countdown with
// beeps, then it pulls in for that long and stops by itself. Big CANCEL / STOP the whole
// way through. The dash keeps sending hold frames during the pull, so if the dash dies the
// control box stops it within 300 ms, and the control box also times the pull itself and
// stops it at the end (capped at its own setting 21), so a stuck dash can't run it on.
import { el, $, holdButton, slideToArm, toast } from "../ui/controls.js";
import { icon } from "../ui/icons.js";
import { Sound } from "../sound.js";
import { HEAT, mmss } from "../winchheat.js";

export const TIMED_PRESETS = [3, 5, 10];
const COUNTDOWN_S = 3;

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
          <div class="panel"><div class="w-stats">
            <div><div class="w-lbl">RUNNING</div><div class="big-val" id="w-run">STOPPED</div></div>
            <div><div class="w-lbl">THIS PULL</div><div class="big-val num" id="w-pull">0:00</div></div>
            <div class="w-heat-box"><div class="w-lbl">MOTOR HEAT <span id="w-heat-txt"></span></div><div class="heat-bar"><div id="w-heat"></div><i style="left:${HEAT.warnPct}%"></i></div></div>
            <div style="text-align:right"><div class="w-lbl">AUTO DISARM IN</div><div class="big-val num" id="w-idle">--</div></div>
          </div></div>
        </div>
        <div class="panel" style="width:330px;display:flex;flex-direction:column">
          <h3>Checks</h3>
          <div class="status-list" id="w-checks"></div>
          <div class="muted small" style="margin-top:16px">The handheld remote and hand switches still work if the dash is down. Keep clear of the rope. Never step over a loaded line.</div>
          <div style="flex:1"></div>
          <button class="btn sm" id="w-timed">${icon("timer")}Timed pull</button>
        </div>
      </div>
      <div class="wt-pop" id="wt" hidden>
        <div class="wt-card">
          <div class="wt-head"><span id="wt-title">TIMED PULL IN</span><span class="wt-heat" id="wt-heat"></span></div>
          <div class="wt-body" id="wt-body"></div>
          <div class="wt-btns" id="wt-btns"></div>
        </div>
      </div>`;
    this.root = root;
    this.secs = 5;
    this.phase = "closed";   // closed | pick | count | pull | done
    const link = this.ctx.link, st = this.ctx.store;
    slideToArm($(root, "#w-arm"), {
      isArmed: () => !!st.get("winch.armed"),
      onArm: () => {
        if (st.get("mc.speed", 0) > 0.5) toast("Stop the Teryx before arming the winch.");
        link.request("winch.armed", true);
      },
      onDisarm: () => { this.abort("Winch disarmed."); link.request("winch.armed", false); },
    });
    const can = () => {
      if (!st.get("winch.armed")) { toast("Slide to arm the winch first."); return false; }
      return true;
    };
    holdButton($(root, "#w-in"), { canStart: can, onStart: () => link.holdStart("winch", 1), onStop: () => link.holdStop("winch") });
    holdButton($(root, "#w-out"), { canStart: can, onStart: () => link.holdStart("winch", -1), onStop: () => link.holdStop("winch") });
    $(root, "#w-timed").onclick = () => this.open();
    // Tap outside the card does nothing on purpose: only the buttons close it.
  }

  hide() { this.abort(null); this.close(); this.ctx.link.holdStop("winch"); }

  // ---------------------------------------------------------------- timed pull popup
  open() { this.phase = "pick"; this.render(); }
  close() { this.stopTimers(); this.phase = "closed"; if (this.root) $(this.root, "#wt").hidden = true; }

  stopTimers() { clearInterval(this._timer); this._timer = null; }

  /** Stop a countdown or pull straight away. msg = why, shown on the done page. */
  abort(msg) {
    if (this.phase === "count" || this.phase === "pull") {
      this.ctx.link.holdStop("winch");
      this.stopTimers();
      this.result = { secs: this.pulledS(), msg: msg || "Stopped." };
      this.phase = "done";
      this.render();
    }
  }

  pulledS() { return this.pullFrom ? Math.min(this.secs, (Date.now() - this.pullFrom) / 1000) : 0; }

  start() {
    const st = this.ctx.store, heat = this.ctx.winchHeat;
    if (!st.get("winch.armed")) { Sound.play("reject"); toast("Slide to arm the winch first."); return; }
    if (st.get("mc.speed", 0) > 0.5) { Sound.play("reject"); toast("Stop the Teryx first."); return; }
    if (st.get("in.winch_remote")) { Sound.play("reject"); toast("The handheld remote or a hand switch is in use."); return; }
    if (heat && heat.state === "rest") { Sound.play("reject"); toast(`Winch needs a rest. About ${mmss(heat.restLeftS())} to go.`, "bad"); return; }
    this.phase = "count";
    this.countLeft = COUNTDOWN_S;
    this.pullFrom = 0;
    Sound.play("count");
    this.render();
    this._timer = setInterval(() => {
      this.countLeft -= 1;
      if (this.countLeft > 0) { Sound.play("count"); this.render(); return; }
      this.stopTimers();
      this.beginPull();
    }, 1000);
  }

  beginPull() {
    const st = this.ctx.store;
    if (!st.get("winch.armed")) { this.phase = "count"; this.abort("Winch was disarmed."); return; }
    Sound.play("go");
    this.phase = "pull";
    this.pullFrom = Date.now();
    this.sawRun = false;
    this.ctx.link.holdStart("winch", 1, this.secs);
    this.render();
    this._timer = setInterval(() => this.pullTick(), 100);
  }

  pullTick() {
    const st = this.ctx.store, el = Date.now() - this.pullFrom;
    if (st.get("winch.in")) this.sawRun = true;
    if (el >= this.secs * 1000) {
      this.ctx.link.holdStop("winch");
      this.stopTimers();
      Sound.play("done");
      this.result = { secs: this.secs, msg: "Done." };
      this.phase = "done";
      this.render();
      return;
    }
    // Control box cut it short (remote grabbed, disarmed, moved...): stop asking.
    if (!st.get("winch.armed")) return this.abort("Winch was disarmed.");
    if (this.sawRun && !st.get("winch.in") && el > 600) return this.abort("Control box stopped the winch.");
    if (!this.sawRun && el > 1500) return this.abort("Winch didn't start. Check the control box.");
    this.renderLive();
  }

  render() {
    if (!this.root) return;
    const pop = $(this.root, "#wt"), body = $(this.root, "#wt-body"), btns = $(this.root, "#wt-btns");
    pop.hidden = this.phase === "closed";
    pop.dataset.phase = this.phase;
    if (this.phase === "closed") return;
    if (this.phase === "pick") {
      body.innerHTML = `
        <div class="wt-msg">How long to pull in for?</div>
        <div class="wt-presets">${TIMED_PRESETS.map((s) => `<button class="wt-preset ${s === this.secs ? "on" : ""}" data-s="${s}">${s}<small>s</small></button>`).join("")}</div>
        <div class="wt-note" id="wt-note"></div>`;
      btns.innerHTML = `<button class="btn wt-cancel" id="wt-x">Cancel</button><button class="btn on wt-go" id="wt-go">${icon("in")}Start</button>`;
      body.querySelectorAll(".wt-preset").forEach((b) => (b.onclick = () => { this.secs = +b.dataset.s; this.render(); }));
      $(this.root, "#wt-x").onclick = () => this.close();
      $(this.root, "#wt-go").onclick = () => this.start();
    } else if (this.phase === "count") {
      body.innerHTML = `<div class="wt-msg">${this.secs} s pull in, starting in</div><div class="wt-count num" id="wt-num">${this.countLeft}</div><div class="wt-note">Stand clear of the rope</div>`;
      btns.innerHTML = `<button class="btn wt-stop" id="wt-x">${icon("stop")}Cancel</button>`;
      $(this.root, "#wt-x").onclick = () => this.abort("Cancelled before it started.");
    } else if (this.phase === "pull") {
      body.innerHTML = `<div class="wt-msg">PULLING IN</div><div class="wt-count num" id="wt-num"></div><div class="heat-bar wt-prog"><div id="wt-prog"></div></div>`;
      btns.innerHTML = `<button class="btn wt-stop" id="wt-x">${icon("stop")}STOP</button>`;
      const x = $(this.root, "#wt-x");
      // Stop on press, not on release, so it's as quick as it can be.
      x.addEventListener("pointerdown", (e) => { e.preventDefault(); this.abort("Stopped."); });
      x.onclick = () => this.abort("Stopped.");
      this.renderLive();
    } else if (this.phase === "done") {
      const r = this.result || { secs: 0, msg: "" };
      body.innerHTML = `<div class="wt-msg">${r.msg}</div><div class="wt-count num small">${r.secs.toFixed(1)}<small>s</small></div><div class="wt-note" id="wt-note"></div>`;
      btns.innerHTML = `<button class="btn wt-cancel" id="wt-x">Close</button><button class="btn on wt-go" id="wt-go">${icon("reset")}Again (${this.secs} s)</button>`;
      $(this.root, "#wt-x").onclick = () => this.close();
      $(this.root, "#wt-go").onclick = () => this.start();
    }
    this.renderHeat();
  }

  renderLive() {
    const left = Math.max(0, this.secs - (Date.now() - this.pullFrom) / 1000);
    const n = $(this.root, "#wt-num"), p = $(this.root, "#wt-prog");
    if (n) n.textContent = left.toFixed(1);
    if (p) p.style.width = `${(1 - left / this.secs) * 100}%`;
  }

  renderHeat() {
    const heat = this.ctx.winchHeat; if (!heat || this.phase === "closed") return;
    const h = $(this.root, "#wt-heat");
    h.textContent = `Motor heat ${Math.round(Math.min(100, heat.pct))}%`;
    h.className = `wt-heat ${heat.state}`;
    const note = $(this.root, "#wt-note");
    if (!note) return;
    let t = "";
    if (heat.state === "rest") t = `Winch needs a rest: about ${mmss(heat.restLeftS())} to go.`;
    else if (this.phase === "pick" && heat.after(this.secs) >= HEAT.restPct) t = "This pull will make the winch too hot. Give it a rest after.";
    else if (heat.state === "warm") t = "Winch is getting hot. Short pulls only.";
    else if (this.phase === "pick") t = "Counts down 3, 2, 1 with beeps, then pulls. STOP works the whole time.";
    if (note.textContent !== t) note.textContent = t;
    note.className = `wt-note ${heat.state}`;
  }

  // ---------------------------------------------------------------- live update
  update(st) {
    const q = (s) => $(this.root, s);
    const armed = !!st.get("winch.armed");
    const arm = q("#w-arm");
    arm.classList.toggle("armed", armed);
    arm.querySelector(".txt").textContent = armed ? "ARMED. TAP TO DISARM" : "SLIDE TO ARM WINCH";
    arm.querySelector(".knob").style.left = armed ? `calc(100% - 75px)` : "";
    q("#w-in").classList.toggle("locked", !armed);
    q("#w-out").classList.toggle("locked", !armed);
    const wi = st.get("winch.in"), wo = st.get("winch.out"), hand = st.get("in.winch_remote");
    q("#w-run").textContent = wi ? "PULLING IN" : wo ? "PAYING OUT" : hand ? "BY HAND" : "STOPPED";
    q("#w-run").className = `big-val ${wi || wo || hand ? "warn" : ""}`;
    const limit = this.ctx.picoLimit("winch_auto_disarm_s", 120);
    // Use the control box's idle timer if it sends one, else keep our own rough copy.
    let idle = st.get("winch.idle_s");
    if (idle == null) {
      if (!armed || wi || wo) this._idleFrom = Date.now();
      idle = (Date.now() - (this._idleFrom || Date.now())) / 1000;
    }
    q("#w-idle").textContent = armed && idle != null ? `${Math.max(0, Math.ceil(limit - idle))} s` : "--";

    const heat = this.ctx.winchHeat;
    if (heat) {
      q("#w-pull").textContent = mmss(heat.pullS);
      q("#w-pull").className = `big-val num ${heat.running ? "warn" : ""}`;
      const bar = q("#w-heat");
      bar.style.width = `${Math.min(100, heat.pct)}%`;
      bar.className = heat.state;
      q("#w-heat-txt").textContent = heat.state === "rest" ? `REST ${mmss(heat.restLeftS())}` : `${Math.round(heat.pct)}%`;
      q("#w-heat-txt").className = heat.state;
      this.renderHeat();
    }
    // The pull popup watches for disarm / movement on its own timer too, this is belt and braces.
    if ((this.phase === "count" || this.phase === "pull") && (!armed || st.get("mc.speed", 0) > 0.5))
      this.abort(!armed ? "Winch was disarmed." : "The Teryx moved.");

    const spd = st.get("mc.speed", 0);
    const checks = [
      [st.get("pico.online", false), "Control box online"],
      [st.get("mc.online") !== false && spd < 0.5, "Stopped"],
      [armed, "Armed"],
      [st.get("an.aux_12v", 13) >= 11.8, `12V battery ${st.get("an.aux_12v", 0).toFixed(1)} V`],
      [!hand, hand ? "Remote or hand switch in use" : "Remote and hand switches idle"],
      [!heat || heat.state !== "rest", !heat || heat.state !== "rest" ? "Winch motor OK" : "Winch motor resting"],
    ];
    const html = checks.map(([ok, t]) => `<div class="check ${ok ? "ok" : ""}"><i></i>${t}</div>`).join("");
    if (html !== this._c) { q("#w-checks").innerHTML = html; this._c = html; }
  }
}
