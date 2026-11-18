# Teryx CAN protocol

Generated from `teryx/canbus/` by `python -m teryx canmap`. Don't edit by hand.

All values little-endian. Physical value = raw x scale + offset. Standard 11-bit ids.
Bit rate: match the Shinegle (likely 250 kbit/s, TBC).

## Pi 5 dash -> Pico 2 control box

### 0x700 PI_HEARTBEAT

From **dash**, every 100 ms.

Pico stops tray, winch and actuators if this goes quiet for 500 ms.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `counter` | byte 0 | u8 |  |  |
| `dash_state` | byte 1 | u8 |  | 0=boot, 1=ok, 2=shutting_down |

### 0x701 PI_LIGHTS

From **dash**, every 1000 ms.

On change, plus a resend every 1 s. Brightness 0-255 (0 = off). On/off-only bars treat anything above 0 as on.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `front_1` | byte 0 | u8 |  |  |
| `front_2` | byte 1 | u8 |  |  |
| `front_3` | byte 2 | u8 |  |  |
| `front_4` | byte 3 | u8 |  |  |
| `interior` | byte 4 | u8 |  |  |
| `effect` | byte 5 | u8 |  | 0=none, 1=strobe, 2=chase, 3=outside_only, 4=inside_only, 5=breathe, 6=sos |
| `rear_on` | byte 6 bit 0 | u1 |  |  |
| `rear_auto` | byte 6 bit 1 | u1 |  | Rear pods on automatically in reverse |
| `counter` | byte 7 | u8 |  |  |

### 0x702 PI_DRIVE

From **dash**, every 1000 ms.

On change, plus a resend every 1 s.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `fourwd_req` | byte 0 | u8 |  | 0 = 2WD, 1 = 4WD |
| `diff_target` | byte 1 | u8 | % |  |
| `counter` | byte 7 | u8 |  |  |

### 0x703 PI_HOLD

From **dash**, every 100 ms.

Hold-to-run, sent at 10 Hz only while a button is held. Pico stops if it goes quiet for 300 ms.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `tray` | byte 0 | i8 |  | -1 down, 0 stop, +1 up |
| `winch` | byte 1 | i8 |  | -1 out, 0 stop, +1 in |
| `winch_armed` | byte 2 bit 0 | u1 |  |  |
| `winch_timed_s` | byte 3 | u8 | s | Timed pull length, 0 = plain hold. Pico stops it on time by itself, capped at setting 21 |
| `counter` | byte 7 | u8 |  |  |

### 0x704 PI_SETTINGS

From **dash**, on change.

On change, one key per frame. The Pico echoes it on 0x714 as an ack. Keys are in SETTINGS below. 0xF0 = save to flash, 0xF1 = reset defaults.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `key` | byte 0 | u8 |  |  |
| `value` | bytes 2-3 | u16 |  |  |

### 0x705 PI_LOCK

From **dash**, on change.

Vehicle lock command, on demand (docs/vehicle-lock.md). Digits are BCD, first digit in the high nibble of d0. PIN 4-6 digits, recovery code 8. The Pico keeps only a salted hash and answers on 0x716 straight away.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `cmd` | byte 0 | u8 |  | 1=lock, 2=unlock, 3=verify, 4=set_pin, 5=set_puk, 6=remove |
| `n_digits` | byte 1 | u8 |  |  |
| `d0` | byte 2 | u8 |  |  |
| `d1` | byte 3 | u8 |  |  |
| `d2` | byte 4 | u8 |  |  |
| `d3` | byte 5 | u8 |  |  |
| `counter` | byte 6 | u8 |  |  |

### 0x71F PI_FW_UPDATE

From **dash**, on change.

Pico reboots to its bootloader when magic = 0x5445 ('TE') and parked.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `magic` | bytes 0-1 | u16 |  |  |

## Pico 2 control box -> Pi 5 dash

### 0x710 PICO_STATUS

