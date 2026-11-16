// Live state store. Holds the latest state from the gateway, plus what we last asked for,
// so screens can show "asked, waiting for the control box" and spot refusals.

export class Store {
  constructor() {
    this.s = {};
    this.subs = new Set();
    this.events = new Map();
    this.requests = new Map(); // id -> {value, at}
    this.lastReject = 0;
  }
  get(k, d = undefined) { const v = this.s[k]; return v === undefined ? d : v; }
  set(patch) {
    Object.assign(this.s, patch);
    const rc = this.s["pico.reject_count"];
    if (rc !== undefined && rc !== this.lastReject) {
      if (this.lastReject !== 0 || this._seenReject) this.emit("reject", this.s["pico.reject"]);
      this.lastReject = rc; this._seenReject = true;
    }
    this._dirty = true;
  }
  noteRequest(id, value) { this.requests.set(id, { value, at: Date.now() }); this._dirty = true; }
  pending(id) { return this.requests.get(id); }
  clearRequest(id) { this.requests.delete(id); }
  subscribe(fn) { this.subs.add(fn); return () => this.subs.delete(fn); }
  on(name, fn) { if (!this.events.has(name)) this.events.set(name, new Set()); this.events.get(name).add(fn); }
  emit(name, arg) { (this.events.get(name) || []).forEach((fn) => fn(arg)); }
  // Render loop: screens update at most once a frame, only when something changed.
  loop() {
    const tick = () => {
      if (this._dirty) { this._dirty = false; this.subs.forEach((fn) => fn(this)); }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
}
