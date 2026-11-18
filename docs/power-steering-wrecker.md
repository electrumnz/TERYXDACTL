# Power steering from a wrecked car

New UTV kits are NZ$1,000+ (see [`power-steering-rc.md`](power-steering-rc.md)).
The cheap way is the electric power steering (EPS) column out of a small car
from a wrecker. This doc covers which cars, what each column needs to switch on,
and whether our own Pico can do the job of a bought "EPS controller".

Checked 18 Nov 2026. Forum posts are owners' reports, not factory data, so each
claim says where it came from.

## 1. Short answer

- **Yes, a wrecker column works.** Lots of people have put Toyota and Kia
  columns in old cars, buggies and kit cars. The column, its own little
  computer (ECU) and its plugs come out of the car as a set.
- **The Pi: no. The Pico: yes.** A bought "standalone controller" doesn't steer.
  It just tells the column's own computer "the engine is running and we're doing
  X km/h". The Pico can send that same message. Someone has already done it with
  an ESP32 and a CAN board on a Prius column, and has run it since 2020. The Pi
  isn't needed, and isn't a good fit because it boots slowly.
- **Steering always falls back to manual.** The column's own Toyota or Kia
  computer still reads your hands and runs the motor. The Pico never tells the
  motor what to do. If the Pico stops, the column drops to "limp mode" (heavier,
  still power assisted). If the column loses power, it's a plain steering shaft.
