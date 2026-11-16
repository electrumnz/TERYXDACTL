// On-screen keyboard for the touch screen: Wi-Fi names and passwords, light names, anything typed.
// Big keys (about 14 mm) so it works with gloves. Letters, numbers and symbols pages,
// shift (tap once for one capital, twice for caps lock), hold backspace to delete fast,
// and show/hide for passwords. A real keyboard plugged into the Pi works too.
//
//   const text = await keyboard({ title: "Wi-Fi password", password: true, minLength: 8 });
//   // text is null if cancelled

import { el } from "./controls.js";
import { icon } from "./icons.js";
import { Sound } from "../sound.js";

const PAGES = {
  abc: [
    ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
    ["a", "s", "d", "f", "g", "h", "j", "k", "l", "'"],
    ["shift", "z", "x", "c", "v", "b", "n", "m", "-", "back"],
    ["123", ",", "space", ".", "done"],
  ],
  "123": [
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
    ["@", "#", "$", "&", "*", "(", ")", "'", "\"", "_"],
    ["#+=", "%", "-", "+", "=", "/", ";", ":", "!", "back"],
    ["abc", ",", "space", ".", "done"],
  ],
  "#+=": [
    ["~", "`", "|", "\\", "<", ">", "{", "}", "[", "]"],
    ["^", "€", "£", "¥", "°", "•", "§", "¿", "¡", "?"],
    ["123", "<", ">", "=", "+", "/", "?", "!", ",", "back"],
    ["abc", ",", "space", ".", "done"],
  ],
};

let open = null;   // only one keyboard at a time

export function keyboard(opts = {}) {
  if (open) open.cancel();
  return new Promise((resolve) => { open = new Keyboard(opts, (v) => { open = null; resolve(v); }); });
}

export function keyboardOpen() { return !!open; }

class Keyboard {
  constructor({ title = "Type", value = "", password = false, minLength = 0, maxLength = 64, hint = "", doneLabel = "Done" }, finish) {
    Object.assign(this, { value: String(value), password, minLength, maxLength, finish, page: "abc", shift: false, caps: false, reveal: false });
    this.root = el(`
      <div class="kb-overlay" role="dialog">
        <div class="kb">
          <div class="kb-head">
            <div class="kb-title"></div>
            <button class="kb-cancel btn sm">Cancel</button>
          </div>
          <div class="kb-field-row">
            <div class="kb-field" aria-live="polite"><span class="kb-text"></span><span class="kb-caret"></span></div>
            ${password ? `<button class="kb-eye btn sm" aria-label="Show password">${icon("eye")}</button>` : ""}
          </div>
          <div class="kb-hint"></div>
          <div class="kb-keys"></div>
        </div>
      </div>`);
    this.doneLabel = doneLabel;
    this.root.querySelector(".kb-title").textContent = title;
    this.root.setAttribute("aria-label", title);
    this.text = this.root.querySelector(".kb-text");
    this.hintEl = this.root.querySelector(".kb-hint");
    this.hint = hint;
    this.keys = this.root.querySelector(".kb-keys");
    this.root.querySelector(".kb-cancel").onclick = () => this.cancel();
    // Taps on the dimmed area do nothing (and don't reach the screen underneath).
    this.root.addEventListener("pointerdown", (e) => { if (e.target === this.root) e.preventDefault(); });
    const eye = this.root.querySelector(".kb-eye");
    if (eye) eye.onclick = () => { this.reveal = !this.reveal; eye.innerHTML = icon(this.reveal ? "eyeoff" : "eye"); this.render(); };
    this.onKey = (e) => this.physical(e);
    window.addEventListener("keydown", this.onKey, true);
    (document.getElementById("app") || document.body).appendChild(this.root);
    this.build();
    this.render();
  }

