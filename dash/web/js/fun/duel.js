// Roar Duel: a two-player reaction game for the campsite. Each player has a half of the screen.
// The T. rex sleeps... then ROARS. First to slap their side after the roar wins the round.
// Slap too early, or on a fake-out snarl, and the point goes to the other side. First to 5.
// Solo: tap after the roar, see your reaction time.
// Original game for Teryx OS.
import { el } from "../ui/controls.js";
import { Sound } from "../sound.js";
import { roarSound } from "./eggs.js";

export const WIN = 5;

/** Decide a round's script: wait time (ms) and whether a fake-out snarl comes first. */
export function roundPlan(rand = Math.random) {
  const fake = rand() < 0.35;
  return { fake, fakeAt: fake ? 1200 + rand() * 1500 : null, roarAt: 2000 + rand() * 4000 + (fake ? 1500 : 0) };
}

export class RoarDuel {
  constructor({ bestMs = 0, onBest } = {}) {
    this.bestMs = bestMs; this.onBest = onBest;
    this.root = el(`<div class="game duel">
      <button class="du-side du-a" data-p="0"><b class="du-score">0</b><span class="du-name">Driver</span></button>
      <div class="du-mid">
        <div class="du-head" data-s="sleep">
          <img class="dh-closed" src="img/dino/head-closed.webp" alt="">
          <img class="dh-snarl" src="img/dino/head-snarl.webp" alt="">
          <img class="dh-roar" src="img/dino/head-roar.webp" alt="">
        </div>
        <div class="du-msg" id="du-msg">Roar Duel</div>
        <div class="du-btns">
          <button class="btn sm" id="du-two">2 players</button>
          <button class="btn sm" id="du-one">Solo</button>
        </div>
      </div>
      <button class="du-side du-b" data-p="1"><b class="du-score">0</b><span class="du-name">Passenger</span></button>
    </div>`);
    this.q = (s) => this.root.querySelector(s);
    this.head = this.q(".du-head");
    this.timers = [];
    this.q("#du-two").onclick = () => this.start(2);
    this.q("#du-one").onclick = () => this.start(1);
    this.root.querySelectorAll(".du-side").forEach((b) => b.addEventListener("pointerdown", (e) => { e.preventDefault(); this.slap(+b.dataset.p); }));
    this.state = "idle";
    this.msg(`Two players: driver slaps left, passenger slaps right. Wait for the ROAR. A snarl is a trick.`);
  }

  msg(t) { this.q("#du-msg").textContent = t; }
  face(s) { this.head.dataset.s = s; }
  later(fn, ms) { this.timers.push(setTimeout(fn, ms)); }
  clear() { this.timers.forEach(clearTimeout); this.timers = []; }

  start(players) {
    this.clear();
    this.players = players; this.score = [0, 0];
    this.root.classList.toggle("solo", players === 1);
    this.root.querySelectorAll(".du-score").forEach((s) => (s.textContent = "0"));
    this.q(".du-a .du-name").textContent = players === 1 ? "Tap here" : "Driver";
    this.round();
  }

  round() {
    this.clear();
    this.state = "wait"; this.face("sleep");
    this.msg("Shhh... it's sleeping.");
    const p = roundPlan();
    if (p.fake) this.later(() => { if (this.state === "wait") { this.face("snarl"); this.msg("Snarl! Don't touch..."); Sound.play("reject"); this.later(() => { if (this.state === "wait") { this.face("sleep"); this.msg("Shhh..."); } }, 900); } }, p.fakeAt);
    this.later(() => { this.state = "go"; this.face("roar"); this.msg("ROAR!"); this.t0 = performance.now(); roarSound(0.7); }, p.roarAt);
  }

  slap(p) {
    if (this.players === 1 && p === 1) p = 0;
    if (this.state === "wait") {
      // Too keen: the point goes the other way (solo: just a telling-off)
      this.clear(); this.state = "pause";
      if (this.players === 2) { this.point(1 - p, `${this.name(p)} jumped the gun. Point to ${this.name(1 - p)}.`); }
      else { this.msg("Too early! Wait for the roar."); Sound.play("reject"); this.later(() => this.round(), 1800); }
      return;
    }
    if (this.state !== "go") return;
    this.clear(); this.state = "pause";
    const ms = Math.round(performance.now() - this.t0);
    if (this.players === 1) {
      const best = !this.bestMs || ms < this.bestMs;
      if (best) { this.bestMs = ms; this.onBest && this.onBest(ms); }
      this.msg(`${ms} ms${best ? ". New best!" : `. Best ${this.bestMs} ms.`}`);
      Sound.play(best ? "done" : "info");
      this.later(() => this.round(), 2200);
      return;
    }
    this.point(p, `${this.name(p)} was quicker (${ms} ms).`);
  }

  name(p) { return p === 0 ? "Driver" : "Passenger"; }

  point(p, text) {
    this.score[p]++;
    this.root.querySelector(p === 0 ? ".du-a .du-score" : ".du-b .du-score").textContent = this.score[p];
    this.face("sleep");
    if (this.score[p] >= WIN) {
      this.state = "idle";
      this.msg(`${this.name(p)} wins ${this.score[p]} to ${this.score[1 - p]}! Top predator.`);
      Sound.play("done");
      return;
    }
    this.msg(text); Sound.play("shifted");
    this.later(() => this.round(), 1800);
  }

  stop() { this.clear(); this.state = "idle"; this.face("sleep"); }
}
