// Teryx whole-vehicle schematic: lays out schematic.json with ELK and draws it as one SVG,
// one canvas with every device once and every wire drawn end to end.
//
// schematic.json is made from config/wiring.yaml by `python -m teryx wiring` (teryx/wiring_sld.py).
// This file is shared by the page (index.html via viewer.js) and the Node check in CI
// (tools/wiring_sld_check.mjs), so it never touches the DOM.
//
//   const geom = await layout(model, new ELK());   // where everything goes
//   const svg  = draw(model, geom);                // one big SVG string
//
// Symbols are drawn here in IEC 60617 style (our own drawing, MIT): fuse = box on the line,
// lamp = circle with a cross, motor = circle with M, contact = gap with a blade, relay coil
// = box, battery = long and short plates, earth = three shrinking bars.

// A short fingerprint of schematic.json, so a saved layout is only used for the same drawing.
export function sig(m) {
  const s = JSON.stringify(m);
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return `sld2:${s.length}:${h}`;
}

// A layout without the shapes (they're quick to rebuild from the model), for saving.
export function packGeom(m, g) {
  const nodes = Object.fromEntries(Object.entries(g.nodes).map(([k, n]) => [k, { x: n.x, y: n.y }]));
  return { sig: sig(m), geom: { ...g, nodes } };
}
export function unpackGeom(m, saved) {
  if (!saved || saved.sig !== sig(m)) return null;
  const shapes = shapesFor(m);
  for (const [k, n] of Object.entries(saved.geom.nodes)) n.shape = shapes[k];
  return saved.geom;
}

export const GRID = 400;            // one grid square, in drawing units (references like C14)
const P = 22;                       // pin pitch
const FONT = "Barlow Condensed, Arial Narrow, Arial, sans-serif";
const SANS = "Inter, Arial, sans-serif";
const MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
const ROW_KINDS = new Set(["lamp", "switch", "key", "estop", "limit", "fuse", "breaker", "diode",
  "battery", "motor", "speaker", "isolator", "contactor"]);
const tw = (s, px = 11) => String(s).length * px * 0.62 + 4;    // text width, monospace (a touch generous)
const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const r1 = (n) => Math.round(n * 10) / 10;

// ------------------------------------------------------------------------------------ sizes
// Every part becomes a node with fixed ports. Coordinates are local to the node.
function partShape(model, part) {
  const dev = model.devices[part.dev];
  const foot = 0;
  const earthS = part.ports.filter((p) => p.side === "S");
  const title = `-${dev.tag} ${part.dev}`;
  if (ROW_KINDS.has(part.kind)) return rowShape(model, part, dev, title, foot, earthS);
  if (part.kind === "bus") {
    const nW = part.ports.filter((p) => p.side === "W").length, nE = part.ports.filter((p) => p.side === "E").length;
    const h = Math.max(80, Math.max(nW, nE) * P + 40);
    const ports = part.ports.map((p) => ({ id: pid(part, p), pin: p.pin, side: p.side, x: p.side === "W" ? 0 : 50, y: h / 2 + 10 }));
    return { w: 50, h: h + foot, ports, title, kind: "bus", bodyH: h, foot };
  }
  if (part.kind === "star") {
    const refs = model.earth_refs;
    const w = 330, h = 44 + refs.length * 16 + 16;
    const ports = part.ports.filter((p) => p.side !== "S").map((p) => ({ id: pid(part, p), pin: p.pin, side: "W", x: 0, y: 44 }));
    return { w, h: h + foot, ports, title, kind: "star", bodyH: h, foot, refs };
  }
  // boxes: module, controller, converter, machine, connector, camera, display, pot, relays, fuseblock
  const west = part.ports.filter((p) => p.side === "W"), east = part.ports.filter((p) => p.side === "E");
  let rows;                                        // [[westPort|null, eastPort|null, decoration]]
  if (part.kind === "relays") rows = relayRows(west, east);
  else if (part.kind === "fuseblock") rows = fuseRows(west, east, dev);
  else {
    rows = [];
    for (let i = 0; i < Math.max(west.length, east.length); i++) rows.push([west[i] || null, east[i] || null, null]);
  }
  const lw = Math.max(0, ...west.map((p) => tw(p.pin, 11))), le = Math.max(0, ...east.map((p) => tw(p.pin, 11)));
  const decoW = part.kind === "relays" ? 80 : part.kind === "fuseblock" ? 100 : 30;
  const w = snap(Math.max(170, tw(title, 13) + 44, lw + le + decoW), 10);
  const nameLines = wrap(dev.name, Math.floor((w - 46) / 6.2), 2);
  const headH = 22 + nameLines.length * 13 + 6;
  const bodyH = headH + Math.max(1, rows.length) * P + 8;
  const earthH = earthS.length ? 40 : 0;
  const h = bodyH + earthH + foot;
  const ports = [];
  rows.forEach(([pw, pe], i) => {
    const y = headH + i * P + P / 2;
    if (pw) ports.push({ id: pid(part, pw), pin: pw.pin, side: "W", x: 0, y });
    if (pe) ports.push({ id: pid(part, pe), pin: pe.pin, side: "E", x: w, y });
  });
  const earths = earthS.map((p, i) => ({ pin: p.pin, x: w / 2 + (i - (earthS.length - 1) / 2) * 56, y: bodyH }));
  return { w, h, ports, title, kind: part.kind, rows, headH, bodyH, nameLines, earths, foot };
}

function relayRows(west, east) {
  const rows = [], usedE = new Set();
  const chan = (pin) => (pin.match(/^(?:COM|NO|NC)(\d+)$/) || [])[1];
  const others = [];
  for (const pw of west) {
    const n = chan(pw.pin);
    if (n && pw.pin.startsWith("COM")) {
      const no = east.find((p) => p.pin === `NO${n}`), nc = east.find((p) => p.pin === `NC${n}`);
      rows.push([pw, no || null, { contact: n, no: !!no, nc: !!nc, first: true }]);
      if (no) usedE.add(no);
      if (nc) { rows.push([null, nc, { contact: n, nc: true }]); usedE.add(nc); }
      if (!no && !nc) rows[rows.length - 1][2] = { contact: n };
    } else others.push(pw);
  }
  const restE = east.filter((p) => !usedE.has(p));
  for (let i = 0; i < Math.max(others.length, restE.length); i++) rows.push([others[i] || null, restE[i] || null, null]);
  return rows;
}

