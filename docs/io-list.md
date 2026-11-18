# Teryx dash OS: IO list (draft v0.1)

This is the master list of every input and output on the Teryx, which board
handles it, what drives it, how it's fused and what safety rules apply.
The machine-readable copy is [`config/io-map.yaml`](../config/io-map.yaml).
If you change one, change the other.

Status: **draft**. Items marked **TBC** need checking on the real hardware.

---

## 1. How it all fits together

```
              Wi-Fi (OTA updates)
                     │
   ┌─────────────────┴─────────────────┐         HDMI + USB
   │  Raspberry Pi 5  ("the dash")     │◄──────► 10.1" touch screen
   │  UI, logging, camera, settings    │◄──USB── rear camera (USB or AHD capture, TBC)
   │  CAN HAT (MCP2515 or Waveshare)   │◄──I2C── IMU (roll/pitch), optional
   └─────────────────┬─────────────────┘
                     │ CAN bus (twisted pair, 120 Ω at each end)
      ┌──────────────┼──────────────────────────┐
      │              │                          │
 Shinegle       Raspberry Pi Pico 2        (Shinegle dash
 controller     ("the control box")         + programmer,
 SG1202         MCP2515 CAN module          for sniffing)
                     │
       ┌─────────────┼──────────────┬───────────────┐
   MCP23017       3x BTS7960     MOSFET board     ADS1115
   (I2C GPIO)     actuators      light dimming    (I2C ADC)
   8 relays out                                   pot, currents,
   8 opto inputs                                  12V sense
```

**Rule of thumb:** the Pi asks, the Pico decides. The Pico owns every output
and every safety rule. If the Pi crashes, reboots or is unplugged, the Teryx
still drives, lights stay as they were, and anything moving stops.

---

## 2. Parts

### On hand
| Part | Used for |
|---|---|
| 10.1" waterproof touch screen (HDMI + USB) | Display and touch |
| 8-channel relay board | On/off loads (see section 4) |
| ~26-way GPIO breakout | Pi side wiring |
| 1x BTS7960 H-bridge | Front diff actuator |
| ADS1115 | Analogue inputs |
| 50mm actuator with pot | Front diff lock (%) |
| 50mm actuator (standard) | 2WD / 4WD (or drive the stock Kawasaki 4WD actuator instead, see [teryx-drivetrain.md](teryx-drivetrain.md)) |
| 400mm actuator | Tray lift |
| Trailer plug | Trailer lights |
| 2K rear camera | Reverse view (USB or RCA/AHD, **TBC**) |
| 4x 12" light bars | Front lights, each controlled on its own |
| 1x 7" light bar | Interior |
| 2x 4" pods | Rear / reverse |
| XBull 5000lb winch (with solenoid box + remote) | Winch |
| 5V buck converter | Pi power (must be 5V **5A** for the Pi 5, **TBC**) |

### To buy
Prices and links checked live: [`shopping-list.md`](shopping-list.md).

