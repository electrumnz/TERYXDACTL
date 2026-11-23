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

Inputs: `key`, `brake`, `park`, `fnr`, `throttle`, `backup_lights`, `estop`,
`trailer`, `winch_switch`, `winch_remote`, `winch_breaker`, `battery`,
`pull_fuse`. Read-backs: `lamp`, `trailer_pin`, `relay`, `powered`, `volts`,
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
| Shinegle | The fake controller in `teryx/sim`, driven by the key, F-N-R, throttle and brake wires |
| Pi | Powered from its buck, shuts itself down 6 s after the Pico asks |

Not simulated, each with a reason in `teryx/rig/models.py` (`NOT_SIMULATED`):
the 72 V side, cameras, audio, CarPlay, the AI HAT+ 2 placeholder, and the RC
box chips until the RC box has firmware. A test fails if a new device is added
to the wiring without a model or a reason.

## What the tests cover

`tests/test_system_sim.py`: boot with no errors, every light (dimming, brake and
reverse, trailer plug pins), brake and backup lights with the control box dead,
4WD and diff, tray up to its limit and a broken limit wire, winch from the dash
and the hand switches, key-off power hold and Pi shutdown, vehicle lock, drive
and E-stop, power steering CAN frames, a low 12 V battery, a lost logic ground,
and a deliberate wiring mistake that the sim has to catch.

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
