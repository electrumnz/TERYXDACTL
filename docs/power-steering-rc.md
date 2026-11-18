# Power steering (EPS) and RC mode

Sam's 2013 Teryx 750 2-seater has no power steering. This doc covers:

1. Electric power steering (EPS) kits, AliExpress versus the bolt-in brand kits.
2. How much 12V current EPS pulls.
3. Whether the Pico can feed it a speed signal.
4. Using the EPS to steer the Teryx by remote (RC mode), plus brake, kill
   switch and radio, with a rough total.

Prices checked 18 Nov 2026, logged in to AliExpress with NZ as the ship-to
country, so shipping figures are what AliExpress quoted for NZ. AliExpress says
"Tax excluded, add at checkout", so add 15% GST on top.

Cheaper option: a column from a wrecked car, see
[`power-steering-wrecker.md`](power-steering-wrecker.md).

**RC mode for launching off the beach or a ramp (phone remote, RC box, speed
caps, water limit, 4G) is now planned in [`rc-beach-launch.md`](rc-beach-launch.md).**
That doc replaces the 8 km/h cap and the radio pick below.

## 1. Short answer

- **Best AliExpress pick:** the CFMoto CF800-style EPS unit (part 7020-100400,
  "Paeps 7001") from MITMC EXTREME MOTOR Parts. About **NZ$955 shipped, around
  NZ$1,100 with GST**. It has the most sales and reviews of any EPS on there.
  It is **not** made for the Teryx: you'd make a bracket and shaft adapters.
- **Bolt-in option:** SuperATV EZ-STEER PS-K-TRX, made for the 2008-2013 Teryx 750.
  It costs US$792.95 before shipping, so it ends up roughly the same price once
  the AliExpress shipping and GST are added. It bolts straight in, is sealed, and
  has a 3 year warranty.
- **RC mode is doable** with either one. The Pico pretends to be the driver by
  sending its own signal into the EPS torque sensor input. This needs care, see section 5.
- **Before buying anything, find out the DC-DC rating.** EPS can pull 30-60 A on 12V.

## 2. EPS options

