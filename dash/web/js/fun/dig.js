// Fossil Dig: a one-player puzzle. A T. rex skeleton is buried somewhere in the dig site.
// Each tap brushes away one square. Dirt squares glow hotter the closer they are to a bone
// you haven't found yet. Find every bone before your brushes run out.
// Original game for Teryx OS.
import { el } from "../ui/controls.js";
import { Sound } from "../sound.js";

export const COLS = 10, ROWS = 6;

/** Lay a skeleton: a wiggly chain of bones (a spine) with a skull at one end. Seeded so tests can repeat it. */
export function layBones(rand = Math.random, count = 9) {
  for (let tries = 0; tries < 200; tries++) {
    const cells = [];
    let c = 1 + Math.floor(rand() * (COLS - 2)), r = 1 + Math.floor(rand() * (ROWS - 2));
    cells.push([c, r]);
    let dir = rand() < 0.5 ? [1, 0] : [-1, 0];
    while (cells.length < count) {
      if (rand() < 0.3) dir = [[1, 0], [-1, 0], [0, 1], [0, -1]][Math.floor(rand() * 4)];
      const nc = c + dir[0], nr = r + dir[1];
      if (nc < 0 || nr < 0 || nc >= COLS || nr >= ROWS || cells.some(([x, y]) => x === nc && y === nr)) {
        dir = [[1, 0], [-1, 0], [0, 1], [0, -1]][Math.floor(rand() * 4)];
        if (cells.length > 1 && rand() < 0.05) break;
        continue;
      }
      c = nc; r = nr; cells.push([c, r]);
    }
    if (cells.length === count) return cells;
  }
  return [[0, 0], [1, 0], [2, 0], [3, 0], [4, 0], [5, 0], [6, 0], [7, 0], [8, 0]].slice(0, count);
}

/** Squares to the nearest bone not yet found (Manhattan distance). */
export function heat(bones, foundSet, c, r) {
  let best = 99;
  for (const [x, y] of bones) if (!foundSet.has(`${x},${y}`)) best = Math.min(best, Math.abs(x - c) + Math.abs(y - r));
  return best;
}

export class FossilDig {
  constructor({ best = 0, onBest } = {}) {
    this.best = best; this.onBest = onBest;
    this.root = el(`<div class="game dig">
      <div class="g-side">
        <div class="g-how">Tap to brush a square. Dirt glows <b class="hot">hot</b> near a bone, <b class="cold">cold</b> far away. Dig up the whole T. rex before your brushes run out.</div>
        <div class="g-stat"><span>Brushes</span><b id="dg-left">0</b></div>
        <div class="g-stat"><span>Bones</span><b id="dg-bones">0</b></div>
        <div class="g-stat"><span>Best</span><b id="dg-best">-</b></div>
        <button class="btn" id="dg-new">New dig</button>
      </div>
      <div class="dig-grid" id="dg-grid"></div>
      <div class="g-msg" id="dg-msg" hidden></div>
    </div>`);
    this.q = (s) => this.root.querySelector(s);
    this.q("#dg-new").onclick = () => this.reset();
    this.reset();
  }

  reset(rand = Math.random) {
    this.bones = layBones(rand);
    this.found = new Set();
    this.dug = new Set();
    this.left = 24;
    this.over = false;
    const g = this.q("#dg-grid"); g.innerHTML = "";
    this.cells = [];
    for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) {
      const b = el(`<button class="dig-cell" data-c="${c}" data-r="${r}" aria-label="Dig square ${c + 1}, ${r + 1}"></button>`);
      b.onclick = () => this.dig(c, r);
      g.appendChild(b); this.cells.push(b);
    }
    this.q("#dg-msg").hidden = true;
    this.paint();
  }

  isBone(c, r) { return this.bones.some(([x, y]) => x === c && y === r); }

  dig(c, r) {
    const k = `${c},${r}`;
    if (this.over || this.dug.has(k)) return;
    this.dug.add(k); this.left--;
    const cell = this.cells[r * COLS + c];
    if (this.isBone(c, r)) {
      this.found.add(k);
      const i = this.bones.findIndex(([x, y]) => x === c && y === r);
      cell.className = `dig-cell bone ${i === 0 ? "skull" : ""}`;
      Sound.play("shifted");
    } else cell.className = "dig-cell dirt";
    // Re-colour every dug dirt square: the heat changes as bones are found
    this.dug.forEach((key) => {
      if (this.found.has(key)) return;
      const [x, y] = key.split(",").map(Number), h = heat(this.bones, this.found, x, y);
      this.cells[y * COLS + x].dataset.h = h >= 4 ? 4 : h;
    });
    if (this.found.size === this.bones.length) this.finish(true);
    else if (this.left <= 0) this.finish(false);
    this.paint();
  }

  finish(win) {
    this.over = true;
    // Show where the rest were
    this.bones.forEach(([x, y]) => { const k = `${x},${y}`; if (!this.found.has(k)) this.cells[y * COLS + x].classList.add("missed"); });
    const m = this.q("#dg-msg");
    if (win) {
      const score = this.left;
      const isBest = score > (this.best || -1);
      if (isBest) { this.best = score; this.onBest && this.onBest(score); }
      m.textContent = `Full skeleton! ${score} brush${score === 1 ? "" : "es"} to spare${isBest ? ". New best." : "."}`;
      Sound.play("done");
    } else {
      m.textContent = `Out of brushes. ${this.found.size} of ${this.bones.length} bones found.`;
      Sound.play("warn");
    }
    m.hidden = false;
  }

  paint() {
    this.q("#dg-left").textContent = this.left;
    this.q("#dg-bones").textContent = `${this.found.size} / ${this.bones.length}`;
    this.q("#dg-best").textContent = this.best ? `${this.best} spare` : "-";
  }

  stop() {}
}
