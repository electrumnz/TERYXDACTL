// Regen on/off for the dash. Regen itself is left to the Shinegle (Sam, 2026-11-19): the
// brake pedal stays standard and the dash only shows when the motor is putting charge back.
//
// Two ways to tell, picked by the dash setting regenFrom:
//  "throttle" (default, Sam 2026-11-19): moving and the throttle at rest. "At rest" is the
//             throttle micro switch off (mc.throttle_sw) if we get it, else the throttle
//             reading within a small deadband of zero, so a released pedal that reads 1 % counts.
//  "current": moving and current flowing back into the pack (mc.batt_a). Falls back to the
//             throttle rule while there's no current reading.
// If the Shinegle turns out to send its own regen flag (mc.regen), that wins either way.
export const REGEN_MIN_KMH = 0.5;       // "above 0", with a little room for speed sensor noise
export const THROTTLE_REST_PCT = 3;     // deadband: a released throttle reads at or below this
export const REGEN_BACK_A = -1;         // amps back into the pack that count as regen

export function throttleAtRest(st) {
  const sw = st.get("mc.throttle_sw");
  if (sw != null) return !sw;
  return (st.get("mc.throttle", 0) || 0) <= THROTTLE_REST_PCT;
}

export function regenOn(st, from = "throttle") {
  if (st.get("mc.online", true) === false) return false;
  const flag = st.get("mc.regen");
  if (flag != null) return !!flag;
  if (Math.abs(st.get("mc.speed", 0) || 0) <= REGEN_MIN_KMH) return false;
  const a = st.get("mc.batt_a");
  if (from === "current" && a != null) return a <= REGEN_BACK_A;
  return throttleAtRest(st);
}