From **controlbox**, every 100 ms.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `counter` | byte 0 | u8 |  |  |
| `fault_bits` | bytes 1-2 | u16 |  | See FAULT_BITS |
| `inputs` | byte 3 | u8 |  | MCP23017 B0-B7, see INPUT_BITS |
| `state` | byte 4 bit 0 (+2 bits) | u2 |  | 0=boot, 1=ok, 2=degraded, 3=failsafe |
| `on_defaults` | byte 4 bit 3 | u1 |  | Pico is running on default settings, please resend |
| `fourwd_wait` | byte 4 bit 4 | u1 |  | A 2WD/4WD request is waiting for the right speed (docs/drive-changes.md) |
| `diff_wait` | byte 4 bit 5 | u1 |  | A diff lock request is waiting for the right speed |
| `throttle_hold` | byte 4 bit 6 | u1 |  | Throttle held: a shift is running from a standstill |
| `reject_reason` | byte 5 bit 0 (+4 bits) | u4 |  | Why the last request was refused 0=none, 1=too_fast, 2=not_stopped, 3=speed_unknown, 4=not_armed, 5=interlock, 6=actuator_fault, 7=low_12v, 8=dash_link, 9=ignition_off, 10=at_limit, 11=not_parked, 12=winch_remote, 13=bad_frame, 14=wait_timeout, 15=busy |
| `reject_count` | byte 5 bit 4 (+4 bits) | u4 |  | Goes up by one each time a request is refused |
| `winch_armed` | byte 6 bit 0 | u1 |  |  |
| `speed_valid` | byte 6 bit 1 | u1 |  |  |
| `reverse_active` | byte 6 bit 2 | u1 |  |  |
| `shutdown_request` | byte 6 bit 3 | u1 |  | Key off: Pi should shut down |
| `parked` | byte 6 bit 4 | u1 |  | Stopped and safe for OTA updates |
| `speed` | byte 7 | u8 | km/h | Speed as the Pico sees it, 255 = unknown |

### 0x711 PICO_OUTPUTS

From **controlbox**, every 100 ms.

What the outputs are actually doing (after effects and safety).

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `relays` | byte 0 | u8 |  | See RELAY_BITS |
| `front_1` | byte 1 | u8 |  |  |
| `front_2` | byte 2 | u8 |  |  |
| `front_3` | byte 3 | u8 |  |  |
| `front_4` | byte 4 | u8 |  |  |
| `interior` | byte 5 | u8 |  |  |
| `effect` | byte 6 | u8 |  | 0=none, 1=strobe, 2=chase, 3=outside_only, 4=inside_only, 5=breathe, 6=sos |

### 0x712 PICO_ACTUATORS

From **controlbox**, every 100 ms.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `diff_pct` | byte 0 | u8 | % | From the actuator pot |
| `fourwd` | byte 1 | u8 |  | 0=2wd, 1=4wd, 2=to_4wd, 3=to_2wd, 4=fault, 5=unknown |
| `tray` | byte 2 | u8 |  | 0=down, 1=up, 2=mid, 3=raising, 4=lowering, 5=fault |
| `diff_current` | byte 3 | u8 x0.1 | A |  |
| `fourwd_current` | byte 4 | u8 x0.1 | A |  |
| `tray_current` | byte 5 | u8 x0.1 | A |  |
| `tray_pct` | byte 6 | u8 | % | Estimate from run time, no pot on the tray |
| `diff_target` | byte 7 | u8 | % | While diff_wait is set, the % it's waiting to move to |

### 0x713 PICO_POWER

From **controlbox**, every 1000 ms.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `aux_12v` | bytes 0-1 | u16 x0.001 | V |  |
| `pico_temp` | byte 2 | i8 | C |  |
| `diff_pot_raw` | bytes 3-4 | u16 |  | Raw ADS1115 reading, for calibrating keys 14/15 |
| `fw_major` | byte 5 | u8 |  |  |
| `fw_minor` | byte 6 | u8 |  |  |
| `winch_idle_s` | byte 7 | u8 | s | Seconds since the winch last ran while armed (caps at 255) |

### 0x714 PICO_SETTINGS_ACK

From **controlbox**, on change.

