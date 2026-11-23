# Power steering: the Toyota Aqua column

Sam has the column (JTEKT 45250-52544) with its ECU (89650-52B51) on it, and the
ECU's power plug. Bought from Dodson's on 19 Nov 2026 for NZ$115. Why a wrecker
column, and where the CAN frames came from: [`power-steering-wrecker.md`](power-steering-wrecker.md).

This page is the code base for running it from the Pico, the guesses it makes,
and how to check them on the bench.

## 1. Short version

- The column's own Toyota ECU still does the steering: it reads the torque
  sensor and drives the motor. The Pico never drives the motor.
- The Pico powers the ECU's ignition through relay 9, sends it "engine running"
  and "our speed" every 20 ms on its own CAN bus, and listens to what it says
  back. The dash shows the state and warns if something's wrong.
- **Nothing about the Aqua ECU's CAN has been confirmed yet.** We start from the
  2004-09 Prius recipe (the only Toyota EPS with a proven standalone setup) and
  what opendbc knows about Toyota EPS ECUs. Every guess is marked `ASSUMED` in
  the code and can be changed in one place (section 4).
- If our guesses are wrong, the worst case is limp mode (heavier, still
  assisted). If the column loses power, it's a plain manual column.

## 2. The missing plug

The Toyota EPS ECUs we found wiring for have two plugs that come off the car's
loom. The motor and torque sensor plugs stay on the column, so you already have
those.

