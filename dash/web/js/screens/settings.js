// Settings: display, lights setup, camera, control box limits, diff calibration, faults, updates (OTA), Wi-Fi, about.
import { el, $, stepper, toggle, toast } from "../ui/controls.js";
import { LIGHTS } from "../settings.js";
import { listCameras } from "./camera.js";
import { PICO_FAULTS, MC_FAULTS, faultText, asList } from "../text.js";

async function api(path, opts = {}) {
  const r = await fetch(`/api/${path}`, { cache: "no-store", headers: { "content-type": "application/json" }, ...opts, body: opts.body ? JSON.stringify(opts.body) : undefined });
  if (!r.ok) { let m = `${r.status}`; try { m = (await r.json()).error || m; } catch {} throw new Error(m); }
  return r.json();
}

const SECTIONS = [
  ["display", "Display"], ["lights", "Lights setup"], ["camera", "Camera"], ["limits", "Safety limits"],
  ["diff", "Diff calibration"], ["faults", "Faults"], ["updates", "Updates"], ["wifi", "Wi-Fi"], ["about", "About"],
];

function row(label, desc, control) {
  const r = el(`<div class="set-row"><div><div class="lbl">${label}</div>${desc ? `<div class="desc">${desc}</div>` : ""}</div><div class="ctl"></div></div>`);
  if (control) r.querySelector(".ctl").appendChild(control.root || control);
  return r;
}

function seg(options, value, onChange) {
  const s = el(`<div class="seg" style="min-width:${options.length * 120}px"></div>`);
  options.forEach(([v, label]) => {
    const b = el(`<button>${label}</button>`);
    b.classList.toggle("on", v === value);
    b.onclick = () => { s.querySelectorAll("button").forEach((x) => x.classList.remove("on")); b.classList.add("on"); onChange(v); };
    s.appendChild(b);
  });
  return s;
}

export class SettingsScreen {
  constructor(ctx) { this.ctx = ctx; this.id = "settings"; this.label = "Settings"; this.icon = "settings"; this.section = "display"; this.faultLog = []; }

  mount(root) {
    root.innerHTML = `<div class="settings"><div class="set-nav" id="s-nav"></div><div class="panel set-body" id="s-body"></div></div>`;
    this.root = root;
    const nav = $(root, "#s-nav");
    SECTIONS.forEach(([k, label]) => {
      const b = el(`<button data-k="${k}">${label}</button>`);
      b.onclick = () => this.open(k);
      nav.appendChild(b);
    });
    this.ctx.store.on("faults-changed", (list) => this.logFaults(list));
    this.open(this.section);
  }

  show() { this.open(this.section); }
  hide() { clearInterval(this._poll); }

  open(k) {
    this.section = k;
    clearInterval(this._poll);
    this.root.querySelectorAll("#s-nav button").forEach((b) => b.classList.toggle("on", b.dataset.k === k));
    const body = $(this.root, "#s-body");
    body.innerHTML = ""; body.scrollTop = 0;
    this[`sec_${k}`](body);
  }

  title(body, t, desc) { body.appendChild(el(`<div><h3>${t}</h3>${desc ? `<div class="muted small" style="margin-bottom:6px">${desc}</div>` : ""}</div>`)); }

  // ---------- Display ----------
  sec_display(body) {
    const s = this.ctx.settings;
    this.title(body, "Display");
    body.appendChild(row("Theme", "Day is brighter and easier to read in full sun. Auto switches at 7am and 7pm.", seg([["night", "Night"], ["day", "Day"], ["auto", "Auto"]], s.get("theme"), (v) => { s.set("theme", v); this.ctx.applyTheme(); })));
    body.appendChild(row("Speed units", "", seg([["kmh", "km/h"], ["mph", "mph"]], s.get("units"), (v) => s.set("units", v))));
    body.appendChild(row("Power bar scale", "Full scale of the power bar on the drive screen.", stepper(s.get("powerMaxKw"), { step: 1, min: 5, max: 30, fmt: (v) => `${v} kW`, onChange: (v) => s.set("powerMaxKw", v) })));
    body.appendChild(row("Battery cells in series", "Only used to estimate battery % from voltage if the motor controller doesn't send one.", stepper(s.get("cells"), { step: 1, min: 10, max: 40, onChange: (v) => s.set("cells", v) })));
  }

