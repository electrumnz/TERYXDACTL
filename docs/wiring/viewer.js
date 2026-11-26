// The wiring page: lays out schematic.json (sld.js + ELK), then pan, zoom, search, tap for
// details, and live state from the simulator page (rig/) when it's running.
//
// Live state comes in two ways, both the same message from rig/rig.js:
//   - the simulator page opens this page in a panel and posts {teryxWiring: state} to it
//   - any other tab of the simulator on this device sends it on BroadcastChannel "teryx-rig"
import { layout, draw, gridRef, rowName, GRID, wireText, SVG_STYLE, packGeom, unpackGeom } from "./sld.js";

document.head.insertAdjacentHTML("beforeend", `<style>${SVG_STYLE}</style>`);

const $ = (id) => document.getElementById(id);
// Inside the simulator page (dash + wiring): the sim is right there, so no Sim or back buttons.
if (window.parent !== window) document.body.classList.add("embedded");
const stage = $("stage"), canvas = $("canvas");
const REPO = "https://github.com/electrumnz/TERYXDACTL/blob/main/";
let model, geom, svg;
const view = { x: 0, y: 0, k: 0.1 };            // top-left of the screen in drawing units, and zoom

// ------------------------------------------------------------------------------------ start
(async () => {
  try {
    const v = new URL(import.meta.url).searchParams.get("v") || "";
    model = await (await fetch("schematic.json" + (v ? `?v=${v}` : ""))).json();
    geom = cached(model) || await prebuilt(model, v) || await layout(model, new self.ELK());
    store(model, geom);
    canvas.innerHTML = draw(model, geom, { colours: coloursOn() });
    svg = canvas.querySelector("svg");
    svg.removeAttribute("width");
    svg.removeAttribute("height");
    svg.setAttribute("preserveAspectRatio", "xMinYMin meet");
    $("loading").hidden = true;
    fillPickers();
    buildKey();
    if (!fromHash()) fit();
  } catch (e) {
    $("loading-text").textContent = "Couldn't draw the wiring: " + (e.message || e);
    $("loading").classList.add("err");
    console.error(e);
  }
})();

// Laying out the whole Teryx takes a few seconds (longer on a phone). The site build saves the
// layout as layout.json; failing that, keep the last one made here for the same schematic.json.
async function prebuilt(m, v) {
  try {
    const r = await fetch("layout.json" + (v ? `?v=${v}` : ""));
    return r.ok ? unpackGeom(m, await r.json()) : null;
  } catch { return null; }
}
function cached(m) {
  try { return unpackGeom(m, JSON.parse(localStorage.getItem("teryx-wiring-geom") || "null")); } catch { return null; }
}
function store(m, g) {
  try { localStorage.setItem("teryx-wiring-geom", JSON.stringify(packGeom(m, g))); } catch { /* storage full or blocked */ }
}

// Line colours by what the wire carries, on unless turned off (remembered on this device).
function coloursOn() {
  try { return localStorage.getItem("teryx-wiring-colours") !== "off"; } catch { return true; }
}
$("cols").setAttribute("aria-pressed", String(coloursOn()));
$("cols").onclick = () => {
  const on = !svg.classList.contains("colours");
  svg.classList.toggle("colours", on);
  $("cols").setAttribute("aria-pressed", String(on));
  try { localStorage.setItem("teryx-wiring-colours", on ? "on" : "off"); } catch { /* ignore */ }
};

// ------------------------------------------------------------------------------------ view
function apply() {
  if (!svg) return;
  const W = stage.clientWidth, H = stage.clientHeight;
  svg.setAttribute("viewBox", `${view.x} ${view.y} ${W / view.k} ${H / view.k}`);
  svg.classList.toggle("far", view.k < 0.32);
  svg.classList.toggle("veryfar", view.k < 0.09);
  rulers();
}
let raf = 0;
const later = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; apply(); }); };

function zoomAt(px, py, f) {
  const k = Math.max(0.02, Math.min(6, view.k * f));
  view.x += px / view.k - px / k;
  view.y += py / view.k - py / k;
  view.k = k;
  later();
}
function show(box, pad = 60, maxK = 1.6) {
  const W = stage.clientWidth;
  // on a phone the details sheet covers the bottom half: centre in what's left
  const sheetUp = !$("info").hidden || !$("legend").hidden;
  const H = stage.clientHeight * (sheetUp && window.innerWidth < 900 ? 0.46 : 1);
  const k = Math.min(maxK, W / (box.w + 2 * pad), H / (box.h + 2 * pad));
  view.k = k;
  view.x = box.x - (W / k - box.w) / 2;
  view.y = box.y - (H / k - box.h) / 2;
  later();
}
function fit() { show({ x: 0, y: 0, w: geom.width, h: geom.height }, 20); }