| Plug | Pins (names from Toyota's RAV4 EPS manual) | Have it? |
|---|---|---|
| Power | PIG (+12 V, always on, thick wire), PGND (earth, thick wire) | **Yes** |
| Signal | IG (ignition), CANH, CANL. Maybe a diagnostic pin as well | **No, still needed** |

So the one to get is the **signal plug**: the smaller one with thin wires.
Ask Dodson's, or any wrecker with an NHP10 Aqua or Prius C, to cut it from the
loom with about 300 mm of wire. It's on the shopping list (`aqua_plug`).

Two caveats, both to check with a photo of the ECU sockets:

- We couldn't find an Aqua-specific pinout. The RAV4 manual has IG on pin 5,
  CANH on pin 2 and CANL on pin 8 of the signal plug, and PIG/PGND on pins 1 and
  2 of the power plug. The Aqua's will be similar but may not match.
- If no plug turns up, the fallback is single crimp terminals pushed onto the
  ECU pins and sealed with heatshrink. Not as good, but fine for the bench.

## 3. What the code does

| Part | Where | What |
|---|---|---|
| Frames to the ECU | `firmware/control-box/src/core/eps.c` `eps_frames()` | RPM (0x2C4) and speed (0x0B4) every 20 ms, Toyota checksum |
| Assist curve | `eps_told_speed_x10()` | Which speed we tell the ECU (settings 34-36) |
| Listening | `eps_on_frame()` | Reads torque, angle and status from the ECU (0x260, 0x262) |
| State + warnings | `eps_update()` | Works out the state the dash sees (section 5) |
| Rules | `controller.c` | Relay 9 on with the key on and not locked. Mode changes wait until stopped |
| Hardware | `src/pico/main_pico.c` | Second MCP2515 on GP22, polled for replies. `EPS` on the UART console lists every ID heard |
| Status to the Pi | CAN 0x718 `PICO_STEER` | State, flags, torque, angle, told speed, ECU status |
| Python twin | `teryx/eps_toyota.py` | Same numbers, frame decoder, assist curve. Used by the simulator |
| ECU in the sim | `teryx/rig/models.py` `EpsEcu` | A guessed Aqua ECU: answers 0x260/0x262, assist by speed, limp, sensor faults. Try it on the [simulator page](https://electrumnz.github.io/TERYXDACTL/rig/); the guesses are listed in [system-sim.md](system-sim.md#guesses-until-the-bench-test) |
| Dash | `dash/web/js/alerts.js`, `telltales.js` | Steering lamp and alert text |

The Python side is checked against the C header and settings table by
`tests/test_eps_toyota.py`, so the two can't drift apart.

## 4. Every guess, and where to change it

| Guess | Value now | Based on | Change it in |
|---|---|---|---|
| Bus speed | 500 kbit/s | Toyota powertrain CAN | `EPS_BITRATE` in `eps.h` (+ `eps_toyota.py`) |
| Engine RPM frame | 0x2C4, RPM in bytes 0-1 | Prius gen 2 retrofit | `EPS_RPM_ID` |
| Speed frame | 0x0B4, bytes 5-6, 0.01 km/h | Prius gen 2 retrofit, opendbc `SPEED` | `EPS_SPEED_ID`, `EPS_SPEED_BYTE` |
| Send rate | every 20 ms | Prius: 100 ms wasn't enough | `EPS_PERIOD_MS` |
| RPM value | 1674 | Prius retrofit | Setting 39 |
| ECU talks back on 0x260 (torque, angle) | yes | opendbc `STEER_TORQUE_SENSOR` | `EPS_TORQUE_ID` |
| ECU status on 0x262 | maybe | opendbc `EPS_STATUS` (an LKA frame, so likely missing on an Aqua) | `EPS_STATUS_ID` |
| "Permanent fault" status value | 17 | opendbc `LKA_STATE` | `EPS_STATUS_PERMANENT_FAULT` |
| Diagnostics address | 0x7A1 / 0x7A9 | opendbc Toyota fingerprints | `EPS_DIAG_REPLY_ID` |
| Lightest steering below | 16.3 km/h | Prius retrofit's "max assist" | Setting 34 |
| How fast it firms up | real speed x 100 % | | Setting 35 |
| ECU boot time | 3 s | Prius owners: 5-15 s wait in limp | Setting 40 |

Settings 33-40 are on the dash's Safety limits screen and saved on the Pico, so
most bench changes need no new firmware. IDs need a rebuild, which goes over the
air as usual.

| Key | Setting | Default | What |
|---|---|---|---|
| 33 | `eps_mode` | 2 | 2 normal, 1 limp (relay on, no frames), 0 manual (relay off). **Only changes when stopped or key off** |
| 34 | `eps_floor_kmh_x10` | 163 | Below this speed, tell the ECU this one |
| 35 | `eps_speed_gain_pct` | 100 | Above it, tell the ECU real speed x this % |
| 36 | `eps_max_kmh` | 120 | Never tell it more than this |
| 37 | `eps_listen` | 0 | 1 = warn if the ECU goes quiet. Turn on once the bench shows it talks |
| 38 | `eps_silent_ms` | 1000 | Quiet this long = no reply |
| 39 | `eps_rpm` | 1674 | Fake engine RPM |
| 40 | `eps_wake_ms` | 3000 | Time the ECU gets to boot before it's judged |

## 5. What the dash shows

| State | Means | Dash |
|---|---|---|
| off | Key off or locked | Nothing |
| waking | Just powered, ECU booting | Nothing |
| ok | Powered and getting frames (and answering, if listening) | Nothing |
| limp | Mode 1, on purpose | Info alert |
| manual | Mode 0, on purpose | Amber steering lamp + alert |
| no_reply | Listening, but the ECU is quiet | Amber steering lamp + alert |
| ecu_fault | ECU says permanent fault | Red flashing steering lamp + alert |
| bus_error | The Pico's steering CAN board isn't working | Amber steering lamp + alert |

None of these turn assist off. Only the key, the vehicle lock and mode 0 do
that. A faulty ECU runs Toyota's own fail-safe, which is safer than us cutting
it.

## 6. Bench test

Kit: 12 V supply that can do 30 A+ (or a car battery with a 60 A fuse), the
control box Pico with the second MCP2515, a USB-serial lead on the Pico's UART
for the `EPS` command, and the CAN sniffer if you have it.

1. **Photo the ECU sockets** and the power plug wiring. Fill in the pin numbers
   in `config/wiring.yaml` (`EPS_ECU`).
2. **Power only (PIG, PGND, IG).** No CAN. Turn the input shaft by hand. Expect
   limp mode: some assist, or none for 5-15 s and then some. This is what the
   Teryx gets if the Pico ever stops.
3. **Add the Pico** (settings default, mode 2). Wire CANH/CANL with 120 Ω at
   each end. Turn the shaft: assist should come on straight away and feel
   lighter than step 2.
4. **See what it sends.** Type `EPS` on the UART console. It lists every ID the
   ECU sent with its last bytes. If 0x260 is there, torque and angle work as
   coded. Note any others (one will be the warning lamp message to the dash
   cluster). Then set `eps_listen` to 1.
5. **Speed feel.** Set setting 34 to 0 and use the bench speed (simulator or the
   Shinegle) at 0, 20 and 60 km/h. Assist should get firmer as speed goes up.
   Pick the floor and gain that feel right, then put them back to sensible values.
6. **Limp and manual.** Set mode 1, then 0, and check each does what it says.
7. **If step 3 gives no assist:** the Aqua wants other frames. Sniff a running
   Aqua or Prius C's OBD port (pins 6 and 14) at 500 kbit/s with the CAN sniffer
   and look for the speed frame (it changes with wheel speed). Change the IDs in
   `eps.h` and `eps_toyota.py`, run the tests, and flash.
8. **Torque sensor centre.** If it pulls to one side, it needs a centre reset
   with a Toyota scan tool (Techstream or a bi-directional tool like an Autel).

Power: plan for the 60 A fuse and its own cable to the battery, as in
`power-steering-wrecker.md`.

## Sources

- opendbc (MIT), Toyota DBCs: `STEER_TORQUE_SENSOR` 0x260 and `SPEED` 0x0B4 in
  [`_toyota_2017.dbc`](https://github.com/commaai/opendbc/blob/master/opendbc/dbc/generator/toyota/_toyota_2017.dbc),
  `EPS_STATUS` 0x262 in
  [`toyota_nodsu_pt.dbc`](https://github.com/commaai/opendbc/blob/master/opendbc/dbc/generator/toyota/toyota_nodsu_pt.dbc),
  EPS diagnostic address 0x7A1 in
  [`fingerprints.py`](https://github.com/commaai/opendbc/blob/master/opendbc/car/toyota/fingerprints.py).
  Our decoder was checked against these with cantools (`tests/test_eps_toyota.py`).
- Prius gen 2 frames: Carloop community thread, see `power-steering-wrecker.md`.
- Toyota RAV4 EPS ECU terminals (IG, CANH, CANL on E18; PIG, PGND on A1):
  [Toyota RAV4 repair manual, EPS system](https://share.qclt.com/%E4%B8%B0%E7%94%B0Toyota%20RAV4%20Repair%20Manual/Power%20Steering/Electronic%20Power%20Steering%20System/041001.pdf)
- No Aqua EPS pinout found online. A PriusChat poster says the Aqua wiring is in
  the Japanese-only electronic technical manual, and that Aqua and Prius C
  connectors differ:
  [PriusChat, 2017 Aqua connectors](https://www.priuschat.com/goto/post?id=2909609)
- Toyota EPS "3 wires, fail-safe mode" builds:
  [The Ranger Station](https://www.therangerstation.com/tech/toyota-electric-power-steering-eps-conversion/)
