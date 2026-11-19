// Look buttons for the online demo only: Auto, Predator, Fossil and Night Hunt, sitting in the
// spare space beside (or above/below) the scaled 1280x800 dash, outside the screen itself.
// On the Teryx (no demo) they never show; the look there is set in Settings > Display.
import { LOOKS } from "../look.js";
import { DESIGN_W, DESIGN_H } from "../fit.js";

const CHOICES = [["auto", "Auto"], ...Object.entries(LOOKS)];

export function lookRail(ctx) {
  const rail = document.createElement("div");
  rail.id = "look-rail";
  rail.hidden = true;
  rail.innerHTML = `<div class="lr-lbl">LOOK</div>` +
    CHOICES.map(([k, name]) => `<button type="button" data-look="${k}">${name}</button>`).join("");
  document.body.appendChild(rail);   // outside #app, so it isn't scaled with the dash

  const mark = () => {
    const now = ctx.settings.get("look") || "auto";
    rail.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b.dataset.look === now));
  };
  rail.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    ctx.settings.set("look", b.dataset.look);
    ctx.applyTheme();
    mark();
  });

  // Put it in whichever margin is bigger: left side on a wide phone or laptop, under the dash on a tall one.
  const place = () => {
    const w = innerWidth, h = innerHeight, s = Math.min(w / DESIGN_W, h / DESIGN_H);
    const side = (w - DESIGN_W * s) / 2, below = (h - DESIGN_H * s) / 2;
    rail.classList.toggle("lr-row", below > side);
    rail.classList.toggle("lr-tight", Math.max(side, below) < 64);
    if (below > side) rail.style.cssText = `left:0;right:0;bottom:0;height:${Math.max(below, 44)}px;width:auto;top:auto`;
    else rail.style.cssText = `left:0;top:0;bottom:0;width:${Math.max(side, 64)}px;height:auto;right:auto`;
  };
  addEventListener("resize", place);
  place();

  return {
    update(st) {
      const on = !!st.get("link.demo");
      if (rail.hidden === on) { rail.hidden = !on; mark(); }
    },
  };
}