window.addEventListener("resize", later);
$("fit").onclick = fit;
$("zin").onclick = () => zoomAt(stage.clientWidth / 2, stage.clientHeight / 2, 1.5);
$("zout").onclick = () => zoomAt(stage.clientWidth / 2, stage.clientHeight / 2, 1 / 1.5);

// rulers along the top and left, so you can always read the grid reference
function rulers() {
  const W = stage.clientWidth, H = stage.clientHeight;
  const step = GRID * view.k;
  const top = [], left = [];
  const c0 = Math.max(0, Math.floor(view.x / GRID)), c1 = Math.min(geom.width / GRID - 1, Math.ceil((view.x + W / view.k) / GRID));
  const r0 = Math.max(0, Math.floor(view.y / GRID)), r1 = Math.min(geom.height / GRID - 1, Math.ceil((view.y + H / view.k) / GRID));
  const every = step < 18 ? Math.ceil(18 / step) : 1;
  for (let c = c0; c <= c1; c++) if (c % every === 0) top.push(`<span style="left:${(c * GRID - view.x) * view.k}px;width:${step}px">${c + 1}</span>`);
  for (let r = r0; r <= r1; r++) if (r % every === 0) left.push(`<span style="top:${(r * GRID - view.y) * view.k}px;height:${step}px">${rowName(r)}</span>`);
  $("rtop").innerHTML = top.join("");
  $("rleft").innerHTML = left.join("");
}

// ------------------------------------------------------------------------------------ pointer
const pts = new Map();
let pinch = null, moved = 0, downAt = null;
stage.addEventListener("pointerdown", (e) => {
  if (e.target.closest(".zoom, .ruler")) return;
  stage.setPointerCapture(e.pointerId);
  pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (pts.size === 1) { moved = 0; downAt = { x: e.clientX, y: e.clientY, t: Date.now(), target: e.target }; }
  if (pts.size === 2) pinch = pinchState();
});
stage.addEventListener("pointermove", (e) => {
  if (!pts.has(e.pointerId)) return;
  const prev = pts.get(e.pointerId);
  const cur = { x: e.clientX, y: e.clientY };
  pts.set(e.pointerId, cur);
  if (pts.size === 1) {
    view.x -= (cur.x - prev.x) / view.k;
    view.y -= (cur.y - prev.y) / view.k;
    moved += Math.abs(cur.x - prev.x) + Math.abs(cur.y - prev.y);
    later();
  } else if (pts.size === 2 && pinch) {
    const now = pinchState();
    const r = stage.getBoundingClientRect();
    view.x -= (now.cx - pinch.cx) / view.k;
    view.y -= (now.cy - pinch.cy) / view.k;
    zoomAt(now.cx - r.left, now.cy - r.top, now.d / pinch.d);
    pinch = now;
    moved += 100;
  }
});
const up = (e) => {
  if (!pts.has(e.pointerId)) return;
  pts.delete(e.pointerId);
  if (pts.size < 2) pinch = null;
  if (pts.size === 0 && downAt && moved < 8 && Date.now() - downAt.t < 600) tap(downAt.target, e);
};
stage.addEventListener("pointerup", up);
stage.addEventListener("pointercancel", (e) => { pts.delete(e.pointerId); pinch = null; });
function pinchState() {
  const [a, b] = [...pts.values()];
  return { cx: (a.x + b.x) / 2, cy: (a.y + b.y) / 2, d: Math.hypot(a.x - b.x, a.y - b.y) || 1 };
}
stage.addEventListener("wheel", (e) => {
  e.preventDefault();
  const r = stage.getBoundingClientRect();
  if (e.ctrlKey || Math.abs(e.deltaY) > Math.abs(e.deltaX) && !e.shiftKey && e.deltaMode !== 0 || e.ctrlKey) {
    zoomAt(e.clientX - r.left, e.clientY - r.top, Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0025)));
  } else if (e.deltaMode === 0 && !e.ctrlKey && Math.abs(e.deltaX) < 1 && Number.isInteger(e.deltaY) && Math.abs(e.deltaY) >= 50) {
    zoomAt(e.clientX - r.left, e.clientY - r.top, Math.exp(-e.deltaY * 0.0025));     // a mouse wheel
  } else {
    view.x += e.deltaX / view.k; view.y += e.deltaY / view.k; later();                 // trackpad scroll
  }
}, { passive: false });
let lastTap = 0;
stage.addEventListener("dblclick", (e) => {
  const r = stage.getBoundingClientRect();
  zoomAt(e.clientX - r.left, e.clientY - r.top, 2);
});