function fuseRows(west, east, dev) {
  const rows = [];
  const all = [...west, ...east];
  const inp = all.filter((p) => p.pin === "IN");
  const ways = all.filter((p) => p.pin !== "IN");
  rows.push([inp.find((p) => p.side === "W") || null, inp.find((p) => p.side === "E") || null, { busTop: true }]);
  for (const p of ways) {
    const pin = dev.pins[p.pin] || {};
    rows.push([p.side === "W" ? p : null, p.side === "E" ? p : null, { fuse: p.pin, amps: pin.fuse_a }]);
  }
  return rows;
}

function rowShape(model, part, dev, title, foot, earthS) {
  if (part.kind === "battery") {
    // drawn upright: + at the top, - at the bottom, both terminals on the right
    const [pos, neg] = part.rows[0];
    const w = 110, head = 28, bodyH = head + 76;
    const negEarth = earthS.some((p) => p.pin === neg);
    const ports = [{ id: `${part.id}|${pos}`, pin: pos, side: "E", x: w, y: head + 10 }];
    if (!negEarth) ports.push({ id: `${part.id}|${neg}`, pin: neg, side: "E", x: w, y: head + 70 });
    return { w, h: bodyH + (negEarth ? 36 : 0) + foot, ports, title, kind: "battery", head, bodyH, foot, pos, neg, negEarth };
  }
  // rows: [left pin, right pin | null, glyph]; common joins the right ends when set
  const rowsIn = part.rows || [];
  const common = part.common;
  const sideOf = (pin) => (part.ports.find((p) => p.pin === pin && p.side !== "S") || {}).side;
  const earthed = earthS.some((p) => p.pin === common);
  // Mirror when the common (or the right pin of a single row) is fed from the left.
  let mirror = false;
  if (common && !earthed) mirror = sideOf(common) === "W" && !rowsIn.some((r) => sideOf(r[0]) === "W");
  else if (!common && rowsIn.length === 1 && rowsIn[0][1]) mirror = sideOf(rowsIn[0][1]) === "W" && sideOf(rowsIn[0][0]) === "E";
  const RH = 40, head = 28;
  const w = common ? 150 : 130;
  const bodyH = head + rowsIn.length * RH + 4;
  const earthH = earthed ? 36 : 0;
  const ports = [];
  const L = mirror ? "E" : "W", R = mirror ? "W" : "E";
  const xL = mirror ? w : 0, xR = mirror ? 0 : w;
  rowsIn.forEach(([a, b], i) => {
    const y = head + i * RH + RH / 2;
    ports.push({ id: `${part.id}|${a}`, pin: a, side: L, x: xL, y });
    if (b) ports.push({ id: `${part.id}|${b}`, pin: b, side: R, x: xR, y });
  });
  const midY = head + (rowsIn.length * RH) / 2;
  if (common && !earthed) ports.push({ id: `${part.id}|${common}`, pin: common, side: R, x: xR, y: snapTo(midY, 10) });
  const nameLines = wrap(dev.name, 26).slice(0, 1);
  return { w, h: bodyH + earthH + foot, ports, title, kind: part.kind, rowsIn, common, earthed, mirror, head, RH, bodyH, foot, nameLines };
}

const pid = (part, p) => `${part.id}|${p.pin}|${p.side}`;
const snap = (v, s) => Math.ceil(v / s) * s;
const snapTo = (v, s) => Math.round(v / s) * s;
function wrap(s, n, max = 3) {
  const words = String(s).split(/\s+/), out = [];
  let cur = "";
  for (const w of words) {
    if ((cur + " " + w).trim().length > n && cur) { out.push(cur); cur = w; } else cur = (cur + " " + w).trim();
  }
  if (cur) out.push(cur);
  if (out.length > max) { out.length = max; out[max - 1] = trunc(out[max - 1] + " …", n); }
  return out.map((l) => trunc(l, n));
}

// ------------------------------------------------------------------------------------ layout
const LAYOUT = {
  "elk.algorithm": "layered",
  "elk.direction": "RIGHT",
  "elk.edgeRouting": "ORTHOGONAL",
  "elk.portConstraints": "FIXED_POS",
  "elk.spacing.nodeNode": "40",
  "elk.layered.spacing.nodeNodeBetweenLayers": "200",
  "elk.layered.spacing.edgeNodeBetweenLayers": "30",
  "elk.spacing.edgeEdge": "18",
  "elk.layered.spacing.edgeEdgeBetweenLayers": "18",
  "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
  "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
  "elk.layered.crossingMinimization.forceNodeModelOrder": "false",
  "elk.layered.mergeEdges": "true",
  "elk.padding": "[top=20,left=20,bottom=20,right=20]",
  "elk.separateConnectedComponents": "true",
  "elk.spacing.componentComponent": "70",
  "elk.layered.thoroughness": "12",
};

function inlineNodes(w) {
  // Things drawn on the wire itself, in order from the `from` end.
  const out = [];
  if (w.inline_fuse != null) out.push({ kind: "fuse", text: `${w.inline_fuse} A`, w: 60, h: 30 });
  if (w.via_kind === "diode" || w.via_kind === "flyback") out.push({ kind: "diode", text: w.via, w: 44, h: 30 });
  else if (w.via_kind !== "plain") out.push({ kind: "via", text: w.via, w: Math.min(150, Math.max(70, tw(w.via, 10) + 12)), h: 30 });
  return out;
}

export function shapesFor(model) {
  const shapes = {};
  for (const part of Object.values(model.parts)) shapes[part.id] = partShape(model, part);
  return shapes;
}

