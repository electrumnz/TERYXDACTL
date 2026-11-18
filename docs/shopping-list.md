# Shopping list and which dash computer to buy

> **Changed 18 November 2026 (evening): buy the Pi 5 8GB, and leave the AI HAT+ 2 for later.**
> Sam isn't sold on the HAT yet, so it's moved to section 4c ("Later"). Every design still
> leaves room for it: the Pi box stays 56 mm tall, the PCIe slot and the HAT's header stay
> free, and the Pololu regulator has the spare power. The CarPlay dongle (Carlinkit CCPA) is
> now on the list (from AliExpress), plus an AliExpress cart (amp, fuse block, fan, H-bridges,
> phone gamepad grip), a 20-way fuse block for the 16 planned fuses, a 4th CAN board for the power steering column, and the 4G modem and
> video SSD as "later". **The list for buying tomorrow (19 Nov), by shop with SKUs and a
> total, is [`pbtech-order.md`](pbtech-order.md).** Cameras have their own write-up in
> [`cameras.md`](cameras.md).

Prices checked live on **17 November 2026** (NZ time), incl GST unless it says otherwise.
Prices added on 18 November came from search results because PB Tech's pages wouldn't open
for me; those say so. Check them before you buy.
Every price has a link. Where I couldn't check a price, it says **not verified** and gives
no number. Prices move a lot right now because of the RAM shortage (see below), so check
the link before you buy.