// ------------------------------------------------------------------------------------ select
function tap(target, e) {
  const now = Date.now();
  if (now - lastTap < 300 && e.pointerType === "touch") {       // double tap zooms in
    const r = stage.getBoundingClientRect();
    zoomAt(e.clientX - r.left, e.clientY - r.top, 2);
    lastTap = 0;
    return;
  }
  lastTap = now;
  const go = target.closest("[data-goto]");
  if (go) return goPart(go.dataset.goto);
  const w = target.closest("[data-w]");
  if (w) return pickWire(w.dataset.w);
  const p = target.closest("[data-p]");
  if (p) return pickPart(p.dataset.p);
  clearPick();
}

function clearPick() {
  for (const el of svg.querySelectorAll(".pick")) el.classList.remove("pick");
  svg.classList.remove("picking");
  $("info").hidden = true;
  history.replaceState(null, "", location.pathname + location.search);
}

function bboxOf(els) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const el of els) {
    const b = el.getBBox();
    const t = el.closest("[transform]");
    const m = t && t !== el ? /translate\(([-\d.]+) ([-\d.]+)\)/.exec(t.getAttribute("transform")) : null;
    const ox = m ? +m[1] : 0, oy = m ? +m[2] : 0;
    x0 = Math.min(x0, b.x + ox); y0 = Math.min(y0, b.y + oy);
    x1 = Math.max(x1, b.x + b.width + ox); y1 = Math.max(y1, b.y + b.height + oy);
  }
  return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
}

function pickWire(id, zoom = false) {
  const w = model.wires.find((q) => q.id === id);
  if (!w) return;
  clearPick();
  const els = [...svg.querySelectorAll(`[data-w="${CSS.escape(id)}"]`)];
  els.forEach((el) => el.classList.add("pick"));
  svg.classList.add("picking");
  const dev = (end) => model.devices[end[0]];
  const pinDesc = (end) => (dev(end).pins[end[1]] || {}).desc;
  const sec = model.sections.find((s) => s.key === w.sec);
  const st = model.statuses[w.status] || {};
  const end = (e) => `<button class="lnk" data-dev="${e[0]}">${e[0]}.${e[1]}</button>
    <small>${esc(dev(e).name)}${pinDesc(e) ? ", " + esc(pinDesc(e)) : ""}</small>`;
  info(`<h2>Wire ${esc(w.id)} <span class="tagst" style="--c:${st.colour}">${esc(st.label || w.status)}</span></h2>
    <div class="kv">
      <span>From</span><div>${end(w.from)}</div>
      <span>To</span><div>${w.earth ? end(w.earth === "to" ? w.from : w.to) + " <small>(earth)</small> " : ""}${end(w.earth === "from" ? w.to : w.earth === "to" ? w.to : w.to)}</div>
      <span>Size</span><div>${w.mm2 != null ? w.mm2 + " mm²" : "not set"}</div>
      <span>Colour</span><div>${w.colour || "not set"}</div>
      <span>Fuse</span><div>${w.fuse != null ? w.fuse + " A" + (w.inline_fuse != null ? " in line" : "") : "none"}</div>
      ${w.via ? `<span>In line</span><div>${esc(w.via)}</div>` : ""}
      ${w.bus ? `<span>CAN bus</span><div>${esc(w.bus)}</div>` : ""}
      <span>Carries</span><div>${esc((model.lines || {})[w.line] || w.line)}</div>
      <span>System</span><div>${sec.no}. ${esc(sec.title)}</div>
      ${w.optional ? `<span>Optional</span><div>Yes, the Teryx works without it</div>` : ""}
    </div>
    ${w.note ? `<p>${esc(w.note)}</p>` : ""}
    ${w.inline_fuse != null ? simButtons([[`Pull or refit fuse ${w.inline_fuse} A`, { fuse: [w.id, !pulled(w.id)] }]]) : ""}
    <p class="small">Label on the drawing: <code>${esc(wireText(w))}</code></p>`);
  if (zoom && els.length) show(bboxOf(els), 120, 1.4);
  setHash(`w=${id}`);
}

