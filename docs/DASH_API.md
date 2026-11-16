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
| `pico.faults` | list of strings | `dash_link`, `speed_unknown`, `fourwd_timeout`, `fourwd_overcurrent`, `diff_timeout`, `diff_pot_stuck`, `tray_timeout`, `tray_overcurrent`, `tray_limit_switch`, `winch_interlock`, `low_12v`, `pico_hot`, `watchdog_reset` |
| `pico.reject` | string | Why the last request was refused: `none`, `too_fast`, `not_stopped`, `speed_unknown`, `not_armed`, `interlock`, `actuator_fault`, `low_12v` |
| `pico.reject_text` | string | Plain-English version |
| `pico.reject_count` | 0-15 | Goes up by one per refusal, so you can tell a new one from an old one |
| `pico.temp` | °C | |
| `pico.version` | string | Pico firmware version, e.g. `0.1` (1 Hz) |
| `an.diff_pos_raw` | 0-32767 | Raw diff pot reading, for calibrating settings 14/15 (1 Hz) |
| `winch.idle_s` | s | Seconds since the winch last ran while armed, for the auto-disarm countdown (1 Hz) |
| `in.ignition`, `in.brake`, `in.reverse`, `in.tray_down`, `in.tray_up`, `in.winch_remote`, `in.park`, `in.spare` | bool | Wired inputs |
| `an.diff_pos` | % | Diff actuator actual position |
| `an.aux_12v` | V | |
| `an.diff_current`, `an.4wd_current`, `an.tray_current` | A | |
| `act.4wd` | `2wd` / `4wd` / `to_4wd` / `to_2wd` / `fault` | |
| `act.diff_target` | % | What the box is aiming for |
| `act.tray` | `down` / `up` / `mid` / `raising` / `lowering` / `fault` | |
| `act.tray_pct` | % | Estimate (no pot on the tray) |
| `winch.armed` | bool | |
| `light.front_1` to `light.front_4`, `light.interior` | 0-255 | Actual output, after effects |
| `light.effect` | string | Actual effect |
| `light.rear`, `trailer.tail`, `trailer.brake`, `winch.in`, `winch.out`, `winch.isolator`, `aux.accessory`, `power.hold` | bool | Actual relay states |

**Dash's own**

| Key | Notes |
|---|---|
| `req.<id>` | What the dash last asked for, for every request id below, plus `req.act.tray` and `req.winch` (current hold) |
| `dash.bus`, `dash.uptime_s`, `dash.settings` | Bus in use, uptime, last settings the Pico acked |
| `sim.scenario`, `sim.links` | Only when the sim runs in the same program |

### UI to server

**Requests** (on/off things and levels):

```json
{"type": "request", "id": "light.front_1", "value": 200}
```

| id | value |
|---|---|
| `light.front_1` to `light.front_4`, `light.interior` | 0-255 |
| `light.effect` | `none`, `strobe`, `chase`, `outside_only`, `inside_only`, `breathe` |
| `light.rear` | `off`, `on`, `auto` (on in reverse) |
| `act.4wd` | 0 = 2WD, 1 = 4WD |
| `act.diff` | 0-100 % |
| `winch.armed` | true / false |

**Hold-to-run** (tray and winch). Send every 100 ms while the finger is down,
and `0` on release. The server stops sending after 300 ms of silence, and the
Pico stops 300 ms after that, so a crashed UI can't leave the tray running.

```json
{"type": "hold", "id": "act.tray", "value": 1}
```

`act.tray`: 1 up, -1 down. `winch`: 1 in, -1 out.

**Settings** (0x704, see the key list in `docs/CAN_PROTOCOL.md`):

```json
{"type": "setting", "key": "fourwd_max_kmh", "value": 8}
```

Reply: `{"type": "setting_ack", "key": "fourwd_max_kmh", "ok": true}` once the
Pico has acked it.

**Errors** come back as `{"type": "error", "error": "..."}`.

## HTTP

| Path | |
|---|---|
| `GET /api/state` | One snapshot of the state above |
| `GET /api/canmap` | Every message, signal, setting and fault list as JSON (handy for building settings screens) |
| `GET /api/bus` | Frame counts and unknown CAN ids |
| `GET/POST /api/sim` | Sim status and controls (when the sim is running here) |

## Server-side plugins

`python -m teryx run --plugin my_module` (or a package called `teryx_dash`
that can be imported) gets `setup_routes(app, gateway)` called at start-up,
so the full dash can add its own routes (settings storage, OTA, wifi).
`gateway` has `snapshot()`, `request(id, value)`, `hold(id, value)`,
`set_setting(key, value)`, `settings` and `send_frame(name, values)`.