Echo of each 0x704 frame once the Pico has applied it (value is what it actually used).

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `key` | byte 0 | u8 |  |  |
| `status` | byte 1 | u8 |  | 0=ok, 1=unknown_key, 2=out_of_range, 3=locked |
| `value` | bytes 2-3 | u16 |  |  |

### 0x715 PICO_REGEN

From **controlbox**, every 100 ms.

Brake pedal regen (docs/brake-regen.md). All zero with state off while the feature is off.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `pedal_pct` | byte 0 | u8 | % | Brake pedal travel from the pedal sensor |
| `request_pct` | byte 1 | u8 | % | Regen asked of the Shinegle, after every limit |
| `state` | byte 2 bit 0 (+4 bits) | u4 |  | 0=off, 1=ready, 2=active, 3=limited, 4=sensor_fault |
| `limit` | byte 2 bit 4 (+4 bits) | u4 |  | What is holding regen back, if anything 0=none, 1=low_speed, 2=speed_unknown, 3=not_forward, 4=battery_full, 5=two_wd, 6=sensor, 7=throttle |
| `pedal_raw` | bytes 3-4 | u16 |  | Raw ADS1115 reading, for calibrating keys 28/29 |
| `brake_light` | byte 5 bit 0 | u1 |  | Regen is strong enough to light the brake lights |

### 0x716 PICO_LOCK

From **controlbox**, every 100 ms.

Vehicle lock state (docs/vehicle-lock.md). Also sent straight after every 0x705.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `state` | byte 0 | u8 |  | 0=off, 1=unlocked, 2=locked |
| `tries_left` | byte 1 | u8 |  | Wrong tries left before a lockout |
| `lockout_s` | bytes 2-3 | u16 | s | Lockout time left |
| `window` | byte 4 bit 0 | u1 |  | Change window open (PIN checked in the last 60 s) |
| `puk_set` | byte 4 bit 1 | u1 |  | A recovery code is stored |
| `inhibit` | byte 4 bit 2 | u1 |  | Drive inhibit asked for (how is TBC until the Shinegle is decoded) |
| `lockout` | byte 4 bit 3 | u1 |  |  |
| `result` | byte 5 | u8 |  | Result of the last 0x705 0=none, 1=ok, 2=wrong, 3=not_parked, 4=no_pin, 5=lockout, 6=bad_digits, 7=not_allowed, 8=recovered |
| `result_count` | byte 6 | u8 |  | Goes up by one per 0x705 |
| `fails` | byte 7 | u8 |  | Wrong tries in a row (kept over power cuts) |

## Bench only

### 0x7E0 BENCH_INPUTS

From **sim**, every 100 ms.

HOST/BENCH BUILD ONLY. Lets the simulator drive the Pico's wired inputs and inject faults. The real Pico firmware ignores it.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `inputs` | byte 0 | u8 |  | Bits as INPUT_BITS |
| `force_mask` | byte 1 | u8 |  | Which input bits to force |
| `fault_inject` | byte 2 | u8 |  | See BENCH_FAULTS |
| `aux_mv` | bytes 3-4 | u16 | mV | Fake 12V reading, 0 = leave alone |

**Bench fault inject bits (0x7E0 byte 2)**

| bit | name |
|---|---|
| 0 | `jam_diff` |
| 1 | `jam_tray` |
| 2 | `fourwd_overcurrent` |
| 3 | `pot_disconnected` |
| 4 | `io_bus_dead` |

## Lookup tables

**Fault bits (0x710 bytes 1-2)**

| bit | name |
|---|---|
| 0 | `dash_link` |
| 1 | `speed_unknown` |
| 2 | `fourwd_timeout` |
| 3 | `fourwd_overcurrent` |
| 4 | `diff_timeout` |
| 5 | `diff_pot_stuck` |
| 6 | `tray_timeout` |
| 7 | `tray_overcurrent` |
| 8 | `tray_limit_switch` |
| 9 | `winch_interlock` |
| 10 | `low_12v` |
| 11 | `pico_hot` |
| 12 | `watchdog_reset` |
| 13 | `diff_overcurrent` |
| 14 | `io_bus` |
| 15 | `brake_pedal` |