function pickPart(pid, zoom = false) {
  const part = model.parts[pid];
  if (!part) return;
  const d = model.devices[part.dev];
  clearPick();
  for (const p of d.parts) svg.querySelector(`[data-p="${CSS.escape(p)}"]`)?.classList.add("pick");
  svg.classList.add("picking");
  const st = model.statuses[d.status] || {};
  const wiresOf = (pin) => model.wires.filter((w) => (w.from[0] === part.dev && w.from[1] === pin) || (w.to[0] === part.dev && w.to[1] === pin));
  const pins = Object.entries(d.pins).map(([pin, p]) => {
    const ws = wiresOf(pin);
    return `<tr><td><b>${esc(pin)}</b></td><td>${esc(p.v)}${p.fuse_a ? `, ${p.fuse_a} A` : ""}</td><td>${esc(p.desc || "")}</td>
      <td>${ws.map((w) => `<button class="lnk" data-wire="${w.id}">${w.id}</button>`).join(" ") || "<small>not wired</small>"}</td></tr>`;
  }).join("");
  const sys = model.sections.find((q) => q.key === part.sec);
  const n = geom.nodes[pid];
  info(`<h2>-${esc(d.tag)} ${esc(part.dev)} <span class="tagst" style="--c:${st.colour}">${esc(st.label || d.status)}</span></h2>
    <p class="nm">${esc(d.name)}${d.optional ? " <small>(optional)</small>" : ""}</p>
    ${d.note ? `<p>${esc(d.note)}</p>` : ""}
    ${d.check ? `<p class="chk"><b>To check:</b> ${esc(d.check)}</p>` : ""}
    ${d.doc ? `<p><a href="${REPO + d.doc}" target="_blank" rel="noopener">${esc(d.doc)}</a></p>` : ""}
    <p><small>At ${gridRef(n.x + 1, n.y + 1)}${sys ? `, ${sys.no}. ${esc(sys.title.split(":")[0])}` : ""}</small></p>
    ${simButtons(controlsFor(part.dev))}
    <h3>Pins</h3><table class="pins">${pins}</table>`);
  if (zoom) goPart(pid, false);
  setHash(`d=${part.dev}`);
}

function goPart(pid, select = true) {
  const n = geom.nodes[pid];
  if (!n) return;
  if (select) pickPart(pid);
  show({ x: n.x, y: n.y, w: n.shape.w, h: n.shape.h }, 200, 1.4);
}

function info(html) {
  $("info-body").innerHTML = html;
  $("info").hidden = false;
  $("legend").hidden = true;
}
$("info-close").onclick = clearPick;
for (const b of document.querySelectorAll("[data-close]")) b.onclick = () => { $(b.dataset.close).hidden = true; };
$("info").addEventListener("click", (e) => {
  const sb = e.target.closest("button.simbtn");
  if (sb) { toSim(JSON.parse(sb.dataset.cmd)); sb.disabled = true; setTimeout(refreshInfo, 500); return; }
  const b = e.target.closest("button.lnk");
  if (!b) return;
  if (b.dataset.wire) pickWire(b.dataset.wire, true);
  else if (b.dataset.part) goPart(b.dataset.part);
  else if (b.dataset.dev) goPart(b.dataset.dev);
});
$("key").onclick = () => { $("legend").hidden = !$("legend").hidden; if (!$("legend").hidden) $("info").hidden = true; };

const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
function setHash(h) { history.replaceState(null, "", "#" + h); }
function fromHash() {
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.get("w")) { pickWire(h.get("w"), true); return true; }
  if (h.get("d") && model.devices[h.get("d")]) { goPart(model.devices[h.get("d")].parts[0]); return true; }
  if (h.get("s") && showSystem(h.get("s"))) return true;
  return false;
}

// ------------------------------------------------------------------------------------ search
function fillPickers() {
  const opts = [];
  for (const [id, d] of Object.entries(model.devices)) if (d.parts.length) opts.push(`<option value="${id}">${esc(d.name)}</option>`);
  for (const w of model.wires) opts.push(`<option value="${w.id}">${w.from.join(".")} to ${w.to.join(".")}</option>`);
  $("ids").innerHTML = opts.join("");
  $("secs").innerHTML = `<option value="">Systems</option>` + model.sections.map((s) => `<option value="${s.key}">${s.no}. ${esc(s.title)}</option>`).join("");
}
$("secs").onchange = (e) => {
  showSystem(e.target.value);
  e.target.value = "";
};
// Light up one system's parts and wires (they stay where they are on the canvas) and fit them.
function showSystem(key) {
  const f = geom.frames.find((q) => q.key === key);
  if (!f) return false;
  clearPick();
  const sec = model.sections.find((q) => q.key === key);
  for (const p of sec.parts) svg.querySelector(`[data-p="${CSS.escape(p)}"]`)?.classList.add("pick");
  for (const w of sec.wires) for (const el of svg.querySelectorAll(`[data-w="${CSS.escape(w)}"]`)) el.classList.add("pick");
  svg.classList.add("picking");
  show(f, 30);
  setHash(`s=${key}`);
  return true;
}
$("search").onsubmit = (e) => {
  e.preventDefault();
  const q = $("q").value.trim();
  if (!q) return;
  const Q = q.toUpperCase();
  const w = model.wires.find((x) => x.id.toUpperCase() === Q);
  if (w) { pickWire(w.id, true); return; }
  let d = model.devices[Q] ? Q : Object.keys(model.devices).find((k) => model.devices[k].parts.length &&
    (k.includes(Q) || model.devices[k].name.toUpperCase().includes(Q)));
  if (d && model.devices[d].parts.length) {
    goPart(d);
    $("q").blur();
  }
};