| Part | Why | Approx |
|---|---|---|
| Raspberry Pi 5 **4GB** | Dash, UI, logging, OTA (built-in Wi-Fi). 4GB is plenty, see the shopping list | $233 |
| Raspberry Pi Pico 2 | Control box | $10 |
| 2x MCP2515 CAN module (TJA1050/SN65HVD230) or 1x module + Pi CAN HAT | CAN for Pico and Pi | $10–40 |
| 2x more BTS7960 | Each actuator needs its own driver | $20 |
| MCP23017 I2C expander | Pico runs out of pins otherwise | $5 |
| 8-ch opto-isolator board (PC817, 12V in) | 12V signals into 3.3V Pico safely | $10 |
| 5-ch MOSFET PWM board (logic-level, e.g. AOD4184) | Light bar dimming/effects | $15 |
| Cheap 12V PWM dimmer | Test if the bars dim before buying the MOSFET board | $10 |
| 2x micro limit switches | Tray up / down end stops | $5 |
| Fuse block (blade, 18-20 way, or two 12-way) + inline fuses | Every output fused. 12 fuses are planned, so Sam's 12-way is exactly full (see [`wiring/README.md`](wiring/README.md#fuse-block)) | $30 |
| Power-hold relay (or use relay 8) | Lets the Pi shut down cleanly after key-off | – |
| Spare Pico + MCP2515 module | USB CAN adaptor for sniffing the Shinegle in step 4 (`firmware/can-sniffer`, slcan + SavvyCAN GVRET) | $20 |
| IMU (ICM-20948 or MPU-6050), optional | Roll / pitch gauge | $10 |
| Brake regen parts, optional, **only once the Shinegle check passes**: Hall angle sensor for the pedal pivot, 2nd ADS1115, divider resistors, opto + RC filter if the Shinegle wants an analogue signal | Brake pedal regen ([`brake-regen.md`](brake-regen.md)) | $150–250 |
| Carlinkit CPC200-CCPA (or Autokit) USB adapter, optional | CarPlay and Android Auto on the dash ([`audio.md`](audio.md)) | $80–150 |
| USB DAC or I2S DAC HAT, 12V marine amp, marine speakers, optional | Sound: the Pi feeds the amp, no head unit ([`audio.md`](audio.md)) | $350–1500 |

---

## 3. Pico 2 pin map

| Pico pin | Function | Connects to |
|---|---|---|
| GP0 / GP1 | UART0 TX/RX | Debug header inside the box. Runs the vehicle lock workshop reset (`docs/vehicle-lock.md`) |
| GP2 | SPI0 SCK | MCP2515 SCK |
| GP3 | SPI0 MOSI | MCP2515 SI |
| GP4 | SPI0 MISO | MCP2515 SO |
| GP5 | SPI0 CS | MCP2515 CS |
| GP6 | IRQ in | MCP2515 INT |
| GP7 | PWM | BTS7960 #1 (front diff) RPWM |
| GP8 | PWM | BTS7960 #1 LPWM |
| GP9 | Out | BTS7960 #1 R_EN + L_EN |
| GP10 | PWM | BTS7960 #2 (2WD/4WD) RPWM |
| GP11 | PWM | BTS7960 #2 LPWM |
| GP12 | Out | BTS7960 #2 R_EN + L_EN |
| GP13 | PWM | BTS7960 #3 (tray) RPWM |
| GP14 | PWM | BTS7960 #3 LPWM |
| GP15 | Out | BTS7960 #3 R_EN + L_EN |
| GP16 | PWM | Front bar 1 (far left) MOSFET |
| GP17 | PWM | Front bar 2 (inner left) MOSFET |
| GP18 | PWM | Front bar 3 (inner right) MOSFET |
| GP19 | PWM | Front bar 4 (far right) MOSFET |
| GP20 | PWM | Interior 7" bar MOSFET |
| GP21 | IRQ in | MCP23017 INTB (inputs changed) |
| GP22 | IRQ in | ADS1115 ALERT/RDY |
| GP26 | I2C1 SDA | MCP23017 + ADS1115 |
| GP27 | I2C1 SCL | MCP23017 + ADS1115 |
| GP28 | ADC2 | BTS7960 #1 current sense (IS) |

If the light bars **don't** dim, GP16–20 still switch the MOSFETs fully on/off,
so the wiring doesn't change. Effects (strobe, chase) still work.

---

## 4. Outputs

