// Lights: 4 front bars, interior bar, headlights, tails, rear floods, beacon, trailer bar and the
// light show. Each front bar is set up as dimmable or on/off in Settings. Everything else dims
// through the control box's PWM board (docs/lights.md), which also makes the safety calls:
// brake lights always full, headlights and tails only dim when parked, show parked only.
import { el, $, Slider } from "../ui/controls.js";
import { LIGHTS } from "../settings.js";
import { vehicleDiagram } from "../ui/vehicle.js";

// Effect names match the control box (LIGHT_EFFECT in teryx/canbus/messages.py). "none" is steady.
const EFFECTS = [["none", "Steady"], ["breathe", "Breathe"], ["strobe", "Strobe"], ["chase", "Chase"], ["outside_only", "Outside pair"], ["inside_only", "Inside pair"]];
// "sos" is also supported by the control box but kept off the main grid so it isn't hit by accident.
const SHOWS = [["wave", "Wave"], ["breathe", "Breathe"], ["roar", "Roar"], ["party", "Party"]];
const pct = (v) => Math.round((v / 255) * 100);
const lvl = (p) => Math.round((p / 100) * 255);

export class LightsScreen {
  constructor(ctx) {
    this.ctx = ctx; this.id = "lights"; this.label = "Lights"; this.icon = "lights";
    this.want = Object.fromEntries(LIGHTS.map((l) => [l.id, 0]));
    this.lastLevel = Object.fromEntries(LIGHTS.map((l) => [l.id, 255]));
    this.effect = "none"; this.rear = "auto";
    this.head = "off"; this.showSel = "none";
    this.more = { "light.head_level": 255, "light.tail": 0, "light.rear_level": 0, "light.trailer_bar": 0, "light.beacon": 0 };
    this.lastBeacon = 255;
  }

