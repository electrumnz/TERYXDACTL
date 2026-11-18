# RC launching: beaches first, boat ramps too

Sam's use: back the jet ski trailer into the sea by remote, either sitting on the
jet ski or standing on dry sand, so the Teryx gets wet and Sam doesn't. Mostly
beach launching, sometimes a boat ramp. This doc turns the RC idea in
[`power-steering-rc.md`](power-steering-rc.md) into a plan for that job.

Checked 18 Nov 2026. Anything marked **TBC** or **not confirmed** is not
proven yet. Sources are at the end, with notes where we only saw a page through
a search summary.

Try the remote screen on a phone: <https://electrumnz.github.io/TERYXDACTL/remote.html>
(turn it sideways; it runs a pretend Teryx on a pretend beach).

## 1. Short answer

- **It's doable, and the safety brain stays the Pico.** A new small "RC box"
  (a second Pico 2) does the driving. It only drives while it hears the remote
  every 200 ms, the main Pico says RC is allowed, and your thumb is on the drive stick
  (that's the dead-man).
  Anything else and it stops on the brake.
- **Steering:** fake the torque sensor signal into the wrecker Aqua column's own
  ECU, so the column's motor does the turning. Hard-wired relays hand steering
  back to the real sensor if the RC box stops. Plan B is a motor that turns the
  steering wheel itself.
- **Remote: your own phone.** The "Teryx Remote" app is a web page the Pi
  serves on its own Wi-Fi hotspot, so there's nothing to install and no
  internet needed at the beach. It drives with **on-screen sticks**, so there's
  nothing to buy: left thumb forward/back (pull back to brake), right thumb steer.
  Lift your left thumb off and it stops and holds. A gamepad grip is an optional
  extra if you ever want real sticks. If the Wi-Fi range or
  splashes turn out to be a problem, the same app runs on a SIYI MK15 handheld
  (splash proof, its own long-range radio). See section 4.
- **4G driving is in Settings, off by default** and needs your PIN to change.
  Meant for getting it back if it's ever pinched. Crawl speed only (2 km/h),
  cameras must be live, and it stops if the lag gets over 0.3 s. See section 4c.
- **Speeds:** 3 km/h in reverse, 5 km/h forward in RC.
- **Water:** never past the bottom of the axle caps (Kawasaki's own limit for the
  Teryx 750). Two water probes on the Teryx stop any more reverse at that line.
- **A brake actuator is a must** before RC goes near a slope. The RC box won't
  arm without one that passes its self-test.
- **Legal:** a beach is a "road" in NZ, most councils only allow vehicles on the
  beach to launch boats, and nothing we found says whether a remote-driven
  vehicle with nobody in it is OK there. Treat public beaches as a grey area
  and use it on private land first. See section 8.

## 2. How it fits together

```
 Phone (on-screen sticks) ◄ Teryx Wi-Fi hotspot (or 4G, off by default) ────► Pi 5
   (or a SIYI handheld: sticks ──own radio──► air unit ──SBUS──► RC box directly)   │ CAN
 RC box ◄──── CAN: "RC allowed" permit, 20 Hz ──── main control box (Pico 2) ◄─┘
   │
   ├─ relay ─► Aqua EPS ECU torque sensor input (TRQ1, TRQ2)   [else real sensor]
   ├─ relay ─► Shinegle throttle wiper J1-16 + throttle switch J1-9 [else the pedal]
   ├─ relay ─► Shinegle Forward J1-22 / Reverse J1-33           [else the F-N-R switch]
   ├─ brake actuator driver + its position sensor
   └─ water probes (2)
```

- **Phone:** the Pi passes stick packets from the phone onto CAN, each with a
  counter and the round trip it measured. If the phone, the Wi-Fi or the Pi
  stops, the packets stop and the RC box stops the Teryx within 200 ms. The Pi
  can pass packets on but can't make the RC box drive without fresh ones.
- **SIYI handheld (if bought later):** sticks go radio → air unit → SBUS → RC box,
  not through the Pi at all.
- Lights, 4WD, diff and camera choice go through the main Pico's normal rules,
  the same as pressing them on the dash.
- **Why a second Pico:** every pin on the main Pico 2 is already used
  ([`io-list.md`](io-list.md), and the Aqua column already needs one freed).
  A separate box also means RC can be unplugged without touching anything else,
  and the Pi's header and PCIe stay free for the AI HAT+ 2.
- **Relays fail back to normal.** Every changeover relay is wired so that when
  it's not powered, the real steering sensor, the pedal and the F-N-R switch are
  connected. The relay coils are fed through a contact the main Pico holds on
  only while RC is allowed, *and* switched by the RC box. Either Pico (or a
  blown fuse, or the RC box crashing) drops them.

## 3. Steering when the column only assists

The Aqua column's ECU turns its motor when its torque sensor says a driver is
twisting the wheel. Two ways to make it steer on its own:

| | A. Fake the torque sensor (pick) | B. A motor turns the steering wheel |
|---|---|---|
| How | RC box writes two voltages into the column ECU's torque sensor input, through a changeover relay | A geared motor with a clutch drives the wheel. The column's torque sensor feels it and adds assist like it would for a person |
| Parts | MCP4728 DAC (2 of its 4 channels), DPDT relay, AS5600 angle sensor on the shaft, ADS1115 to read the DAC back | Motor, clutch, mount, angle sensor |
| Good | Cheap, nothing to bolt on, the column's own motor is strong enough to park a car | The column never sees a fake signal, so no fault codes |
| Risks | Wrong voltages give fault codes and no assist. A stuck DAC could hold a turn (MoreTorque warns about this) | Bulky in the cab, extra cost. **Not researched or priced yet** |

**What we know about Toyota torque sensors** (Prius and RAV4 service info, so
**not confirmed for the Aqua**): two outputs, TRQ1 and TRQ2, about 2.3-2.7 V
with the wheel centred, the two within 0.3 V of each other, moving in opposite
directions under load. If they stop agreeing, the ECU stops assist and stores a
code (Prius C1511, C1512, C1513). So the RC box drives them as a mirrored pair
about the centre (`trq_volts()` in `teryx/rc_mode.py`) and reads both back. If
the read-back pair stops mirroring, the RC box drops the steering relay and
faults. **The full voltage swing is TBC**: meter the Aqua column at centre,
hard left effort and hard right effort on the bench before wiring anything.

While in RC, the column is told 16 km/h (full assist) through the CAN frames
already in `teryx/eps_toyota.py`.

## 4. The remote

Sam's wishlist: a screen with the front, rear and trailer cameras, sticks that
give a percentage (forward/back on one, steer on the other), winch in/out, lights,
F-N-R, diff lock, 2WD/4WD. Splash proof is enough.

| | Your phone, on-screen sticks (pick) | SIYI MK15 | Android gaming handheld (eg Retroid Pocket 5) |
|---|---|---|---|
| Screen | Your phone's | 5.5" 1080p touch, about 1000 nits (good in sun) | 5.5" 1080p OLED touch |
| Runs our app | Yes, in the browser, add to home screen | Yes, Android 9 | Yes, Android |
| Go/brake and steer | On-screen sticks (thumb on = drive). Optional gamepad grip | Two sticks | Two Hall sticks, analogue L2/R2 |
| Link | Teryx's own Wi-Fi hotspot. 4G optional, off by default | Own radio, 16 ch SBUS out, up to 15 km clear line | Wi-Fi |
| Video | Wi-Fi from the Pi. About 0.5 s in one Pi 5 test, needs tuning | Own link, about 180 ms | Wi-Fi from the Pi |
| Splash proof | Depends on the phone | IP53 (retailer listings) | No rating found |
| Cost | Free. Optional grip: Razer Kishi V3 NZ$167.58 at PB Tech | About £485 at a UK shop (sold out on the day), US$447-1,104 elsewhere. No NZ stockist found | About US$199-219 |

**Why the phone:** you already carry it, there's nothing to buy,
and the app updates with the rest of Teryx OS. The RC box doesn't care what the
remote is, only that fresh packets keep coming.

**Phone things to sort (TBC):**

- **HTTPS.** See 4a below. The on-screen sticks work without it, but gamepads
  need the secure page.
- **Wi-Fi range.** The Pi 5's own Wi-Fi is small. Plan on a USB Wi-Fi adaptor
  with an outside antenna up on the roll cage (or a small outdoor access
  point) and test it from a jet ski. Range over water and sand is **not measured**.
- **Video lag.** One Pi 5 test got about 0.5 s with a plain TCP stream and 1.3 s
  through MediaMTX RTSP. At 3 km/h, 0.5 s is about 40 cm. WebRTC should do
  better, **to be tested**. The speed caps are set low partly for this.

**SIYI MK15 is the fallback.** It's the only option that ticks everything at
once (screen, two proportional sticks, our app, splash proof and its own
control and video link). **Not confirmed:** its buttons and switches (for the
dead-man and e-stop), its failsafe behaviour, and which air unit suits our 12V
(one listing gives 3S-6S, 12.6-25.2 V, for the HM30 air unit).

**Over water:** 2.4 GHz range drops when antennas are low over water
(reflections), so keep the Teryx's antenna high on the roll cage and the remote
up off your lap. ExpressLRS users report more range on 900 MHz. NZ allows short
range devices in 915-928 MHz (30 dBm, per a LoRaWAN forum thread, **check the
current RSM notice**).

### 4a. iPhone and Android

Sam uses an iPhone, but the remote has to work on both. It's one web app, so
the same page runs on iPhone Safari and Android Chrome. What's done in the app:

- **Install to the home screen.** `remote.webmanifest` (full screen, landscape)
  plus Apple's home-screen tags. iPhone: Safari, Share, Add to Home Screen.
  Android: Chrome menu, Add to Home screen. The Settings panel says which you're
  in and what to do.
- **Screen stays on.** Uses the Screen Wake Lock API. Safari has it from 16.4,
  but it didn't work in home-screen apps until **iOS 18.4** (WebKit bug 254545),
  so keep the iPhone updated. If it's not there, the app says to set Auto-Lock
  to Never while launching. It takes the lock again whenever the app comes back.
- **No zoom or page dragging.** iOS ignores `user-scalable=no`, so the app
  blocks Safari's pinch (`gesturestart`), double-tap zoom, long-press menus and
  page scrolling. Notch and home-bar space is padded with `safe-area-inset`.
- **Two thumbs at once.** Each stick follows its own finger (pointer capture),
  so you can steer and drive together. Tested with two touches in a phone-sized
  browser. Palm rejection uses the touch size the browser reports. Some phones
  report a fixed size, and then palms just aren't filtered there (the sticks
  still only take one thumb each). **Test on the real phones.**
