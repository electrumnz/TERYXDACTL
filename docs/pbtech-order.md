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
| [Raspberry Pi Pico 2 5-pack](https://www.pbtech.co.nz/product/SEVRBP0628) (SEVRBP0628) | 1 | 47.20 | 47.20 | Checked 17 Nov | Control box, RC box, CAN sniffer, steering bench test, 1 spare |
| [Raspberry Pi 27W USB-C power supply (bench)](https://www.pbtech.co.nz/product/SEVRBP0512) (SEVRBP0512) | 1 | 24.90 | 24.90 | Search result 18 Nov | Bench only |
| [Raspberry Pi micro HDMI to HDMI cable 1m](https://www.pbtech.co.nz/product/SEVRBP0207) (SEVRBP0207) | 1 | 11.80 | 11.80 | Search result 18 Nov | Alt black SEVRBP0262 ~11.10 |
| [Raspberry Pi A2 SD card 128GB (OS)](https://www.pbtech.co.nz/product/SEVRBP0538) (SEVRBP0538) | 1 | 47.32 | 47.32 | Search result 18 Nov | Official card, in the Pi's own slot. Not made for non-stop writes, so dashcam/Sentry recording stays off or minimal until extra storage is added |
| [Raspberry Pi DAC+ HAT (ex IQaudio DAC+, SC0368)](https://www.pbtech.co.nz/product/SEVRBP0313) (SEVRBP0313) | 1 | 35.65 | 35.65 | Search result 18 Nov (out of stock when indexed) | Official board, RCA out. If PB Tech has none: Pakronics NZ ~NZ$40 |
| **Total** | | | **623.21** | | |

### AliExpress (one order, 2 to 4 weeks)

| Part | Qty | Each NZ$ | Total NZ$ | Price from | Notes |
|---|---|---|---|---|---|
| CVBS (PAL) to MIPI CSI-2 board, ADV7280-M, multi-input | 1 | 120.00 | 120.00 | Estimate. AliExpress search: ADV7282 MIPI CSI (or ADV7280 CSI Raspberry Pi). No official Pi product does this | Sam unsure if ordered: check your AliExpress orders first. Search: ADV7282 MIPI CSI Raspberry Pi (or ADV7280 CVBS to CSI2). Chip must be ADV7280-M, ADV7281-M or ADV7282-M (the -M is the ribbon output), 2+ CVBS inputs, Pi camera ribbon socket. Not TP28xx (no Pi driver) or HDMI-to-CSI. Bench test on the Pi 5 |
| **Total** | | | **120.00** | | |

### AliExpress top-up (second order, not placed yet)

| Part | Qty | Each NZ$ | Total NZ$ | Price from | Notes |
|---|---|---|---|---|---|
| Waterproof DC-DC step-down converter, 12V/24V in, 5V 10A 50W out (finned aluminium case, wire leads) | 1 | 22.00 | 22.00 | Estimate, AliExpress | Search: DC DC converter 12V 24V to 5V 10A waterproof. The finned aluminium ones with wire leads are the right kind (potted means filled with resin inside that case). Listing must say input 8-40V or wider, 10A, and no USB plug. 5V or 5.2V out are both fine for the Pi 5. Powers the Pi + 4G board |
| AS5600 magnetic angle sensor board, with its round magnet | 1 | 6.00 | 6.00 | Estimate, AliExpress | Search: AS5600 magnetic encoder module. It's a small square board (about 23 x 23 mm) that reads the angle of a little round magnet spinning over its chip. The round thing in the photos is that magnet (6 mm across, 2.5 mm thick, magnetised across its face, called diametric), sometimes in a plastic holder. Get the plain board with the magnet. Skip the kits with a second board or bracket, you don't need them. If no magnet is included, add a 6x2.5mm diametric magnet. Only needed if the Aqua ECU doesn't send the angle |
| 4-channel I2C logic level converter board, bi-directional, 3.3V to 5V, 5 pack | 1 | 4.00 | 4.00 | Estimate, AliExpress | Search: 4 channel IIC I2C logic level converter bi-directional module 3.3V 5V. Small board with pins marked HV, LV, GND, HV1-4 and LV1-4. The chips on it are BSS138s, that's just the part inside, so don't search for the bare BSS138 |
| Closed-cell EVA foam tape, single-sided sticky, 2mm thick x 10mm wide, black, 3-5m roll | 1 | 5.00 | 5.00 | Estimate, AliExpress | Seals the screen bezel to the dash panel (needs about 1 m round the cut-out). The bezel lip is about 28 mm, so 10 mm wide sits in the recess with room to spare |
| Split corrugated conduit (black ribbed tube with a slit), about 10mm and 16mm inside size, 10m each | 1 | 18.00 | 18.00 | Estimate, AliExpress | Yes, split conduit, not spiral wrap. It takes rubbing, mud and sun better and wires can be added later through the slit. Listings often give the outside size (AD13, AD21.2 etc), so pick by the inside size in the size chart. Nylon (PA) if you can, it handles heat better than PP near the motor |
| Heatshrink, 3:1 glue-lined (adhesive), black kit: 1.6, 2.4, 3.2, 4.8, 6.4, 9.5, 12.7 and 19.1mm, plus a small red pack | 1 | 15.00 | 15.00 | Estimate, AliExpress | 3.2mm for 0.5-1mm² joins, 4.8mm for 1.5-2.5mm², 6.4-9.5mm for 4-10mm², 19.1mm for the 35mm² lugs (that cable is about 12mm thick). Red for the + ends of the big cables |
| SB560 Schottky diode, 5A 60V (DO-201AD, through hole), 20 pack | 1 | 4.00 | 4.00 | Estimate, AliExpress | Need SB560 5 A Schottky diode x18 (counted from the wiring), rest spare |
| 1N5408 rectifier diode, 3A 1000V, 20 pack | 1 | 3.00 | 3.00 | Estimate, AliExpress | Need 1N5408 x10 (counted from the wiring), rest spare |
| 1N4148 small signal diode, 50 pack | 1 | 2.00 | 2.00 | Estimate, AliExpress | Need 1N4148 x12 (counted from the wiring), rest spare |
| 10SQ045 Schottky diode, 10A 45V (R-6, through hole), 5 pack | 1 | 4.00 | 4.00 | Estimate, AliExpress | Need 10SQ045 10 A Schottky diode x1 (counted from the wiring), rest spare |
| 1N4007 rectifier diode, 1A 1000V, 20 pack | 1 | 2.00 | 2.00 | Estimate, AliExpress | Need 1N4007 x1 (counted from the wiring), rest spare |
| 1N4728A zener diode, 3.3V 1W, 20 pack | 1 | 2.00 | 2.00 | Estimate, AliExpress | Need 3.3 V zener x1 (counted from the wiring), rest spare |
| Resistor kit, 1/4W metal film 1%, about 30 values x 20 (600 pcs) | 1 | 6.00 | 6.00 | Estimate, AliExpress | Need 10k resistor x1, 1k resistor x3, 2.2k resistor x1 (counted from the wiring), rest spare |
| Ground bus bar, 150A or more, M8 studs plus small screw terminals, with cover | 1 | 15.00 | 15.00 | Estimate, AliExpress | About 25 earths land here, the biggest is the 10mm² battery negative, and the total is well under 100 A. A bar with 2-4 M8 studs plus 8-12 small screw terminals saves stacking lots of rings on a stud. The winch earth goes straight to the battery, not here |
| RCA stereo lead 3m (one cable, 2 plugs each end) | 1 | 8.00 | 8.00 | Estimate, AliExpress | One lead is all you need: it's the left + right pair in one cable, DAC HAT to the amp. If the amp has a 2CH/4CH input switch set it to 2CH so the sub channels get signal too, if not add a pair of RCA Y splitters (1 male to 2 female) |
| Heavy duty momentary toggle switch, (ON)-OFF-(ON), SPDT 3 terminals, 20A 12V DC, 12mm hole, with waterproof rubber boot | 2 | 8.00 | 16.00 | Estimate, AliExpress | Search: 12V 20A momentary toggle switch ON-OFF-ON 3 pin, and pick one where both sides spring back to the middle (shown as (ON)-OFF-(ON) or momentary on both sides). Hidden winch in/out switches, one at the winch and one in the cab. They work the solenoid coil (5 A fuse), so 20A is plenty. Get boots that match the thread (usually 12mm) |
| Tinned copper cable lug 4 mm², M8 hole (listed as SC4-8) | 6 | 1.00 | 6.00 | Estimate; counted from config/wiring.yaml | 2 spare. Crimp with a hex lug crimper (the ferrule crimper won't do these) |
| Tinned copper cable lug 6 mm², M8 hole (listed as SC6-8) | 6 | 1.00 | 6.00 | Estimate; counted from config/wiring.yaml | 2 spare. Crimp with a hex lug crimper (the ferrule crimper won't do these) |
| Tinned copper cable lug 10 mm², M8 hole (listed as SC10-8) | 10 | 1.00 | 10.00 | Estimate; counted from config/wiring.yaml | 2 spare. Crimp with a hex lug crimper (the ferrule crimper won't do these) |
| Tinned copper cable lug 35 mm², M8 hole (listed as SC35-8) | 4 | 1.00 | 4.00 | Estimate; counted from config/wiring.yaml | 2 spare. Crimp with a hex lug crimper (the ferrule crimper won't do these) |
| **Total** | | | **158.00** | | |

### Local: Jaycar, Narva stockist, Repco, auto electrical

| Part | Qty | Each NZ$ | Total NZ$ | Price from | Notes |
|---|---|---|---|---|---|
| [Narva 7-pin flat socket with reed switch](https://narva.com.au/products/narva-7-pin-flat-quickfit-trailer-socket-with-reed-switch-for-use-with-normally-closed-circuits-1-pack) (82043BL) | 1 | 35.00 | 35.00 | Estimate | NZ/AU flat 7-pin trailer socket with the reed switch that tells the dash a trailer is plugged in. Narva stockist (Repco, auto electrical) |
| F-N-R switch: DPDT centre-off toggle, ON-OFF-ON, 6 terminals, 15A, with rubber boot | 1 | 20.00 | 20.00 | Estimate | Forward / neutral / reverse, straight to the Shinegle controller. Not momentary: it must stay where you put it. Jaycar or Narva stockist. It only carries a small signal, but check the controller's F/R wire voltage first (it might be 72 V, see the wiring notes) |
| E-stop button: 22mm panel mount, 40mm red mushroom, twist to release, 1 NC contact (e.g. Schneider XB5AS8442 or XB4BS8442) | 1 | 25.00 | 25.00 | Estimate | RC mode only: cuts the Shinegle key line (KSI) with no software. NC means the contact opens when you hit it. Electrical wholesaler (Corys, JA Russell) or Jaycar. Needs a 22mm hole |
| Prepaid SIM with 4G on 700MHz (band 28): Spark, One NZ or 2degrees | 1 | 10.00 | 10.00 | Estimate | For the A7670SA 4G board: SMS commands and light data. Any of the three works; cheapest yearly top-up wins |
| Wago 221-415 lever connectors (5-way, up to 4mm², 32A), pack of 10+ | 1 | 20.00 | 20.00 | Estimate | Dash 12V rail splits. Genuine Wago from an electrical wholesaler, Bunnings or Mitre 10; lots of fakes online |
| Backup lights switch: SPST ON-OFF toggle, 20A at 12V DC, 12mm hole, with waterproof rubber boot | 1 | 12.00 | 12.00 | Estimate | Hidden. Carries both low beams, tails and trailer tails at full (about 8 A) if the control box dies. Not momentary. Narva stockist or Jaycar |
| Dielectric grease, small tube (CRC or Permatex) | 1 | 12.00 | 12.00 | Estimate | Repco or Supercheap. A smear in the trailer plugs and outdoor plugs before joining |
| ASA filament 1.75mm 1kg (dash panel, hood, back plate, speaker pods and their T. rex heads) | 7 | 45.00 | 315.00 | Estimate | Bambu ASA or similar, stone grey or olive. The two heads and jaws take about 1.6 kg at 10-15% infill. Leave out what you already have |
| ASA filament 1.75mm, small spools: bone/off-white, amber/orange, black (T. rex teeth, eyes, pupils) | 3 | 45.00 | 135.00 | Estimate | Only about 60 g of each is used. Leave out what you already have |
| Polyester fibre fill (speaker wadding or pillow stuffing), 200 g | 1 | 12.00 | 12.00 | Estimate | Kmart or Spotlight pillow stuffing is fine. About 70 g per speaker pod, loose. Not foam (it holds water) |
| PETG filament 1.75mm 1kg (boxes, liner) | 1 | 35.00 | 35.00 | Estimate | Bambu PETG or similar, any colour (inside the boxes) |
| 3mm aluminium cut from DXF: back plate + Pi lid plate | 1 | 80.00 | 80.00 | Estimate | Laser or waterjet shop; send them the DXF files in cad/stl/*.dxf. 3mm 5052 or 5083 aluminium |
| Auto cable 0.5 mm², pure copper (metres) | 110 | 0.90 | 99.00 | Estimate; counted from config/wiring.yaml | About 86 m in the plan + 25%. Split red (+) / black (-) / a signal colour. Buy by mm² (cross-section) on the label, not the outside 'mm' size, and not CCA (copper-clad aluminium) |
| Auto cable 0.75 mm², pure copper (metres) | 15 | 1.10 | 16.50 | Estimate; counted from config/wiring.yaml | About 12 m in the plan + 25%. Split red (+) / black (-) / a signal colour. Buy by mm² (cross-section) on the label, not the outside 'mm' size, and not CCA (copper-clad aluminium) |
| Auto cable 1 mm², pure copper (metres) | 65 | 1.40 | 91.00 | Estimate; counted from config/wiring.yaml | About 52 m in the plan + 25%. Split red (+) / black (-) / a signal colour. Buy by mm² (cross-section) on the label, not the outside 'mm' size, and not CCA (copper-clad aluminium) |
| Auto cable 1.5 mm², pure copper (metres) | 105 | 1.90 | 199.50 | Estimate; counted from config/wiring.yaml | About 82 m in the plan + 25%. Split red (+) / black (-) / a signal colour. Buy by mm² (cross-section) on the label, not the outside 'mm' size, and not CCA (copper-clad aluminium) |
| Auto cable 2.5 mm², pure copper (metres) | 15 | 2.90 | 43.50 | Estimate; counted from config/wiring.yaml | About 10 m in the plan + 25%. Split red (+) / black (-) / a signal colour. Buy by mm² (cross-section) on the label, not the outside 'mm' size, and not CCA (copper-clad aluminium) |
| Auto cable 4 mm², pure copper (metres) | 5 | 4.50 | 22.50 | Estimate; counted from config/wiring.yaml | About 2 m in the plan + 25%. Split red (+) / black (-) / a signal colour. Buy by mm² (cross-section) on the label, not the outside 'mm' size, and not CCA (copper-clad aluminium) |
| Auto cable 6 mm², pure copper (metres) | 5 | 6.50 | 32.50 | Estimate; counted from config/wiring.yaml | About 3 m in the plan + 25%. Split red (+) / black (-) / a signal colour. Buy by mm² (cross-section) on the label, not the outside 'mm' size, and not CCA (copper-clad aluminium) |
| Auto cable 10 mm², pure copper (metres) | 7 | 11.00 | 77.00 | Estimate; counted from config/wiring.yaml | About 5 m in the plan + 25%. Split red (+) / black (-) / a signal colour. Buy by mm² (cross-section) on the label, not the outside 'mm' size, and not CCA (copper-clad aluminium) |
| Auto cable 35 mm², pure copper (metres) | 2 | 30.00 | 60.00 | Estimate; counted from config/wiring.yaml | About 2 m in the plan + 25%. Split red (+) / black (-) / a signal colour. Buy by mm² (cross-section) on the label, not the outside 'mm' size, and not CCA (copper-clad aluminium) |
| CAN cable: 2-core twisted pair, 0.5mm², screened (metres) | 15 | 2.50 | 37.50 | Estimate; counted from config/wiring.yaml |  |
| Speaker cable 1.5mm² (16 AWG), pure copper (metres) | 10 | 1.50 | 15.00 | Estimate; counted from config/wiring.yaml |  |
| Standard blade fuses, Narva or Jaycar (not AliExpress) | 34 | 1.50 | 51.00 | Estimate; counted from config/wiring.yaml | 1 A x3, 2 A x6, 3 A x5, 5 A x4, 7.5 A x5, 10 A x5, 15 A x6 (2 spare of each) |
| Waterproof inline fuse holder, standard blade (ATO), 30A, with 4mm² leads | 8 | 6.00 | 48.00 | Estimate; counted from config/wiring.yaml | Feeds that don't come off the fuse block (bucks, screen, amp, 12V sense, accessories) |
| 40 A MIDI fuse + bolt-down holder | 1 | 31.00 | 31.00 | Estimate; counted from config/wiring.yaml | At the battery, one per big feed (fuse block, power steering, amp) |
| 60 A MIDI fuse + bolt-down holder | 2 | 31.00 | 62.00 | Estimate; counted from config/wiring.yaml | At the battery, one per big feed (fuse block, power steering, amp) |
| **Total** | | | **1,597.00** | | |

### Separate pickup

| Part | Qty | Each NZ$ | Total NZ$ | Price from | Notes |
|---|---|---|---|---|---|
| Toyota Aqua EPS ECU signal plug (ignition + CAN H/L), cut from an Aqua / Prius C loom with 300 mm of wire | 1 | 20.00 | 20.00 | Estimate | Sam has the column and its power plug (19 Nov). This is the other plug on the ECU. Ask Dodson's, or any wrecker with an NHP10 Aqua or Prius C. docs/power-steering-aqua.md |
| **Total** | | | **20.00** | | |

### Totals

| Shop | NZ$ |
|---|---|
| PB Tech (buy Thursday) | 623.21 |
| AliExpress (one order, 2 to 4 weeks) | 120.00 |
| AliExpress top-up (second order, not placed yet) | 158.00 |
| Local: Jaycar, Narva stockist, Repco, auto electrical | 1,597.00 |
| Separate pickup | 20.00 |
| **Everything** | **2,518.21** |

### Already got (not in the totals)

1.5KE18A TVS diodes (AliExpress top-up, bought 23 Nov), 10.1 in touch screen, 12 V battery, 12 in light bar, 12-way fuse box (in the post; 12 fuses planned, so it is full), 12V AHD trailer camera (AliExpress main order, bought 22 Nov), 12V USB-C panel socket (AliExpress main order, bought 22 Nov), 16-channel relay board (AliExpress main order, bought 22 Nov), 200 degree rear camera (in the post), 250 A manual reset breaker (winch kill switch), 4 in pod, 4-channel class D amp (AliExpress main order, bought 22 Nov), 5 A step-down buck (in the post; input must take 20 V+), 6-way blade fuse block (AliExpress main order, bought 22 Nov), 7 in light bar, 8-channel MOSFET driver board (AliExpress main order, bought 22 Nov), 8-channel PC817 opto boards (2) (AliExpress main order, bought 22 Nov), ADS1115 (3 in the post), ADS1115 (third of the 3 in the post, for the RC box), Amber + white LED roof beacon, BTS7960 (3 in the post), BTS7960 boards (6 more) (AliExpress main order, bought 22 Nov), Carlinkit CCPA CarPlay dongle (AliExpress main order, bought 22 Nov), DPDT signal relay modules (2) (AliExpress top-up, bought 23 Nov), Dupont jumpers + pin headers (AliExpress main order, bought 22 Nov), EU 7-pin round trailer plug (check the socket half and cap came too), Kenwood KFC-2053MRB 8 in marine speakers (pair), Kicker KM104 10 in marine sub (bought 18 Nov), LTC3780 buck-boost board (AliExpress main order, bought 22 Nov), MCP23017 I/O boards (2) (AliExpress top-up, bought 23 Nov), MCP2515 CAN boards (5, swap the TJA1050 for SN65HVD230) (AliExpress top-up, bought 23 Nov), MCP4728 DAC board (AliExpress top-up, bought 23 Nov), MPU-6050 IMU board (AliExpress main order, bought 22 Nov), PCA9685 PWM boards (2) (AliExpress main order, bought 22 Nov), SIMCom A7670SA 4G board (AliExpress main order, bought 22 Nov), Toyota Aqua EPS ECU 89650-52B51 on the column, with its power plug (Dodson's, 19 Nov), Toyota Aqua EPS column (Dodson's, 19 Nov), Waterproof roller limit switches (3) (AliExpress main order, bought 22 Nov), XBull 5000 lb winch (and its 35 mm² cables), XBull remote, XBull solenoid box, short actuator (in the post), smart actuator with position feedback (in the post), spare light bar (trailer), tray actuator (in the post). Cable glands and M12 breather vents, 10 packs (boxes + speaker pods) (NZ$24), Heat-set insert kit (M2 to M6) and stainless bolt kit (M2 to M6) (NZ$45), Samsung Galaxy XCover 5 (RC remote) (NZ$187), 4-channel BSS138 level shifter (NZ$2), Active GPS antenna, SMA male (NZ$8), LTE antenna 698-2700MHz, SMA male (NZ$12), u.FL to SMA female bulkhead pigtail with O-ring, 15cm x2 (NZ$6), Finned heatsink 100x100x40mm, flat 5mm+ base (NZ$20), Thermal pad 1mm, 4 W/mK+ (NZ$5), Solid aluminium block 20x20x50mm (NZ$5), Thermal paste small tube (NZ$3), Bootlace ferrule kit 0.5-6mm² with ratchet crimper (NZ$30), Heatshrink ring / spade / butt terminal kit 0.5-6mm² (NZ$25), Waterproof DT-style plug pairs (2, 3, 4 and 6 pin) (NZ$63), SN65HVD230 CAN chips, 10 pack (NZ$6), UV-black cable ties + adhesive P-clips (NZ$10).

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
| GameSir G8 Galileo phone gamepad | AliExpress | 78.00 | RC mode, Sam: not now |
| EasyCAP DC60 USB capture | PB Tech | 28.75 | Only if the rear camera turns out to be RCA |
| Carlinkit CCPA from Audio City (NZ stock) | Audio City | 180.00 | Backup if the AliExpress one is slow |

Wiring parts waiting on that: AIHAT: AI HAT+ 2, ~NZ$423 (Sam: not now). Box, power and cooling stay sized for it.

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