  mount(root) {
    root.innerHTML = `
      <div class="lights">
        <div class="col">
          <div class="light-grid" id="l-front"></div>
          <div class="light-grid" id="l-other"></div>
          <div class="light-grid" id="l-more"></div>
        </div>
        <div class="col lights-side">
          <div class="panel">
            <h3>Headlights</h3>
            <div class="seg" id="l-head"><button data-v="off">Off</button><button data-v="low">Low</button><button data-v="high">High</button></div>
            <div id="l-head-dim" style="margin-top:8px"></div>
            <div class="muted small" style="margin-top:4px">Only dims when parked. Always full on the move.</div>
          </div>
          <div class="panel">
            <h3>Front bars</h3>
            <div class="fx-grid" id="l-groups"></div>
            <div class="fx-grid" id="l-fx" style="margin-top:8px"></div>
          </div>
          <div class="panel grow">
            <h3>Light show</h3>
            <div class="fx-grid" id="l-show"></div>
            <div class="muted small" id="l-show-state" style="margin-top:6px">Parked only: key on, park brake on, stopped. Brake lights still work.</div>
          </div>
        </div>
      </div>`;
    this.root = root;
    this.tiles = {};
    const front = $(root, "#l-front"), other = $(root, "#l-other");
    LIGHTS.forEach((l, i) => (i < 4 ? front : other).appendChild(this.makeTile(l)));
    other.appendChild(this.makeRearTile());
    other.lastElementChild.style.gridColumn = "span 2";
    const more = $(root, "#l-more");
    more.appendChild(this.makeLevelTile("light.tail", "Tail lights", "Brake always full", { zeroText: "AUTO", min: 0 }));
    more.appendChild(this.makeLevelTile("light.beacon", "Roof beacon", "Flashes 3 times a second", { toggle: true, min: 10 }));
    this.trailerTile = this.makeLevelTile("light.trailer_bar", "Trailer bar", "Only with the trailer plugged in", { toggle: true, min: 10 });
    this.trailerTile.appendChild(el(`<div class="lt-sub">Trailer tail <b id="l-tt">--</b> · brake <b id="l-tb">--</b></div>`));
    more.appendChild(this.trailerTile);
    more.lastElementChild.style.gridColumn = "span 2";

    this.root.querySelectorAll("#l-head button").forEach((b) => (b.onclick = () => this.setHead(b.dataset.v)));
    this.headSlider = new Slider({ min: 10, max: 100, step: 5, label: "Brightness", fmt: (v) => `${v}%`, onChange: (v) => this.setMore("light.head_level", lvl(v)) });
    $(root, "#l-head-dim").appendChild(this.headSlider.root);
    this.paintHead();
    const sh = $(root, "#l-show");
    SHOWS.forEach(([k, label]) => {
      const b = el(`<button class="btn sm" data-show="${k}">${label}</button>`);
      b.onclick = () => this.setShow(this.showSel === k ? "none" : k);
      sh.appendChild(b);
    });
    const stop = el(`<button class="btn sm wide" data-show="none">Stop show</button>`);
    stop.onclick = () => this.setShow("none");
    sh.appendChild(stop);
    this.paintShow();

    const vp = el(`<div class="light-tile" style="align-items:center;justify-content:center;padding:4px"></div>`);
    this.veh = vehicleDiagram(); this.veh.root.classList.add("tiny"); vp.appendChild(this.veh.root); other.appendChild(vp);
    const g = $(root, "#l-groups");
    const groups = [["all_on", "All on"], ["all_off", "All off"], ["trail", "Trail"], ["work", "Work"], ["spot", "Spot"]];
    groups.forEach(([k, label]) => {
      const b = el(`<button class="btn sm" data-g="${k}">${label}</button>`);
      b.onclick = () => this.group(k);
      g.appendChild(b);
    });
    const fx = $(root, "#l-fx");
    EFFECTS.forEach(([k, label]) => {
      const b = el(`<button class="btn sm" data-fx="${k}">${label}</button>`);
      b.onclick = () => { this.effect = k; this.ctx.link.request("light.effect", k); this.paintFx(); };
      fx.appendChild(b);
    });
    this.paintFx();
    // Subscribe once only: rebuild() calls mount() again, and adding a subscriber while the
    // settings are telling subscribers about a change used to loop forever (renaming a bar hung the dash).
    if (!this._subbed) { this._subbed = true; this.ctx.settings.subscribe((path) => { if (path.startsWith("lights.")) this.rebuild(); }); }
  }

  rebuild() { const r = this.root; r.innerHTML = ""; this.mount(r); }

  makeTile(l) {
    const cfg = this.ctx.settings.light(l.id);
    const t = el(`<div class="light-tile" data-id="${l.id}">
      <div class="lt-head"><div><div class="lt-name">${cfg.name}</div><div class="lt-sub">${l.where}</div></div></div>
      <button class="lt-big">OFF</button>
      <div class="lt-dim"></div>
      <div class="lt-sub lt-mode">${cfg.dimmable ? "" : "On / off only"}</div>
    </div>`);
    const big = t.querySelector(".lt-big");
    big.onclick = () => this.set(l.id, this.want[l.id] > 0 ? 0 : cfg.dimmable ? this.lastLevel[l.id] : 255);
    let slider = null;
    if (cfg.dimmable) {
      slider = new Slider({ min: 0, max: 100, step: 5, label: "", fmt: (v) => `${v}%`, onChange: (v) => this.set(l.id, Math.round((v / 100) * 255)) });
      t.querySelector(".lt-dim").appendChild(slider.root);
    }
    this.tiles[l.id] = { root: t, big, slider, cfg };
    return t;
  }

