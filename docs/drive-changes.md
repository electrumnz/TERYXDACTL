# Safe 4WD and diff lock changes

Asked for by Sam (2026-11-17): when you tap 4WD or diff lock and it can't change
yet, the dash should show a spinner, wait for the right conditions, then change
by itself, with a time-out and a Cancel button. Other drive changes are blocked
while one is happening, and you get clear feedback when it's done.

The **control box (Pico) does the waiting and the safety checks**. The dash
only shows what's going on, so a frozen or rebooting dash can't leave a change
half done.

## What happens when you tap

| Situation | What the control box does | What the dash shows |
| --- | --- | --- |
| Speed is fine | Changes straight away | Spinner on the button, then a tick, a green pulse, a chime and a toast ("4WD engaged.") |
| Too fast (4WD: not stopped, under 1 km/h; adding diff lock: 15 km/h or more) | Holds the request for up to 10 s (`shift_wait_ms`), then changes as soon as the speed is right | Spinner, "Stop to shift · 8s" or "Slow down to 15 km/h · 8s" with a countdown, and **Cancel** |
| You tap Cancel (or the same button again) | Drops the request. Nothing changes | Grey "Cancelled" and a toast |
| 10 s runs out | Drops the request, refuses with `wait_timeout` (14) | Amber shake, "Timed out. Tap again to retry." |
| No speed signal, key off, lost dash, actuator fault | Refuses at once (or drops a waiting request) with the reason | Red outline and the reason in a toast |
| Another drive change is waiting or running | Refuses with `busy` (15) | The other buttons are dimmed and say why |

Taking diff lock **off** never waits and is never blocked: it works at any
speed, even while 4WD is changing (Kawasaki has you unlock after the obstacle,
and a locked front diff makes steering heavy).

A request that times out or is cancelled is gone for good. The dash resends its
last request every second, but the control box only acts on a *change*, so
nothing happens later by surprise.

## Throttle hold

While a shift is running **and the Teryx was stopped when it started**, the
control box sets "throttle hold" so you don't drive off with the actuator half
way. It is never applied while moving:

- If the Teryx starts to roll during the shift, the hold drops and stays off
  until that shift is done.
- A diff lock change started on the move is never held, even if you then stop.
- It only lasts as long as the actuator runs (2-3 s for 4WD, at most its max run time).
- Setting 31 `shift_throttle_hold` turns it off.

**Still to do:** the hold is worked out and reported (`0x710` byte 4 bit 6, and
`cb_out_t.throttle_hold` in the firmware), but nothing tells the Shinegle yet.
How (a CAN command, or a wired inhibit input on the controller) waits for the
Shinegle decode. The simulator does honour it, so you can see it on the bench.

## On the wire

- `0x710` byte 4: bit 4 `fourwd_wait`, bit 5 `diff_wait`, bit 6 `throttle_hold`.
- `0x712` byte 7 (`diff_target`): while `diff_wait` is set, the % it's waiting to go to.
- Reject reasons: 14 `wait_timeout`, 15 `busy`.
- Settings: 30 `shift_wait_ms` (default 10000, 0 = refuse at once like before),
  31 `shift_throttle_hold` (default 1). In `config/io-map.yaml` as
  `shift_wait_s` and `shift_throttle_hold`.
- Cancel is not a new message: the dash just asks for what's already there.

## Where the code is

- Firmware: `firmware/control-box/src/core/controller.c` (`wait_4wd`, `wait_diff`,
  `update_throttle_hold`), tests in `firmware/control-box/tests/test_controller.c`.
- Simulator (same rules, readable spec): `teryx/sim/controlbox.py`, tests in
  `tests/test_controlbox.py`. The sim's vehicle won't pull away while held.
- Dash: `dash/web/js/ui/shift.js` tracks each change, `dash/web/js/screens/drivetrain.js`
  draws it, styles at the end of `dash/web/css/dash.css`.
