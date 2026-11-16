// Top-down Teryx drawing that shows drive mode, diff lock and lights at a glance.
import { el } from "./controls.js";

export function vehicleDiagram() {
  const root = el(`<div class="veh"><svg viewBox="0 0 200 300">
    <g class="beams">
      <path class="beam" data-i="1" d="M52 46 L20 0 L66 0 Z"/>
      <path class="beam" data-i="2" d="M82 46 L64 0 L100 0 Z"/>
      <path class="beam" data-i="3" d="M118 46 L100 0 L136 0 Z"/>
      <path class="beam" data-i="4" d="M148 46 L134 0 L180 0 Z"/>
    </g>
    <rect class="lamp" data-i="1" x="40" y="44" width="26" height="8" rx="3"/>
    <rect class="lamp" data-i="2" x="70" y="44" width="26" height="8" rx="3"/>
    <rect class="lamp" data-i="3" x="104" y="44" width="26" height="8" rx="3"/>
    <rect class="lamp" data-i="4" x="134" y="44" width="26" height="8" rx="3"/>
    <rect class="body" x="46" y="58" width="108" height="210" rx="22"/>
    <rect class="lamp cabin" x="72" y="128" width="56" height="7" rx="3"/>
    <line class="axle front" x1="30" y1="96" x2="170" y2="96"/>
    <line class="axle rear" x1="30" y1="226" x2="170" y2="226"/>
    <line class="axle shaft" x1="100" y1="110" x2="100" y2="226" stroke-dasharray="6 6"/>
    <circle class="diff" cx="100" cy="96" r="14"/>
    <text class="diff-txt" x="100" y="101" text-anchor="middle" font-size="13" font-weight="800" fill="currentColor"></text>
    <rect class="wheel fl" x="14" y="72" width="26" height="48" rx="7"/>
    <rect class="wheel fr" x="160" y="72" width="26" height="48" rx="7"/>
    <rect class="wheel rl" x="14" y="202" width="26" height="48" rx="7"/>
    <rect class="wheel rr" x="160" y="202" width="26" height="48" rx="7"/>
    <rect class="lamp rearlamp" x="54" y="266" width="22" height="8" rx="3"/>
    <rect class="lamp rearlamp" x="124" y="266" width="22" height="8" rx="3"/>
    <rect class="lamp taillamp" x="42" y="252" width="12" height="14" rx="3"/>
    <rect class="lamp taillamp" x="146" y="252" width="12" height="14" rx="3"/>
  </svg></div>`);
  const q = (s) => root.querySelector(s);
  const qa = (s) => [...root.querySelectorAll(s)];
  return {
    root,
    update(st) {
      const four = st.get("act.4wd") === "4wd";
      qa(".wheel.rl, .wheel.rr, .axle.rear, .axle.shaft").forEach((e) => e.classList.add("pwr"));
      qa(".wheel.fl, .wheel.fr, .axle.front").forEach((e) => e.classList.toggle("pwr", four));
      q(".axle.shaft").classList.toggle("pwr", four);
      const d = Math.round(st.get("an.diff_pos", 0));
      q(".diff").classList.toggle("locked", d > 2);
      q(".diff-txt").textContent = d > 2 ? `${d}` : "";
      for (let i = 1; i <= 4; i++) {
        const v = st.get(`light.front_${i}`, 0);
        q(`.lamp[data-i="${i}"]`).classList.toggle("on", v > 0);
        q(`.beam[data-i="${i}"]`).style.opacity = (v / 255) * 0.35;
      }
      q(".lamp.cabin").classList.toggle("on", st.get("light.interior", 0) > 0);
      qa(".rearlamp").forEach((e) => e.classList.toggle("on", !!st.get("light.rear")));
      const brake = !!(st.get("in.brake") || st.get("mc.brake"));
      qa(".taillamp").forEach((e) => { e.classList.toggle("brake", brake); e.classList.toggle("on", !brake && !!st.get("trailer.tail")); });
    },
  };
}
