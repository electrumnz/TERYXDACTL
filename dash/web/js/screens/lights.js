// Lights: 4 front bars, interior bar, rear pods, trailer. Each bar is set up as dimmable or on/off in Settings.
import { el, $, Slider } from "../ui/controls.js";
import { LIGHTS } from "../settings.js";
import { vehicleDiagram } from "../ui/vehicle.js";

// Effect names match the control box (LIGHT_EFFECT in teryx/canbus/messages.py). "none" is steady.
const EFFECTS = [["none", "Steady"], ["breathe", "Breathe"], ["strobe", "Strobe"], ["chase", "Chase"], ["outside_only", "Outside pair"], ["inside_only", "Inside pair"]];
// "sos" is also supported by the control box but kept off the main grid so it isn't hit by accident.

export class LightsScreen {
  constructor(ctx) {
    this.ctx = ctx; this.id = "lights"; this.label = "Lights"; this.icon = "lights";
    this.want = Object.fromEntries(LIGHTS.map((l) => [l.id, 0]));
    this.lastLevel = Object.fromEntries(LIGHTS.map((l) => [l.id, 255]));
    this.effect = "none"; this.rear = "auto";
  }

  mount(root) {
    root.innerHTML = `
      <div class="lights">
        <div class="col">
          <div class="light-grid" id="l-front"></div>
          <div class="light-grid" id="l-other"></div>
        </div>
        <div class="col">
          <div class="panel">
            <h3>Front bars</h3>
            <div class="fx-grid" id="l-groups"></div>
          </div>
          <div class="panel">
            <h3>Effect</h3>
            <div class="fx-grid" id="l-fx"></div>
          </div>
          <div class="panel grow">
            <h3>Trailer</h3>
            <div class="kv"><span class="k">Tail</span><span class="v" id="l-tt">--</span></div>
            <div class="kv"><span class="k">Brake</span><span class="v" id="l-tb">--</span></div>
            <div class="muted small" style="margin-top:6px">Tail lights come on with any front bar. Brake follows the brake pedal.</div>
          </div>
        </div>
      </div>`;
    this.root = root;
    this.tiles = {};
    const front = $(root, "#l-front"), other = $(root, "#l-other");
    LIGHTS.forEach((l, i) => (i < 4 ? front : other).appendChild(this.makeTile(l)));
    other.appendChild(this.makeRearTile());
    other.lastElementChild.style.gridColumn = "span 2";

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
    this.ctx.settings.subscribe((path) => { if (path.startsWith("lights.")) this.rebuild(); });
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
    </div>`);
    t.querySelectorAll("#l-rear button").forEach((b) => (b.onclick = () => { this.rear = b.dataset.v; this.ctx.link.request("light.rear", this.rear); this.paintRear(); }));
    this.rearTile = t;
    this.paintRear();
    return t;
  }

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
    $(this.root, "#l-tt").textContent = st.get("trailer.tail") ? "On" : "Off";
    $(this.root, "#l-tb").textContent = st.get("trailer.brake") ? "On" : "Off";
  }
}
