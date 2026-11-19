# Brake pedal regen

> **Dropped 2026-11-19 (Sam's call).** Regen is left to the Shinegle controller
> and the brake pedal stays standard. No pedal sensor, no second ADS1115, no
> control box regen rules. The dash just shows regen on or off: the battery
> teeth glow green and pulse while the motor puts charge back
> (`dash/web/js/regen.js`). Default (Sam, 2026-11-19): speed above 0 and the
> throttle at rest (micro switch off if we get it, else within 3 % of zero).
> The dash setting `regenFrom: "current"` switches to current flowing back
> into the pack while moving. The Shinegle's own regen flag wins if it sends one. How strong regen feels is set on the Shinegle itself
> with the SG1810 programmer (`B_Rat` / `DecRat`, see
> [`shinegle-sg1810-tables.md`](shinegle-sg1810-tables.md)). Control box
> settings 22-29, CAN ID 0x715 and fault bit 15 are kept reserved. The code is
> in git history (PR #23) if we ever come back to it. The rest of this page is
> the old research, kept for reference.

Idea: the first part of the brake pedal makes the motor brake (regen, puts
charge back in the battery), and the normal hydraulic brakes come in on top as
you push further. The more pedal, the more regen, up to a strength you set on
the dash.

**Status:** test feature, **off by default** (control box setting 22
`brake_regen_on`). The rules are written and tested in the simulator. It can't
go on the real Teryx until we know the Shinegle controller can take a regen
request (section 3).

## 1. Short answer

**Probably doable, but it hangs on one thing we can't find out online:** how the
Shinegle controller lets something else ask it for regen. Shinegle don't publish
a manual or pinout for their controller. Everything public about the kit says
"vector control", "CAN", "comes with programmer and accelerator", and nothing
about a brake input or regen settings (sources 1–3).

Other controllers in this class do have exactly this. The Curtis 1236/1238, a
well known AC induction controller, has a "Brake Pot" input
that sets regen current from the pedal, plus a "Brake Taper Speed" that fades
regen to zero at a stop (source 4). Kelly controllers have three separate regen
settings: on throttle release, on a brake switch, and a 0–5 V analogue brake
input for variable regen (source 5). So it's very likely the Shinegle has at
least some of this, but **that's a guess until we look at the real one**.

One thing worth knowing: **a Tesla doesn't do this.** Tesla's regen is on
lifting off the accelerator, and the brake pedal is plain friction brakes. Tesla
also cuts regen back when the battery is cold or full, and turns the brake
lights on when regen slows the car hard (source 6). Regen on the brake pedal is
usually called "blended braking". If what you're after is the Tesla
feel, that's lift-off regen, and the Shinegle programmer may already have a
setting for it (check list below). This doc covers the brake pedal version
since that's what you asked for, and both can run together.

## 2. How it works

```
 brake pedal ──┬── master cylinder ── hydraulic brakes      (untouched, always works)
               │
               └── Hall angle sensor (just watches the pedal)
                        │ 0.5–4.5 V
                        ▼
                  Pico control box  ── rules below ──►  regen request ──► Shinegle
                        ▲                                (analogue, switch or CAN: TBC)
          speed, direction, throttle, battery %, 4WD state, brake switch
```

* **The hydraulic brakes are not changed at all.** No lost-motion pushrod, no
  extra free travel, nothing in the brake lines. The sensor only watches the
  pedal. If the sensor, the Pico or the Shinegle all fail, you still have
  exactly the brakes you have today.
* Regen comes in over the pedal's existing free play and the first light bit
  of pressure, then the pads take over. We don't add free travel, because that
  would delay the hydraulic brakes, and that's the one thing it must never do.
  The trade off: it won't feel like a pure "regen only" zone, it'll feel like
  stronger brakes for less pedal, with charge going back in.
* All the decisions are made on the **control box**, not the Pi, same as every
  other safety rule. The dash only sets the strength.

### Rules (teryx/regen.py, tested in tests/test_brake_regen.py)

Every rule can only lower regen, never raise it.

| # | Rule | Why |
|---|---|---|
| 1 | Feature off → nothing | Off until the Shinegle check is done |
| 2 | Pedal sensor out of range (broken wire, short, not calibrated) → no regen, fault latched until "clear faults" | Fail safe. A bad sensor must never cause braking you didn't ask for |
| 3 | Pedal reads well down but the stock brake switch says "not pressed" for 0.5 s → same as rule 2 | Catches a sensor that has slipped or drifted |
| 4 | Below 5 % pedal → nothing, then linear to full at 30 % pedal | A resting foot doesn't brake. Set "full" near where the pads bite |
| 5 | × strength setting (default 50 %) | The dash setting |
| 6 | Speed unknown, not in forward, or throttle on → nothing | No guessing. Left-foot braking on a climb is a real off-road trick, so the motor isn't made to fight itself |
| 7 | Fades to nothing below 5 km/h | Motor braking can't hold a stop and goes jerky near zero (Curtis do the same, source 4). Hydraulics finish the stop |
| 8 | Battery 90–98 % → fades to nothing | A full battery can't take the charge (Tesla do the same, source 6) |
| 9 | Not in 4WD → × 60 % | In 2WD it only brakes the rear wheels, which can lock up on gravel downhill. No ABS on a Teryx |
| 10 | Rises at most 250 %/s, drops instantly | No snatch when you touch the pedal |
| 11 | Regen over 10 % lights the brake lights | Regen on its own still has to show brake lights (source 7) |

### Settings (control box, Settings → Safety limits on the dash)

| Key | Name | Default | Range |
|---|---|---|---|
| 22 | `brake_regen_on` | 0 (off) | 0–1 |
| 23 | `brake_regen_pct` strength | 50 % | 0–100 % |
| 24 | `brake_regen_start_pct` | 5 % pedal | 0–50 % |
| 25 | `brake_regen_full_pct` | 30 % pedal | 5–100 % |
| 26 | `brake_regen_fade_kmh` | 5 km/h | 0–20 km/h |
| 27 | `brake_regen_2wd_pct` | 60 % | 0–100 % |
| 28 | `brake_pedal_min_raw` | 2000 | raw counts, pedal up |
| 29 | `brake_pedal_max_raw` | 22000 | raw counts, pedal on the floor |

The control box reports what it's doing on CAN 0x715 (`PICO_REGEN`, see
[`CAN_PROTOCOL.md`](CAN_PROTOCOL.md)): pedal %, regen request %, state (off,
ready, active, limited, sensor fault), what's limiting it, raw pedal reading
(for calibrating) and the brake light bit. Fault bit 15 on 0x710 is
"brake pedal sensor".

### In the simulator

Turn it on with Settings → Safety limits → "Brake pedal regen" = 1. The sim's
brake slider is the pedal: the control box reads it as the pedal sensor and the
fake Shinegle adds the regen on top of the hydraulic braking (up to 4 kW, a
guess). You'll see the power bar go into regen and the trailer brake light come
on. The Pico firmware stores and acks settings 22–29 but doesn't run the rules
yet; that waits for the Shinegle check, because the output side depends on it.

## 3. What to check on the real Shinegle (do this first, costs nothing)

**Update 2026-11-18: we now have the controller manual** (SG12X2, covers
Sam's SG1202), summarised in [`shinegle-controller.md`](shinegle-controller.md).
It confirms "full regeneration capability" but shows **no brake input and no
regen settings**: only 14 of the 35 J1 pins are drawn. The programmer is the
**SG1810** handheld, on a serial link (J1-25 +12 V, J1-28 Tx, J1-29 Rx,
J1-7 ground). CAN is listed as **optional** (CANopen, 29-bit IDs). So items 1
and 2 below are now the main job: the SG1810 menus, and which J1 pins
actually have wires in the harness.

**Update 2026-11-18 (later): we have the SG1810 programmer manual**, copied in
[`shinegle-sg1810-programmer.md`](shinegle-sg1810-programmer.md), with the
full parameter list in [`shinegle-sg1810-tables.md`](shinegle-sg1810-tables.md).
What it says about regen:

* **`B_Cur` (page 9) is the regen strength**, "Regenerative brake
  Coefficient", 512-4096. Locked: "prohibited to change without authorized".
* **`B_Rat` (brake rate) and `DecRat` (deceleration rate), page 4**, default
  12, range 3-36, green = Shinegle allow changing them. These are the knobs to
  try first for lift-off regen feel (item 3 below).
* Other brake ones, all "already optimised" or "special vehicle": `B_Trat`
  (braking current response, 32, range 24-64), `B_Trat2`, `BrkRat2`, `BrkTm`.
* **Fault 13 is "main contactor or brake fault"** (Chinese 制动器 = brake), so
  the controller does watch some brake device. Its pin is still unknown.
* **Faults 14 and 19**: braking too hard can over-volt the battery; the fix is
  a lower brake or deceleration rate. So keep regen soft when the pack is full.
* Nothing in the menus is a brake *input* setting, so item 2 (harness pins)
  still decides routes A to C.

Takes about half an hour with the Shinegle programmer and the wiring diagram
that came in the box. Ticks here decide which way we go.

1. **Programmer menus.** Look for anything named brake regen, EBS, braking
   energy recovery, regen %, sliding/coasting regen, brake type, brake
   analogue. Chinese menus: 制动 or 刹车 = brake, 能量回收 = energy recovery,
   回馈 = feedback/regen. Photo every screen, they help either way.
2. **Harness pins.** On the wiring diagram or the plug labels, look for BRK,
   brake, brake switch, brake analogue, 0–5 V input, second throttle, "EBS".
   Note which pins go nowhere in your harness.
3. **Lift-off regen.** Does it already slow down when you lift off the
   throttle? Is there a % for it in the programmer? (This is the Tesla style
   one, and if it's there it's a free win.)
4. **Brake switch.** Is the stock Teryx brake switch (or any brake wire) wired
   into the Shinegle at the moment?
5. **During the CAN decode** ([`shinegle-decode.md`](shinegle-decode.md)), the
   decode steps already include a regen test. Also note whether the Shinegle
   seems to *listen* for any frames from its dash (frames stop when the dash is
   unplugged = it may take commands over CAN).
6. **Ask the seller** (Shinegle on Alibaba / made-in-china): "Does the SG1202
   controller have an analogue brake regen input or brake switch input? Which
   J1 pins? Is CAN fitted on mine? Can regen be set in the SG1810 programmer
   or commanded over CAN or SCI? Can you send the full J1 pinout, the SG1810
   programmer manual, and the CAN and SCI protocols?"

### Which way we go after the check

| What the Shinegle has | Variable regen? | What we build |
|---|---|---|
| **A. Analogue brake input** (0–5 V, like Curtis/Kelly) | Yes | Pico makes the voltage from its regen request. The Shinegle's signal side is almost certainly tied to the 72 V pack's negative, not the 12 V chassis, so the Pico drives it through an **opto-isolator + RC filter powered from the Shinegle's own 5 V** (no wire joins the two sides). Pico dead = 0 V = no regen |
| **B. Brake switch input only**, regen % set in the programmer | On/off only | Pico closes the brake input (through an opto/relay) in the regen zone. Strength is whatever the programmer is set to, the dash slider would be off/on. Still useful |
| **C. Takes a regen/torque command over CAN or the SCI serial port** | Yes | Pico sends it. Needs the protocol from Shinegle, we won't guess command frames on a motor controller |
| **D. None of the above** | No | Can't do brake pedal regen with this controller. Fall back to lift-off regen from the programmer |

**We never fake the throttle signal** to get regen, and never put anything
between the pedal and the master cylinder.

## 4. Parts (only buy once the check above passes)

| Part | Why | Rough NZ cost |
|---|---|---|
| Hall angle sensor, sealed, 5 V, 0.5–4.5 V out (eg Amphenol Piher HRPM, IP69K) | Reads pedal travel at the pedal pivot, no contact to wear out | ~$130 (HK$586 at element14, source 8) |
| Printed bracket + lever to the pedal arm | Mount the sensor | filament |
| 2nd ADS1115 (address 0x49) + 10k/20k divider | ADS1115 #1 is full | $15–25 |
| Opto-isolator (PC817) + resistor + capacitor | Route A only | $5 |
| Brake pressure transducer 0.5–4.5 V, 1/8" NPT, optional (eg Amphenol P51, source 9) + banjo/tee adaptor | Second opinion on the pedal sensor. Note it reads nothing in the free play, so it can't replace the pedal sensor | $60–250 depending on brand, **not price checked** |
| Brake light relay or diode into the stock brake light circuit | So the Teryx's own brake lights come on with regen, not only the trailer plug | $10 |

**Total: roughly $150–250** for route A or B, plus the optional pressure
sensor. Treat these as rough, prices weren't checked in NZ shops.

## 5. Confirmed vs still to check

| | Item |
|---|---|
| Confirmed | Shinegle kit SG-72-7.5: 72 V, 7.5 kW rated / 15 kW peak, vector control, CAN, comes with programmer and accelerator (sources 1, 2) |
| Confirmed | Curtis 1236/1238 and Kelly controllers have analogue brake regen inputs and fade regen near zero speed (sources 4, 5) |
| Confirmed | Tesla regen is lift-off, not brake pedal, and is limited when the battery is cold or full (source 6) |
| Confirmed | UN R13-H: regen alone must light the brake lights above 1.3 m/s² decel and must not below 0.7 m/s² (source 7). We use "over 10 % regen" until we can measure decel on the real Teryx |
| Confirmed | 2013 Teryx 750: dual hydraulic front discs with 2-piston calipers, sealed oil-bathed multi-disc rear brake (source 10) |
| Confirmed | Controller is the Shinegle SG1202: vector control, "full regeneration capability", SG1810 handheld programmer on SCI serial (J1-25/28/29/7), CANopen optional (source 12) |
| Confirmed | The manual shows no brake input and no regen settings (source 12) |
| **To check** | Whether the Shinegle has a brake input on an undrawn J1 pin, of what type, and its voltage (section 3) |
| **To check** | Whether Sam's SG1202 has CAN fitted |
| Confirmed | SG1810 menus: regen coefficient `B_Cur` (locked), brake rate `B_Rat` and decel rate `DecRat` (3-36, allowed to change). Fault 13 = contactor or brake fault (source 13) |
| **To check** | What `B_Cur`, `B_Rat` and `DecRat` are set to on Sam's controller (photo page 4 and page 9 in Mode A) |
| **To check** | Whether the Shinegle's signal ground is the pack negative (assumed, so we isolate) |
| **To check** | How much regen the Shinegle can actually give (sim guesses 4 kW) |
| **To check** | Teryx brake pedal free play and where the pads bite (sets setting 25) |
| **To check** | The battery's charge limits, especially cold (lithium can't take charge below about 0 °C, the BMS should block it). The Pico doesn't see battery temperature yet |
| **To check** | Whether the stock brake light switch closes early enough, and how to light the stock brake lights from the Pico |
| **To check** | Whether the Shinegle already blocks regen at full battery by itself |

## 6. Sources

1. [Shinegle 7.5 kW conversion kit for UTV/ATV, made-in-china.com](https://www.made-in-china.com/showroom/1a6d66f17f5919e6/product-detailtvfnapzZTlYA/China-Shinegle-7-5kw-Conversion-Kit-for-UTV-ATV.html): model SG-72-7.5, 72 V, CAN, vector control, "with programmer and accelerator". No mention of regen or brake input.
2. [Shinegle 5–30 kW kits, E Smart Way](https://e-smartway.com/products/shinegle-5kw-10kw-15kw-20kw-30kw-electric-car-conversion-kit): kit includes key switch, "stall switch", accelerator and 4 m harness. No brake input listed.
3. [Shinegle 7.5 kW listing, bestsuppliers.com](https://bestsuppliers.com/index.php/products/qjxvekujvovm/shinegle-75kw-72v-96v-ac-electric-motor-controller-transaxle-battery-regenerative-braking-golf-cart): title says "regenerative braking", no detail on how it's triggered.
4. [Curtis 1236/1238 manual](https://www.thierry-lequeu.fr/data/CURTIS-1236-1238.pdf): Brake Pot input (pin 17), Brake Type, Brake Current Limit, Brake Taper Speed (fades braking current to 0 at zero speed), broken-wire detection on 2-wire pots.
5. [Kelly KLS-S manual](https://manuals.plus/kelly/kls-s-series-cheetah-controllers-manual): brake switch input, Brake_AN 0–5 V "variable regen", separate regen % for throttle release, brake switch and brake analogue (each 0–50 %).
6. [Tesla Model 3 owner's manual, Braking and Stopping](https://www.tesla.com/ownersmanual/model3/en_mo/GUID-3DFFB071-C0F6-474D-8A45-17BE1A006365.html): regen when your foot is off the accelerator; limited if the battery is cold or full; brake lights on when regen slows the car hard.
7. [UNECE GRRF/2010/10, amendment to Regulation 13-H, para 5.2.22.4](https://digitallibrary.un.org/record/675284/files/%5BE_%5DECE_TRANS_WP.29_GRRF_2010_10-EN.pdf): stop lamp thresholds for regen braking.
8. [Amphenol Piher HRPM-A-050S-05-A, element14](https://hk.element14.com/amphenol-piher-sensorscontrols/hrpm-a-050s-05-a/hall-effect-rotary-sensor-50deg/dp/4180225): 50° Hall rotary sensor, 5 V, IP69K.
9. [Amphenol P51 1000 psi 0.5–4.5 V pressure sensor, Digi-Key NZ](https://www.digikey.co.nz/en/products/detail/amphenol-ssi-technologies/P51-1000-S-B-I36-4-5V-000000/1665851).
10. [Kawasaki Teryx 750 FI 4x4 Sport specs, CycleChaos](https://www.cyclechaos.com/wiki/Kawasaki_Teryx_750_FI_4x4_Sport).
11. [GEVCU analogue brake discussion](https://groups.google.com/g/gevcu-development/c/X3sNoh9HC9E): a DIY VCU reading an existing brake pressure sensor for regen; set the "brake min" above the resting reading or it thinks you're braking, and brake overrides throttle.
12. Shinegle "SG12X2 Manual" (SG1202/1212/1222), 9 pages, 2017, supplied by Sam. Summary: [`shinegle-controller.md`](shinegle-controller.md).
13. Shinegle "6_Programmer SG1810 Instruction English 20220415", screenshots supplied by Sam. Copy: [`shinegle-sg1810-programmer.md`](shinegle-sg1810-programmer.md).