- **Pick, in order:**
  1. **2004-2009 Toyota Prius (NHW20) column + ECU, run by the Pico.** Common in
     NZ, the exact CAN messages are known and tested, and the Pico code for them
     is already in this repo (`teryx/eps_toyota.py`).
  2. **2012-2014 Kia Soul column (the one in Sam's YouTube video).** Needs no
     controller at all: power, earth and ignition. Reported as the beefiest of the
     lot. Harder to find in NZ.
  3. **Older Toyota Yaris / Vitz / Echo with a wired speed input.** The Pico (or
     the Shinegle's own speed output) sends a pulse. Cheap and simple, but which
     years have the wired input is murky.
- **Budget:** column + ECU about NZ$100-250 from a wrecker, plus ~NZ$10 for a
  second CAN board for the Pico, plus metal for brackets and a shaft joiner.
  Against NZ$955-1,400 for a new UTV kit.

## 2. Donor columns compared

| | Prius gen 2 (2004-2009) | Kia Soul (2012-2014) | Yaris / Vitz / Echo (older, wired speed input) | Yaris (2006-2011, with ABS) |
|---|---|---|---|---|
| What it needs to give assist | CAN: engine RPM (0x2C4) and speed (0x0B4), 500 kbit/s | Nothing: power, earth, ignition on. Runs in its "default mode" | Ignition on and a speed pulse on one wire | Reported to run in fail-safe on 3 wires |
| With nothing sent | Limp mode: Toyota's manual says assist is fixed as if doing 70 km/h; owners say little assist at low speed and a 5-15 s wait at key-on | Normal default mode | Won't turn on without pulses (Wilhelm). One MGA build says current on the speed pin alone gives fail-safe mode | "Feels just right" (Ranger Station) |
| Speed-sensitive with the Pico? | Yes, change the speed bytes | No | Yes, change the pulse rate | Unclear |
| Bought controller | Servtronic GPS box (€73.99), ePowerSteering KIT-51 (US$125), Hang Tight PSC (US$384.99) | None needed | Servtronic says non-ABS needs a different kit, ask them | Servtronic GPS box |
| Fuse | Gen 3 Prius has a 60 A EPS fuse (gen 2 not found) | Not found | 40 A in two builds | Not found |
| Found in NZ | Very common import. Trade Me had no column on the day, so wreckers / Pick a Part | 0 columns on Trade Me page 1 | Trade Me: "Steering column with elec motor only, Yaris/Vitz" NZ$150, North Shore | Common |
| Catch | Torque sensor centre needs a scan tool reset after fitting | Firmware versions differ, one builder's bench test failed on the wrong diagram | Which years/markets have the wired input isn't clear. Check the ECU plug | Same ECU part numbers matter |

Others (Corsa C / Holden Barina, Suzuki Swift, Daihatsu, Mazda 2, Toyota Aqua):
the Corsa needs both an engine pulse and a speed pulse or it shuts off after
about 10 s (controller seller's own words). For the rest we found no proven
builds or signal details, so they aren't recommended. Aqua columns are on Trade
Me for NZ$115, but nothing says what their ECU wants.

**Get the ECU and both plugs with the column.** On the Toyotas the ECU is a
separate box behind the dash. Cut the plugs out of the loom with a good tail of wire.

## 3. Can the Pico run it instead of a bought controller?

Yes, and it fits how the Teryx already works: the Pico is the one that knows the
key, the speed and whether the vehicle is locked.

### Prius column (CAN)

From the Carloop community thread (2008 Prius column in a 1967 Fairlane, running
since 2020, later redone on an ESP32 with a Waveshare SN65 CAN board):

| ID | What | Bytes they send | Notes |
|---|---|---|---|
| 0x2C4 | Engine RPM | `06 8A 00 19 00 00 92 09` | 0x068A = 1674 RPM. On its own it didn't wake the ECU |
| 0x0B4 | Vehicle speed | `00 00 00 00 8D 06 66 B5` | Bytes 5-6 × 0.0062 mph (0.01 km/h). 0x0666 ≈ 16 km/h. This makes the ECU think the ABS computer is still there |

- 500 kbit/s, both frames every 20 ms. 100 ms wasn't enough.
- With both: assist straight away at key-on, no fault codes, return to centre
  much better, and the torque sensor centre reset worked (it won't while codes are stored).
- They ran it fixed at the "10 mph" setting, which gives the most assist with no
  dead zone. Prius steps: max assist at low speed, medium around 15-40 mph,
  least above about 45 mph.
- The last byte is a checksum. We checked it's Toyota's usual one (ID bytes +
  length + data bytes) against both frames above. Our version and a test that
  rebuilds those exact bytes are in `teryx/eps_toyota.py` and
  `tests/test_eps_toyota.py`.
- Gen 3 (2010-2015) is thought to use the same IDs (poster "about 80% sure") and
  a brushless motor. Not confirmed, so stick to gen 2.

**How it'd be wired on the Teryx:**

- The column gets **its own little CAN bus**: a second MCP2515 board on the Pico's
  SPI0, with its own chip select, 120 Ω at each end. Don't put it on the main
  Teryx bus: it runs at 500 kbit/s, the Teryx bus will match the Shinegle
  (likely 250, TBC), and the Toyota IDs could clash with ours.
- **Pins are tight.** Every Pico 2 pin is already used (`wiring.md`). The easy
  fix is to free GP22 by reading the ADS1115 "ready" bit over I2C instead of its
  ALERT pin, and use GP22 as the second chip select. The Pico only transmits, so
  that board's INT pin can stay unconnected. The RC mode plan also wants pins, so
  do a full pin review before building either.
- **Rules (in `frames()` in `teryx/eps_toyota.py`):** send both frames only while
  the key is on, the Shinegle is ready and the vehicle isn't locked. Below about
  16 km/h report 16 km/h (full assist), above that report real speed so it firms
  up. Unknown speed: report 16 km/h. Speed comes from the Shinegle (CAN once
  decoded, or its J1-6 speed pulse output, per the SG1202 manual).
- **EPS power through a Pico relay** (as well as the key), like
  `power-steering-rc.md` says, so the vehicle lock and RC kill can turn it off.

### Yaris / Vitz with a wired speed input

The MGA build feeds ignition to ECU pin D32/6 and speed pulses to D32/5. At least
4 pulses wake the motor. 2 Hz, 30 Hz and 60 Hz gave three assist levels (about
60, 48 and 40 lb) and three levels of firmness. The Pico makes a pulse on one pin
through a transistor. Or the Shinegle's J1-6 speed pulse could feed it directly,
but going through the Pico keeps lock and RC kill working. Pin numbers are from a
2004 European Yaris. The author warns ABS cars may differ, so check the plug.

### Kia Soul

Nothing to send. The Pico just switches its ignition feed through a relay.

### What happens when things go wrong

| Failure | What you feel |
|---|---|
| Pico crashes or the EPS CAN wire breaks | Frames stop. Prius ECU goes to limp mode: heavier, still assisted |
| Pico sends the wrong speed | Too light or too heavy at speed. It can't steer the wheel by itself: the column's ECU only adds help in the direction your hands are already turning |
| EPS fuse blows or the relay drops | Plain manual steering (Ranger Station: with full EPS failure "the steering returns to fully manual") |
| Column ECU fault | Toyota's own fail-safes: assist stopped, fixed or reduced, depending on the fault |

**Don't** drive the column motor straight from the Pico with our own H-bridge,
skipping the Toyota/Kia ECU. That's where a software bug can turn the wheel on
its own. Using the car's own ECU keeps its years of fail-safe work.

## 4. Power (12V)

- Plan for a **60 A fuse** and its own cable straight to the 12V battery, sized
  for that fuse. The Yaris builds used 40 A; Toyota fuses the gen 3 Prius EPS at 60 A.
- The Toyota ECU stays awake for about 120 s after key-off and draws about
  220 mA (MGA build), so it doesn't flatten anything.
- Most current is drawn stopped or crawling at full lock. The DC-DC rating is
  still the open question from `power-steering-rc.md` and `wiring.md`.

## 5. Fitting it to the Teryx

- **Measure first:** the space from the steering wheel to where the Teryx
  shaft goes through to the rack. Car columns are much longer than the Teryx
  one and come with a tilt bracket and lock.
- **Mount:** a steel bracket off the dash bar using the column's own mounting
  holes. Car EPS motors push hard, so brace it. An ih8mud owner added an L
  bracket because the motor torque flexed the stock one.
- **Join the shafts:** keep the car column's lower U-joint and join it to the Teryx
  lower shaft. The MGA build welded and pinned a sliding piece onto the Toyota
  end. Measure the Teryx spline (count and diameter) to see whether an
  off-the-shelf adaptor fits before welding. Steering welds need to be good:
  get a proper welder to do them if in doubt.
- **Water:** these columns are made to live inside a car. Our guess (not from a
  source): mount the column and ECU high under the dash, add a cover, and give
  the plugs drip loops.
- **Torque sensor centre:** Prius needs a scan tool reset after fitting
  (Techstream or a bi-directional tool such as an Autel). Wilhelm's Yaris has a
  TS pin for this.
- **RC mode** still works the same way (fake torque sensor signal into the
  column ECU), but the donor column's torque sensor signal needs measuring first.

## 6. Next steps

1. Look for a 2004-2009 Prius (or a 2012-2014 Kia Soul) at Pick a Part / wreckers.
   Get column, ECU and plugs. Pick a Part is in person only.
2. Measure the Teryx steering space and spline.
3. Bench test on a 12V supply: Prius ECU + an MCP2515 on a Pico running the two frames.
4. Pin review on the Pico 2 (EPS CAN chip select, RC mode).
5. DC-DC rating.

## Sources

- Sam's video: DirtGearTv, "Add Electric Power Steering To Any Vehicle for $150 | EPS Conversion" (2014 Kia Soul column, 3 wires): https://www.youtube.com/watch?v=oRNOmAqsVLg (YouTube blocked a transcript from here; details from the description via search)
- Carloop community, Prius EPS CAN frames: https://carloop.github.io/community/t/modifying-can-transmit-sample-app-to-control-retrofit-electric-power-steering/856.html and page 2: https://carloop.github.io/community/t/modifying-can-transmit-sample-app-to-control-retrofit-electric-power-steering/856-1.html?page=2
- The Ranger Station, Toyota EPS conversion (Prius/Corolla/Yaris/Soul ECU numbers, 3 wires, fail-safe): https://www.therangerstation.com/tech/toyota-electric-power-steering-eps-conversion/
- MGA Guru, 2004 Yaris column in an MGA (pins D32/5 and D32/6, pulse rates, 40 A, 220 mA): https://mgaguru.com/mgtech/steering/sr302.htm
- Wilhelm Raceworks, 2007 Yaris column in an MR2 (speed input, TS pin, 40 A): https://wilhelmraceworks.com/blog/electric-power-steering-conversion
- Grassroots Motorsports forum, junkyard EPS (Soul default mode, Prius fail-safe): https://grassrootsmotorsports.com/forum/grm/have-we-talked-about-the-junkyard-electric-power-steering-assist-stuff/257657/page1/
- LS1Tech, $35 EPS with fail-safe (Kia ECU is remote, Kia unit the most heavy duty, wiring differs): https://ls1tech.com/forums/suspension-brakes/1848775-35-electric-power-steering-fail-safe-no-ebay-module-no-caster-issues.html
- Kia Soul Forums, two EPS module firmware versions: https://www.kiasoulforums.com/threads/2013-soul-base-running-in-limp-home-mode-now.123446/
- Toyota 2004 Prius repair manual, EPS fail-safe chart (CAN fault: assist fixed at 70 km/h): https://share.qclt.com/%E4%B8%B0%E7%94%B0%E6%99%AE%E7%91%9E%E6%96%AF%E5%8E%9F%E5%8E%82%E8%8B%B1%E6%96%87%E6%89%8B%E5%86%8CPDF%E6%A0%BC%E5%BC%8F/Repair%20Manual/04pruisr/05/21bvv/cifschar.pdf
- Prius gen 3 fuse chart (EPS 60 A): https://attachments.priuschat.com/attachment-files/2023/10/244871_Prius_gen3_Engine__Interior_Fuses.pdf
- Servtronic GPS controller (€73.99, ships worldwide): https://www.servtronic.com/products/new-automatic-gps-toyota-prius-yaris-electronic-power-steering-controller-box-kit
- ePowerSteering KIT-51 (US$125): https://epowersteering.com/page/2?product_view=list&product_orderby=price&product_count=36
- Hang Tight PSC (US$384.99): https://drifthq.com/products/hang-tight-psc-epas-power-steering-controller
- Corsa EPAS controller listing (needs 2 signals, shuts off after 10 s): https://www.ebay.com/itm/322372412305
- epasuino (Arduino speed-sensitive EPAS helper, Apache-2.0): https://github.com/srenner/epasuino
- ih8mud, Yaris column install (L bracket): https://forum.ih8mud.com/threads/electric-power-steering-install.1365119
- Trade Me searches 18 Nov 2026: "yaris steering column", "prius steering column", "kia soul steering"
- Pick a Part NZ (in-person only, no holds or shipping): https://pickapart.co.nz