  build() {
    this.keys.innerHTML = "";
    PAGES[this.page].forEach((row, ri) => {
      const r = el(`<div class="kb-row r${ri}"></div>`);
      row.forEach((k) => {
        const b = el(`<button class="kb-key" data-k="${k === '"' ? "&quot;" : k}"></button>`);
        if (k === "shift") { b.innerHTML = icon("shift"); b.classList.add("fn", "shift"); }
        else if (k === "back") { b.innerHTML = icon("backspace"); b.classList.add("fn"); b.setAttribute("aria-label", "Backspace"); }
        else if (k === "space") { b.textContent = "space"; b.classList.add("space"); }
        else if (k === "done") { b.textContent = this.doneLabel; b.classList.add("done"); }
        else if (k === "123" || k === "abc" || k === "#+=") { b.textContent = k; b.classList.add("fn"); }
        else b.textContent = k;
        this.bindKey(b, k);
        r.appendChild(b);
      });
      this.keys.appendChild(r);
    });
    this.renderShift();
  }

  bindKey(b, k) {
    let repeat = null, delay = null;
    const stop = () => { clearTimeout(delay); clearInterval(repeat); delay = repeat = null; b.classList.remove("down"); };
    // Done acts on release, so the lift of the finger can't land on whatever is under the keyboard.
    if (k === "done") { b.addEventListener("click", () => this.press(k)); }
    b.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      b.classList.add("down");
      if (k !== "done") this.press(k);
      if (k === "back") delay = setTimeout(() => (repeat = setInterval(() => this.press("back"), 70)), 450);
    });
    b.addEventListener("pointerup", stop);
    b.addEventListener("pointerleave", stop);
    b.addEventListener("pointercancel", stop);
    b.addEventListener("contextmenu", (e) => e.preventDefault());
  }

  press(k) {
    if (k === "back") this.value = [...this.value].slice(0, -1).join("");
    else if (k === "space") this.add(" ");
    else if (k === "done") return this.done();
    else if (k === "shift") {
      const now = Date.now();
      if (this.caps) { this.caps = false; this.shift = false; }
      else if (this.shift && now - (this._lastShift || 0) < 400) { this.caps = true; }
      else this.shift = !this.shift;
      this._lastShift = now;
      this.renderShift();
      return;
    } else if (k === "123" || k === "abc" || k === "#+=") { this.page = k; this.build(); return; }
    else {
      this.add(this.page === "abc" && (this.shift || this.caps) ? k.toUpperCase() : k);
      if (this.shift && !this.caps) { this.shift = false; this.renderShift(); }
    }
    this.render();
  }

  add(ch) { if ([...this.value].length < this.maxLength) this.value += ch; else this.flash(`That's the most it takes (${this.maxLength}).`); }

  physical(e) {
    if (e.key === "Escape") this.cancel();
    else if (e.key === "Enter") this.done();
    else if (e.key === "Backspace") this.press("back");
    else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey) { this.add(e.key); this.render(); }
    else return;
    e.preventDefault(); e.stopPropagation();
  }

  renderShift() {
    const up = this.page === "abc" && (this.shift || this.caps);
    this.keys.querySelectorAll(".kb-key").forEach((b) => {
      const k = b.dataset.k;
      if (k.length === 1 && this.page === "abc") b.textContent = up ? k.toUpperCase() : k;
    });
    const sh = this.keys.querySelector(".shift");
    if (sh) { sh.classList.toggle("on", this.shift || this.caps); sh.classList.toggle("caps", this.caps); }
  }

  render() {
    this.text.textContent = this.password && !this.reveal ? "•".repeat([...this.value].length) : this.value;
    const d = this.keys.querySelector(".done");
    const short = this.minLength && this.value.length > 0 && this.value.length < this.minLength;
    if (d) d.classList.toggle("locked", !!short);
    this.hintEl.textContent = short ? `At least ${this.minLength} characters (${this.value.length} so far)` : this.hint;
    this.hintEl.classList.toggle("warn", !!short);
  }

  flash(msg) { this.hintEl.textContent = msg; this.hintEl.classList.add("warn"); }

  done() {
    if (this.minLength && this.value.length > 0 && this.value.length < this.minLength) {
      this.flash(`Needs at least ${this.minLength} characters.`); Sound.play("reject"); return;
    }
    this.close(); this.finish(this.value);
  }

  cancel() { this.close(); this.finish(null); }

  close() { window.removeEventListener("keydown", this.onKey, true); this.root.remove(); }
}
