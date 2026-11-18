// Vehicle lock (docs/vehicle-lock.md): the keypad lock screen and the PIN pad Settings uses.
//
// The control box does the locking. This screen only shows what it says (lock.* in the state)
// and passes the digits on. Rebooting the Pi or unplugging the screen doesn't unlock anything:
// the lock lives in the control box's flash. Nothing here keeps the PIN.
import { el, toast } from "./ui/controls.js";
import { icon } from "./ui/icons.js";
import { Sound } from "./sound.js";

const RESULT_TEXT = {
  wrong: "Wrong PIN.",
  not_parked: "Stop, put the park brake on and let everything finish moving first.",
  no_pin: "Set a PIN first.",
  lockout: "Too many wrong tries. Wait for the timer.",
  bad_digits: "A PIN is 4 to 6 digits.",
  not_allowed: "Not allowed right now. Enter the current PIN first.",
  recovered: "Unlocked with the recovery code. The old PIN is gone, so set a new one.",
};
export const lockResultText = (r) => RESULT_TEXT[r] || "";

/** Send a lock command and wait for the control box's answer. Resolves with the result code. */
export function lockCommand(ctx, cmd, digits = "") {
  const st = ctx.store, before = st.get("lock.result_count");
  return new Promise((resolve) => {
    const sent = ctx.link.send({ type: "lock", cmd, digits });
    if (!sent) { resolve("no_link"); return; }
    const t0 = Date.now();
    const iv = setInterval(() => {
      const n = st.get("lock.result_count");
      if (n !== undefined && n !== before) { clearInterval(iv); resolve(st.get("lock.result")); }
      else if (Date.now() - t0 > 2500) { clearInterval(iv); resolve("no_answer"); }
    }, 40);
  });
}

/** Random 8 digit recovery code, made on the dash and sent once. Only its hash is kept. */
export function newRecoveryCode() {
  const a = new Uint32Array(2);
  (window.crypto || window.msCrypto).getRandomValues(a);
  return (String(a[0] % 10000).padStart(4, "0") + String(a[1] % 10000).padStart(4, "0"));
}

const fmtMmSs = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

/**
 * Number pad with dots. Glove-sized keys. onSubmit(digits) when the tick is pressed.
 * max = most digits it takes (8 lets the recovery code in on the lock screen).
 */
export function pinPad({ max = 6, min = 4, onSubmit, onChange }) {
  const root = el(`<div class="pin-pad"><div class="pin-dots" aria-live="polite"></div><div class="pin-keys"></div></div>`);
  const dots = root.querySelector(".pin-dots"), keys = root.querySelector(".pin-keys");
  let digits = "", disabled = false;
  const draw = () => {
    dots.innerHTML = "";
    const n = Math.max(min, digits.length);
    for (let i = 0; i < n; i++) dots.appendChild(el(`<i class="${i < digits.length ? "on" : ""}"></i>`));
    root.querySelector('[data-k="ok"]').classList.toggle("ready", digits.length >= min);
    onChange && onChange(digits);
  };
  const press = (k) => {
    if (disabled) return;
    if (k === "del") digits = digits.slice(0, -1);
    else if (k === "ok") { if (digits.length >= min) { const d = digits; digits = ""; draw(); onSubmit(d); } return; }
    else if (digits.length < max) digits += k;
    draw();
  };
  ["1", "2", "3", "4", "5", "6", "7", "8", "9", "del", "0", "ok"].forEach((k) => {
    const label = k === "del" ? icon("backspace") : k === "ok" ? "OK" : k;
    const b = el(`<button class="pin-key ${k === "ok" ? "ok" : k === "del" ? "del" : ""}" data-k="${k}" aria-label="${k === "del" ? "Delete" : k === "ok" ? "Enter" : k}">${label}</button>`);
    b.onclick = () => press(k);
    keys.appendChild(b);
  });
  draw();
  return {
    root,
    clear() { digits = ""; draw(); },
    shake() { root.classList.remove("shake"); void root.offsetWidth; root.classList.add("shake"); },
    setDisabled(b) { disabled = b; root.classList.toggle("disabled", b); if (b) { digits = ""; draw(); } },
  };
}

/** A pop-up with a PIN pad. Resolves with the digits, or null if cancelled. */
export function askPin(title, sub = "", { max = 6 } = {}) {
  return new Promise((resolve) => {
    const m = el(`<div class="lk-modal" role="dialog" aria-modal="true"><div class="lk-card">
      <div class="lk-card-head"><div><div class="lk-card-title"></div><div class="lk-card-sub"></div></div>
      <button class="btn sm lk-cancel">Cancel</button></div></div></div>`);
    m.querySelector(".lk-card-title").textContent = title;
    m.querySelector(".lk-card-sub").textContent = sub;
    const done = (v) => { m.remove(); resolve(v); };
    const pad = pinPad({ max, onSubmit: (d) => done(d) });
    m.querySelector(".lk-card").appendChild(pad.root);
    m.querySelector(".lk-cancel").onclick = () => done(null);
    document.getElementById("app").appendChild(m);
  });
}