You own the screen (10.1" 1280x800, HDMI + USB touch). Everything else on this list is
still to buy. [`io-list.md`](io-list.md) lists some things as "on hand" (relay board,
one BTS7960, ADS1115, actuators, camera, lights, winch, a buck): those are in
section 5 below, so tick off whatever you really do have.

## 1. Short answer

**Buy a Raspberry Pi 5 8GB with the Active Cooler. The AI HAT+ 2 can come later** (section 4c).

- It needs **no code changes**, draws the least power of the options, and fits the plan.
- If it goes in later, the AI HAT+ 2 runs the camera AI and a small local language model for the voice assistant,
  using its **own 8GB of memory** ([Raspberry Pi](https://www.raspberrypi.com/products/ai-hat-plus-2/)).
  The older AI HAT+ is about as good for cameras alone but can't run a language model
  ([Raspberry Pi](https://www.raspberrypi.com/news/introducing-the-raspberry-pi-ai-hat-plus-2-generative-ai-on-raspberry-pi/),
  [Core Electronics](https://core-electronics.com.au/guides/raspberry-pi/raspberry-pi-ai-hat-1-vs-ai-hat-2-which-should-you-buy/)).
- 8GB rather than 4GB: see the budget below. 4GB would most likely cope, but with only about
  1 GB spare. 8GB leaves about 5 GB for whatever comes next, for about NZ$139 more.
- An N100/N150 mini PC or a rugged tablet still aren't worth it (section 3).

### Memory budget with everything on

| | MB | Where the number comes from |
|---|---|---|
| Raspberry Pi OS desktop | ~330 | Measured / Raspberry Pi magazine (section 2) |
| Chromium: dash with CarPlay video | ~800 | Measured (section 2) |
| Python dash server | ~52 | Measured |
| 2-3 camera feeds and the camera AI pipeline on the Pi side | 300-500 | **Guess**, not measured. The AI models themselves sit in the HAT's own 8GB |
| Speech to text on the Pi (whisper.cpp tiny to small) | ~270-850 | [whisper.cpp](https://github.com/ggerganov/whisper.cpp) memory table. Could move to the HAT later |
| PipeWire, BlueZ, ffmpeg, updates | ~200 | Allowance (section 2) |
| **Total** | **~2.0-2.7 GB** | |

So: 4GB leaves about 1.3-2 GB, 8GB leaves about 5.3-6 GB.

### Rough cost (dash computer, section 4 and 4a)

About **NZ$590** for the Pi 5 8GB, Active Cooler, HDMI adaptor, 128GB card, CAN module, lid fan
and front camera, plus about **NZ$115** for proper 12V protection and a good 5V regulator, and
about **NZ$118-180** for the CarPlay dongle. The control box (section 6) is extra. The AI HAT+ 2
would add about NZ$360-425 later.

## 2. Is 4GB enough? Measured, not guessed

### What the dash computer actually runs

From the repo:

| Thing | Where | Notes |
|---|---|---|
| Chromium in kiosk mode, one page | `dash/deploy/kiosk.sh` | The whole dash UI, 1280x800 |
| Python dash server (aiohttp) | `dash/deploy/teryx-dash.service` | CAN gateway, settings, OTA, media, camera |
| CarPlay / Android Auto | `dash/web/lib/node-carplay.js`, [`audio.md`](audio.md) | Carlinkit adapter over WebUSB, H.264 video decoded in the page with WebCodecs |
| Reverse camera | `dash/web/js/screens/camera.js` | USB camera opened by Chromium (ffmpeg MJPEG fallback) |
| PipeWire + BlueZ | `scripts/audio-setup.sh` | Bluetooth phone audio, output to USB DAC or I2S HAT |
| CAN | `scripts/pi-setup.sh` | MCP2515 HAT on SPI, SocketCAN `can0` |
| picotool, can-utils, ffmpeg | `scripts/pi-setup.sh` | Flashing the Pico, radio pass-through |

### My measurement

I ran the real dash (`python -m teryx run --scenario trail`) and measured Chromium with
[`tools/measure-dash-ram.js`](../tools/measure-dash-ram.js), which is now in the repo so
you can run it again on the real Pi. It adds up PSS (the fair share of memory) across all
of Chromium's processes:

| Step | Chromium memory (PSS) |
|---|---|
| Drive screen, sim running, after 15 s | 267 MB |
| After opening every screen | 292 MB |
| Reverse camera open (fake camera) | 297 MB |
| After 20 s of 1280x720 30 fps H.264 decoded and drawn with WebCodecs (what CarPlay does) | 757 MB |
| Python dash server | 52 MB |

Two runs gave nearly the same numbers (264/290/294/798 MB the first time).

**Be honest about the limits of this:** it ran on an x86 Linux box in the cloud with
Playwright's Chromium in headless mode and software graphics, not on a Pi. On a real Pi
the GPU does the drawing, so the numbers will differ a bit. They're the right size though,
and the script will give you the exact Pi numbers once you have one.

### Adding it up for a Pi 5

| | MB |
|---|---|
| Raspberry Pi OS desktop. The Pi's own magazine says the desktop takes about a third of a 1 GB Pi and headless uses 266 MB ([source](https://magazine.raspberrypi.com/articles/make-your-ram-go-further-raspberry-pi-os-memory-optimisation-tips)) | ~330 |
| Chromium with CarPlay running (measured, worst case) | ~760-800 |
| Dash server (measured) | ~52 |
| PipeWire, BlueZ, ffmpeg for radio, picotool during an update: not measured, small | allow 200 |
| **Total, worst case** | **about 1.4 GB** |

So a **4GB** Pi has more than 2.5 GB spare. A **2GB** Pi would probably cope but leaves
little room for an OTA update running in the background. For comparison, Tom's Hardware
found Chromium used 1.3 GB with 5 tabs and 1.7 GB with 10 tabs on a 2GB Pi 5, and said
4GB is enough for about 99% of projects
([source](https://tomshardware.com/raspberry-pi/raspberry-pi-5s-new-2gb-model-benchmarked-do-you-need-2-4-or-8gb-we-test-against-the-4-and-8gb-versions)).
The dash is one tab.

### The one real weak spot: CarPlay video

The Pi 5 has **no H.264 hardware decoder**. Its only hardware video decoder is HEVC
(H.265) ([Armbian forum](https://forum.armbian.com/topic/59022-raspberry-pi-5-missing-video-decode-hardware-acceleration-in-chromium/),
and our own [`audio.md`](audio.md) says the same). CarPlay sends H.264, so the Pi's CPU
decodes it. More RAM doesn't change that at all; 8GB decodes exactly the same. I couldn't
measure CPU use without a Pi, and I didn't find a trustworthy published figure for this
exact case, so **this is the first thing to test on the bench**. If it stutters, the fix is
to ask the adapter for a smaller picture (node-CarPlay lets you set the size and frame rate),
not a bigger Pi.

## 3. Comparing the options

| | Pi 5 4GB | Pi 5 8GB | N150 mini PC (MINIX Z150-0dB) | RK3588 board (Rock 5C, Orange Pi 5) | Rugged tablet |
|---|---|---|---|---|---|
| **Price NZ** | [NZ$232.69](https://www.pbtech.co.nz/product/SEVRBP0501/Raspberry-Pi-5-4GB-LPDDR4-24GHz-Quad-Core-ARM-Cort) PB Tech, on order (ships about 11 Jan) | [NZ$371.39](https://www.pbtech.co.nz/product/SEVRBP0502/Raspberry-Pi-5-8GB-LPDDR4-24GHz-Quad-Core-ARM-Cort) PB Tech, on order (ships about 30 Nov) | [NZ$509.29](https://www.pbtech.co.nz/product/IPCMNXZ15002/MINIX-Fanless-MiniPC-Z150-0dB-Intel-N150-8G256GB-W) PB Tech, 8GB/256GB, 5+ at Head Office | No NZ stock found. Rock 5C 8GB is [US$209.95 and sold out](https://ameridroid.com/products/radxa-rock-5c-8gb) at Ameridroid | Cheapest found: ONERUGGED M10J [NZ$2,254](https://www.pbtech.co.nz/product/POSORGM10J01) |
| **RAM for this job** | Plenty (section 2) | More than plenty | Plenty | Plenty | Plenty |
| **Power in** | 5V only, needs a 12V to 5V regulator | Same | **12V DC in** (12V/3A on the PB Tech listing) | 5V or 12V depending on board | Own battery + charger |
| **Power draw** | 1.8 W idle at the wall ([Jeff Geerling](https://www.jeffgeerling.com/blog/2023/answering-some-questions-about-raspberry-pi-5/)); 4.8 W idle, 6.5 W typical load, 11.6 W flat out ([bret.dk](https://bret.dk/how-to-power-the-raspberry-pi-5-a-complete-guide)) | About the same | MINIX doesn't publish a figure. A fanless N100 box measured 10.5-12 W idle, 22-23 W flat out ([ServeTheHome](https://servethehome.com/fanless-intel-n100-firewall-and-virtualization-appliance-review/4)) | Not checked | Not checked |
| **Heat in a sealed box** | Hard throttles at 85°C. With no cooler it hit 83°C in 30 s of full load; with the Active Cooler it peaked at 71°C over 2 min ([Raspberry Pi white paper](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010139-WP-1-Use-case-specific%20thermal%20performance%20of%20Raspberry%20Pi%20SBCs.pdf)). Our Pi box already has a 30 mm fan and cowl | Same | Fanless, so the case is the heatsink. Two to three times the heat of a Pi, and it won't fit the Pi box | Hotter than a Pi 5 under load (8 cores) | Built for it |
| **CAN** | Waveshare HAT on the header, `can0`, working today | Same | No GPIO. Use the spare Pico 2 + MCP2515 running our `firmware/can-sniffer` as a USB CAN adaptor (bridge GP15 to GND so it can send). The code already accepts `slcan:/dev/ttyACM0@250000` | HATs may work, overlays differ by board | USB CAN adaptor, Windows or Android driver |
| **CarPlay video** | Software H.264 (see above) | Same | Intel has H.264 hardware decode, but Chromium on Linux only uses it with VA-API turned on. Not tested with our stack | Has H.264 hardware decode, but Chromium only uses it with the vendor kernel and an extra PPA ([Armbian forum](https://forum.armbian.com/topic/61548-how-to-hardware-video-decode-in-google-chrome-firefox-on-rk3588-orange-pi-5b-ubuntu-rockchip-bsp/)) | Depends |
| **Boot time** | **Not verified.** I couldn't find a measured figure I'd trust. Measure it with `systemd-analyze` on the bench | Same | Not verified. Has a BIOS step a Pi doesn't | Not verified | Usually sleeps instead |
| **Code changes needed** | **None** | **None** | New setup script (no `config.txt`, no `raspi-config`), service file uses `slcan:` instead of `socketcan:can0`, USB DAC only (no I2S HAT), BIOS set to power on when power comes back, new printed box | New setup script and CAN overlay, check the header pinout, fiddle with Chromium video decode | Big: audio (PipeWire, BlueZ), setup and OTA are all Linux-only. And you'd be paying for a second screen |

### Why the Pi 5 wins here

- It's the only one that runs today with no changes, in a box that's already designed.
- It draws the least from the 12V system, which matters when the 12V battery is also
  feeding a winch.
- The mini PC's one real advantage is H.264 hardware decode for CarPlay, and that's not
  proven with Chromium on Linux either. Test the Pi first; if CarPlay can't be made smooth
  at a lower resolution, the mini PC is the fallback and the CAN side already works with it.

### Why everything costs so much right now

Raspberry Pi has put prices up more than once in 2026 because of the memory shortage. On
2 February 2026 the 4GB went up US$15 and the 8GB US$30
([Raspberry Pi](https://raspberrypi.com/news/more-memory-driven-price-rises)). Mini PCs
have gone the same way: GMKtec's N150 G3 Plus is US$329.99 on their own site with
"price increase coming soon", and sold out
([GMKtec](https://www.gmktec.com/products/nucbox-g3-plus-enhanced-performance-mini-pc-with-intel-n150-processor)).
The more RAM, the bigger the jump, which is another reason 4GB is the sweet spot.

## 4. Dash computer parts (Pi 5 8GB)

| Part | Why | Where | Price | Notes |
|---|---|---|---|---|
| Raspberry Pi 5 **8GB** | The dash | [PB Tech](https://www.pbtech.co.nz/product/SEVRBP0502/Raspberry-Pi-5-8GB-LPDDR4-24GHz-Quad-Core-ARM-Cort) | NZ$371.39 | Checked 17 Nov: on order, ships about 30 Nov. A search result on 18 Nov showed NZ$254.15, which may be an old cached price, so check. The 16GB is about [NZ$644](https://www.pbtech.co.nz/product/SEVRBP0505/Raspberry-Pi-5-16GB-LPDDR4-24GHz-Quad-Core-ARM-Cor) (search result), not needed |
| Raspberry Pi Active Cooler | Keeps the Pi under 85°C in a closed box | [PB Tech](https://www.pbtech.co.nz/product/SEVRBP0531) | NZ$11.21 | In stock (17 Nov). **Still needed without the AI HAT**: CarPlay video is decoded on the CPU the whole time it runs, which is a long steady load, and Raspberry Pi say a long heavy load throttles a bare Pi 5 ([Raspberry Pi](https://www.raspberrypi.com/news/heating-and-cooling-raspberry-pi-5/)). It's also what goes under the HAT later: with the AI HAT+ 2 on top, Raspberry Pi say fit the Active Cooler on the Pi and the HAT's heatsink on the AI chip ([Raspberry Pi docs](https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html)). Keep the passive one for the bench. Don't take the Active Cooler off once fitted, the push pins and pads don't like it |
| Micro HDMI to HDMI cable | Pi to screen | [PB Tech, Raspberry Pi official 1 m SEVRBP0207](https://www.pbtech.co.nz/product/SEVRBP0207/Raspberry-Pi-Official-1M-White-Cable-Micro-HDMI-to) | NZ$11.80 (search result) | For the bench. In the car it may need to be longer: the 2 m [Vention](https://www.pbtech.co.nz/product/VNT1306/Vention-VAA-D03-B200-Micro-HDMI-Cable---2m---Black) (NZ$12.41) has no stock, ships about 28 Jan. In stock now: [Jaycar micro HDMI adaptor](https://jaycar.co.nz/micro-hdmi-plug-to-hdmi-socket-adaptor/p/PA3649) NZ$20.90 plus an HDMI cable |
| microSD card **128GB A2** | OS, apps, logs | [PB Tech, official Raspberry Pi card](https://www.pbtech.co.nz/product/SEVRBP0538/Raspberry-Pi-Official-A2---Class-UltraSD-Card-128G) | **Not verified** | Doesn't have to be the Pi one, but the Pi 5 turns on command queueing for it, and one guide says a SanDisk Extreme runs below its A2 rating on the Pi 5 ([HackMD guide](https://hackmd.io/@ampheo/what-is-the-best-micro-sd-card-for-raspberry-pi-5)); other guides disagree. Not a "high endurance" card: those are for dashcams and aren't A2 rated. The 64GB [SanDisk Extreme](https://www.pbtech.co.nz/product/MEMSDK33210/SanDisk-Extreme-64GB-microSDXC-Memory-Card-Class-1) (NZ$56.35, 17 Nov) is the fallback |
| MCP2515 CAN module (same Seeed board as the control box, section 6) | CAN for the Pi | [Core Electronics (AU)](https://core-electronics.com.au/seeed-studio-can-bus-breakout-board-for-xiao-and-qt-py-mcp2515-controller-sn65hvd230-transceiver-chip.html) | AU$18.45 (about NZ$23) | **Changed 18 Nov:** the Waveshare CAN HAT can't stack over the AI HAT+ 2's heatsink, so a small module sits on the Pi box wall, wired to the GPIO pins on top of the HAT (pins in [`wiring.md`](wiring.md)). Run `pi-setup.sh --can-osc <its crystal>`. Interrupt is GPIO 25, our default |
| 30 mm 5V fan (3007, 2-pin) | Pi box lid (see `cad/README.md`) | AliExpress (Sam's pick), or [Jaycar YX2500](https://www.jaycar.co.nz/5vdc-30mm-thin-2-wire-fan/p/YX2500) NZ$31.90 | ~NZ$4-9 (estimate) | Not needed for the bench. Less critical without the HAT (about 7-12 W in the box instead of up to 16 W) but still worth it: the Active Cooler only stirs the air inside, the lid fan swaps it for outside air, and the box may sit in the sun. Needed for sure with the HAT |
| USB audio out (optional, for the amp) | Pi 5 has no audio jack | [Jaycar USB to 3.5 mm](https://jaycar.co.nz/p/XC4953) | NZ$24.90 | NZ stock. It's a headphone output, not a line out, so keep the amp gain low |
| **Carlinkit CPC200-CCPA** ("Autokit") | CarPlay / Android Auto | **AliExpress** (Sam's pick, ~NZ$60-71), or [Carlinkit's Autokit store](https://autokitcarplay.com/products/autokit-ccpa-wireless-carplay-dongle-special-for-android-head-unit) US$65 (~NZ$118), or [Audio City NZ](https://www.audiocity.co.nz/ottocast/carlinkit-android-system-to-wireless-apple-carplay-android-auto-dongle.html) NZ$180 in stock (photo shows the CCPA code) | NZ$60-180 | Must be the CCPA / Autokit type for Android head units (see [`audio.md`](audio.md)). **Not** the "wired to wireless" ones (MINIX CA525 at PB Tech, Carlinkit 5.0 / 2Air at Mighty Ape): those need a car with CarPlay built in. On arrival `lsusb` must show `1314:1520` or `1314:1521`. Don't update its firmware. More in [`pbtech-order.md`](pbtech-order.md) |
| USB AV capture dongle (only if the camera is RCA/AHD) | Camera into the Pi | AliExpress, or [EasyCAP DC60 at PB Tech](https://www.pbtech.co.nz/product/SEVOEM9701) NZ$28.75 (composite only) | **Not verified** for AHD | Needs to be UVC so Linux sees it as a webcam. One per RCA/AHD camera. See [`cameras.md`](cameras.md) |

**Subtotal (Pi 8GB, cooler, HDMI adaptor, CAN module, fan): about NZ$458**, plus the SD card
(~NZ$47, search result), front camera (section 4a) and CarPlay dongle.

### 4a. Added for headroom (18 November)

| Part | Why | Where | Price | Notes |
|---|---|---|---|---|
| Raspberry Pi Camera Module 3 **Wide** | Front camera inside the screen housing, and the one the camera AI watches | [PB Tech](https://www.pbtech.co.nz/product/SEVRBP0398/Raspberry-Pi-Official-Camera-Module-3-Wide-Version) | ~NZ$80.71 (search result) | Out of stock when the search ran. [element14 NZ](https://nz.element14.com/raspberry-pi/sc0874/rpi-wide-camera-mod-3-wide-lens/dp/4132320) ~NZ$69, also out. Not waterproof and the ribbon only comes up to 500 mm, so it must sit inside the housing near the Pi |
| Pi 5 camera cable, 200 or 300 mm | Front camera to the Pi | Raspberry Pi resellers | **Not verified** | Pi 5 needs the 22-pin to 15-pin cable ([Raspberry Pi](https://www.raspberrypi.com/products/camera-cable/)) |
| Narva 7-pin flat socket with reed switch, 82043BL | Tells the dash a trailer is plugged in (`in.trailer`) | Narva stockists | **Not verified** | [Narva](https://narva.com.au/products/narva-7-pin-flat-quickfit-trailer-socket-with-reed-switch-for-use-with-normally-closed-circuits-1-pack). Check which way it switches |
| Trailer camera bits | See [`cameras.md`](cameras.md) section 3 | | | Pick wired plug, wireless or power-line first |
| USB SSD (later, see 4c) | Somewhere to keep recordings | e.g. Samsung T7 at PB Tech | **TBC** | **No NVMe on the PCIe port**, so it stays free for the AI HAT+ 2: the Pi 5 has one PCIe lane, so NVMe needs a switch board like the Seeed dual M.2 HAT ([SunFounder FAQ](https://docs.sunfounder.com/projects/nvme-kit/en/latest/faq.html), [Seeed wiki](https://wiki.seeedstudio.com/raspberry_pi_5_uses_pcie_hat_dual_hat/)). A USB SSD avoids that |

**Heat (when the HAT goes in).** The AI HAT+ 2 is rated for 0 to 50°C air around it
([Core Electronics](https://core-electronics.com.au/raspberry-pi-ai-hat-plus-2.html)). Its chip
draws about 2.5 to 4.5 W depending on the job ([heise](https://heise.de/-11136612),
[Jeff Geerling](https://jeffgeerling.com/blog/2026/raspberry-pi-ai-hat-2)). So the Pi box's
lid fan has to move air through the box, and the box wants to stay out of direct sun.

**Pi box height. Done 18 Nov:** the box was 46 mm tall inside; it's now 56 mm
(`cad/measurements.scad`, `pi_box_in`), sized for the Pi on 6 mm standoffs, the Active
Cooler, the AI HAT+ 2 on its 16 mm spacers and its heatsink, with about 19 mm of air under
the lid fan. The side vents grow with it. The CAN HAT is replaced by a small CAN module on the
box wall. Check the stack on the real parts before printing.

**Power.** The Pololu 5V 5.5A regulator in section 5 is still the pick. The Pi 5 flat out is
11.6 W (section 3), plus up to about 4.5 W for the HAT if it goes in later, so about 16 W of the
regulator's 27 W before USB devices. Power 12 V cameras from 12 V, not from the Pi's USB.

### 4b. GPS (added 18 November)

**The Pi 5 has no GPS built in, so it isn't free, but it's cheap.** The dash already knows
what to do with one: it reads `pi.gps.*` (see [`DASH_API.md`](DASH_API.md)) and shows "not
fitted" until those turn up. What's still to write is the small Pi-side bit that reads the
receiver (through `gpsd`, BSD licence, fine for us) and sends those keys.

| Part | Why | Where | Price | Notes |
|---|---|---|---|---|
| **DFRobot USB GPS receiver, TEL0138** | Position, speed, heading, height | [Core Electronics (AU)](https://core-electronics.com.au/catalog/product/view/sku/TEL0138), goes in the same parcel as the CAN boards | AU$21.05 (~NZ$26) (search result) | Local option: [RS NZ 247-3251](https://nz.rs-online.com/web/p/gnss-gps-modules/2473251) NZ$30.85 (search result). u-blox UBX-G7020 chip, 56 channels, under 2.5 m accuracy, 1 update a second, -40 to 85°C, magnetic base, 2 m USB lead ([DFRobot wiki](https://wiki.dfrobot.com/tel0138/), [Mouser](https://www.mouser.co.uk/new/dfrobot/dfrobot-tel0138-gps-receiver/)). The aerial is inside the puck. **No waterproof rating found**, so it goes under plastic, not out in the weather |

**Where it goes.** GPS goes through plastic but not metal. Stick the puck under the plastic
dash top or the roof panel with a clear view of the sky, and run the 2 m lead to the Pi. If
the Pi ends up under the bonnet and 2 m won't reach, a USB extension is fine (USB 2 is good
to 5 m).

**Why this one and not a fancier one.** On this dash GPS is a backup and a nice extra: speed
comes from the motor controller, and night mode already works from the clock. The TEL0138
is an older chip and I couldn't confirm it uses more than the American GPS satellites at
once, which can mean a slower or patchier fix under thick bush. If that bites, the upgrade is
a plug-in swap with no code change:

| Upgrade (only if needed) | Where | Price | Notes |
|---|---|---|---|
| u-blox NEO-M9N USB dongle with SMA aerial plug, ELT0103 | [gnss.store](https://gnss.store/products/elt0103) (Europe) | €66.99 ex VAT (search result), shipping to NZ **not checked** | Uses GPS, Galileo, GLONASS and BeiDou together, so more satellites under trees ([gnss.store](https://gnss.store/collections/standard-precision-dongles)) |
| Active magnetic GPS aerial, SMA, 3 m lead | [PB Tech CCTMLS1025 (Milesight)](https://www.pbtech.com/pacific/product/CCTMLS1025/Milesight-ACC-AM3M-G-GPS-Magnetic-Antenna-28dBi-wi) or [Core Electronics GPS-14986](https://core-electronics.com.au/catalog/product/view/sku/GPS-14986) | NZ$29.57 / AU$29.25 (search results) | Goes on the roof or roll cage, outside. Needed with the dongle above |

**What the dash uses it for:**

| Use | Status |
|---|---|
| Night mode from sunrise and sunset at where you actually are | **Works now** with a fix (a light sensor wins if one is fitted). Without GPS it uses the region picked in Settings. Position stays on the Pi, never saved or sent |
| Compass heading, height and satellite count on the Sensors panel | **Works now** with a fix |
| Speed backup if the motor controller speed is missing or wrong (wheelspin, locked wheels) | Key is there (`pi.gps.speed_kmh`), not wired into the speedo yet |
| Trail logging (record a ride, show where you've been) | **Not built yet.** Would need Sam's OK, since it saves where he goes |
| Offline maps | **Not built yet.** Would need map tiles stored on the SD card |
| Clock | The Pi has no clock battery fitted by default, so GPS can set the time with no wifi |

**USB ports are getting full.** The Pi 5 has 4 USB ports. Touch, rear camera, trailer camera
dongle, CarPlay dongle, USB audio, GPS and a mic later makes 6 or 7. Plan on a **powered USB
hub** in the Pi box for the low-speed ones (GPS, audio, mic, touch). Not priced yet.

### 4c. Later and optional (don't buy now)

| Part | Why | Price | Notes |
|---|---|---|---|
| [Raspberry Pi AI HAT+ 2](https://www.pbtech.co.nz/product/SEVRBP0446/Raspberry-Pi-5-Official-AI-Hat-2) (Hailo-10H, 8GB on board) | Camera AI and the voice assistant's language model | ~NZ$423 PB Tech (search result), or [Core Electronics](https://core-electronics.com.au/raspberry-pi-ai-hat-plus-2.html) ~NZ$357-373 landed | **Not buying now (Sam, 18 Nov).** US$200 list price ([Raspberry Pi](https://www.raspberrypi.com/products/ai-hat-plus-2/)). Comes with its own heatsink and a 16 mm stacking header so it sits over the Active Cooler. Uses the Pi's only PCIe port, so nothing else may use it |
| 4G board, prepaid SIM, AirTag | Anti-theft tracking, SMS and remote access | **Sam's pick: SIMCom A7670SA board** to solder in, ~NZ$28 on AliExpress, must list **B28**, needs its own 3.8 V supply from a 3 A buck (2.8 A peak), maybe a 1.8 V level shifter; UART is too slow for cameras, so a board with the module's own USB on USB-C is better and a wideband LTE antenna. Plug-in alternatives: Huawei E3372h-607 stick ~NZ$66-77, Waveshare SIM7600G-H US$101.99. AirTag ~NZ$47-68 | From the 4G anti-theft work. Dongle goes inside the Pi box. SIM needs a top-up once a year |
| Kingston XS1000 1TB USB-C SSD (optional), PB Tech HDDKCP225100 | Dashcam and Sentry video | NZ$189-253 | USB, not NVMe. Cradle in the Pi box lid, short right-angle USB-C to USB-A lead |
| Camera Module 3 NoIR Wide (optional), PB Tech SEVRBP0399 | Cabin camera | ~NZ$70 | Plus a second 200 mm cable |
| Powered USB hub | More USB ports | Not priced | See "USB ports are getting full" below. The Pi 5's USB ports share 1.6 A, so the modem and SSD may need the hub's power |

AUD to NZD: 1 AUD = 1.234 NZD on [Wise](https://wise.com/us/currency-converter/aud-to-nzd-rate)
when checked (no timestamp on the page). Core Electronics prices are AUD incl Australian GST;
NZ GST may be charged on import instead.

## 5. Power from the Teryx's 12V

The dash runs off the 12V battery that's kept after the conversion. In an EV there's no
starter motor, so no cranking dips. The real risks are:

- **Winch sag.** The XBull pulls hundreds of amps (it has a 250 A breaker, see
  [`wiring.md`](wiring.md)), so the 12V can sag well below 11V while winching.
- **Spikes** when big inductive loads (winch, actuators) switch off.
- **Charging voltage** from the DC-DC, up to about 14.8V ([`cad/README.md`](../cad/README.md)).

So both regulators want a **wide input range**, and there's a TVS diode across the dash rail.

| Part | Why | Where | Price | Notes |
|---|---|---|---|---|
| Pololu D36V50F5, 5V 5.5A, 5.5-50V in | Pi 5 power. Handles winch sag and spikes, has reverse polarity protection to 40V | [Core Electronics (AU)](https://core-electronics.com.au/catalog/product/view/sku/POLOLU-4091) | AU$90.11 (about NZ$111) | In stock. Specs: [Pololu](https://www.pololu.com/product/4091/specs). Feed the Pi's 5V/GND header pins with short thick wire and set `usb_max_current_enable=1`, or USB gets limited to 600 mA ([bret.dk](https://bret.dk/how-to-power-the-raspberry-pi-5-a-complete-guide)) |
| Cheap alternative: Mini560 5V 5A buck, 7-20V in | Same job, cheaper | [Gogo:Tronics](https://sparks.gogo.co.nz/catalog/DC-Power-260/Fixed-Output-Step-Down-Converter-Out-5v-up-to-5A-Continuous-In-7-20v-1009.html) | NZ$2.95 | About 9 in stock. Fine on the bench. 20V max input is tight for the car: the TVS below clamps at up to 25V, so a spike could still kill it. That's why the Pololu is the pick for the car |
| Mini560 5V 5A buck | Pico control box power (5V 2A is plenty) | [Gogo:Tronics](https://sparks.gogo.co.nz/catalog/DC-Power-260/Fixed-Output-Step-Down-Converter-Out-5v-up-to-5A-Continuous-In-7-20v-1009.html) | NZ$2.95 | Buy two or three, they're cheap. Same 20V limit, so it sits behind the TVS and fuse |
| 1.5KE18A TVS diode | Clamps spikes on the dash 12V rail | [element14 NZ](https://nz.element14.com/stmicroelectronics/1-5ke18a/diode-tvs-1-5kw-18v/dp/9884831) | $2.24 each (element14 NZ, didn't say if GST is in) | 15.3V standoff, so it ignores normal charging voltage. Fit after the rail fuse, so if it ever shorts it blows the fuse |
| **20-way** blade fuse block with cover and negative bus | Fusing every output | AliExpress (Sam's pick) | ~NZ$27-46 (estimate) | **Changed 18 Nov:** the wiring plan (`config/wiring.yaml`) has 16 fused circuits, so the 12-way [Jaycar SZ2032](https://www.jaycar.co.nz/12-way-fuse-block-with-bus-bar/p/SZ2032) (NZ$53.90) is too small; two of those also work. Want 30 A per way, 100 A total, a cover, stud feed. Buy the blade fuses themselves in NZ |
| Screen 12V supply | The screen's own power | Depends on its brick | **TBC** | Read the label on the screen's power brick first. If it's 12V: a 12V stabiliser like the [Gogo:Tronics buck/boost](https://sparks.gogo.co.nz/catalog/DC-Power-260/Step-Up-288/Auto-Step-UpDown-BuckBoost-DC-DC-Converter-174.html) (NZ$15.00, 3-35V in, but only 12 W without a heatsink, so it depends on the screen's draw) or the [SparkFun 8-40V to 12V 3A](https://core-electronics.com.au/buck-boost-converter-8-40v-to-12v-3a.html) (AU$53.30, lead time). The [interVOLT 12/12 5A](https://www.marine-deals.co.nz/intervolt-voltage-stabiliser-12-12-vdc-5-amp) (NZ$179) was out of stock |

**If you go mini PC instead:** it wants 12V in, so it needs the same kind of 12V stabiliser
as the screen, sized for about 3A (the PB Tech listing says 12V/3A in). MINIX doesn't say
how far over 12V it will take, so don't feed it raw battery voltage.

## 6. Control box parts

From [`io-list.md`](io-list.md) and [`wiring.md`](wiring.md).

| Part | Qty | Where | Price | Notes |
|---|---|---|---|---|
| Raspberry Pi Pico 2, 5-pack | 1 pack | [PB Tech](https://www.pbtech.co.nz/product/SEVRBP0628/Raspberry-Pi-Kit-Pack-Microcontrollers-Board---Pic) | NZ$47.20 | In stock, 40 across 7 stores. Covers the control box, the CAN sniffer and three spares. Singles are [NZ$17 at Pakronics](https://www.pakronics.co.nz/products/raspberry-pi-pico-2-ss102111004) but were out of stock |
| CAN board, MCP2515 + SN65HVD230 (3.3V) | 3 | [Core Electronics (AU), Seeed](https://core-electronics.com.au/seeed-studio-can-bus-breakout-board-for-xiao-and-qt-py-mcp2515-controller-sn65hvd230-transceiver-chip.html) | AU$18.45 each (about NZ$23) | 15 in stock. One for the control box, one for the sniffer, and one for the Pico's own CAN link to the Toyota Aqua power steering column ([`power-steering-wrecker.md`](power-steering-wrecker.md)). Plus one more for the Pi (section 4), so 4 in the Core order. 3.3V all through, which `wiring.md` prefers over the 5V TJA1050 boards. **Check the crystal on the board** and build the firmware to match (`MCP2515_OSC_HZ`, default 8 MHz; the sniffer has 8 and 16 MHz builds) |
| Cheap alternative: blue MCP2515 + TJA1050 module | 2 | AliExpress | **Not verified** | 5V transceiver, so wire it as `wiring.md` says. Usually an 8 MHz crystal |
| MCP23017 board | 1 | [Core Electronics (AU), Waveshare](https://core-electronics.com.au/catalog/product/view/sku/WS-15391) | AU$10.90 (about NZ$13) | 9 in stock |
| ADS1115 board | 1 (io-list says on hand) | [Core Electronics (AU), DFRobot](https://core-electronics.com.au/gravity-i2c-ads1115-16-bit-adc-module-arduino-raspberry-pi-compatible.html) | AU$24.53 (about NZ$30) | In stock. Cheap ADS1115 boards on AliExpress, not verified |
| BTS7960 H-bridge | 3 (io-list says 1 on hand) | AliExpress | **Not verified** | No NZ shop stocks them that I could find. Fruugo NZ lists them but the prices and dates on the page looked stale |
| 8-channel PC817 opto board, 12V in | 1 | AliExpress | **Not verified** | |
| MOSFET PWM board, logic level (AOD4184 or similar), 5 channels | 1 (or five 1-channel boards) | AliExpress | **Not verified** | Only once a light bar is shown to dim |
| 8-channel relay board | 1 (io-list says on hand) | | | Check it switches from 3.3V |
| Micro switch with lever (tray limits) | 2 | Jaycar SM1038 | **NZ price not verified** | [Australian page](https://jaycar-prod.australia-southeast1.gcp.storefrontcloud.io/spdt-250v-3a-miniature-micro-switch-with-lever/p/SM1038) shows $4.95. Wants to be sealed for under a tray: look for IP67 |
| Resistors, diodes, 3.3V zener, 4.7k pull-ups | a few | Gogo:Tronics or Jaycar | **Not verified** | Values in `wiring.md` |
| IMU (optional) | 1 | | **Not verified** | |
| Toyota Aqua power steering column, ECU 89650-52B51 | 1 | Dodson's, Trade Me | about NZ$115 | Separate pickup, 19 Nov. See [`power-steering-wrecker.md`](power-steering-wrecker.md) |

## 7. Printed parts hardware

Full list in [`cad/README.md`](../cad/README.md): M3 heat-set inserts (about 40), M3 and M4
bolts and nylocs, cable glands (PG7, PG9, PG16, M20), 2 mm foam tape, gasket TPU, and ASA or
PETG filament. **Not priced**: bolts and glands are cheapest at a fastener shop or AliExpress
and I didn't check them.

## 8. What I couldn't check

- Prices of the cheap AliExpress modules (BTS7960, opto board, MOSFET board, blue MCP2515).
  AliExpress search pages show bait "welcome deal" prices, so I didn't quote them.
- Whether Audio City's Carlinkit dongle is the CCPA: their page has no model number.
- Which Carlinkit web shops are official: several sites use the name and I found no list.
- Boot time of any option.
- Real CPU load of CarPlay video on a Pi 5. Test this first when the Pi turns up.
- Live prices for the Pi 5 8GB, AI HAT+ 2, Camera Module 3 Wide and the official SD card
  (PB Tech's pages wouldn't open on 18 November, so these came from search results).
- Prices for the 4G modem and video SSD (models not picked yet).
- Memory used by camera feeds and camera AI on the Pi (guessed in section 1).
- The screen's power brick voltage and current.
- Whether the TEL0138 GPS uses GLONASS as well as GPS, and the landed price of the NEO-M9N upgrade.

## Sources

Shops: [PB Tech](https://www.pbtech.co.nz), [Jaycar NZ](https://www.jaycar.co.nz),
[Gogo:Tronics](https://sparks.gogo.co.nz), [Core Electronics](https://core-electronics.com.au),
[element14 NZ](https://nz.element14.com), [Pakronics](https://www.pakronics.co.nz),
[Marine Deals](https://www.marine-deals.co.nz). Facts: linked in each row above.
Nicegear and Mindkits were checked too: a web search didn't turn up Nicegear listings for these parts,
and Mindkits had the Active Cooler at [NZ$12.66 but out of stock](https://mindkits.co.nz/Raspberry-Pi-Active-Cooler.aspx).