export async function layout(model, elk) {
  // One graph: every device once, every wire end to end. Devices go in system order
  // (traction, 12 V, earths, then each system) so ELK keeps each system's parts together.
  const shapes = shapesFor(model);
  const order = model.sections.flatMap((s) => s.parts);
  const children = [], edges = [], inl = {};
  for (const id of order) {
    const s = shapes[id];
    children.push({
      id, width: s.w, height: s.h,
      layoutOptions: { "elk.portConstraints": "FIXED_POS" },
      ports: s.ports.map((p) => ({ id: p.id, x: p.x, y: p.y, width: 0, height: 0,
        layoutOptions: { "elk.port.side": { W: "WEST", E: "EAST", S: "SOUTH", N: "NORTH" }[p.side] } })),
    });
  }
  const bySec = Object.fromEntries(model.sections.map((s) => [s.key, s.no]));
  const wires = [...model.wires].sort((p, q) => (bySec[p.sec] || 99) - (bySec[q.sec] || 99));
  for (const w of wires) {
    if (w.earth) continue;                                   // drawn as an earth symbol on the part
    const a = portFor(shapes, w.from[0], w.from[1], "E");
    const b = portFor(shapes, w.to[0], w.to[1], "W");
    if (!a || !b) throw new Error(`wire ${w.id}: no port for ${!a ? w.from.join(".") : w.to.join(".")}`);
    const chain = inlineNodes(w);
    let prev = a;
    chain.forEach((n, i) => {
      const nid = `~${w.id}~${i}`;
      inl[nid] = { ...n, wire: w.id };
      children.push({ id: nid, width: n.w, height: n.h, layoutOptions: { "elk.portConstraints": "FIXED_POS" },
        ports: [{ id: nid + "|a", x: 0, y: n.h / 2, width: 0, height: 0, layoutOptions: { "elk.port.side": "WEST" } },
                { id: nid + "|b", x: n.w, y: n.h / 2, width: 0, height: 0, layoutOptions: { "elk.port.side": "EAST" } }] });
      edges.push({ id: `${w.id}#${i}`, sources: [prev], targets: [nid + "|a"], wire: w.id });
      prev = nid + "|b";
    });
    edges.push({ id: `${w.id}#${chain.length}`, sources: [prev], targets: [b], wire: w.id, last: true });
  }
  const g = await elk.layout({ id: "teryx", layoutOptions: LAYOUT, children,
    edges: edges.map(({ id, sources, targets }) => ({ id, sources, targets })) });
  return place(model, shapes, g, inl, Object.fromEntries(edges.map((e) => [e.id, e])));
}

function portFor(shapes, partId, pin, prefer) {
  const s = shapes[partId];
  if (!s) return null;
  const ps = s.ports.filter((p) => p.pin === pin);
  return (ps.find((p) => p.side === prefer) || ps[0] || {}).id;
}

// Put the laid-out graph on the grid, one square in from the top left. `systems` are the
// bounding boxes of each system's parts: not drawn, just so the page can jump to one.
function place(model, shapes, g, inl, edgeMeta) {
  const ox = GRID, oy = GRID;
  const nodes = {}, edges = [], inlines = [];
  for (const c of g.children) {
    if (inl[c.id]) inlines.push({ ...inl[c.id], x: ox + c.x, y: oy + c.y });
    else nodes[c.id] = { x: ox + c.x, y: oy + c.y, shape: shapes[c.id] };
  }
  for (const e of g.edges || []) {
    const meta = edgeMeta[e.id];
    for (const s of e.sections || []) {
      const pts = [s.startPoint, ...(s.bendPoints || []), s.endPoint].map((p) => [r1(ox + p.x), r1(oy + p.y)]);
      edges.push({ id: e.id, wire: meta.wire, last: !!meta.last, first: e.id.endsWith("#0"), pts,
        junctions: (e.junctionPoints || []).map((p) => [r1(ox + p.x), r1(oy + p.y)]) });
    }
  }
  const width = snap(ox + g.width + GRID / 2, GRID), height = snap(oy + g.height + GRID / 2, GRID);
  const systems = [];
  for (const s of model.sections) {
    const ns = s.parts.map((p) => nodes[p]).filter(Boolean);
    if (!ns.length) continue;
    const x0 = Math.min(...ns.map((n) => n.x)), y0 = Math.min(...ns.map((n) => n.y));
    const x1 = Math.max(...ns.map((n) => n.x + n.shape.w)), y1 = Math.max(...ns.map((n) => n.y + n.shape.h));
    systems.push({ key: s.key, no: s.no, title: s.title, x: x0 - 40, y: y0 - 40, w: x1 - x0 + 80, h: y1 - y0 + 80 });
  }
  return { width, height, frames: systems, nodes, edges, inlines };
}

// ------------------------------------------------------------------------------------ grid refs
export function gridRef(x, y) {
  const col = Math.floor(x / GRID) + 1, row = Math.floor(y / GRID);
  return rowName(row) + col;
}
export function rowName(i) {
  const A = "ABCDEFGHJKLMNPQRSTUVWXYZ";          // no I or O, like drawing sheets
  return i < A.length ? A[i] : A[Math.floor(i / A.length) - 1] + A[i % A.length];
}

// ------------------------------------------------------------------------------------ drawing
// The drawing's look. The page puts it in its own stylesheet; a saved SVG carries a copy.
export const SVG_STYLE = `
.sld .paper{fill:#fbfaf6}.sld .gmin{stroke:#ece9df;stroke-width:1}.sld .gmaj{stroke:#d6d1c2;stroke-width:1.5}
.sld .gridlbl text{font:600 64px ${MONO};fill:#c9c2ad}
.sld .frame>rect{fill:#fffefb;stroke:#24292f;stroke-width:2.5}.sld .frame .fhead{fill:#24292f;stroke:none}
.sld .fno{font:700 30px ${MONO};fill:#f5c84c}.sld .ftitle{font:600 26px ${FONT};fill:#fff;letter-spacing:.02em}
.sld .fref{font:500 15px ${MONO};fill:#c9d1d9}
.sld .w{fill:none;stroke:#24292f;stroke-width:1.4;stroke-linejoin:round}
.sld .w.heavy{stroke-width:3}.sld .w.hv{stroke:#d9480f;stroke-width:3.2}
.sld .w.st-tbc{stroke-dasharray:8 4}.sld .w.st-placeholder{stroke-dasharray:2 4;stroke:#8250df}
.sld .w.opt{stroke-opacity:.55}
.sld .jn{fill:#24292f}
.sld.colours .w.k-hv{stroke:#e16f24}.sld.colours .w.k-12v{stroke:#d1242f}.sld.colours .w.k-logic{stroke:#0969da}
.sld.colours .w.k-gnd{stroke:#24292f}.sld.colours .w.k-can{stroke:#1a7f37;stroke-width:2}.sld.colours .w.k-signal{stroke:#8a6a00}
.sld .wl{font:500 10.5px ${MONO};fill:#57606a;paint-order:stroke;stroke:#fffefb;stroke-width:3px}
.sld .wl .sw{font-size:11px;stroke:none}
.sld .box{fill:#fff;stroke:#24292f;stroke-width:1.6}.sld .hrule{stroke:#24292f;stroke-width:.8}
.sld .k-controller>.box{fill:#f6f8fa}.sld .k-relays>.box,.sld .k-fuseblock>.box{fill:#fff8e1}
.sld .st-tbc>.box{stroke-dasharray:7 4}.sld .st-placeholder>.box{stroke:#8250df;stroke-dasharray:2 4}
.sld .opt>.box{fill:#f6f6f6}
.sld .hit{fill:transparent}
.sld .tag{font:700 13px ${MONO};fill:#24292f}.sld .nm{font:400 10.5px ${SANS};fill:#57606a}
.sld .pin{font:500 11px ${MONO};fill:#24292f}.sld .pin.dim{fill:#8c959f}
.sld .sym{fill:none;stroke:#24292f;stroke-width:1.6}.sld .symf{fill:#24292f;stroke:#24292f;stroke-width:1}
.sld .sym.thick{stroke-width:3}.sld .sym.thick2{stroke-width:5}
.sld .lead{stroke:#24292f;stroke-width:1.4;fill:none}.sld .busl{stroke:#24292f;stroke-width:3}
.sld .blade{stroke:#24292f;stroke-width:1.8;stroke-linecap:round}
.sld .busbar{fill:#24292f}.sld .term{fill:#fff;stroke:#24292f;stroke-width:1.2}
.sld .sl{font:600 10px ${MONO};fill:#24292f}.sld .kl{font:700 9.5px ${MONO};fill:#57606a}
.sld .gl{font:700 13px ${FONT};fill:#24292f}.sld .gs{font:700 10px ${FONT};fill:#24292f}
.sld .el{font:500 10px ${MONO};fill:#57606a}
.sld .glow{fill:transparent;stroke:none}
.sld .xrefs{font:500 10.5px ${MONO};fill:#0969da}.sld .xr{fill:#0969da}
.sld .isym .sym{fill:#fff}
.sld .ahead{font:700 15px ${FONT};fill:#57606a;letter-spacing:.12em}.sld .arule{stroke:#d0d7de;stroke-width:1.5}
.sld .adiv{stroke:#d0d7de;stroke-width:2;stroke-dasharray:10 8}
`;

