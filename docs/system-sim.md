# System sim: the whole Teryx on a PC

The system sim runs the **real control box firmware** inside the **whole-vehicle
wiring diagram** ([`config/wiring.yaml`](../config/wiring.yaml)), with the fake
Shinegle and the real dash gateway on one virtual CAN bus. You flick a switch in
Python, and it goes through the wires, fuses, optos, the MCP23017, the Pico
code, CAN, and back out through the driver boards to a lamp or a motor. Tests
then check the outputs.

If a wire, a fuse, a ground or a pin number is wrong in the diagram or in the
firmware, a test fails. That's the point: the SLD gets tested, not just drawn.

```
 switch ─ wire ─ fuse ─ opto ─ MCP23017 ─┐                       ┌─ Fake Shinegle
                                         ▼                       │  (teryx/sim)
                           real main_pico.c + drivers ── CAN ────┤
                           (compiled for the PC)                 │
                                         │                       └─ Dash gateway
 lamp ─ fuse ─ BTS7960 ─ PCA9685 / GP ◄──┘                          (teryx/dash)
```

## On your phone: the simulator page

**<https://electrumnz.github.io/TERYXDACTL/rig/>**

The real dash screen, with every button working, sitting on top of the whole sim:
the real control box firmware (built for the browser from the same C files with
Emscripten), the wiring diagram, the Shinegle and the power steering. Next to the
screen is a panel that stands in for your hands and feet: the key, park brake,
brake pedal, F-N-R, throttle, steering wheel, E-stop, winch switches, trailer plug,
the 12 V battery, Shinegle faults, steering faults, and every fuse to pull.

Press a light bar button on the dash and it goes dash -> Pi gateway -> CAN -> real
firmware -> PCA9685 -> MOSFET -> fuse -> lamp, and the lamp lights up in the panel.
Pull fuse FB.F1 and bars 1 and 4 go dark while the dash still thinks they're on.

The first load downloads Python for the browser (Pyodide, about 10 MB, from the
jsDelivr CDN); after that it's cached. It runs in real time on a laptop and on most
phones; if a phone can't keep up the status pill says "Running at 70% speed".
Turn the phone sideways for a bigger screen.

On the laptop, with no GitHub Pages: `python -m teryx rig-web` then open
<http://localhost:8090/rig/>.

How it fits together (all in `dash/web/rig/`):

| File | What it does |
|---|---|
| `index.html`, `rig.js`, `rig.css` | The page: dash in an iframe (`../index.html?rig=1`), the panel |
| `worker.js` | Web worker: runs the sim in real time off the page's main thread |
| `rig-core.js` | Starts Pyodide, unpacks the Python, makes a `WebRig` |
| `rigfw.js` | The calls `teryx/rig/webfw.py` makes into the firmware |
| `pico.js`, `pico.wasm` | The firmware, built by `python tools/build_rig_web.py --wasm` (kept in git) |
| `teryx-py.zip` | `teryx/` + `config/`, built by `python tools/build_rig_web.py` (not in git) |

The dash's `js/link.js` sees `?rig` and swaps its websocket for messages to the page,
in the same format (`docs/DASH_API.md`). `teryx/rig/web.py` (`WebRig`) answers them,
and is the same code on the PC (`tests/test_rig_web.py`) and in the browser.
`teryx/rig/web_can.py` stands in for python-can in the browser.