**Input bits (0x710 byte 3, MCP23017 B0-B7)**

| bit | name |
|---|---|
| 0 | `in.ignition` |
| 1 | `in.brake` |
| 2 | `in.reverse` |
| 3 | `in.tray_down` |
| 4 | `in.tray_up` |
| 5 | `in.winch_remote` |
| 6 | `in.park` |
| 7 | `in.trailer` |

**Relay bits (0x711 byte 0, relay 1 = bit 0)**

| bit | name |
|---|---|
| 0 | `light.rear` |
| 1 | `trailer.tail` |
| 2 | `trailer.brake` |
| 3 | `winch.in` |
| 4 | `winch.out` |
| 5 | `winch.isolator` |
| 6 | `aux.accessory` |
| 7 | `power.hold` |

**Reject reasons (0x710 byte 5 low nibble)**

| value | name |
|---|---|
| 0 | `none` |
| 1 | `too_fast` |
| 2 | `not_stopped` |
| 3 | `speed_unknown` |
| 4 | `not_armed` |
| 5 | `interlock` |
| 6 | `actuator_fault` |
| 7 | `low_12v` |
| 8 | `dash_link` |
| 9 | `ignition_off` |
| 10 | `at_limit` |
| 11 | `not_parked` |
| 12 | `winch_remote` |
| 13 | `bad_frame` |
| 14 | `wait_timeout` |
| 15 | `busy` |

**Settings keys (0x704 / 0x714)**

| key | name | unit | default | range |
|---|---|---|---|---|
| 1 (0x01) | `heartbeat_timeout_ms` | ms | 500 | 100-5000 |
| 2 (0x02) | `speed_timeout_ms` | ms | 500 | 100-5000 |
| 3 (0x03) | `fourwd_max_kmh` | km/h | 1 | 0-40 |
| 4 (0x04) | `fourwd_max_run_ms` | ms | 3000 | 500-10000 |
| 5 (0x05) | `fourwd_overcurrent_da` | 0.1A | 60 | 5-300 |
| 6 (0x06) | `diff_max_kmh` | km/h | 15 | 0-40 |
| 7 (0x07) | `diff_max_run_ms` | ms | 4000 | 500-10000 |
| 8 (0x08) | `diff_overcurrent_da` | 0.1A | 80 | 5-300 |
| 9 (0x09) | `tray_max_run_ms` | ms | 20000 | 1000-60000 |
| 10 (0x0A) | `tray_overcurrent_da` | 0.1A | 100 | 5-300 |
| 11 (0x0B) | `winch_dead_time_ms` | ms | 100 | 50-1000 |
| 12 (0x0C) | `winch_auto_disarm_s` | s | 120 | 10-3600 |
| 13 (0x0D) | `shutdown_wait_s` | s | 30 | 5-300 |
| 14 (0x0E) | `diff_pot_min_raw` | raw | 1000 | 0-32767 |
| 15 (0x0F) | `diff_pot_max_raw` | raw | 25000 | 0-32767 |
| 16 (0x10) | `light_dimmable_mask` | bits | 31 | 0-31 |
| 17 (0x11) | `hold_to_run_timeout_ms` | ms | 300 | 100-2000 |
| 18 (0x12) | `relay_active_low` | bool | 0 | 0-1 |
| 19 (0x13) | `tray_full_travel_ms` | ms | 16000 | 1000-60000 |
| 20 (0x14) | `low_12v_mv` | mV | 11000 | 9000-13000 |
| 21 (0x15) | `winch_timed_max_s` | s | 30 | 1-120 |
| 22 (0x16) | `brake_regen_on` | bool | 0 | 0-1 |
| 23 (0x17) | `brake_regen_pct` | % | 50 | 0-100 |
| 24 (0x18) | `brake_regen_start_pct` | % | 5 | 0-50 |
| 25 (0x19) | `brake_regen_full_pct` | % | 30 | 5-100 |
| 26 (0x1A) | `brake_regen_fade_kmh` | km/h | 5 | 0-20 |
| 27 (0x1B) | `brake_regen_2wd_pct` | % | 60 | 0-100 |
| 28 (0x1C) | `brake_pedal_min_raw` | raw | 2000 | 0-32767 |
| 29 (0x1D) | `brake_pedal_max_raw` | raw | 22000 | 0-32767 |
| 30 (0x1E) | `shift_wait_ms` | ms | 10000 | 0-30000 |
| 31 (0x1F) | `shift_throttle_hold` | bool | 1 | 0-1 |
| 240 (0xF0) | save to flash | | | |
| 241 (0xF1) | reset to defaults | | | |
| 242 (0xF2) | clear latched faults | | | |

