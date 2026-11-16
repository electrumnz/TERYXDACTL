# Teryx dash UI

The touch screen dash for the Teryx: a rugged, high-contrast take on a Tesla-style screen,
built for a 10.1" 1280x800 touch screen on a Raspberry Pi 5, used with gloves on a bumpy track.

**The Pi only asks. The control box (Pico) decides.** Every button sends a request; what the
screen shows is what the control box reports back. If the control box says no (too fast,
not stopped, not armed), the dash says why in plain words.

## Screens

| Screen | What it does |
|---|---|
| Drive | Speed, gear (R/N/D), power and regen bar, battery %, pack volts/amps/temp, 12V, motor and controller temps, throttle, mode, odometer, tilt (if an IMU is fitted), a top-down view showing 2WD/4WD, diff lock and lights |
| 4WD | 2WD/4WD switch and diff lock 0-100% (slider plus Open/25/50/75/Lock). Shows the target and where the actuator actually is, and locks out above the speed limits |
| Lights | 4 front bars, interior bar, rear pods (Off / Auto in reverse / On), trailer status. Each bar is dimmable or on/off only (set in Settings). Presets (All on/off, Trail, Work, Spot) and effects (Steady, Breathe, Strobe, Chase, Outside pair, Inside pair) |
| Winch | Slide to arm (so a knee can't arm it), then hold IN or OUT. Lifting your finger stops it. Shows checks and the auto-disarm countdown |
| Tray | Hold UP or DOWN. Only when stopped. Shows limit switches, current and position |
| Camera | Reverse camera with guide lines and mirror. Pops up on its own in reverse and goes back 3 s after |
| Settings | Display (night/day/auto, units), lights setup, camera, control box safety limits, diff pot calibration, faults, updates (OTA), Wi-Fi, about |

Faults from the control box or motor controller show as a banner along the bottom with plain
English text, and are listed under Settings > Faults.

## Camera: USB or RCA, both work

We don't know yet which camera is fitted, so both are supported:

- **USB camera**: shows up as a video device and opens straight in the browser.
- **RCA / AHD camera**: plug it into a cheap USB AV capture dongle (UVC). It then looks
  exactly like a USB camera. The Pi 5 has no analogue video input, so a dongle is needed.
- **Fallback**: Settings > Camera > Server stream uses ffmpeg on the Pi to serve
  `/api/camera.mjpg`, in case the browser can't open the device.

## Running it

### On a laptop with the simulator (no Teryx needed)

The simulator and gateway are in the `teryx` package (test environment work).

```bash
pip install -r requirements.txt
PYTHONPATH=dash/server python -m teryx run --scenario trail --ui dash/web
# open http://localhost:8080   (sim controls at http://localhost:8080/sim)
```

Scenarios: `idle`, `trail`, `reversing`, `low_battery`, `hill_climb`, `faults`,
`actuator_faults`, `comms_loss`, `key_off`, `manual`.

### Demo mode (just a browser)

Open `dash/web/index.html?demo=drive` from any web server (for example
`python -m http.server -d dash/web`) and go to `http://localhost:8000/?demo=drive`.
A small built-in fake vehicle runs in the page. Other demos: `?demo=park`, `?demo=reverse`,
`?demo=faults`. Add `&screen=lights` (or `drivetrain`, `winch`, `tray`, `camera`, `settings`)
to open a screen straight away. Settings that need the Pi (limits, updates, Wi-Fi) say
"not available in demo mode".

### On the Pi

```bash
sudo bash dash/deploy/install-pi.sh <repo git url> v0.1.0
```

That sets up `/opt/teryx`, a Python venv, the `teryx-dash` service (server on port 8080,
CAN on `can0`), and prints the two commands to start the full screen kiosk.

## Updates over Wi-Fi (OTA)

Settings > Updates checks for new versions and installs them. Releases are git tags:
`v1.2.0` is stable, `v1.3.0-beta.1` is beta.

- Only installs when the Teryx is stopped.
- Each version is kept in its own folder; switching is an instant link swap.
- If a new version fails to start twice, it goes back to the last good one on its own.
  There's also a Roll back button.
- Control box firmware: if a release has a newer `firmware/VERSION` than the Pico reports,
  an "Update control box" button appears (only while the control box says it's parked). It runs
  `tools/pi/flash-control-box.sh`, which asks the Pico over CAN to make its outputs safe, flashes
  the release's `.uf2` with picotool, checks the new version is running and keeps the old one for
  rollback (change with `TERYX_PICO_FLASH_CMD`).

To publish an update: tag a commit (`git tag -a v0.2.0 -m "What changed"`) and push the tag.
The tag message shows on the Updates screen.

## Wi-Fi

The Updates screen uses the Pi's built-in Wi-Fi. Add networks the normal Raspberry Pi way
(`sudo nmtui`, or the desktop Wi-Fi menu). Settings > Wi-Fi shows the link and switches
between saved networks. Network names and passwords stay on the Pi, never in this repo.

## Where things are

```
dash/web/                 the UI (plain HTML/CSS/JS, no build step)
  js/app.js               app shell: top bar, nav, faults banner, reverse camera pop-up
  js/link.js              websocket link to the gateway, requests and hold-to-run
  js/store.js             live state, plus what we last asked for
  js/settings.js          dash settings (saved on the Pi)
  js/text.js              plain-English fault and refusal text
  js/demo.js              built-in demo vehicle
  js/screens/*.js         one file per screen
  js/ui/                  controls (sliders, hold buttons, slide-to-arm), icons, vehicle drawing
dash/server/teryx_dash/   /api/ routes: settings, control box limits, OTA, Wi-Fi, system, camera
dash/deploy/              systemd units, kiosk launcher, Pi installer
dash/tests/               server tests (pytest) and an end-to-end UI test against the simulator
```

Settings are saved to `~/.config/teryx/dash-settings.json` on the Pi (not in the repo).

## Tests

```bash
cd dash && python -m pytest                 # server, settings, OTA install and rollback
node dash/tests/ui_live.mjs                 # needs the simulator running on :8080
```

`ui_live.mjs` drives the real UI with the mouse as a finger: lights, presets, 4WD, diff lock,
arming and running the winch, the tray, a refusal when too fast, the camera popping up in
reverse, the fault banner and the safety limits page.

## Safety notes

- Hold-to-run (winch, tray) repeats every 100 ms while your finger is down. Lift, slide off,
  lose the touch, switch screens or lose the link and it stops. The control box also stops
  it if the repeats stop for 300 ms.
- Lockouts shown on screen (speed limits, stopped, armed) are only hints. The control box
  enforces the real rules with the limits under Settings > Safety limits.
- Updates and Pi shutdown are refused while moving.