- **Gamepads on iPhone.** Safari supports the web Gamepad API, but only on the
  secure (HTTPS) page. Pads that work with iPhone: Xbox Wireless, PlayStation
  DualShock 4 and DualSense (iOS 14.5+), and "MFi" pads, all over Bluetooth.
  Clip-on grips: Backbone One USB-C works on iPhone 15 and newer, and the
  Lightning Backbone works on older iPhones. Razer Kishi V3 iPhone support
  **wasn't confirmed** (Razer lists the Kishi Ultra for USB-C iPhones). The
  webЯcade project lists Xbox Wireless, DualShock 4 and 8BitDo Lite / Zero 2
  as working in iOS Safari. Safari can't rumble the pad. **Not tested by us
  yet.** A pad only shows up after you press one of its buttons.
- **HTTPS on the Teryx's own hotspot (no internet at the beach).** The Pi makes
  its own small certificate authority (a root certificate with Basic
  Constraints, which iOS needs) and signs the page's certificate with it. Each
  phone trusts that root once:
  - iPhone: open the root on the Pi's page, install the profile in Settings,
    then turn it on under **Settings > General > About > Certificate Trust
    Settings**. Some people found that switch missing on iOS 18 after a
    phone-to-phone move, and later updates fixed it for some of them.
  - Android: Settings > Security > Encryption & credentials > Install a
    certificate > CA certificate (the menu names differ by brand).
  - Another option, **not tested**: `tailscale cert` gives the Pi a real
    certificate for its Tailscale name, and the Pi's hotspot DNS points that
    name at itself. Then no phone needs to trust anything. It renews every
    90 days, so the Pi needs internet now and then.