  // ---------- Lights ----------
  sec_lights(body) {
    const s = this.ctx.settings;
    this.title(body, "Lights setup", "Set each bar as dimmable or on/off only. If a bar flickers or buzzes when dimmed, set it to on/off. The control box is told too, so it never dims a bar that can't take it.");
    LIGHTS.forEach((l) => {
      const cfg = s.light(l.id);
      const names = ["Bar 1", "Bar 2", "Bar 3", "Bar 4", "Interior", "Left spot", "Right spot", "Centre", "Wide", "Flood", "Cab"];
      const nameSel = el(`<select class="big">${[...new Set([cfg.name, ...names])].map((n) => `<option ${n === cfg.name ? "selected" : ""}>${n}</option>`).join("")}</select>`);
      nameSel.onchange = () => s.set(`lights.${l.id}.name`, nameSel.value);
      const r = row(`${l.where}`, "", null);
      const ctl = r.querySelector(".ctl");
      ctl.style.display = "flex"; ctl.style.gap = "16px"; ctl.style.alignItems = "center";
      ctl.appendChild(nameSel);
      ctl.appendChild(seg([[true, "Dimmable"], [false, "On / off"]], cfg.dimmable, (v) => { s.set(`lights.${l.id}.dimmable`, v); this.pushDimMask(); }));
      body.appendChild(r);
    });
  }

  pushDimMask() {
    let mask = 0;
    LIGHTS.forEach((l, i) => { if (this.ctx.settings.light(l.id).dimmable) mask |= 1 << i; });
    this.ctx.setPicoSetting("light_dimmable_mask", mask);
  }

  // ---------- Camera ----------
  async sec_camera(body) {
    const s = this.ctx.settings;
    this.title(body, "Reverse camera", "Works with a USB camera, or an RCA/AHD camera through a USB capture dongle. Both show up below as a camera.");
    body.appendChild(row("Source", "Auto tries the camera directly, then the server stream.", seg([["auto", "Auto"], ["usb", "Camera"], ["stream", "Server stream"]], s.get("camera.source"), (v) => s.set("camera.source", v))));
    const sel = el(`<select class="big"><option value="">First camera found</option></select>`);
    sel.onchange = () => s.set("camera.deviceId", sel.value);
    body.appendChild(row("Which camera", "", sel));
    body.appendChild(row("Pop up in reverse", "Shows the camera when you select reverse, and goes back after.", toggle(s.get("camera.autoOnReverse"), (v) => s.set("camera.autoOnReverse", v))));
    body.appendChild(row("Mirror image", "Most reverse cameras want this on, so left on screen is left behind you.", toggle(s.get("camera.mirror"), (v) => s.set("camera.mirror", v))));
    body.appendChild(row("Guide lines", "", toggle(s.get("camera.guides"), (v) => s.set("camera.guides", v))));
    body.appendChild(row("Guide line offset", "Nudge if the camera isn't mounted in the middle.", stepper(s.get("camera.guideOffset"), { step: 10, min: -200, max: 200, fmt: (v) => `${v > 0 ? "+" : ""}${v}`, onChange: (v) => s.set("camera.guideOffset", v) })));
    const cams = await listCameras();
    cams.forEach((c, i) => sel.appendChild(el(`<option value="${c.deviceId}" ${c.deviceId === s.get("camera.deviceId") ? "selected" : ""}>${c.label || `Camera ${i + 1}`}</option>`)));
  }

  // ---------- Safety limits (control box) ----------
  async sec_limits(body) {
    this.title(body, "Safety limits", "These live on the control box, which enforces them even if the dash is down. Changes are sent to it straight away.");
    const list = el(`<div class="muted">Loading from the control box…</div>`);
    body.appendChild(list);
    let data;
    try { data = await api("pico-settings"); } catch (e) {
      list.textContent = this.ctx.store.get("link.demo") ? "Not available in demo mode." : `Couldn't read the control box settings (${e.message}).`;
      return;
    }
    list.remove();
    data.settings.filter((x) => x.editable !== false).forEach((x) => {
      const st = stepper(x.value, {
        step: x.step || 1, min: x.min ?? 0, max: x.max ?? 65535, fmt: (v) => `${x.scale ? (v * x.scale).toFixed(1) : v} ${x.units || ""}`,
        onChange: (v) => this.ctx.setPicoSetting(x.name, v),
      });
      body.appendChild(row(x.label || x.name, x.help || "", st));
    });
    const btns = el(`<div class="row" style="margin-top:16px"><button class="btn sm" id="l-save">Save to control box</button><button class="btn sm danger" id="l-reset">Reset to defaults</button></div>`);
    btns.querySelector("#l-save").onclick = async () => { try { await api("pico-settings/save", { method: "POST" }); toast("Saved on the control box.", "good"); } catch (e) { toast(`Save failed: ${e.message}`, "bad"); } };
    btns.querySelector("#l-reset").onclick = async () => { try { await api("pico-settings/reset", { method: "POST" }); toast("Control box limits reset to defaults.", "good"); this.open("limits"); } catch (e) { toast(`Reset failed: ${e.message}`, "bad"); } };
    body.appendChild(btns);
  }