// ------------------------------------------------------------------------------------ key
const LINE_HEX = { hv: "#e16f24", "12v": "#d1242f", logic: "#0969da", gnd: "#24292f", can: "#1a7f37", signal: "#8a6a00" };
function buildKey() {
  $("linekey").innerHTML = Object.entries(model.lines || {}).map(([k, label]) =>
    `<li><svg width="46" height="10"><path d="M2 5H44" stroke="${LINE_HEX[k] || "#24292f"}" stroke-width="3"/></svg>${esc(label)}</li>`).join("");
  const row = (y, html, text) => `<g transform="translate(0 ${y})">${html}<text x="120" y="5" class="kt">${text}</text></g>`;
  const line = (cls) => `<path class="w ${cls}" d="M10 0H100"/>`;
  $("keysvg").innerHTML = [
    row(16, line("st-planned"), "Wire, our design (not built yet)"),
    row(42, line("st-tbc"), "Wire, TBC: needs checking on the Teryx"),
    row(68, line("st-placeholder"), "Placeholder or later add-on"),
    row(94, line("heavy"), "Heavy cable, 6 mm² and up"),
    row(120, line("st-planned opt"), "Optional (faded)"),
    row(176, `<line class="lead" x1="10" y1="0" x2="100" y2="0"/><rect class="sym" x="40" y="-6" width="30" height="12" fill="#fff"/>`, "Fuse"),
    row(206, `<circle class="sym" cx="55" r="11"/><path class="sym" d="M47 -8L63 8M47 8L63 -8"/>`, "Lamp"),
    row(236, `<line class="lead" x1="10" y1="0" x2="45" y2="0"/><line class="blade" x1="45" y1="0" x2="66" y2="-10"/><path class="sym" d="M66 0H100M66 0v-4"/>`, "Switch or relay contact"),
    row(268, `<line class="lead" x1="55" y1="-12" x2="55" y2="4"/><line class="sym" x1="45" y1="4" x2="65" y2="4"/><line class="sym" x1="49" y1="9" x2="61" y2="9"/><line class="sym" x1="53" y1="14" x2="57" y2="14"/>`, "Earth (to the star point)"),
  ].join("");
}

