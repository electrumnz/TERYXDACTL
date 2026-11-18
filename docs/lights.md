# Lights: dimming, the beacon and the light show

Every light on the Teryx can be dimmed and can join the light show. The four
front bars and the cabin bar keep their own setup (MOSFET board channels 1-5,
CAN 0x701 and its effects). Everything else runs off one PCA9685 16-channel
PWM board on the control box's I2C bus. The control box (Pico) makes every
safety call. The dash and the phone only ask.

## Channel map

PCA9685 at address 0x40 on the Pico's I2C1 (GP26/GP27), 3.3 V, 500 Hz on all
channels (`LAMP_PWM_HZ` in `firmware/control-box/src/core/config.h`).

| PWM | Light | Driven by |
|---|---|---|
| 0 | Trailer light bar | MOSFET board ch6 |
| 1 / 2 | Left headlight low / high | BTS7960 no. 4 (RPWM / LPWM) |
| 3 / 4 | Right headlight low / high | BTS7960 no. 5 |
| 5 / 6 | Left tail / left brake | BTS7960 no. 6 |
| 7 / 8 | Right tail / right brake | BTS7960 no. 7 |
| 9 / 10 | Trailer tail / trailer stop | BTS7960 no. 8 |
| 11 / 12 | Rear flood left / right | MOSFET board ch7 / ch8 |
| 13 / 14 | Roof beacon amber / white | BTS7960 no. 9 (RPWM / LPWM) |
| 15 | Enable for all six BTS7960s | 10k pull-down, so they're off at boot |

## Why the stock lamps go on BTS7960 boards

The headlights (12 V 35/35 W) and tail/brake lamps (12 V 8/27 W) are
dual-filament bulbs with one shared earth (2013 Teryx 750 FI owner's manual).
The MOSFET boards switch the earth side, so they can't turn one filament on
without the other. The BTS7960 is two separate half-bridges, so each one can
feed +12 V to its own filament: RPWM drives M+, LPWM drives M-. One board
does both filaments of one lamp. LED replacement lamps with the usual 3-wire
plug are wired the same way, so the plan doesn't change when Sam swaps to LED.

Each BTS output goes to its filament through a 5 A Schottky diode (SB560), so
the backup feeds below can't push current back into the board.

## Backups that work with the control box dead

- **Brake lights:** the brake switch feeds both brake filaments and the
  trailer stop pin through Schottky diodes. Brake lights work even if the
  Pico, PWM board or CAN are dead.
- **Low beams and tails:** the Teryx has no headlight switch, so a hidden
  waterproof toggle (`LIMP_SW`, 10 A fuse on the second fuse block) feeds both
  low beams and both tails through diodes.
- **Key on, no dash:** if the key is on but the dash isn't talking (Pi still
  booting, or crashed), the Pico puts the low beams and tails on full by itself.

## Rules the control box enforces

`teryx/lights.py` is the spec, `firmware/control-box/src/core/lights.c` is the
same rules in C, and `tests/test_lights_parity.py` checks the two match.

1. Brake pressed: both brake lamps and the trailer stop pin at full, always.
   Nothing (show, lock, dimming) can change that.
2. Low and high beam are never on together on one side. High wins.
3. Moving, or speed unknown: headlights and tails don't dim. Anything above
   off is full. Dimming them is for when you're parked.
4. Tails come on by themselves with any headlight or front bar (tail slider
   at 0 = automatic).
5. The beacon flashes at a fixed 3 Hz. The white side takes the other half of
   each flash, and only while the Teryx is stopped.
6. Rear floods: off, on, or on by themselves in reverse. Always full in reverse.
7. The trailer bar is only live with the trailer plugged in.
8. Locked: everything off except rule 1.
9. Key on and no dash: low beams and tails on at full.
10. The light show only runs with the key on, the park brake on, the speed
    signal there and under 0.5 km/h, the dash talking and the vehicle not
    locked. Lose any of those and it stops at once. Never while driving.

## NZ rules we checked

- **Beacon flash rate:** Land Transport Rule: Vehicle Lighting 2004, clause
  11.1(2), a flashing warning lamp must flash at 2 to 4 times a second. We use
  3 Hz, fixed, so it can't be changed into something that isn't allowed.
- **White beacon:** lamps showing to the rear must be red or amber on the
  road (Vehicle Lighting Amendment 2011), and the NZTA beacon checks say a
  beacon must not show anything but red or amber to the rear. So the white
  side only works when you're stopped (beach launching, finding the Teryx
  in the dark), never while driving.
- **Amber beacons:** clause 11.2(4) lists the vehicles allowed an amber
  beacon (including agricultural vehicles and vehicles that are a hazard to
  other road users). Use it off-road, on the beach or when you're a hazard.
- **Stop and rear lamps:** must be steady red on the road (NZTA Vehicle
  Inspection Requirements Manual). That's why the show is parked only and why
  headlights and tails don't dim on the move.

Rules text: <https://www.nzta.govt.nz/resources/rules/vehicle-lighting-2004/>

## CAN

- **0x706 PI_LIGHTS2** (dash to Pico): head low, head high, tail (0 = auto),
  rear flood level (0 = full), trailer bar, beacon amber, show + counter (4 bits each), beacon white. Sent on
  change and every second.
- **0x717 PICO_LIGHTS2** (Pico to dash, 10 Hz): what each of the 15 lamps is
  really doing (4-bit level each), plus show running, show blocked and PWM
  board OK.

Full layout in [`CAN_PROTOCOL.md`](CAN_PROTOCOL.md).

## Light shows

| Show | What it does |
|---|---|
| Wave | A soft spot of light sweeps left to right and back across everything |
| Breathe | Everything fades up and down, the reds the other way |
| Roar | Red glow, eyes open, a strobe roar, a heartbeat, then a fade out (8 s) |
| Party | Left and right swap at 4 Hz, the front bars chase, beacon on the beat |

Start a show from the Lights screen on the dash. The brake pedal still lights
the brake lamps at full during a show.

## Night mode and the cabin light

When the dash goes into Night mode it fades the cabin light down to 15 % over
3 seconds, and back up when it leaves Night mode, unless you've touched the
cabin light yourself in the meantime (Settings, `nightCabin`).

## Bench notes

- Flicker: 500 Hz is well above what eyes or most cameras see. If a camera
  shows banding, try 1 kHz (`LAMP_PWM_HZ`). The BTS7960 is happy up to 25 kHz,
  the MOSFET boards up to 20 kHz.
- Each BTS7960 half-bridge also has a low FET that pulls its output to earth
  when its PWM is low. The Schottky diodes stop that fighting the backups.
