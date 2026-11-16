// Fits the 1280x800 layout to whatever screen it's on.
// The dash is drawn for a 1280x800 10.1" screen. If the real screen is a different size
// (1024x600, 1920x1200, a laptop on the bench), the whole dash is scaled to fit and centred,
// so nothing gets cut off or reflowed. Touch still lands in the right place.
export const DESIGN_W = 1280, DESIGN_H = 800;

export function fitToScreen(app = document.getElementById("app")) {
  const apply = () => {
    const w = window.innerWidth, h = window.innerHeight;
    const s = Math.min(w / DESIGN_W, h / DESIGN_H);
    window.__teryxScale = s;
    const x = Math.round((w - DESIGN_W * s) / 2), y = Math.round((h - DESIGN_H * s) / 2);
    app.style.transformOrigin = "0 0";
    app.style.transform = s === 1 && x === 0 && y === 0 ? "" : `translate(${x}px, ${y}px) scale(${s})`;
    document.documentElement.dataset.screen = `${w}x${h}`;
  };
  apply();
  window.addEventListener("resize", apply);
  return apply;
}