const COLOURS = { RD: "#d1242f", BK: "#24292f", OG: "#e16f24", YE: "#d4a72c", GN: "#1a7f37", BU: "#0969da", WH: "#8c959f" };

export function draw(model, geom, opts = {}) {
  const wiresById = Object.fromEntries(model.wires.map((w) => [w.id, w]));
  const out = [];
  const { width, height } = geom;
  const colours = opts.colours === false ? "" : " colours";
  out.push(`<svg xmlns="http://www.w3.org/2000/svg" class="sld${colours}" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" font-family="${FONT}">`);
  if (opts.style) out.push(`<style>${opts.style}</style>`);
  out.push(`<defs>
  <pattern id="g-minor" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" class="gmin"/></pattern>
  <pattern id="g-major" width="${GRID}" height="${GRID}" patternUnits="userSpaceOnUse"><rect width="${GRID}" height="${GRID}" fill="url(#g-minor)"/><path d="M${GRID} 0H0V${GRID}" fill="none" class="gmaj"/></pattern>
</defs>`);
  out.push(`<rect class="paper" width="${width}" height="${height}"/><rect class="gridbg" width="${width}" height="${height}" fill="url(#g-major)"/>`);
  // grid labels along the edges (the page also keeps them on screen as you pan)
  out.push(`<g class="gridlbl">`);
  for (let c = 0; c * GRID < width; c++) out.push(`<text x="${c * GRID + GRID / 2}" y="${GRID / 2 - 60}" text-anchor="middle">${c + 1}</text><text x="${c * GRID + GRID / 2}" y="${height - 40}" text-anchor="middle">${c + 1}</text>`);
  for (let r = 0; r * GRID < height; r++) out.push(`<text x="${GRID / 2 - 60}" y="${r * GRID + GRID / 2}" text-anchor="middle" dominant-baseline="middle">${rowName(r)}</text>`);
  out.push(`</g>`);

  // wires
  const lastEnd = {}, firstEnd = {}, portUse = {};
  for (const e of geom.edges) {
    const k = e.pts[0].join(",");
    portUse[k] = (portUse[k] || 0) + 1;
  }
  out.push(`<g class="wires">`);
  for (const e of geom.edges) {
    const w = wiresById[e.wire];
    const d = "M" + e.pts.map((p) => p.join(" ")).join("L");
    const cls = ["w", "k-" + (w.line || "signal"), "st-" + w.status, w.optional ? "opt" : "", w.colour === "OG" ? "hv" : "", (w.mm2 || 0) >= 6 ? "heavy" : ""].join(" ").trim();
    out.push(`<path class="${cls}" data-w="${w.id}" d="${d}"/>`);
    for (const j of e.junctions) out.push(`<circle class="jn" cx="${j[0]}" cy="${j[1]}" r="3.5"/>`);
    if (e.last) lastEnd[w.id] = e;
    if (e.first) firstEnd[w.id] = e;
  }
  out.push(`</g>`);
  // wire labels: next to the pin the wire lands on when there's room, else on the wire's
  // longest level run; and at the start too when that pin has only this wire
  out.push(`<g class="wlbl">`);
  const runs = {};
  for (const e of geom.edges) (runs[e.wire] = runs[e.wire] || []).push(e);
  for (const w of model.wires) {
    if (w.earth) continue;
    const text = wireText(w);
    const need = tw(text, 10.5) + 22;
    const e = lastEnd[w.id];
    let placed = false;
    if (e) {
      const n = e.pts.length;
      if (runLen(e.pts[n - 1], e.pts[n - 2]) >= need) { out.push(label(e.pts[n - 1], e.pts[n - 2], text, w)); placed = true; }
    }
    const s = firstEnd[w.id];
    if (s && (!placed || portUse[s.pts[0].join(",")] === 1 && dist(s.pts) > 260) && runLen(s.pts[0], s.pts[1]) >= need) {
      out.push(label(s.pts[0], s.pts[1], text, w));
      placed = true;
    }
    if (!placed) {
      let best = null;
      for (const r of runs[w.id] || []) {
        for (let i = 1; i < r.pts.length; i++) {
          const a = r.pts[i - 1], b = r.pts[i];
          if (Math.abs(a[1] - b[1]) < 0.5 && (!best || Math.abs(a[0] - b[0]) > best.len)) best = { a, b, len: Math.abs(a[0] - b[0]) };
        }
      }
      if (best) {
        const mid = [(best.a[0] + best.b[0]) / 2 - Math.min(need, best.len) / 2 + 4, best.a[1]];
        out.push(`<text class="wl" data-w="${w.id}" x="${mid[0]}" y="${mid[1] - 4}">${esc(text)} ${swatch(w)}</text>`);
      } else if (e) out.push(label(e.pts[e.pts.length - 1], e.pts[e.pts.length - 2], text, w));
    }
  }
  out.push(`</g>`);

  // in-line fuses, diodes, optos
  out.push(`<g class="inl">`);
  for (const n of geom.inlines) out.push(inlineSym(n, wiresById[n.wire]));
  out.push(`</g>`);

  // parts
  out.push(`<g class="parts">`);
  for (const [id, n] of Object.entries(geom.nodes)) out.push(partSym(model, geom, id, n));
  out.push(`</g></svg>`);
  return out.join("\n");
}

