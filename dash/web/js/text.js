// Plain-English words for codes from the control box and the motor controller.
// Codes agreed with the test environment and firmware work (see docs/DASH_API.md).

export const PICO_FAULTS = {
  dash_link:          { sev: "warn", text: "Control box lost the dash for a moment. Moving parts were stopped." },
  speed_unknown:      { sev: "warn", text: "No speed from the motor controller. 4WD, diff, tray and winch are locked out." },
  fourwd_timeout:     { sev: "bad",  text: "4WD actuator didn't finish in time. Check the actuator and wiring." },
  fourwd_overcurrent: { sev: "bad",  text: "4WD actuator pulled too much current and was stopped." },
  diff_timeout:       { sev: "bad",  text: "Diff lock actuator didn't reach its target in time." },
  diff_pot_stuck:     { sev: "bad",  text: "Diff lock position sensor isn't moving. Check the pot wiring." },
  tray_timeout:       { sev: "warn", text: "Tray ran too long without hitting a limit switch and was stopped." },
  tray_overcurrent:   { sev: "bad",  text: "Tray actuator pulled too much current and was stopped. Is it overloaded?" },
  tray_limit_switch:  { sev: "bad",  text: "Tray limit switches don't make sense. Check both switches." },
  winch_interlock:    { sev: "bad",  text: "Winch in and out were both asked for. Winch has been disarmed." },
  low_12v:            { sev: "warn", text: "12V battery is low." },
  pico_hot:           { sev: "warn", text: "Control box is running hot." },
  watchdog_reset:     { sev: "warn", text: "Control box restarted itself after a hang. Everything started off." },
  diff_overcurrent:   { sev: "bad",  text: "Diff lock actuator pulled too much current and was stopped." },
  io_bus:             { sev: "bad",  text: "Control box can't talk to its relay or sensor boards. Check the I2C wiring." },
};

export const MC_FAULTS = {
  over_current:         { sev: "bad",  text: "Motor controller: over current" },
  over_voltage:         { sev: "bad",  text: "Motor controller: battery voltage too high" },
  under_voltage:        { sev: "bad",  text: "Motor controller: battery voltage too low" },
  motor_over_temp:      { sev: "bad",  text: "Motor too hot. Ease off and let it cool." },
  controller_over_temp: { sev: "bad",  text: "Motor controller too hot. Ease off and let it cool." },
  hall_sensor:          { sev: "bad",  text: "Motor position (hall) sensor fault" },
  throttle:             { sev: "bad",  text: "Throttle fault. Check the pedal wiring." },
  comms:                { sev: "warn", text: "Motor controller comms fault" },
  battery_over_temp:    { sev: "bad",  text: "Traction battery too hot" },
  precharge:            { sev: "bad",  text: "Precharge fault. Controller didn't power up cleanly." },
};

export const REJECTS = {
  too_fast:       "Too fast for that. Slow down first.",
  not_stopped:    "Stop the Teryx first.",
  speed_unknown:  "Speed unknown, so that's locked out.",
  not_armed:      "Arm the winch first.",
  interlock:      "Blocked by a safety interlock.",
  actuator_fault: "That actuator has a fault. See Faults in Settings.",
  low_12v:        "12V battery too low for that.",
  dash_link:      "The control box lost the dash for a moment. Try again.",
  ignition_off:   "Key is off.",
  at_limit:       "Already at the end of its travel.",
  not_parked:     "Put it in park first.",
  winch_remote:   "The handheld winch remote is in use.",
  bad_frame:      "The control box didn't understand that request.",
  wait_timeout:   "Waited too long for the right speed, so it didn't change. Tap again to retry.",
  busy:           "Wait for the last 4WD or diff change to finish.",
};

export function faultText(code, table) {
  return (table[code] && table[code].text) || code.replace(/_/g, " ");
}

export function asList(v) {
  if (!v) return [];
  if (Array.isArray(v)) return v;
  if (typeof v === "string") return v === "none" || v === "" ? [] : [v];
  return [];
}
