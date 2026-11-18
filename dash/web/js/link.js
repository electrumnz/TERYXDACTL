// Link to the dash gateway (the Python server on the Pi).
// Protocol: see docs/DASH_API.md in the test environment work.
//   server -> UI: {"type":"state","t":..,"state":{...}} at about 20 Hz
//   UI -> server: {"type":"request","id":..,"value":..}
//                 {"type":"hold","id":"act.tray"|"winch","value":1|-1|0} every 100 ms while held
//                 winch only: add "secs":N for a timed pull. The control box stops it after N s
//                 by itself, even if these keep coming.
// The Pi only ASKS. The control box (Pico) decides and the state feed shows what really happened.

import { DemoVehicle } from "./demo.js";

// The online copy for phones (GitHub Pages) has no Pi behind it, so it always runs the demo vehicle.
// Only these web hosts count: the Pi and the bench laptop are never on them.
export function isHostedDemo(host = location.hostname) {
  return /\.vercel\.app$/.test(host) || /\.github\.io$/.test(host);
}

export class Link {
  constructor(store) {
    this.store = store;
    this.ws = null;
    this.demo = null;
    this.connected = false;
    this.retry = 500;
    this.holds = new Map(); // id -> {value, timer}
  }

  start() {
    const params = new URLSearchParams(location.search);
    if (params.has("demo") || location.protocol === "file:" || isHostedDemo()) {
      this.startDemo(params.get("demo") || "drive");
      return;
    }
    this.connect();
  }

  startDemo(scenario) {
    this.demo = new DemoVehicle(scenario);
    this.connected = true;
    this.store.set({ "link.online": true, "link.demo": true });
    this.demo.onState = (s) => this.store.set(s);
    this.demo.start();
  }

  connect() {
    const url = (location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws";
    let ws;
    try { ws = new WebSocket(url); } catch (e) { return this.later(); }
    this.ws = ws;
    ws.onopen = () => {
      this.connected = true; this.retry = 500;
      this.store.set({ "link.online": true, "link.demo": false });
    };
    ws.onmessage = (ev) => {
      let msg; try { msg = JSON.parse(ev.data); } catch { return; }
      if (msg.type === "state" && msg.state) this.store.set(msg.state);
      else if (msg.type === "event") this.store.emit("event", msg);
    };
    ws.onclose = () => {
      this.connected = false;
      this.store.set({ "link.online": false, "pico.online": false });
      this.later();
    };
    ws.onerror = () => { try { ws.close(); } catch {} };
  }

  later() {
    setTimeout(() => this.connect(), this.retry);
    this.retry = Math.min(this.retry * 2, 4000);
  }

  send(obj) {
    if (this.demo) { this.demo.receive(obj); return true; }
    if (this.ws && this.ws.readyState === 1) { this.ws.send(JSON.stringify(obj)); return true; }
    return false;
  }

  /** Ask for something. The control box may say no. */
  request(id, value) {
    this.store.noteRequest(id, value);
    return this.send({ type: "request", id, value });
  }

  /** Start a hold-to-run. Repeats every 100 ms until holdStop(). The server stops it after 300 ms of silence. */
  holdStart(id, value, secs = 0) {
    this.holdStop(id, false);
    const msg = secs ? { type: "hold", id, value, secs } : { type: "hold", id, value };
    const tick = () => this.send(msg);
    tick();
    const timer = setInterval(tick, 100);
    this.holds.set(id, { value, timer });
  }

  holdStop(id, sendStop = true) {
    const h = this.holds.get(id);
    if (h) { clearInterval(h.timer); this.holds.delete(id); }
    if (sendStop) this.send({ type: "hold", id, value: 0 });
  }

  stopAllHolds() { for (const id of [...this.holds.keys()]) this.holdStop(id); }
}