### 4b. A cheap phone that lives in the ATV (optional)

Sam's happy to buy a cheap phone that stays with the Teryx as its remote. It's
cheaper than any RC remote, and it means your own phone isn't the one on the
jet ski. It doesn't need a SIM: it joins the Teryx's hotspot.

| | Ulefone Armor X13 (pick) | Second-hand budget Android | Samsung Galaxy XCover7 |
|---|---|---|---|
| Rugged | IP68/IP69K, MIL-STD-810H. 1.5 m for 30 min | Usually just splash rated. Add a cheap waterproof pouch | IP68, but Samsung says not for full dunking |
| Screen | 6.52", 720x1600. Brightness not published | Varies | 6.6" |
| Battery | 6320 mAh | Varies, often tired | Swappable |
| Gamepad later | USB-C OTG, Chrome on Android | Same, if USB-C | Same |
| Speed | Slow chip (Helio G36). Fine for one camera at a time, **test it** | Varies | Better |
| Cost | About €142-152 in Europe, US$127 in the US. NZ$396 at Rugged Phones NZ. AliExpress price **not checked** (it blocks us) | Trade Me, often under NZ$150 (**not checked**) | NZ$598.99 at PB Tech |

**Pick: Ulefone Armor X13 from AliExpress**, or the Armor X12 Pro (NZ$365 at
Rugged Phones NZ) if you want it from an NZ shop. It's properly waterproof,
has a big battery and USB-C, and costs about what a decent RC remote's battery
does. A second-hand Android in a waterproof pouch is the cheapest way to try it
first. Glove or wet-finger mode isn't listed for the X13, so check that when
it arrives.

**Kiosk setup (boots straight into the remote):**

1. Join it to the Teryx's Wi-Fi only, and turn off auto updates and battery
   saving for Chrome.
2. Trust the Pi's root certificate (4a), open `https://teryx/remote.html` and
   Add to Home screen.
3. Free way: Android screen pinning (Settings > Security > App pinning), and
   pin the remote. It holds until you unpin it with the right gesture and PIN.
   Kiosk app guides say updates and gestures can still get past pinning.