// ------------------------------------------------------------------------------------ sim controls
// With the simulator running, the switches, key, E-stop and fuses on the canvas work: tap one,
// then the button in its info sheet. The command goes to the simulator page the same way the
// live state comes from it (the parent page, or the "teryx-rig" BroadcastChannel).
let lastLive = null;
const inp = (k) => lastLive && lastLive.inputs ? lastLive.inputs[k] : undefined;
const pulled = (ref) => !!(lastLive && (lastLive.pulled || []).includes(ref));
function controlsFor(dev) {
  const tog = (label, k) => [`${label}: turn ${inp(k) ? "off" : "on"}`, { [k]: !inp(k) }];
  const cyc = (k, vals) => { const i = vals.indexOf(inp(k) ?? null); const nx = vals[(i + 1) % vals.length]; return [`Move to ${nx ?? "off"}`, { [k]: nx }]; };
  switch (dev) {
    case "KEY": case "KIT_KEY": return [tog("Key", "key")];
    case "BRAKE_SW": return [tog("Brake", "brake")];
    case "PARK_SW": return [tog("Park brake", "park")];
    case "ESTOP": return [[inp("estop") ? "Release the E-stop" : "Press the E-stop", { estop: !inp("estop") }]];
    case "LIMP_SW": return [tog("Backup lights switch", "backup_lights")];
    case "TRAILER": return [[inp("trailer") ? "Unplug the trailer" : "Plug the trailer in", { trailer: !inp("trailer") }]];
    case "FNR": return ["forward", "neutral", "reverse"].map((v) => [`F-N-R to ${v}`, { fnr: v }]);
    case "HSW_CAB": return [["Winch in", { winch_cab: "in" }], ["Winch off", { winch_cab: null }], ["Winch out", { winch_cab: "out" }]];
    case "BRK_WINCH": return [[inp("winch_breaker") === false ? "Close the winch breaker" : "Trip the winch breaker", { winch_breaker: inp("winch_breaker") === false }]];
    case "FB": case "FB2": return Object.entries(model.devices[dev].pins).filter(([p, s]) => s.fuse_a != null)
      .map(([p, s]) => [`${pulled(`${dev}.${p}`) ? "Refit" : "Pull"} ${p} (${s.fuse_a} A)`, { fuse: [`${dev}.${p}`, !pulled(`${dev}.${p}`)] }]);
    default: return [];
  }
}
function simButtons(list) {
  if (!list.length) return "";
  if (!liveSeen) return `<p class="small">Open this from the simulator (Sim, then Wiring) to work the controls here.</p>`;
  return `<h3>In the simulator</h3><p class="simrow">${list.map(([label, cmd]) =>
    `<button class="simbtn" data-cmd='${esc(JSON.stringify(cmd))}'>${esc(label)}</button>`).join(" ")}</p>`;
}
function toSim(cmd) {
  try { if (window.parent !== window) window.parent.postMessage({ teryxPanel: cmd }, "*"); } catch { /* ignore */ }
  try { new BroadcastChannel("teryx-rig").postMessage({ teryxPanel: cmd }); } catch { /* ignore */ }
}
function refreshInfo() {
  if ($("info").hidden) return;
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.get("d")) pickPart(h.get("d"));
  else if (h.get("w")) pickWire(h.get("w"));
}

// ------------------------------------------------------------------------------------ live
let liveSeen = 0;
// Element lists, found once (a few hundred wires, three times a second).
let liveEls = null;
function liveIndex() {
  const wires = {};
  for (const el of svg.querySelectorAll(".wires [data-w], .isym[data-w]")) (wires[el.dataset.w] = wires[el.dataset.w] || []).push(el);
  const parts = {};
  for (const el of svg.querySelectorAll(".parts [data-p]")) parts[el.dataset.p] = el;
  return { wires, parts, contacts: [...svg.querySelectorAll(".contact")], glows: [...svg.querySelectorAll(".glow")],
    fuses: [...svg.querySelectorAll("[data-f]")] };
}
// What each thing was last time, so a change can pulse and go on the list.
const prevWire = {}, prevVolts = {}, prevContact = {}, prevLamp = {}, lastPulse = {}, prevPin = {}, seenPin = {};
let frameNo = 0;
const EARTHS = new Set(["GND_STAR.G", "BAT12.neg"]);
let firstFrame = true;
const changes = [];                                   // newest first: {t, text, part?, wire?}

