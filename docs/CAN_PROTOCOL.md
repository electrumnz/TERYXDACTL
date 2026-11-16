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
| `effect` | byte 5 | u8 |  | 0=none, 1=strobe, 2=chase, 3=outside_only, 4=inside_only, 5=breathe |
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
| `counter` | byte 7 | u8 |  |  |

### 0x704 PI_SETTINGS

From **dash**, on change.

On change, one key per frame. The Pico echoes it on 0x714 as an ack. Keys are in SETTINGS below. 0xF0 = save to flash, 0xF1 = reset defaults.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `key` | byte 0 | u8 |  |  |
| `value` | bytes 2-3 | u16 |  |  |

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
| `reject_reason` | byte 5 bit 0 (+4 bits) | u4 |  | Why the last request was refused 0=none, 1=too_fast, 2=not_stopped, 3=speed_unknown, 4=not_armed, 5=interlock, 6=actuator_fault, 7=low_12v |
| `reject_count` | byte 5 bit 4 (+4 bits) | u4 |  | Goes up by one each time a request is refused |
| `winch_armed` | byte 6 bit 0 | u1 |  |  |

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
| `effect` | byte 6 | u8 |  | 0=none, 1=strobe, 2=chase, 3=outside_only, 4=inside_only, 5=breathe |

### 0x712 PICO_ACTUATORS

From **controlbox**, every 100 ms.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `diff_pct` | byte 0 | u8 | % | From the actuator pot |
| `fourwd` | byte 1 | u8 |  | 0=2wd, 1=4wd, 2=to_4wd, 3=to_2wd, 4=fault |
| `tray` | byte 2 | u8 |  | 0=down, 1=up, 2=mid, 3=raising, 4=lowering, 5=fault |
| `diff_current` | byte 3 | u8 x0.1 | A |  |
| `fourwd_current` | byte 4 | u8 x0.1 | A |  |
| `tray_current` | byte 5 | u8 x0.1 | A |  |
| `tray_pct` | byte 6 | u8 | % | Estimate from run time, no pot on the tray |
| `diff_target` | byte 7 | u8 | % |  |

### 0x713 PICO_POWER

From **controlbox**, every 1000 ms.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `aux_12v` | bytes 0-1 | u16 x0.001 | V |  |
| `pico_temp` | byte 2 | i8 | C |  |

### 0x714 PICO_SETTINGS_ACK

From **controlbox**, on change.

Echo of each 0x704 frame once the Pico has applied it (value is what it actually used).

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `key` | byte 0 | u8 |  |  |
| `value` | bytes 2-3 | u16 |  |  |

## Bench only

### 0x7E0 BENCH_INPUTS

From **sim**, every 100 ms.

HOST/BENCH BUILD ONLY. Lets the simulator drive the Pico's wired inputs and inject faults. The real Pico firmware ignores it.

| Signal | Where | Type | Unit | Notes |
|---|---|---|---|---|
| `inputs` | byte 0 | u8 |  | Bits as INPUT_BITS |
| `force_mask` | byte 1 | u8 |  | Which input bits to force |
| `fault_inject` | byte 2 | u8 |  | See BENCH_FAULTS |

**Bench fault inject bits (0x7E0 byte 2)**

| bit | name |
|---|---|
| 0 | `jam_diff` |
| 1 | `jam_tray` |
| 2 | `fourwd_overcurrent` |

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
| 7 | `in.spare` |

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

**Settings keys (0x704 / 0x714)**

| key | name | unit | default | range |
|---|---|---|---|---|
| 1 (0x01) | `heartbeat_timeout_ms` | ms | 500 | 100-5000 |
| 2 (0x02) | `speed_timeout_ms` | ms | 500 | 100-5000 |
| 3 (0x03) | `fourwd_max_kmh` | km/h | 5 | 0-40 |
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
| 240 (0xF0) | save to flash | | | |
| 241 (0xF1) | reset to defaults | | | |

## Shinegle SG1202 (PLACEHOLDER)

Made-up layout so we can build now. Replace in `teryx/canbus/shinegle.py` once the real bus has been recorded.

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
| `motor_rpm` | bytes 5-6 | i16 | rpm |  |
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
| `faults` | bytes 0-1 | u16 |  |  |
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