## Shinegle SG1202 (PLACEHOLDER)

Made-up layout so we can build now. It lives in `teryx/canbus/shinegle.dbc`; replace that file once the real bus has been decoded (docs/shinegle-decode.md).

### 0x180 SG_MOTOR

From **shinegle**, every 50 ms. **PLACEHOLDER.**

Bytes 0-2 are what the Pico reads for its speed interlocks.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `speed` | bytes 0-1 | u16 x0.1 | km/h |  |
| `direction` | byte 2 | u8 |  | 0=neutral, 1=forward, 2=reverse |
| `mode` | byte 3 bit 0 (+2 bits) | u2 |  | 0=eco, 1=normal, 2=sport |
| `ready` | byte 3 bit 2 | u1 |  |  |
| `limp` | byte 3 bit 3 | u1 |  |  |
| `brake` | byte 3 bit 4 | u1 |  |  |
| `throttle` | byte 4 | u8 | % |  |
| `rpm` | bytes 5-6 | i16 | rpm |  |
| `counter` | byte 7 | u8 |  |  |

### 0x181 SG_BATTERY

From **shinegle**, every 100 ms. **PLACEHOLDER.**

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `batt_v` | bytes 0-1 | u16 x0.1 | V |  |
| `batt_a` | bytes 2-3 | i16 x0.1 | A | + = draw, - = regen |
| `soc` | byte 4 | u8 | % |  |
| `counter` | byte 7 | u8 |  |  |

### 0x182 SG_TEMPS

From **shinegle**, every 500 ms. **PLACEHOLDER.**

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `motor_temp` | byte 0 | u8 -40 | C |  |
| `ctrl_temp` | byte 1 | u8 -40 | C |  |
| `batt_temp` | byte 2 | u8 -40 | C |  |
| `counter` | byte 7 | u8 |  |  |

### 0x183 SG_FAULTS

From **shinegle**, every 200 ms. **PLACEHOLDER.**

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `fault_over_current` | byte 0 bit 0 | u1 |  | Motor over current |
| `fault_over_voltage` | byte 0 bit 1 | u1 |  | Battery voltage too high |
| `fault_under_voltage` | byte 0 bit 2 | u1 |  | Battery voltage too low |
| `fault_motor_over_temp` | byte 0 bit 3 | u1 |  | Motor too hot |
| `fault_controller_over_temp` | byte 0 bit 4 | u1 |  | Controller too hot |
| `fault_hall_sensor` | byte 0 bit 5 | u1 |  | Motor position sensor fault |
| `fault_throttle` | byte 0 bit 6 | u1 |  | Throttle fault |
| `fault_comms` | byte 0 bit 7 | u1 |  | Controller comms fault |
| `fault_battery_over_temp` | byte 1 bit 0 | u1 |  | Battery too hot |
| `fault_precharge` | byte 1 bit 1 | u1 |  | Precharge fault |
| `odometer` | bytes 2-5 | u32 x0.1 | km |  |
| `counter` | byte 7 | u8 |  |  |

**Shinegle fault bits (placeholder)**

| bit | name |
|---|---|
| 0 | `over_current` |
| 1 | `over_voltage` |
| 2 | `under_voltage` |
| 3 | `motor_over_temp` |
| 4 | `controller_over_temp` |
| 5 | `hall_sensor` |
| 6 | `throttle` |
| 7 | `comms` |
| 8 | `battery_over_temp` |
| 9 | `precharge` |