function dist(pts) {
  let d = 0;
  for (let i = 1; i < pts.length; i++) d += Math.abs(pts[i][0] - pts[i - 1][0]) + Math.abs(pts[i][1] - pts[i - 1][1]);
  return d;
}

export function wireText(w) {
  const bits = [w.id];
  if (w.mm2 != null) bits.push(`${w.mm2}mm²`);
  if (w.colour) bits.push(w.colour);
  return bits.join(" ");
}

const runLen = (p, q) => (q && Math.abs(p[1] - q[1]) < 0.5 ? Math.abs(p[0] - q[0]) : 0);
const swatch = (w) => {
  const c = String(w.colour || "").split("/")[0];
  return COLOURS[c] ? `<tspan class="sw" fill="${COLOURS[c]}">■</tspan>` : "";
};

function label(p, q, text, w) {
  // p is the pin end, q the next point along the wire. Text sits just above a level run.
  if (!q) return "";
  const horiz = Math.abs(p[1] - q[1]) < 0.5;
  const sw = swatch(w);
  if (horiz) {
    const leftward = q[0] < p[0];
    const x = leftward ? p[0] - 8 : p[0] + 8;
    return `<text class="wl" data-w="${w.id}" x="${x}" y="${p[1] - 4}" text-anchor="${leftward ? "end" : "start"}">${esc(text)} ${sw}</text>`;
  }
  return `<text class="wl" data-w="${w.id}" x="${p[0] + 5}" y="${p[1] + (q[1] > p[1] ? 14 : -6)}">${esc(text)} ${sw}</text>`;
}

function inlineSym(n, w) {
  const cy = n.y + n.h / 2, x0 = n.x, x1 = n.x + n.w;
  const g = [`<g class="isym" data-w="${w.id}">`];
  if (n.kind === "fuse") {
    g.push(`<line class="lead" x1="${x0}" y1="${cy}" x2="${x1}" y2="${cy}"/><rect class="sym" x="${x0 + 14}" y="${cy - 6}" width="${n.w - 28}" height="12"/>`);
    g.push(`<text class="sl" x="${(x0 + x1) / 2}" y="${cy - 10}" text-anchor="middle">F ${esc(n.text)}</text>`);
  } else if (n.kind === "diode") {
    const cx = (x0 + x1) / 2;
    g.push(`<line class="lead" x1="${x0}" y1="${cy}" x2="${x1}" y2="${cy}"/><path class="symf" d="M${cx - 7} ${cy - 8}L${cx + 7} ${cy}L${cx - 7} ${cy + 8}Z"/><line class="sym" x1="${cx + 7}" y1="${cy - 8}" x2="${cx + 7}" y2="${cy + 8}"/>`);
    g.push(`<text class="sl" x="${cx}" y="${cy + 21}" text-anchor="middle">${esc(diodeName(n.text))}</text>`);
  } else {
    g.push(`<line class="lead" x1="${x0}" y1="${cy}" x2="${x0 + 6}" y2="${cy}"/><line class="lead" x1="${x1 - 6}" y1="${cy}" x2="${x1}" y2="${cy}"/>`);
    g.push(`<rect class="sym" x="${x0 + 6}" y="${cy - 10}" width="${n.w - 12}" height="20" rx="2"/><text class="sl" x="${(x0 + x1) / 2}" y="${cy + 4}" text-anchor="middle">${esc(shortVia(n.text, 22))}</text>`);
  }
  g.push(`</g>`);
  return g.join("");
}
function diodeName(t) {
  t = String(t || "");
  const part = t.match(/1N\d{4}/i), amps = t.match(/(\d+(?:\.\d+)?)\s*A\b/);
  if (/flyback/i.test(t)) return "flyback";
  if (part) return part[0].toUpperCase();
  if (/schottky/i.test(t)) return `SB ${amps ? amps[1] + "A" : ""}`.trim();
  return shortVia(t, 12);
}
const shortVia = (s, n = 16) => { s = String(s || ""); return s.length > n ? s.slice(0, n - 1) + "…" : s; };

// ---- part symbols
function earthSym(x, y, label) {
  // a short lead down from (x, y), then the three bars of an earth (IEC 60617 02-15-01)
  return `<line class="lead" x1="${x}" y1="${y}" x2="${x}" y2="${y + 16}"/>` +
    `<line class="sym" x1="${x - 10}" y1="${y + 16}" x2="${x + 10}" y2="${y + 16}"/>` +
    `<line class="sym" x1="${x - 6}" y1="${y + 21}" x2="${x + 6}" y2="${y + 21}"/>` +
    `<line class="sym" x1="${x - 2}" y1="${y + 26}" x2="${x + 2}" y2="${y + 26}"/>` +
    (label ? `<text class="el" x="${x + 13}" y="${y + 12}">${esc(label)}</text>` : "");
}

function terminal(x, y) { return `<circle class="term" cx="${x}" cy="${y}" r="2.6"/>`; }

