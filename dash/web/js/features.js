// Features that aren't wired up on the Teryx yet show greyed out with a SOON tag.
// Tapping one says so instead of opening it. Switch each on in Settings > Features once
// the hardware is fitted (saved in settings.features.<id>).
//
// To grey out any other control:  soon(element, true)  (or add class "soon" in the markup).

export const FEATURES = [
  { id: "trips", name: "Trips", desc: "Trip log and range." },
  { id: "drivetrain", name: "4WD and diff lock", desc: "Needs the 4WD and diff actuators wired to the control box." },
  { id: "lights", name: "Lights", desc: "Needs the light bars wired to the control box." },
  { id: "winch", name: "Winch", desc: "Needs the winch contactor wired to the control box." },
  { id: "tray", name: "Tray", desc: "Needs the tray actuator and limit switches wired to the control box." },
  { id: "camera", name: "Cameras", desc: "Needs at least one camera (rear, front or trailer) plugged into the Pi." },
  { id: "media", name: "Media", desc: "Needs speakers and the audio setup on the Pi." },
];

// Not wired up yet (Sam, 2026-11-17): media, winch and tray.
// In the whole-Teryx simulator (rig/) the winch and tray are wired up in the sim, so they start on.
const IN_RIG = typeof location !== "undefined" && new URLSearchParams(location.search).has("rig");
export const FEATURE_DEFAULTS = { trips: true, drivetrain: true, lights: true, winch: IN_RIG, tray: IN_RIG, camera: true, media: false };

export function featureOn(settings, id) {
  if (!FEATURE_DEFAULTS.hasOwnProperty(id)) return true;   // drive, settings: always on
  const v = settings.get(`features.${id}`);
  return v == null ? FEATURE_DEFAULTS[id] : v !== false;
}

export function featureName(id) { return (FEATURES.find((f) => f.id === id) || { name: id }).name; }

/** Grey out (or bring back) any element. */
export function soon(elm, on = true) {
  elm.classList.toggle("soon", !!on);
  if (on) elm.setAttribute("aria-disabled", "true"); else elm.removeAttribute("aria-disabled");
}