function onLive(st) {
  if (!svg || !st || !st.pins) return;
  liveSeen = Date.now();
  lastLive = st;
  liveEls = liveEls || liveIndex();
  $("live").hidden = false;
  $("live").textContent = st.t != null ? `LIVE ${(+st.t).toFixed(0)} s` : "LIVE";
  svg.classList.add("live");
  const lv = (dev, pin) => st.pins[`${dev}.${pin}`];
  const level = (x) => (x && x[1] != null ? x[1] * (x[2] ?? 1) : 0);
  const cut = new Set(st.cut || []), blown = new Set(st.blown || []);
  const frame = [];                                   // this frame's changes
  const changedParts = new Map();                     // part -> what changed there
  const note = (part, text) => { if (part && model.parts[part]) changedParts.set(part, [...(changedParts.get(part) || []), text]); };

  // Each pin's own level: a part only flashes when one of its own pins changes, not because
  // something further along a shared net did.
  const clsOf = (v) => (v > 30 ? "hv" : v > 7 ? "12" : v > 0.5 ? "lo" : "");
  for (const w of model.wires) {
    for (const end of [w.from, w.to]) {
      const key = `${end[0]}.${end[1]}`;
      if (key in seenPin && seenPin[key] === frameNo) continue;
      seenPin[key] = frameNo;
      const now = clsOf(level(lv(end[0], end[1])));
      if (prevPin[key] !== undefined && prevPin[key] !== now && !(w.earth && EARTHS.has(key)))
        note(end[0], `${end[1]} ${now ? "on" : "off"}`);
      prevPin[key] = now;
    }
  }
  frameNo++;

  for (const w of model.wires) {
    const a = lv(w.from[0], w.from[1]), b = lv(w.to[0], w.to[1]);
    // a diode in line only lets the feed end through, so the wire shows what its feed end is doing
    const v = w.via_kind === "diode" || w.via_kind === "flyback" ? level(a) : Math.max(level(a), level(b));
    const pwm = [a, b].some((x) => x && x[1] > 0.5 && x[2] != null && x[2] < 0.999);
    const cls = cut.has(w.id) ? "cut" : v > 30 ? "on-hv" : v > 7 ? "on-12" : v > 0.5 ? "on-lo" : "";
    const state = cls + (pwm ? "+pwm" : "");
    const was = prevWire[w.id];
    // a big enough move on an analogue signal (throttle, sensors) counts as a change too
    const moved = was === state && cls === "on-lo" && Math.abs(v - (prevVolts[w.id] ?? v)) > 0.4;
    if (was !== state || moved) {
      for (const el of liveEls.wires[w.id] || []) {
        el.classList.remove("on-hv", "on-12", "on-lo", "cut", "pwm");
        if (cls) el.classList.add(cls);
        if (pwm && cls && cls !== "cut") el.classList.add("pwm");
      }
      if (!firstFrame) {
        const what = cls === "cut" ? "cut" : !cls ? "off" : moved ? `${v.toFixed(1)} V` : pwm ? "on (PWM)" : "on";
        frame.push({ wire: w.id, text: `${w.id} ${what}` });
        pulseWire(w.id);
      }
      prevWire[w.id] = state;
    }
    if (was !== state || moved || prevVolts[w.id] == null) prevVolts[w.id] = v;
  }
  // relay contacts: closed to NO when COM and NO are on one net
  for (const c of liveEls.contacts) {
    const [dev, n] = c.dataset.k.split(":");
    const com = lv(dev, `COM${n}`), no = lv(dev, `NO${n}`);
    const closed = !!(com && no && com[0] === no[0]);
    if (prevContact[c.dataset.k] !== closed) {
      const blade = c.querySelector(".blade");
      const [x, y] = (closed ? blade.dataset.no : blade.dataset.nc).split(" ");
      blade.setAttribute("x2", x); blade.setAttribute("y2", y);
      c.classList.toggle("on", closed);
      if (!firstFrame) {
        const t = `${dev} relay ${n} ${closed ? "on" : "off"}`;
        frame.unshift({ part: dev, text: t, strong: true });
        note(dev, t);
        pulseEl(c);
      }
      prevContact[c.dataset.k] = closed;
    }
  }
  // lamps: lit when one side is up and the other is down
  for (const g of liveEls.glows) {
    const [dev, pin] = g.dataset.k.split(":");
    const d = model.devices[dev];
    const p = lv(dev, pin);
    const others = Object.keys(d.pins).filter((q) => q !== pin && (d.pins[q].v === "gnd" || /neg|GND/.test(q)));
    const low = others.some((q) => { const o = lv(dev, q); return o && o[1] != null && o[1] < 1; });
    const lit = low && level(p) > 5 ? Math.min(1, level(p) / 12) : 0;
    g.style.fill = lit ? `rgba(255, 196, 0, ${0.25 + 0.6 * lit})` : "";
    const on = lit > 0;
    if (prevLamp[g.dataset.k] !== on) {
      if (prevLamp[g.dataset.k] !== undefined) {
        const t = `${dev} ${on ? "lit" : "off"}`;
        frame.unshift({ part: dev, text: t, strong: true });
        note(dev, t);
      }
      prevLamp[g.dataset.k] = on;
    }
  }
  for (const f of liveEls.fuses) {
    const was = f.classList.contains("blown"), now = blown.has(f.dataset.f);
    if (was !== now) {
      f.classList.toggle("blown", now);
      const [dev, way] = f.dataset.f.split(".");
      frame.unshift({ part: dev, text: `${dev} ${way} ${now ? "pulled" : "back in"}`, strong: true });
      note(dev, `${way} ${now ? "pulled" : "back in"}`);
    }
  }
  for (const [part] of changedParts) pulsePart(part);
  firstFrame = false;
  if (frame.length) addChanges(st.t, frame, changedParts);
}

