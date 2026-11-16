// Drive demo player: a small floating bar that shows up when the simulator is playing the
// scripted drive (scenario "drive_demo"). Says what's happening, how far through it is, and
// has big restart / play-pause / skip buttons. Only on the bench: on the real Teryx there is
// no simulator, so no sim.demo key, so this never shows.
import { el } from "./controls.js";
import { icon } from "./icons.js";

async function sim(cmd) {
  try {
    await fetch("/api/sim", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(cmd) });
  } catch {}
}

export function demoPlayer() {
  const root = el(`<div class="demo-player" id="demo-player" hidden>
      <div class="dp-text">
        <div class="dp-head"><span class="dp-tag">DRIVE DEMO</span><span class="dp-step num" id="dp-step"></span></div>
        <div class="dp-caption" id="dp-caption"></div>
        <div class="dp-bar"><div id="dp-fill"></div></div>
      </div>
      <button class="dp-btn" id="dp-restart" aria-label="Start the drive demo again">${icon("reset")}</button>
      <button class="dp-btn main" id="dp-play" aria-label="Pause or play the drive demo"></button>
      <button class="dp-btn" id="dp-next" aria-label="Skip to the next step">${icon("next")}</button>
    </div>`);
  const q = (s) => root.querySelector(s);
  let info = null;
  q("#dp-restart").onclick = () => sim({ restart: true });
  q("#dp-play").onclick = () => info && sim({ paused: !info.paused });
  q("#dp-next").onclick = () => info && sim({ demo_step: info.step + 1 });
  let lastPlay = null;
  return {
    root,
    update(st) {
      info = st.get("sim.demo");
      const on = !!info && st.get("sim.scenario") === "drive_demo";
      root.hidden = !on;
      if (!on) return;
      q("#dp-step").textContent = `${info.step + 1}/${info.steps}`;
      const cap = info.paused ? `Paused: ${info.caption}` : info.caption;
      if (q("#dp-caption").textContent !== cap) q("#dp-caption").textContent = cap;
      q("#dp-fill").style.width = `${Math.min(100, (info.t / info.length) * 100)}%`;
      if (lastPlay !== info.paused) { q("#dp-play").innerHTML = icon(info.paused ? "play" : "pause"); lastPlay = info.paused; }
      root.classList.toggle("paused", !!info.paused);
    },
  };
}
