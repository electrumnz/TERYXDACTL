# Park brake interlock

Sam found on the /rig/ sim (26 Nov 2026) that he could pick Forward and drive with the park
brake on. Now the control box blocks drive while it's on.

## What the park brake is

The stock 2013 Teryx park brake is a **foot pedal on a cable**, left of the brake pedal. There's
no actuator, and we're not adding one. The only electrical part is the stock **park brake
switch** (`PARK_SW` in `config/wiring.yaml`) that lights the red P light in the meter. We tap that
switch into the control box as `in.park` (opto input 7, MCP1 B6). See `teryx-drivetrain.md`.

## What happens

| You do | What happens |
|---|---|
| Park brake on, key on, F-N-R in N | Nothing. P lamp lit as normal |
| Park brake on, pick F or R | Allowed (the switch goes straight to the Shinegle). Dash chimes once, P lamp flashes, banner: **"Release park brake. Drive is blocked while it's on."** |
| Park brake on, press the pedal | No drive. Relay 6 has the pedal switch wire open, so the Shinegle sees the pedal as up |
| Let the park brake off | Relay 6 drops straight away, drive is back. If your foot is already down the Shinegle may want you to lift off and press again (its high pedal disable, to check on the bench) |
| Pull the park brake on while moving | Not cut on the move. The dash warns "Park brake is still on". Once you're stopped the block goes on |
| Key off, dead control box, Pico rebooting | Relay off, NC contact closed, pedal works as normal. A dead control box never strands you |

4WD, diff lock, winch, tray and lights don't care about the park brake here (the light show and
vehicle lock still need it on, as before).

## How it's done

- **Pico rule 11** (`firmware/control-box/src/core/controller.c`, `update_park_block`): key on +
  park brake on + inputs trusted + setting on, and the Teryx is stopped (or the speed isn't known
  yet at key-on), sets `park_block`. It stays set until the park brake goes off, the key goes off
  or the setting is turned off.
- **Relay 6** (`R_PARK_BLOCK`, was spare) on the 16-ch board, MCP1 A5. Its **NC** contact is cut
  into the throttle pedal switch wire: `THROTTLE.SW -> RELAYS.COM6`, `RELAYS.NC6 -> SG1202.J1-9`
  (wires S10, S10b, L24). Only a few mA through it.
- **CAN:** `0x710` byte 4 bit 7 `park_block`, `0x711` relay bit 5 `drive.park_block`. Dash keys
  `pico.park_block`, `drive.park_block`.
- **Setting 41** `park_interlock` (1 = on, default). In Settings on the dash as "No drive with park
  brake on", and in `config/io-map.yaml`.
- **Dash** (`dash/web/js/alerts.js`): the `a:handbrake` alert now fires as soon as F or R is picked
  with the park brake on (not only once you're moving), so you hear about it the moment you try.
- **Sims:** the Python twin (`teryx/sim/controlbox.py`) has the same rule. In the whole-Teryx sim
  (/rig/) it's the real firmware switching the real relay in `wiring.yaml`, and the modelled
  Shinegle reads the pedal switch through it. The rig also now drags the wheels with the park
  brake on.

## RC mode

RC mode still needs the park brake on to switch on (docs/rc-beach-launch.md). The interlock
means it must be let off before RC can drive, the same as from the seat.

## Still to check on the bench

- Does the park switch ground or give 12 V (flip the opto input to suit)?
- Does the SG1202 fault or go into HPD if the pedal switch opens with the pedal down? Either is
  safe, but note what it does.
- Does the SG1202 actually use J1-9 (pedal micro switch)? If it's set to ignore it, the
  interlock needs to cut the wiper (J1-16) instead.
