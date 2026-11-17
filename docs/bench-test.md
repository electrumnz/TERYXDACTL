# Bench test guide

Bring the system up on the bench one piece at a time, before anything goes
in the Teryx. Each stage has a pass check. Don't move on until it passes.

**You'll need:** a 12V bench supply with a current limit (or a 12V battery
with a 10A inline fuse), a multimeter, the parts from
[`io-list.md`](io-list.md), and wiring per [`wiring.md`](wiring.md).

Set the bench supply's current limit **low** (1A) for every stage, and only
raise it for the stage that needs more.

---

## Stage 0: everything on the laptop first

No hardware at all. Proves the software before you wire anything.

```bash
pip install -e .
python -m teryx run --scenario trail
```

Open http://localhost:8080/ and the sim page at /sim.

- [ ] Dash shows speed, battery and temps moving
- [ ] Tapping 4WD, diff, lights, tray and winch on the dash changes them on the sim page
- [ ] Driving on the sim page (1 km/h or more), then asking for 4WD gets refused with a reason. Above 15 km/h, adding diff lock is refused but OPEN still works

Then run the real firmware logic against the sim (see
[`firmware/control-box/README.md`](../firmware/control-box/README.md)):

```bash
./build-host/control-box-host --bus udp
python -m teryx run --bus udp --no-controlbox
```

- [ ] Same checks pass with the host-built firmware playing the Pico

## Stage 1: Pi 5 on its own

1. Flash Raspberry Pi OS (64-bit, desktop) to the SD card or SSD. Set up your
   wifi in the imager, not in this repo.
2. Plug in the screen (HDMI + USB) and a 5V 5A supply.
3. Run the installer: `sudo bash scripts/pi-setup.sh` (see the Pi section
   of the [README](../README.md)).
4. Reboot.

- [ ] Dash opens full screen on its own after boot
- [ ] Touch works across the whole screen, corners included
- [ ] No under-voltage warning: `vcgencmd get_throttled` prints `throttled=0x0`

## Stage 2: CAN between the Pi and a laptop (or a second Pi)

Before the Pico is involved, prove the Pi's CAN HAT works.

1. Wire the HAT's CAN H/L to a USB CAN adaptor (or the Teryx CAN sniffer from
   `firmware/can-sniffer`, with its GP15 transmit jumper fitted so it can send;
   on Linux `sudo slcand -o -s5 /dev/ttyACM0 can1 && sudo ip link set can1 up`
   makes it a normal `can1`) with 120Ω at both ends. Check 60Ω across H and L with power off.
2. On the Pi: `candump can0`. On the other end send a frame, e.g.
   `cansend can0 123#DEADBEEF`.

- [ ] The frame shows up on the other side, both directions
- [ ] `ip -details -statistics link show can0` shows no bus-off and no error growth

## Stage 3: Pico 2 on its own

1. Flash the firmware: hold BOOTSEL, plug the Pico into the Pi's USB, then
   `tools/pi/flash-control-box.sh teryx_control_box.uf2` (or drag the `.uf2`
   onto the drive). The `.uf2` comes from the GitHub Actions build.
2. Wire only the MCP2515 module to the Pico (wiring.md, "Pico 2 to its boards").
   Check the crystal on the module: if it says 16.000, change
   `MCP2515_OSC_HZ` to 16 MHz and rebuild.
3. Join the MCP2515 to the CAN bus with the Pi.

- [ ] `python -m teryx monitor --bus socketcan:can0` on the Pi shows `0x710` heartbeats from the Pico at 10 Hz
- [ ] The dash's status dot says "Control box online"
- [ ] Unplug the Pi's CAN: within half a second the Pico reports "dash link lost" when it comes back

## Stage 4: inputs

Wire the MCP23017 and the opto board. Feed each opto input from the bench
12V through a switch or a jumper wire.

- [ ] Each input (key, brake, reverse, tray limits, winch remote, park) lights up on the dash when its 12V is applied, and only that one
- [ ] Unplugging a tray limit switch shows it as "at limit" (normally closed check)
- [ ] ADS1115 A1 reads within 0.2V of your multimeter on the 12V supply

## Stage 5: relays (no loads yet)

Wire the relay board, JD-VCC from the 5V buck. No loads on the contacts yet.

- [ ] Each relay clicks when its button is pressed on the dash, and only that one. If they're all on when they should be off, flip settings key 18 (active-low)
- [ ] Turning the key input off: the Pico tells the Pi to shut down, the Pi powers off, then relay 8 lets go (within 30 s)
- [ ] Winch relays: "in" and "out" can never both be on. Try pressing both on the dash
- [ ] Winch relays don't work unless the winch is armed and speed is 0 on the sim

## Stage 6: actuators

Raise the bench supply limit to 5A for the 50mm actuators, 10A for the tray.
Run each actuator **loose on the bench** first, not connected to anything.

For each one:
- [ ] Moves the right way when asked. If not, change its `_DIR` setting in the firmware, not the wires
- [ ] Stops at the end of its travel on its own (current rise or timeout)
- [ ] Unplugging the Pi's CAN mid-move stops it within half a second
- [ ] Current reading on the dash is roughly what the bench supply shows

Diff actuator extras:
- [ ] Pot reading goes smoothly from one end to the other with no jumps
- [ ] Calibrate: note the raw reading fully in and fully out, set settings keys 14 and 15
- [ ] Ask for 25 %, 50 %, 75 %: it stops within a few percent each time

Tray extras:
- [ ] Time a full lift. The 20 s tray timeout must be longer than this
- [ ] Hold-to-run: letting go of the button on the dash stops it within 0.3 s

## Stage 7: lights

Test **one** light bar first with a cheap 12V PWM dimmer, before wiring the
MOSFET board.

- [ ] Smooth dimming, no flicker or buzz → keep PWM on in settings
- [ ] Flickers, buzzes or ignores it → set that light to on/off in settings

Then wire the MOSFET board and all the bars (bench supply up to 10A, or use
a battery).

- [ ] Each bar comes on alone, at the brightness set on the dash
- [ ] Effects (strobe, chase) run, and keep running if the Pi's CAN is unplugged
- [ ] MOSFET board stays cool to the touch after 10 minutes with all bars full on
- [ ] Reverse on: rear pods come on and the camera shows on the dash

## Stage 8: the whole lot

Everything connected, run for an hour on the bench.

- [ ] No resets: the Pico's "watchdog reset" fault never appears
- [ ] Pi temperature stays under 70 °C (`vcgencmd measure_temp`)
- [ ] Key off → clean shutdown → key on → everything back to the same state
- [ ] An OTA update of the dash works, and a broken dash release rolls back on its own
- [ ] An OTA update of the Pico from the Pi works (automatic Pico rollback isn't built yet, so keep the last good `.uf2` handy)

Once all of these pass, it's ready to go in the Teryx. Step 4 of the plan
(recording and decoding the Shinegle CAN) happens there.