4. Tighter way: **Fully Kiosk Browser** set as the home app, with the remote
   page as its start page and launch on boot. One forum user found launch on
   boot didn't fire on their tablet until they added an autostart app. Its
   kiosk features need a paid licence (price **not checked**).
5. Keep it on a USB charger in the cab so it's always full.

**Or install our Android app** (`android/`, guide in `android/README.md`). It's
the same remote page inside a small app you install from a file (the demo site
has it at `teryx-remote.apk`). It can be the phone's Home app, keeps the screen
on, does a full kiosk lock if set up with adb once, ignores the back button,
and needs no certificate setup because it serves the page to itself securely.
iPhones can't install apps from a file, so on iPhone it stays the home-screen
web app. **Built but not yet tried on a real phone.**

**Living in the glove box:**

- Charger: a 12 V USB-C socket in the glove box (`GLOVE_USB` in
  `config/wiring.yaml`), fed from the accessory relay with a 3 A fuse. It's off
  with the key off, so it can't flatten the 12 V battery. The control box could
  keep it on for a while after key-off later (TBC).
- Battery care: if the phone has a charge limit (often called "protect battery"
  or 80%), turn it on, since it sits on the charger. A closed glove box in the
  sun gets hot, and heat plus full charge is what swells phone batteries. Leave
  it out of the glove box on hot days if it feels warm, and check it now and
  then for swelling (the screen lifting or the back bulging).
- Taking it out: pulling it off the charger wakes the screen straight into the
  remote, showing READY.

### 4c. Driving over 4G (off by default)

Sam's idea: if it's ever stolen, drive it out of the thief's driveway from the
phone. It's in **Settings > Remote control > Allow driving over 4G** on the
dash, and also in the remote app's own settings, so it can be switched on over
4G when the dash is out of reach. Off by default, and turning it on or off
needs the vehicle lock PIN (checked by the control box, which counts wrong tries
the same as the lock screen).

- Plain 4G is jumpy: a 2025 study says normal 4G/LTE has too much jitter, loss
  and congestion for teleoperated driving, and drivers struggle from about
  300 ms round trip. Sub-50 ms has been shown on LTE, but only with a lot of
  tuning. So over 4G the RC box:
  - caps it at **2 km/h**,
  - stops on the brake if the measured round trip goes over **0.3 s**,
  - allows **0.5 s** between packets (4G jitter would trip 200 ms all the time;
    0.5 s at 2 km/h is 28 cm),
  - won't move unless the phone says the camera picture is live,
  - keeps the dead-man and every other rule.
- **How it connects** (from the 4G anti-theft work, `docs/remote-access.md`
  once merged): text `ONLINE <code>` to the Teryx's SIM from a listed number to
  wake its 4G data (30 min by default, `OFF <code>` drops it). The phone and the
  Pi are both on Sam's Tailscale tailnet, and the Pi is at `http://teryx:8080`.
  Being on the tailnet is the device check; the PIN for `rc.allow4g` sits on
  top. The remote app can open a ready-filled `sms:` link for the wake text.
- **The 4G module has to give real data speed.** On a board wired only to the
  Pi's UART, 4G data is PPP at roughly 11-90 KB/s: fine for texts, far too slow
  for live video. So RC over 4G needs the module's own USB wired to the Pi (not a
  USB-serial chip), or a USB 4G stick. On a UART-only setup the link endpoint
  answers "texts only", the link never shows as up, and RC over 4G refuses on its
  own. See "Which 4G module" in `docs/remote-access.md`.
- **RC over 4G also refuses unless the 4G link is up** (`GET /api/remote/link`
  says `up`), and the app keeps the link alive while driving
  (`POST /api/remote/link` with `minutes`) so it can't drop mid-drive. To be
  wired up once both PRs are in.
- **For now the flag lives on the Pi** (`rc.allow4g` in the dash settings). When
  the RC box is built, the flag moves into the RC box so a Pi that's been
  tampered with can't turn it on.
- **Legal and safety, plainly:** NZ Police say don't go after a vehicle you think
  is stolen, and to call 111 if it's being driven or the people are nearby.
  Driving it away by remote on a road, unseen, with no one in it, is not
  something we found any rule allowing. Treat 4G driving as a last resort,
  tell the police first, and expect to be treated as the driver of a vehicle on
  a road. Location (GPS) and the lock are the safer tools here.

### The "Teryx Remote" app (mini OS)

Built as `dash/web/remote.html` in the same Predator / Fossil / Night Hunt
looks as the dash (it swaps look when 4WD, diff or lights are on). On
github.io it drives a pretend Teryx.

- Middle: live camera, Rear / Trailer / Front tabs, guide lines that bend with
  the steering, speed with the RC cap under it.
