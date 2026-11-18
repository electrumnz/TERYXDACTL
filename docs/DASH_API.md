# Dash API

How a dash UI gets live data and asks for things. The UI never touches CAN.
A ready-made client is in `teryx/web/common/teryx.js` (served at
`/common/teryx.js`).

## Websocket `/ws`

### Server to UI, 20 times a second

```json
{"type": "state", "t": 1794838651.75, "state": { "mc.speed": 28.4, "...": "..." }}
```

Keys follow the io-map ids in `config/io-map.yaml`.

**Motor controller (Shinegle)**

| Key | Type | Notes |
|---|---|---|
| `mc.online` | bool | Shinegle frames seen in the last 1 s |
| `mc.speed` | km/h | |
| `mc.rpm` | rpm | Signed, minus in reverse |
| `mc.direction` | `forward` / `neutral` / `reverse` | |
| `mc.mode` | `eco` / `normal` / `sport` | |
| `mc.throttle` | % | |
| `mc.brake`, `mc.ready`, `mc.limp` | bool | Limp = power cut back |
| `mc.batt_v`, `mc.batt_a` | V, A | Amps: plus = draw, minus = regen |
| `mc.power_kw` | kW | |
| `mc.soc` | % | |
| `mc.motor_temp`, `mc.ctrl_temp`, `mc.batt_temp` | °C | |
| `mc.faults` | list of strings | `over_current`, `over_voltage`, `under_voltage`, `motor_over_temp`, `controller_over_temp`, `hall_sensor`, `throttle`, `comms`, `battery_over_temp`, `precharge` (placeholder until sniffed) |
| `mc.odometer` | km | |

**Control box (Pico)**

| Key | Type | Notes |
|---|---|---|
| `pico.online` | bool | 0x710 seen in the last 1 s |
| `pico.state` | `boot` / `ok` / `degraded` / `failsafe` | |
| `pico.on_defaults` | bool | Box is on default settings (the gateway resends ours) |
| `pico.speed`, `pico.speed_valid` | km/h, bool | Speed as the Pico sees it (`null` when unknown) |
| `pico.parked` | bool | Stopped and safe for an OTA update |
| `pico.shutdown_request` | bool | Key is off: the Pi should shut down cleanly |
| `pico.faults` | list of strings | `dash_link`, `speed_unknown`, `fourwd_timeout`, `fourwd_overcurrent`, `diff_timeout`, `diff_pot_stuck`, `tray_timeout`, `tray_overcurrent`, `tray_limit_switch`, `winch_interlock`, `low_12v`, `pico_hot`, `watchdog_reset`, `diff_overcurrent`, `io_bus` |
| `pico.reject` | string | Why the last request was refused: `none`, `too_fast`, `not_stopped`, `speed_unknown`, `not_armed`, `interlock`, `actuator_fault`, `low_12v`, `dash_link`, `ignition_off`, `at_limit`, `not_parked`, `winch_remote`, `bad_frame` |
| `pico.reject_text` | string | Plain-English version |
| `pico.reject_count` | 0-15 | Goes up by one per refusal, so you can tell a new one from an old one |
| `pico.temp` | °C | |
| `pico.version` | string | Pico firmware version, e.g. `0.1` (1 Hz) |
| `an.diff_pos_raw` | 0-32767 | Raw diff pot reading, for calibrating settings 14/15 (1 Hz) |
| `winch.idle_s` | s | Seconds since the winch last ran while armed, for the auto-disarm countdown (1 Hz) |
| `regen.pedal_pct` | % | Brake pedal travel from the pedal sensor (brake regen, 10 Hz) |
| `regen.request_pct` | % | Regen the control box is asking the Shinegle for |
| `regen.state` | off / ready / active / limited / sensor_fault | Brake regen state |
| `regen.limit` | none / low_speed / speed_unknown / not_forward / battery_full / two_wd / sensor / throttle | What is holding regen back |
| `an.brake_pedal_raw` | 0-32767 | Raw pedal sensor reading, for calibrating settings 28/29 |
| `in.ignition`, `in.brake`, `in.reverse`, `in.tray_down`, `in.tray_up`, `in.winch_remote`, `in.park`, `in.spare` | bool | Wired inputs |
| `an.diff_pos` | % | Diff actuator actual position |
| `an.aux_12v` | V | |
| `an.diff_current`, `an.4wd_current`, `an.tray_current` | A | |
| `act.4wd` | `2wd` / `4wd` / `to_4wd` / `to_2wd` / `fault` / `unknown` | Unknown after the Pico boots, until its first move |
| `act.diff_target` | % | What the box is aiming for |
| `act.tray` | `down` / `up` / `mid` / `raising` / `lowering` / `fault` | |
| `act.tray_pct` | % | Estimate (no pot on the tray) |
| `winch.armed` | bool | |
| `light.front_1` to `light.front_4`, `light.interior` | 0-255 | Actual output, after effects |
| `light.effect` | string | Actual effect |
| `light.rear`, `trailer.tail`, `trailer.brake`, `winch.in`, `winch.out`, `winch.isolator`, `aux.accessory`, `power.hold` | bool | Actual relay states |

**Vehicle lock** (`0x716`, see `docs/vehicle-lock.md`)

