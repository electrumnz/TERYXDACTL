# Decoding the Shinegle CAN bus: step by step

> **From the controller manual (2026-11-18):** CAN is *optional* on the
> SG1202, and when fitted it's CANopen with 29-bit (extended) IDs. If the bus
> is silent, check Sam's controller actually has CAN before blaming the
> wiring. The programmer uses a separate serial (SCI) link on J1-28/29. See
> [`shinegle-controller.md`](shinegle-controller.md).

Shinegle don't publish their CAN layout, so we work it out by listening. You
plug a small sniffer into the Shinegle's CAN wires, do one thing at a time
(brake, throttle, forward/reverse ...) while the laptop records, and the tools
work out which bytes changed with what you did. The result is one file,
`teryx/canbus/shinegle.dbc`, and the whole of Teryx OS (dash, sim, tests) uses
it from then on.

Allow about an hour for the first go. Nothing here sends anything on the
Shinegle bus, so it can't upset the controller.

```
 Shinegle controller ── CAN H/L ──┬── Shinegle dash
                                  │
                         MCP2515 module ── Pico 2 (sniffer) ── USB ── laptop or Pi
```

## 1. What you need

- A spare **Pico 2** and an **MCP2515 CAN module** (the same type as the control
  box uses), plus 7 jumper wires.
- A USB cable for the Pico, and a laptop (Windows, Mac or Linux) or the Pi 5.
- The **Shinegle dash** and **Shinegle programmer**, both plugged in as normal.
- **Stands** to get the driven wheels off the ground for the throttle steps.
- Read the number printed on the MCP2515 module's silver crystal: **8.000** or
  **16.000** (MHz). You need it in step 2.

## 2. Flash the sniffer firmware

1. On GitHub, open **Actions**, pick **CAN sniffer firmware**, open the latest
   green run and download the artifact that matches your crystal:
   `teryx_can_sniffer-8000000` or `teryx_can_sniffer-16000000`. Unzip it.
2. Hold the **BOOTSEL** button on the Pico 2 while you plug it into USB. A drive
   called `RP2350` appears.
3. Drag the `.uf2` file onto that drive. The Pico restarts by itself.
4. The Pico's LED now **blinks slowly**. That means "ready, waiting for the
   laptop".

## 3. Wire the sniffer

Same pins as the control box ([wiring.md](wiring.md) has the full notes):

| Pico 2 | MCP2515 module |
|---|---|
| GP2 | SCK |
| GP3 | SI (MOSI) |
| GP4 | SO (MISO) |
| GP5 | CS |
| GP6 | INT |
| 3V3(OUT) | VCC (for a 5V TJA1050 board, follow the power note in wiring.md) |
| GND | GND |

- **Leave GP15 unconnected.** GP15 to GND is the "transmit" jumper. Without it
  the sniffer is listen-only and physically can't send, however it's asked.
- **Take the 120 ohm jumper off the MCP2515 module** (usually marked J1). The
  Shinegle bus already has its terminators; a third one can cause errors.