/** Shows the recovery code once, big, until "Written it down" is pressed. */
export function showRecoveryCode(code) {
  return new Promise((resolve) => {
    const m = el(`<div class="lk-modal" role="dialog" aria-modal="true"><div class="lk-card lk-code-card">
      <div class="lk-card-title">Your recovery code</div>
      <div class="lk-code num">${code.slice(0, 4)} ${code.slice(4)}</div>
      <div class="lk-card-sub">If you forget the PIN, type this 8 digit code on the lock screen instead. It unlocks once and wipes the PIN.
        Write it down and keep it somewhere other than the Teryx. It won't be shown again.</div>
      <button class="btn lk-written">Written it down</button></div></div>`);
    m.querySelector(".lk-written").onclick = () => { m.remove(); resolve(); };
    document.getElementById("app").appendChild(m);
  });
}

/** Full-screen lock: the T. rex sleeps while locked and wakes on a wrong PIN. */
export class LockScreen {
  constructor(ctx) {
    this.ctx = ctx;
    this.shown = false;
    this.lastCount = undefined;
    this.root = el(`<div id="lock-screen" class="lock-screen" hidden aria-label="Vehicle locked">
      <div class="lk-art" aria-hidden="true"><i class="lk-sleep"></i><i class="lk-awake"></i></div>
      <div class="lk-side">
        <div class="lk-head"><img class="lk-padlock" src="img/dino/padlock.webp" alt="">
          <div><div class="lk-title">LOCKED</div><div class="lk-sub" id="lk-sub">Enter PIN to unlock</div></div></div>
        <div class="lk-msg" id="lk-msg"></div>
      </div>
      <div class="lk-foot" id="lk-foot">Forgot the PIN? Type your 8 digit recovery code instead.</div>
    </div>`);
    this.pad = pinPad({ max: 8, onSubmit: (d) => this.submit(d) });
    this.root.querySelector(".lk-side").insertBefore(this.pad.root, this.root.querySelector("#lk-msg"));
    this.msg = this.root.querySelector("#lk-msg");
    this.sub = this.root.querySelector("#lk-sub");
    document.getElementById("app").appendChild(this.root);
  }

  async submit(digits) {
    this.msg.textContent = "Checking…"; this.msg.className = "lk-msg";
    const r = await lockCommand(this.ctx, "unlock", digits);
    if (r === "ok" || r === "recovered") return;   // update() handles the unlock
    if (r === "no_link" || r === "no_answer") { this.msg.textContent = "No answer from the control box. Try again."; return; }
    this.wake();
    this.pad.shake();
    Sound.play("reject");
  }

  wake() {
    this.root.classList.add("awake");
    clearTimeout(this._sleep);
    this._sleep = setTimeout(() => { if (!this.lockout) this.root.classList.remove("awake"); }, 2600);
  }

  update(st) {
    const locked = st.get("lock.state") === "locked";
    if (locked !== this.shown) {
      this.shown = locked;
      this.root.hidden = !locked;
      if (locked) {
        this.ctx.link.stopAllHolds();
        this.pad.clear();
        this.msg.textContent = "";
        document.getElementById("app").classList.add("is-locked");
      } else {
        document.getElementById("app").classList.remove("is-locked");
        this.root.classList.remove("awake");
        if (this.lastCount !== undefined) {
          Sound.play("info");
          toast(st.get("lock.result") === "recovered" ? lockResultText("recovered") : "Unlocked. Good to go.", "good");
        }
      }
    }
    const count = st.get("lock.result_count");
    this.lastCount = count;
    if (!locked) return;
    this.lockout = !!st.get("lock.lockout");
    this.pad.setDisabled(this.lockout);
    if (this.lockout) {
      this.root.classList.add("awake");
      this.msg.className = "lk-msg bad";
      this.msg.textContent = `Too many wrong tries. Try again in ${fmtMmSs(st.get("lock.lockout_s", 0))}.`;
    } else if (st.get("lock.result") === "wrong") {
      const left = st.get("lock.tries_left", 0);
      this.msg.className = "lk-msg bad";
      this.msg.textContent = `Wrong PIN. ${left} ${left === 1 ? "try" : "tries"} left before a wait.`;
    } else if (this.msg.textContent === "Checking…") {
      this.msg.textContent = "";
    }
    this.sub.textContent = st.get("mc.speed", 0) > 1 ? "Rolling, but drive is off while locked" : "Enter PIN to unlock";
  }
}