| ID | Output | Driver | Pico control | Fuse | Notes |
|---|---|---|---|---|---|
| `light.front_1` | Front bar 1 (far left) | MOSFET ch1 | GP16 PWM | 10A | Dimmable **TBC** |
| `light.front_2` | Front bar 2 (inner left) | MOSFET ch2 | GP17 PWM | 10A | |
| `light.front_3` | Front bar 3 (inner right) | MOSFET ch3 | GP18 PWM | 10A | |
| `light.front_4` | Front bar 4 (far right) | MOSFET ch4 | GP19 PWM | 10A | |
| `light.interior` | Interior 7" bar | MOSFET ch5 | GP20 PWM | 5A | |
| `light.rear` | Rear / reverse pods (pair) | Relay 1 | MCP23017 A0 | 10A | Auto on in reverse |
| `trailer.tail` | Trailer tail lights | Relay 2 | MCP23017 A1 | 5A | On with any front light |
| `trailer.brake` | Trailer brake lights | Relay 3 | MCP23017 A2 | 5A | Follows brake input. Also hard-wire a diode from the brake switch as backup |
| `winch.in` | Winch in | Relay 4 → winch solenoid coil | MCP23017 A3 | 3A (coil) | Never the motor current through the relay board |
| `winch.out` | Winch out | Relay 5 → winch solenoid coil | MCP23017 A4 | 3A (coil) | Interlocked with `winch.in` |
| `aux.accessory` | Accessory 12V (camera, USB, spare) | Relay 7 | MCP23017 A6 | 10A | On with ignition |
| `power.hold` | Pi + Pico power hold | Relay 8 | MCP23017 A7 | 7.5A | Keeps power on after key-off for clean shutdown |
| `act.diff` | Front diff lock actuator (%) | BTS7960 #1 | GP7/8/9 | 10A | Closed loop on pot, 0–100% |
| `act.4wd` | 2WD / 4WD actuator | BTS7960 #2 | GP10/11/12 | 10A | Runs to end stop, stops on current rise or timeout |
| `act.tray` | Tray lift actuator (400mm) | BTS7960 #3 | GP13/14/15 | 15A | Hold-to-run, limit switches + current |

Relay board note: check the relay board triggers from 3.3V (most opto
boards do with JD-VCC fed 5V). If not, run the MCP23017 off 5V on a level
shifter. **TBC** on the bench.

---

## 5. Inputs

### Digital (12V through opto board → MCP23017 port B)
| ID | Input | MCP23017 | Notes |
|---|---|---|---|
| `in.ignition` | Key on (12V switched) | B0 | Starts boot; key-off starts shutdown timer |
| `in.brake` | Brake switch | B1 | Trailer brake lights, shown on dash |
| `in.reverse` | Reverse selected | B2 | Use the Shinegle direction switch wire. Also expected on CAN, **TBC** |
| `in.tray_down` | Tray down limit | B3 | Normally closed, so a broken wire reads as "at limit" |
| `in.tray_up` | Tray up limit | B4 | Normally closed |
| `in.winch_remote` | Winch being run by hand: handheld remote, or either hidden hand switch | B5 | All of them diode-OR'd into this one input. The dash shows "by hand", counts it towards winch motor heat, and the Pico won't let the dash drive the winch while it's on |
| `in.park` | Parking brake pedal switch | B6 | The stock Teryx has one (it lights the red parking brake light in the meter). Tap that wire. Ground or 12V switching **TBC** |
| `in.trailer` | Trailer plugged in | B7 | Reed switch in the 7-pin socket (Narva 82043BL type, see [`cameras.md`](cameras.md)). Shows the trailer camera. Was the spare input |

### Analogue
| ID | Input | Where | Scaling |
|---|---|---|---|
| `an.diff_pos` | Diff actuator pot | ADS1115 A0 | Calibrate min/max in settings, shown as 0–100% |
| `an.aux_12v` | 12V aux battery | ADS1115 A1 | Divider 10k/2.2k (max ~16V) |
| `an.4wd_current` | BTS7960 #2 current | ADS1115 A2 | IS pins diode-OR'd, 1k to ground |
| `an.tray_current` | BTS7960 #3 current | ADS1115 A3 | Same as above |
| `an.diff_current` | BTS7960 #1 current | Pico GP28 | Same as above |
| `an.brake_pedal` | Brake pedal position (Hall angle sensor, 0.5–4.5 V) | 2nd ADS1115 (addr 0x49) A0 | Divider 10k/20k so 4.5 V reads 3.0 V. Calibrate up/floor points (settings 28/29). Only needed for brake regen, see [`brake-regen.md`](brake-regen.md) |
| `an.brake_pressure` | Brake line pressure, optional | 2nd ADS1115 A1 | 0.5–4.5 V transducer, same divider. Optional cross-check for the pedal sensor |