| Key | Type | Notes |
|---|---|---|
| `lock.state` | `off` / `unlocked` / `locked` | `off` = no PIN set |
| `lock.tries_left` | count | Wrong tries left before a wait |
| `lock.lockout`, `lock.lockout_s` | bool, s | Too many wrong tries, and how long is left |
| `lock.window` | bool | PIN checked in the last 60 s, so it can be changed or removed |
| `lock.puk_set` | bool | A recovery code is stored |
| `lock.inhibit` | bool | The Pico is asking for no drive |
| `lock.result`, `lock.result_text`, `lock.result_count` | string, string, count | Answer to the last lock command. `result_count` goes up by one per command |
| `lock.fails` | count | Wrong tries in a row |

**Dash's own**

| Key | Notes |
|---|---|
| `req.<id>` | What the dash last asked for, for every request id below, plus `req.act.tray` and `req.winch` (current hold) |
| `dash.bus`, `dash.uptime_s`, `dash.settings` | Bus in use, uptime, last settings the Pico acked |
| `sim.scenario`, `sim.links` | Only when the sim runs in the same program |

**Pi sensors (not fitted yet)**

The dash's tilt/GPS widget, tilt alarms and day/night Auto read these when they're there. A
sensor service on the Pi will publish them later; the simulator fakes them now.

| Key | Type | Notes |
|---|---|---|
| `pi.imu.roll` | ° | + = right side down |
| `pi.imu.pitch` | ° | + = nose up |
| `pi.gps.fix` | bool | `false` = GPS fitted but no fix yet. Missing = no GPS |
| `pi.gps.lat`, `pi.gps.lon` | ° | Only used on the Pi (day/night). Never saved or sent anywhere |
| `pi.gps.alt_m`, `pi.gps.heading`, `pi.gps.speed_kmh`, `pi.gps.sats` | m, °, km/h, count | |
| `pi.light_lux` | lux | Light sensor, if one is ever fitted. Wins over the sun for day/night |

### UI to server

**Requests** (on/off things and levels):

```json
{"type": "request", "id": "light.front_1", "value": 200}
```

| id | value |
|---|---|
| `light.front_1` to `light.front_4`, `light.interior` | 0-255 |
| `light.effect` | `none`, `strobe`, `chase`, `outside_only`, `inside_only`, `breathe`, `sos` |
| `light.rear` | `off`, `on`, `auto` (on in reverse) |
| `act.4wd` | 0 = 2WD, 1 = 4WD |
| `act.diff` | 0-100 % |
| `winch.armed` | true / false |

**Hold-to-run** (tray and winch). Send every 100 ms while the finger is down,
and `0` on release. The server stops sending after 300 ms of silence, and the
Pico stops 300 ms after that, so a crashed UI can't leave the tray running.

```json
{"type": "hold", "id": "act.tray", "value": 1}
{"type": "hold", "id": "winch", "value": 1, "secs": 5}
```

`act.tray`: 1 up, -1 down. `winch`: 1 in, -1 out. `secs` (winch only) makes it a timed
pull: keep sending it every 100 ms as usual, and the control box stops the winch after
that many seconds by itself (capped at its setting 21).

**Settings** (0x704, see the key list in `docs/CAN_PROTOCOL.md`):

```json
{"type": "setting", "key": "fourwd_max_kmh", "value": 8}
```

Reply: `{"type": "setting_ack", "key": "fourwd_max_kmh", "ok": true}` once the
Pico has acked it.

**Vehicle lock** (`0x705`, see `docs/vehicle-lock.md`). The answer shows in `lock.*` above.

```json
{"type": "lock", "cmd": "unlock", "digits": "4821"}
```

`cmd`: `lock`, `unlock` (PIN, or the 8 digit recovery code), `verify` (opens the 60 s change
window), `set_pin`, `set_puk`, `remove`. Nothing on the Pi keeps the digits.

**Errors** come back as `{"type": "error", "error": "..."}`.

## HTTP

| Path | |
|---|---|
| `GET /api/state` | One snapshot of the state above |
| `GET /api/canmap` | Every message, signal, setting and fault list as JSON (handy for building settings screens) |
| `GET /api/bus` | Frame counts and unknown CAN ids |
| `GET/POST /api/sim` | Sim status and controls (when the sim is running here). Fake sensors: `{"tilt": {"roll": 30}}` holds a tilt, `{"tilt": null}` lets go, `{"sensor": ["gps", false]}` turns one off |
| `GET /api/trips` | This trip, trip A, lifetime, past trips, Wh/km and range (dash plugin) |
| `POST /api/trips/reset/trip-a`, `/api/trips/reset/history` | |
| `GET /api/wifi/scan`, `POST /api/wifi/add {ssid, password, hidden}`, `POST /api/wifi/forget {ssid}` | Wi-Fi from the on-screen keyboard |

## Server-side plugins

`python -m teryx run --plugin my_module` (or a package called `teryx_dash`
that can be imported) gets `setup_routes(app, gateway)` called at start-up,
so the full dash can add its own routes (settings storage, OTA, wifi).
`gateway` has `snapshot()`, `request(id, value)`, `hold(id, value)`,
`set_setting(key, value)`, `settings` and `send_frame(name, values)`.
