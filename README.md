# Teryx OS

Custom dash and control system for an EV-converted 2013 Kawasaki Teryx
(Shinegle 7.5 kW kit). A Raspberry Pi 5 runs the 10.1" touch dash, a Pico 2
control box does the safety-critical switching, and they talk over CAN.

This repo currently holds the **test bench**: a simulator that fakes the
Shinegle motor controller and the control box, so the dash can be built and
tested on a laptop or the Pi with no Teryx attached.

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

## What's in here

| Path | What it is |
|---|---|
| `teryx/canbus/` | CAN messages, codec, bus drivers. `messages.py` is our Pi/Pico protocol, `shinegle.py` is the (placeholder) Shinegle adapter |
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
