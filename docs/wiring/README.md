# Teryx wiring (made from `config/wiring.yaml`)

Don't edit this file or schematic.json here. Edit [`config/wiring.yaml`](../../config/wiring.yaml), then run
`python -m teryx wiring`. A test fails if they get out of step, and it also checks the wiring
itself: every fused feed has a fuse, wires are thick enough for their fuse, no 12 V or 72 V
wire lands on a 3.3 V pin, each CAN bus has exactly two 120 ohm ends, the Pico pins match
`config/io-map.yaml`, and the Pi's PCIe port and header stay free for the AI HAT+ 2.

Why things are wired this way (power hold, diodes, CAN rules): [`docs/wiring.md`](../wiring.md).
The drawing: one big schematic of the whole Teryx on a pan and zoom grid, online at
<https://electrumnz.github.io/TERYXDACTL/wiring/> (or open [`index.html`](index.html) through any
web server). It's laid out from [`schematic.json`](schematic.json) by [`sld.js`](sld.js) with ELK
(elkjs, EPL-2.0, unchanged copy in [`vendor/`](vendor/)). The simulator page links to it and lights
up the live wires.

**97 devices, 377 wires.** By status: 18 from_manual, 3 confirmed, 300 planned, 52 tbc, 4 placeholder.
Nothing has been checked on the real Teryx yet.

