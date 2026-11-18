# Vehicle lock (PIN)

A lock button in **Settings > Vehicle lock** that locks the Teryx down when you leave it, like
parked at the beach. You need the PIN to drive again.

## How it works

- The **control box (Pico) does the locking**, not the screen. It keeps the lock, a salted hash
  of the PIN and the wrong-try count in its own flash sector. Rebooting the Pi, unplugging the
  screen, or cutting power to everything does not unlock it. It comes back up locked.
- The dash only asks (CAN `0x705`) and shows what the Pico says (`0x716`). The Pi never keeps
  the PIN.

### Locking

- Needs a PIN set (4 to 6 digits).
- Needs the Teryx **stopped** (known speed under 0.5 km/h, or key off), the **park brake on**
  (`in.park`) and nothing moving (4WD, diff, tray, winch). Otherwise it says why and stays
  unlocked.

### While locked

| Thing | What happens |
|---|---|
| Drive | Drive inhibit asked for. **See "The gap" below.** In the simulator the throttle does nothing |
| 4WD / diff | Refused. Not done later by surprise after unlocking |
| Tray, winch | Refused. Winch disarmed, isolator off |
| Lights | All bars, interior and rear pods off. Trailer brake lights still follow the brake pedal |
| Settings (`0x704`) | Refused (ack status 3 "locked") |
| Firmware update (`0x71F`) | Refused |
| Accessory relay, power hold | Unchanged, so the Pi can still boot and show the lock screen |

The dash shows a full-screen lock with a keypad. The T. rex sleeps; a wrong PIN wakes it.

### Wrong tries

- 5 wrong tries in a row, then a **30 s** wait. Each wrong try after that doubles it, up to
  **15 minutes**. The right PIN is refused during a wait and doesn't count.
- The count is kept over power cuts, and the wait starts over after a reboot, so pulling the
  power doesn't skip it.
- With this limit, guessing a 4 digit PIN takes about 50 days of non-stop tries on average
  (5,000 guesses, 15 min apart). 6 digits is
  better if you want it.

### Changing the PIN, turning it off

Only while unlocked, and only within 60 s of typing the current PIN (the dash asks for it).
Setting a new PIN also makes a new recovery code.

## Recovery: forgot the PIN

1. **Recovery code (normal way).** When you set a PIN the dash shows an 8 digit recovery code
   once. Write it down and keep it somewhere other than the Teryx. Type it on the lock screen
   instead of the PIN: it unlocks once and wipes both the PIN and the code, so you set a new
   PIN straight after. It counts as a try, same as a PIN.
2. **Workshop reset (lost the code too).** Needs the control box opened, so it can't be done from
   the dash or over Wi-Fi.
   - Plug a 3.3 V USB serial adaptor into the control box debug header (Pico GP0 TX, GP1 RX,
     GND), 115200 baud.
   - Key on, park brake on.
   - Type `LOCK RESET` and press Enter. It answers `lock: wiped and unlocked`.
   - On the host build: `control-box-host --lock-reset`.
3. **Last resort:** erase the Pico's flash (hold BOOTSEL, `picotool erase`, then reflash). That
   also wipes the control box settings, so they need sending again from the dash.

Nothing here can be done by the dash on its own, on purpose.

## The gap: actually stopping it driving

The Pico sets `drive_inhibit` (firmware `cb_out_t.drive_inhibit`, `0x716` flag bit 2) the whole
time it's locked, but **nothing tells the Shinegle yet**, because its CAN isn't decoded. Until
then the lock blocks everything the control box runs (4WD, diff, tray, winch, lights) and the
simulator honours drive inhibit, but **on the real Teryx the motor would still drive.**

Ways to close it, best first:

| Way | Notes |
|---|---|
| **A. CAN command** | If the Shinegle takes a "disable drive" or "inhibit" command on CAN, the Pico sends it. Find out in the decode session (`docs/shinegle-decode.md`). No wiring |
| **B. Relay on the Shinegle key switch line** | The kit has its own key switch [1]. A relay contact in that wire, opened only while locked, keeps the controller off. Use a **normally closed** contact so a dead or unplugged control box never strands you. Needs one more relay output: the 8 on the MCP23017 are all used, so add a second MCP23017 (address 0x21) on the same I2C bus |
| C. Relay on the throttle signal | Works, but an open throttle wire may throw a throttle fault on the controller. Only if A and B are out |

Honest limit: with B, someone who opens the control box and pulls its fuse gets drive back. That
is the price of never cutting drive by surprise. It is a deterrent, like a steering lock, not a
car alarm.

The rule that matters most stays: drive inhibit only ever comes on with the Teryx already stopped
and the park brake on, so it can't cut power while moving.

## Security notes

- The PIN goes from the touch screen to the dash server and over CAN as digits. Both stay inside
  the Teryx. Only a salted SHA-256 hash (512 rounds, salt new each time a PIN is set) is stored,
  never the digits. A short PIN can still be guessed from a flash dump by someone with the box
  open; the wrong-try limit is what protects it on the vehicle.
- Anyone with a shell on the Pi could send CAN frames or reflash the Pico over USB. Keep SSH on
  keys only and the Wi-Fi password private.

## Where things are

| Part | File |
|---|---|
| Rules (firmware) | `firmware/control-box/src/core/lock.c`, wiring into `controller.c` |
| Flash sector | `main_pico.c`: the sector before the settings sector |
| Rules (simulator, same answers) | `teryx/vehicle_lock.py`, used by `teryx/sim/controlbox.py` |
| CAN layouts | `teryx/canbus/messages.py` `PI_LOCK` 0x705, `PICO_LOCK` 0x716, `firmware/.../protocol.h` |
| Dash | `dash/web/js/lock.js` (lock screen, PIN pad), Settings > Vehicle lock, demo copy in `demo.js` |
| Art | `dash/web/img/dino/lock-sleep.webp`, `lock-awake.webp`, `padlock.webp` (Higgsfield, 2026-11-18) |
| Tests | `firmware/control-box/tests/test_controller.c` (lock tests), `tests/test_bus.py`, `tests/test_vehicle_lock.py` |

## Sources

1. [Shinegle 5-30 kW kits, E Smart Way](https://e-smartway.com/products/shinegle-5kw-10kw-15kw-20kw-30kw-electric-car-conversion-kit): the kit comes with a key switch, accelerator and harness.
2. [SHA-256, FIPS 180-4, NIST](https://csrc.nist.gov/pubs/fips/180-4/upd1/final): the hash written in `sha256.c`. Checked against the standard "abc" test vector in the unit tests.
