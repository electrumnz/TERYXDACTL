#!/usr/bin/env node
// Lays out docs/wiring/schematic.json with the same code as the page and checks the result.
//
//   node tools/wiring_sld_check.mjs                 check only (CI, via tests/test_wiring_sld.py)
//   node tools/wiring_sld_check.mjs out.svg         also write the whole drawing as one SVG file
//   node tools/wiring_sld_check.mjs --geom f.json   also save the layout (the site build ships it
//                                                    as wiring/layout.json so phones don't wait)
//
// Checks: the one canvas lays out, every wire is drawn, every device is drawn once, and no
// two parts overlap.
import { createRequire } from "node:module";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const dir = join(here, "..", "docs", "wiring");
const require = createRequire(import.meta.url);
const ELK = require(join(dir, "vendor", "elk.bundled.js"));
const { layout, draw, SVG_STYLE, packGeom } = await import(pathToFileURL(join(dir, "sld.js")).href);

const model = JSON.parse(readFileSync(join(dir, "schematic.json"), "utf8"));
const t0 = Date.now();
const geom = await layout(model, new ELK());
const ms = Date.now() - t0;
const problems = [];

const drawn = new Set(geom.edges.map((e) => e.wire));
for (const w of model.wires) if (!w.earth && !drawn.has(w.id)) problems.push(`wire ${w.id} isn't drawn`);
for (const id of Object.keys(model.parts)) if (!geom.nodes[id]) problems.push(`part ${id} isn't placed`);

const boxes = Object.entries(geom.nodes).map(([id, n]) => ({ id, x: n.x, y: n.y, w: n.shape.w, h: n.shape.h }));
for (let i = 0; i < boxes.length; i++) {
  for (let j = i + 1; j < boxes.length; j++) {
    const a = boxes[i], b = boxes[j];
    if (a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h) problems.push(`${a.id} overlaps ${b.id}`);
  }
}
const ids = Object.keys(model.parts);
if (ids.length !== new Set(ids.map((i) => model.parts[i].dev)).size) problems.push("a device is drawn more than once");

const args = process.argv.slice(2);
const gi = args.indexOf("--geom");
if (gi >= 0) { writeFileSync(args[gi + 1], JSON.stringify(packGeom(model, geom))); args.splice(gi, 2); }
const out = args[0];
if (out) writeFileSync(out, draw(model, geom, { style: SVG_STYLE }));
console.log(`laid out one canvas: ${Object.keys(geom.nodes).length} parts, ${geom.edges.length} wire runs in ${ms} ms; drawing ${geom.width} x ${geom.height}`);
for (const p of problems) console.log("problem:", p);
process.exit(problems.length ? 1 : 0);