Connecting to the Shinegle's CAN wires: find CAN H and CAN L at the Shinegle
dash plug (back-probe the connector or use a T-piece, don't cut anything). CAN
H on the module to CAN H, L to L. Keep the wires twisted and short-ish.

## 4. Set up the laptop

You need Python 3.10 or newer.

```bash
git clone https://github.com/electrumnz/TERYXDACTL.git
cd TERYXDACTL
python -m venv .venv
# Windows: .venv\Scripts\activate     Mac/Linux: source .venv/bin/activate
pip install -e .
```

Find the sniffer's port:

| Computer | Port looks like | Where to look |
|---|---|---|
| Windows | `COM5` | Device Manager, "Ports (COM & LPT)" |
| Linux / Pi | `/dev/ttyACM0` | `ls /dev/ttyACM*` |
| Mac | `/dev/cu.usbmodem1101` | `ls /dev/cu.usbmodem*` |

Below, swap `PORT` for yours.

## 5. Practise first (no Teryx needed)

```bash
python -m teryx decode demo captures/demo
python -m teryx decode analyse captures/demo
```

This makes a pretend capture from a made-up controller and decodes it. Open
`captures/demo/report.md` to see what a good result looks like. It should find
all 14 signals.

## 6. Find the bus speed

Key on. Then:

```bash
python -m teryx decode bitrate --port PORT
```

It listens at each common speed for 2 seconds and tells you which one heard
frames (most likely 250k or 500k). Use that number below. If nothing is heard
at any speed: check H and L aren't swapped, the key is on, and the crystal
firmware matches your module.

## 7. Record, following the guided procedure

```bash
python -m teryx decode capture --bus slcan:PORT@250000
```

(Use your bus speed in place of 250000. `python -m teryx decode steps` prints
the whole procedure if you want to read it first.)

The tool walks you through each step on screen. For each one:

1. Read what to do. Press **Enter** to start the step.
2. When it asks "Enter the moment it's: FORWARD", press Enter **at the moment**
   you make that change. These marks are how the analysis lines up what you did
   with the bytes that moved, so try to be quick.
3. When it asks for a reading ("Shinegle dash battery volts?"), type the number
   the Shinegle dash or programmer shows and press Enter. Press Enter on its
   own if the dash doesn't show that value.

You can also type these at any prompt:

| Type | What it does |
|---|---|
| `r batt_v 74.2` | Save a reading at any time |
| `n dash shows E-03` | Save a note |
| `s` | Skip this step |
| `q` | Finish and save |

The steps, in order: key off, key on, ready, **Shinegle dash unplugged** (tells
us who sends what), brake, forward/neutral/reverse, drive modes, slow throttle
sweeps, throttle holds with readings, regen, reverse, an optional slow drive,
charging, the programmer, a throttle fault, key off. Optional ones can be skipped.

**Safety for the throttle steps:** driven wheels off the ground on stands,
transfer case in 2WD, nobody near the wheels. For the throttle fault step, only
unplug the throttle with the key on and **not** in ready.

Everything is saved as you go into `captures/<date_time>/` (`bus.log` plus
`steps.json`). That folder is kept out of git. If something goes wrong, just
run the capture again; you can do single steps with `--steps brake,direction`.

## 8. Analyse

```bash
python -m teryx decode analyse captures/<date_time>
```

It writes three files into the capture folder:

- `report.md`: what it found, how sure it is, and runner-up guesses.
- `shinegle-draft.dbc`: the layout as a .dbc using the Teryx names.
- `candidates.json`: every guess with its score (for Claude, next round).

"Low" confidence lines are worth a second look. Values read once (battery %,
temperatures) are the usual ones, because a single reading can match more than
one byte. Reading them again in another step (e.g. after charging) firms them up.

## 9. Check it

```bash
python -m teryx decode check captures/<date_time>/shinegle-draft.dbc captures/<date_time>
```

This decodes the whole capture with the draft, the same way the dash will, and
puts every reading you typed next to the decoded value at that moment. If they
match, the draft is right. Each step also shows what every value did (for
example, direction should go forward > neutral > reverse in the direction step).

Want to look for yourself? Open the capture in **SavvyCAN** (File, Load Log
File, `bus.log` is "candump" format), load the draft .dbc, and graph any signal.
You can also connect SavvyCAN straight to the sniffer: Connection, Add New
Device Connection, Serial (GVRET or LAWICEL), pick the port.

## 10. Install it

```bash
python -m teryx decode install captures/<date_time>/shinegle-draft.dbc
python -m teryx canmap
python -m pytest
```

That copies the draft to `teryx/canbus/shinegle.dbc` (the one file Teryx OS
loads) and regenerates `docs/CAN_PROTOCOL.md`. Then try it on the bench:

```bash
python -m teryx replay captures/<date_time>/bus.log --bus udp --loop
python -m teryx dash --bus udp        # open http://localhost:8080/
```

**One test will fail on purpose** if the real speed frame isn't where the Pico
firmware expects it (`test_pico_firmware_reads_the_installed_shinegle_speed_frame`).
The control box uses the Shinegle's speed for its safety interlocks (4WD, diff
lock, tray, winch), so its firmware has to be updated to read the real frame
before it goes on the vehicle. Ask Claude to do that; the install command prints
exactly what needs changing.

## 11. Send it to Claude

Commit nothing from `captures/` by hand. Instead, zip the capture folder and drop
it into the project chat (or project files) and say "decode this". Claude can
re-run the analysis, look at the runner-up guesses, and open a PR with the
installed .dbc and any firmware change. The capture only holds CAN frames, your
readings and notes, so there's nothing personal in it.

## If the controller goes quiet without its dash

If the report says **"Everything went quiet with the Shinegle dash unplugged"**,
the controller only talks when its dash asks (some Kelly and Votol controllers
work like this). The report lists the dash's frames. The next step is to have the
Pi send those same frames instead of the Shinegle dash. That needs the sniffer's
**GP15 to GND** transmit jumper and some care, so talk to Claude before doing it.

Also worth knowing: while the Shinegle dash is unplugged, nothing on the bus
acknowledges the controller's frames (the sniffer only listens). Some
controllers then repeat frames or flag a comms fault. That's expected for those
15 seconds and goes away when the dash is plugged back in.

## Troubleshooting

| Problem | Try |
|---|---|
| LED blinks slowly and nothing happens | The laptop hasn't opened the port. Check the port name; close SavvyCAN or anything else using it |
| LED blinks fast | The Pico can't talk to the MCP2515. Check the 5 SPI wires and power |
| LED steady but no frames | Wrong bus speed, CAN H/L swapped, key off, or 8/16 MHz firmware doesn't match the crystal |
| `could not open port` on Linux | `sudo usermod -aG dialout $USER`, then log out and in |
| Frames, but `bitrate` says lots at two speeds | Pick the one with more ids. A wrong speed usually gives nothing at all |
| `report.md` says "not found" for something | Redo just that step with `--steps <id>` (ids from `decode steps`) and analyse both captures |

## How the pieces fit

| Piece | Where |
|---|---|
| Sniffer firmware (Pico 2) | [`firmware/can-sniffer/`](../firmware/can-sniffer/README.md) |
| Procedure, capture, analysis, check, install | `teryx/decode/` (`python -m teryx decode --help`) |
| The Shinegle layout everything uses | `teryx/canbus/shinegle.dbc`, loaded by `teryx/canbus/shinegle.py` |
| Signal names the dash understands | top of `teryx/canbus/shinegle.py` |
