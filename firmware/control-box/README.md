# Control box firmware (Pico 2)

The Pico 2 owns every output and every safety rule. The Pi 5 dash only asks
over CAN. If the Pi crashes or is unplugged, the Teryx still drives, the lights
stay as they were and anything moving stops.

Wiring and pins: [`docs/io-list.md`](../../docs/io-list.md) section 3.
CAN messages: `docs/CAN_PROTOCOL.md` and `teryx/canbus/messages.py` (test
environment). This firmware matches them byte for byte, plus the extras listed
at the bottom of this page.

## Layout

| Folder | What |
|---|---|
| `src/core/` | All the control logic and safety rules. Plain C, no hardware calls, so the same code runs on the Pico, on a PC and in the tests |
| `src/pico/` | Pico 2 hardware layer: MCP2515 CAN, MCP23017 relays/inputs, ADS1115, PWM, watchdog, settings in flash, USB bootloader |
| `src/host/` | PC build: a model of the actuators, limit switches and pot, plus a UDP or SocketCAN bus |
| `tests/` | Unit tests (`test_controller.c`) and an end-to-end bus test (`test_bus.py`) |
| `pico_sdk_import.cmake` | Copied unchanged from the Pico SDK (BSD-3-Clause, fine to use in this MIT repo) |

## Build