  // ---------- Diff calibration ----------
  sec_diff(body) {
    this.title(body, "Front diff lock calibration", "Tells the control box where fully open and fully locked are on the actuator's position sensor. Do this with the Teryx stopped.");
    const live = el(`<div class="kv"><span class="k">Position now</span><span class="v num" id="c-live">--</span></div>`);
    body.appendChild(live);
    const mk = (label, desc, which) => {
      const b = el(`<button class="btn sm">${label}</button>`);
      b.onclick = async () => {
        try { const r = await api("diff-calibrate", { method: "POST", body: { which } }); toast(`Saved ${which === "min" ? "open" : "locked"} point (raw ${r.raw}).`, "good"); }
        catch (e) { toast(`Couldn't calibrate: ${e.message}`, "bad"); }
      };
      return row(label, desc, b);
    };
    body.appendChild(mk("Set open here", "Run the diff lock fully open, then press this.", "min"));
    body.appendChild(mk("Set locked here", "Run the diff lock fully locked, then press this.", "max"));
    this._poll = setInterval(() => {
      const st = this.ctx.store, raw = st.get("an.diff_pos_raw");
      const e = $(body, "#c-live"); if (!e) return;
      e.textContent = `${Math.round(st.get("an.diff_pos", 0))}%${raw != null ? `  (raw ${raw})` : ""}`;
    }, 200);
  }

  // ---------- Faults ----------
  logFaults(list) {
    const now = new Date();
    list.forEach((f) => this.faultLog.unshift({ at: now, ...f }));
    this.faultLog = this.faultLog.slice(0, 50);
    if (this.section === "faults" && this.ctx.current === this) this.open("faults");
  }

  sec_faults(body) {
    const st = this.ctx.store;
    const active = [
      ...asList(st.get("pico.faults")).map((c) => ({ src: "Control box", code: c, text: faultText(c, PICO_FAULTS), sev: (PICO_FAULTS[c] || {}).sev || "bad" })),
      ...asList(st.get("mc.faults")).map((c) => ({ src: "Motor controller", code: c, text: faultText(c, MC_FAULTS), sev: (MC_FAULTS[c] || {}).sev || "bad" })),
    ];
    this.title(body, "Active faults");
    if (!active.length) body.appendChild(el(`<div class="ok" style="font-weight:800;padding:12px 0">No active faults</div>`));
    active.forEach((f) => body.appendChild(el(`<div class="fault-row"><span class="pill ${f.sev}">${f.src.toUpperCase()}</span><span class="grow">${f.text}</span><span class="code">${f.code}</span></div>`)));
    this.title(body, "Recent (since the dash started)");
    if (!this.faultLog.length) body.appendChild(el(`<div class="muted" style="padding:12px 0">Nothing logged yet</div>`));
    this.faultLog.forEach((f) => body.appendChild(el(`<div class="fault-row"><span class="code">${f.at.toLocaleTimeString("en-NZ", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span><span class="grow">${f.text}</span><span class="code">${f.code}</span></div>`)));
  }