function partSym(model, geom, id, n) {
  const part = model.parts[id], dev = model.devices[part.dev], s = n.shape;
  const x = n.x, y = n.y;
  const st = dev.status, opt = dev.optional ? " opt" : "";
  const g = [`<g class="part k-${part.kind} st-${st}${opt}" data-p="${id}" data-d="${part.dev}" transform="translate(${x} ${y})">`];
  const earthWires = model.wires.filter((w) => w.earth && (w.earth === "to" ? w.from[0] : w.to[0]) === part.dev);
  const earthLbl = (pin) => earthWires.filter((w) => (w.earth === "to" ? w.from[1] : w.to[1]) === pin).map((w) => {
    const pt = w.earth === "to" ? w.to : w.from;
    return `${w.id}${w.mm2 ? " " + w.mm2 + "mm²" : ""} BK${pt[0] === "GND_STAR" ? "" : " to " + pt.join(".")}`;
  }).join(", ");

  if (part.kind === "battery") {
    const cx = 40, top = s.head + 10, bot = s.head + 70, mid = (top + bot) / 2;
    g.push(`<rect class="hit" width="${s.w}" height="${s.bodyH}"/>`);
    g.push(`<text class="tag" x="0" y="12">${esc(s.title)}</text><text class="nm" x="0" y="24">${esc(trunc(dev.name, 18))}</text>`);
    g.push(`<path class="lead" d="M${s.w} ${top}H${cx}V${mid - 6}M${cx} ${mid + 6}V${bot}${s.negEarth ? "" : "H" + s.w}"/>`);
    g.push(`<line class="sym thick" x1="${cx - 16}" y1="${mid - 6}" x2="${cx + 16}" y2="${mid - 6}"/><line class="sym thick2" x1="${cx - 8}" y1="${mid + 6}" x2="${cx + 8}" y2="${mid + 6}"/>`);
    g.push(`<text class="sl" x="${cx + 20}" y="${mid - 9}">+</text><text class="sl" x="${cx + 14}" y="${mid + 17}">−</text>`);
    g.push(`${terminal(s.w, top)}<text class="pin" x="${s.w - 4}" y="${top - 5}" text-anchor="end">${esc(s.pos)}</text>`);
    if (s.negEarth) g.push(earthSym(cx, bot, `${s.neg} ${earthLbl(s.neg)}`));
    else g.push(`${terminal(s.w, bot)}<text class="pin" x="${s.w - 4}" y="${bot - 5}" text-anchor="end">${esc(s.neg)}</text>`);
  } else if (ROW_KINDS.has(part.kind)) {
    g.push(`<rect class="hit" x="0" y="0" width="${s.w}" height="${s.bodyH}"/>`);
    g.push(`<text class="tag" x="${s.w / 2}" y="12" text-anchor="middle">${esc(s.title)}</text>`);
    g.push(`<text class="nm" x="${s.w / 2}" y="24" text-anchor="middle">${esc(trunc(dev.name, 28))}</text>`);
    const xL = s.mirror ? s.w : 0, dir = s.mirror ? -1 : 1;
    const busX = s.mirror ? 20 : s.w - 20;
    s.rowsIn.forEach(([a, b, glyph], i) => {
      const cy = s.head + i * s.RH + s.RH / 2;
      const cx = s.w / 2 - (s.common ? 10 * dir : 0);
      const xEnd = b ? (s.mirror ? 0 : s.w) : busX;
      g.push(`<line class="lead" x1="${xL}" y1="${cy}" x2="${cx - 16 * dir}" y2="${cy}"/>`);
      g.push(`<line class="lead" x1="${cx + 16 * dir}" y1="${cy}" x2="${xEnd}" y2="${cy}"/>`);
      g.push(glyphSym(glyph, cx, cy, part, a, b));
      g.push(`<text class="pin" x="${xL + 4 * dir}" y="${cy - 5}" text-anchor="${s.mirror ? "end" : "start"}">${esc(a)}</text>`);
      if (b) g.push(`<text class="pin" x="${(s.mirror ? 0 : s.w) - 4 * dir}" y="${cy - 5}" text-anchor="${s.mirror ? "start" : "end"}">${esc(b)}</text>`);
      g.push(terminal(xL, cy));
      if (b) g.push(terminal(s.mirror ? 0 : s.w, cy));
    });
    if (s.common) {
      const y0 = s.head + s.RH / 2, y1 = s.head + (s.rowsIn.length - 1) * s.RH + s.RH / 2;
      if (s.rowsIn.length > 1) g.push(`<line class="lead" x1="${busX}" y1="${y0}" x2="${busX}" y2="${y1}"/>`);
      for (let i = 0; i < s.rowsIn.length; i++) if (s.rowsIn.length > 1) g.push(`<circle class="jn" cx="${busX}" cy="${s.head + i * s.RH + s.RH / 2}" r="2.5"/>`);
      if (s.earthed) {
        g.push(`<line class="lead" x1="${busX}" y1="${y1}" x2="${busX}" y2="${s.bodyH}"/>`);
        g.push(earthSym(busX, s.bodyH, `${s.common} ${earthLbl(s.common)}`));
      } else {
        const p = s.ports.find((q) => q.pin === s.common);
        const xc = s.mirror ? 0 : s.w;
        g.push(`<line class="lead" x1="${busX}" y1="${p.y}" x2="${xc}" y2="${p.y}"/>${terminal(xc, p.y)}`);
        g.push(`<text class="pin" x="${xc - 4 * dir}" y="${p.y - 5}" text-anchor="${s.mirror ? "start" : "end"}">${esc(s.common)}</text>`);
        if (s.rowsIn.length === 1) g.push(`<line class="lead" x1="${busX}" y1="${y0}" x2="${busX}" y2="${p.y}"/>`);
      }
    }
    // a 2-pin symbol with its second pin earthed (lamp neg to earth etc)
    for (const e of part.ports.filter((p) => p.side === "S" && p.pin !== s.common)) {
      const row = s.rowsIn.findIndex((r) => r[1] === e.pin);
      const cy = s.head + Math.max(0, row) * s.RH + s.RH / 2, xe = s.mirror ? 0 : s.w;
      g.push(`<line class="lead" x1="${xe}" y1="${cy}" x2="${xe}" y2="${s.bodyH}"/>` + earthSym(xe, s.bodyH, `${e.pin} ${earthLbl(e.pin)}`));
    }
  } else if (part.kind === "bus") {
    g.push(`<rect class="hit" width="${s.w}" height="${s.bodyH}"/><text class="tag" x="${s.w / 2}" y="12" text-anchor="middle">${esc(s.title)}</text>`);
    g.push(`<rect class="busbar" x="${s.w / 2 - 4}" y="22" width="8" height="${s.bodyH - 30}"/>`);
    for (const p of s.ports) g.push(`<line class="lead" x1="${p.x}" y1="${p.y}" x2="${s.w / 2}" y2="${p.y}"/>${terminal(p.x, p.y)}`);
  } else if (part.kind === "star") {
    g.push(`<rect class="box" width="${s.w}" height="${s.bodyH}"/><text class="tag" x="10" y="16">${esc(s.title)}  earth star point</text>`);
    g.push(`<rect class="busbar" x="30" y="34" width="${s.w - 60}" height="6"/>`);
    for (const p of s.ports) g.push(`<line class="lead" x1="0" y1="${p.y}" x2="30" y2="${p.y}"/>${terminal(0, p.y)}`);
    s.refs.forEach((r, i) => {
      const yy = 58 + i * 16;
      const w = model.wires.find((q) => q.id === r.wire);
      const target = geom.nodes[r.part];
      const ref = target ? gridRef(target.x + 1, target.y + 1) : "";
      g.push(`<g class="xref" data-w="${r.wire}" data-goto="${r.part}"><text class="pin" x="16" y="${yy}">${esc(r.wire)}</text>` +
        `<text class="pin" x="58" y="${yy}">${esc(r.dev)}.${esc(r.pin)}</text><text class="pin dim" x="190" y="${yy}">${w && w.mm2 ? w.mm2 + "mm²" : ""}</text>` +
        `<text class="xr" x="${s.w - 12}" y="${yy}" text-anchor="end">→ ${ref}</text></g>`);
    });
  } else {
    g.push(boxPart(model, part, dev, s, earthLbl));
  }
  g.push(`</g>`);
  return g.join("");
}

