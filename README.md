# Teryx OS

Custom dash and control system for an EV-converted 2013 Kawasaki Teryx
(Shinegle 7.5 kW kit). A Raspberry Pi 5 runs the 10.1" touch dash, a Pico 2
control box does the safety-critical switching, and they talk over CAN.

| Part | Where | Start here |
|---|---|---|
| Plan, IO list, wiring | `docs/` | [`io-list.md`](docs/io-list.md), [`wiring.md`](docs/wiring.md), [`bench-test.md`](docs/bench-test.md) |
| Test bench (fake Shinegle + control box) | `teryx/` | [`docs/TEST_ENVIRONMENT.md`](docs/TEST_ENVIRONMENT.md) |
| Dash touch UI (Pi 5) | `dash/` | [`dash/README.md`](dash/README.md) |
| Control box firmware (Pico 2) | `firmware/control-box/` | [`firmware/control-box/README.md`](firmware/control-box/README.md) |
| Sound, music, Bluetooth phone, CarPlay / Android Auto | `dash/` | [`docs/audio.md`](docs/audio.md) |
| 3D-printed screen mount, sun hood and boxes | `cad/` | [`cad/README.md`](cad/README.md), [`cad/MEASURING.md`](cad/MEASURING.md) |
| Decoding the Shinegle CAN bus (sniffer + tools) | `firmware/can-sniffer/`, `teryx/decode/` | [`docs/shinegle-decode.md`](docs/shinegle-decode.md) |
| Ideas and open-source projects to learn from | `docs/` | [`inspiration.md`](docs/inspiration.md) |

Everything runs on a laptop with no Teryx attached, using the simulator.

## Quick start (any laptop: Windows, Mac or Linux)

You need Python 3.10 or newer.

```bash
git clone https://github.com/electrumnz/TERYXDACTL.git
cd TERYXDACTL
python -m venv .venv
# Windows: .venv\Scripts\activate     Mac/Linux: source .venv/bin/activate
pip install -e .
python -m teryx run --scenario trail
```

Then open:

- **http://localhost:8080/** for the test screen (live data, tap things)
- **http://localhost:8080/sim** for the sim panel (scenarios, throttle, faults)
- **http://localhost:8080/virtual** for the 3D virtual Teryx

A phone or tablet on the same wifi can open them too, using the laptop's IP
address instead of `localhost`.

## Setting up the Pi 5

On a fresh Raspberry Pi OS (64-bit, desktop) with wifi set up in Raspberry Pi
Imager:

```bash
git clone https://github.com/electrumnz/TERYXDACTL.git
cd TERYXDACTL
sudo bash scripts/pi-setup.sh --can-osc 16000000   # use the number on your CAN HAT's crystal
sudo reboot
```

It installs the dash, turns on the CAN HAT, brings `can0` up at boot, and opens
the dash full screen. Run `sudo bash scripts/pi-setup.sh --help` for the other
options. Then work through [`docs/bench-test.md`](docs/bench-test.md).

## What's in here

| Path | What it is |
|---|---|
| `teryx/canbus/` | CAN messages, codec, bus drivers, .dbc reader. `messages.py` is our Pi/Pico protocol; the Shinegle layout is `shinegle.dbc` (placeholder until decoded), loaded by `shinegle.py` |
| `teryx/decode/` | Shinegle decoding kit: guided capture, analysis, draft .dbc, check, install |
| `teryx/sim/` | Fake Shinegle with simple physics, fake Pico control box with all the safety rules, scenarios |
| `teryx/dash/` | Dash gateway (CAN to live state) and the web server the UI talks to |
| `teryx/web/test/` | Basic test screen that proves the pipeline works. The real dash UI is built separately |
| `teryx/web/sim/` | Sim panel |
| `docs/TEST_ENVIRONMENT.md` | How the bench works, run modes, scenarios, swapping in real CAN |
| `docs/DASH_API.md` | The websocket feed and requests the dash UI uses |
| `docs/CAN_PROTOCOL.md` | Every CAN frame and bit (generated, don't edit by hand) |
| `docs/teryx.dbc` | Same, as a DBC file for SavvyCAN / cantools |
| `tests/` | `python -m pytest` |

## Licence

MIT. Keep anything personal (wifi details, keys, location logs) out of the
repo. Local config and CAN captures are gitignored.
