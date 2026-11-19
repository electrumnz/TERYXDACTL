// Regen on/off for the dash. Regen itself is left to the Shinegle (Sam, 2026-11-19): the
// brake pedal stays standard and the dash only shows when the motor is putting charge back.
//
// Best source first:
//  1. mc.regen, if the Shinegle turns out to send its own regen flag.
//  2. mc.batt_a, if we have the battery current: moving and current flowing back into the pack.
//  3. Otherwise: moving, off the throttle and in gear (that's when the Shinegle regens).
export const REGEN_MIN_KMH = 3;        // below this, call it stopped
export const REGEN_THROTTLE_MAX = 2;   // % throttle that still counts as "off the throttle"
export const REGEN_BACK_A = -1;        // amps back into the pack that count as regen

export function regenOn(st) {
  if (st.get("mc.online", true) === false) return false;
  const flag = st.get("mc.regen");
  if (flag != null) return !!flag;
  const moving = Math.abs(st.get("mc.speed", 0)) >= REGEN_MIN_KMH;
  if (!moving) return false;
  const a = st.get("mc.batt_a");
  if (a != null) return a <= REGEN_BACK_A;
  const inGear = ["forward", "reverse"].includes(st.get("mc.direction", "neutral"));
  return inGear && st.get("mc.throttle", 0) <= REGEN_THROTTLE_MAX;
}
