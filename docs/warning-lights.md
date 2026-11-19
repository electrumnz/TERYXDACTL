# Warning lights and inputs

What a normal car or EV dash would show, and how Teryx OS covers each one.
Code: `dash/web/js/telltales.js` (the lamps), `dash/web/js/alerts.js` (the
banner text and thresholds behind them). Checked 19 Nov 2026.

## How it works

- A row of warning lights along the top of the drive screen. Fixed order,
  fixed colours like any car: **red** = stop or act now, **amber** = take
  care, **green** = on and working, **blue** = high beam. Only lit lamps show.
- **Lamp check:** every lamp lights for 2.5 s at key-on, like a real cluster.
- Each warning lamp has a banner behind it that says what's wrong and what to
  do. The lamp and the banner use the same thresholds, so they never disagree.
- Lamps flash when something needs you now (handbrake on while driving, tray
  up on the move, very low battery, overheating, a 4WD or diff change running).

## The lamps

| Lamp | Colour | Lit when | Source |
|---|---|---|---|
| READY | green | Motor controller says ready to drive | Shinegle CAN (`mc.ready`) |
| Park brake (P) | red, flashes if you drive with it on | Park brake pedal switch | `in.park` |
| Brake system (!) | red | Brake pedal sensor disagrees with the brake switch, or the regen pedal sensor failed | Pico fault `brake_pedal`, `regen.state` |
| Seat belt | red | 10 s after key-on, same as the stock Teryx (it has no buckle switches) | timer |
| 12V battery | red | 12V under 11.8 V, or READY but the 12V sits under 12.9 V for 20 s (DC-DC not charging). Ignored while winching | `an.aux_12v` |
| Motor controller fault | red | Any controller fault bit, or a controller ErrorCode above 1. The banner shows the SG1810 manual's words and fix for that code | Shinegle CAN, `config/shinegle-faults.yaml` |
| Temperature | amber / red flashing | Motor (105 / 120 °C), controller (75 / 85 °C) or traction battery (47 / 55 °C) | Shinegle CAN |
| Traction battery low | amber at 20 %, red flashing at 10 % | State of charge | Shinegle CAN |
| Reduced power (turtle) | amber | Controller has cut power back (limp) | Shinegle CAN |
| Power steering | amber (red, flashing, on an ECU fault) | Key on, not locked, and the column is unpowered, not answering, or its CAN board is down. Red when the ECU says it has a fault | Pico relay 9 (0x711 byte 7) and 0x718 steering state |
| Control box | amber / red flashing | Any control box fault (amber), or the box is offline or in failsafe (red) | 0x710 |
| Slope | amber / red flashing | Side slope or pitch past the Settings limits | IMU |
| Tray | amber, red flashing on the move | Tray isn't fully down. Moving over 3 km/h with it up is the "door open" warning | 0x712 |
| Service | amber | Odometer past "Next service at" (Settings > Display, off by default) | odometer |
| 4WD | green, flashes while changing | 4WD engaged | 0x712 |
| Diff lock | amber, flashes while moving | Front diff lock above 2 % | 0x712 |
| Throttle hold | green | Throttle held while a shift runs from a standstill | 0x710 |
| Winch | amber, flashes while it runs | Winch armed, running, or run by hand | 0x710/0x711 |
| RC | amber | RC mode on | RC |
| Headlights | green | Low beams on | 0x717 lamp levels |
| High beam | blue | High beams on | 0x717 lamp levels |
| Light bars | green | Any front bar on | 0x711 |
| Beacon | amber | Beacon on | dash request |
| Trailer | green | Trailer plugged in | `in.trailer` |

Things that are banners only (no lamp of their own, as in most cars): dash
server lost, winch motor heat, RC state, each control box fault's details.

## Not on the list, on purpose

- **Fuel, oil pressure, coolant, check engine, CVT belt:** engine parts, gone
  with the conversion.
- **Indicators and hazards:** the Teryx has none stock ([lights.md](lights.md)).
- **Doors:** no doors, side nets only. The tray is the "door open" warning.
- **Airbag, ABS, traction control:** the Teryx has none.

## Inputs we don't have yet

These are the gaps between our inputs and a normal EV. None of them stop the
build. Each one needs a decision from Sam before parts get added to the list.

1. **Charging.** Nothing tells us the traction battery is on charge, so there's
   no charging lamp and nothing stops you driving off with the lead plugged in
   (every road EV blocks that). Fix: a signal from the charger, or a switch on
   the charge inlet cap, into one of the 8 spare inputs on the second opto
   board. Then the Pico blocks drive while it's plugged in and the dash shows
   charge %, time left and a charging lamp. Needs: which charger and inlet the
   kit came with.
2. **Seat belt buckles.** The stock light is a reminder only, and so is ours.
   Buckle switches would make it a real "belt off" warning, using 2 spare
   inputs.
3. **Power steering column health.** Now coded: the Pico polls the steering
   CAN board for the ECU's replies and the dash warns on "no reply", "ECU
   fault" and "CAN board down" (`docs/power-steering-aqua.md`). The frames it
   listens for are guesses until the bench test, so "no reply" is off
   (setting 37) until then.
4. **Tyre pressures.** Cars have TPMS. Bluetooth valve-cap sensors can be read
   by the Pi's built-in Bluetooth (no USB). Optional.
5. **High voltage isolation.** Road EVs watch for the traction pack leaking to
   the chassis. The Shinegle's fault list doesn't include one. An isolation
   monitor is extra hardware. Low priority for a 72 V off-roader, noted here so
   it isn't forgotten.

## Sources

- Seat belt reminder lights at key-on for about 10 s, even with the belt done
  up: Kawasaki Teryx owner's manual (2014 edition), meter section,
  [manualowl p. 46](https://www.manualowl.com/am/Kawasaki/2014-Teryx/Manual/10235?page=46).
  2013 edition meter page: [manualowl p. 45](https://www.manualowl.com/am/Kawasaki/2013-Teryx%20750%20FI%204x4%20LE/Manual/10657?page=45)
  (blocks automated reads, check by eye).
- Shinegle ErrorCodes: SG1810 programmer manual, our copy in
  [`config/shinegle-faults.yaml`](../config/shinegle-faults.yaml).
- Park brake switch in the stock meter: [teryx-drivetrain.md](teryx-drivetrain.md).
