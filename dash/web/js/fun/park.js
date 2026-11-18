// The one rule for everything in Fun: games, video, streaming and the easter eggs only run
// when the Teryx is parked. Parked means the park brake is on AND it's stopped AND the
// speed is known. If the motor controller goes quiet, that counts as moving.
// The dash server applies the same rule to the streaming window (teryx_dash/fun.py).

export function isParked(st) {
  if (!st.get("in.park")) return false;
  if (st.get("mc.online") === false) return false;
  if (st.get("pico.parked") === false) return false;   // the control box's own view, when it sends one
  return Math.abs(st.get("mc.speed", 0)) < 0.5;
}

export function whyNotParked(st) {
  if (st.get("mc.online") === false) return "No speed from the motor controller";
  if (Math.abs(st.get("mc.speed", 0)) >= 0.5) return "The Teryx is moving";
  if (!st.get("in.park")) return "Put the park brake on";
  return "";
}
