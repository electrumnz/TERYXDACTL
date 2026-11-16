// Trips: this trip, trip A (reset it yourself), range left, and a history of past trips.
import { el, $, toast } from "../ui/controls.js";
import { icon } from "../ui/icons.js";
import { fmtKm, fmtKwh, fmtWhKm, fmtDur } from "../tripdata.js";

const BASIS = {
  recent: "Based on the last 10 km you've driven.",
  average: "Based on your average so far. Gets better as you drive.",
  guess: "A first guess until you've driven a couple of km.",
};

export class TripsScreen {
  constructor(ctx) { this.ctx = ctx; this.id = "trips"; this.label = "Trips"; this.icon = "trips"; }

  mount(root) {
    root.innerHTML = `
      <div class="trips">
        <div class="col">
          <div class="panel trip-card" id="tr-cur"><h3>This trip</h3><div class="trip-grid"></div></div>
          <div class="panel trip-card" id="tr-a">
            <div class="row" style="justify-content:space-between;align-items:center"><h3 style="margin:0">Trip A</h3>
              <button class="btn sm" id="tr-reset">${icon("reset")}<span>Reset</span></button></div>
            <div class="muted small" id="tr-a-since"></div>
            <div class="trip-grid"></div>
          </div>
        </div>
        <div class="col">
          <div class="panel range-card">
            <h3>Range left</h3>
            <div class="range-big"><span class="big-val num" id="tr-range">--</span><span class="unit" id="tr-range-u">km</span></div>
            <div class="kv"><span class="k">Energy left</span><span class="v num" id="tr-left">--</span></div>
            <div class="kv"><span class="k">Using</span><span class="v num" id="tr-whk">--</span></div>
            <div class="muted small" id="tr-basis"></div>
          </div>
          <div class="panel grow hist">
            <div class="row" style="justify-content:space-between;align-items:center"><h3 style="margin:0">Past trips</h3></div>
            <div class="hist-list" id="tr-hist"></div>
          </div>
        </div>
      </div>`;
    this.root = root;
    const reset = $(root, "#tr-reset");
    reset.onclick = async () => {
      // Two taps, so a bump can't wipe it.
      if (!this._armed) {
        this._armed = true; reset.classList.add("danger"); reset.querySelector("span").textContent = "Tap again";
        clearTimeout(this._t); this._t = setTimeout(() => { this._armed = false; reset.classList.remove("danger"); reset.querySelector("span").textContent = "Reset"; }, 3000);
        return;
      }
      this._armed = false; clearTimeout(this._t); reset.classList.remove("danger"); reset.querySelector("span").textContent = "Reset";
      try { await this.ctx.trips.reset("trip-a"); toast("Trip A reset.", "good"); } catch (e) { toast(`Couldn't reset (${e.message}).`, "bad"); }
    };
    this.ctx.trips.on(() => { if (this.ctx.current === this) this.render(); });
  }

  show() { this.ctx.trips.refresh(); }

  grid(t, mph) {
    if (!t) return `<div class="muted">Not started yet. A trip starts when the key goes on.</div>`;
    const socUsed = t.soc_start != null && t.soc_end != null ? Math.max(0, t.soc_start - t.soc_end) : null;
    const cell = (k, v, cls = "") => `<div class="tg"><div class="k">${k}</div><div class="v num ${cls}">${v}</div></div>`;
    return [
      cell("Distance", fmtKm(t.km, mph), "lg"),
      cell("Energy used", fmtKwh(t.net_wh), "lg"),
      cell("Average use", fmtWhKm(t.wh_per_km, mph)),
      cell("Put back (regen)", fmtKwh(t.regen_wh), "ok"),
      cell("Moving time", fmtDur(t.moving_s)),
      cell("Average speed", t.avg_kmh == null ? "--" : `${Math.round(mph ? t.avg_kmh * 0.621371 : t.avg_kmh)} ${mph ? "mph" : "km/h"}`),
      cell("Top speed", `${Math.round(mph ? t.max_kmh * 0.621371 : t.max_kmh)} ${mph ? "mph" : "km/h"}`),
      socUsed == null ? "" : cell("Battery used", `${Math.round(socUsed)}%`),
    ].join("");
  }

  render() {
    const d = this.ctx.trips.data, r = this.root; if (!d || !r) return;
    const mph = this.ctx.settings.get("units") === "mph";
    const set = (sel, html) => { const e = $(r, sel); if (e._h !== html) { e.innerHTML = html; e._h = html; } };
    set("#tr-cur .trip-grid", this.grid(d.current, mph));
    set("#tr-a .trip-grid", this.grid(d.trip_a, mph));
    $(r, "#tr-a-since").textContent = d.trip_a ? `Since ${new Date(d.trip_a.start * 1000).toLocaleString("en-NZ", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: false })}` : "";
    const rng = d.range_km == null ? null : mph ? d.range_km * 0.621371 : d.range_km;
    $(r, "#tr-range").textContent = rng == null ? "--" : Math.round(rng);
    $(r, "#tr-range-u").textContent = mph ? "mi" : "km";
    $(r, "#tr-range").className = `big-val num ${rng != null && d.range_km < 5 ? "bad" : rng != null && d.range_km < 15 ? "warn" : ""}`;
    $(r, "#tr-left").textContent = d.kwh_left == null ? "--" : `${d.kwh_left.toFixed(1)} of ${d.pack_kwh} kWh`;
    $(r, "#tr-whk").textContent = fmtWhKm(d.wh_per_km, mph);
    $(r, "#tr-basis").textContent = `${BASIS[d.basis] || ""} Pack size is set in Settings > Display.`;

    const hist = d.history || [];
    const maxKm = Math.max(1, ...hist.map((t) => t.km));
    set("#tr-hist", d.local ? `<div class="muted" style="padding:12px 0">Past trips are kept on the Pi. Not available in demo mode.</div>`
      : !hist.length ? `<div class="muted" style="padding:12px 0">No trips logged yet.</div>`
      : hist.slice(0, 30).map((t) => {
        const when = new Date(t.start * 1000);
        return `<div class="hist-row">
          <div class="hist-when"><b>${when.toLocaleDateString("en-NZ", { weekday: "short", day: "numeric", month: "short" })}</b><span>${when.toLocaleTimeString("en-NZ", { hour: "2-digit", minute: "2-digit", hour12: false })}</span></div>
          <div class="hist-bar"><div style="width:${(t.km / maxKm) * 100}%"></div></div>
          <div class="hist-v num">${fmtKm(t.km, mph)}</div>
          <div class="hist-v num muted">${fmtWhKm(t.wh_per_km, mph)}</div>
        </div>`;
      }).join(""));
  }

  update() { if (this.ctx.trips.data && !this._drawn) { this._drawn = true; this.render(); } }
}
