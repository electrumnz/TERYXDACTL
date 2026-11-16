// Tiny client for the Teryx dash websocket. No build step, no libraries.
//
//   const t = new TeryxLink();
//   t.onState(s => console.log(s["mc.speed"]));
//   t.request("light.front_1", 200);
//   t.holdButton(el, "act.tray", 1);   // hold-to-run while the finger is down
//
// See docs/DASH_API.md for every state key and request id.
class TeryxLink {
  constructor(url) {
    this.url = url || `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;
    this.state = {};
    this.connected = false;
    this._state = [];
    this._conn = [];
    this._err = [];
    this._connect();
  }
  onState(fn) { this._state.push(fn); }
  onConnection(fn) { this._conn.push(fn); }
  onError(fn) { this._err.push(fn); }
  _connect() {
    const ws = new WebSocket(this.url);
    this.ws = ws;
    ws.onopen = () => { this.connected = true; this._conn.forEach(f => f(true)); };
    ws.onclose = () => {
      this.connected = false;
      this._conn.forEach(f => f(false));
      setTimeout(() => this._connect(), 1000);
    };
    ws.onmessage = ev => {
      const m = JSON.parse(ev.data);
      if (m.type === "state") { this.state = m.state; this._state.forEach(f => f(m.state, m.t)); }
      else if (m.type === "error") this._err.forEach(f => f(m.error));
    };
  }
  send(obj) { if (this.ws && this.ws.readyState === 1) this.ws.send(JSON.stringify(obj)); }
  request(id, value) { this.send({ type: "request", id, value }); }
  hold(id, value) { this.send({ type: "hold", id, value }); }
  setting(key, value) { this.send({ type: "setting", key, value }); }
  sim(cmd) { this.send({ type: "sim", cmd }); }

  // Hold-to-run: sends `value` every 100 ms while pressed, 0 on release.
  holdButton(el, id, value) {
    let timer = null;
    const stop = () => {
      if (!timer) return;
      clearInterval(timer); timer = null;
      el.classList.remove("held");
      this.hold(id, 0);
    };
    el.addEventListener("pointerdown", e => {
      e.preventDefault();
      el.setPointerCapture?.(e.pointerId);
      el.classList.add("held");
      this.hold(id, value);
      timer = setInterval(() => this.hold(id, value), 100);
    });
    ["pointerup", "pointercancel", "lostpointercapture"].forEach(n => el.addEventListener(n, stop));
    window.addEventListener("blur", stop);
  }
}
window.TeryxLink = TeryxLink;
