# Shopping list: everything for the build

Updated **18 November 2026** (NZ time). Prices are NZ$ incl GST. "Checked 17 Nov" means I
opened the shop's page then. "Search result" or "Estimate" means the shop's page wouldn't open
for me (PB Tech and AliExpress block my requests), so **check each price before you pay**.
USD to NZD at 1.822, AUD to NZD at 1.234 (Wise, 17-18 Nov).

**This list is made from the wiring plan.** Every part in [`config/wiring.yaml`](../config/wiring.yaml)
is on it, as something to buy, something you've got, part of the Shinegle kit, or "later".
Wire by size, CAN cable, fuses, fuse holders, lugs, plugs, diodes and resistors are counted
straight from the wires in the plan. A test fails if a part is added to the wiring and not to
this list. The source is [`config/bom.yaml`](../config/bom.yaml); run `python -m teryx bom` after
changing it. Spreadsheet copy: [`pbtech-order.csv`](pbtech-order.csv). Why each part is needed:
[`shopping-list.md`](shopping-list.md).

<!-- parts list: made by `python -m teryx bom` from config/bom.yaml + config/wiring.yaml. Don't edit by hand -->

### PB Tech (buy Thursday)

| Part | Qty | Each NZ$ | Total NZ$ | Price from | Notes |
|---|---|---|---|---|---|
| [Raspberry Pi 5 8GB](https://www.pbtech.co.nz/product/SEVRBP0502) (SEVRBP0502) | 1 | 371.39 | 371.39 | Checked 17 Nov | On order, ships about 30 Nov; ask in store |
| [Raspberry Pi Camera Module 3 Wide (front)](https://www.pbtech.co.nz/product/SEVRBP0398) (SEVRBP0398) | 1 | 80.71 | 80.71 | Search result 18 Nov | Out of stock when indexed; alt element14 SC0874 ~NZ$69 |
| [Pi 5 camera cable 200mm](https://www.pbtech.com/pacific/product/SEVRBP0541) (SEVRBP0541) | 2 | 2.12 | 4.24 | Search result 18 Nov | Front camera + video board |
| [Raspberry Pi Pico 2 5-pack](https://www.pbtech.co.nz/product/SEVRBP0628) (SEVRBP0628) | 1 | 47.20 | 47.20 | Checked 17 Nov | Control box, CAN sniffer, steering bench test, 2 spare |
| [Raspberry Pi 27W USB-C power supply (bench)](https://www.pbtech.co.nz/product/SEVRBP0512) (SEVRBP0512) | 1 | 24.90 | 24.90 | Search result 18 Nov | Bench only |
| [Raspberry Pi micro HDMI to HDMI cable 1m](https://www.pbtech.co.nz/product/SEVRBP0207) (SEVRBP0207) | 1 | 11.80 | 11.80 | Search result 18 Nov | Alt black SEVRBP0262 ~11.10 |
| [Raspberry Pi A2 SD card 128GB (OS)](https://www.pbtech.co.nz/product/SEVRBP0538) (SEVRBP0538) | 1 | 47.32 | 47.32 | Search result 18 Nov | Official card, in the Pi's own slot. Not made for non-stop writes, so dashcam/Sentry recording stays off or minimal until extra storage is added |
| [Raspberry Pi DAC+ HAT (ex IQaudio DAC+, SC0368)](https://www.pbtech.co.nz/product/SEVRBP0313) (SEVRBP0313) | 1 | 35.65 | 35.65 | Search result 18 Nov (out of stock when indexed) | Official board, RCA out. If PB Tech has none: Pakronics NZ ~NZ$40 |
| **Total** | | | **623.21** | | |

### AliExpress (one order, 2 to 4 weeks)

| Part | Qty | Each NZ$ | Total NZ$ | Price from | Notes |
|---|---|---|---|---|---|
| Carlinkit CPC200-CCPA (or CCPA-MIC) CarPlay dongle | 1 | 65.00 | 65.00 | US$33-39 x 1.822 | Title must say CCPA + Android head unit; lsusb 1314:1520/1521 |
| 4-channel class D amp, 4 x 63W RMS at 4 ohm, 2 x 200W bridged, 90Hz HPF/LPF (Sam's pick) | 1 | 100.00 | 100.00 | Sam, AliExpress ~NZ$100 | Ch 1-2 Kenwoods, ch 3-4 bridged to the Kicker KM104 sub; under the seat, not waterproof |
| 8-channel PC817 opto board 12V in | 2 | 9.00 | 18.00 | ~US$5 estimate | Board 1 = all 8 inputs; board 2 = 8 spare on MCP2 |
| 8-Channel Opto-Isolated MOSFET Driver Module, DC 3.7-27V, 10A per channel, PWM 3-20V input, 0-20kHz (Sam's pick) | 1 | 22.00 | 22.00 | ~US$12 estimate | Front bars, cabin bar, trailer bar, rear floods (all 8 used) |
| BTS7960 43A motor driver board (IBT-2), same as the 3 already owned | 6 | 10.00 | 60.00 | ~US$5-6 estimate | Used as two + side (high side) switches each: headlights L and R (low + high), tail/brake L and R, trailer tail/stop, beacon amber/white. The stock bulbs share one earth per bulb, so the MOSFET boards can't do them |
| 6-way blade fuse block with cover | 1 | 15.00 | 15.00 | Estimate | Stock lights + beacon; the 12-way is full. 2 ways spare |
| 16-channel 5V relay board, mechanical, opto + JD-VCC jumper, 10A | 1 | 21.00 | 21.00 | ~US$11.28 x 1.822 | 7 used, 9 spare after the lights moved to MOSFET/BTS7960 boards and the winch isolator was dropped; an 8-ch board would leave 1 spare. Must have the JD-VCC jumper |
| Waterproof micro limit switch, roller lever (NC) | 3 | 2.67 | 8.01 | Estimate | Tray up/down + 1 spare |
| LTC3780 auto buck-boost board, 5-32V in, 80W (set to 12.0V) | 1 | 18.00 | 18.00 | Spec from sellers (5-32V in, 1-30V out, 80W cont); price estimate | Search AliExpress: LTC3780 buck boost module. Bare board, lives in the Pi box. Screen draws well under 80W. Skip if the screen board says 9-36V in |
| 12V USB-C PD panel socket, 30W, waterproof cap | 1 | 15.00 | 15.00 | Estimate | Glove box phone (RC remote) |
| PCA9685 16-channel 12-bit PWM board (I2C) | 1 | 8.00 | 8.00 | Estimate | Trailer light bar dimming + 15 spare. Solder wires to the pads, skip the header pins |
| MPU-6050 IMU board (roll / pitch) | 1 | 5.00 | 5.00 | Estimate | I2C to the Pi |
| 12V AHD reversing camera (trailer) | 1 | 30.00 | 30.00 | Estimate |  |
| CVBS (PAL) to MIPI CSI-2 board, ADV7280-M, multi-input | 1 | 120.00 | 120.00 | Estimate. AliExpress search: ADV7282 MIPI CSI (or ADV7280 CSI Raspberry Pi). No official Pi product does this | Chip must be ADV7280-M, ADV7281-M or ADV7282-M (the -M is the ribbon output), 2+ CVBS inputs, Pi camera ribbon socket. Not TP28xx (no Pi driver) or HDMI-to-CSI. Bench test on the Pi 5 |
| SIMCom A7670SA 4G board (B28, GPS 'FASE' option) | 1 | 28.00 | 28.00 | US$15.46 x 1.822 | Must list B28; V pin from the 2nd Mini560, never raw 12V |
| 4-channel BSS138 level shifter | 1 | 2.00 | 2.00 | Estimate | Probably not needed; measure the T pin first |
| Active GPS antenna, SMA male | 1 | 8.00 | 8.00 | Estimate |  |
| LTE antenna 698-2700MHz, SMA male | 1 | 12.00 | 12.00 | Estimate | Must cover 700MHz B28 |
| u.FL to SMA female bulkhead pigtail with O-ring, 15cm | 2 | 3.00 | 6.00 | Estimate | Through the Pi box wall for both aerials |
| Finned heatsink 100x100x40mm, flat 5mm+ base | 1 | 20.00 | 20.00 | Estimate | Pi box lid |
| Thermal pad 1mm, 4 W/mK+ | 1 | 5.00 | 5.00 | Estimate |  |
| Solid aluminium block 20x20x50mm | 1 | 5.00 | 5.00 | Estimate | Cut to ~45.3mm |
| Thermal paste small tube | 1 | 3.00 | 3.00 | Estimate |  |
| M12x1.5 breather vent plug | 4 | 2.00 | 8.00 | Estimate | Pi box, both speaker pods, one spare |
| Nylon cable glands IP68: PG7 x5, PG9 x5, PG16 x5, M20 x1 | 1 | 16.00 | 16.00 | Estimate | Pi box 4, control box 5, relay box 5, speaker pods 2 (cad/measurements.scad) |
| M3 brass heat-set inserts 4.0mm OD x 5.7mm, 100 pack | 1 | 8.00 | 8.00 | Estimate | About 40 used |
| Aluminium roll-cage clamp with flat tab, 1.875 in (47.6 mm) tube, rubber liner, M6 bolt hole | 4 | 9.00 | 36.00 | Estimate | Speaker pods, 2 each. Teryx perimeter tube is 1.875 in, top crossbars 1.7 in (Axia Alloys, 2008+ Teryx): measure where the pods go and buy that size |
| M6 brass heat-set inserts 8mm OD x 12mm, 10 pack | 1 | 6.00 | 6.00 | Estimate | Speaker pod mounting pads, 2 each |
| M6 x 20 stainless bolts, spring + flat washers, 10 each | 1 | 6.00 | 6.00 | Estimate | Pod to cage clamp, with threadlocker |
| M2 + M2.5 heat-set inserts, 50 each | 1 | 8.00 | 8.00 | Estimate | Pi and 4G board standoffs |
| Stainless bolt kit: M2, M2.5, M3 (6-16mm), M4 (12-20mm), nuts, nylocs, washers | 1 | 25.00 | 25.00 | Estimate | cad/README.md hardware table: ~50 small bolts, 16 M4, 4 M5 nuts |
| Bootlace ferrule kit 0.5-6mm² with ratchet crimper | 1 | 30.00 | 30.00 | Estimate | Every wire end into a screw terminal in the boxes |
| Heatshrink ring / spade / butt terminal kit 0.5-6mm² | 1 | 25.00 | 25.00 | Estimate |  |
| Dupont jumper wires (F-F, M-F, 20cm) + 2.54mm pin headers | 1 | 10.00 | 10.00 | Estimate | Pico, Pi and board-to-board links inside the boxes; debug header |
| Waterproof 2-pin plug pair (DT style) | 14 | 2.50 | 35.00 | Estimate; counted from config/wiring.yaml | So lights, actuators, switches and cameras unplug; 1 spare |
| Waterproof 3-pin plug pair (DT style) | 3 | 3.00 | 9.00 | Estimate; counted from config/wiring.yaml | So lights, actuators, switches and cameras unplug; 1 spare |
| Waterproof 4-pin plug pair (DT style) | 2 | 3.50 | 7.00 | Estimate; counted from config/wiring.yaml | So lights, actuators, switches and cameras unplug; 1 spare |
| Waterproof 6-pin plug pair (DT style) | 2 | 5.00 | 10.00 | Estimate; counted from config/wiring.yaml | So lights, actuators, switches and cameras unplug; 1 spare |
| **Total** | | | **833.01** | | |

### Core Electronics (AU, online)

| Part | Qty | Each NZ$ | Total NZ$ | Price from | Notes |
|---|---|---|---|---|---|
| [Seeed MCP2515 + SN65HVD230 CAN board](https://core-electronics.com.au) | 4 | 22.77 | 91.08 | AU$18.45 x 1.234 | Pi, control box, steering bus, sniffer |
| [MCP23017 board](https://core-electronics.com.au/catalog/product/view/sku/WS-15391) (WS-15391) | 2 | 13.45 | 26.90 | AU$10.90 x 1.234 |  |
| [Pololu D36V50F5 5V 5.5A regulator](https://core-electronics.com.au/catalog/product/view/sku/POLOLU-4091) (POLOLU-4091) | 1 | 111.20 | 111.20 | AU$90.11 x 1.234 |  |
| Shipping to NZ (estimate) | 1 | 17.50 | 17.50 | AU$12-16 |  |
| **Total** | | | **246.68** | | |

### Gogo:Tronics and element14 (NZ, online)

| Part | Qty | Each NZ$ | Total NZ$ | Price from | Notes |
|---|---|---|---|---|---|
| [Mini560 5V 5A buck (Gogo:Tronics)](https://sparks.gogo.co.nz/catalog/DC-Power-260/Fixed-Output-Step-Down-Converter-Out-5v-up-to-5A-Continuous-In-7-20v-1009.html) | 1 | 2.95 | 2.95 | Checked 17 Nov | 4G board only; the control box uses Sam's own 5A buck |
| [1.5KE18A TVS diode (element14)](https://nz.element14.com/stmicroelectronics/1-5ke18a/diode-tvs-1-5kw-18v/dp/9884831) (9884831) | 2 | 2.24 | 4.48 | Checked 17 Nov |  |
| **Total** | | | **7.43** | | |

### Local: Jaycar, Narva stockist, Repco, auto electrical

| Part | Qty | Each NZ$ | Total NZ$ | Price from | Notes |
|---|---|---|---|---|---|
| [Narva 7-pin flat socket with reed switch](https://narva.com.au/products/narva-7-pin-flat-quickfit-trailer-socket-with-reed-switch-for-use-with-normally-closed-circuits-1-pack) (82043BL) | 1 | 35.00 | 35.00 | Estimate |  |
| F-N-R switch, DPDT centre-off, 10A+ | 1 | 20.00 | 20.00 | Estimate |  |
| E-stop mushroom button, twist release, NC, IP65 | 1 | 25.00 | 25.00 | Estimate | RC mode: cuts KSI with no software |
| Momentary (ON)-OFF-(ON) toggle, 10A, with waterproof boot | 2 | 15.00 | 30.00 | Estimate | Hidden winch switches |
| RCA to RCA stereo lead 3m | 1 | 15.00 | 15.00 | Estimate | DAC HAT to the amp under the seat |
| Prepaid SIM | 1 | 10.00 | 10.00 | Estimate |  |
| Ground bus bar, M8 studs, 6+ ways, with cover | 1 | 25.00 | 25.00 | Estimate |  |
| Wago 221 lever connectors, 5-way pack | 1 | 20.00 | 20.00 | Estimate | Dash 12V rail splits |
| Waterproof toggle switch, on-off, 15 A+ at 12 V, with rubber boot | 1 | 12.00 | 12.00 | Estimate | Hidden backup lights switch (low beams + tails at full if the control box dies). Narva or Jaycar |
| Diodes and resistors (see contents) | 1 | 30.00 | 30.00 | Estimate | Contents, counted from the wiring: 10k resistor x1, 1N4007 x1, 1N4148 x11, 1N5408 x7, 1k resistor x3, 2.2k resistor x1, 3.3 V zener x1, SB560 5 A Schottky diode x15. Buy a few spare of each |
| Heatshrink assortment (glue-lined) | 1 | 20.00 | 20.00 | Estimate |  |
| Split corrugated loom 10mm + 16mm, 10m each | 1 | 30.00 | 30.00 | Estimate |  |
| UV-black cable ties + adhesive P-clips | 1 | 20.00 | 20.00 | Estimate |  |
| Dielectric grease, small tube | 1 | 12.00 | 12.00 | Estimate | Trailer plugs and outdoor connectors |
| 2mm closed-cell foam tape, 1m+ | 1 | 10.00 | 10.00 | Estimate | Bezel to panel |
| ASA filament 1.75mm 1kg (dash panel, hood, back plate, speaker pods) | 5 | 45.00 | 225.00 | Estimate | Leave out what you already have |
| Polyester fibre fill (speaker wadding or pillow stuffing), 200 g | 1 | 12.00 | 12.00 | Estimate | About 70 g per speaker pod, loose. Not foam (it holds water) |
| PETG filament 1.75mm 1kg (boxes, liner) | 1 | 35.00 | 35.00 | Estimate |  |
| 3mm aluminium cut from DXF: back plate + Pi lid plate | 1 | 80.00 | 80.00 | Estimate | Laser or waterjet shop; cad/stl/*.dxf |
| Auto cable 0.5 mm² (metres) | 85 | 0.90 | 76.50 | Estimate; counted from config/wiring.yaml | About 68 m in the plan + 25%. Split red (+) / black (-) / a signal colour |
| Auto cable 0.75 mm² (metres) | 15 | 1.10 | 16.50 | Estimate; counted from config/wiring.yaml | About 12 m in the plan + 25%. Split red (+) / black (-) / a signal colour |
| Auto cable 1 mm² (metres) | 65 | 1.40 | 91.00 | Estimate; counted from config/wiring.yaml | About 52 m in the plan + 25%. Split red (+) / black (-) / a signal colour |
| Auto cable 1.5 mm² (metres) | 100 | 1.90 | 190.00 | Estimate; counted from config/wiring.yaml | About 80 m in the plan + 25%. Split red (+) / black (-) / a signal colour |
| Auto cable 2.5 mm² (metres) | 15 | 2.90 | 43.50 | Estimate; counted from config/wiring.yaml | About 10 m in the plan + 25%. Split red (+) / black (-) / a signal colour |
| Auto cable 4 mm² (metres) | 5 | 4.50 | 22.50 | Estimate; counted from config/wiring.yaml | About 2 m in the plan + 25%. Split red (+) / black (-) / a signal colour |
| Auto cable 6 mm² (metres) | 5 | 6.50 | 32.50 | Estimate; counted from config/wiring.yaml | About 3 m in the plan + 25%. Split red (+) / black (-) / a signal colour |
| Auto cable 10 mm² (metres) | 7 | 11.00 | 77.00 | Estimate; counted from config/wiring.yaml | About 5 m in the plan + 25%. Split red (+) / black (-) / a signal colour |
| Auto cable 35 mm² (metres) | 2 | 30.00 | 60.00 | Estimate; counted from config/wiring.yaml | About 2 m in the plan + 25%. Split red (+) / black (-) / a signal colour |
| CAN cable, 2-core twisted + screen (metres) | 10 | 2.50 | 25.00 | Estimate; counted from config/wiring.yaml |  |
| Speaker cable (metres) | 10 | 1.50 | 15.00 | Estimate; counted from config/wiring.yaml |  |
| Standard blade fuses, Narva or Jaycar (not AliExpress) | 31 | 1.50 | 46.50 | Estimate; counted from config/wiring.yaml | 1 A x3, 2 A x5, 3 A x7, 7.5 A x5, 10 A x6, 15 A x5 (2 spare of each) |
| Waterproof inline blade fuse holder | 7 | 6.00 | 42.00 | Estimate; counted from config/wiring.yaml | Feeds that don't come off the fuse block (bucks, screen, amp, 12V sense, accessories) |
| 40 A MIDI fuse + bolt-down holder | 1 | 31.00 | 31.00 | Estimate; counted from config/wiring.yaml | At the battery, one per big feed (fuse block, power steering, amp) |
| 60 A MIDI fuse + bolt-down holder | 2 | 31.00 | 62.00 | Estimate; counted from config/wiring.yaml | At the battery, one per big feed (fuse block, power steering, amp) |
| Tinned lugs for 4 mm², M8 hole | 6 | 2.00 | 12.00 | Estimate; counted from config/wiring.yaml | 2 spare |
| Tinned lugs for 6 mm², M8 hole | 6 | 2.00 | 12.00 | Estimate; counted from config/wiring.yaml | 2 spare |
| Tinned lugs for 10 mm², M8 hole | 10 | 2.00 | 20.00 | Estimate; counted from config/wiring.yaml | 2 spare |
| Tinned lugs for 35 mm², M8 hole | 4 | 2.00 | 8.00 | Estimate; counted from config/wiring.yaml | 2 spare |
| **Total** | | | **1,549.00** | | |

### Separate pickup

| Part | Qty | Each NZ$ | Total NZ$ | Price from | Notes |
|---|---|---|---|---|---|
| Toyota Aqua EPS column (ECU 89650-52B51) | 1 | 115.00 | 115.00 | About NZ$115 | Dodson's, picking up 19 Nov |
| **Total** | | | **115.00** | | |

### Totals

| Shop | NZ$ |
|---|---|
| PB Tech (buy Thursday) | 623.21 |
| AliExpress (one order, 2 to 4 weeks) | 833.01 |
| Core Electronics (AU, online) | 246.68 |
| Gogo:Tronics and element14 (NZ, online) | 7.43 |
| Local: Jaycar, Narva stockist, Repco, auto electrical | 1,549.00 |
| Separate pickup | 115.00 |
| **Everything** | **3,374.33** |

### Already got (not in the totals)

10.1 in touch screen, 12 V battery, 12 in light bar, 12-way fuse box (in the post; 12 fuses planned, so it is full), 200 degree rear camera (in the post), 250 A manual reset breaker (winch kill switch), 4 in pod, 5 A step-down buck (in the post; input must take 20 V+), 7 in light bar, ADS1115 (3 in the post), Amber + white LED roof beacon, BTS7960 (3 in the post), EU 7-pin round trailer plug (check the socket half and cap came too), Kenwood KFC-2053MRB 8 in marine speakers (pair), Kicker KM104 10 in marine sub (bought 18 Nov), XBull 5000 lb winch (and its 35 mm² cables), XBull remote, XBull solenoid box, short actuator (in the post), smart actuator with position feedback (in the post), spare light bar (trailer), tray actuator (in the post). Samsung Galaxy XCover 5 (RC remote) (NZ$187).

### Comes with the Shinegle kit or the stock Teryx

Traction battery pack, 150 A air-break switch, Main contactor, Shinegle SG1202 controller, 7.5 kW AC motor, DC-DC converter 72 V to 12 V, Shinegle kit key switch, Throttle pedal (kit accelerator), Shinegle dash / speed panel, SG1810 handheld programmer, Teryx key switch, Brake light switch (stock), Parking brake switch (stock), Left headlight (stock, 12 V 35/35 W), Right headlight (stock, 12 V 35/35 W), Left tail / brake light (stock, 12 V 8/27 W), Right tail / brake light (stock, 12 V 8/27 W).

### Later (not in the totals)

| Part | Shop | About NZ$ | Notes |
|---|---|---|---|
| Small CVBS (analogue) cabin camera (Sentry face shot) | AliExpress | 25.00 | Spare input on the video board; both camera ribbon ports are used (front Pi camera + video board) |
| Recording storage (e.g. Samsung PRO Endurance 128GB, MEMSAM11230) | PB Tech | 114.90 | For dashcam/Sentry. Sam to sort later |
| Raspberry Pi AI HAT+ 2 | PB Tech | 423.43 | Not now |
| Raspberry Pi Active Cooler | PB Tech | 11.21 | Only with the AI HAT |
| Noctua NF-A4x10 5V fan | Newegg NZ | 21.85 | Only if the Pi box runs hot |
| Brake pedal Hall sensor (+ pressure sensor) | AliExpress | 30.00 | Brake regen; the second ADS1115 is already owned |
| GameSir G8 Galileo phone gamepad | AliExpress | 78.00 | RC mode, Sam: not now |
| EasyCAP DC60 USB capture | PB Tech | 28.75 | Only if the rear camera turns out to be RCA |
| Carlinkit CCPA from Audio City (NZ stock) | Audio City | 180.00 | Backup if the AliExpress one is slow |

Wiring parts waiting on that: AIHAT: AI HAT+ 2, ~NZ$423 (Sam: not now). Box, power and cooling stay sized for it; BRAKE_PEDAL: Brake regen only, after the Shinegle regen check passes; BRAKE_PRESS: Brake regen cross-check only.

Tools aren't listed (crimpers, soldering iron, heat gun, multimeter, 3D printer).

<!-- end parts list -->

**The 8-channel solid state relay board you've got coming won't work here.** Those boards use Omron G3MB-202P relays, which are for AC only. On 12 V DC they switch on but never switch off again until the power is cut ([Omron FAQ](https://www.ia.omron.com/support/faq/answer/18/faq02101/index.html)). Keep it for a mains project, or send it back if you can.

## Better bought in NZ or from a proper shop, not AliExpress

| Part | Why |
|---|---|
| Raspberry Pi 5, Active Cooler, Camera Module 3, Pico 2 | Fakes and grey stock are common on AliExpress, and PB Tech gives you a local warranty. Prices are about the same once shipping is on |
| SD card | Fake cards that lie about their size are very common on AliExpress. They lose files and corrupt the OS |
| The fuses themselves | The fuse block from AliExpress is fine (it's plastic and brass), but buy the **blade fuses** in NZ (Narva or Jaycar packs, 3/5/7.5/10/15 A). Cheap fuses often don't blow at their rated current, and they're the safety part |
| Pololu 5V regulator | It powers the Pi and has to survive winch spikes. Pololu copies exist; buy it genuine from Core Electronics |
| Seeed CAN boards | They're 3.3V all through, which is what the firmware and `wiring.md` expect. The cheap blue AliExpress MCP2515 boards are 5V and need extra wiring. Already in the Core parcel, so no extra shipping |
| TVS diodes | Fake parts are common in cheap diodes, and element14 has them for NZ$2.24 |
| Mini560 bucks | Already cheap in NZ (Gogo:Tronics NZ$2.95). Not worth the wait |
| 4G dongle (later) | The Huawei E3372h-607 is fine from AliExpress or Trade Me if the label checks out. If you go Waveshare SIM7600G-H, buy it from [Waveshare](https://www.waveshare.com/sim7600g-h-4g-dongle.htm) directly: third-party listings call it "unbranded" |

## Wiring the 4G board

Sam's board (from its datasheet): a 6-pin header marked **S** (sleep), **G** (ground), **V** (power,
**5-10 V**), **K** (power key), **T** (TX out), **R** (RX in), **G** (ground). It has its own regulator, a
470 µF tantalum capacitor for the transmit peaks, a GPS antenna plug, a micro USB and runs at 115200 baud.

- **Power:** feed **V** from the spare **Mini560 5 V buck**, with both grounds joined. No separate 3.8 V
  buck or big capacitor needed: the board does that itself. **Never put raw 12 V on V**, as 10 V is its
  limit and a car's 12 V runs at 14.4 V when charging, with spikes on top.
- **Power key (K):** tied to ground on the board by default (R104), so the module starts by itself when
  power comes on. Leave it unconnected.
- **Sleep (S):** leave it unconnected for now. It can go to a spare GPIO later to save battery when parked.
- **To the Pi:** T goes to the Pi's RX (GPIO 15), R goes to the Pi's TX (GPIO 14), G to ground. **Measure
  T first** (see the level shifter row): about 3.3 V is fine straight in. The code supports this (PR #42).
  The Pi sends AT commands for SMS and can run PPP over it for light data.
- **Or always on, off a spare Pico:** the Pi is off when the key is off, so for "text the Teryx to
  lock it" while parked, the module has to stay powered from the 12V battery and something small
  has to listen. The control box Pico has no spare pins, but the Pico 5-pack has spares. A spare
  Pico 2 could run just the modem and talk to the control box over the existing CAN bus, which
  needs a **5th CAN board** (~NZ$23, Core Electronics). That's a design choice for the 4G
  anti-theft work, so it's not in the totals. Standby draw has to be checked against the 12V
  battery.

## Cooling: sealed and fanless (18 Nov)

Sam wants the Pi box to survive hosing the Teryx down, and no fan noise. So the box is now sealed:
no vents, no lid fan. The lid is a 3 mm aluminium plate (cut with the back plate) with a finned
heatsink on the outside, and a 20 x 20 mm aluminium pillar carries the Pi chip's heat straight up
to it through a thermal pad. Full write-up, sums and assembly: [`pi-box-cooling.md`](pi-box-cooling.md).

- **Active Cooler: not now.** The pillar does its job. It comes back with the AI HAT, under the HAT,
  as Raspberry Pi say. Keep your passive heatsink for the bench.
- **30 mm lid fan: gone** from the AliExpress cart. The heatsink parts are in its place.
- **Heat:** about 9 W in normal driving puts the heatsink near 56°C and the Pi chip near 62°C on a
  40°C day, well under the 80°C point where the Pi slows down. Everything flat out at once on a hot
  day just touches it. A quiet optional fan on the outside of the fins (Noctua NF-A4x10 5V PWM,
  "Later") is the fix if the logs say so, and it'll be needed with the AI HAT.

## Getting the right CarPlay dongle

The dash only talks to the **CCPA / Autokit** type, the one made for aftermarket Android
screens. Most "wireless CarPlay adapters" in NZ shops are the wrong kind.

- **Wrong kind, won't work:** anything "wired to wireless" or "for factory wired CarPlay". That
  includes the [MINIX CA525](https://www.pbtech.co.nz/product/CARMNX0525/MINIX-CA525-Mini-Wireless-CarPlay--Android-Auto-Ad)
  and CP86 at PB Tech, Carlinkit 3.0 / 4.0 / 5.0 / 2Air / U2W / CP2A, and Ottocast. They need a
  car that already has CarPlay ([Best Buy, CA525](https://www.bestbuy.com/product/minix-ca525-wireless-carplay-android-auto-adapter-for-factory-wired-carplay-android-auto-with-wi-fi-6-black/CGCLX97947)).
- **Right kind:** the listing says **CPC200-CCPA** or **Autokit**, "for Android head unit /
  Android car radio", and mentions installing the Autokit app. There's also a **CCPA-MIC**
  version with a mic built in, which may save buying a USB mic for Siri and calls (not tested).
- **Fakes and clones:** I couldn't find a Carlinkit list of official shops, and several sites use
  the Carlinkit name. A seller on Trustpilot speaking for Carlinkit said one bad unit came from a
  third-party seller, not their store ([Trustpilot](https://www.trustpilot.com/review/carlinkitcarplay.com)).
  Be wary of listings that say "Carlink" instead of "Carlinkit", or prices well under about
  US$40. MacRumors users say firmware updates are only given out after proof of purchase
  ([MacRumors](https://forums.macrumors.com/threads/carplay-adapter-to-convert-to-wireless-carplay.2193978/page-260)).
- **Check it when it arrives:** plug it into the Pi or a Linux laptop and run `lsusb`. It must
  show **`1314:1520`** or **`1314:1521`**, the two IDs the dash code looks for
  (`dash/web/lib/node-carplay.js`). Anything else, send it back.
- **Don't update its firmware.** Firmware 2025.10.15.1127 broke setup for LIVI, our fallback,
  which worked again after going back to 2025.02.25.1521
  ([LIVI issue #347](https://github.com/f-io/LIVI/issues/347)).

## Later (don't buy now)

| Part | Why | Price | Notes |
|---|---|---|---|
| GameSir G8 Galileo phone gamepad grip, USB-C (GameSir official store on AliExpress) | RC mode | US$40-45 on deals (~NZ$73-82), list [US$79.99](https://gamesir.com/collections/all-products/products/gamesir-g8-galileo) | **Not now (Sam, 18 Nov).** RC mode uses on-screen sticks until then; gamepad support stays in the code. Half the price of the Razer Kishi V3 (NZ$167.58 at PB Tech) |
| Samsung Galaxy XCover 5, second-hand, lives in the ATV as the RC remote (Android 14, 4 GB RAM / 64 GB, IP68, 5.3" screen works with gloves, swappable battery, 5 GHz wifi) | RC mode | NZ$187 on Trade Me, 90 day warranty | **Bought (Sam, 18 Nov).** Fully Kiosk Browser licence optional (price not checked). See docs/rc-beach-launch.md section 4b |
| [Raspberry Pi Active Cooler](https://www.pbtech.co.nz/product/SEVRBP0531) | Goes under the AI HAT+ 2 | NZ$11.21 at PB Tech (checked 17 Nov) | Only with the HAT. Not needed for the sealed box now |
| Noctua NF-A4x10 5V PWM 40 mm fan (optional) | Blows on the Pi box heatsink fins if it runs hot, and with the AI HAT | about NZ$22 at [Newegg NZ](https://www.newegg.com/global/nz-en/noctua-nf-a4x10-5v-pwm/p/1YF-000T-000N2) (search result) | Outside the sealed box, so the seal doesn't care. Runs off the Pi 5 fan connector (needs an adaptor), off below 50°C |
| [Raspberry Pi AI HAT+ 2](https://www.pbtech.co.nz/product/SEVRBP0446/Raspberry-Pi-5-Official-AI-Hat-2) | Camera AI, local voice assistant | ~NZ$423 PB Tech (search result), or [Core Electronics](https://core-electronics.com.au/raspberry-pi-ai-hat-plus-2.html) AU$289 (~NZ$357-373 landed) | **Not buying now.** The Pi box stays 56 mm tall for it, the Pi's PCIe slot stays free, its header stays clear (the CAN board sits on the box wall), and the Pololu regulator has the spare power |
| Huawei E3372h-607 4G USB stick (plug-in alternative to the A7670SA board in the AliExpress cart) | Anti-theft tracking, SMS and remote access | ~US$36-42 (~NZ$66-77) on eBay/AliExpress (search results), or second-hand on Trade Me | Bands 1/3/7/8/28/40, which covers Spark, One NZ and 2degrees including the 700 MHz B28 country band ([listing](https://ubbthreads.com/store/item/Huawei-E3372h-607-4G-LTE-FDD-TDD-B40-4GX-USB-Dongle-Mobile-Broadband-150Mbps-NEW_314457944618.html)). Shows up on the Pi as a plain network adaptor, no driver needed, and SMS works through its built-in web API. **Check the label under the cap says E3372h-607** (other versions like -153 or -320 miss B28), and that it's unlocked if second-hand. No GPS built in, but the Pi already has the GPS puck. Light data and SMS is all we need |
| Waveshare SIM7600G-H 4G Dongle (dearer alternative) | Same, plus its own GPS | US$101.99 at [waveshare.com](https://www.waveshare.com/sim7600g-h-4g-dongle.htm), or about NZ$139-179 plus shipping on Fruugo NZ | The 4G anti-theft work's first pick. Worth it only if we want a GPS fix that keeps working when the Pi's own GPS puck is unplugged or cut. Goes inside the Pi box |
| Prepaid SIM (optional) | For the 4G dongle | | Needs topping up once a year |
| AirTag (optional) | Backup tracker | about NZ$47-68 | Hidden somewhere separate from the Pi box |
| **Kingston XS1000 1TB USB-C SSD** (optional) | Video drive for the dashcam and Sentry | NZ$189-253 at PB Tech (HDDKCP225100, the price moved between checks) | USB, not NVMe, so the PCIe slot stays free for the AI HAT. Sits in a cradle in the Pi box lid, no case needed |
| Short right-angle USB-C to USB-A lead (optional) | For the SSD | Not priced | |
| **Camera Module 3 NoIR Wide** (optional) | Cabin camera for the face shot | about NZ$70 at PB Tech (SEVRBP0399) | Plus a second 200 mm cable (SEVRBP0541, ~NZ$2) |
| Powered USB hub | Pi 5 only has 4 USB ports | Not priced | Touch, cameras, CarPlay dongle, audio, GPS, and later the 4G modem and SSD won't all fit. The Pi 5's USB ports share 1.6 A, so the modem and SSD may need the hub's power |
| [EasyCAP DC60 USB capture](https://www.pbtech.co.nz/product/SEVOEM9701) (PB Tech SEVOEM9701) | Only if the rear camera is RCA | NZ$28.75 (search result) | Composite only, not AHD. See [`cameras.md`](cameras.md) |

## Cheaper places, part by part

| Part | PB Tech | Best other I found | Better? |
|---|---|---|---|
| Pi 5 8GB | NZ$371.39 | [Core Electronics](https://core-electronics.com.au/raspberry-pi-5-model-b-8gb.html) AU$283.85 (~NZ$350-366 landed) + shipping | **No.** About the same once shipping is on. Buy at PB Tech for the local warranty |
| Camera Module 3 Wide | ~NZ$80.71, out of stock | element14 NZ ~NZ$69, out of stock | Whoever has stock first |
| CarPlay dongle | Not stocked (CA525 is the wrong type) | AliExpress ~NZ$60-71, Carlinkit's own store ~NZ$118, Audio City NZ$180 | **AliExpress** (Sam's pick). Audio City if you want it now |
| Phone gamepad grip (later) | Razer Kishi V3 NZ$167.58 | GameSir G8 Galileo ~NZ$73-82 on AliExpress | **Yes**, about half, when you get one |
| AI HAT+ 2 (later) | ~NZ$423 | Core Electronics ~NZ$357-373 landed | **Yes**, when the time comes |
| Everything small | | | Not worth splitting: savings would be smaller than a shipping fee |

**Note on "landed" prices from Australia:** Core's prices include Australian GST (10%). For
orders to NZ under NZ$1,000 the overseas shop normally charges NZ GST (15%) instead. I couldn't
confirm which they do, so check the total at checkout.

Not checked, or nothing found: nicegear, MicroCentre, The Warehouse, Pakronics NZ, PriceSpy NZ.