  makeRearTile() {
    const t = el(`<div class="light-tile" data-id="light.rear">
      <div class="lt-head"><div><div class="lt-name">Rear pods</div><div class="lt-sub">2x 4" reverse / work</div></div><span class="pill" id="l-rear-state">OFF</span></div>
      <div class="seg" id="l-rear"><button data-v="off">Off</button><button data-v="auto">Auto in reverse</button><button data-v="on">On</button></div>
      <div class="lt-dim"></div>
    </div>`);
    t.querySelectorAll("#l-rear button").forEach((b) => (b.onclick = () => { this.rear = b.dataset.v; this.ctx.link.request("light.rear", this.rear); this.paintRear(); }));
    this.rearSlider = new Slider({ min: 10, max: 100, step: 5, label: "When on", fmt: (v) => `${v}%`, onChange: (v) => this.setMore("light.rear_level", lvl(v)) });
    this.rearSlider.set(100);
    t.querySelector(".lt-dim").appendChild(this.rearSlider.root);
    this.rearTile = t;
    this.paintRear();
    return t;
  }

  // A tile for one 0x706 level: slider, and an on/off button if toggle is set.
  makeLevelTile(id, name, sub, { toggle = false, zeroText = "OFF", min = 0 } = {}) {
    const t = el(`<div class="light-tile" data-id="${id}">
      <div class="lt-head"><div><div class="lt-name">${name}</div><div class="lt-sub">${sub}</div></div></div>
      ${toggle ? `<button class="lt-big">OFF</button>` : ""}
      <div class="lt-dim"></div>
    </div>`);
    const slider = new Slider({ min, max: 100, step: 5, label: "", fmt: (v) => (v === 0 ? zeroText : `${v}%`), onChange: (v) => this.setMore(id, lvl(v)) });
    t.querySelector(".lt-dim").appendChild(slider.root);
    const big = t.querySelector(".lt-big");
    if (big) big.onclick = () => this.setMore(id, this.more[id] > 0 ? 0 : (this.lastOn?.[id] || 255));
    this.levelTiles = this.levelTiles || {};
    this.levelTiles[id] = { root: t, slider, big, zeroText };
    this.paintLevel(id);
    return t;
  }

  setMore(id, v) {
    this.more[id] = v;
    if (v > 0) { this.lastOn = this.lastOn || {}; this.lastOn[id] = v; }
    this.ctx.link.request(id, v);
    if (id === "light.head_level") this.paintHead(); else if (id === "light.rear_level") this.rearSlider.set(pct(v) || 100); else this.paintLevel(id);
  }

  setHead(v) { this.head = v; this.ctx.link.request("light.head", v); this.paintHead(); }
  setShow(v) { this.showSel = v; this.ctx.link.request("light.show", v); this.paintShow(); }

  paintLevel(id) {
    const t = this.levelTiles && this.levelTiles[id]; if (!t) return;
    const v = this.more[id];
    t.root.classList.toggle("on", v > 0);
    if (t.big) t.big.textContent = v > 0 ? `ON ${pct(v)}%` : "OFF";
    t.slider.set(pct(v));
  }

  paintHead() {
    this.root.querySelectorAll("#l-head button").forEach((b) => b.classList.toggle("on", b.dataset.v === this.head));
    this.headSlider.set(pct(this.more["light.head_level"]) || 100);
  }

  paintShow() { this.root.querySelectorAll("[data-show]").forEach((b) => b.classList.toggle("on", b.dataset.show === this.showSel && this.showSel !== "none")); }

  set(id, v) {
    const cfg = this.ctx.settings.light(id);
    if (!cfg.dimmable) v = v > 0 ? 255 : 0;
    this.want[id] = v;
    if (v > 0) this.lastLevel[id] = v;
    this.ctx.link.request(id, v);
    this.paintTile(id);
  }

  group(k) {
    const front = LIGHTS.slice(0, 4).map((l) => l.id);
    if (k === "all_on") front.forEach((id) => this.set(id, this.lastLevel[id] || 255));
    else if (k === "all_off") front.forEach((id) => this.set(id, 0));
    else { const p = this.ctx.settings.get("lightPresets")[k] || {}; front.forEach((id) => this.set(id, p[id] ?? 0)); }
  }