  // ---------- Updates (OTA) ----------
  async sec_updates(body) {
    this.title(body, "Software updates", "Updates come down over Wi-Fi. They only install when the Teryx is stopped. If an update fails, the dash rolls back to the last version that worked.");
    const box = el(`<div></div>`);
    body.appendChild(box);
    const render = (u) => {
      const busy = u.state === "checking" || u.state === "downloading" || u.state === "installing" || u.state === "flashing";
      box.innerHTML = "";
      box.appendChild(row("Dash software", `This version: <b>${u.dash?.current || "?"}</b>${u.dash?.available ? `<br>New version: <b>${u.dash.available}</b>${u.dash.notes ? `. ${u.dash.notes}` : ""}` : ""}`, null));
      box.appendChild(row("Control box firmware", `This version: <b>${u.pico?.current || "?"}</b>${u.pico?.available ? `<br>New version: <b>${u.pico.available}</b>` : ""}`, null));
      box.appendChild(row("Channel", "Stable is tested. Beta gets new things first.", seg([["stable", "Stable"], ["beta", "Beta"]], this.ctx.settings.get("updates.channel"), (v) => this.ctx.settings.set("updates.channel", v))));
      if (busy || u.progress != null) {
        const p = el(`<div style="padding:14px 0"><div class="lbl" style="font-weight:800;margin-bottom:8px">${u.message || u.state}</div><div class="progress"><div style="width:${u.progress ?? 0}%"></div></div></div>`);
        box.appendChild(p);
      } else if (u.message) box.appendChild(el(`<div class="${u.state === "error" ? "bad" : "muted"}" style="padding:12px 0;font-weight:700">${u.message}</div>`));
      const btns = el(`<div class="row" style="margin-top:12px;flex-wrap:wrap"></div>`);
      const b = (label, fn, cls = "") => { const x = el(`<button class="btn sm ${cls}" ${busy ? "disabled" : ""}>${label}</button>`); x.onclick = fn; btns.appendChild(x); };
      b("Check for updates", () => this.ota("check", render));
      if (u.dash?.available) b(`Install dash ${u.dash.available}`, () => this.ota("install", render, { target: "dash" }), "on");
      if (u.pico?.available) b(`Update control box to ${u.pico.available}`, () => this.ota("install", render, { target: "pico" }), "on");
      if (u.dash?.previous) b(`Roll back to ${u.dash.previous}`, () => this.ota("rollback", render));
      box.appendChild(btns);
    };
    try { render(await api("ota/status")); } catch (e) {
      box.innerHTML = `<div class="muted" style="padding:12px 0">${this.ctx.store.get("link.demo") ? "Not available in demo mode." : `Can't reach the update service (${e.message}).`}</div>`;
      return;
    }
    this._poll = setInterval(async () => { try { render(await api("ota/status")); } catch {} }, 1000);
  }

  async ota(action, render, body) {
    const st = this.ctx.store;
    if (action !== "check" && (st.get("mc.speed", 0) > 0.5)) { toast("Stop the Teryx before installing updates.", "bad"); return; }
    try { render(await api(`ota/${action}`, { method: "POST", body: body || {} })); }
    catch (e) { toast(`Update: ${e.message}`, "bad"); }
  }

  // ---------- Wi-Fi ----------
  async sec_wifi(body) {
    this.title(body, "Wi-Fi", "Used for updates. Add new networks from a laptop or phone (see the dash README); here you can see the link and switch between saved networks.");
    const box = el(`<div class="muted">Checking…</div>`);
    body.appendChild(box);
    const render = (w) => {
      box.className = ""; box.innerHTML = "";
      box.appendChild(row("Connected to", w.connected ? `${w.ssid} · signal ${w.signal}% · ${w.ip || ""}` : "Not connected", null));
      (w.saved || []).forEach((n) => {
        const b = el(`<button class="btn sm ${n === w.ssid ? "on" : ""}">${n === w.ssid ? "Connected" : "Connect"}</button>`);
        b.onclick = async () => { try { await api("wifi/connect", { method: "POST", body: { ssid: n } }); toast(`Connecting to ${n}…`); setTimeout(() => this.open("wifi"), 4000); } catch (e) { toast(`Couldn't connect: ${e.message}`, "bad"); } };
        box.appendChild(row(n, "Saved network", b));
      });
    };
    try { render(await api("wifi")); } catch (e) { box.textContent = this.ctx.store.get("link.demo") ? "Not available in demo mode." : `Can't read Wi-Fi status (${e.message}).`; }
  }

  // ---------- About ----------
  async sec_about(body) {
    const st = this.ctx.store;
    this.title(body, "About");
    const info = el(`<div></div>`);
    body.appendChild(info);
    let sys = {};
    try { sys = await api("system"); } catch {}
    const kv = (k, v) => info.appendChild(el(`<div class="kv"><span class="k">${k}</span><span class="v">${v}</span></div>`));
    kv("Dash version", sys.version || "dev");
    kv("Control box", st.get("pico.online") ? `online (${st.get("pico.state", "run")})` : "offline");
    kv("Motor controller", st.get("mc.online") === false ? "no data" : "online");
    kv("Mode", st.get("link.demo") ? "Demo (no server)" : "Live");
    if (sys.uptime) kv("Up for", sys.uptime);
    if (sys.temp != null) kv("Pi temperature", `${sys.temp}°C`);
    const btns = el(`<div class="row" style="margin-top:16px"><button class="btn sm" id="a-restart">Restart dash</button><button class="btn sm danger" id="a-off">Shut down Pi</button></div>`);
    btns.querySelector("#a-restart").onclick = () => api("system/restart", { method: "POST" }).catch(() => location.reload());
    btns.querySelector("#a-off").onclick = () => {
      if (st.get("mc.speed", 0) > 0.5) return toast("Stop first.", "bad");
      api("system/shutdown", { method: "POST" }).then(() => toast("Shutting down…")).catch((e) => toast(e.message, "bad"));
    };
    body.appendChild(btns);
  }

  update() {}
}
