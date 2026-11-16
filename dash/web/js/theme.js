// Day/night theme. In Auto it goes by, in order:
//   1. a light sensor on the Pi (pi.light_lux), if one is ever fitted
//   2. where the sun is, using the GPS position (pi.gps.lat/lon) when there's a fix,
//      otherwise the region picked in Settings > Display (no exact location is ever saved)
// Night starts a bit after sunset (sun 3° below the horizon) and day a bit before sunrise,
// with a small gap so it doesn't flick back and forth at dusk.

export const REGIONS = {
  northland: { name: "Northland", lat: -35.4, lon: 174.0 },
  auckland: { name: "Auckland", lat: -36.9, lon: 174.8 },
  waikato: { name: "Waikato / BOP", lat: -37.9, lon: 175.6 },
  east: { name: "Gisborne / Hawke's Bay", lat: -39.3, lon: 177.0 },
  central: { name: "Taranaki / Manawatū", lat: -39.8, lon: 175.2 },
  wellington: { name: "Wellington / Wairarapa", lat: -41.1, lon: 175.2 },
  top_south: { name: "Nelson / Marlborough", lat: -41.4, lon: 173.4 },
  west: { name: "West Coast", lat: -42.4, lon: 171.3 },
  canterbury: { name: "Canterbury", lat: -43.5, lon: 172.0 },
  otago: { name: "Otago", lat: -45.4, lon: 169.9 },
  southland: { name: "Southland", lat: -46.2, lon: 168.4 },
};

const RAD = Math.PI / 180;

/** Sun height above the horizon in degrees (simple formula, good to about a degree). */
export function sunElevation(date, lat, lon) {
  const d = date.getTime() / 86400000 + 2440587.5 - 2451545.0;
  const g = (357.529 + 0.98560028 * d) * RAD;
  const q = 280.459 + 0.98564736 * d;
  const L = (q + 1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * RAD;
  const e = (23.439 - 0.00000036 * d) * RAD;
  const ra = Math.atan2(Math.cos(e) * Math.sin(L), Math.cos(L));
  const dec = Math.asin(Math.sin(e) * Math.sin(L));
  const gmst = ((18.697374558 + 24.06570982441908 * d) % 24 + 24) % 24;
  const h = (gmst * 15 + lon) * RAD - ra;
  return Math.asin(Math.sin(lat * RAD) * Math.sin(dec) + Math.cos(lat * RAD) * Math.cos(dec) * Math.cos(h)) / RAD;
}

/**
 * Pick day or night. Returns {theme, why} so Settings can say what it went by.
 * prev is the theme on show now, for the dusk gap.
 */
export function autoTheme(st, settings, date = new Date(), prev = "night") {
  const lux = st.get("pi.light_lux");
  if (lux != null) {
    const day = prev === "day" ? lux > 25 : lux > 60;
    return { theme: day ? "day" : "night", why: `light sensor, ${Math.round(lux)} lux` };
  }
  let lat, lon, from;
  if (st.get("pi.gps.fix") && st.get("pi.gps.lat") != null) { lat = st.get("pi.gps.lat"); lon = st.get("pi.gps.lon"); from = "GPS"; }
  else {
    const r = REGIONS[settings.get("themeRegion")] || REGIONS.wellington;
    lat = r.lat; lon = r.lon; from = r.name;
  }
  const el = sunElevation(date, lat, lon);
  const day = prev === "day" ? el > -4 : el > -2;
  return { theme: day ? "day" : "night", why: `sun ${el >= 0 ? `${Math.round(el)}° up` : `${Math.round(-el)}° down`} (${from})`, elevation: el };
}