const trunc = (s, n) => (String(s).length > n ? String(s).slice(0, n - 1) + "…" : String(s));

function boxPart(model, part, dev, s, earthLbl) {
  const g = [];
  g.push(`<rect class="box" width="${s.w}" height="${s.bodyH}"/>`);
  g.push(`<line class="hrule" x1="0" y1="${s.headH - 4}" x2="${s.w}" y2="${s.headH - 4}"/>`);
  g.push(`<text class="tag" x="8" y="16">${esc(s.title)}</text>`);
  s.nameLines.forEach((l, i) => g.push(`<text class="nm" x="8" y="${30 + i * 13}">${esc(l)}</text>`));
  g.push(boxGlyph(part.kind, s.w - 22, 16));
  s.rows.forEach(([pw, pe, deco], i) => {
    const cy = s.headH + i * P + P / 2;
    const pinW = pw ? pw.pin : null, pinE = pe ? pe.pin : null;
    if (pw) g.push(`${terminal(0, cy)}<text class="pin" x="7" y="${cy + 4}">${esc(pinW)}</text>`);
    if (pe) g.push(`${terminal(s.w, cy)}<text class="pin" x="${s.w - 7}" y="${cy + 4}" text-anchor="end">${esc(pinE)}</text>`);
    if (deco && deco.contact && deco.first) {
      // relay contact: COM on the left, NO on this row, NC on the next (blade drawn at rest, on NC)
      const xa = 7 + tw(pinW, 11) + 4, xb = s.w - 10 - tw(pinE || `NC${deco.contact}`, 11);
      const mid = (xa + xb) / 2;
      g.push(`<g class="contact" data-k="${part.dev}:${deco.contact}"><line class="lead" x1="${xa}" y1="${cy}" x2="${mid - 10}" y2="${cy}"/>`);
      if (deco.no) g.push(`<line class="lead" x1="${mid + 10}" y1="${cy}" x2="${xb}" y2="${cy}"/>`);
      if (deco.nc) g.push(`<line class="lead" x1="${mid + 10}" y1="${cy + P}" x2="${xb}" y2="${cy + P}"/><line class="lead" x1="${mid + 10}" y1="${cy + P}" x2="${mid + 10}" y2="${cy + P - 6}"/>`);
      g.push(`<line class="blade" x1="${mid - 10}" y1="${cy}" x2="${mid + 12}" y2="${cy + (deco.nc ? P - 6 : -9)}" data-no="${mid + 10} ${cy}" data-nc="${deco.nc ? `${mid + 12} ${cy + P - 6}` : `${mid + 12} ${cy - 9}`}"/>`);
      g.push(`<text class="kl" x="${mid}" y="${cy - 6}" text-anchor="middle">K${deco.contact}</text></g>`);
    }
    if (deco && deco.busTop) {
      const n = s.rows.length;
      g.push(`<line class="lead" x1="${pw ? 7 + tw("IN", 11) : 22}" y1="${cy}" x2="40" y2="${cy}"/>`);
      g.push(`<line class="busl" x1="40" y1="${cy}" x2="40" y2="${s.headH + (n - 1) * P + P / 2}"/>`);
      if (pe) g.push(`<line class="lead" x1="40" y1="${cy}" x2="${s.w - 7 - tw("IN", 11)}" y2="${cy}"/>`);
    }
    if (deco && deco.fuse) {
      const xr = s.w - 8 - tw(pinE || pinW, 11);
      g.push(`<line class="lead" x1="40" y1="${cy}" x2="${xr}" y2="${cy}"/><circle class="jn" cx="40" cy="${cy}" r="2.5"/>` +
        `<rect class="sym" data-f="${part.dev}.${deco.fuse}" x="${(40 + xr) / 2 - 15}" y="${cy - 5}" width="30" height="10"/>` +
        `<text class="sl" x="${(40 + xr) / 2 + 20}" y="${cy - 3}">${deco.amps != null ? deco.amps + "A" : ""}</text>`);
    }
  });
  for (const e of s.earths) {
    g.push(`<text class="pin" x="${e.x}" y="${s.bodyH - 5}" text-anchor="middle">${esc(e.pin)}</text>`);
    g.push(terminal(e.x, s.bodyH) + earthSym(e.x, s.bodyH, earthLbl(e.pin)));
  }
  return g.join("");
}

function boxGlyph(kind, cx, cy) {
  switch (kind) {
    case "machine": return `<circle class="sym" cx="${cx}" cy="${cy}" r="11"/><text class="gl" x="${cx}" y="${cy + 4.5}" text-anchor="middle">M</text>`;
    case "converter": return `<rect class="sym" x="${cx - 11}" y="${cy - 11}" width="22" height="22"/><line class="sym" x1="${cx - 11}" y1="${cy + 11}" x2="${cx + 11}" y2="${cy - 11}"/><text class="gs" x="${cx - 6}" y="${cy - 2}" text-anchor="middle">=</text><text class="gs" x="${cx + 5}" y="${cy + 9}" text-anchor="middle">=</text>`;
    case "connector": return `<path class="sym" d="M${cx - 10} ${cy - 8}h6v16h-6M${cx + 2} ${cy - 8}a8 8 0 0 1 0 16"/>`;
    case "camera": return `<rect class="sym" x="${cx - 11}" y="${cy - 7}" width="15" height="14"/><path class="sym" d="M${cx + 4} ${cy - 3}l7 -4v14l-7 -4"/>`;
    case "display": return `<rect class="sym" x="${cx - 11}" y="${cy - 8}" width="22" height="15"/><line class="sym" x1="${cx - 5}" y1="${cy + 10}" x2="${cx + 5}" y2="${cy + 10}"/>`;
    case "pot": return `<rect class="sym" x="${cx - 12}" y="${cy - 4}" width="24" height="8"/><path class="sym" d="M${cx - 6} ${cy + 10}L${cx + 8} ${cy - 10}M${cx + 3} ${cy - 10}h5v5"/>`;
    case "relays": return `<rect class="sym" x="${cx - 9}" y="${cy - 9}" width="18" height="18"/><line class="sym" x1="${cx - 9}" y1="${cy + 9}" x2="${cx + 9}" y2="${cy - 9}"/>`;
    case "fuseblock": return `<rect class="sym" x="${cx - 12}" y="${cy - 5}" width="24" height="10"/><line class="sym" x1="${cx - 16}" y1="${cy}" x2="${cx + 16}" y2="${cy}"/>`;
    case "controller": return `<rect class="sym" x="${cx - 11}" y="${cy - 9}" width="22" height="18"/><path class="sym" d="M${cx - 7} ${cy + 4}l4 -8l4 8l4 -8"/>`;
    default: return `<rect class="sym" x="${cx - 10}" y="${cy - 8}" width="20" height="16"/><path class="sym" d="M${cx - 6} ${cy - 8}v-3M${cx} ${cy - 8}v-3M${cx + 6} ${cy - 8}v-3M${cx - 6} ${cy + 8}v3M${cx} ${cy + 8}v3M${cx + 6} ${cy + 8}v3"/>`;
  }
}