**Pico 2** (needs the [Pico SDK](https://github.com/raspberrypi/pico-sdk) 2.x and `arm-none-eabi-gcc`):

```sh
cmake -S . -B build -DPICO_BOARD=pico2 -DPICO_SDK_PATH=/path/to/pico-sdk
cmake --build build -j4        # gives build/teryx_control_box.uf2
```

GitHub Actions builds the `.uf2` on every push and keeps it as a download.

**PC (host) build and tests:**

```sh
cmake -S . -B build-host -DTERYX_HOST=ON
cmake --build build-host
ctest --test-dir build-host --output-on-failure
```

## Run it against the simulator

The host build plays the Pico on the same bus as the test environment:

```sh
./build-host/control-box-host --bus udp          # terminal 1: the "Pico"
python -m teryx run --bus udp --no-controlbox    # terminal 2: sim + dash
```

`--bus socketcan:vcan0` works too on Linux. The sim page drives the Pico's
wired inputs (ignition, brake, reverse, tray limits, winch remote, park) and
injects faults with the `0x7E0` bench frame. The real Pico ignores `0x7E0`.

The firmware version comes from `firmware/VERSION` ("major.minor"), which the dash compares with what `0x713` reports.

Settings the dash saves (`0x704` key `0xF0`) go to `control-box-settings.bin`
on the PC, and to the last 4 KB of flash on the Pico.

## Updating the Pico from the Pi (OTA)

The Pico's USB plugs into the Pi (data only, the Pico has its own 5V supply).

```sh
tools/pi/flash-control-box.sh teryx_control_box.uf2 can0
```

1. Checks the "parked" flag in `0x710` (stopped, or key off, or park switch on,
   and nothing moving).
2. Sends `0x71F` with magic `0x5445`. The Pico checks it's parked, makes every
   output safe (power hold and accessory stay on), and reboots into the RP2350
   USB bootloader.
3. `picotool load -v -x` writes, verifies and starts the new firmware.
4. Waits for `0x713` and prints the version. Keeps `current.uf2` and
   `previous.uf2` in `/var/lib/teryx/control-box/` for rollback.

If CAN is down it falls back to `picotool reboot -f -u` over USB. Needs
`picotool` and `can-utils` on the Pi.

## How each rule is done (IO list section 7)

| Rule | What the firmware does |
|---|---|
| 1 Lost dash | No `0x700` for 500 ms: stop tray, 4WD and diff actuators, winch off and disarmed, isolator off. Lights stay. 3 s grace after boot |
| 2 Lost speed | No Shinegle speed for 500 ms: speed unknown, so anything that needs "stopped" or a speed check is refused |
| 3 2WD/4WD | Starts only when stopped (under 1 km/h, Kawasaki says stop first, see `docs/teryx-drivetrain.md`). Requests act on a change only, except that while the position is unknown (after boot) a resend homes it once it is safe. Full power to the end. Done when the current drops away (actuator's own limit switch), fault on over 6 A, gives up after 3 s |
| 3/4 waiting | A 4WD or diff request that is only too fast waits up to `shift_wait_ms` (10 s) and runs once the speed is right. Asking for what's already there cancels it. Hard reasons (no speed, key off, lost dash, fault) drop it, a time-out rejects it (14). One drive change at a time (15 busy), except unlocking. Throttle hold only while a shift runs from a standstill, dropped for good if it rolls |
| 4 Diff % | Adding lock starts only under 15 km/h, and stops where it is if speed goes over. Unlocking runs at any speed (needs a known speed). Closed loop on the pot with a 2 % deadband. Fault if the pot doesn't move for 1 s while driving, over 8 A, or after 4 s. Pot reading outside its calibrated range = wire fault |
| 5 Tray | Stopped only, hold-to-run (stops 300 ms after the last `0x703`). Stops at limit switches, over 10 A, after 20 s, or if the Teryx moves. Both limits showing at once = wiring fault, tray locked out |
| 6 Winch | Arm only when stopped. Hold-to-run. In and out never together, with 100 ms of both-off between them. Disarms on lost dash, key off, any speed, or 2 min idle. Tray and winch can't run at the same time. If the handheld remote or a hand switch is in use, the dash can't drive the winch. **Timed pull:** if `0x703` byte 3 is set (seconds), the Pico starts its own timer when the winch actually starts and stops it on time even if the dash keeps sending, capped at setting 21 (default 30 s). It won't run again until the dash lets go and presses again. A timed pull cut short (remote, interlock) also needs a new press. The 300 ms hold timeout still applies the whole time |
| 7 Reverse | Reverse = the wired input or the Shinegle's direction. Rear pods on when "auto rear" is set |
| 8 Key-off | Accessory off, motion stops, winch disarmed. `0x710` asks the Pi to shut down. Power hold drops 10 s after the Pi stops heartbeating, or after 30 s at most. Key back on cancels it |
| 10 Vehicle lock | `lock.c` (`docs/vehicle-lock.md`). PIN lock kept in its own flash sector with a salted SHA-256 hash and the wrong-try count, so a power cut doesn't unlock it. Locks only when stopped, park brake on and nothing moving. Locked: drive inhibit flag, no 4WD/diff/tray/winch, lights off, no settings or OTA. 5 wrong tries, then 30 s doubling to 15 min. Recovery code, or `LOCK RESET` on the debug UART inside the box |
| 9 Watchdog | 250 ms hardware watchdog. Everything starts off at boot. A watchdog reset shows as a fault for 30 s |

Other things it does:
- **Lights:** each bar has a "dims" or "on/off only" setting (`0x704` key 16,
  bit per light). On/off bars go full on for any level above 0. Dimmable bars
  fade over about 80 ms. Effects (strobe, chase, outside only, inside only,
  breathe, SOS) run on the Pico, on the front bars that are on.
- **Trailer:** tail on with any front light, brake follows the brake input.
- **Relays** are active-low by default (most opto relay boards). Change with
  setting key 18 if yours isn't. The "all off" pattern is written to the
  MCP23017 before its pins become outputs, so nothing clicks on at power-up.
- **Power hold across a Pico reset:** if only the Pico resets (watchdog or
  update), it reads the power-hold relay back from the MCP23017 and keeps it,
  so the Pi isn't cut off halfway through a shutdown.

## Extras on top of messages.py

These are in the firmware and need adding to the test environment's
`messages.py` (agreed with that thread, or flagged to it):

- `0x710` byte 6: bit 1 speed valid, bit 2 reverse active, bit 3 shutdown
  request (key off, Pi should shut down), bit 4 parked (OTA allowed).
  Byte 7: speed in km/h as the Pico sees it (`0xFF` unknown).
- `0x710` reject reasons 8+: 8 dash link, 9 ignition off, 10 at limit,
  11 not parked, 12 winch remote in use, 13 bad frame.
- Fault bits 13 diff overcurrent, 14 IO bus (MCP23017 or ADS1115 not answering).
- 4WD state 5 = unknown (after boot, until the first move).
- Light effect 6 = SOS.
- `0x714` byte 1: 0 ok, 1 unknown key, 2 out of range.
- Settings keys 18 relay active-low, 19 tray full travel ms (for the tray %
  estimate), 20 low 12V warning mV, and `0xF2` clear latched faults.
- `0x7E0` bench: bit 3 pot disconnected, bit 4 IO bus dead, bytes 3-4 12V aux mV.
- Safe drive changes (`docs/drive-changes.md`, now in `messages.py` too):
  `0x710` byte 4 bit 4 4WD waiting, bit 5 diff waiting, bit 6 throttle hold;
  reject reasons 14 wait timed out, 15 busy; settings 30 `shift_wait_ms`,
  31 `shift_throttle_hold`. `cb_out_t.throttle_hold` is there for the hardware
  layer, but nothing sends it to the Shinegle until its CAN is decoded.
- Vehicle lock (`docs/vehicle-lock.md`, in `messages.py` too): `0x705` lock command,
  `0x716` lock state, `0x714` status 3 "locked". `cb_out_t.drive_inhibit` is set while locked,
  but like throttle hold nothing reaches the Shinegle yet. `cb_out_t.save_lock` asks the
  hardware layer to write the lock sector. Debug UART (GP0/GP1, 115200) now runs the
  `LOCK RESET` workshop command.

## Check on the bench before it goes on the Teryx

- MCP2515 crystal: 8 MHz is assumed (`MCP2515_OSC_HZ` in `src/core/config.h`).
  Change to 16 MHz if your module says 16.000.
- CAN bit rate 250 kbit/s is a guess until the Shinegle is recorded.
- Shinegle speed is read from the **mock** frame `0x180`. Once the real bus
  is decoded, only the `CAN_ID_MC_SPEED` case in `controller.c` changes.
- Relay board polarity (setting 18) and whether it triggers from 3.3 V.
- Actuator directions (`DIFF_LOCK_DIR`, `FOURWD_ENGAGE_DIR`, `TRAY_UP_DIR`).
- Diff pot calibration: set keys 14 and 15 to the raw readings at 0 % and
  100 % (the dash can show the raw value during calibration).
- Tray travel time: the 20 s tray limit must be longer than a full lift.
- Winch isolator: with the isolator off whenever the winch is disarmed, the
  handheld remote only works while armed. If the remote must always work as a
  backup, wire it to bypass the isolator relay.
- Pico power: if the Pico runs off switched 12V it loses power at key-off
  and can't hold the Pi on. Feed its buck from the power-hold side too.

## Later

- The RP2350 boot ROM supports A/B firmware slots with "try before you buy"
  (a new image must confirm itself or the Pico falls back). That would make a
  bad update recover on its own. Worth adding once the basics are proven.