  paintTile(id) {
    const tile = this.tiles[id]; if (!tile) return;
    const v = this.want[id];
    tile.root.classList.toggle("on", v > 0);
    tile.big.textContent = v > 0 ? (tile.cfg.dimmable ? `ON ${Math.round((v / 255) * 100)}%` : "ON") : "OFF";
    if (tile.slider) tile.slider.set(Math.round((v / 255) * 100));
  }

  paintFx() { this.root.querySelectorAll("[data-fx]").forEach((b) => b.classList.toggle("on", b.dataset.fx === this.effect)); }
  paintRear() { this.rearTile.querySelectorAll("#l-rear button").forEach((b) => b.classList.toggle("on", b.dataset.v === this.rear)); }

  update(st) {
    // Follow what the control box reports, unless we've just asked for something (it may still be catching up).
    LIGHTS.forEach((l) => {
      const p = st.pending(l.id);
      const actual = st.get(l.id);
      if (actual == null) return;
      const echo = st.get(`req.${l.id}`);
      if (echo != null && (!p || Date.now() - p.at > 1500)) {
        if (echo !== this.want[l.id]) { this.want[l.id] = echo; if (echo > 0) this.lastLevel[l.id] = echo; }
      } else if (!p || Date.now() - p.at > 1500) {
        // With an effect running the actual level flickers, so only follow it when steady.
        if (st.get("light.effect", "none") === "none" && actual !== this.want[l.id]) { this.want[l.id] = actual; if (actual > 0) this.lastLevel[l.id] = actual; }
      }
      this.paintTile(l.id);
      const tile = this.tiles[l.id];
      if (tile && tile.slider) tile.slider.setActual((actual / 255) * 100);
    });
    const rearReq = st.get("req.light.rear");
    if (rearReq && rearReq !== this.rear && !st.pending("light.rear")) { this.rear = rearReq; this.paintRear(); }
    const fx = st.get("req.light.effect") ?? st.get("light.effect");
    if (fx && fx !== this.effect && !st.pending("light.effect")) { this.effect = fx; this.paintFx(); }
    this.veh.update(st);
    const rearOn = !!st.get("light.rear");
    const pill = $(this.root, "#l-rear-state");
    pill.textContent = rearOn ? "ON" : "OFF"; pill.className = `pill ${rearOn ? "warn" : "muted"}`;
    this.rearTile.classList.toggle("on", rearOn);
    $(this.root, "#l-tt").textContent = st.get("trailer.tail") ? "on" : "off";
    $(this.root, "#l-tb").textContent = st.get("trailer.brake") ? "on" : "off";
    // Headlights, tails, floods, beacon, trailer bar, show: follow the gateway's echo of our requests
    const head = st.get("req.light.head");
    if (head && head !== this.head && !st.pending("light.head")) { this.head = head; this.paintHead(); }
    for (const id of Object.keys(this.more)) {
      const r = st.get(`req.${id}`);
      if (r != null && r !== this.more[id] && !st.pending(id)) {
        this.more[id] = r;
        if (id === "light.head_level") this.paintHead(); else if (id === "light.rear_level") this.rearSlider.set(pct(r) || 100); else this.paintLevel(id);
      }
    }
    const show = st.get("req.light.show");
    if (show && show !== this.showSel && !st.pending("light.show")) { this.showSel = show; this.paintShow(); }
    const ss = $(this.root, "#l-show-state");
    if (st.get("light.show_running")) { ss.textContent = "Show running. It stops the moment the Teryx moves."; ss.className = "small ok"; }
    else if (st.get("light.show_blocked")) { ss.textContent = "Waiting: key on, park brake on and stopped first."; ss.className = "small warn"; }
    else { ss.textContent = "Parked only: key on, park brake on, stopped. Brake lights still work."; ss.className = "muted small"; }
    if (st.get("light.pwm_ok") === false) { ss.textContent = "PWM board not answering: headlights, tails, floods, beacon and trailer can't be changed."; ss.className = "small warn"; }
  }
}