Wire sizes follow the conservative table in the YAML (from
[speedingparts.eu](https://info.speedingparts.eu/what-cable-size-should-you-use-in-a-12v-automotive-system),
runs up to about 5 m). Go one size up for bundled or hot runs.

## Systems on the drawing

1. Traction: 72 V pack, controller, motor, DC-DC (10 wires)
2. 12 V power: battery, fuses, key, dash rail, bucks (25 wires)
3. Grounds (chassis, star point) (1 wires)
4. Shinegle low voltage: key, F-N-R, throttle, sensors, programmer (19 wires)
5. Winch (20 wires)
6. Lights (85 wires)
7. Drive: 4WD, diff lock, tray, power steering (39 wires)
8. Trailer plug and trailer camera (24 wires)
9. Control box inside: Pico 2 and its boards (52 wires)
10. 12 V signals into the control box (opto board) (18 wires)
11. CAN buses: main Teryx bus and the steering bus (8 wires)
12. RC box: steering by remote (fake torque sensor) (37 wires)
13. Dash computer: Pi 5, screen, cameras, USB, audio (39 wires)

## Things to check or photograph on the Teryx

- [ ] **Traction battery pack** (PACK): Battery pack make, size (kWh), and where its main fuse is. Photo the label
- [ ] **150 A air-break switch** (HV_ISO): Is the air-break switch fitted, and where? Photo it
- [ ] **Main contactor** (CONTACTOR): Is there a main contactor between the pack and the controller? Photo it and trace its two small coil wires
- [ ] **DC-DC converter 72 V to 12 V** (DCDC): DC-DC label (amps out), where its 72 V feed comes from, and whether it is isolated (does its 12 V negative join the pack negative?)
- [ ] **Shinegle kit key switch** (KIT_KEY): Is the kit key the same switch as the Teryx key? Meter what voltage reaches J1-1 with the key on (12 V or 72 V)
- [ ] **Blade fuse block** (FB): Check the 12-way's rating (want 30 A per way, about 100 A total, a cover). Read the front bar labels. Each pair (1+4, 2+3) must draw under about 12 A together (about 140 W) to share a 15 A fuse. If not, give each bar its own 10 A again
- [ ] **Potted 5 V 10 A buck (12/24 V in)** (PI_BUCK): Measure its output on the bench under load: 5.0-5.25 V. The Pi flags low voltage below about 4.6 V
- [ ] **Screen 12 V supply** (SCREEN_PSU): Read the label on the screen's power brick (volts and amps)
- [ ] **16-ch relay board, channels 1-8** (RELAYS): Does the relay board click from 3.3 V logic? Active high or low? Relays are SRD-05VDC type, 10 A at 28-30 V DC. Keep each load under about 7 A. Nothing on the relays gets near that now the floods are on the MOSFET board (relay 1 only feeds the trailer reversing lamp)
- [ ] **16-ch relay board, channels 9-16 (2 used, 6 spare)** (RELAYS2): Relay 10 is rated 30 V DC. If the Shinegle KSI turns out to be 72 V (see KIT_KEY), swap relay 10 for one rated 80 V DC or more
- [ ] **8-ch isolated MOSFET board (low side, all 8 used)** (MOSFET): The listing must say 3.3 V input, PNP / high-level trigger (firmware drives the pins high for on; pins sit low at boot so lights stay off), at least 24 V load and 10 A per channel. If it only says 5 A, use single LR7843 modules instead. Low side switching only works if each light's - wire isn't joined to its metal body. Meter a bar's - lead to its housing (and the floods and trailer bar), it must read open. If one reads shorted, that light needs a high side switch
- [ ] **Rear flood left (4 in pod)** (FLOOD_L): Light bars and pods dim with PWM? Test one on a cheap dimmer
- [ ] **Left headlight (stock, 12 V 35/35 W)** (HEAD_L): Unplug a headlight and photo the plug. Which pin is low, high and earth?
- [ ] **Left tail / brake light (stock, 12 V 8/27 W)** (TAIL_L): Photo the tail light plug. Which wire is tail, brake and earth?
- [ ] **Roof beacon (amber + white LED, steady-on)** (BEACON): Count the wires. Common earth + one wire per colour is what this plan expects. If each colour has its own earth it still works (join the earths). If it has a mode wire instead (one + feed, cycles colours on a pulse), tell the dash thread
- [ ] **XBull solenoid box** (WINCH_SOL): Photo the XBull solenoid box terminals and the remote plug pins
- [ ] **2WD/4WD actuator** (ACT_4WD): Is the stock electric 4WD actuator still on the front diff, and is the dash 2WD/4WD switch still wired to it? Photo its plug
- [ ] **Brake light switch (stock)** (BRAKE_SW): Find the brake light switch's two wires and meter them. Feed one from the 6-way (way 6), the other is OUT. If the stock loom still feeds the switch, cut that feed so it's only on our fuse. The switch now carries both brake filaments plus the trailer stop lamps (about 8 A with bulbs): if its contacts look small, put a 12 V automotive relay after it
- [ ] **Parking brake switch (stock)** (PARK_SW): Find the parking brake switch wire at the meter plug. Does it switch ground or 12 V?
- [ ] **Toyota Aqua EPS ECU (89650-52B51)** (EPS_ECU): Photo both EPS ECU sockets (pin numbers) and the power plug's wire colours
- [ ] **Aqua steering column (motor + torque sensor)** (EPS_COL): Measure the space from the steering wheel to where the Teryx shaft goes to the rack. Meter TRQ1/TRQ2 at centre, hard left and hard right effort (Toyota: about 2.5 V centre, the two moving in opposite directions)
- [ ] **AS5600 magnetic angle sensor + magnet** (RC_ANGLE): Fit check: magnet centred over the chip, 1-2 mm gap (spec 0.5-3 mm), gear backlash small enough to hold centre
- [ ] **7-pin flat trailer socket (Narva 82043BL, reed switch)** (TRAILER): Which way does the Narva reed switch switch, and what triggers it?
- [ ] **Analogue video to camera-ribbon (CSI) board, ADV728x-M (front + rear + trailer, cabin later)** (TCAM_DONGLE): Count the video inputs on the board (need 3, 4 with the cabin cam). Confirm it works on the Pi 5 (dtoverlay=adv728x-m,adv7280m=1); set each camera to CVBS/PAL, not AHD (OSD menu, button or mode wire)
- [ ] **Glove box USB-C charger (RC phone)** (GLOVE_USB): Pick a 12 V USB-C PD panel socket (waterproof cap, about 20-30 W)
- [ ] **Rear camera (200 degree, Sam's)** (CAM_REAR): Rear camera: AHD with a CVBS mode? Photo its plug and label
- [ ] **Front camera (12 V car camera, Sam's best of the 3)** (CAM_FRONT): Front camera: CVBS (PAL) or AHD with a CVBS mode? Photo its plug and label

Wires marked TBC, with what's unknown:

- H08 CONTACTOR.out to DCDC.in_pos: Where the DC-DC takes its 72 V from is TBC
- S18 SG1202.J3 to PROG.PLUG: Setup only. J3 to J1-25/28/29/7 TBC
- P13 RAIL.BUS to SCREEN_PSU.VIN: Fuse size depends on the screen's draw
- P18 DCDC.out_pos to BAT12.pos: DC-DC charge lead. Size and fuse depend on its rating
- G33 BEACON.GND to GND_STAR.G: Beacon earth, or a good chassis earth on the roll cage
- G27 HEAD_L.GND to GND_STAR.G: Stock earth, keep it if it's good
- C01 SG1202.CAN_H to PICO_CAN.CANH: Twisted pair. CAN is optional on the SG1202, check it's fitted. Bit rate TBC (try 250k then 500k)
- I03 FNR.R to OPTO.IN3: The F-N-R switch is on the Shinegle key line. If J1-1 runs at 72 V, this needs a 72 V rated input, not the 12 V opto
- I10 WINCH_SOL.REM_IN to OPTO.IN6: Remote tap, on the remote's own line before its diode (WN21). Not on COIL_IN: that would also see relay 4 and make the Pico stop its own pull
- I16 WINCH_SOL.REM_OUT to OPTO.IN6: Remote tap, out side
- I11 PARK_SW.OUT to OPTO.IN7: If the switch grounds, wire the opto input the other way round
- LT63 FB2.F6 to BRAKE_SW.IN: Brake switch feed, always live
- WN19 WINCH_SOL.COIL_IN to WINCH_SOL.GND: Across the coil, at the solenoid box, unless the box already has one. Stops the coil's kick arcing the relay contacts and spiking the 12 V
- WN21 WINCH_SOL.REM_IN to WINCH_SOL.COIL_IN: Inside the solenoid box: cut the remote socket's in wire off the coil and rejoin it through this diode
- D33 EPS_ECU.MOTOR to EPS_COL.MOTOR: Toyota's own plug, keep it from the wrecker
- RC23 EPS_COL.TRQ1 to RC_REL.NC1: Cut into Toyota's torque sensor lead; twisted with TRQ2
- RC32 RC_ANGLE.OUT to RC_ADC.A2: Screened lead from the column
- T05 BRAKE_SW.OUT to TRAILER.P6_STOP: Trailer brake lights still work with the control box off
- T06 RELAYS.NO1 to TRAILER.P2_REV: Reversing pin. Relay 1 follows the rear floods, so trailer reverse lights come on with them
- X03 CAM_REAR.VID to TCAM_DONGLE.VID_R: Shielded video lead, soldered
- X05 RELAYS.NO7 to CAM_REAR.V12: 2 A inline fuse. On with the key, like the trailer camera
- G34 CAM_REAR.GND to GND_STAR.G: Or a good chassis earth near the camera
- X04 TCAM_DONGLE.CSI to PI5.CSI1: Camera ribbon, 2nd port
- X11 CAM_FRONT.VID to TCAM_DONGLE.VID_F: Shielded video lead to video board input 3, soldered
- X12 RELAYS.NO7 to CAM_FRONT.V12: 2 A inline fuse. On with the key, like the rear camera
- G61 CAM_FRONT.GND to GND_STAR.G: Or a good chassis earth near the camera

## Fuse block

| Slot | Fuse | Feeds | Wires |
|---|---|---|---|
| F1 | 15 A | front bars 1 + 4 (outer pair) | LT01, LT04 |
| F2 | 15 A | front bars 2 + 3 (inner pair) | LT02, LT03 |
| F3 | 15 A | rear floods (MOSFET 7-8) + relay 1 trailer reverse pin | LT16, LT17, LT18 |
| F4 | 7.5 A | BTS7960 8 trailer tail + stop | T01 |
| F5 | 5 A | relays 4-5 winch coils | WN07, WN08 |
| F6 | 5 A | winch hand switches, tray limits, trailer reed | I13, WN13, WN14 |
| F7 | 10 A | extras - interior bar + relay 7 accessory (phone charger, trailer cam) | P15, LT05 |
| F8 | 7.5 A | relay 8 power hold | P04 |
| F9 | 10 A | BTS7960 1 diff | D05 |
| F10 | 10 A | BTS7960 2 4WD | D15 |
| F11 | 15 A | BTS7960 3 tray | D22 |
| F12 | 7.5 A | key switch | P02 |

Fuses not in the block (inline, at the battery or on a board):

| Wire | Fuse | From | To |
|---|---|---|---|
| S03 | 10 A | RELAYS2.NC2 | SG1202.J1-1 |
| P01 | 60 A | BAT12.pos | FB.IN |
| P03 | 7.5 A | KEY.IGN | RAIL.BUS |
| P05 | 7.5 A | RELAYS.NO8 | RAIL.BUS |
| P08 | 2 A | RAIL.BUS | PICO_BUCK.VIN |
| P13 | 3 A | RAIL.BUS | SCREEN_PSU.VIN |
| P20 | 3 A | RELAYS.NO7 | GLOVE_USB.VIN |
| P16 | 40 A | BAT12.pos | AMP.B+ |
| P17 | 2 A | RAIL.BUS | AMP.REM |
| P19 | 60 A | BAT12.pos | EPS_ECU.B+ |
| I01 | 7.5 A | KEY.IGN | OPTO.IN1 |
| WN01 | 250 A | BAT12.pos | BRK_WINCH.in |
| WN02 | 250 A | BRK_WINCH.out | WINCH_SOL.B+ |
| WN10 | 5 A | RELAYS.NO4 | WINCH_SOL.COIL_IN |
| WN11 | 5 A | RELAYS.NO5 | WINCH_SOL.COIL_OUT |
| WN15 | 5 A | HSW_WINCH.IN | WINCH_SOL.COIL_IN |
| WN16 | 5 A | HSW_WINCH.OUT | WINCH_SOL.COIL_OUT |
| WN17 | 5 A | HSW_CAB.IN | WINCH_SOL.COIL_IN |
| WN18 | 5 A | HSW_CAB.OUT | WINCH_SOL.COIL_OUT |
| D06 | 10 A | BTS1.M+ | ACT_DIFF.M+ |
| D07 | 10 A | BTS1.M- | ACT_DIFF.M- |
| D16 | 10 A | BTS2.M+ | ACT_4WD.M+ |
| D17 | 10 A | BTS2.M- | ACT_4WD.M- |
| D23 | 15 A | BTS3.M+ | ACT_TRAY.M+ |
| D24 | 15 A | BTS3.M- | ACT_TRAY.M- |
| D28 | 1 A | BAT12.pos | ADS1.A1 |
| D31 | 3 A | RAIL.BUS | RELAYS2.COM1 |
| D32 | 3 A | RELAYS2.NO1 | EPS_ECU.IG |
| T06 | 15 A | RELAYS.NO1 | TRAILER.P2_REV |
| T07 | 2 A | RELAYS.NO7 | TCAM_PLUG.V12 |
| T08 | 2 A | TCAM_PLUG.V12 | CAM_TRAILER.V12 |
| X05 | 2 A | RELAYS.NO7 | CAM_REAR.V12 |
| X12 | 2 A | RELAYS.NO7 | CAM_FRONT.V12 |

## Wire schedule

### Traction: 72 V pack, controller, motor, DC-DC

| Wire | From | To | Size | Fuse | Via | Status | Note |
|---|---|---|---|---|---|---|---|
| H01 | PACK.pos | HV_ISO.in |  |  |  | from_manual | Main pack + to the air-break switch. Size TBC, check for a main HV fuse |
| H02 | HV_ISO.out | CONTACTOR.in |  |  |  | tbc |  |
| H03 | CONTACTOR.out | SG1202.B+ |  |  |  | tbc |  |
| H04 | PACK.neg | SG1202.B- |  |  |  | from_manual |  |
| H05 | SG1202.U | MOTOR.U |  |  |  | from_manual |  |
| H06 | SG1202.V | MOTOR.V |  |  |  | from_manual |  |
| H07 | SG1202.W | MOTOR.W |  |  |  | from_manual |  |
| H08 | CONTACTOR.out | DCDC.in_pos |  |  |  | tbc | Where the DC-DC takes its 72 V from is TBC |
| H09 | PACK.neg | DCDC.in_neg |  |  |  | tbc |  |

### Shinegle low voltage: key, F-N-R, throttle, sensors, programmer

| Wire | From | To | Size | Fuse | Via | Status | Note |
|---|---|---|---|---|---|---|---|
| S01 | KIT_KEY.out | ESTOP.in |  |  |  | planned (optional) | Without the e-stop, KIT_KEY goes straight to the lock relay or J1-1 |
| S02 | ESTOP.out | RELAYS2.COM2 |  |  |  | planned (optional) |  |
| S03 | RELAYS2.NC2 | SG1202.J1-1 | 1 mm² | 10 A |  | planned | KSI through 10 A fuse (manual). NC contact so a dead control box never strands you |
| S04 | KIT_KEY.out | FNR.COM |  |  |  | from_manual | Manual feeds the direction switch from the key |
| S05 | FNR.F | SG1202.J1-22 |  |  |  | from_manual |  |
| S06 | FNR.R | SG1202.J1-33 |  |  |  | from_manual |  |
| S07 | SG1202.J1-25 | THROTTLE.V12 |  |  |  | from_manual |  |
| S08 | THROTTLE.WIPER | SG1202.J1-16 |  |  |  | from_manual |  |
| S09 | THROTTLE.GND | SG1202.J1-18 |  |  |  | from_manual |  |
| S10 | THROTTLE.SW | RELAYS.COM6 |  |  |  | planned | Pedal switch wire cut and run through relay 6 (park brake interlock, docs/park-brake.md) |
| S10b | RELAYS.NC6 | SG1202.J1-9 |  |  |  | planned | NC contact: relay off = pedal switch works as normal, so a dead control box never strands you. Relay on (park brake on) = Shinegle sees the pedal as up, no drive |
| S11 | SG1202.J1-25 | MOTOR.SPD_12V |  |  |  | from_manual | Speed sensor plugs J6/J7 |
| S12 | MOTOR.SPD_A | SG1202.J1-31 |  |  |  | from_manual |  |
| S13 | MOTOR.SPD_B | SG1202.J1-32 |  |  |  | from_manual |  |
| S14 | MOTOR.SPD_GND | SG1202.J1-7 |  |  |  | from_manual |  |
| S15 | MOTOR.TEMP1 | SG1202.J1-8 |  |  |  | from_manual | Motor temp plugs J8/J9 |
| S16 | MOTOR.TEMP2 | SG1202.J1-7 |  |  |  | from_manual |  |
| S17 | SG1202.J1-6 | SPEEDO.SPD |  |  |  | from_manual (optional) | Speed pulse. Could also feed the Pico if CAN isn't fitted |
| S18 | SG1202.J3 | PROG.PLUG |  |  |  | tbc (optional) | Setup only. J3 to J1-25/28/29/7 TBC |

### 12 V power: battery, fuses, key, dash rail, bucks

| Wire | From | To | Size | Fuse | Via | Status | Note |
|---|---|---|---|---|---|---|---|
| P01 | BAT12.pos | FB.IN | 10 mm² | 60 A |  | planned | 60 A main fuse at the battery. Was 6 mm² in wiring.md, which the table only rates to 40 A |
| P02 | FB.F12 | KEY.BAT | 1 mm² | 7.5 A |  | planned |  |
| P03 | KEY.IGN | RAIL.BUS | 1 mm² | 7.5 A | Schottky diode 10 A | planned | Diode so relay 8 can't feed back into the key wire after key-off. Without it the Pico would see the key still on and never shut down |
| P04 | FB.F8 | RELAYS.COM8 | 1 mm² | 7.5 A |  | planned |  |
| P05 | RELAYS.NO8 | RAIL.BUS | 1 mm² | 7.5 A |  | planned | Power hold, in parallel with the key |
| P06 | RAIL.BUS | TVS.K | 1 mm² | 7.5 A |  | planned |  |
| P07 | RAIL.BUS | PI_BUCK.VIN | 1.5 mm² | 7.5 A |  | planned |  |
| P08 | RAIL.BUS | PICO_BUCK.VIN | 0.75 mm² | 2 A |  | planned | 2 A inline fuse |
| P09 | PI_BUCK.VOUT | PI5.5V | 1.5 mm² |  |  | planned | Short and thick, under 30 cm. Set usb_max_current_enable=1 |
| P10 | PICO_BUCK.VOUT | PICO.VSYS | 0.5 mm² |  |  | planned |  |
| P11 | PICO_BUCK.VOUT | RELAYS.JDVCC | 0.5 mm² |  |  | planned | Relay coils, about 0.6 A for 8 |
| P12 | PICO_BUCK.VOUT | RELAYS2.JDVCC | 0.5 mm² |  |  | planned (optional) |  |
| P13 | RAIL.BUS | SCREEN_PSU.VIN | 1 mm² | 3 A |  | tbc | Fuse size depends on the screen's draw |
| P14 | SCREEN_PSU.VOUT | SCREEN.DC_IN | 1 mm² |  |  | tbc |  |
| P15 | FB.F7 | RELAYS.COM7 | 1.5 mm² | 10 A |  | planned | Accessory 12 V, on with ignition |
| P20 | RELAYS.NO7 | GLOVE_USB.VIN | 0.75 mm² | 3 A |  | planned (optional) | 3 A inline fuse. Charges the RC phone with the key on; the control box may hold it on for a while after key-off (TBC) |
| P16 | BAT12.pos | AMP.B+ | 6 mm² | 40 A |  | planned (optional) | Own 40 A fuse at the battery. The amp pulls up to 33 A flat out, so 6 mm² (good to 40 A on the table) |
| P17 | RAIL.BUS | AMP.REM | 0.5 mm² | 2 A |  | planned (optional) | Remote turn-on, goes off with the rail |
| P18 | DCDC.out_pos | BAT12.pos |  |  |  | tbc | DC-DC charge lead. Size and fuse depend on its rating |
| P19 | BAT12.pos | EPS_ECU.B+ | 10 mm² | 60 A |  | planned (optional) | Own 60 A fuse and cable straight to the battery (Toyota fuses the Prius EPS at 60 A) |
| P22 | PI_BUCK.VOUT | MODEM_4G.V | 0.5 mm² |  |  | planned (optional) | Soldered lead to the V pin, from the Pi buck |

### Grounds (chassis, star point)

| Wire | From | To | Size | Fuse | Via | Status | Note |
|---|---|---|---|---|---|---|---|
| G01 | BAT12.neg | GND_STAR.G | 10 mm² |  |  | planned | Same size as the main feed |
| G02 | DCDC.out_neg | GND_STAR.G |  |  |  | tbc |  |
| G03 | TVS.A | GND_STAR.G | 1 mm² |  |  | planned |  |
| G04 | PI_BUCK.GND | GND_STAR.G | 1.5 mm² |  |  | planned |  |
| G05 | PI5.GND | PI_BUCK.GND | 1.5 mm² |  |  | planned |  |
| G06 | PICO_BUCK.GND | GND_STAR.G | 0.75 mm² |  |  | planned |  |
| G07 | PICO.GND | PICO_BUCK.GND | 0.5 mm² |  |  | planned | All control box boards share the Pico ground |
| G08 | SCREEN_PSU.GND | GND_STAR.G | 1 mm² |  |  | tbc |  |
| G09 | SCREEN.GND | SCREEN_PSU.GND | 1 mm² |  |  | tbc |  |
| G10 | AMP.GND | GND_STAR.G | 6 mm² |  |  | planned (optional) | Same size as the feed |
| G24 | GLOVE_USB.GND | GND_STAR.G | 0.75 mm² |  |  | planned (optional) |  |
| G11 | MOSFET.GND | GND_STAR.G | 4 mm² |  |  | planned | Carries the current of all 8 lights on the board (about 30 A with everything on) |
| G15 | BTS9.B- | GND_STAR.G | 1 mm² |  |  | planned |  |
| G33 | BEACON.GND | GND_STAR.G | 1 mm² |  |  | tbc | Beacon earth, or a good chassis earth on the roll cage |
| G16 | BTS4.B- | GND_STAR.G | 1.5 mm² |  |  | planned |  |
| G31 | BTS5.B- | GND_STAR.G | 1.5 mm² |  |  | planned |  |
| G32 | BTS6.B- | GND_STAR.G | 1.5 mm² |  |  | planned |  |
| G25 | BTS7.B- | GND_STAR.G | 1.5 mm² |  |  | planned |  |
| G26 | BTS8.B- | GND_STAR.G | 1 mm² |  |  | planned |  |
| G27 | HEAD_L.GND | GND_STAR.G | 1.5 mm² |  |  | tbc | Stock earth, keep it if it's good |
| G28 | HEAD_R.GND | GND_STAR.G | 1.5 mm² |  |  | tbc |  |
| G29 | TAIL_L.GND | GND_STAR.G | 1 mm² |  |  | tbc |  |
| G30 | TAIL_R.GND | GND_STAR.G | 1 mm² |  |  | tbc |  |
| G12 | BTS1.B- | GND_STAR.G | 1.5 mm² |  |  | planned |  |
| G13 | BTS2.B- | GND_STAR.G | 1.5 mm² |  |  | planned |  |
| G14 | BTS3.B- | GND_STAR.G | 2.5 mm² |  |  | planned |  |
| G17 | WINCH_SOL.GND | BAT12.neg | 35 mm² |  |  | planned | Winch return straight to the battery, cable from the winch kit |
| G37 | RELAYS.GND | PICO_BUCK.GND | 0.5 mm² |  |  | planned | Relay coil return (JD-VCC side) |
| G38 | RELAYS2.GND | PICO_BUCK.GND | 0.5 mm² |  |  | planned (optional) |  |
| G39 | MCP1.GND | PICO.GND |  |  |  | planned | Logic ground. Without it the board has no ground and never answers on I2C |
| G40 | MCP2.GND | PICO.GND |  |  |  | planned |  |
| G41 | ADS1.GND | PICO.GND |  |  |  | planned | Also the diff pot's low end (D10) |
| G42 | PCA.GND | PICO.GND |  |  |  | planned |  |
| G43 | PICO_CAN.GND | PICO.GND |  |  |  | planned |  |
| G44 | EPS_CAN.GND | PICO.GND |  |  |  | planned (optional) |  |
| G45 | OPTO.GND | PICO.GND |  |  |  | planned | 3.3 V side only. COM12 (12 V side) stays on the chassis ground (G19), so the opto still isolates |
| G46 | BTS1.GND | PICO.GND |  |  |  | planned | BTS7960 logic header ground, so the Pico's PWM has a reference. B- carries the load current |
| G47 | BTS2.GND | PICO.GND |  |  |  | planned |  |
| G48 | BTS3.GND | PICO.GND |  |  |  | planned |  |
| G49 | BTS4.GND | PICO.GND |  |  |  | planned |  |
| G50 | BTS5.GND | PICO.GND |  |  |  | planned |  |
| G51 | BTS6.GND | PICO.GND |  |  |  | planned |  |
| G52 | BTS7.GND | PICO.GND |  |  |  | planned |  |
| G53 | BTS8.GND | PICO.GND |  |  |  | planned |  |
| G54 | BTS9.GND | PICO.GND |  |  |  | planned |  |
| G55 | PI_CAN.GND | PI5.GND |  |  |  | planned | Header ground pin, with the CAN board's other leads |
| G56 | RC_CAN.GND | RC_PICO.GND |  |  |  | planned (optional) |  |
| G57 | RC_LVL.GND | RC_PICO.GND |  |  |  | planned (optional) |  |
| G58 | RC_DAC.GND | RC_PICO.GND |  |  |  | planned (optional) |  |
| G59 | RC_ADC.GND | RC_PICO.GND |  |  |  | planned (optional) |  |
| G60 | RC_REL.GND | RC_PICO.GND |  |  |  | planned (optional) |  |
| G19 | OPTO.COM12 | GND_STAR.G | 0.5 mm² |  |  | planned | 12 V side ground of the opto board |
| G20 | TRAILER.P3_EARTH | GND_STAR.G | 2.5 mm² |  |  | planned |  |
| G21 | TCAM_PLUG.GND | GND_STAR.G | 0.5 mm² |  |  | planned (optional) |  |
| G22 | EPS_ECU.GND | BAT12.neg | 10 mm² |  |  | planned (optional) |  |
| G23 | CAM_TRAILER.GND | TCAM_PLUG.GND | 0.5 mm² |  |  | planned (optional) | Earth the camera at the hitch, not through the 7-pin earth |
| G34 | CAM_REAR.GND | GND_STAR.G | 0.5 mm² |  |  | tbc | Or a good chassis earth near the camera |
| G61 | CAM_FRONT.GND | GND_STAR.G | 0.5 mm² |  |  | tbc | Or a good chassis earth near the camera |
| G36 | MODEM_4G.G | PI5.GND |  |  |  | planned (optional) | Ground with the UART leads |

### CAN buses: main Teryx bus and the steering bus

| Wire | From | To | Size | Fuse | Via | Status | Note |
|---|---|---|---|---|---|---|---|
| C01 | SG1202.CAN_H | PICO_CAN.CANH | 0.5 mm² |  |  | tbc | Twisted pair. CAN is optional on the SG1202, check it's fitted. Bit rate TBC (try 250k then 500k) |
| C02 | SG1202.CAN_L | PICO_CAN.CANL | 0.5 mm² |  |  | tbc |  |
| C03 | PICO_CAN.CANH | PI_CAN.CANH | 0.5 mm² |  |  | planned | 120 ohm at the Shinegle end and the Pi end. 60 ohm H to L with all off |
| C04 | PICO_CAN.CANL | PI_CAN.CANL | 0.5 mm² |  |  | planned |  |
| C05 | EPS_CAN.CANH | EPS_ECU.CANH | 0.5 mm² |  |  | planned (optional) | Own bus, 500 kbit/s, Toyota frames 0x0B4 and 0x2C4 |
| C06 | EPS_CAN.CANL | EPS_ECU.CANL | 0.5 mm² |  |  | planned (optional) |  |
| RC03 | PICO_CAN.CANH | RC_CAN.CANH | 0.5 mm² |  |  | planned (optional) | Short stub inside the control box, under 30 cm |
| RC04 | PICO_CAN.CANL | RC_CAN.CANL | 0.5 mm² |  |  | planned (optional) |  |

### Control box inside: Pico 2 and its boards

| Wire | From | To | Size | Fuse | Via | Status | Note |
|---|---|---|---|---|---|---|---|
| L01 | PICO.GP2 | PICO_CAN.SCK |  |  |  | planned | SPI under 10 cm |
| L02 | PICO.GP3 | PICO_CAN.SI |  |  |  | planned |  |
| L03 | PICO.GP4 | PICO_CAN.SO |  |  |  | planned |  |
| L04 | PICO.GP5 | PICO_CAN.CS |  |  |  | planned |  |
| L05 | PICO_CAN.INT | PICO.GP6 |  |  |  | planned |  |
| L06 | PICO.GP2 | EPS_CAN.SCK |  |  |  | planned (optional) |  |
| L07 | PICO.GP3 | EPS_CAN.SI |  |  |  | planned (optional) |  |
| L08 | PICO.GP4 | EPS_CAN.SO |  |  |  | planned (optional) |  |
| L09 | PICO.GP22 | EPS_CAN.CS |  |  |  | planned (optional) | GP22 freed from ADS1115 ALERT |
| L10 | PICO.GP26 | MCP1.SDA |  |  |  | planned | 4.7k pull-ups to 3.3 V, once for the whole bus |
| L11 | PICO.GP27 | MCP1.SCL |  |  |  | planned |  |
| L12 | PICO.GP26 | ADS1.SDA |  |  |  | planned |  |
| L13 | PICO.GP27 | ADS1.SCL |  |  |  | planned |  |
| L14 | PICO.GP26 | MCP2.SDA |  |  |  | planned |  |
| L15 | PICO.GP27 | MCP2.SCL |  |  |  | planned |  |
| L18 | MCP1.INTB | PICO.GP21 |  |  |  | planned |  |
| L19 | MCP1.A0 | RELAYS.IN1 |  |  |  | planned | light.rear (relay 1 now only feeds the trailer reverse pin) |
| L22 | MCP1.A3 | RELAYS.IN4 |  |  |  | planned | winch.in |
| L23 | MCP1.A4 | RELAYS.IN5 |  |  |  | planned | winch.out |
| L24 | MCP1.A5 | RELAYS.IN6 |  |  |  | planned | drive.park_block (park brake interlock) |
| L25 | MCP1.A6 | RELAYS.IN7 |  |  |  | planned | aux.accessory |
| L26 | MCP1.A7 | RELAYS.IN8 |  |  |  | planned | power.hold |
| L27 | MCP2.A0 | RELAYS2.IN1 |  |  |  | planned (optional) | steering enable |
| L28 | MCP2.A1 | RELAYS2.IN2 |  |  |  | planned (optional) | drive lock (opens the KSI line while locked and parked) |
| L29 | OPTO.OUT1 | MCP1.B0 |  |  |  | planned | in.ignition |
| L30 | OPTO.OUT2 | MCP1.B1 |  |  |  | planned | in.brake |
| L31 | OPTO.OUT3 | MCP1.B2 |  |  |  | planned | in.reverse |
| L32 | OPTO.OUT4 | MCP1.B3 |  |  |  | planned | in.tray_down |
| L33 | OPTO.OUT5 | MCP1.B4 |  |  |  | planned | in.tray_up |
| L34 | OPTO.OUT6 | MCP1.B5 |  |  |  | planned | in.winch_remote |
| L35 | OPTO.OUT7 | MCP1.B6 |  |  |  | planned | in.park |
| L36 | OPTO.OUT8 | MCP2.B0 |  |  |  | planned | in.trailer (not MCP1 B7: GPB7 is output only on newer chips) |
| L37 | PICO.3V3 | MCP1.VDD |  |  |  | planned |  |
| L38 | PICO.3V3 | ADS1.VDD |  |  |  | planned |  |
| L39 | PICO.3V3 | PICO_CAN.VCC |  |  |  | planned |  |
| L40 | PICO.3V3 | RELAYS.VCC |  |  |  | planned |  |
| L41 | PICO.3V3 | OPTO.VCC |  |  |  | planned |  |
| L42 | PICO.3V3 | MCP2.VDD |  |  |  | planned |  |
| L44 | PICO.3V3 | EPS_CAN.VCC |  |  |  | planned (optional) |  |
| L45 | PICO.3V3 | RELAYS2.VCC |  |  |  | planned (optional) |  |
| L46 | PICO.GP0 | DEBUG.RX |  |  |  | planned | UART0 TX |
| L47 | DEBUG.TX | PICO.GP1 |  |  |  | planned |  |
| L60 | PICO.GP26 | PCA.SDA |  |  |  | planned (optional) | soldered |
| L61 | PICO.GP27 | PCA.SCL |  |  |  | planned (optional) | soldered |
| L62 | PICO.3V3 | PCA.VCC |  |  |  | planned (optional) | soldered |

### 12 V signals into the control box (opto board)

| Wire | From | To | Size | Fuse | Via | Status | Note |
|---|---|---|---|---|---|---|---|
| I01 | KEY.IGN | OPTO.IN1 | 0.75 mm² | 7.5 A | 1 A diode | planned | Taken from the key side of the P03 diode, so the Pico sees key-off while relay 8 holds the rail. 0.75 mm² because the 7.5 A key fuse is upstream |
| I02 | BRAKE_SW.OUT | OPTO.IN2 | 0.5 mm² |  |  | tbc |  |
| I03 | FNR.R | OPTO.IN3 | 0.5 mm² |  | opto board | tbc | The F-N-R switch is on the Shinegle key line. If J1-1 runs at 72 V, this needs a 72 V rated input, not the 12 V opto |
| I04 | LIM_DN.NC | OPTO.IN4 | 0.5 mm² |  |  | planned | Normally closed, a broken wire reads as at the limit |
| I05 | LIM_UP.NC | OPTO.IN5 | 0.5 mm² |  |  | planned |  |
| I06 | HSW_WINCH.IN | OPTO.IN6 | 0.5 mm² |  | 1N4148 | planned | Each hand control taps in through its own small diode |
| I07 | HSW_WINCH.OUT | OPTO.IN6 | 0.5 mm² |  | 1N4148 | planned |  |
| I08 | HSW_CAB.IN | OPTO.IN6 | 0.5 mm² |  | 1N4148 | planned |  |
| I09 | HSW_CAB.OUT | OPTO.IN6 | 0.5 mm² |  | 1N4148 | planned |  |
| I10 | WINCH_SOL.REM_IN | OPTO.IN6 | 0.5 mm² |  | 1N4148 | tbc | Remote tap, on the remote's own line before its diode (WN21). Not on COIL_IN: that would also see relay 4 and make the Pico stop its own pull |
| I16 | WINCH_SOL.REM_OUT | OPTO.IN6 | 0.5 mm² |  | 1N4148 | tbc | Remote tap, out side |
| I11 | PARK_SW.OUT | OPTO.IN7 | 0.5 mm² |  |  | tbc | If the switch grounds, wire the opto input the other way round |
| I12 | TRAILER.REED_A | OPTO.IN8 | 0.5 mm² |  |  | tbc |  |
| I13 | FB.F6 | LIM_DN.C | 0.5 mm² | 3 A |  | planned | Limit switch and reed feed from a small fused 12 V |
| I14 | LIM_DN.C | LIM_UP.C | 0.5 mm² |  |  | planned |  |
| I15 | LIM_UP.C | TRAILER.REED_B | 0.5 mm² |  |  | tbc |  |

### Lights

| Wire | From | To | Size | Fuse | Via | Status | Note |
|---|---|---|---|---|---|---|---|
| LT01 | FB.F1 | LB1.pos | 1.5 mm² | 15 A |  | planned |  |
| LT02 | FB.F2 | LB2.pos | 1.5 mm² | 15 A |  | planned |  |
| LT03 | FB.F2 | LB3.pos | 1.5 mm² | 15 A |  | planned |  |
| LT04 | FB.F1 | LB4.pos | 1.5 mm² | 15 A |  | planned |  |
| LT05 | FB.F7 | LB_INT.pos | 1 mm² | 10 A |  | planned |  |
| LT06 | LB1.neg | MOSFET.OUT1 | 1.5 mm² |  |  | planned |  |
| LT07 | LB2.neg | MOSFET.OUT2 | 1.5 mm² |  |  | planned |  |
| LT08 | LB3.neg | MOSFET.OUT3 | 1.5 mm² |  |  | planned |  |
| LT09 | LB4.neg | MOSFET.OUT4 | 1.5 mm² |  |  | planned |  |
| LT10 | LB_INT.neg | MOSFET.OUT5 | 1 mm² |  |  | planned |  |
| LT11 | PICO.GP16 | MOSFET.IN1 |  |  |  | planned | light.front_1 PWM |
| LT12 | PICO.GP17 | MOSFET.IN2 |  |  |  | planned | light.front_2 PWM |
| LT13 | PICO.GP18 | MOSFET.IN3 |  |  |  | planned | light.front_3 PWM |
| LT14 | PICO.GP19 | MOSFET.IN4 |  |  |  | planned | light.front_4 PWM |
| LT15 | PICO.GP20 | MOSFET.IN5 |  |  |  | planned | light.interior PWM |
| LT16 | FB.F3 | RELAYS.COM1 | 1.5 mm² | 15 A |  | planned |  |
| LT17 | FB.F3 | FLOOD_L.pos | 1.5 mm² | 15 A |  | planned | Always live, the MOSFET switches the - side |
| LT18 | FB.F3 | FLOOD_R.pos | 1.5 mm² | 15 A |  | planned |  |
| LT19 | FLOOD_L.neg | MOSFET.OUT7 | 1.5 mm² |  |  | planned |  |
| LT20 | FLOOD_R.neg | MOSFET.OUT8 | 1.5 mm² |  |  | planned |  |
| LT21 | PCA.PWM11 | MOSFET.IN7 |  |  |  | planned | light.flood_l PWM |
| LT22 | PCA.PWM12 | MOSFET.IN8 |  |  |  | planned | light.flood_r PWM |
| LT23 | FB.IN | FB2.IN | 4 mm² | 30 A |  | planned | Own 30 A inline fuse off the 12-way's feed stud |
| LT24 | FB2.F1 | BTS4.B+ | 1.5 mm² | 10 A |  | planned |  |
| LT25 | FB2.F2 | BTS5.B+ | 1.5 mm² | 10 A |  | planned |  |
| LT26 | FB2.F3 | BTS6.B+ | 1.5 mm² | 10 A |  | planned |  |
| LT27 | FB2.F3 | BTS7.B+ | 1.5 mm² | 10 A |  | planned |  |
| LT28 | BTS4.M+ | HEAD_L.LO | 1.5 mm² |  | Schottky diode 5 A | planned | light.head_l_low. The diode stops the backup toggle feeding back into the BTS7960 |
| LT29 | BTS4.M- | HEAD_L.HI | 1.5 mm² |  | Schottky diode 5 A | planned | light.head_l_high |
| LT30 | BTS5.M+ | HEAD_R.LO | 1.5 mm² |  | Schottky diode 5 A | planned | light.head_r_low |
| LT31 | BTS5.M- | HEAD_R.HI | 1.5 mm² |  | Schottky diode 5 A | planned | light.head_r_high |
| LT32 | BTS6.M+ | TAIL_L.TAIL | 1 mm² |  | Schottky diode 5 A | planned | light.tail_l |
| LT33 | BTS6.M- | TAIL_L.STOP | 1 mm² |  | Schottky diode 5 A | planned | light.brake_l |
| LT34 | BTS7.M+ | TAIL_R.TAIL | 1 mm² |  | Schottky diode 5 A | planned | light.tail_r |
| LT35 | BTS7.M- | TAIL_R.STOP | 1 mm² |  | Schottky diode 5 A | planned | light.brake_r |
| LT36 | PCA.PWM1 | BTS4.RPWM |  |  |  | planned | light.head_l_low PWM |
| LT37 | PCA.PWM2 | BTS4.LPWM |  |  |  | planned | light.head_l_high PWM |
| LT38 | PCA.PWM3 | BTS5.RPWM |  |  |  | planned | light.head_r_low PWM |
| LT39 | PCA.PWM4 | BTS5.LPWM |  |  |  | planned | light.head_r_high PWM |
| LT40 | PCA.PWM5 | BTS6.RPWM |  |  |  | planned | light.tail_l PWM |
| LT41 | PCA.PWM6 | BTS6.LPWM |  |  |  | planned | light.brake_l PWM |
| LT42 | PCA.PWM7 | BTS7.RPWM |  |  |  | planned | light.tail_r PWM |
| LT43 | PCA.PWM8 | BTS7.LPWM |  |  |  | planned | light.brake_r PWM |
| LT44 | PCA.PWM15 | BTS4.EN |  |  |  | planned | R_EN + L_EN joined, 10k to ground |
| LT45 | PCA.PWM15 | BTS5.EN |  |  |  | planned |  |
| LT46 | PCA.PWM15 | BTS6.EN |  |  |  | planned |  |
| LT47 | PCA.PWM15 | BTS7.EN |  |  |  | planned |  |
| LT48 | BRAKE_SW.OUT | TAIL_L.STOP | 1 mm² |  | Schottky diode 5 A | planned | Brake lights always work, whatever the Pico does |
| LT49 | BRAKE_SW.OUT | TAIL_R.STOP | 1 mm² |  | Schottky diode 5 A | planned |  |
| LT50 | FB2.F5 | LIMP_SW.IN | 1.5 mm² | 10 A |  | planned |  |
| LT51 | LIMP_SW.OUT | HEAD_L.LO | 1.5 mm² |  | Schottky diode 5 A | planned | Backup toggle on = low beams at full, even with the control box dead |
| LT52 | LIMP_SW.OUT | HEAD_R.LO | 1.5 mm² |  | Schottky diode 5 A | planned |  |
| LT54 | LIMP_SW.OUT | TAIL_L.TAIL | 1 mm² |  | Schottky diode 5 A | planned | Tails on with the backup toggle too |
| LT55 | LIMP_SW.OUT | TAIL_R.TAIL | 1 mm² |  | Schottky diode 5 A | planned |  |
| LT62 | LIMP_SW.OUT | TRAILER.P7_TAIL | 1 mm² |  | Schottky diode 5 A | planned | Trailer tail lights on the backup toggle too |
| LT63 | FB2.F6 | BRAKE_SW.IN | 1 mm² | 10 A |  | tbc | Brake switch feed, always live |
| LT56 | FB2.F4 | BTS9.B+ | 1 mm² | 5 A |  | planned |  |
| LT57 | BTS9.M+ | BEACON.AMBER | 0.75 mm² |  |  | planned | light.beacon (amber) |
| LT58 | PCA.PWM13 | BTS9.RPWM |  |  |  | planned | light.beacon: flashed at 3 Hz by the Pico |
| LT59 | BTS9.M- | BEACON.WHITE | 0.75 mm² |  |  | planned | light.beacon_white |
| LT60 | PCA.PWM14 | BTS9.LPWM |  |  |  | planned | light.beacon_white: 3 Hz, opposite amber, stopped only |
| LT61 | PCA.PWM15 | BTS9.EN |  |  |  | planned |  |
| LT64 | PICO.3V3 | BTS4.VCC |  |  |  | planned | Logic supply, like BTS1-3 |
| LT65 | PICO.3V3 | BTS5.VCC |  |  |  | planned |  |
| LT66 | PICO.3V3 | BTS6.VCC |  |  |  | planned |  |
| LT67 | PICO.3V3 | BTS7.VCC |  |  |  | planned |  |
| LT68 | PICO.3V3 | BTS8.VCC |  |  |  | planned |  |
| LT69 | PICO.3V3 | BTS9.VCC |  |  |  | planned |  |

### Winch

| Wire | From | To | Size | Fuse | Via | Status | Note |
|---|---|---|---|---|---|---|---|
| WN01 | BAT12.pos | BRK_WINCH.in | 35 mm² | 250 A |  | planned | Cable that came with the winch |
| WN02 | BRK_WINCH.out | WINCH_SOL.B+ | 35 mm² | 250 A |  | planned |  |
| WN04 | WINCH_SOL.M1 | WINCH_MOTOR.M1 | 35 mm² |  |  | confirmed |  |
| WN05 | WINCH_SOL.M2 | WINCH_MOTOR.M2 | 35 mm² |  |  | confirmed |  |
| WN06 | WINCH_SOL.REMOTE | WINCH_REMOTE.PLUG |  |  |  | confirmed | XBull remote stays as a backup |
| WN07 | FB.F5 | RELAYS.COM4 | 0.5 mm² | 5 A |  | planned |  |
| WN08 | FB.F5 | RELAYS.COM5 | 0.5 mm² | 5 A |  | planned |  |
| WN10 | RELAYS.NO4 | WINCH_SOL.COIL_IN | 0.5 mm² | 5 A | 3 A diode (1N5408) | planned | winch.in. Never the motor current through the relay board |
| WN11 | RELAYS.NO5 | WINCH_SOL.COIL_OUT | 0.5 mm² | 5 A | 3 A diode (1N5408) | planned | winch.out, interlocked with in |
| WN19 | WINCH_SOL.COIL_IN | WINCH_SOL.GND |  |  | flyback diode 1N5408 (band to the coil wire) | tbc | Across the coil, at the solenoid box, unless the box already has one. Stops the coil's kick arcing the relay contacts and spiking the 12 V |
| WN20 | WINCH_SOL.COIL_OUT | WINCH_SOL.GND |  |  | flyback diode 1N5408 (band to the coil wire) | tbc |  |
| WN21 | WINCH_SOL.REM_IN | WINCH_SOL.COIL_IN | 0.5 mm² |  | 3 A diode (1N5408) | tbc | Inside the solenoid box: cut the remote socket's in wire off the coil and rejoin it through this diode |
| WN22 | WINCH_SOL.REM_OUT | WINCH_SOL.COIL_OUT | 0.5 mm² |  | 3 A diode (1N5408) | tbc |  |
| WN13 | FB.F6 | HSW_WINCH.FEED | 0.5 mm² | 5 A |  | planned |  |
| WN14 | FB.F6 | HSW_CAB.FEED | 0.5 mm² | 5 A |  | planned |  |
| WN15 | HSW_WINCH.IN | WINCH_SOL.COIL_IN | 0.5 mm² | 5 A | 3 A diode (1N5408) | planned |  |
| WN16 | HSW_WINCH.OUT | WINCH_SOL.COIL_OUT | 0.5 mm² | 5 A | 3 A diode (1N5408) | planned |  |
| WN17 | HSW_CAB.IN | WINCH_SOL.COIL_IN | 0.5 mm² | 5 A | 3 A diode (1N5408) | planned |  |
| WN18 | HSW_CAB.OUT | WINCH_SOL.COIL_OUT | 0.5 mm² | 5 A | 3 A diode (1N5408) | planned |  |

### Drive: 4WD, diff lock, tray, power steering

| Wire | From | To | Size | Fuse | Via | Status | Note |
|---|---|---|---|---|---|---|---|
| D01 | PICO.GP7 | BTS1.RPWM |  |  |  | planned | act.diff |
| D02 | PICO.GP8 | BTS1.LPWM |  |  |  | planned |  |
| D03 | PICO.GP9 | BTS1.EN |  |  |  | planned | R_EN and L_EN joined |
| D04 | BTS1.IS | PICO.GP28 |  |  | 2 diodes + 1k to ground | planned | an.diff_current |
| D05 | FB.F9 | BTS1.B+ | 1.5 mm² | 10 A |  | planned |  |
| D06 | BTS1.M+ | ACT_DIFF.M+ | 1.5 mm² | 10 A |  | planned | Wrong way? Change DIFF_LOCK_DIR in firmware, not the wires |
| D07 | BTS1.M- | ACT_DIFF.M- | 1.5 mm² | 10 A |  | planned |  |
| D08 | ADS1.VDD | ACT_DIFF.POT_HI |  |  |  | planned | Pot on 3.3 V, never 12 V |
| D09 | ACT_DIFF.POT_W | ADS1.A0 |  |  |  | planned | an.diff_pos |
| D10 | ACT_DIFF.POT_LO | ADS1.GND |  |  |  | planned |  |
| D11 | PICO.GP10 | BTS2.RPWM |  |  |  | planned | act.4wd |
| D12 | PICO.GP11 | BTS2.LPWM |  |  |  | planned |  |
| D13 | PICO.GP12 | BTS2.EN |  |  |  | planned |  |
| D14 | BTS2.IS | ADS1.A2 |  |  | 2 diodes + 1k to ground | planned | an.4wd_current |
| D15 | FB.F10 | BTS2.B+ | 1.5 mm² | 10 A |  | planned |  |
| D16 | BTS2.M+ | ACT_4WD.M+ | 1.5 mm² | 10 A |  | tbc |  |
| D17 | BTS2.M- | ACT_4WD.M- | 1.5 mm² | 10 A |  | tbc |  |
| D18 | PICO.GP13 | BTS3.RPWM |  |  |  | planned | act.tray |
| D19 | PICO.GP14 | BTS3.LPWM |  |  |  | planned |  |
| D20 | PICO.GP15 | BTS3.EN |  |  |  | planned |  |
| D21 | BTS3.IS | ADS1.A3 |  |  | 2 diodes + 1k to ground | planned | an.tray_current |
| D22 | FB.F11 | BTS3.B+ | 2.5 mm² | 15 A |  | planned |  |
| D23 | BTS3.M+ | ACT_TRAY.M+ | 2.5 mm² | 15 A |  | planned |  |
| D24 | BTS3.M- | ACT_TRAY.M- | 2.5 mm² | 15 A |  | planned |  |
| D25 | PICO.3V3 | BTS1.VCC |  |  |  | planned |  |
| D26 | PICO.3V3 | BTS2.VCC |  |  |  | planned |  |
| D27 | PICO.3V3 | BTS3.VCC |  |  |  | planned |  |
| D28 | BAT12.pos | ADS1.A1 | 0.5 mm² | 1 A | divider 10k / 2.2k + 3.3 V zener | planned | an.aux_12v. Fuse the sense lead |
| D31 | RAIL.BUS | RELAYS2.COM1 | 0.5 mm² | 3 A |  | planned (optional) | Steering ignition feed through relay 9, so the lock and RC kill can turn assist off |
| D32 | RELAYS2.NO1 | EPS_ECU.IG | 0.5 mm² | 3 A |  | tbc (optional) |  |
| D33 | EPS_ECU.MOTOR | EPS_COL.MOTOR |  |  |  | tbc (optional) | Toyota's own plug, keep it from the wrecker |

### Trailer plug and trailer camera

| Wire | From | To | Size | Fuse | Via | Status | Note |
|---|---|---|---|---|---|---|---|
| T01 | FB.F4 | BTS8.B+ | 1 mm² | 7.5 A |  | planned |  |
| T02 | BTS8.M+ | TRAILER.P7_TAIL | 1 mm² |  | Schottky diode 5 A | planned | light.trailer_tail (dimmable). Diode so the backup toggle (LT62) can't feed back into the BTS7960 |
| T04 | BTS8.M- | TRAILER.P6_STOP | 1 mm² |  | Schottky diode 5 A | planned | light.trailer_stop. Diode so the brake switch backup (T05) can't feed back into the BTS7960 |
| T18 | PCA.PWM9 | BTS8.RPWM |  |  |  | planned | light.trailer_tail PWM |
| T19 | PCA.PWM10 | BTS8.LPWM |  |  |  | planned | light.trailer_stop PWM |
| T20 | PCA.PWM15 | BTS8.EN |  |  |  | planned |  |
| T05 | BRAKE_SW.OUT | TRAILER.P6_STOP | 1 mm² |  | Schottky diode 5 A | tbc | Trailer brake lights still work with the control box off |
| T06 | RELAYS.NO1 | TRAILER.P2_REV | 1.5 mm² | 15 A |  | tbc (optional) | Reversing pin. Relay 1 follows the rear floods, so trailer reverse lights come on with them |
| T07 | RELAYS.NO7 | TCAM_PLUG.V12 | 0.5 mm² | 2 A |  | planned (optional) | 2 A inline fuse. Runs while driving, not just reversing |
| T08 | TCAM_PLUG.V12 | CAM_TRAILER.V12 | 0.5 mm² | 2 A |  | planned (optional) |  |
| T09 | CAM_TRAILER.VID | TCAM_PLUG.VID |  |  |  | planned (optional) |  |
| T10 | CAM_TRAILER.VID_GND | TCAM_PLUG.VID_GND |  |  |  | planned (optional) |  |
| T11 | TCAM_PLUG.VID | TCAM_DONGLE.VID |  |  |  | planned (optional) | Shielded video cable |
| T13 | FB.IN | TCAM_PLUG.LB_POS | 1.5 mm² | 10 A |  | planned (optional) | Own 10 A inline fuse off the fuse block's feed stud (the 12-way is full) |
| T14 | TCAM_PLUG.LB_POS | LB_TRL.pos | 1.5 mm² |  |  | planned (optional) |  |
| T15 | LB_TRL.neg | TCAM_PLUG.LB_NEG | 1.5 mm² |  |  | planned (optional) |  |
| T16 | TCAM_PLUG.LB_NEG | MOSFET.OUT6 | 1.5 mm² |  |  | planned (optional) |  |
| T17 | PCA.PWM0 | MOSFET.IN6 |  |  |  | planned (optional) | light.trailer PWM (dimmable) |
| T12 | TCAM_PLUG.VID_GND | TCAM_DONGLE.VID_GND |  |  |  | planned (optional) |  |

### Dash computer: Pi 5, screen, cameras, USB, audio

| Wire | From | To | Size | Fuse | Via | Status | Note |
|---|---|---|---|---|---|---|---|
| X01 | PI5.HDMI0 | SCREEN.HDMI |  |  |  | planned |  |
| X02 | SCREEN.USB | PI5.USB2_B |  |  |  | planned | Touch. Screen only does touch over USB. Right-angle lead, cable-tied to the box |
| X03 | CAM_REAR.VID | TCAM_DONGLE.VID_R |  |  |  | tbc | Shielded video lead, soldered |
| X05 | RELAYS.NO7 | CAM_REAR.V12 | 0.5 mm² | 2 A |  | tbc | 2 A inline fuse. On with the key, like the trailer camera |
| X03b | CAM_REAR.VID_GND | TCAM_DONGLE.VID_R_GND |  |  |  | tbc |  |
| X04 | TCAM_DONGLE.CSI | PI5.CSI1 |  |  |  | tbc | Camera ribbon, 2nd port |
| X07 | CARPLAY.USB | PI5.USB2_A |  |  |  | planned (optional) | CarPlay dongle is USB only. Right-angle lead, dongle zip-tied down inside the box |
| X11 | CAM_FRONT.VID | TCAM_DONGLE.VID_F |  |  |  | tbc | Shielded video lead to video board input 3, soldered |
| X11b | CAM_FRONT.VID_GND | TCAM_DONGLE.VID_F_GND |  |  |  | tbc |  |
| X12 | RELAYS.NO7 | CAM_FRONT.V12 | 0.5 mm² | 2 A |  | tbc | 2 A inline fuse. On with the key, like the rear camera |
| X13 | AIHAT.PCIE | PI5.PCIE |  |  |  | placeholder (optional) | Keep the PCIe port free for this |
| X14 | AIHAT.HDR | PI5.HAT_HDR |  |  |  | placeholder (optional) | 16 mm stacking header over the Active Cooler |
| X15 | PI5.P1_3V3 | PI_CAN.VCC |  |  |  | planned |  |
| X16 | PI5.P23_SCLK | PI_CAN.SCK |  |  |  | planned |  |
| X17 | PI5.P19_MOSI | PI_CAN.SI |  |  |  | planned |  |
| X18 | PI_CAN.SO | PI5.P21_MISO |  |  |  | planned |  |
| X19 | PI5.P24_CE0 | PI_CAN.CS |  |  |  | planned |  |
| X20 | PI_CAN.INT | PI5.P22_GPIO25 |  |  |  | planned |  |
| X21 | DAC_HAT.OUT | AMP.IN |  |  |  | planned (optional) | 3.5 mm to 2x RCA lead out through the Pi box's spare PG7 gland, then a ground loop isolator at the amp |
| X32 | PI5.P8_TXD | MODEM_4G.R |  |  |  | placeholder (optional) | Soldered lead, 115200 baud |
| X33 | MODEM_4G.T | PI5.P10_RXD |  |  |  | placeholder (optional) | Soldered lead. Measure T first: 3.3 V ok, else BSS138 |
| X25 | PI5.P12_GPIO18 | DAC_HAT.BCK |  |  |  | planned (optional) | jumper lead |
| X26 | PI5.P35_GPIO19 | DAC_HAT.LRCK |  |  |  | planned (optional) | jumper lead |
| X27 | PI5.P40_GPIO21 | DAC_HAT.DIN |  |  |  | planned (optional) | jumper lead |
| X30 | PI5.P2_5V | DAC_HAT.V5 |  |  |  | planned (optional) | jumper lead |
| X31 | DAC_HAT.GND | PI5.GND |  |  |  | planned (optional) | jumper lead |
| X22 | AMP.SPK | SPEAKERS.IN |  |  |  | planned (optional) |  |
| X34 | AMP.SUB | SUB.IN |  |  |  | planned (optional) | Amp ch 3 + 4 bridged (ch 3 + and ch 4 -, check the amp's label) |
| X23 | PI5.P3_SDA | IMU.SDA |  |  |  | planned (optional) |  |
| X35 | PI5.P17_3V3 | IMU.VCC |  |  |  | planned (optional) |  |
| X36 | IMU.GND | PI5.GND |  |  |  | planned (optional) |  |
| X24 | PI5.P5_SCL | IMU.SCL |  |  |  | planned (optional) |  |

### RC box: steering by remote (fake torque sensor)

| Wire | From | To | Size | Fuse | Via | Status | Note |
|---|---|---|---|---|---|---|---|
| RC01 | PICO_BUCK.VOUT | RC_PICO.VSYS | 0.5 mm² |  |  | planned (optional) |  |
| RC02 | RC_PICO.GND | PICO_BUCK.GND | 0.5 mm² |  |  | planned (optional) | Same ground as the control box Pico |
| RC05 | RC_PICO.GP2 | RC_CAN.SCK |  |  |  | planned (optional) |  |
| RC06 | RC_PICO.GP3 | RC_CAN.SI |  |  |  | planned (optional) |  |
| RC07 | RC_PICO.GP4 | RC_CAN.SO |  |  |  | planned (optional) |  |
| RC08 | RC_PICO.GP5 | RC_CAN.CS |  |  |  | planned (optional) |  |
| RC09 | RC_CAN.INT | RC_PICO.GP6 |  |  |  | planned (optional) |  |
| RC10 | RC_PICO.3V3 | RC_CAN.VCC |  |  |  | planned (optional) |  |
| RC11 | RC_PICO.3V3 | RC_LVL.LV |  |  |  | planned (optional) |  |
| RC12 | PICO_BUCK.VOUT | RC_LVL.HV |  |  |  | planned (optional) |  |
| RC13 | RC_PICO.GP8 | RC_LVL.LV1 |  |  |  | planned (optional) | SDA |
| RC14 | RC_PICO.GP9 | RC_LVL.LV2 |  |  |  | planned (optional) | SCL |
| RC15 | RC_LVL.HV1 | RC_DAC.SDA |  |  |  | planned (optional) |  |
| RC16 | RC_LVL.HV2 | RC_DAC.SCL |  |  |  | planned (optional) |  |
| RC17 | RC_LVL.HV1 | RC_ADC.SDA |  |  |  | planned (optional) |  |
| RC18 | RC_LVL.HV2 | RC_ADC.SCL |  |  |  | planned (optional) |  |
| RC19 | PICO_BUCK.VOUT | RC_DAC.VDD |  |  |  | planned (optional) |  |
| RC20 | PICO_BUCK.VOUT | RC_ADC.VDD |  |  |  | planned (optional) |  |
| RC21 | PICO_BUCK.VOUT | RC_REL.VCC |  |  |  | planned (optional) |  |
| RC22 | RC_PICO.GP10 | RC_REL.IN |  |  |  | planned (optional) | High = RC steering. Pico reset or unpowered = relay off = real sensor |
| RC23 | EPS_COL.TRQ1 | RC_REL.NC1 | 0.5 mm² |  |  | tbc (optional) | Cut into Toyota's torque sensor lead; twisted with TRQ2 |
| RC24 | EPS_COL.TRQ2 | RC_REL.NC2 | 0.5 mm² |  |  | tbc (optional) |  |
| RC25 | RC_DAC.VOUTA | RC_REL.NO1 |  |  |  | planned (optional) |  |
| RC26 | RC_DAC.VOUTB | RC_REL.NO2 |  |  |  | planned (optional) |  |
| RC27 | RC_REL.COM1 | EPS_ECU.TRQ1 | 0.5 mm² |  |  | tbc (optional) |  |
| RC28 | RC_REL.COM2 | EPS_ECU.TRQ2 | 0.5 mm² |  |  | tbc (optional) |  |
| RC29 | RC_REL.COM1 | RC_ADC.A0 |  |  |  | planned (optional) | Read back what the ECU actually sees |
| RC30 | RC_REL.COM2 | RC_ADC.A1 |  |  |  | planned (optional) |  |
| RC31 | PICO_BUCK.VOUT | RC_ANGLE.VCC | 0.5 mm² |  |  | tbc (optional) |  |
| RC32 | RC_ANGLE.OUT | RC_ADC.A2 | 0.5 mm² |  |  | tbc (optional) | Screened lead from the column |
| RC33 | RC_ANGLE.GND | PICO_BUCK.GND | 0.5 mm² |  |  | tbc (optional) |  |

## Devices

| ID | Device | Where | Status | Notes |
|---|---|---|---|---|
| PACK | Traction battery pack | hv | tbc | 72 V. Size TBC (the range maths assumes 7.5 kWh) |
| HV_ISO | 150 A air-break switch | hv | from_manual | SG12X2 manual Fig. 2 puts B+ through it |
| CONTACTOR | Main contactor | hv | tbc | SG1810 fault 13 is "main contactor or brake fault", so there is probably one. Coil wiring not in any manual we have |
| SG1202 | Shinegle SG1202 controller | hv | from_manual | Full J1 pinout in config/shinegle-sg1202.yaml and docs/img/sg1202-wiring.svg See [`docs/shinegle-controller.md`](../../docs/shinegle-controller.md). |
| MOTOR | 7.5 kW AC motor | hv | confirmed |  |
| DCDC | DC-DC converter 72 V to 12 V | hv | tbc | Charges the 12 V battery. Rating TBC; it decides how long winch + steering can run |
| KIT_KEY | Shinegle kit key switch | cab | tbc | The kit comes with its own key switch. Is it the Teryx key, or a second one? |
| ESTOP | E-stop button | cab | planned (optional) | For RC mode. In series with KSI so it cuts drive with no software See [`docs/power-steering-rc.md`](../../docs/power-steering-rc.md). |
| FNR | F-N-R switch | cab | planned | Physical switch straight to the controller. The reverse side is also tapped for the control box |
| THROTTLE | Throttle pedal (kit accelerator) | cab | from_manual |  |
| SPEEDO | Shinegle dash / speed panel | cab | from_manual (optional) |  |
| PROG | SG1810 handheld programmer | cab | from_manual (optional) | Only plugged in for setup. Carries 12 V, never into USB See [`docs/shinegle-sg1810-programmer.md`](../../docs/shinegle-sg1810-programmer.md). |
| BAT12 | 12 V aux battery | engine_bay | confirmed | Kept after the conversion. Charged by the DC-DC |
| GND_STAR | Ground point (star) | engine_bay | planned | One solid chassis ground near the fuse block. Every 12 V ground goes here |
| FB | Blade fuse block | cab | tbc | 12 fuses in use. Small loads that can go out together share a fuse (front bars in pairs, trailer tail + stop, interior bar + accessory). All four front bars are NOT on one fuse, so one fault can't black out the front at night. The winch, control box power, key, power hold and each actuator keep their own. Sam's 12-way (in the post) is used, so it is full with no spares; add a small 6-way next to it if more circuits come |
| FB2 | Small 6-way blade fuse block (stock lights + beacon) | cab | planned | Next to the 12-way, which is full. Fed off the 12-way's feed stud through its own 30 A fuse. All 6 ways used (way 6 feeds the stock brake switch so the brake lights are on a known fuse, always live) |
| KEY | Teryx key switch | cab | confirmed |  |
| RAIL | Dash 12 V rail | dash | planned | Key OR relay 8 (power hold). Stays up after key-off until the Pico lets go See [`docs/wiring.md`](../../docs/wiring.md). |
| TVS | 1.5KE18A TVS diode | dash | planned | Clamps spikes on the dash rail |
| PI_BUCK | Potted 5 V 10 A buck (12/24 V in) | dash | planned | Sealed car-type 12/24 V to 5 V 10 A (50 W) buck, input 8-35 V or wider. Feeds the Pi 5 (about 16 W with the AI HAT+ 2) and the 4G board (2 A peaks), so about 30 W worst case of its 50 W. Wide input rides out spikes the Mini560 (20 V max) couldn't |
| PICO_BUCK | 5 V 5 A buck (Sam's, control box) | control_box | planned |  |
| SCREEN_PSU | Screen 12 V supply | dash | tbc | LTC3780 buck-boost board (5-32 V in, set to 12.0 V, 80 W) in the Pi box. Keeps the screen on a steady 12 V while the battery swings 11-14.4 V. No reverse-polarity protection, so it sits after the fuse. Skip it if the screen's own board says 9-36 V in |
| PICO | Raspberry Pi Pico 2 | control_box | planned | Talks to the Pi over CAN only. No USB lead to the Pi; reflash with a laptop on its own USB port in the workshop See [`docs/io-list.md`](../../docs/io-list.md). |
| DEBUG | Debug UART header | control_box | planned | Inside the box. Vehicle lock workshop reset |
| PICO_CAN | MCP2515 CAN module (control box) | control_box | planned | Blue AliExpress MCP2515 board (8 MHz crystal) with its 5 V TJA1050 swapped for a 3.3 V SN65HVD230 (same pins), so the whole board runs on 3.3 V. Never fit one with the TJA1050 still on: it puts 5 V on the Pico pins |
| EPS_CAN | MCP2515 CAN module (steering bus) | control_box | planned (optional) | Own 500 kbit/s bus to the steering ECU. INT not wired, the Pico polls it for the ECU's replies See [`docs/power-steering-wrecker.md`](../../docs/power-steering-wrecker.md). |
| MCP1 | MCP23017 I/O expander (0x20) | control_box | planned |  |
| MCP2 | Second MCP23017 (0x21) | control_box | planned | Steering enable and drive lock relays, and the trailer input on B0. Newer MCP23017 chips say GPA7/GPB7 are outputs only (Microchip datasheet rev D on), so the trailer input moved here off MCP1 B7 See [`docs/vehicle-lock.md`](../../docs/vehicle-lock.md). |
| PCA | PCA9685 16-ch PWM board (0x40) | control_box | planned (optional) | Every light that isn't a front bar or the cabin bar dims through this (docs/lights.md). Wires soldered straight to the pads, no header pins. VCC 3.3 V so the outputs are 3.3 V, which the MOSFET boards (3-20 V input) and the BTS7960s (3.3 V logic like BTS1-3) take. Leave V+ (servo power) empty. OE tied low on the board. PWM0 trailer bar, 1-10 stock lights on BTS7960 4-8, 11-12 rear floods, 13-14 beacon amber / white on BTS7960 9, 15 BTS7960 enable. All outputs are off at power-up |
| ADS1 | ADS1115 ADC (0x48) | control_box | planned | ALERT pin left free so GP22 can be the steering CAN chip select (read "ready" over I2C) |
| OPTO | 8-ch opto board (PC817, 12 V in) | control_box | planned | All 8 channels used. OUT8 (trailer) goes to MCP2 B0. A second 8-ch board (AliExpress cart) gives spare inputs on MCP2 B1-B6 (B7 is output only) |
| RELAYS | 16-ch relay board, channels 1-8 | control_box | planned | One 16-channel board of mechanical 5 V relays with opto and JD-VCC jumper (AliExpress cart), in an aux box next to the control box. RELAYS2 is channels 9-16 of the same board. The solid state G3MB-202P board Sam has is AC only and won't turn off on 12 V DC. JD-VCC jumper off, coils on 5 V, inputs from 3.3 V |
| RELAYS2 | 16-ch relay board, channels 9-16 (2 used, 6 spare) | control_box | planned (optional) | Same board as RELAYS. Relay 9 steering enable, relay 10 drive lock (uses the NC contact) |
| BTS1 | BTS7960 1 (front diff) | control_box | confirmed |  |
| BTS2 | BTS7960 2 (2WD/4WD) | control_box | planned |  |
| BTS3 | BTS7960 3 (tray) | control_box | planned |  |
| BTS4 | BTS7960 4 (left headlight low / high) | control_box | planned | Used as two high-side switches, not a motor bridge. VCC from the Pico 3.3 V like BTS1-3. EN (R_EN + L_EN) from PCA9685 PWM15 with a 10k to ground, so the lamps stay off until the Pico is running |
| BTS5 | BTS7960 5 (right headlight low / high) | control_box | planned |  |
| BTS6 | BTS7960 6 (left tail / brake) | control_box | planned |  |
| BTS7 | BTS7960 7 (right tail / brake) | control_box | planned |  |
| BTS8 | BTS7960 8 (trailer tail / stop) | control_box | planned |  |
| BTS9 | BTS7960 9 (roof beacon amber / white) | control_box | planned | Two-colour beacons usually share one earth wire, so the colours are switched on the + side like the stock lamps: RPWM amber, LPWM white |
| MOSFET | 8-ch isolated MOSFET board (low side, all 8 used) | control_box | planned | Sam's board: 8-channel opto-isolated MOSFET driver, DC 3.7-27 V, 10 A per channel, PWM input 3-20 V, 0-20 kHz. 1-4 front bars, 5 cabin bar, 6 trailer bar, 7-8 rear floods. Low side switching, so each light's + comes from its fuse and its - goes to an OUT pin |
| LB1 | Front bar 1 (far left) | front | confirmed |  |
| LB2 | Front bar 2 (inner left) | front | confirmed |  |
| LB3 | Front bar 3 (inner right) | front | confirmed |  |
| LB4 | Front bar 4 (far right) | front | confirmed |  |
| LB_INT | Interior 7 in bar | cab | confirmed |  |
| LB_TRL | Trailer light bar (Sam's spare) | trailer | planned (optional) | On the trailer, through the 8-pin plug. On/off from the dash and the phone remote; only live when the trailer plug is in |
| FLOOD_L | Rear flood left (4 in pod) | rear | confirmed | Outside of the roll cage mounting plate. Also the reverse light. Dimmable on MOSFET channel 7 (left) and 8 (right) |
| FLOOD_R | Rear flood right (4 in pod) | rear | confirmed |  |
| HEAD_L | Left headlight (stock, 12 V 35/35 W) | front | from_manual | Dual filament bulb, low and high, one shared earth (Kawasaki 2013 Teryx 750 owner's manual: headlight 12 V 35/35 W x 2) |
| HEAD_R | Right headlight (stock, 12 V 35/35 W) | front | from_manual |  |
| TAIL_L | Left tail / brake light (stock, 12 V 8/27 W) | rear | from_manual | Dual filament bulb, 8 W tail and 27 W brake, one shared earth (owner's manual: tail/brake light 12 V 8/27 W x 2) |
| TAIL_R | Right tail / brake light (stock, 12 V 8/27 W) | rear | from_manual |  |
| LIMP_SW | Backup lights toggle (hidden) | cab | planned | The Teryx has no headlight switch, so the dash and the Pico do everything. This hidden toggle is the backup if the control box dies: it feeds both low beams, both tails and the trailer tail at full through diodes. Leave it off normally. The Pico also turns low beams and tails on by itself if the dash goes quiet with the key on |
| BEACON | Roof beacon (amber + white LED, steady-on) | rear | planned | Sam's amber + white LED beacon (bought 18 Nov). Each colour stays on steady and the Pico flashes them at 3 Hz (NZ Vehicle Lighting Rule 11.1(2): 2 to 4 Hz), amber and white taking turns. White only when stopped: on the road only red or amber may show to the rear. Fits Sam's existing hole on the roof |
| BRK_WINCH | 250 A breaker | engine_bay | planned | Manual reset breaker, also the winch's kill switch: push it off to make the winch dead. No isolator contactor (Sam, 18 Nov), so the XBull remote and hand switches work whenever this is on |
| WINCH_SOL | XBull solenoid box | front | confirmed | The remote socket's in and out lines are cut from the coils inside the box and rejoined through their own diodes (WN21, WN22), like the hand switches. Then the in.winch_remote tap sees only the remote, not the Pico's own relays 4-5 driving the coils (found by the system sim, 23 Nov: tapped at the coil, the Pico would stop its own winch pull) |
| WINCH_MOTOR | XBull 5000 lb winch motor | front | confirmed |  |
| WINCH_REMOTE | XBull handheld remote | front | confirmed |  |
| HSW_WINCH | Hidden winch switch (at the winch) | front | confirmed | Momentary (ON)-OFF-(ON) |
| HSW_CAB | Hidden winch switch (in the cab) | cab | confirmed | Momentary (ON)-OFF-(ON) |
| ACT_DIFF | Front diff lock actuator (50 mm, pot) | front | confirmed |  |
| ACT_4WD | 2WD/4WD actuator | front | tbc | 50 mm actuator, or drive the stock Kawasaki electric 4WD actuator instead See [`docs/teryx-drivetrain.md`](../../docs/teryx-drivetrain.md). |
| ACT_TRAY | Tray lift actuator (400 mm) | rear | confirmed |  |
| LIM_DN | Tray down limit (NC) | rear | planned |  |
| LIM_UP | Tray up limit (NC) | rear | planned |  |
| BRAKE_SW | Brake light switch (stock) | cab | tbc | Also feeds both brake filaments and the trailer stop pin through diodes, so the brake lights work at full even with the control box off |
| PARK_SW | Parking brake switch (stock) | cab | tbc | Foot pedal park brake, cable only, no actuator. This switch only senses it: it lights the red park brake light in the meter and tells the control box (in.park), which then blocks drive through relay 6 (docs/park-brake.md) |
| EPS_ECU | Toyota Aqua EPS ECU (89650-52B51) | cab | tbc (optional) | Owned with its power plug (B+, GND). Still need the signal plug (IG, CANH, CANL). Pin numbers TBC: Toyota's RAV4 EPS ECU has IG, CANH, CANL on one plug and PIG, PGND on the other See [`docs/power-steering-aqua.md`](../../docs/power-steering-aqua.md). |
| EPS_COL | Aqua steering column (motor + torque sensor) | cab | tbc (optional) | Motor and torque sensor plugs go to the ECU on Toyota's own loom. For RC, the two torque sensor signal wires (TRQ1, TRQ2) are cut and go through the RC changeover relay; the sensor's own 5 V and ground stay as Toyota wired them |
| RC_PICO | RC box Raspberry Pi Pico 2 (spare from the 5-pack) | control_box | planned (optional) | Second Pico, only for RC. Drives the steering by faking the torque sensor. If it stops or loses power the changeover relay drops and the real torque sensor is back. Pins TBC in the RC firmware; these are a starting point See [`docs/rc-beach-launch.md`](../../docs/rc-beach-launch.md). |
| RC_CAN | MCP2515 CAN module (RC box, main bus) | control_box | planned (optional) | Same 3.3 V-converted board as the control box (TJA1050 swapped for SN65HVD230). A short stub off the main bus inside the control box, no terminator |
| RC_LVL | I2C level shifter, 4-ch BSS138 (3.3 V to 5 V) | control_box | planned (optional) | The DAC and ADC run on 5 V so they can reach the torque sensor's range (up to about 3.5 V). The Pico's I2C is 3.3 V, so it goes through this |
| RC_DAC | MCP4728 4-ch 12-bit DAC (0x60) | control_box | planned (optional) | VOUTA = fake TRQ1, VOUTB = fake TRQ2 (a mirrored pair about the centre, trq_volts() in teryx/rc_mode.py). C and D spare (throttle wiper later). VDD 5 V, so 0-5 V out |
| RC_ADC | ADS1115 ADC (third one, 0x48 on the RC box's own I2C) | control_box | planned (optional) | Reads back what actually reaches the ECU (A0 TRQ1, A1 TRQ2) and the steering angle (A2). If TRQ1/TRQ2 stop mirroring, the RC box drops the relay. VDD 5 V so it can read up to 5 V |
| RC_REL | DPDT signal relay module, 5 V coil, gold contacts | control_box | planned (optional) | Off (NC) = the real torque sensor goes to the ECU. On (NO) = the DAC does. Not the 16-ch board: its 10 A silver contacts aren't made for tiny sensor currents. The coil only gets power from the RC box, so anything that stops the RC box hands the steering back |
| RC_ANGLE | AS5600 magnetic angle sensor + magnet | cab | planned (optional) | Steering angle for the RC steering loop. The bought Aqua column has no clock spring or angle sensor, so the AS5600 sits on a small printed gear driven off the column, geared down so lock to lock is under one turn, magnet on that gear. Analogue OUT (not I2C) because it's a long run from the cab. May not be needed if the Aqua ECU sends the angle on 0x260 (bench test step 4, docs/power-steering-aqua.md) |
| TRAILER | 7-pin flat trailer socket (Narva 82043BL, reed switch) | rear | planned | See [`docs/cameras.md`](../../docs/cameras.md). |
| TCAM_PLUG | Trailer EU 7-pin round plug (camera + light bar, Sam's) | rear | planned (optional) | Sam's EU round 7-pin, next to the flat NZ/AU 7-pin for the main trailer lights, so they can't be mixed up. NOT wired to the EU light standard. 1 cam +12 V, 2 video, 3 cam ground, 4 video shield, 5 light bar +12 V, 6 light bar - (switched), 7 spare. Light bar on 1.5 mm² (pins are good for 10 A+). Spring cap on the socket and dielectric grease on the pins |
| CAM_TRAILER | Trailer camera (12 V car camera, CVBS/PAL mode) | trailer | planned (optional) |  |
| TCAM_DONGLE | Analogue video to camera-ribbon (CSI) board, ADV728x-M (front + rear + trailer, cabin later) | dash | tbc | No USB (Sam). ALL the cameras are car cameras in CVBS (PAL) mode into this one board, which sits in the Pi box on the Pi's camera ribbon port (CSI1). The Pi Camera Module 3 is dropped (26 Nov, PB Tech had none and Sam has car cameras). Inputs picked in software (adv728x-m overlay, adv7180 driver): input 0 rear, 1 trailer, 2 cabin (later), 3 front. The chip has 6-8 inputs (ADV7280-M 8, ADV7281-M/ADV7282-M 6) but cheap boards only bring some out to plugs: needs 3 now, 4 with the cabin camera. ONE decoder: only one camera is live at a time, the others show their last picture (or take turns, see docs/cameras.md). Pi 5 support for these boards is not proven yet: bench test it first |
| PI5 | Raspberry Pi 5 8GB | dash | confirmed | The 40-pin header and the PCIe port are kept for the AI HAT+ 2. CAN module wires go to header pins that come up through the HAT See [`docs/wiring.md`](../../docs/wiring.md). |
| AIHAT | AI HAT+ 2 (later) | dash | placeholder (optional) | Not buying yet. Room, cooling (about 4.5 W) and the PCIe port stay free for it See [`docs/ai-hat-ideas.md`](../../docs/ai-hat-ideas.md). |
| PI_CAN | MCP2515 CAN module (Pi) | dash | planned | Blue MCP2515 board with the SN65HVD230 swap (as the control box one), on the Pi box wall. 8 MHz crystal: pi-setup.sh default |
| SCREEN | 10.1 in touch screen | dash | confirmed | 1280x800, HDMI + USB touch, 3.5 mm audio in |
| GLOVE_USB | Glove box USB-C charger (RC phone) | dash | planned (optional) | 12 V to USB-C PD socket for the phone that lives in the glove box (docs/rc-beach-launch.md 4b). Fed from the accessory relay so it's off with the key off |
| CAM_REAR | Rear camera (200 degree, Sam's) | rear | tbc | Sam thinks it's AHD. Set to CVBS/PAL mode, soldered shielded video lead to the analogue-to-ribbon board. Rear or trailer is picked in software when the trailer plug is in. 12 V from the accessory relay (relay 7) through its own 2 A inline fuse |
| CAM_FRONT | Front camera (12 V car camera, Sam's best of the 3) | front | tbc | Replaces the Pi Camera Module 3 (26 Nov). Use the best of Sam's 3 AliExpress car cameras here: the front is the dashcam and the trail view at speed, so detail matters most. CVBS/PAL mode, not AHD. Mount behind the grille or on the bull bar, looking ahead, not mirrored. 12 V from the accessory relay (relay 7) through its own 2 A inline fuse, shielded video lead to video board input 3 |
| MODEM_4G | SIMCom A7670SA 4G board | dash | placeholder (optional) | 6-pin header S G V K T R G. V takes 5-10 V: a soldered lead from the Pi buck (5 V). NEVER raw 12 V (10 V max, and the car runs 14.4 V with spikes). K is tied to ground on the board, so it starts by itself. T/R are 115200 baud TTL to the Pi's GPIO 15/14; measure T before connecting (3.3 V ok, else BSS138). Micro USB also on board. Its GNSS (FASE version, u.FL GPS socket on Sam's board) is the dash GPS too, so there is no separate USB GPS. Check on arrival that it gets a fix with the SIM out / 4G off. No USB: it's on the header pins (soldered leads), so texts, GPS and slow data only, no live video over 4G |
| CARPLAY | Carlinkit CPC200-CCPA | dash | planned (optional) |  |
| DAC_HAT | PCM5102 I2S DAC board (on jumper leads) | dash | planned (optional) | Swapped 26 Nov from the official Raspberry Pi DAC+ HAT to a cheap PCM5102(A) I2S DAC board from AliExpress (Sam). The ID stays DAC_HAT so nothing else moves. Small board with a 3.5 mm stereo jack out, to the amp's RCA inputs with a 3.5 mm to 2x RCA lead and a ground loop isolator. Sits on standoffs in the right-hand end of the Pi box, off the Pi, so the top of the Pi stays free for the AI HAT+ 2. Joined by 5 male-to-female jumper leads (about 20 cm): GPIO 18 to BCK, 19 to LCK, 21 to DIN, 5 V to VIN, GND to GND. No I2C on this chip, so SDA/SCL stay free for the IMU. On the board: SCK tied to GND (most boards have a solder bridge for it, else a short jumper), FLT, DEMP, FMT low and XSMT high (unmuted), which is how the usual purple board comes. Overlay: scripts/audio-setup.sh --i2s hifiberry-dac. Nothing else on the Pi uses 18-21 (CAN is SPI0 + GPIO 25, 4G is UART GPIO 14/15). A dab of hot glue on the leads at both ends against vibration. Later the leads move onto the AI HAT's stacking header pins See [`docs/audio.md`](../../docs/audio.md). |
| AMP | 4-ch class D amp (AliExpress, 4 x 63 W RMS at 4 ohm) | cab | confirmed (optional) | Sam's pick. 4 x 63 W RMS at 4 ohm, or 2 x 200 W RMS bridged at 4 ohm; built-in 90 Hz high and low pass; 8-16 V; up to 33 A flat out (16.5 A on music); 145 x 100 x 45 mm. Channels 1 and 2 drive the Kenwoods (set the HPF on). Channels 3 and 4 bridged (200 W at 4 ohm) drive the Kicker KM104 sub (LPF on, gain set so it stays under the sub's 150 W RMS) See [`docs/audio.md`](../../docs/audio.md). |
| SPEAKERS | Kenwood KFC-2053MRB 8 in marine speakers (pair) | cab | confirmed (optional) | Sam has these. 8 in 2-way, 4 ohm, about 50 W RMS each (100 W the pair), 180 mm cut-out, about 86 mm mounting depth (Kenwood spec page). One amp channel each; speaker cable 1.5 mm² is plenty. In sealed printed pods on the roll cage (cad/parts/speaker_pod.scad, docs/speaker-pods.md); the cable goes in through a PG7 gland underneath each pod |
| SUB | Kicker KM104 10 in marine subwoofer | cab | confirmed (optional) | Sam has bought it (18 Nov). 10 in, 4 ohm, 150 W RMS, 30-500 Hz. On amp ch 3 + 4 bridged, low pass on (90 Hz, matches the pods' EQ handover). Sealed printed box under the seat, on hold until Sam scans the space. 1.5 mm² speaker cable |
| IMU | IMU (roll / pitch) | dash | planned (optional) |  |