### From the Shinegle controller (CAN, to be decoded)
Expected values, all **TBC** once we record the bus with the Shinegle dash
and programmer plugged in.

| ID | Value | Units |
|---|---|---|
| `mc.speed` | Road speed (or motor RPM, scaled by gear ratio) | km/h, rpm |
| `mc.batt_v` | Traction battery voltage | V |
| `mc.batt_a` | Battery current (+ draw, − regen) | A |
| `mc.soc` | State of charge (if sent, else estimate from voltage) | % |
| `mc.motor_temp` | Motor temperature | °C |
| `mc.ctrl_temp` | Controller temperature | °C |
| `mc.throttle` | Throttle position | % |
| `mc.direction` | Forward / neutral / reverse | enum |
| `mc.mode` | Eco / sport / speed mode | enum |
| `mc.faults` | Fault code bits | bitfield |

### Pi side
| ID | Input | How |
|---|---|---|
| `pi.touch` | Touch screen | USB |
| `pi.camera` | Rear camera | USB, or AHD/RCA via a USB capture dongle (**TBC**) |
| `pi.imu` | Roll / pitch | I2C, optional |
| `pi.gps` | Position / speed backup | USB GPS (DFRobot TEL0138), see `shopping-list.md` 4b |

---

## 6. CAN bus

- **Bit rate:** match the Shinegle. Likely 250 kbit/s, **TBC** when sniffing.
- **Termination:** 120 Ω at each end of the bus (one end at the Shinegle,
  the other at the Pi or Pico, whichever is furthest).
- **Our IDs:** 0x700–0x71F (standard 11-bit). If these clash with anything
  the Shinegle sends, move the whole block. All values little-endian.

| ID | From → To | Rate | Contents |
|---|---|---|---|
| 0x700 | Pi → Pico | 10 Hz | Heartbeat: counter (u8), dash state (u8) |
| 0x701 | Pi → Pico | on change + every 1 s | Lights: front 1–4, interior brightness (u8 ×5, 0–255), effect id (u8), rear on (bit), auto-rear (bit) |
| 0x702 | Pi → Pico | on change + every 1 s | Drive: 4WD request (u8: 0=2WD, 1=4WD), diff target % (u8) |
| 0x703 | Pi → Pico | 10 Hz while held | Hold-to-run: tray (i8: −1 down, 0 stop, +1 up), winch (i8: −1 out, 0 stop, +1 in), winch armed (bit), timed pull seconds (u8, 0 = plain hold). Pico stops the motion if no 0x703 for 300 ms, and stops a timed pull on time by itself |
| 0x704 | Pi → Pico | on change | Settings: speed limits, timeouts (see section 7) |
| 0x710 | Pico → Pi | 10 Hz | Status: b0 counter, b1–2 fault flags (u16, see below), b3 digital inputs B0–B7 as bits, b4 Pico state (0 boot, 1 ok, 2 degraded, 3 failsafe), b5 reject reason (low nibble) + reject counter (high nibble), b6 bit 0 winch armed |
| 0x711 | Pico → Pi | 10 Hz | Outputs: b0 relay bits, b1–5 light levels (u8 ×5), b6 active light effect |
| 0x712 | Pico → Pi | 10 Hz | Actuators: b0 diff %, b1 4WD state, b2 tray state, b3–5 currents (u8 ×3, 0.1A), b6 tray estimated % (from run time), b7 diff target % |
| 0x713 | Pico → Pi | 1 Hz | 12V aux (u16, mV), Pico temp (i8) |
| 0x715 | Pico → Pi | 10 Hz | Brake regen: pedal % (u8), regen request % (u8), state + limit (nibbles), pedal raw (u16), brake light bit. See [`brake-regen.md`](brake-regen.md) |
| 0x71F | Pi → Pico | on demand | Firmware update request (Pico reboots to bootloader) |