- Left: Arm RC, F-N-R, 2WD/4WD, diff lock %, lights.
- Right: big STOP, winch in, winch out (hold-to-run).
- Over the camera: two big on-screen sticks. Left is forward/back (pull back to
  brake), right is steer. Your thumb on the left stick is the dead-man: lift it
  and the Teryx stops and holds on the brake. To arm, your thumb has to be off
  the stick first.
- Wet fingers and palms: the sticks are big (about 120 x 190 px and 220 x 120 px)
  and the whole stick area grabs your thumb, so you don't have to hit the knob.
  A touch bigger than about 70 px (a palm or the side of your hand) is ignored,
  and each stick only follows the first thumb that lands on it.
- Bottom: brake %, steering, go %.
- Warnings in the middle: signal lost, let go of the stick, water at the limit,
  digging in, stuck.
- Optional gamepad (phone grip or handheld). Two clean layouts, swapped on
  their own:
  - **Touch (no gamepad):** sticks over the camera, winch in/out on the right.
  - **Gamepad plugged in:** anything the pad does leaves the screen (both sticks
    and the winch buttons), the right column slims down and the camera gets the
    room. A small panel shows the pad layout and lights up green while L1 (the
    dead-man) is held. Left stick Y forward/back, right stick X steer, R2 go,
    L2 brake, L1 dead-man, A winch in, B winch out. STOP, F-N-R, 2WD/4WD, diff
    and lights stay on screen.
  - **Gamepad unplugged or flat:** the Teryx stops and holds straight away, the
    on-screen sticks come back, and driving again needs your thumb on the stick
    and the stick centred. Plugging a pad in while armed also stops and holds
    until L1 is held with the stick centred.
  - Keyboard (for testing): W/S, A/D, Space, I/O.

On the real remote the app shows what the RC box reports; it doesn't make the
safety calls itself.

### 4d. A gamepad paired straight to the Pi (no phone)

For close-range jobs, like hitching up or lining up the trailer, an Xbox or
8BitDo style Bluetooth pad can pair straight to the Pi and drive with no phone
at all. It goes through exactly the same RC box rules (link "bt",
`teryx/rc_pad.py`). If Bluetooth drops, the packets stop and the Teryx stops
and holds. When Linux reports the pad gone, a failsafe goes out straight away.
There's no screen in your hand, so the **dash screen shows the RC banner**:
who's driving, ready/driving/holding, the gear, the speed cap and why it
stopped.

| Pad | Does |
|---|---|
| LB (L1) held | Dead-man. Let go and it stops and holds |
| Left stick up / down | Go forward / back, pull against the way you're moving to brake. F-N-R follows the stick (stop and re-centre to swap) |
| RT / LT | Go / brake, if you'd rather use triggers |
| Right stick left / right | Steer |
| A held / B held | Winch in / out (only stopped, neutral, off the throttle) |
| D-pad up / down | Lights / 2WD-4WD |
| D-pad left / right | Diff lock down / up 25 % |
| Start held 1 s | RC on / off. Needs LB let go and the sticks centred |
| Select (View) | E-stop. Stays on until RC is turned off and on again |

Lights, 4WD and diff go to the control box as normal dash buttons, with the same
rules. Bluetooth range is short (not measured, our guess is tens of metres
at best and less over water), so this is for close work. Use the phone for launching. **Not tested
with a real pad yet.** The Pi needs `pip install evdev` (BSD licence).

## 5. RC rules (the RC box)

Written as code in `teryx/rc_mode.py` with tests in `tests/test_rc_mode.py`. The
RC box firmware has to match.

