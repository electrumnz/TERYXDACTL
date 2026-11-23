// The whole-Teryx sim page: the real dash in an iframe, the sim in a web worker, a hands-on panel.
// The dash sends what it would send the Pi's websocket; we pass it to the worker, and pass the
// worker's state back. The panel is your hands and feet: key, pedals, F-N-R, wheel, switches.
(() => {
  const ver = new URL(document.currentScript.src).searchParams.get("v") || "";
  const q = ver ? `?v=${ver}` : "";
  const $ = (id) => document.getElementById(id);
  const dash = $("dash");
  let worker = null, last = null, dashReady = false;

  // ---------------------------------------------------------------- worker
  function start() {
    const wq = new URLSearchParams(ver ? { v: ver } : {});
    const py = new URLSearchParams(location.search).get("pyodide");
    if (py) wq.set("pyodide", new URL(py, location.href).href);
    worker = new Worker("worker.js" + (wq.toString() ? "?" + wq : ""), { type: "module" });
    worker.onmessage = (ev) => {
      const m = ev.data;
      if (m.type === "status") {
        $("loading-text").textContent = m.text;
        $("status").textContent = m.text === "Running" ? "Running" : "Loading";
      } else if (m.type === "error") {
        $("loading").hidden = false;
        $("loading").classList.add("err");
        $("loading-text").textContent = "The simulator stopped: " + m.text.split("\n").slice(-3).join(" ");
        $("status").textContent = "Stopped";
        $("status").className = "pill bad";
      } else if (m.type === "warn") {
        console.warn(m.text);
      } else if (m.type === "out") {
        $("loading").hidden = true;
        last = m;
        toDash({ type: "state", state: m.dash });
        for (const r of m.replies || []) toDash(r);
        show(m);
      }
    };
  }
  const send = (type, body) => worker && worker.postMessage({ type, ...body });
  const panel = (cmd) => send("panel", { cmd });

  // ---------------------------------------------------------------- the dash screen
  dash.src = "../index.html?rig=1" + (ver ? `&v=${ver}` : "");
  function toDash(msg) {
    if (dashReady) dash.contentWindow.postMessage({ teryxRig: "state", msg }, "*");
  }
  window.addEventListener("message", (ev) => {
    if (ev.source !== dash.contentWindow || !ev.data || !ev.data.teryxRig) return;
    if (ev.data.teryxRig === "hello") { dashReady = true; if (last) toDash({ type: "state", state: last.dash }); }
    else if (ev.data.teryxRig === "ui") send("ui", { msg: ev.data.msg });
  });
  // Keep the screen 16:10 (1280 x 800) and as big as fits.
  function fit() {
    const wrap = $("screen");
    const w = wrap.clientWidth;
    dash.style.width = "1280px";
    dash.style.height = "800px";
    dash.style.transform = `scale(${w / 1280})`;
    wrap.style.height = `${(w / 1280) * 800}px`;
  }
  window.addEventListener("resize", fit);
  fit();

  // ---------------------------------------------------------------- panel controls
  for (const b of document.querySelectorAll("button.tog[data-in]")) {
    b.addEventListener("click", () => {
      const k = b.dataset.in;
      const on = !(last && last.panel.inputs[k]);
      panel({ [k]: on });
      b.classList.toggle("on", on);
    });
  }
  for (const b of document.querySelectorAll("button.hold")) {
    const k = b.dataset.hold, v = b.dataset.v || true;
    const down = (e) => { e.preventDefault(); b.classList.add("on"); panel({ [k]: v }); };
    const up = () => { if (!b.classList.contains("on")) return; b.classList.remove("on"); panel({ [k]: k === "brake" ? false : null }); };
    b.addEventListener("pointerdown", down);
    for (const ev of ["pointerup", "pointerleave", "pointercancel"]) b.addEventListener(ev, up);
  }
  // Dash look: Auto or lock one of the three (same as Settings > Display on the dash).
  const lookBtns = [...document.querySelectorAll("#looks button")];
  const markLook = () => {
    const t = dash.contentWindow && dash.contentWindow.teryx;
    const now = (t && t.settings.get("look")) || "auto";
    lookBtns.forEach((b) => b.classList.toggle("on", b.dataset.look === now));
  };
  for (const b of lookBtns) b.addEventListener("click", () => {
    const t = dash.contentWindow && dash.contentWindow.teryx; if (!t) return;
    t.settings.set("look", b.dataset.look); t.looks.refresh(); t.applyTheme(); markLook();
  });
  dash.addEventListener("load", () => setTimeout(markLook, 1500));
  for (const seg of document.querySelectorAll(".seg[data-seg]")) {
    for (const b of seg.querySelectorAll("button")) {
      b.addEventListener("click", () => panel({ [seg.dataset.seg]: b.dataset.v }));
    }
  }
  const thr = $("throttle"), steer = $("steer"), bat = $("battery");
  thr.addEventListener("input", () => panel({ throttle: thr.value / 100 }));
  const thrBack = () => { if (!$("cruise").checked) { thr.value = 0; panel({ throttle: 0 }); } };
  thr.addEventListener("pointerup", thrBack);
  thr.addEventListener("touchend", thrBack);
  steer.addEventListener("input", () => panel({ steer: +steer.value }));
  const steerBack = () => { steer.value = 0; panel({ steer: 0 }); };
  steer.addEventListener("pointerup", steerBack);
  steer.addEventListener("touchend", steerBack);
  bat.addEventListener("input", () => panel({ battery: +bat.value }));
  const sgSel = $("sg-fault"), sgBtn = $("sg-fault-btn");
  sgSel.addEventListener("change", () => { sgBtn.disabled = !sgSel.value; syncFaultBtn(); });
  sgBtn.addEventListener("click", () => {
    const on = !(last && last.panel.shinegle_faults.includes(sgSel.value));
    panel({ shinegle_fault: [sgSel.value, on] });
  });
  $("restart").addEventListener("click", () => { panel({ restart: true }); thr.value = 0; steer.value = 0; bat.value = 12.6; });
  function syncFaultBtn() {
    const on = !!(last && sgSel.value && last.panel.shinegle_faults.includes(sgSel.value));
    sgBtn.classList.toggle("on", on);
    sgBtn.textContent = on ? "Fault on" : "Turn fault on";
  }

  // ---------------------------------------------------------------- showing what's happening
  const pretty = (s) => String(s).replace(/_/g, " ");
  let fusesBuilt = false, faultsBuilt = false;
  function show(m) {
    const p = m.panel, d = m.dash, i = p.inputs;
    const slow = m.speed < 0.9;
    $("status").textContent = slow ? `Running at ${Math.round(m.speed * 100)}% speed` : "Running";
    $("status").className = "pill " + (slow ? "warn" : "ok");
    for (const b of document.querySelectorAll("button.tog[data-in]")) b.classList.toggle("on", !!i[b.dataset.in]);
    for (const seg of document.querySelectorAll(".seg[data-seg]")) {
      for (const b of seg.querySelectorAll("button")) b.classList.toggle("on", i[seg.dataset.seg] === b.dataset.v);
    }
    $("thr-v").textContent = `${Math.round(i.throttle * 100)}%` + (p.shinegle.hpd ? " (lift off: HPD)" : "");
    $("str-v").textContent = Math.abs(i.steer) < 0.25 ? "hands off" : `${i.steer > 0 ? "right" : "left"} ${Math.abs(i.steer)} Nm`;
    $("bat-v").textContent = `${(+i.battery).toFixed(1)} V`;
    $("g-speed").textContent = p.speed_kmh.toFixed(0);
    $("g-wheel").style.transform = `rotate(${p.eps.angle_deg}deg)`;
    $("g-angle").textContent = `${Math.round(p.eps.angle_deg)}°`;
    $("g-assist").textContent = p.eps.mode === "normal" || p.eps.mode === "limp" ? `${p.eps.assist_ratio}x` : p.eps.mode;
    $("g-soc").textContent = Math.round(p.soc);

    const off = !p.screen_on;
    $("screen-off").hidden = !off;
    $("screen-why").textContent = !p.inputs.key ? "Key off. Turn the key on to start the Pi." : "The Pi has no power or has shut down.";

    const kv = [
      ["Control box (Pico)", p.pico_on ? (d["pico.state"] || "on") : "off"],
      ["Pi and dash", p.pi_on ? "on" : "off"],
      ["Shinegle", p.shinegle.ksi ? `on, ${p.shinegle.direction}, throttle ${Math.round(p.shinegle.throttle * 100)}%` : "off (no KSI)"],
      ["Power steering ECU", `${pretty(p.eps.mode)}, told ${p.eps.told_kmh} km/h`],
      ["Steering on the dash", d["steer.state"] ? pretty(d["steer.state"]) : "-"],
      ["Winch", p.winch ? `pulling ${p.winch}` : "stopped"],
      ["Shinegle faults", (p.mc_faults || []).map(pretty).join(", ") || "none"],
      ["Control box faults", (p.pico_faults || []).map(pretty).join(", ") || "none"],
    ];
    $("kv").innerHTML = kv.map(([k, v]) => `<div><span>${k}</span><b>${v}</b></div>`).join("");
    $("lamps").innerHTML = Object.entries(p.lights).flatMap(([dev, parts]) =>
      Object.entries(parts).map(([part, lv]) => {
        const glow = Math.max(0, Math.min(1, lv));
        return `<div class="lamp" style="--lv:${glow}"><i></i><span>${dev.replace("_", " ")}${Object.keys(parts).length > 1 ? " " + part : ""}</span></div>`;
      })).join("");
    $("relays").innerHTML = Object.entries(p.relays).map(([n, on]) => `<span class="${on ? "on" : ""}">${n}</span>`).join("");
    const actName = { ACT_4WD: "4WD", ACT_DIFF: "Diff lock", ACT_TRAY: "Tray" };
    $("acts").innerHTML = Object.entries(p.actuators).map(([k, v]) =>
      `<div class="act"><span>${actName[k] || k}</span><div class="bar"><div style="width:${Math.round(v * 100)}%"></div></div><b>${Math.round(v * 100)}%</b></div>`).join("");
    $("problems").innerHTML = p.problems.length ? p.problems.map((x) => `<li>${x}</li>`).join("") : `<li class="muted">None</li>`;
    $("strip").textContent = `Sim time ${p.t.toFixed(1)} s`;

    if (!faultsBuilt && p.shinegle_fault_names) {
      faultsBuilt = true;
      for (const f of p.shinegle_fault_names) sgSel.insertAdjacentHTML("beforeend", `<option value="${f}">${pretty(f)}</option>`);
    }
    syncFaultBtn();
    if (!fusesBuilt) {
      fusesBuilt = true;
      $("fuses").innerHTML = Object.entries(p.fuses).map(([ref, f]) =>
        `<label><input type="checkbox" data-fuse="${ref}"> <b>${ref}</b> ${f.amps ? f.amps + " A, " : ""}${pretty(f.what)}</label>`).join("");
      for (const cb of $("fuses").querySelectorAll("input")) {
        cb.addEventListener("change", () => panel({ fuse: [cb.dataset.fuse, cb.checked] }));
      }
    } else {
      for (const cb of $("fuses").querySelectorAll("input")) cb.checked = !!(p.fuses[cb.dataset.fuse] || {}).pulled;
    }
  }

  start();
})();
