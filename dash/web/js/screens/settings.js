// Settings: display, lights setup, camera, control box limits, diff calibration, faults, updates (OTA), Wi-Fi, about.
import { el, $, stepper, toggle, toast } from "../ui/controls.js";
import { LIGHTS } from "../settings.js";
import { listCameras, CAMS } from "./camera.js";
import { keyboard } from "../ui/keyboard.js";
import { REGIONS } from "../theme.js";
import { LOOKS } from "../look.js";
import { FEATURES, featureOn } from "../features.js";
import { Sound } from "../sound.js";
import { lockCommand, askPin, showRecoveryCode, newRecoveryCode, lockResultText } from "../lock.js";

async function api(path, opts = {}) {
  const r = await fetch(`/api/${path}`, { cache: "no-store", headers: { "content-type": "application/json" }, ...opts, body: opts.body ? JSON.stringify(opts.body) : undefined });
  if (!r.ok) { let m = `${r.status}`; try { m = (await r.json()).error || m; } catch {} throw new Error(m); }
  return r.json();
}

const SECTIONS = [
  ["display", "Display"], ["lock", "Vehicle lock"], ["remote", "Remote control"], ["sounds", "Sounds and alerts"], ["audio", "Audio and media"], ["lights", "Lights setup"], ["camera", "Cameras"], ["limits", "Safety limits"],
  ["diff", "Diff calibration"], ["features", "Features"], ["faults", "Faults"], ["updates", "Updates"], ["wifi", "Wi-Fi"], ["about", "About"],
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
    const now = el(`<span class="muted"></span>`);
    const showNow = () => {
      const i = this.ctx.lookInfo();
      now.textContent = `Now: ${LOOKS[i.look]}${i.dark ? ", night colours" : ""} (${i.why})`;
    };
    const lookRow = row("Look", "Auto picks it for you: Fossil when 4WD or the diff lock is on, Night Hunt when the light bars are on or after sunset, Predator the rest of the time. Off-road wins at night, with darker colours. Or lock one here.",
      seg([["auto", "Auto"], ["std", "Predator"], ["offroad", "Fossil"], ["night", "Night Hunt"]], s.get("look") || "auto", (v) => { s.set("look", v); this.ctx.looks.refresh(); this.ctx.applyTheme(); showNow(); }));
    lookRow.querySelector(".desc").appendChild(el(`<div style="margin-top:6px"></div>`)).appendChild(now);
    body.appendChild(lookRow);
    const reg = el(`<select class="big">${Object.entries(REGIONS).map(([k, r]) => `<option value="${k}" ${k === s.get("themeRegion") ? "selected" : ""}>${r.name}</option>`).join("")}</select>`);
    reg.onchange = () => { s.set("themeRegion", reg.value); this.ctx.looks.refresh(); this.ctx.applyTheme(); showNow(); };
    body.appendChild(row("Area for sunset", "For when it gets dark in Auto. Only used when there's no GPS fix. Just a rough area, no exact spot is saved.", reg));
    showNow();
    body.appendChild(row("Battery on the drive screen", "Which one shows big. The other shows small underneath. You can also tap the battery to swap.", seg([["pct", "Percent"], ["km", "Range (km)"]], s.get("batteryShow") || "pct", (v) => s.set("batteryShow", v))));
    body.appendChild(row("Speed units", "", seg([["kmh", "km/h"], ["mph", "mph"]], s.get("units"), (v) => s.set("units", v))));
    body.appendChild(row("Power bar scale", "Full scale of the power bar on the drive screen.", stepper(s.get("powerMaxKw"), { step: 1, min: 5, max: 30, fmt: (v) => `${v} kW`, onChange: (v) => s.set("powerMaxKw", v) })));
    body.appendChild(row("Battery pack size", "Usable energy in the traction pack, for the range estimate. 72 V x 105 Ah is about 7.5 kWh.", stepper(s.get("packKwh"), { step: 0.5, min: 1, max: 40, fmt: (v) => `${v.toFixed(1)} kWh`, onChange: (v) => s.set("packKwh", v) })));
    body.appendChild(row("Battery cells in series", "Only used to estimate battery % from voltage if the motor controller doesn't send one.", stepper(s.get("cells"), { step: 1, min: 10, max: 40, onChange: (v) => s.set("cells", v) })));
  }

  // ---------- Remote control (docs/rc-beach-launch.md) ----------
  // 4G driving is off unless turned on here, and changing it either way needs the lock PIN.
  sec_remote(body) {
    const ctx = this.ctx, s = ctx.settings, st = ctx.store;
    this.title(body, "Remote control", "Drive the Teryx from your phone or a handheld, for launching off the beach. 3 km/h in reverse, 5 km/h forward. It stops on the brake if the signal drops, you let go of the green button or the wheels dig in. On the Teryx's own Wi-Fi, open <b>remote.html</b> on the dash's address.");
    const sw = toggle(!!s.get("rc.allow4g"), async (v) => {
      sw.set(!v);   // only changes once the PIN checks out
      if (st.get("lock.state") === "off" || st.get("lock.state") == null) { toast("Set a vehicle lock PIN first (Vehicle lock).", "bad"); return; }
      const p = await askPin("Enter your PIN", v ? "To allow driving over 4G." : "To turn 4G driving off.");
      if (p == null) return;
      const r = await lockCommand(ctx, "verify", p);
      if (r !== "ok") { toast(r === "no_link" || r === "no_answer" ? "No answer from the control box." : lockResultText(r) || `Control box said no (${r}).`, "bad"); return; }
      s.set("rc.allow4g", v); sw.set(v);
      toast(v ? "4G driving allowed. 2 km/h, cameras must be live, stops if the lag gets over 0.3 s." : "4G driving off.", v ? "warn" : "good");
    });
    body.appendChild(row("Allow driving over 4G", "Off unless you turn it on. Meant for getting it back if it's ever pinched, not for everyday use. Over 4G it's capped at 2 km/h, won't move unless the cameras are live, and stops on the brake if the lag gets over 0.3 s or the link drops. Police say don't go after a stolen vehicle yourself: call 111. Needs your PIN to change.", sw));
    body.appendChild(row("Remote speed limits", "Reverse 3 km/h, forward 5 km/h on Wi-Fi or the handheld's own radio. 2 km/h over 4G. Set in the RC box.", null));
  }

  // ---------- Vehicle lock (docs/vehicle-lock.md) ----------
  // The control box keeps the lock, the PIN hash and the wrong-try count. This only asks.
  sec_lock(body) {
    const ctx = this.ctx, st = ctx.store;
    this.title(body, "Vehicle lock", "Locks the Teryx down when you leave it, like at the beach. Once locked there's no drive, no 4WD or diff changes, no tray, no winch and the lights go off until the PIN goes in. The control box holds the lock, so turning the screen off or pulling its plug doesn't unlock it.");
    const box = el(`<div class="lk-set"></div>`);
    body.appendChild(box);
    const say = (r, okText) => {
      if (r === "ok" || r === "recovered") { if (okText) toast(okText, "good"); return true; }
      toast(r === "no_link" || r === "no_answer" ? "No answer from the control box." : lockResultText(r) || `Control box said no (${r}).`, "bad");
      return false;
    };
    // New PIN twice, then a fresh recovery code. Needs the change window (or no PIN yet).
    const newPin = async () => {
      const a = await askPin("New PIN", "4 to 6 digits.");
      if (a == null) return false;
      const b = await askPin("Same PIN again", "To make sure.");
      if (b == null) return false;
      if (a !== b) { toast("Those didn't match. Nothing changed.", "bad"); return false; }
      if (!say(await lockCommand(ctx, "set_pin", a))) return false;
      const code = newRecoveryCode();
      if (!say(await lockCommand(ctx, "set_puk", code))) return false;
      await showRecoveryCode(code);
      toast("PIN set.", "good");
      return true;
    };
    const verify = async (why) => {
      const p = await askPin("Current PIN", why);
      if (p == null) return false;
      return say(await lockCommand(ctx, "verify", p));
    };
    const draw = () => {
      const state = st.get("lock.state");
      box.innerHTML = "";
      if (state === undefined) {
        box.appendChild(el(`<div class="muted">Waiting for the control box…</div>`));
        return;
      }
      if (state === "off") {
        const b = el(`<button class="btn">Set a PIN</button>`);
        b.onclick = async () => { if (await newPin()) draw(); };
        box.appendChild(row("Lock is off", "Set a 4 to 6 digit PIN to use the lock. You'll also get a one-off recovery code to write down.", b));
        return;
      }
      // Lock now: the big padlock button, with what's needed first.
      const speedOk = st.get("pico.speed_valid") !== false && (st.get("mc.speed", 0) < 0.5);
      const parkOk = !!st.get("in.park");
      const ready = speedOk && parkOk;
      const lockBtn = el(`<button class="lk-now ${ready ? "" : "not-ready"}"><img src="img/dino/padlock.webp" alt=""><span>LOCK NOW</span></button>`);
      lockBtn.onclick = async () => {
        if (!ready) { toast("Stop and put the park brake on first.", "bad"); return; }
        say(await lockCommand(ctx, "lock"));
      };
      const checks = el(`<div class="lk-checks">
        <div class="${speedOk ? "ok" : ""}">${speedOk ? "✓" : "✗"} Stopped</div>
        <div class="${parkOk ? "ok" : ""}">${parkOk ? "✓" : "✗"} Park brake on</div></div>`);
      const lockRow = el(`<div class="lk-now-row"></div>`);
      lockRow.appendChild(lockBtn); lockRow.appendChild(checks);
      box.appendChild(lockRow);
      const puk = st.get("lock.puk_set");
      const ch = el(`<button class="btn sm">Change PIN</button>`);
      ch.onclick = async () => { if (await verify("To change it.")) await newPin(); };
      box.appendChild(row("PIN", "Change it any time. You need the current one.", ch));
      const rc = el(`<button class="btn sm">New code</button>`);
      rc.onclick = async () => {
        if (!(await verify("To make a new recovery code."))) return;
        const code = newRecoveryCode();
        if (say(await lockCommand(ctx, "set_puk", code))) await showRecoveryCode(code);
        draw();
      };
      box.appendChild(row("Recovery code", puk ? "Set. A new one replaces the old one." : "Not set. Make one so a forgotten PIN isn't a workshop job.", rc));
      const rm = el(`<button class="btn sm danger">Turn off</button>`);
      rm.onclick = async () => {
        if (!(await verify("To turn the lock off."))) return;
        if (say(await lockCommand(ctx, "remove"), "Lock turned off. PIN and recovery code wiped.")) draw();
      };
      box.appendChild(row("Turn the lock off", "Wipes the PIN and the recovery code.", rm));
      const fails = st.get("lock.fails", 0);
      if (fails) box.appendChild(el(`<div class="muted small">${fails} wrong ${fails === 1 ? "try" : "tries"} since the last right one.</div>`));
      box.appendChild(el(`<div class="muted small" style="margin-top:8px">Forgot the PIN and lost the code? There's a workshop reset inside the control box. See docs/vehicle-lock.md.</div>`));
    };
    draw();
    // Redraw when the lock state or the "ready to lock" checks change.
    let last = "";
    clearInterval(this._poll);
    this._poll = setInterval(() => {
      const k = [st.get("lock.state"), st.get("lock.puk_set"), st.get("in.park"), st.get("mc.speed", 0) < 0.5, st.get("lock.fails")].join();
      if (k !== last && !document.querySelector(".lk-modal")) { if (last) draw(); last = k; }
    }, 300);
  }

  // ---------- Sounds and alerts ----------
  sec_sounds(body) {
    const s = this.ctx.settings;
    this.title(body, "Sounds and alerts", "Warnings beep twice. Serious ones beep three times and keep beeping every few seconds until you tap OK on the banner.");
    const apply = () => this.ctx.applySound();
    body.appendChild(row("Alert sounds", "", toggle(s.get("sound.enabled"), (v) => { s.set("sound.enabled", v); apply(); })));
    body.appendChild(row("Volume", "", stepper(Math.round(s.get("sound.volume") * 10), { step: 1, min: 1, max: 10, fmt: (v) => `${v * 10}%`, onChange: (v) => { s.set("sound.volume", v / 10); apply(); Sound.play("warn"); } })));
    body.appendChild(row("Tap clicks", "A small tick on every press, so you know a gloved tap landed.", toggle(s.get("sound.clicks"), (v) => { s.set("sound.clicks", v); apply(); })));
    const test = el(`<div class="row" style="gap:10px;flex-wrap:wrap"></div>`);
    [["warn", "Warning"], ["bad", "Serious"], ["info", "Info"]].forEach(([k, l]) => { const b = el(`<button class="btn sm">${l}</button>`); b.onclick = () => Sound.play(k); test.appendChild(b); });
    body.appendChild(row("Try the sounds", "", test));
    this.title(body, "Tilt alerts", "Only used once a tilt sensor is fitted. Side to side is the one that rolls you, so it warns earlier.");
    const deg = (path, label, desc) => body.appendChild(row(label, desc, stepper(s.get(path), { step: 1, min: 10, max: 45, fmt: (v) => `${v}°`, onChange: (v) => s.set(path, v) })));
    deg("tilt.rollWarn", "Side slope warning", "");
    deg("tilt.rollBad", "Side slope alarm", "Rollover risk.");
    deg("tilt.pitchWarn", "Up/down warning", "");
    deg("tilt.pitchBad", "Up/down alarm", "");
  }

  // ---------- Features: what's wired up yet ----------
  sec_features(body) {
    const s = this.ctx.settings;
    this.title(body, "Features", "Anything not wired up on the Teryx yet shows greyed out with a SOON tag. Switch it on here once it's fitted.");
    FEATURES.forEach((f) => body.appendChild(row(f.name, f.desc, toggle(featureOn(s, f.id), (v) => s.set(`features.${f.id}`, v)))));
  }

  // ---------- Audio and media ----------
  sec_audio(body) {
    const s = this.ctx.settings, hub = this.ctx.media;
    this.title(body, "Audio and media", "Where the sound goes and how music behaves. Alert sounds are set under Sounds and alerts, and are never turned down by the music.");
    const outBox = el(`<div class="col" style="gap:10px"><div class="muted">Checking…</div></div>`);
    body.appendChild(row("Sound goes to", "The Pi 5 has no headphone jack. Use a USB DAC or an I2S amp HAT into the amp. HDMI only helps if the HDMI to VGA adapter has a 3.5 mm audio out.", outBox));
    const lvl = stepper(100, { step: 10, min: 10, max: 100, fmt: (v) => `${v}%`, onChange: (v) => api("audio/output-level", { method: "POST", body: { level: v / 100 } }).catch((e) => toast(`Couldn't set the level (${e.message}).`, "bad")) });
    body.appendChild(row("Output level", "The feed to the amp. Leave it at 100% and set the amp's gain once, so alerts are always loud enough.", lvl));
    const fill = async () => {
      if (this.ctx.store.get("link.demo")) { outBox.innerHTML = `<div class="muted">Not available in demo mode.</div>`; return; }
      try {
        const a = await api("audio");
        if (a.output_level != null) lvl.set(Math.round(a.output_level * 10) * 10);
        outBox.innerHTML = "";
        if (!a.outputs.length) outBox.appendChild(el(`<div class="muted">No outputs found. Is PipeWire running? See docs/audio.md.</div>`));
        a.outputs.forEach((o) => {
          const b = el(`<button class="btn sm ${o.default ? "on" : ""}" style="justify-content:flex-start;min-width:320px"></button>`);
          b.textContent = o.label;
          b.onclick = async () => { try { await api("audio/output", { method: "POST", body: { id: o.id } }); fill(); toast("Sound output changed.", "good"); } catch (e) { toast(`Couldn't switch (${e.message}).`, "bad"); } };
          outBox.appendChild(b);
        });
        if (a.backend === "sim") outBox.appendChild(el(`<div class="muted small">Simulator: these outputs are pretend.</div>`));
      } catch (e) { outBox.innerHTML = `<div class="muted">Can't reach the Pi's audio (${e.message}).</div>`; }
    };
    fill();
    body.appendChild(row("Music under alerts", "How far music drops while an alert sounds. It comes back up after.", stepper(Math.round((s.get("media.duckTo") ?? 0.25) * 100), { step: 5, min: 0, max: 60, fmt: (v) => (v === 0 ? "Silent" : `${v}%`), onChange: (v) => { s.set("media.duckTo", v / 100); hub.mixer.setDuckTo(v / 100); hub.mixer.pulse(2500); Sound.play("warn"); } })));
    body.appendChild(row("Quieter in reverse", "Drops the music while reversing, so you can hear what's behind you.", toggle(s.get("media.quietInReverse") !== false, (v) => s.set("media.quietInReverse", v))));
    this.title(body, "CarPlay and Android Auto", "Through a Carlinkit USB adapter plugged into the Pi.");
    body.appendChild(row("Start by itself", "Start the adapter when the dash starts or when it's plugged in.", toggle(s.get("media.carplay.autoStart") !== false, (v) => s.set("media.carplay.autoStart", v))));
    body.appendChild(row("Driver's side", "Puts the CarPlay dock on the driver's side. Takes effect the next time CarPlay starts.", seg([["rhd", "Right (NZ)"], ["lhd", "Left"]], s.get("media.carplay.hand") || "rhd", (v) => s.set("media.carplay.hand", v))));
  }

  // ---------- Lights ----------
  sec_lights(body) {
    const s = this.ctx.settings;
    this.title(body, "Lights setup", "Set each bar as dimmable or on/off only. If a bar flickers or buzzes when dimmed, set it to on/off. The control box is told too, so it never dims a bar that can't take it.");
    LIGHTS.forEach((l) => {
      const cfg = s.light(l.id);
      const names = ["Bar 1", "Bar 2", "Bar 3", "Bar 4", "Interior", "Left spot", "Right spot", "Centre", "Wide", "Flood", "Cab"];
      const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
      const nameSel = el(`<select class="big">${[...new Set([cfg.name, ...names])].map((n) => `<option value="${esc(n)}" ${n === cfg.name ? "selected" : ""}>${esc(n)}</option>`).join("")}<option value="__type">Type a name…</option></select>`);
      nameSel.onchange = async () => {
        if (nameSel.value !== "__type") return s.set(`lights.${l.id}.name`, nameSel.value);
        const t = await keyboard({ title: `Name for ${l.where.toLowerCase()}`, value: s.light(l.id).name, maxLength: 16 });
        if (t && t.trim()) s.set(`lights.${l.id}.name`, t.trim());
        this.open("lights");
      };
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
    this.title(body, "Cameras", "Up to three: rear, front and trailer. Each can be a USB camera, or an RCA/AHD camera through a USB capture dongle. Both show up below as a device. Cameras that aren't fitted show greyed out on the Cameras screen.");
    body.appendChild(row("Source", "Auto tries the camera directly, then the server stream.", seg([["auto", "Auto"], ["usb", "Camera"], ["stream", "Server stream"]], s.get("camera.source"), (v) => s.set("camera.source", v))));
    body.appendChild(row("Pop up in reverse", "Shows a camera when you select reverse, and goes back after.", toggle(s.get("camera.autoOnReverse"), (v) => s.set("camera.autoOnReverse", v))));
    body.appendChild(row("Trailer camera in reverse", "With a trailer plugged in, reverse shows the trailer camera instead of the rear one. You can still swap on the Cameras screen.", toggle(s.get("camera.trailerInReverse") !== false, (v) => s.set("camera.trailerInReverse", v))));
    body.appendChild(row("Guide line offset", "Nudge if the camera isn't mounted in the middle.", stepper(s.get("camera.guideOffset"), { step: 10, min: -200, max: 200, fmt: (v) => `${v > 0 ? "+" : ""}${v}`, onChange: (v) => s.set("camera.guideOffset", v) })));
    const devices = await listCameras();
    const esc = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
    const HELP = {
      rear: "Mirror on, so left on screen is left behind you.",
      front: "Grille or bull bar camera, for seeing over a crest. Usually no mirror and no guide lines.",
      trailer: "On the back of the trailer. Only shows when a trailer is plugged in (reed switch in the 7-pin socket).",
    };
    CAMS.forEach((c) => {
      const k = `camera.cams.${c.id}`, cfg = s.get(k) || {};
      body.appendChild(el(`<div style="margin-top:18px"><h3>${esc(c.name)} camera</h3><div class="muted small" style="margin-bottom:6px">${HELP[c.id]}</div></div>`));
      body.appendChild(row("Fitted", "", toggle(!!cfg.fitted, (v) => { s.set(`${k}.fitted`, v); this.open("camera"); })));
      if (!cfg.fitted) return;
      const sel = el(`<select class="big"><option value="">${c.id === "rear" ? "First camera found" : "Pick one…"}</option></select>`);
      devices.forEach((d, i) => sel.appendChild(el(`<option value="${esc(d.deviceId)}" ${d.deviceId === cfg.deviceId ? "selected" : ""}>${esc(d.label || `Camera ${i + 1}`)}</option>`)));
      sel.onchange = () => s.set(`${k}.deviceId`, sel.value);
      body.appendChild(row("Which device", c.id === "rear" ? "" : "With more than one camera plugged in, pick which one this is.", sel));
      body.appendChild(row("Mirror image", "", toggle(!!cfg.mirror, (v) => s.set(`${k}.mirror`, v))));
      body.appendChild(row("Guide lines", "", toggle(!!cfg.guides, (v) => s.set(`${k}.guides`, v))));
    });
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
    const SRC = { p: "Control box", m: "Motor controller", a: "Dash" };
    const active = this.ctx.alerts.active.map((a) => ({ src: SRC[a.key[0]] || "Dash", code: a.code, text: a.text, sev: a.sev }));
    const head = el(`<div class="row" style="justify-content:space-between;align-items:center"><h3 style="margin:0">Active alerts and faults</h3><button class="btn sm">Clear latched faults</button></div>`);
    head.querySelector("button").onclick = async () => {
      try { await api("pico-settings/clear-faults", { method: "POST" }); toast("Asked the control box to clear faults. Any that are still there will come back.", "good"); }
      catch (e) { toast(`Couldn't clear: ${e.message}`, "bad"); }
      setTimeout(() => this.open("faults"), 1500);
    };
    body.appendChild(head);
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
      box.appendChild(row("Control box firmware", `This version: <b>${u.pico?.current || "?"}</b>${u.pico?.available ? `<br>New version: <b>${u.pico.available}</b>${this.ctx.store.get("pico.parked") === false ? " (park to install)" : ""}` : ""}`, null));
      box.appendChild(row("Channel", "Stable is tested. Beta gets new things first.", seg([["stable", "Stable"], ["beta", "Beta"]], this.ctx.settings.get("updates.channel"), (v) => this.ctx.settings.set("updates.channel", v))));
      if (busy || u.progress != null) {
        const p = el(`<div style="padding:14px 0"><div class="lbl" style="font-weight:800;margin-bottom:8px">${u.message || u.state}</div><div class="progress"><div style="width:${u.progress ?? 0}%"></div></div></div>`);
        box.appendChild(p);
      } else if (u.message) box.appendChild(el(`<div class="${u.state === "error" ? "bad" : "muted"}" style="padding:12px 0;font-weight:700">${u.message}</div>`));
      const btns = el(`<div class="row" style="margin-top:12px;flex-wrap:wrap"></div>`);
      const b = (label, fn, cls = "") => { const x = el(`<button class="btn sm ${cls}" ${busy ? "disabled" : ""}>${label}</button>`); x.onclick = fn; btns.appendChild(x); };
      b("Check for updates", () => this.ota("check", render));
      if (u.dash?.available) b(`Install dash ${u.dash.available}`, () => this.ota("install", render, { target: "dash" }), "on");
      if (u.pico?.available && this.ctx.store.get("pico.parked") !== false) b(`Update control box to ${u.pico.available}`, () => this.ota("install", render, { target: "pico" }), "on");
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
    this.title(body, "Wi-Fi", "Used for updates. Tap a network to join it, and type the password on the on-screen keyboard. Passwords stay on the Pi.");
    const box = el(`<div class="muted">Checking…</div>`);
    body.appendChild(box);
    if (this.ctx.store.get("link.demo")) {
      box.textContent = "Not available in demo mode. You can still try the keyboard:";
      const b = el(`<button class="btn sm" style="margin-top:12px">Try the keyboard</button>`);
      b.onclick = async () => { const t = await keyboard({ title: "Wi-Fi password", password: true, minLength: 8, hint: "8 to 63 characters", doneLabel: "Join" }); if (t != null) toast(`Typed ${t.length} characters.`, "good"); };
      body.appendChild(b);
      return;
    }
    let w;
    try { w = await api("wifi"); } catch (e) { box.textContent = `Can't read Wi-Fi status (${e.message}).`; return; }
    box.className = ""; box.innerHTML = "";
    box.appendChild(row("Connected to", w.connected ? `${w.ssid} · signal ${w.signal}% · ${w.ip || ""}` : "Not connected", null));
    const saved = new Set(w.saved || []);
    this.title(body, "Saved networks");
    (w.saved || []).forEach((n) => {
      const c = el(`<div class="row" style="gap:10px"></div>`);
      const b = el(`<button class="btn sm ${n === w.ssid ? "on" : ""}">${n === w.ssid ? "Connected" : "Connect"}</button>`);
      b.onclick = async () => { try { await api("wifi/connect", { method: "POST", body: { ssid: n } }); toast(`Connecting to ${n}…`); setTimeout(() => this.open("wifi"), 4000); } catch (e) { toast(`Couldn't connect: ${e.message}`, "bad"); } };
      const f = el(`<button class="btn sm danger">Forget</button>`);
      f.onclick = async () => {
        if (f.dataset.armed !== "1") { f.dataset.armed = "1"; f.textContent = "Tap again"; setTimeout(() => { f.dataset.armed = ""; f.textContent = "Forget"; }, 3000); return; }
        try { await api("wifi/forget", { method: "POST", body: { ssid: n } }); toast(`Forgot ${n}.`, "good"); this.open("wifi"); } catch (e) { toast(`Couldn't forget: ${e.message}`, "bad"); }
      };
      c.appendChild(b); c.appendChild(f);
      box.appendChild(row(this.escape(n), "", c));
    });
    if (!saved.size) box.appendChild(el(`<div class="muted" style="padding:8px 0">None yet.</div>`));
    this.title(body, "Networks nearby");
    const near = el(`<div class="muted" style="padding:8px 0">Looking…</div>`);
    body.appendChild(near);
    const other = el(`<button class="btn sm" style="margin-top:12px">Other network (type the name)</button>`);
    other.onclick = async () => {
      const ssid = await keyboard({ title: "Network name", maxLength: 32, hint: "Exactly as it shows on your phone or router", doneLabel: "Next" });
      if (ssid) this.join(ssid, true, true);
    };
    body.appendChild(other);
    try {
      const { networks } = await api("wifi/scan");
      near.className = ""; near.innerHTML = "";
      networks.filter((n) => !saved.has(n.ssid)).slice(0, 12).forEach((n) => {
        const b = el(`<button class="btn sm">Join</button>`);
        b.onclick = () => this.join(n.ssid, n.secure);
        near.appendChild(row(this.escape(n.ssid), `${n.secure ? "Password" : "Open"} · signal ${n.signal}%`, b));
      });
      if (!near.children.length) near.innerHTML = `<div class="muted">No new networks found.</div>`;
    } catch (e) { near.textContent = `Couldn't scan (${e.message}).`; }
  }

  escape(t) { return String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;"); }

  async join(ssid, secure, hidden = false) {
    let password = "";
    if (secure) {
      password = await keyboard({ title: `Password for ${ssid}`, password: true, minLength: 8, maxLength: 63, hint: hidden ? "Leave empty if it's an open network" : "8 to 63 characters", doneLabel: "Join" });
      if (password == null) return;
    }
    toast(`Joining ${ssid}…`);
    try { await api("wifi/add", { method: "POST", body: { ssid, password, hidden } }); toast(`Connected to ${ssid}.`, "good"); }
    catch (e) { toast(`Couldn't join ${ssid}: ${e.message}`, "bad"); }
    if (this.section === "wifi") this.open("wifi");
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
