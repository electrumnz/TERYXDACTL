# Stock 2013 Teryx 750 drivetrain: what it has and what Teryx OS does with it

This sets the 2WD/4WD, diff lock and handbrake defaults in the control box.
Everything under **Confirmed** comes from Kawasaki's own owner's manuals
(linked below). Anything we haven't been able to confirm is in
**Still to check on the real vehicle** at the bottom.

The Teryx here is a 2013 Kawasaki Teryx 750 FI 4x4 two-seater (KRF750),
converted to electric with a Shinegle 7.5 kW kit.

---

## Confirmed (Kawasaki owner's manuals)

### 2WD / 4WD
- It's an **electric switch on the dash**, not a lever. Kawasaki calls it the
  "selectable 2WD/4WD shift switch". [1] [2]
- **Stop first.** "To shift, first stop the vehicle completely then press the
  electrically selectable 2WD/4WD shift switch up or down." [1]
  "Always stop the vehicle before changing from 2WD to 4WD and vice versa." [1] [3]
- Shifting on the move can break things: "Shifting from 2WD to 4WD (or 4WD to
  2WD) when the vehicle is in motion could cause front drive train damage." [1] [4]
- It doesn't engage the instant you press it. "The transmission shifts when the
  vehicle has rolled a short distance. Drive off slowly to allow 4WD to engage
  or disengage." A small clank is normal. [3]
- There's a **4WD indicator** in the meter, lit when 4WD is in. [1] [5]
- The 2008 to 2013 Teryx 750 uses an electric 4WD actuator on the front diff
  (Kawasaki part 16172-0014, later 16172-0019), and a 2/4WD switch
  (27010-0068). Aftermarket "manual 4WD actuator" kits are sold to replace it. [6] [7] [8]

### Front diff lock
- It's **variable**. Kawasaki's spec for the 2013 Teryx 750 FI 4x4 lists
  "Selectable four-wheel drive with Variable Front Differential Control", and
  says it "permits the rider to distribute torque equally to left and right
  front wheels for maximum traction via a hand lever located between the
  seats". [15] Reviews of the same platform describe it as letting you
  "progressively increase front differential lock". [16] The owner confirmed
  the lever on this Teryx has multiple positions.
- Normally the front diff is **limited-slip**, which "reduces steering effort
  under normal four-wheel drive operation". The lever adds lock on top. [15]
- The owner's manual names the two ends of the lever's travel: "Differential
  Mode (Unlocked-Axle)" with the lever fully forward, and "Locked-Axle Mode"
  with it "all the way rearward". [1] [9] It doesn't describe the positions in
  between, but that's the variable range. (Our first read wrongly took the two
  named ends to mean it only had two positions.)
- **Only works in 4WD**: "The differential control is effective only when 4WD
  is engaged." [9]
- To unlock it just says "after crossing the obstacle, move the shift lever
  forward". No stop is mentioned for unlocking. [9]
- **Don't lock in a turn**: "Do not shift to Locked-Axle Mode while turning or
  before entering a turn", because steering gets heavy and the Teryx can go
  where you didn't expect. [1] [4]
- Kawasaki gives no speed limit for using the lever, so Teryx OS keeps its
  15 km/h default for adding lock.

### Handbrake (parking brake)
- It's a **foot pedal** to the left of the brake pedal. Push it right down to
  set it. To release, press it slightly and pull the release lever above it. [10]
- The meter has a **red parking brake light** that comes on "when the parking
  brake is applied with the ignition switch in the ON position". [11] [12]
  So there's a parking brake switch on the stock loom we can tap into.
- From 2011 the Teryx 750 also has an ignition cutout tied to the parking
  brake [16], another sign the switch is wired into the stock loom.
- The rear brakes are an enclosed wet multi-plate type. [13]

### Stock gearbox (for reference)
- Stock it's a CVT plus an H / L / N / R sub-transmission on a lever right of
  the seat. Kawasaki says stop and idle before shifting between H, L and R. [2]
  Whether any of this is still in the Teryx after the conversion is in the
  "still to check" list.

## Shinegle kit
- Shinegle's own listings for the 7.5 kW / 72 V kit (SG-72-7.5) only cover the
  motor and controller: CAN comms, a 64-pulse motor speed sensor, and reduction
  gearbox options of 6:1 to 12:1. [14]
- We found **nothing public** about a Shinegle transfer case, 4WD, diff lock or
  a park/handbrake input. Treat all of that as unknown until we look at the
  real thing.

---

## What Teryx OS does with this

| Thing | Before | Now | Why |
|---|---|---|---|
| 2WD/4WD | changes under 5 km/h | changes only when **stopped** (under 1 km/h) | Kawasaki: stop first, shifting while moving can damage the front drive train [1] |
| Diff lock (adding lock) | under 15 km/h | under 15 km/h (unchanged) | Variable diff, so the old default stays |
| Diff lock (unlocking) | under 15 km/h | **any speed** | Kawasaki unlocks "after crossing the obstacle", and a locked diff makes steering heavy, so you want to be able to drop it before a turn [1] [9] |
| Diff lock on the dash | 0 to 100% slider with presets | same (Open, 25, 50, 75, Lock) | Kawasaki fits Variable Front Differential Control [15], and the owner confirmed it |
| Diff lock in 2WD | no hint | dash says it does nothing in 2WD | Kawasaki: diff control only works in 4WD [9] |
| Handbrake input `in.park` | optional, "TBC if fitted" | expected, from the **stock parking brake switch** | The stock meter has a parking brake light, so the switch is there [11] |