If you change the firmware, rebuild the browser copy:
`python tools/build_rig_web.py --wasm` (needs [Emscripten](https://emscripten.org) 6.0.13).
`tests/test_rig_web.py` fails until you do, and CI (`.github/workflows/rig-web.yml`)
rebuilds it and runs the whole sim in Pyodide under Node.

## Running it

Linux or macOS with a C compiler (`cc`). On Windows the sim tests skip.

```
python -m pytest tests/test_system_sim.py -v
```

From Python:

```python
from teryx.rig import System

s = System()
s.key(True); s.park(True)
s.run(4)                        # boot, 4WD homes
s.dash.request("light.front_1", 255)   # what the dash slider sends
s.run(0.5)
print(s.lamp("LB1"))            # 0..1, PWM duty at the light bar
s.pull_fuse("FB.F1")            # or cut a wire by id: s.pull_fuse("G39")
s.battery(10.5)                 # flat 12 V battery
print(s.report())               # every device model's state
s.close()
```

Inputs: `key`, `brake`, `park`, `fnr`, `throttle`, `steer` (Nm on the wheel), `backup_lights`, `estop`,
`trailer`, `winch_switch`, `winch_remote`, `winch_breaker`, `battery`,
`pull_fuse`. Read-backs: `lamp`, `trailer_pin`, `relay`, `powered`, `volts`, `eps`,
`level`, `actuator`, `ground_ok`, `pi_on`, `shinegle_on`, `report`, and the dash
snapshot (`s.dash.snapshot()`).

## What's real and what's modelled

| Part | In the sim |
|---|---|
| Control box firmware | **Real.** `firmware/control-box/src/pico/main_pico.c` and the MCP2515, MCP23017, ADS1115 and PCA9685 drivers, compiled for the PC against a stand-in Pico SDK (`firmware/control-box/src/rig/`) |
| Dash gateway | **Real.** `teryx/dash/gateway.py`, on a virtual clock |
| Wiring | **Real.** Every device, pin and wire in `config/wiring.yaml`, as drawn |
| I2C and SPI chips | Register-level models: MCP23017, ADS1115, PCA9685, MCP2515 (bit rate worked out from CNF1-3, frames only ACK'd when something is listening) |
| Pico pins | PWM slices, ADC, watchdog, flash, UART |
| Boards and loads | Switch-level models: battery, DC-DC, bucks, fuse box, optos, relay boards, BTS7960 (with current sense), actuators (travel time, end stops, can jam), limit switches, lamps, winch solenoid and motor, EPS ECU, trailer |
| Shinegle | `models.Shinegle` reads the key (KSI), F-N-R and the throttle pedal off its own pins; the fake controller in `teryx/sim` drives and sends the CAN frames. **Assumed**, see below |
| Power steering | `models.EpsEcu` + `models.TorqueSensor`: the Aqua ECU wakes on IG, hears the Pico's speed frames, gives assist, turns the column, and answers on the steering CAN bus. **Assumed**, see below |
| Pi | Powered from its buck, shuts itself down 6 s after the Pico asks |

Not simulated, each with a reason in `teryx/rig/models.py` (`NOT_SIMULATED`):
the 72 V side, cameras, audio, CarPlay, the AI HAT+ 2 placeholder, and the RC
box chips until the RC box has firmware. A test fails if a new device is added
to the wiring without a model or a reason.

## Guesses until the bench test

Sam asked for the sim to work end to end now, on sensible guesses, and to swap them
for the real thing once the bench sniffing is done. Every guess is a named constant
marked `ASSUMED`, so a bench result is a one-line change and the tests show what moved.

**Shinegle SG1202** (`teryx/rig/models.py`, top of the Shinegle section, and `teryx/canbus/shinegle.dbc`)

| Guess | Value | Swap for |
|---|---|---|
| CAN layout | `shinegle.dbc` PLACEHOLDER: 0x180 motor, 0x181 battery, 0x182 temps, 0x183 faults | The `.dbc` from the decode kit (`python -m teryx decode`, docs/shinegle-decode.md) |
| Throttle start (PedSet) | 0.8 V | Read PedSet off the SG1810 programmer |
| Full throttle | 4.2 V | Programmer / measure the pedal |
| Throttle fault | wiper over 4.8 V | Programmer manual |
| High pedal disable (HPD) | on | Programmer "HPD" setting |

**Aqua EPS column** (`teryx/rig/models.py`, the power steering section, and `teryx/eps_toyota.py`)

| Guess | Value | Swap for |
|---|---|---|
| Frames from the Pico | 0x2C4 engine running + 0x0B4 speed, 20 ms, 500 kbit/s (Prius gen 2) | Sniff a running Aqua's OBD port |
| Frames back | 0x260 torque + angle (50 Hz), 0x262 status (25 Hz), opendbc layouts | Same sniff |
| Driver torque scale | 0.01 Nm per bit in 0x260 | Bench: turn the wheel with a known force |
| Torque sensor | 2.5 V hands off, 0.25 V per Nm, both outputs alike | Meter on the sensor plug |
| Sensor fault | outputs more than 0.4 V apart, or outside 0.5-4.5 V | Bench: pull one wire |
| Assist | 3x up to 16.3 km/h, 1.2x at 60, 0.6x from 100 | Feel on the bench |
| Limp mode | 1x assist after 1 s without frames | Bench: stop the frames |
| Column | 450 deg each way, 6 Nm to start turning, self-centres when rolling | The real Teryx |

The panel on the simulator page can make the ECU go quiet (wrong frames guessed) or
pull a torque sensor wire, so you can see what the dash does when the guesses are wrong.

## What the tests cover

`tests/test_system_sim.py`: boot with no errors, every light (dimming, brake and
reverse, trailer plug pins), brake and backup lights with the control box dead,
4WD and diff, tray up to its limit and a broken limit wire, winch from the dash
and the hand switches, key-off power hold and Pi shutdown, vehicle lock, drive
and E-stop, power steering CAN frames, a low 12 V battery, a lost logic ground,
and a deliberate wiring mistake that the sim has to catch.

`tests/test_system_sim_drive.py`: steering assist and the Pico hearing the ECU,
assist dropping with speed, a heavy manual column with the key off, limp mode, a
quiet ECU, a torque sensor wire off, high pedal disable, a cut throttle wire, and a
Shinegle fault reaching the dash.

`tests/test_rig_web.py`: the simulator page's Python side (dash buttons through the
real firmware, the panel, pulling fuses), the python-can stand-in, the bundle, and
that `pico.wasm` matches the firmware source.

CI runs them on Linux and macOS (`.github/workflows/test.yml`). On Linux they
must run, not skip (`TERYX_RIG_REQUIRED`).

## Problems it found in the diagram (Nov 2026)

1. **Logic boards had no ground wire.** The MCP23017s, ADS1115, PCA9685, CAN
   boards, opto board and all nine BTS7960s had a GND pin but no wire to the
   Pico ground. Added G39 to G60.
2. **Winch remote tap in the wrong place.** The input that tells the Pico "the
   hand remote is pulling the winch" was on the solenoid coil, which the Pico's
   own winch relay also drives. So the Pico saw its own pull as the remote and
   stopped it. The remote now has its own wires (REM_IN, REM_OUT) through
   diodes into the coil, and the Pico reads those.

## Why our own, and not an off-the-shelf simulator

We looked at the main options for running Pico 2 code in a simulator:

| Tool | Licence | Pico 2 (RP2350) | MCP2515 / CAN | Notes |
|---|---|---|---|---|
| [Renode](https://github.com/renode/renode) | MIT | No | No | RP2040 only through a [community add-on](https://github.com/matgla/Renode_RP2040) that's unfinished (no PWM) |
| [Wokwi](https://docs.wokwi.com/parts/board-pi-pico-2) | Closed, cloud | Yes | No (would need a [custom chip](https://docs.wokwi.com/chips-api/getting-started)) | CI needs a paid token past [50 minutes a month](https://wokwi.com/pricing), [wokwi-cli](https://github.com/wokwi/wokwi-cli) |
| Our own harness | MIT, in this repo | Runs the same C on the PC | Modelled | Reads the wiring diagram directly, free in CI |

Neither tool knows about our wiring diagram, and both would mean drawing the
vehicle a second time. Running the firmware's C on the PC against a stand-in SDK
tests the same logic, uses the SLD as the single source, and costs nothing in
CI. No GPL code is used.

## Limits

- It's switch level, not SPICE. A net is high, low, PWM or floating. No
  current, voltage drop, or anything inside a PWM cycle. Use it for "does this
  lamp light, does this relay click, does the Pico see this switch".
- The firmware runs on the PC, so RP2350 timing, interrupts and real peripheral
  quirks aren't tested. The bench test ([bench-test.md](bench-test.md)) still
  has to be done on the real boards.
- Device models are written from datasheets and our notes. Where real hardware
  behaves differently, fix the model.