**Arming** (Arm RC on the remote, after RC is switched on on the dash):
parked with the park brake on, vehicle unlocked, brake actuator fitted and
self-tested, radio and main Pico both heard in the last 200 ms, stick or
triggers at zero, F-N-R in neutral, and the dead-man **not** held (so a stuck
button can't drive off).

**Stops on the brake straight away** (throttle 0, neutral, brake 100%):

| Cause | Why |
|---|---|
| No radio packet for 200 ms, or the receiver flags failsafe | ExpressLRS itself takes up to about 1 s to failsafe. 200 ms at 3 km/h is 17 cm |
| No "RC allowed" from the main Pico for 200 ms, or it says no (locked, key off, fault) | The main Pico stays the boss |
| Dead-man let go | |
| E-stop on the remote | |
| Brake actuator fault | |
| Wheelspin: wheels at 3 km/h or more, GPS says under 0.5 km/h, for 1.5 s | Digging into soft sand. Stop before it buries itself. Try 4WD and diff lock |
| Stuck: half throttle or more, nothing moving, 3 s | Bogged or hard against something |
| Steering read-back wrong | Also drops the steering relay, needs a re-arm from the dash |

After a stop the stick or trigger has to go back to zero before it drives again.

**While driving:** reverse 3 km/h, forward 5 km/h (Auckland Council asks for 10
km/h or less when launching, RC goes slower). Throttle cuts at the cap, brake
comes in at 1.5 km/h over. Direction only changes when stopped. The brake
trigger always beats the go trigger. Standing still with no throttle, it holds
on the brake (slope, waves pushing). Steering still works while held, to line
up the trailer.

**Water:** once the low probe is wet, no more reverse (forward still works). The
high probe gives "TOO DEEP".

**Winch from the remote:** hold-to-run in and out, only when stopped, in neutral
and off the throttle. The RC box passes it on to the main Pico, so all the
existing winch rules still apply (arming, 100 ms gap between in and out, 2 minute
idle disarm, heat guess, timed pull). Let go, lose signal or let go of the
dead-man and it stops. **The XBull handheld can go**; keep the two hidden
hard-wired toggles as the backup.

**4WD and diff lock** from the remote go to the main Pico like the dash
buttons do, with the same rules: 4WD only when stopped, adding diff lock only
under 15 km/h, waiting if it's a bit fast ([`drive-changes.md`](drive-changes.md)).
Arming RC is a good moment to put 4WD and some diff lock on for sand, since
you're stopped anyway.

## 6. Brake and holding still

Cutting drive doesn't hold a trailer and jet ski on a wet slope. The plan in
[`power-steering-rc.md`](power-steering-rc.md) section 5 still stands: a pedal
actuator (still to be chosen once the pedal force is measured), regen if the
Shinegle brake input works out, and ideally a spring-applied brake so a total
power loss still brakes. The RC box won't arm without a working brake actuator.
**Hill hold on the Shinegle: not found** (the SG1810 "Slope" parameter is listed
as reserved).

## 7. Water, salt and the HV system

- **Depth:** Kawasaki says never run the Teryx 750 "in water deeper than the bottom
  edge of the axle caps" or in fast-flowing water. That's for the petrol Teryx,
  but the axles, diffs and hubs are the same, so it's our limit too. **Where the
  battery pack, motor and Shinegle sit relative to that line is TBC**: measure
  the lowest point of each.
- **Probes:** two stainless probes on the rear, one at axle-cap-bottom height and
  one a bit higher, into the RC box. Salt water conducts, so a wet probe is easy
  to see. Exact heights TBC once the low points are measured.
- **Waves:** a wave lifts the water line for a moment. The RC box only stops
  reverse at the probe, it doesn't drive forward on its own; you pull forward.
- **Shinegle controller:** IP65 per its manual. That means water jets, **not**
  dunking, so it has to stay above the water line. The motor and battery pack IP
  ratings are **not known**: ask Shinegle.
- **After salt:** rinse with fresh water at low pressure, keep a pressure washer
  wand well back (one guide says 600 mm) from looms and fuse blocks. Dielectric
  grease on 12V plugs (it doesn't conduct, don't over-pack so they won't latch).
  Heat-shrink butt splices, not plain nylon. **Don't grease HV plugs or their
  interlock pins unless Shinegle says to.**
- **Brakes:** Kawasaki says to use the brakes after water so the linings dry, and
  check them more often if it's used in water.
- Kawasaki's CVT warning doesn't apply: the EV has no CVT.

## 8. NZ rules

- **A beach is a road.** NZTA says the Land Transport Act's "road" includes a
  beach, so road rules, rego and WoF apply there. Police have said the same about
  beaches with public vehicle access.
- **Councils decide where you can drive on a beach.** Most only allow it to launch
  or retrieve a boat. Auckland: launching allowed with a recommended 10 km/h or
  less, and move the vehicle off straight after. Kāpiti: 10 km/h in accessways,
  20 km/h on the beach (council pages don't fully agree). Horowhenua: 30 km/h.
  Check the bylaw for each beach.
- **Remote driving with nobody in it: not clear.** The Ministry of Transport says
  NZ law doesn't require a driver to be inside for a vehicle to be operated on a
  road (seen through a search summary, the page wouldn't load for us). NZTA also
  says most rules "strongly imply" a vehicle in operation has a driver. There's
  no rule we found that covers a person driving by remote from outside. Whoever
  holds the remote should expect to be treated as the driver.
- **Leaving it running unattended:** we couldn't confirm the exact NZ rule.
  Don't leave it armed with nobody holding the remote.
- **On the jet ski:** Maritime Rule 91.6, 5 knots within 200 m of shore, which you
  will be when you're launching.
- **Radio:** 2.4 GHz and 915-928 MHz are licence-free short range bands in NZ.
  Power limits for 915-928 MHz are 30 dBm (36 dBm for 920-928) per a forum
  summary. **Check the current RSM notice** before using a 1 W module.

**Our advice:** get it working on private land. On a public beach, have a
second person near the Teryx the first few times, use it only at the launching
spot, and ask the council if in doubt.

## 9. Parts for the RC box (rough)

| Part | Note |
|---|---|
| Pico 2 + MCP2515 | Second box on the main Teryx CAN bus |
| MCP4728 DAC | TRQ1, TRQ2, throttle wiper, 1 spare |
| ADS1115 | Read back TRQ1, TRQ2, throttle, brake actuator position |
| Relays | DPDT steering changeover, throttle wiper + switch changeover, F and R, brake actuator enable |
| BTS7960 | Brake actuator driver |
| AS5600 | Steering shaft angle |
| 2 stainless probes | Water |
| Remote | Your phone (on-screen sticks, free), iPhone or Android. Optional: a cheap rugged phone that lives in the ATV (Ulefone Armor X13, see 4b), a gamepad, or a SIYI MK15 |
| Wi-Fi | USB Wi-Fi adaptor with an outside antenna, or a small outdoor access point (TBC) |
| Brake actuator | Not chosen, needs pedal measurements |

Proposed new CAN frames (**not in `teryx.dbc` yet**): Pi → RC box arm/disarm,
main Pico → RC box "RC allowed" permit at 20 Hz, RC box → all status (state,
reason, throttle, brake, direction, link age).

## 10. Next steps

1. Bench: meter the Aqua column's torque sensor (centre, left, right) and its plug.
2. Measure the lowest point of the battery pack, motor and Shinegle against the
   axle caps.
3. Measure brake pedal force and travel, choose the brake actuator.
4. Meter the Shinegle throttle wiper (J1-16) range and what F/R (J1-22, J1-33)
   expect.
5. Try the app on your iPhone now (Add to Home Screen, iOS 18.4 or later), with wet hands too. A gamepad is optional, only if the on-screen sticks don't feel right.
6. Build the RC box on the bench with the sim, then on the Teryx up on stands.
7. Ask Shinegle for the motor and battery IP ratings.

## Sources

- Kawasaki Teryx 750 FI 4x4 owner's manual (2012, page 101) and 2014 Teryx manual (page 97) via ManualOwl, water depth, brakes and CVT. Text seen through a search summary; the pages blocked direct loading: https://www.manualowl.com/am/Kawasaki/2012-Teryx%20750%20FI%204x4/Manual/10558?page=101
- Toyota EPS torque sensor checks (TRQ1 2.3-2.7 V at centre, TRQ1/TRQ2 within 0.3 V), 2004 Prius repair manual DTC C1511: https://share.qclt.com/%E4%B8%B0%E7%94%B0%E6%99%AE%E7%91%9E%E6%96%AF%E5%8E%9F%E5%8E%82%E8%8B%B1%E6%96%87%E6%89%8B%E5%86%8CPDF%E6%A0%BC%E5%BC%8F/Repair%20Manual/04pruisr/05/21bvv/cic1511.pdf and TOYOTAtech guide: https://automotivetechinfo.com/wp-content/uploads/2020/10/Understanding-Toyota-Electronic-Power-Steering-EPS.pdf
- MoreTorque, torque interceptor risks (stuck DAC): https://moretorques-organization.gitbook.io/torque-interceptor-2/risks
- comma.ai, Safer control of steering: https://blog.comma.ai/safer-control-of-steering/
- SIYI MK15 specs (IP53, 5.5" 1080p, Android 9, 180 ms, 15 km, SBUS/PWM/UART/LAN, air unit voltages, £484.95): https://www.unmannedtechshop.co.uk/products/siyi-mk15-mini-hd-handheld-ground-control-station ; price range: https://shop.siyi.biz/search/?Sort=7d
- SIYI MK32 (IP4X, for comparison): https://siyi.biz/en/product/hand-gcs/mk32/spec/
- Retroid Pocket 5 vs AYN Odin 2 (prices, sticks, triggers): https://handheldindex.pages.dev/comparisons/ayn-odin-2-vs-retroid-pocket-5/ and https://evezone.evetech.co.za/deep-dives/retroid-pocket-5-vs-ayn-odin-2-the-android-emulation-flagship-showdown
- RadioMaster MT12 at KiwiQuads (NZ$253.99): https://kiwiquads.co.nz/product/radiomaster-mt12-surface-radio-4in1-expresslrs ; controls: https://radiomasterrc.com/products/mt12-surface-radio-controller
- Samsung Galaxy XCover7 at PB Tech (NZ$598.99, IP68, not for full submersion): https://www.pbtech.co.nz/product/MPHSAM055600/Samsung-Galaxy-Xcover-7-5G-2024-Rugged-Dual-SIM-Sm
- Pi 5 camera stream latency (about 0.5 s TCP, 1.3 s via MediaMTX RTSP, one test): https://www.hackster.io/eugene-tkachenko/comparing-video-stream-latencies-raspberry-pi-5-camera-v3-6c0ee4
- ExpressLRS failsafe timing: https://expresslrs.org/hardware/pwm-receivers/ ; signal health and line of sight: https://expresslrs.org/info/signal-health/
- 2.4 GHz over water (forum reports): https://discuss.ardupilot.org/t/2-4ghz-frsky-expected-range/98808
- NZ 915-928 MHz limits (forum summary of the NZ rules): https://www.thethingsnetwork.org/forum/t/frequency-plan-new-zealand/6846
- NZTA, what is a road: https://www.nzta.govt.nz/resources/what-is-a-road/what-is-a-road.html
- Ministry of Transport, current regulatory settings for autonomous vehicles (page didn't load for us, seen via search): https://www.transport.govt.nz/about-us/what-we-do/queries/current-regulatory-settings-for-autonomous-vehicles
- Auckland Council, rules for driving on beaches: https://aucklandcouncil.govt.nz/licences-regulations/driving-on-beaches/Pages/rules-driving-beaches.aspx and 2025 controls: https://www.aucklandcouncil.govt.nz/plans-projects-policies-reports-bylaws/Documents/vehicle-use-and-parking-on-beaches-bylaw-controls-2025.pdf
- Kāpiti Coast, vehicles on the beach: https://www.kapiticoast.govt.nz/our-district/beaches/vehicles-on-the-beach
- Horowhenua, police on beach road rules: https://www.nzherald.co.nz/horowhenua-chronicle/news/police-remind-horowhenua-drivers-the-beach-has-road-rules/A3SV2OA7DG2FKQVA4ADEM5HNEY/
- Waikato Regional Council, 5 knot rule: https://waikatoregion.govt.nz/services/maritime-services/the-5-knot-rule
- 4G and teleoperation latency: https://arxiv.org/html/2503.14186v1 (5G study, 4G jitter), https://arxiv.org/pdf/2209.09794 (sub-50 ms on LTE), https://www.frontiersin.org/articles/10.3389/ffutr.2021.801567/full (300 ms)
- NZ Police, stolen vehicles (don't pursue, call 111): https://www.police.govt.nz/can-you-help-us/stolen-vehicles
- MDN, getGamepads() needs a secure context: https://developer.mozilla.org/en-US/docs/Web/API/Navigator/getGamepads
- Wake Lock in iOS home-screen apps (WebKit bug 254545, fixed in iOS 18.4): https://bugs.webkit.org/show_bug.cgi?id=254545 and https://progressier.com/pwa-capabilities/screen-wake-lock ; Safari 16.4 support: https://developer.chrome.com/docs/capabilities/web-apis/wake-lock
- Apple, trusting a root certificate (Certificate Trust Settings): https://support.apple.com/en-gw/guide/deployment/depb5eff8914/web ; Basic Constraints needed and iOS 18 missing-toggle reports: https://developer.apple.com/forums/thread/764673
- iPhone support for DualSense and Xbox Series pads (iOS 14.5): https://www.gamesradar.com/iphone-finally-gets-ps5-and-xbox-series-x-controller-support ; pads tested in iOS Safari: https://docs.webrcade.com/platforms/ios/gamepads/
- Backbone One USB-C on iPhone 15: https://www.engadget.com/the-backbone-one-android-controller-now-supports-iphone-15-190059914.html ; Kishi Ultra for USB-C iPhones: https://imore.com/iphone/iphone-accessories/razer-kishi-ultra-controller-vs-backbone-one-battle-of-the-extendable-iphone-gamepads
- Ulefone Armor X13 specs: https://m.gsmarena.com/ulefone_armor_x13-12475.php , https://smartprix.com/mobiles/ulefone-armor-x13-ppd14y4ftqd8 ; EU prices: https://aio.lv/en/product--ulefone-uf-ax13bk--11204123.md , https://arvutitark.ee/en/smart-devices/phones/nutitelefon-ulefone-armor-x13-664gb-must-1360683 ; NZ prices: https://ruggedphones.co.nz/product-category/rugged-android-phones/
- Android kiosk: screen pinning vs kiosk app: https://help.virtualfrontdesk.com/en/article/android-tablets-chrome-in-full-screen-and-kiosk-mode-pinned-app ; Fully Kiosk launch on boot: https://community.home-assistant.io/t/fully-kiosk-not-launching-at-boot-on-my-android-tablet/1021331
- PB Tech: Razer Kishi V3 https://www.pbtech.co.nz/product/JOYRAZ112682 , Backbone One Gen2 https://www.pbtech.co.nz/product/JOYBBN1006/BACKBONE-One-Classic-Gaming-Controller-Gen2-USB-C
- Salt and connectors (dielectric grease, splices, washer distance): https://buywitchdoctors.com/blogs/news/ultimate-guide-on-how-to-protect-utv-atv-electronics-from-water-damage
- Shinegle controller IP65 and J1 pins: [`shinegle-controller.md`](shinegle-controller.md)