All the limits are still adjustable in Settings.

### Hardware notes (our reasoning, not from Kawasaki)
- **4WD actuator:** the stock front diff only meshes once the wheels roll
  [3], so a plain linear actuator pushing hard against it may stall
  tooth-on-tooth and trip the current limit. If the stock Kawasaki electric
  actuator is still on the front diff, the simplest fix may be to drive that
  from a relay instead of the 50 mm actuator. If the 50 mm actuator is used,
  it needs a spring in the linkage so it can preload the shift and let it snap
  in as you roll. Worth trying on the bench before deciding.
- **Diff lever:** if the lever has a catch or detent, an actuator on the
  lever or its cable needs that removed or held, or it can't unlock.

---

## Still to check on the real vehicle
1. Is the stock electric 4WD actuator still on the front diff, and is the
   dash 2WD/4WD switch still wired to it?
2. Measure the diff lever's full travel and pull force, so the 50 mm
   actuator and its pot calibration (Settings, diff pot min/max) match it.
3. What did the Shinegle kit replace? Is the stock gearbox still there with
   its front and rear outputs, or is the "transfer case" a Shinegle part? Any
   paperwork or a photo of the label would answer this.
4. Find the parking brake switch wire at the meter plug (the one that lights
   the red parking brake light) so `in.park` can tap it. Check whether it
   switches to ground or to 12 V.
5. Is the stock speed sensor still working, or does speed only come from the
   Shinegle now? The 4WD and diff rules need a reliable "stopped".

---

## Sources
1. [2011 Teryx 750 FI 4x4 LE owner's manual, p55: diff, 2WD/4WD switch, warnings](https://manualowl.com/am/Kawasaki/2011-Teryx%20750%20FI%204x4%20LE/Manual/10846?page=57)
2. [2013 Teryx 750 FI 4x4 Sport owner's manual, p51: shift levers](https://www.manualowl.com/am/Kawasaki/2013-Teryx%20750%20FI%204X4%20SPORT/Manual/10791?page=53)
3. [2012 Teryx 750 FI 4x4 LE SGE owner's manual, p78: 2WD/4WD](https://www.manualowl.com/am/Kawasaki/2012-Teryx%20750%20FI%204x4%20LE%20SGE/Manual/10765?page=80)
4. [2012 Teryx 750 FI 4x4 LE SGE owner's manual, p79: shifting the differential](https://www.manualowl.com/am/Kawasaki/2012-Teryx%20750%20FI%204x4%20LE%20SGE/Manual/10765?page=81)
5. [2011 Teryx 750 FI 4x4 LE owner's manual, p38: meter and indicator lights](https://manualowl.com/am/Kawasaki/2011-Teryx%20750%20FI%204x4%20LE/Manual/10846?page=40)
6. [Teryx 750 2008-2013 manual 4WD actuator kit, replaces 16172-0014](https://www.ebay.com/itm/297461950373)
7. [Genuine Kawasaki Teryx 750 2008-2013 actuator 16172-0019](https://mxlocker.com/product/new-2008-2013-genuine-oem-kawasaki-teryx-750-actuator-krf750-etYwH)
8. [Teryx 750 2008-2013 2/4WD switch 27010-0068](https://crossroadscycle.net/shop/2008-2013-kawasaki-teryx-750-switch-2-4wd/)
9. [2012 Teryx 750 FI 4x4 LE SGE owner's manual, p80: locked-axle mode and when stuck](https://www.manualowl.com/am/Kawasaki/2012-Teryx%20750%20FI%204x4%20LE%20SGE/Manual/10765?page=82)
10. [2012 Teryx 750 FI 4x4 LE SGE owner's manual, p58: parking brake pedal](https://www.manualowl.com/am/Kawasaki/2012-Teryx%20750%20FI%204x4%20LE%20SGE/Manual/10765?page=60)
11. [2013 Teryx 750 FI 4x4 LE owner's manual, p43: parking brake indicator light](https://www.manualowl.com/am/Kawasaki/2013-Teryx%20750%20FI%204x4%20LE/Manual/10657?page=45)
12. [2011 Teryx 750 FI 4x4 LE owner's manual, p37: multifunction meter](https://manualowl.com/am/Kawasaki/2011-Teryx%20750%20FI%204x4%20LE/Manual/10846?page=39)
13. [2011 Teryx 750 FI 4x4 LE owner's manual, p136: brakes](https://manualowl.com/am/Kawasaki/2011-Teryx%20750%20FI%204x4%20LE/Manual/10846?page=138)
14. [Shinegle 7.5 kW conversion kit for UTV/ATV (made-in-china listing)](https://www.made-in-china.com/showroom/1a6d66f17f5919e6/product-detailtvfnapzZTlYA/China-Shinegle-7-5kw-Conversion-Kit-for-UTV-ATV.html)
15. [2013 Kawasaki Teryx 750 FI 4x4, Kawasaki features and spec (totalmotorcycle)](https://www.totalmotorcycle.com/ATV-Quad/2013ATVmodels/2013-Kawasaki-Teryx750FI4x4)
16. [2011 Kawasaki Teryx 750 FI 4x4 Sport review and specs (UTV Guide)](https://utvguide.net/2011-kawasaki-teryx-750-fi-4x4-sport/)

The 2011 and 2012 manuals are used where the 2013 pages aren't online. The
Teryx 750 2WD/4WD switch, diff and parking brake are the same across these
years (the same parts fit 2008 to 2013 [6] [8]), and the 2013 pages we could
read [2] [11] match.
