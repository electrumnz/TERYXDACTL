// Safe 4WD / diff lock changes (docs/drive-changes.md), as the dash sees them.
//
// The control box does the real work: if a change can't happen yet (too fast),
// it waits up to shift_wait_ms for the speed to come right, then runs it, and
// gives up after that. This file only tracks each change so the buttons can
// show a spinner, a hint, a countdown and a Cancel while it waits, then a tick
// and a pulse when it's done (or a different look if it timed out or was cancelled).
//
// Phases: idle, asked (sent, nothing back yet), waiting, moving,
//         done, timeout, cancelled, failed. The last four fade back to idle.
import { toast } from "./controls.js";
import { Sound } from "../sound.js";

const SETTLE_MS = 1800;       // how long done / timeout / cancelled stay on show
const ASK_GRACE_MS = 2500;    // asked but nothing changed: the box ignored it (already there)

export class ShiftWatch {
  constructor(ctx) {
    this.ctx = ctx;
    this.items = {
      fourwd: { phase: "idle", target: null, at: 0, waitFrom: 0 },
      diff: { phase: "idle", target: null, at: 0, waitFrom: 0 },
    };
    ctx.store.on("reject", (code) => this.onReject(code));
  }

  get(name) { return this.items[name]; }
  waitMs() { return this.ctx.picoLimit("shift_wait_ms", 10000); }
  // Seconds left before the control box gives up waiting.
  secsLeft(name) {
    const it = this.items[name];
    if (it.phase !== "waiting") return null;
    return Math.max(0, Math.ceil((this.waitMs() - (Date.now() - it.waitFrom)) / 1000));
  }
  // Another drive change is waiting or running, so this one is locked for now.
  busy(except) {
    return Object.entries(this.items).some(([k, it]) => k !== except && ["asked", "waiting", "moving"].includes(it.phase));
  }
  active(name) { return ["asked", "waiting", "moving"].includes(this.items[name].phase); }

  set(name, phase) {
    const it = this.items[name];
    if (it.phase === phase) return;
    it.phase = phase; it.at = Date.now();
    if (phase === "waiting") it.waitFrom = Date.now();
    this.ctx.store._dirty = true;
  }

  // ---- taps
  ask4wd(v) {
    const st = this.ctx.store, fw = st.get("act.4wd", "2wd");
    if (fw === (v ? "4wd" : "2wd") && !st.get("act.4wd_wait")) return;  // already there
    this.items.fourwd.target = v;
    this.set("fourwd", "asked");
    this.ctx.link.request("act.4wd", v);
  }
  askDiff(v) {
    const st = this.ctx.store;
    if (Math.abs(v - st.get("an.diff_pos", 0)) <= 2 && !st.get("act.diff_wait")) return;
    this.items.diff.target = v;
    this.set("diff", "asked");
    this.ctx.link.request("act.diff", v);
  }
  // Cancel = ask the control box for what's already there.
  cancel(name) {
    const st = this.ctx.store;
    if (name === "fourwd") {
      const fw = st.get("act.4wd", "2wd");
      this.ctx.link.request("act.4wd", fw === "4wd" ? 1 : 0);
    } else {
      this.ctx.link.request("act.diff", Math.round(st.get("an.diff_pos", 0)));
    }
    this.set(name, "cancelled");
    Sound.play("info");
    toast(name === "fourwd" ? "4WD change cancelled." : "Diff lock change cancelled.");
  }

  onReject(code) {
    // The reject toast itself comes from app.js. Here we just change the button's look.
    // A time-out ends whatever was waiting; any other refusal only counts for a
    // fresh tap (a tray refusal mustn't mark a waiting 4WD change as failed).
    for (const name of Object.keys(this.items)) {
      const ph = this.items[name].phase;
      if (code === "wait_timeout" && ph === "waiting") this.set(name, "timeout");
      else if (code !== "wait_timeout" && ph === "asked") this.set(name, "failed");
    }
  }

  // ---- every state update
  update(st) {
    const now = Date.now();
    const f = this.items.fourwd, fw = st.get("act.4wd", "2wd");
    if (st.get("act.4wd_wait")) {
      this.set("fourwd", "waiting");
    } else if (fw.startsWith("to_")) {
      if (f.target == null) f.target = fw === "to_4wd" ? 1 : 0;
      this.set("fourwd", "moving");
    } else if (this.active("fourwd")) {
      if (fw === (f.target ? "4wd" : "2wd") && (f.phase !== "asked" || now - f.at > 300)) {
        this.set("fourwd", "done");
        Sound.play("shifted");
        toast(f.target ? "4WD engaged." : "Back in 2WD.", "good");
      } else if (fw === "fault" || f.phase === "waiting") {
        // Fault, or the box dropped the wait for a reason of its own (the reject says why)
        this.set("fourwd", "failed");
      } else if (f.phase === "asked" && now - f.at > ASK_GRACE_MS) {
        this.set("fourwd", "idle");
      }
    }

    const d = this.items.diff, pos = st.get("an.diff_pos", 0), tgt = st.get("act.diff_target", pos);
    if (st.get("act.diff_wait")) {
      this.set("diff", "waiting");
    } else if (d.phase === "waiting") {
      this.set("diff", Math.abs(tgt - (d.target ?? pos)) <= 2 ? "moving" : "failed");
    } else if (Math.abs(tgt - pos) > 2 && this.active("diff")) {
      this.set("diff", "moving");
    } else if (this.active("diff")) {
      if (d.target != null && Math.abs(pos - d.target) <= 3 && (d.phase !== "asked" || now - d.at > 300)) {
        this.set("diff", "done");
        Sound.play("shifted");
        const p = Math.round(d.target);
        toast(p <= 2 ? "Front diff open." : p >= 98 ? "Front diff fully locked." : `Front diff lock at ${p}%.`, "good");
      } else if (d.phase === "moving" || now - d.at > ASK_GRACE_MS) {
        // Stopped short (sped up past the limit mid-move, or a fault)
        this.set("diff", Math.abs(pos - (d.target ?? pos)) <= 3 ? "done" : "failed");
      }
    }

    for (const name of Object.keys(this.items)) {
      const it = this.items[name];
      if (["done", "timeout", "cancelled", "failed"].includes(it.phase) && now - it.at > SETTLE_MS) this.set(name, "idle");
    }
    // Redraw twice a second while something waits, for the countdown (not every
    // frame, to keep the Pi cool).
    const waiting = f.phase === "waiting" || d.phase === "waiting";
    if (waiting && !this.ticker) this.ticker = setInterval(() => { this.ctx.store._dirty = true; }, 500);
    if (!waiting && this.ticker) { clearInterval(this.ticker); this.ticker = null; }
    // ...and once more after a done / cancelled look, so it fades back
    const settling = Object.values(this.items).some((it) => ["done", "timeout", "cancelled", "failed"].includes(it.phase));
    if (settling && !this.settleT) this.settleT = setTimeout(() => { this.settleT = null; this.ctx.store._dirty = true; }, SETTLE_MS + 50);
  }
}

// The hint under a waiting button, in plain words.
export function waitHint(ctx, name) {
  if (name === "fourwd") {
    const lim = ctx.picoLimit("fourwd_max_kmh", 1);
    return lim <= 1 ? "Stop to shift" : `Slow down to ${lim} km/h`;
  }
  return `Slow down to ${ctx.picoLimit("diff_max_kmh", 15)} km/h`;
}