// Symbols drawn on one row of a row-symbol part, centred on (cx, cy), 32 wide.
function glyphSym(kind, cx, cy, part, a, b) {
  const k = `data-k="${part.dev}:${a}"`;
  switch (kind) {
    case "lamp": return `<circle class="sym" cx="${cx}" cy="${cy}" r="11"/><path class="sym" d="M${cx - 7.8} ${cy - 7.8}L${cx + 7.8} ${cy + 7.8}M${cx - 7.8} ${cy + 7.8}L${cx + 7.8} ${cy - 7.8}"/><circle class="glow" cx="${cx}" cy="${cy}" r="11" ${k}/>`;
    case "motor": return `<circle class="sym" cx="${cx}" cy="${cy}" r="12"/><text class="gl" x="${cx}" y="${cy + 4.5}" text-anchor="middle">M</text>`;
    case "speaker": return `<rect class="sym" x="${cx - 12}" y="${cy - 6}" width="7" height="12"/><path class="sym" d="M${cx - 5} ${cy - 6}L${cx + 5} ${cy - 13}V${cy + 13}L${cx - 5} ${cy + 6}"/>`;
    case "fuse": return `<rect class="sym" x="${cx - 14}" y="${cy - 6}" width="28" height="12"/><line class="lead" x1="${cx - 16}" y1="${cy}" x2="${cx + 16}" y2="${cy}"/>`;
    case "breaker": return `<line class="lead" x1="${cx - 16}" y1="${cy}" x2="${cx - 8}" y2="${cy}"/><path class="sym" d="M${cx - 8} ${cy}L${cx + 10} ${cy - 10}"/><path class="sym" d="M${cx + 7} ${cy - 4}l6 6m0 -6l-6 6"/><line class="lead" x1="${cx + 10}" y1="${cy}" x2="${cx + 16}" y2="${cy}"/>`;
    case "diode": return `<line class="lead" x1="${cx - 16}" y1="${cy}" x2="${cx + 16}" y2="${cy}"/><path class="symf" d="M${cx - 7} ${cy - 8}L${cx + 7} ${cy}L${cx - 7} ${cy + 8}Z"/><path class="sym" d="M${cx + 4} ${cy - 10}l3 2v16l3 2"/>`;
    case "battery": return `<line class="lead" x1="${cx - 16}" y1="${cy}" x2="${cx - 3}" y2="${cy}"/><line class="sym thick" x1="${cx - 3}" y1="${cy - 12}" x2="${cx - 3}" y2="${cy + 12}"/><line class="sym thick2" x1="${cx + 4}" y1="${cy - 6}" x2="${cx + 4}" y2="${cy + 6}"/><line class="lead" x1="${cx + 4}" y1="${cy}" x2="${cx + 16}" y2="${cy}"/><text class="sl" x="${cx - 12}" y="${cy - 9}">+</text>`;
    case "contactor": return `<line class="lead" x1="${cx - 16}" y1="${cy}" x2="${cx - 8}" y2="${cy}"/><line class="blade" x1="${cx - 8}" y1="${cy}" x2="${cx + 9}" y2="${cy - 9}" ${k}/><path class="sym" d="M${cx + 9} ${cy}h7M${cx + 9} ${cy}v-4M${cx - 8} ${cy}m-2 -3a3 3 0 0 1 0 6"/>`;
    case "coil": return `<rect class="sym" x="${cx - 12}" y="${cy - 8}" width="24" height="16"/><line class="lead" x1="${cx - 16}" y1="${cy}" x2="${cx - 12}" y2="${cy}"/><line class="lead" x1="${cx + 12}" y1="${cy}" x2="${cx + 16}" y2="${cy}"/>`;
    case "isolator": return `<line class="lead" x1="${cx - 16}" y1="${cy}" x2="${cx - 8}" y2="${cy}"/><line class="blade" x1="${cx - 8}" y1="${cy}" x2="${cx + 9}" y2="${cy - 9}"/><path class="sym" d="M${cx + 9} ${cy}h7M${cx + 9} ${cy - 5}v10"/>`;
    case "estop": return `<line class="lead" x1="${cx - 16}" y1="${cy}" x2="${cx - 8}" y2="${cy}"/><line class="blade" x1="${cx - 8}" y1="${cy}" x2="${cx + 10}" y2="${cy + 3}"/><path class="sym" d="M${cx + 10} ${cy}h6M${cx + 10} ${cy}v5M${cx} ${cy + 1}v-12M${cx - 6} ${cy - 13}a6 4 0 0 1 12 0z"/>`;
    case "key": return `<line class="lead" x1="${cx - 16}" y1="${cy}" x2="${cx - 8}" y2="${cy}"/><line class="blade" x1="${cx - 8}" y1="${cy}" x2="${cx + 9}" y2="${cy - 9}"/><path class="sym" d="M${cx + 9} ${cy}h7M${cx + 9} ${cy}v-4"/><circle class="sym" cx="${cx - 3}" cy="${cy - 16}" r="3"/><path class="sym" d="M${cx} ${cy - 16}h7v3"/>`;
    case "limit": return `<line class="lead" x1="${cx - 16}" y1="${cy}" x2="${cx - 8}" y2="${cy}"/><line class="blade" x1="${cx - 8}" y1="${cy}" x2="${cx + 10}" y2="${cy + 3}"/><path class="sym" d="M${cx + 10} ${cy}h6M${cx + 10} ${cy}v5M${cx + 1} ${cy + 1}v-8l-5 -5h10z"/>`;
    default: return `<line class="lead" x1="${cx - 16}" y1="${cy}" x2="${cx - 8}" y2="${cy}"/><line class="blade" x1="${cx - 8}" y1="${cy}" x2="${cx + 9}" y2="${cy - 9}" ${k}/><path class="sym" d="M${cx + 9} ${cy}h7M${cx + 9} ${cy}v-4"/>`;
  }
}
