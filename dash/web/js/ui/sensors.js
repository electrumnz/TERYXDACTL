// Tilt and GPS widget for the drive screen. Ready for sensors that aren't fitted yet:
// it reads pi.imu.* and pi.gps.* (see docs/DASH_API.md) and says "not fitted" until they show up.
// The simulator feeds fake ones so it can be tried on the bench.
import { el } from "./controls.js";

const DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
export const compassPoint = (deg) => DIRS[Math.round((((deg % 360) + 360) % 360) / 45) % 8];

function tiltClass(v, warn, bad) { const a = Math.abs(v); return a >= bad ? "bad" : a >= warn ? "warn" : ""; }

export function sensorWidget(settings) {
  const root = el(`
    <div class="sens">
      <div class="tilt-row">
        <div class="tilt" data-k="roll">
          <svg viewBox="-60 -50 120 100">
            <line class="horizon" x1="-58" y1="30" x2="58" y2="30"/>
            <g class="veh-g">
              <rect class="tb" x="-30" y="-22" width="60" height="34" rx="6"/>
              <rect class="tw" x="-38" y="6" width="14" height="22" rx="4"/><rect class="tw" x="24" y="6" width="14" height="22" rx="4"/>
              <path class="tc" d="M-20 -22 L-14 -40 L14 -40 L20 -22"/>
            </g>
          </svg>
          <div class="tilt-v num" id="sn-roll">--</div><div class="tilt-l">SIDE TO SIDE</div>
        </div>
        <div class="tilt" data-k="pitch">
          <svg viewBox="-60 -50 120 100">
            <line class="horizon" x1="-58" y1="30" x2="58" y2="30"/>
            <g class="veh-g">
              <path class="tb" d="M-44 6 L-40 -14 L-14 -16 L-6 -36 L22 -36 L30 -16 L44 -12 L44 6 Z"/>
              <circle class="tw" cx="-28" cy="14" r="13"/><circle class="tw" cx="30" cy="14" r="13"/>
            </g>
          </svg>
          <div class="tilt-v num" id="sn-pitch">--</div><div class="tilt-l">UP / DOWN</div>
        </div>
      </div>
      <div class="gps">
        <div class="compass"><svg viewBox="-30 -30 60 60"><circle r="27" class="ring"/><g class="needle"><path d="M0 -22 L6 0 L0 -4 L-6 0Z" class="n"/><path d="M0 22 L6 0 L0 4 L-6 0Z" class="s"/></g></svg></div>
        <div class="gps-txt">
          <div class="gps-head num" id="sn-head">--</div>
          <div class="gps-sub" id="sn-sub">No GPS fitted yet</div>
        </div>
      </div>
    </div>`);
  const q = (s) => root.querySelector(s);
  const rollG = root.querySelector('[data-k="roll"] .veh-g'), pitchG = root.querySelector('[data-k="pitch"] .veh-g');
  const needle = q(".needle");
  return {
    root,
    update(st) {
      const roll = st.get("pi.imu.roll"), pitch = st.get("pi.imu.pitch");
      const imu = roll != null || pitch != null;
      root.classList.toggle("no-imu", !imu);
      const rw = settings.get("tilt.rollWarn"), rb = settings.get("tilt.rollBad");
      const pw = settings.get("tilt.pitchWarn"), pb = settings.get("tilt.pitchBad");
      if (imu) {
        const r = roll ?? 0, p = pitch ?? 0;
        rollG.setAttribute("transform", `rotate(${Math.max(-45, Math.min(45, r))})`);
        pitchG.setAttribute("transform", `rotate(${Math.max(-45, Math.min(45, -p))})`);
        q("#sn-roll").textContent = `${Math.abs(r).toFixed(0)}°${Math.abs(r) >= 1 ? (r > 0 ? " R" : " L") : ""}`;
        q("#sn-roll").className = `tilt-v num ${tiltClass(r, rw, rb)}`;
        q("#sn-pitch").textContent = `${Math.abs(p).toFixed(0)}°${Math.abs(p) >= 1 ? (p > 0 ? " UP" : " DN") : ""}`;
        q("#sn-pitch").className = `tilt-v num ${tiltClass(p, pw, pb)}`;
        root.querySelector('[data-k="roll"]').className = `tilt ${tiltClass(r, rw, rb)}`;
        root.querySelector('[data-k="pitch"]').className = `tilt ${tiltClass(p, pw, pb)}`;
      } else {
        q("#sn-roll").textContent = "--"; q("#sn-pitch").textContent = "--";
        q("#sn-roll").className = q("#sn-pitch").className = "tilt-v num";
      }
      const fix = st.get("pi.gps.fix");
      root.classList.toggle("no-gps", st.get("pi.gps.fix") == null);
      if (fix) {
        const h = st.get("pi.gps.heading", 0);
        needle.setAttribute("transform", `rotate(${h})`);
        q("#sn-head").textContent = `${compassPoint(h)} ${Math.round(h)}°`;
        const alt = st.get("pi.gps.alt_m"), sats = st.get("pi.gps.sats");
        q("#sn-sub").textContent = `${alt != null ? `${Math.round(alt)} m up` : ""}${sats != null ? ` · ${sats} satellites` : ""}`;
      } else {
        needle.setAttribute("transform", "rotate(0)");
        q("#sn-head").textContent = "--";
        q("#sn-sub").textContent = fix === false ? "GPS looking for satellites…" : "No GPS fitted yet";
      }
    },
  };
}
