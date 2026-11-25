#!/usr/bin/env node
// Lays out docs/wiring/schematic.json with the same code as the page and checks the result.
//
//   node tools/wiring_sld_check.mjs                 check only (CI, via tests/test_wiring_sld.py)
//   node tools/wiring_sld_check.mjs out.svg         also write the whole drawing as one SVG file
//
// Checks: every section lays out, every wire is drawn, no two parts overlap, and every
// part sits inside its section frame.
import { createRequire } from "node:module";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const dir = join(here, "..", "docs", "wiring");
const require = createRequire(import.meta.url);
const ELK = require(join(dir, "vendor", "elk.bundled.js"));
const { layout, draw, SVG_STYLE } = await import(pathToFileURL(join(dir, "sld.js")).href);

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
for (const b of boxes) {
  const f = geom.frames.find((fr) => fr.key === model.parts[b.id].sec);
  if (b.x < f.x || b.y < f.y || b.x + b.w > f.x + f.w || b.y + b.h > f.y + f.h) problems.push(`${b.id} sticks out of section ${f.key}`);
}

const out = process.argv[2];
if (out) writeFileSync(out, draw(model, geom, { style: SVG_STYLE }));
console.log(`laid out ${model.sections.length} sections, ${Object.keys(geom.nodes).length} parts, ${geom.edges.length} wire runs in ${ms} ms; drawing ${geom.width} x ${geom.height}`);
for (const p of problems) console.log("problem:", p);
process.exit(problems.length ? 1 : 0);