| | A. CF800-style EPS (AliExpress) | B. "Universal 12V EPS kit" (AliExpress) | C. "Universal EPS NAR-6101S" (AliExpress) | Ref: SuperATV EZ-STEER PS-K-TRX |
|---|---|---|---|---|
| Link | [item 1005003788140709](https://www.aliexpress.com/item/1005003788140709.html) | [item 1005012226808860](https://www.aliexpress.com/item/1005012226808860.html) | [item 1005012352920877](https://www.aliexpress.com/item/1005012352920877.html) | [superatv.com](https://www.superatv.com/kawasaki-teryx-power-steering-kit) |
| Price | NZ$706.79 | NZ$591.99 | NZ$510.19 | US$792.95 |
| Shipping to NZ | NZ$248.03 express (27 Nov - 10 Dec) | NZ$430.17 standard | NZ$710.88 standard | not checked |
| Shipped total, before GST | **NZ$954.82** | NZ$1,022.16 | NZ$1,221.07 | about NZ$1,330-1,410 before shipping and GST (at 1.68-1.78 NZD per USD, rate not confirmed for today) |
| Reviews / sold | 4.8 stars, 11 reviews, 86 sold | 5.0 stars, 2 reviews, 3 sold | no reviews, 3 sold | many retailers, 3 yr warranty |
| Store | 94.5% positive, 6,599 followers | HaiGou Store, 100%, 615 followers | Factory General Store, 100%, 68 followers | SuperATV |
| Weight | 8 kg | 6.9 kg | 15 kg packed | |
| Fits a Teryx? | No, made for CFMoto. Reviewers fitted it to other quads by modifying the steering column and making a motor mount | "Universal", no fitment details | "Universal", no fitment details | Yes, 2008-2013 Teryx 750 |
| Specs given | Model and size only | Hardly any | Hardly any | See install guide |

**Pick A over B and C.** It's the cheapest once shipped, and it has real buyers.
One buyer fitted it to a CFMoto 500 after modifying the steering column and
adding a mount for the motor. Another said the wiring diagram arrived separately
by email. B and C are thin listings from trader stores with almost no sales.

**What fitting A on the Teryx involves** (from the SuperATV install, which does the
same job): the EPS unit goes in the steering shaft between the column and the
rack. SuperATV supplies a new lower shaft through the firewall to the rack, a
U-joint from the motor to the stock upper shaft, and a bracket bolted to the frame
near the park brake lever. For A you'd have to make all of those, plus match the
splines at both ends. **Spline sizes for A are not listed.** Ask the seller for
the input and output spline counts and diameters, and measure the Teryx shaft,
before ordering.

Other Teryx-specific kits seen: Rugged UTV PEPS-3002 (US$509-689 at
UTVSource) and Demon Powersports 220W (about US$700, Vivid Racing). Vivid
Racing says the Demon kit doesn't fit Teryxes with the dual cup holder.

## 3. 12V current

| Kit | Current / fuse | Source |
|---|---|---|
| 220W universal (Kartek) | Motor current 30A, 40A fuse, ECU input 10-16V | Kartek listing |
| 400W universal (Kartek) | 33A peak at full lock (400W / 12V) | Kartek listing |
| CFMoto CFORCE 800 EPS | 60A fuse in the parts list | CFMoto parts diagram |
| SuperATV PS-K-TRX | Red and black straight to the battery, white to switched 12V (Kawasaki brown ignition wire) | SuperATV install guide |

EPS pulls the most when you're stopped or crawling at full lock, which is
exactly when you're winching or picking through rocks. **Peaks come off the 12V
battery and the DC-DC tops it back up**, so the DC-DC rating (still TBC in
`wiring.md`) decides whether the battery slowly drains when you're winching and steering at the same time.
Plan for a 60A fuse and its own cable to the battery for kit A, and size the cable for that fuse.

Wire the "switched 12V" enable through a Pico-controlled relay (as well as the
key), so the vehicle lock and RC kill can both turn it off.

## 4. Speed input (speed-sensitive assist)

- **SuperATV PS-K-TRX:** only power, earth and switched 12V. The install guide
  has no speed wire, so it's torque only, with no speed-sensitive assist.
- **CFMoto-style EPS (kit A):** EPS units in this class decide how much assist
  to give from the torque sensor *and* vehicle speed (a UTV service manual found in the search,
  general EPS description). A CFMoto forum owner found the speed sensor shares a
  wire with the EPS module. So kit A most likely has a speed input. **Not
  confirmed for this exact unit**: get the seller's wiring diagram first.
- **Pico feeding it:** the Pico already gets speed from the Shinegle over CAN,
  so it can make a matching pulse train on a spare GPIO for the EPS speed
  input. Light steering when parking and firmer steering at speed. The
  pulses per km/h has to be matched to what the EPS expects. Scope the
  CFMoto sensor spec or test on the bench.
- **No CAN** is listed on any of the AliExpress units.

## 5. RC mode: can the Pi or Pico steer it?

Yes. An EPS unit can't tell a driver's hands apart from a fake torque sensor
signal. A "torque interceptor" sits in the torque sensor wiring and changes
the signal, so the EPS turns the wheel as if a driver were turning it.
comma.ai describe this approach and say Waymo used it on early cars.

**Who does what:**

- **Pi 5:** RC mode screen, arming, shows the radio link and speed cap. It does
  **not** steer. The Pi isn't real time and it takes a while to boot.
- **Pico 2 (control box):** runs the steering loop. It reads the radio, reads a
  steering angle sensor, and writes the fake torque signal through a DAC. It also
  sends the throttle request to the Shinegle and works the brake actuator.
  This fits the existing split, where the Pico handles safety.

**Steering loop:** the radio sends the steering angle you want. An angle sensor on the column
(AS5600 or MT6701 magnet sensor) gives the real angle. The Pico works out the
"torque" to send so the column moves toward the target angle. RP2350 has no DAC, so use an
MCP4728 I2C 4-channel DAC (two channels if the torque sensor has two
outputs, as most do for safety). **The torque sensor's voltage range is not
known yet**: measure it with a multimeter at centre, full left effort and full right effort when the unit arrives.

**Hardware failsafe for normal driving:** a relay chooses whether the EPS ECU
sees the real torque sensor or the Pico. With the relay **off**, the EPS sees the
real sensor, so the Teryx steers like normal. The Pico has to hold the relay on
for RC mode. If the Pico crashes, browns out or loses power, the relay drops and
normal steering comes back.

**comma.ai's warnings, which apply here:** the EPS motor can overpower the person at the wheel,
so a bad signal can stop you steering. Don't trust it because a few test runs
went well, test what happens when each part fails. They also say if a chip wouldn't be good
enough for an EPS module, it isn't good enough for an interceptor. This is a
private land, low speed, nobody in the seat or nearby feature.

### Safety rules for RC mode (non-negotiable)

1. **Nobody in the seat, nobody near the vehicle**, private land only.
2. **Speed cap 8 km/h** in RC mode, enforced by the Pico on the Shinegle throttle request.
3. **Link loss stop in under 0.25 s, done by the Pico.** ExpressLRS only goes
   into failsafe when link quality hits 0 or after about **1 second** with no
   good packet. At 8 km/h that's about 2.2 m. Too slow, so the Pico times out
   on CRSF packets itself (about 200 ms) and stops.
4. **Dead-man:** a sprung switch on the radio must be held. Let go and it stops.
5. **Physical e-stop button** on the vehicle, wired in series with the
   Shinegle key/enable line, so it cuts drive with no software involved.
6. **Separate radio kill**, see the note on 433 MHz relays below.
7. RC mode can only be switched on when parked, park brake on, with the vehicle unlocked.

**Stopping:** cutting drive doesn't stop the Teryx on a hill. RC mode needs a brake.

- **Brake actuator on the pedal.** Measure the pedal force and travel needed for a
  hard stop first (luggage scale on the pedal). The cheap 12V actuators on
  AliExpress are **too slow**: the best-selling feedback one does 27 mm/s at
  600N and 4 mm/s at 1500N ([item 1005009338057759](https://www.aliexpress.com/item/1005009338057759.html)).
  You want at least about 50 mm/s with a position output. The fast 160 mm/s HAKIWO is 48V only. Not
  chosen yet.
- **Regen** through the Shinegle, if the brake input in `brake-regen.md` works
  out, could do most of the slowing, with the pedal actuator as the backup.
- A powered actuator **doesn't brake when the power is cut**. So with full power
  loss the Teryx coasts with drive cut. A spring-applied brake (spring pulls the
  pedal, actuator holds it off) would fix that. Worth designing in before trying
  it on a slope.

**Note on 433 MHz "wireless battery disconnect" relays** (about NZ$43, 2,000+
sold, [item 1005009960036689](https://www.aliexpress.com/item/1005009960036689.html)):
they latch. If you're out of range when you press the button, nothing happens.
Fine as an extra kill, but **not** the failsafe. The failsafe is the Pico holding
the drive enable relay on only while good packets arrive and the dead-man is held.

## 6. RC parts and rough total

| Part | Pick | Price (NZ$, before GST) |
|---|---|---|
| EPS | A. CF800-style, shipped | 954.82 |
| Radio | RadioMaster Pocket ELRS (3,000+ sold, [item 1005005975423127](https://www.aliexpress.com/item/1005005975423127.html)) | 112.37 |
| Receiver | RadioMaster ER5A V2 ELRS PWM (or a CRSF receiver straight into a Pico UART) ([item 1005008096047362](https://www.aliexpress.com/item/1005008096047362.html)) | 40.59 |
| DAC | MCP4728 4-channel I2C ([item 1005009064769721](https://www.aliexpress.com/item/1005009064769721.html)) | 1.97 |
| Steering angle sensor | AS5600 (10,000+ sold, [item 1005007038660086](https://www.aliexpress.com/item/1005007038660086.html)) | 3.29 |
| Torque signal changeover relay | DPDT signal relay module ([item 1005013589456340](https://www.aliexpress.com/item/1005013589456340.html)) | 3.09 |
| E-stop button | 22 mm lockable mushroom, NC ([item 1005008518428843](https://www.aliexpress.com/item/1005008518428843.html)) | 7.09 |
| Extra radio kill | 433 MHz battery disconnect, 240A ([item 1005009960036689](https://www.aliexpress.com/item/1005009960036689.html)) | 42.89 |
| Brake actuator | Not chosen, needs pedal measurements first | budget 100-250 (guess) |
| **Total** | | **about NZ$1,270-1,420 before GST and shipping on the small parts** |

Most of the small parts ship cheaply or free with other orders. Shipping wasn't
checked on each one.

## 7. Next steps

1. Find the DC-DC rating and 12V battery size (also blocks the winch maths).
2. Ask the MITMC seller for the wiring diagram, spline sizes, rated current
   and whether it has a speed input. Measure the Teryx steering shaft.
3. Measure brake pedal force and travel, then choose the actuator.
4. When the EPS arrives: bench test on the 12V supply, measure the torque
   sensor voltages, then the Pico interceptor with the relay failsafe.

## Sources

- AliExpress listings above, viewed 18 Nov 2026 with NZ shipping.
- SuperATV, Kawasaki Teryx Power Steering Kit: https://www.superatv.com/kawasaki-teryx-power-steering-kit
- SuperATV install guide IN-PS-K-TRX (rev 3/6/2018): https://cdn.shopify.com/s/files/1/0331/2341/files/IN-PS-K-TRX.pdf.pdf
- Kartek 220W universal EPS kit: https://www.kartek.com/parts/220-watt-12-volt-sand-rail-dune-buggy-baja-bug-manx-or-utv-universal-electric-power-steering-kit.html
- Kartek 400W universal EPS kit: https://kartek.com/parts/400-watt-12-volt-sand-rail-dune-buggy-baja-bug-manx-or-utv-universal-electric-power-steering-kit.html
- CFMoto CFORCE 800 steering system EPS diagram (60A fuse): https://cfmotousaparts.com/product/diagram-2017-cfmoto-cforce-800-cf800-2-steering-system-eps-f10-3
- CFMoto forum, EPS failure and shared speed sensor wire: https://cfmoto-forum.com/general-discussion/2021-cfmoto-600-eps-failure
- Rugged UTV PEPS-3002 at UTVSource: https://www.utvsource.com/rugged-utv-products-kawasaki-krf750-800-teryx-electric-power-steering-kit/
- Demon Powersports Teryx 750 kit (Vivid Racing): https://www.vividracing.com/demon-powersports-rugged-electrical-power-steering-kit-220w-for-kawasaki-teryx-750-20082013-p-153016609.html
- comma.ai, Safer control of steering: https://blog.comma.ai/safer-control-of-steering/
- ExpressLRS failsafe timing (LQ 0 or 1 s without a channels packet): https://expresslrs.org/hardware/pwm-receivers/
- USD to NZD: Key Currency 1.78 (13 Oct 2026), Wise about 1.65-1.69 (undated). Check on the day.
