// Volume, always one tap away: the speaker button in the top bar opens a big
// glove-sized panel with - / + keys, a slider and mute. It shuts itself after a few seconds.
import { el, Slider } from "./controls.js";
import { icon } from "./icons.js";

export function volumeControl(ctx, button) {
  const hub = ctx.media;
  const pop = el(`
    <div class="vol-pop" hidden>
      <div class="vol-head"><span>Music volume</span><span class="vol-pct num"></span></div>
      <div class="vol-row">
        <button class="btn vol-dn" aria-label="Quieter">${icon("minus") || "−"}</button>
        <div class="vol-slider"></div>
        <button class="btn vol-up" aria-label="Louder">${icon("plus")}</button>
      </div>
      <button class="btn vol-mute"></button>
      <div class="vol-note muted small">Alerts always play at their own volume.</div>
    </div>`);
  document.getElementById("app").appendChild(pop);
  let before = 0.6, timer = null;
  const level = () => hub.mixer.level;
  const slider = new Slider({ min: 0, max: 100, step: 5, value: Math.round(level() * 100), label: "", fmt: (v) => `${v}%`, onChange: (v) => { set(v / 100, false); } });
  pop.querySelector(".vol-slider").appendChild(slider.root);

  const draw = () => {
    const v = Math.round(level() * 100);
    button.innerHTML = `${icon(v === 0 ? "volumeoff" : "volume")}<span class="num">${v}</span>`;
    button.classList.toggle("muted", v === 0);
    pop.querySelector(".vol-pct").textContent = `${v}%`;
    pop.querySelector(".vol-mute").textContent = v === 0 ? "Unmute" : "Mute";
    pop.querySelector(".vol-mute").classList.toggle("on", v === 0);
    if (!slider.dragging) slider.set ? slider.set(v) : null;
  };
  const keepOpen = () => { clearTimeout(timer); timer = setTimeout(close, 6000); };
  const set = (v, moveSlider = true) => {
    v = Math.max(0, Math.min(1, Math.round(v * 20) / 20));
    hub.setVolume(v);
    if (moveSlider && slider.set) slider.set(Math.round(v * 100));
    draw(); keepOpen();
  };
  const open = () => { pop.hidden = false; draw(); keepOpen(); };
  const close = () => { pop.hidden = true; clearTimeout(timer); };

  button.onclick = (e) => { e.stopPropagation(); pop.hidden ? open() : close(); };
  pop.querySelector(".vol-dn").onclick = () => set(level() - 0.1);
  pop.querySelector(".vol-up").onclick = () => set(level() + 0.1);
  pop.querySelector(".vol-mute").onclick = () => {
    if (level() > 0) { before = level(); set(0); } else set(before || 0.6);
  };
  pop.addEventListener("pointerdown", (e) => { e.stopPropagation(); keepOpen(); });
  document.addEventListener("pointerdown", (e) => { if (!pop.hidden && !button.contains(e.target)) close(); });
  hub.on && hub.on(draw);
  draw();
  return { open, close, draw };
}
