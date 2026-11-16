# Shopping list and which dash computer to buy

Prices checked live on **17 November 2026** (NZ time), incl GST unless it says otherwise.
Every price has a link. Where I couldn't check a price, it says **not verified** and gives
no number. Prices move a lot right now because of the RAM shortage (see below), so check
the link before you buy.

You own the screen (10.1" 1280x800, HDMI + USB touch). Everything else on this list is
still to buy. [`io-list.md`](io-list.md) lists some things as "on hand" (relay board,
one BTS7960, ADS1115, actuators, camera, lights, winch, a buck): those are in
section 5 below, so tick off whatever you really do have.

## 1. Short answer

**Buy a Raspberry Pi 5 4GB.** It's the cheapest option that runs the whole stack with
lots of room to spare, it's the only one that needs **no code changes**, it fits the Pi box
we already designed, and it draws the least power from the 12V system.

- 8GB is a waste for this job: the measured worst case is under 1.5 GB in use (section 2).
- An N100/N150 mini PC works, costs about twice as much, draws two to three times the
  power, and needs a new box and setup script (section 3).
- A rugged tablet costs NZ$2,254 or more and throws away the screen you already have. No.

Rough cost of the dash computer bits (section 4): about **NZ$341** for the Pi 5 4GB, cooler,
cable, SD card and CAN HAT, plus about **NZ$115** for proper 12V protection and a good 5V
regulator. The control box (section 5) is extra.

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

## 4. Dash computer parts (Pi 5 4GB)

| Part | Why | Where | Price | Notes |
|---|---|---|---|---|
| Raspberry Pi 5 4GB | The dash | [PB Tech](https://www.pbtech.co.nz/product/SEVRBP0501/Raspberry-Pi-5-4GB-LPDDR4-24GHz-Quad-Core-ARM-Cort) | NZ$232.69 | On order, ships about 11 Jan. Or the [4GB starter kit](https://www.pbtech.co.nz/product/SEVRBP0855/Raspberry-Pi-5-4GB-Entry-Level-Starter-Kit-Pack-Wh) for NZ$309.00, which adds a micro HDMI cable, 32GB card, case and a 27 W mains power supply for the bench (on order, ships about 17 May) |
| Raspberry Pi Active Cooler | Keeps it under 85°C | [PB Tech](https://www.pbtech.co.nz/product/SEVRBP0531) | NZ$11.21 | In stock |
| Micro HDMI to HDMI cable, 2 m | Pi to screen | [PB Tech (Vention)](https://www.pbtech.co.nz/product/VNT1306/Vention-VAA-D03-B200-Micro-HDMI-Cable---2m---Black) | NZ$12.41 | No stock, ships about 28 Jan. In stock now: [Jaycar micro HDMI adaptor](https://jaycar.co.nz/micro-hdmi-plug-to-hdmi-socket-adaptor/p/PA3649) NZ$20.90 plus an HDMI cable |
| microSD card 64GB A2 | OS | [PB Tech SanDisk Extreme](https://www.pbtech.co.nz/product/MEMSDK33210/SanDisk-Extreme-64GB-microSDXC-Memory-Card-Class-1) | NZ$56.35 | Out of stock when checked. Any A2 card from a name brand is fine |
| Waveshare RS485 CAN HAT | CAN for the Pi | [Core Electronics (AU)](https://core-electronics.com.au/catalog/product/view/sku/WS-14882) | AU$22.75 (about NZ$28) | In stock. Ships to NZ from about AU$12. **It has a 12 MHz crystal** ([Waveshare wiki](https://www.waveshare.com/wiki/RS485_CAN_HAT)), so run `pi-setup.sh --can-osc 12000000`. Interrupt is GPIO 25, which is our default |
| 30 mm 5V fan | Pi box lid (see `cad/README.md`) | [Jaycar](https://www.jaycar.co.nz/5vdc-30mm-thin-2-wire-fan/p/YX2500) | NZ$31.90 | NZ stock. Much cheaper on AliExpress, not verified |
| USB audio out (optional, for the amp) | Pi 5 has no audio jack | [Jaycar USB to 3.5 mm](https://jaycar.co.nz/p/XC4953) | NZ$24.90 | NZ stock. It's a headphone output, not a line out, so keep the amp gain low |
| Carlinkit CPC200-CCPA (optional) | CarPlay / Android Auto | Carlinkit's own store or AliExpress | **Not verified** | No NZ seller found. [PriceSpy NZ](https://pricespy.co.nz/product.php?p=13023735) has no active listings. Must be the CCPA / Autokit type (see [`audio.md`](audio.md)) |
| USB AV capture dongle (only if the camera is RCA/AHD) | Camera into the Pi | AliExpress | **Not verified** | Needs to be UVC so Linux sees it as a webcam |

**Subtotal (Pi, cooler, cable, card, HAT): about NZ$341** (NZ$312.66 at PB Tech plus about
NZ$28 for the HAT, before shipping).

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
| 12-way blade fuse block | Fusing every output | [Jaycar SZ2032](https://www.jaycar.co.nz/12-way-fuse-block-with-bus-bar/p/SZ2032) | NZ$53.90 | NZ stock. 30 A per way, 100 A total |
| Screen 12V supply | The screen's own power | Depends on its brick | **TBC** | Read the label on the screen's power brick first. If it's 12V: a 12V stabiliser like the [Gogo:Tronics buck/boost](https://sparks.gogo.co.nz/catalog/DC-Power-260/Step-Up-288/Auto-Step-UpDown-BuckBoost-DC-DC-Converter-174.html) (NZ$15.00, 3-35V in, but only 12 W without a heatsink, so it depends on the screen's draw) or the [SparkFun 8-40V to 12V 3A](https://core-electronics.com.au/buck-boost-converter-8-40v-to-12v-3a.html) (AU$53.30, lead time). The [interVOLT 12/12 5A](https://www.marine-deals.co.nz/intervolt-voltage-stabiliser-12-12-vdc-5-amp) (NZ$179) was out of stock |

**If you go mini PC instead:** it wants 12V in, so it needs the same kind of 12V stabiliser
as the screen, sized for about 3A (the PB Tech listing says 12V/3A in). MINIX doesn't say
how far over 12V it will take, so don't feed it raw battery voltage.

## 6. Control box parts

From [`io-list.md`](io-list.md) and [`wiring.md`](wiring.md).

| Part | Qty | Where | Price | Notes |
|---|---|---|---|---|
| Raspberry Pi Pico 2, 5-pack | 1 pack | [PB Tech](https://www.pbtech.co.nz/product/SEVRBP0628/Raspberry-Pi-Kit-Pack-Microcontrollers-Board---Pic) | NZ$47.20 | In stock, 40 across 7 stores. Covers the control box, the CAN sniffer and three spares. Singles are [NZ$17 at Pakronics](https://www.pakronics.co.nz/products/raspberry-pi-pico-2-ss102111004) but were out of stock |
| CAN board, MCP2515 + SN65HVD230 (3.3V) | 2 | [Core Electronics (AU), Seeed](https://core-electronics.com.au/seeed-studio-can-bus-breakout-board-for-xiao-and-qt-py-mcp2515-controller-sn65hvd230-transceiver-chip.html) | AU$18.45 each (about NZ$23) | 15 in stock. One for the control box, one for the sniffer. 3.3V all through, which `wiring.md` prefers over the 5V TJA1050 boards. **Check the crystal on the board** and build the firmware to match (`MCP2515_OSC_HZ`, default 8 MHz; the sniffer has 8 and 16 MHz builds) |
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

## 7. Printed parts hardware

Full list in [`cad/README.md`](../cad/README.md): M3 heat-set inserts (about 40), M3 and M4
bolts and nylocs, cable glands (PG7, PG9, PG16, M20), 2 mm foam tape, gasket TPU, and ASA or
PETG filament. **Not priced**: bolts and glands are cheapest at a fastener shop or AliExpress
and I didn't check them.

## 8. What I couldn't check

- Prices of the cheap AliExpress modules (BTS7960, opto board, MOSFET board, blue MCP2515).
  AliExpress search pages show bait "welcome deal" prices, so I didn't quote them.
- The Carlinkit CCPA in NZ.
- Boot time of any option.
- Real CPU load of CarPlay video on a Pi 5. Test this first when the Pi turns up.
- The screen's power brick voltage and current.

## Sources

Shops: [PB Tech](https://www.pbtech.co.nz), [Jaycar NZ](https://www.jaycar.co.nz),
[Gogo:Tronics](https://sparks.gogo.co.nz), [Core Electronics](https://core-electronics.com.au),
[element14 NZ](https://nz.element14.com), [Pakronics](https://www.pakronics.co.nz),
[Marine Deals](https://www.marine-deals.co.nz). Facts: linked in each row above.
Nicegear and Mindkits were checked too: a web search didn't turn up Nicegear listings for these parts,
and Mindkits had the Active Cooler at [NZ$12.66 but out of stock](https://mindkits.co.nz/Raspberry-Pi-Active-Cooler.aspx).