// ---- pulses: a quick amber flash on whatever changed, big enough to see zoomed right out
function pulseWire(id) {
  const now = Date.now();
  if (now - (lastPulse[id] || 0) < 1200) return;    // a busy analogue wire doesn't strobe
  lastPulse[id] = now;
  for (const el of liveEls.wires[id] || []) {
    if (el.tagName !== "path") continue;
    const ghost = el.cloneNode();
    ghost.removeAttribute("data-w");
    ghost.setAttribute("class", "wpulse");
    el.parentNode.insertBefore(ghost, el);
    ghost.addEventListener("animationend", () => ghost.remove());
  }
}
function pulsePart(pid) {
  const now = Date.now();
  if (now - (lastPulse["p:" + pid] || 0) < 1200) return;
  lastPulse["p:" + pid] = now;
  const g = liveEls.parts[pid], n = geom.nodes[pid];
  if (!g || !n) return;
  const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  r.setAttribute("class", "ppulse");
  r.setAttribute("x", -14); r.setAttribute("y", -14);
  r.setAttribute("width", n.shape.w + 28); r.setAttribute("height", n.shape.h + 28);
  r.setAttribute("rx", 10);
  g.insertBefore(r, g.firstChild);
  r.addEventListener("animationend", () => r.remove());
}
function pulseEl(el) {
  const b = el.getBBox();
  const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  r.setAttribute("class", "ppulse small");
  r.setAttribute("x", b.x - 6); r.setAttribute("y", b.y - 6);
  r.setAttribute("width", b.width + 12); r.setAttribute("height", b.height + 12);
  r.setAttribute("rx", 4);
  el.insertBefore(r, el.firstChild);
  r.addEventListener("animationend", () => r.remove());
}

// ---- the "What changed" list: newest first, tap one to go to it
function addChanges(t, frame, changedParts) {
  // one line per part that changed (relays and lamps by name), wires on their own only if
  // nothing else explains them; a key turn changes 100 wires, so keep it short
  const lines = [];
  const seen = new Set();
  for (const f of frame) if (f.strong && !seen.has(f.text)) { lines.push(f); seen.add(f.text); }
  for (const [part, what] of changedParts) {
    if (lines.some((l) => l.part === part)) continue;
    const uniq = [...new Set(what)];
    lines.push({ part, text: uniq.length > 3 ? `${part}: ${uniq.length} pins changed` : `${part}: ${uniq.join(", ")}` });
  }
  const tt = t != null ? `${(+t).toFixed(1)} s` : "";
  for (const l of lines.slice(0, 12).reverse()) changes.unshift({ ...l, t: tt });
  if (lines.length > 12) changes.unshift({ text: `and ${lines.length - 12} more`, t: tt });
  changes.length = Math.min(changes.length, 40);
  drawChanges();
}
function drawChanges() {
  const box = $("changes");
  if (box.hidden) {
    // folded or open as you last left it; on a small pane it starts folded
    let saved = null;
    try { saved = localStorage.getItem("teryx-wiring-changes"); } catch { /* ignore */ }
    box.classList.toggle("shut", saved ? saved === "shut" : innerHeight < 520);
    $("changes-toggle").setAttribute("aria-expanded", String(!box.classList.contains("shut")));
  }
  box.hidden = false;
  $("changes-list").innerHTML = changes.map((c, i) =>
    `<li><button data-i="${i}"${c.part || c.wire ? "" : " disabled"}><span>${esc(c.t)}</span>${esc(c.text)}</button></li>`).join("");
  $("changes-n").textContent = changes.length;
}
$("changes-list").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-i]");
  if (!b) return;
  const c = changes[+b.dataset.i];
  if (c.part) goPart(c.part);
  else if (c.wire) pickWire(c.wire, true);
});
$("changes-toggle").onclick = () => {
  const shut = $("changes").classList.toggle("shut");
  $("changes-toggle").setAttribute("aria-expanded", String(!shut));
  try { localStorage.setItem("teryx-wiring-changes", shut ? "shut" : "open"); } catch { /* ignore */ }
};
$("changes-clear").onclick = () => { changes.length = 0; drawChanges(); };
window.addEventListener("message", (e) => { if (e.data && e.data.teryxWiring) onLive(e.data.teryxWiring); });
try { new BroadcastChannel("teryx-rig").onmessage = (e) => { if (e.data && e.data.teryxWiring) onLive(e.data.teryxWiring); }; } catch { /* old browser */ }
setInterval(() => {
  if (liveSeen && Date.now() - liveSeen > 3000) {
    $("live").textContent = "LIVE (paused)";
  }
}, 1000);
// tell a simulator page we're here, so it starts sending
try { window.parent !== window && window.parent.postMessage({ teryxWiringHello: true }, "*"); } catch { /* ignore */ }
try { new BroadcastChannel("teryx-rig").postMessage({ teryxWiringHello: true }); } catch { /* ignore */ }