**Fault flag bits (0x710 b1–2):** 0 dash link lost, 1 speed unknown,
2 4WD timeout, 3 4WD overcurrent, 4 diff timeout, 5 diff pot stuck,
6 tray timeout, 7 tray overcurrent, 8 tray limit switch, 9 winch interlock,
10 low 12V, 11 Pico hot, 12 watchdog reset, 13 diff overcurrent, 14 IO bus,
15 brake pedal sensor (only while brake regen is on).

The Shinegle's own messages are read by **both** the Pi (for the screen) and
the Pico (for speed interlocks).

---

## 7. Safety rules (enforced on the Pico)

All limits are adjustable in settings, with these defaults:

1. **Lost dash:** no heartbeat from the Pi for 500 ms → stop winch, tray and
   actuators, disarm the winch. Lights stay as they were. Driving
   is never affected.
2. **Lost speed:** no Shinegle speed for 500 ms → treat speed as unknown and
   block anything that needs "stopped".
3. **2WD / 4WD:** only changes when **stopped** (under 1 km/h). Kawasaki says
   stop first, and shifting on the move can damage the front drive train. It
   finishes engaging as you roll off. Max run 3 s, stop on current over 6A.
4. **Diff lock %:** **adding lock** only under **15 km/h**. **Unlocking**
   works at any speed, so you can drop it before a turn. It only does
   anything in 4WD. Max run 4 s. If the pot reading
   doesn't move while driving, stop and flag a fault.

   Sources for 3 and 4 (Kawasaki owner's manuals) are in
   [teryx-drivetrain.md](teryx-drivetrain.md).

   **Waiting, one at a time, throttle hold (3 and 4):** a request that is only
   too fast **waits** up to 10 s (`shift_wait_s`) for the speed to come right,
   then runs. The dash shows a spinner, a hint and Cancel. Any other reason is
   refused at once, and a wait that runs out is dropped. Only one drive change
   at a time, except unlocking the diff. Throttle is held while a shift runs
   **only if it started from a standstill**, and never once moving. Details in
   [drive-changes.md](drive-changes.md).
5. **Tray:** only when **stopped** (speed 0). Hold-to-run only. Stops at limit
   switches, on current over 10A, or after 20 s.
6. **Winch:** must be armed on the dash, speed 0, hold-to-run. In and out can
   never be on together (100 ms dead time). Auto-disarm after 2 min idle.
   The XBull handheld remote stays wired in parallel as a backup, and so do
   two hidden hand switches (one at the winch, one in the cab, see below).
   **Timed pull:** the dash can ask for a 3, 5 or 10 s pull in. The Pico
   times it itself and stops it at the end even if the dash keeps asking,
   never longer than its own limit (setting 21, default 30 s). The dash
   still has to keep sending every 100 ms, so if the dash dies the winch
   stops within 300 ms as usual. The dash also keeps a rough motor heat
   guess and warns when the winch needs a rest (no sensor, see below).
7. **Reverse:** rear pods and camera come on automatically in reverse.
8. **Key-off:** Pico tells the Pi to shut down, waits up to 30 s, then drops
   `power.hold`.
9. **Watchdog:** the Pico's hardware watchdog resets it if the firmware hangs.
   On boot every output starts **off**.
10. **Every output fused.** Winch motor cable gets its own breaker at the
    battery, sized to the winch (usually 250–300A for a 5000lb).
11. **Brake pedal regen (test feature, off by default):** the first part of
    the brake pedal asks the Shinegle for regen. The hydraulic brakes are
    never touched. No regen if the pedal sensor is out of range or disagrees
    with the brake switch (latched fault), if speed is unknown, out of
    forward, throttle on, or the battery is nearly full. Fades out under
    5 km/h, cut to 60% when not in 4WD. Full rules and what still has to be
    checked on the Shinegle: [`brake-regen.md`](brake-regen.md).

---

## 8. Power

| Supply | Feeds | Notes |
|---|---|---|
| 12V aux battery (kept after the conversion, confirmed) | Everything 12V, winch | Charged by the kit's DC-DC. Winch runs straight off this battery with its own breaker. DC-DC rating still **TBC** (decides how long the winch can run before the battery sags) |
| "Dash 12V" rail = key switch **or** `power.hold` relay contacts (wired in parallel) | Both 5V bucks below | Key on powers the rail; the Pico closes `power.hold` straight away, so after key-off the rail stays up until the Pico drops it |
| 5V 5A buck (from the dash 12V rail) | Pi 5 + screen | Pi 5 throttles on a 3A supply |
| 12V aux battery, own fuse (optional) | Audio amp | Remote turn-on from the dash 12V rail so it goes off with the key. 4 x 50 W can pull 20–30 A. See [`audio.md`](audio.md) |
| Own small 5V buck (from the dash 12V rail) | Pico 2 | Separate from the Pi so the Pico keeps running if the Pi goes down, and still on after key-off so it can hold the Pi up. USB to the Pi is for data and reflashing only |

Wiring detail: [`docs/wiring.md`](wiring.md).

---

## 9. Open items

- [ ] Camera type: USB or RCA/AHD
- [ ] Do the light bars dim with PWM? Test one with a cheap dimmer
- [ ] Shinegle CAN bit rate and message layout (record with dash + programmer). Listen-only, try 250k then 500k, check if frames stop without the Shinegle dash (request/response), log findings to `shinegle.dbc`
- [ ] Shinegle reverse signal: CAN or a wire?
- [x] 12V battery: yes, kept after the conversion
- [ ] DC-DC converter rating
- [ ] 5V buck converter rating (needs 5A)
- [ ] Relay board works off 3.3V logic?
- [ ] Trailer indicators wanted? (Teryx has none stock; would need 2 more outputs)
- [ ] Brake pedal regen: does the Shinegle take a brake/regen input (analogue, switch or CAN)? Checklist in [`brake-regen.md`](brake-regen.md)


## Winch hand switches and motor heat

**Hand switches (Sam, 2026-11-17).** Two hidden momentary (ON)-OFF-(ON)
toggles: one near the winch, one in the cab. Spring return, so they can't
be left on. They're wired like the XBull remote, straight to the solenoid
box coil wires, so they work even if the dash or the Pico is down:

- Each switch's "in" side feeds the solenoid "in" coil wire through its own
  diode (3 A, e.g. 1N5408), same for "out". The diodes stop one source
  back-feeding another (relay 4/5, remote, the other switch).
- Tap each switch's in and out sides, before those diodes, through small
  diodes (1N4148 is fine) onto opto input 6, so `in.winch_remote` goes high
  when any hand control is pressed. See [`wiring.md`](wiring.md).
- Fuse the switch feed at 3 A, like the relay coil feeds.
- No winch isolator (Sam, 18 Nov). The 250 A manual reset breaker is the
  kill switch: push it off and the winch is dead. Arming on the dash only
  gates the control box's relays 4-5, so the remote and hand switches work
  whenever the breaker is on, dash or no dash.

**Motor heat.** There's no current or temperature sensor on the winch (a
500 A hall sensor on the motor cable could be added later). The dash guesses
heat from run time instead (`dash/web/js/winchheat.js`): about 60 s of hard
pulling in fills it, paying out counts about a third as much, hand pulls
count as pulling in, and it cools from full in about 10 minutes. Warns at
70%, says rest at 100% and blocks a new timed pull until it's back under
40%. Hold-to-run still works when it's hot, because sometimes you have to
finish the pull. Where the numbers come from:

- Zeak 5500 lb ATV winch manual: duty cycle is time running within 15
  minutes; at 5% and full load, rest 14 min 15 s after every 45 s of running
  ([manual, p.12](https://www.manualslib.com/manual/2833574/Zeak-5500-Lb.html?page=12)).
- Superwinch (via etrailer): about 5 min at full pull then 30 min rest;
  lighter pulls run longer and cool faster; if the motor's too hot to keep
  your hand on, stop
  ([etrailer Q&A](https://www.etrailer.com/question-261309.html)).
- The XBull 5000 manual wasn't reachable online, so check its duty cycle
  when the winch is in hand and adjust `HEAT` in `winchheat.js` to suit.
