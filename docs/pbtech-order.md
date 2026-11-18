# Shopping list for Thursday 19 November (PB Tech and the rest)

Updated **18 November 2026** (NZ time). Prices are NZ$ incl GST. "Checked 17 Nov" means I
opened the shop's page then. "Search result" means the shop's page wouldn't open for me on
18 Nov (PB Tech blocks my requests), so the price came from a search engine's copy of the
page and **may be out of date**. Check each link before you pay. Why each part is needed:
[`shopping-list.md`](shopping-list.md). Spreadsheet copy: [`pbtech-order.csv`](pbtech-order.csv).

**What changed today:** the AI HAT+ 2 is off the list for now (moved to "Later"), the CarPlay
dongle is on, a fourth CAN board is added for the power steering column, and the 4G modem
and video SSD are listed as "later". The Pi box stays sized for the AI HAT.

## Buy tomorrow (in store or click and collect)

| # | Part | Shop | SKU | Qty | Price | Price from | Stock / notes |
|---|---|---|---|---|---|---|---|
| 1 | [Raspberry Pi 5 8GB](https://www.pbtech.co.nz/product/SEVRBP0502/Raspberry-Pi-5-8GB-LPDDR4-24GHz-Quad-Core-ARM-Cort) | PB Tech | SEVRBP0502 | 1 | NZ$371.39 | Checked 17 Nov | Was on order, ships about 30 Nov. Ask in store if any have come in. A search result showed NZ$254.15, maybe an old price |
| 2 | [Raspberry Pi Active Cooler](https://www.pbtech.co.nz/product/SEVRBP0531) | PB Tech | SEVRBP0531 | 1 | NZ$11.21 | Checked 17 Nov | In stock. **Still needed without the AI HAT**, see "Cooling" below |
| 3 | [Raspberry Pi A2 SD card 128GB](https://www.pbtech.co.nz/product/SEVRBP0538/Raspberry-Pi-Official-A2---Class-UltraSD-Card-128G) | PB Tech | SEVRBP0538 | 1 | NZ$47.32 | Search result | In stock when indexed |
| 4 | [Camera Module 3 Wide](https://www.pbtech.co.nz/product/SEVRBP0398/Raspberry-Pi-Official-Camera-Module-3-Wide-Version) | PB Tech | SEVRBP0398 | 1 | NZ$80.71 | Search result | **Out of stock** when indexed. Alternative: [element14 NZ SC0874](https://nz.element14.com/raspberry-pi/sc0874/rpi-wide-camera-mod-3-wide-lens/dp/4132320) ~NZ$69, also out then. Not needed for the first bench tests, so skip it if there's none |
| 5 | [Pi 5 camera cable 200 mm](https://www.pbtech.com/pacific/product/SEVRBP0541) | PB Tech | SEVRBP0541 | 1 | ~NZ$2.12 | Search result | Only with the camera |
| 6 | [Raspberry Pi Pico 2, 5-pack](https://www.pbtech.co.nz/product/SEVRBP0628/Raspberry-Pi-Kit-Pack-Microcontrollers-Board---Pic) | PB Tech | SEVRBP0628 | 1 | NZ$47.20 | Checked 17 Nov | In stock. Control box, CAN sniffer, power steering bench test, 2 spares |
| 7 | [Raspberry Pi 27W USB-C power supply](https://www.pbtech.co.nz/product/SEVRBP0512) | PB Tech | SEVRBP0512 | 1 | ~NZ$24.90 | Search result | Bench only. In the Teryx the Pololu regulator powers the Pi |
| 8 | [Raspberry Pi official micro HDMI to HDMI cable, 1 m, white](https://www.pbtech.co.nz/product/SEVRBP0207/Raspberry-Pi-Official-1M-White-Cable-Micro-HDMI-to) | PB Tech | SEVRBP0207 | 1 | NZ$11.80 | Search result | Stock not confirmed. Same cable in black: [SEVRBP0262](https://www.pbtech.co.nz/product/SEVRBP0262/Raspberry-Pi-Official-1M-Black-Cable-Micro-HDMI-to) ~NZ$11.10. If neither is in, [Jaycar PA3649 adaptor](https://jaycar.co.nz/micro-hdmi-plug-to-hdmi-socket-adaptor/p/PA3649) NZ$20.90 plus any HDMI cable. Use a **cable**, not a plug-in adaptor: a stiff adaptor hanging off the micro HDMI socket will work loose or crack the socket on the trail. The screen sits right over the Pi box, so 1 m is plenty; zip-tie the cable down close to the plug. Stay with HDMI, not VGA: the Pi has no VGA out, so it would need an active converter box, which is one more thing to fail and gives a softer picture. A printed clamp for the plug in the Pi box is a follow-up |
| | **Buy tomorrow total (all PB Tech)** | | | | **about NZ$597** | | NZ$516 if the camera is out of stock |

Everything for tomorrow is at PB Tech now. The lid fan and fuse block moved to the AliExpress cart
(Sam, 18 Nov): the bench Pi runs fine on the Active Cooler alone, and the fuse block isn't needed
until wiring the Teryx.

**CarPlay dongle:** Sam has decided to get it from AliExpress (see the AliExpress cart below).
Audio City's one (NZ$180, [link](https://www.audiocity.co.nz/ottocast/carlinkit-android-system-to-wireless-apple-carplay-android-auto-dongle.html))
shows the right CCPA part code in its photo, so it's the backup if you want it straight away.
**Not these:** the Carlinkit 5.0 / 2Air at Mighty Ape, or the MINIX CA525 at PB Tech (see
"Getting the right CarPlay dongle").

## AliExpress cart (one order, about 2 to 4 weeks)

Sam wants one AliExpress order at about half NZ shop prices. **AliExpress pages won't open for
me**, so these prices are from search-engine snapshots and deal sites, in US$ at 1.822. They
move daily with coupons, so check each one in the app before paying. AliExpress adds NZ GST at
checkout. Delivery to NZ is usually 2 to 4 weeks, and only the travel part is covered by
AliExpress's delivery promises, not customs
([findniche](https://findniche.com/blog/aliexpress-shipping-time),
[parcelmonitor](https://www.parcelmonitor.com/blog/aliexpress-shipping-time-tracking)).
Pick listings marked "Choice" where you can: they usually ship free and faster.

| Part | Search for | Qty | Rough price | What to check |
|---|---|---|---|---|
| **Carlinkit CPC200-CCPA** CarPlay / Android Auto dongle | "Carlinkit CCPA" | 1 | US$33-39 (~NZ$60-71). Snapshots: [US$33.17, 2,000+ sold](https://www.aliexpress.us/item/3256809220614383.html), [CCPA with mic US$38.77](https://www.aliexpress.com/item/32983926178.html) | Title must say **CCPA** (or Autokit) and "for Android head unit / car radio", and mention the Autokit app. The **CCPA-MIC** option has a built-in mic, worth the few dollars more for Siri and calls. I couldn't confirm which AliExpress shop is Carlinkit's own, so pick one with thousands sold and good reviews. On arrival `lsusb` must show `1314:1520` or `1314:1521`, or send it back (see "Getting the right CarPlay dongle") |
| **4-channel class D amp, 12V** | "4 channel class D amplifier 12V marine" | 1 | ~US$45 (~NZ$82). Snapshot: a Sennuopu 4-channel "400W RMS" listing at [US$44.79](https://www.aliexpress.com/w/wholesale-amplifier-4-channel-class-d.html) | Must have **RCA line inputs** and a **remote turn-on wire** ([`audio.md`](audio.md) section 2). Cheap amps overstate power: "400W" usually means about 4 x 25-50 W real, which is fine for a pair of marine speakers. The one I found **doesn't say it's waterproof**, so mount it under the seat out of the weather. If you want a proper IPX5/6 sealed one, that's a brand-name marine amp from an NZ car audio shop (about NZ$150-300 budget, NZ$400-900 good) |
| **BTS7960 43A H-bridge** | "BTS7960" | 2 | ~US$6-7 each (~NZ$12). Not found on AliExpress itself; [Walmart](https://www.walmart.com/ip/BTS7960-43A-High-Power-Motor-Driver-Module-Smart-Car-Driver-Module-for-Current-Limit/8904873796) has 2 for US$11.56 | Actuators. You have one already (io-list), 3 needed |
| **8-channel PC817 opto board, 12V in** | "8 channel optocoupler PC817 12V" | 1 | Not priced | See `shopping-list.md` section 6 |
| **MOSFET PWM board, 5 channels** | "AOD4184 MOSFET module" | 1 (or 5 singles) | Not priced | Only once a light bar is shown to dim |
| **Phone gamepad grip** (Razer Kishi style) for RC mode | "GameSir G8 Galileo", from the **GameSir official store** | 1 | US$40-45 on deals (~NZ$73-82), list price [US$79.99](https://gamesir.com/collections/all-products/products/gamesir-g8-galileo). Deal posts: [Slickdeals](https://slickdeals.net/f/19268917-gamesir-phone-controllers-g8-galileo-usb-c-gray-44-79-g8-bluetooth-black-free-u-s-shipping-aliexpress) | Half the [Razer Kishi V3](https://www.pbtech.co.nz/product/JOYRAZ112682) at PB Tech (NZ$167.58, [`rc-beach-launch.md`](rc-beach-launch.md)). USB-C, Hall effect sticks and triggers, stretches to fit the phone. Get the **USB-C** one, not the Bluetooth G8+, so it plugs straight into the phone like the Kishi. Test it on the RC page (HTTPS) when it arrives |
| **Blade fuse block, 20-way, with cover and negative bus** | "20 way blade fuse box negative bus cover" | 1 | ~US$15-25 (~NZ$27-46), my estimate. AliExpress search pages show bait prices like [US$1.09](https://www.aliexpress.com/w/wholesale-Modular%20Fuse%20Block.html); a similar 12-way Nilight is [US$22.99 at Walmart](https://www.walmart.com/c/kp/electrical-box-bus) | The wiring plan has **16 fused circuits** (`config/wiring.yaml`, F1-F16), so get a 20-way for spares. Look for: clip-on cover (ideally a seal), built-in negative bus, 30 A per way and 100 A total, studs or screw terminals for the feed (not a push-on spade), and blown-fuse LEDs are a bonus. A proper brand (Blue Sea, Narva) is better if it'll live where it gets wet |
| **30 mm 5V fan, 2-pin (3007)** | "3007 5V fan 2 pin" | 1-2 | ~US$2-5 (~NZ$4-9), my estimate. A [reseller copy of an AliExpress listing](https://ubbthreads.com/store/item/4x-2-Pin-30MMx30MM-3007-5V-Cooling-Fan-radiating-For-Raspberry-Pi-2-3-Model-B-4B_285308377334.html) shows US$8.89 for 4 | Pi box lid. Must be 30 x 30 x 7 mm to fit the printed lid. Get a spare, they're cheap |
| | | | **about NZ$295** | Dongle NZ$65, amp NZ$82, 2 x BTS7960 NZ$24, grip NZ$78, fuse block ~NZ$40, fan ~NZ$6. Opto and MOSFET boards on top |

### Better bought in NZ or from a proper shop, not AliExpress

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

## Order online this week (other shops)

| Part | Where | Qty | Price | Notes |
|---|---|---|---|---|
| [Seeed MCP2515 + SN65HVD230 CAN board](https://core-electronics.com.au/seeed-studio-can-bus-breakout-board-for-xiao-and-qt-py-mcp2515-controller-sn65hvd230-transceiver-chip.html) | Core Electronics (AU) | **4** | AU$18.45 each (~NZ$91 for 4) | Pi, control box, sniffer, and **new: the Pico's own CAN link to the Toyota Aqua power steering column** ([`power-steering-wrecker.md`](power-steering-wrecker.md)). Check the crystal |
| [MCP23017 board](https://core-electronics.com.au/catalog/product/view/sku/WS-15391) | Core Electronics (AU) | 1 | AU$10.90 (~NZ$13) | Control box inputs and relays |
| [DFRobot USB GPS TEL0138](https://core-electronics.com.au/catalog/product/view/sku/TEL0138) | Core Electronics (AU) | 1 | AU$21.05 (~NZ$26) | Search result. Or [RS NZ](https://nz.rs-online.com/web/p/gnss-gps-modules/2473251) NZ$30.85 |
| [Pololu D36V50F5 5V 5.5A regulator](https://core-electronics.com.au/catalog/product/view/sku/POLOLU-4091) | Core Electronics (AU) | 1 | AU$90.11 (~NZ$111) | Powers the Pi from the 12V battery. Big enough for the AI HAT later |
| Core Electronics shipping | | | ~NZ$15-20 | Check at checkout |
| [Mini560 5V 5A buck](https://sparks.gogo.co.nz/catalog/DC-Power-260/Fixed-Output-Step-Down-Converter-Out-5v-up-to-5A-Continuous-In-7-20v-1009.html) | Gogo:Tronics | 2 | NZ$2.95 each | Pico control box power and a spare |
| [1.5KE18A TVS diode](https://nz.element14.com/stmicroelectronics/1-5ke18a/diode-tvs-1-5kw-18v/dp/9884831) | element14 NZ | 2 | NZ$2.24 each | Spike clamp on the dash 12V |
| [Narva 7-pin flat socket with reed switch 82043BL](https://narva.com.au/products/narva-7-pin-flat-quickfit-trailer-socket-with-reed-switch-for-use-with-normally-closed-circuits-1-pack) | Narva stockists | 1 | **Not priced** | Trailer detect |
| | | | **about NZ$270** | Priced items |

AUD to NZD at 1.234 (Wise, 17 Nov). USD to NZD at 1.822 (Wise, 18 Nov, no time shown on the page).

## Separate pickup

| Part | Where | Price | Notes |
|---|---|---|---|
| Toyota Aqua power steering column, ECU 89650-52B51 | Dodson's, Trade Me | about NZ$115 | Picking up 19 Nov. A cheap gamble, see [`power-steering-wrecker.md`](power-steering-wrecker.md). Needs the 4th CAN board above to bench test |

## Totals

| | NZ$ |
|---|---|
| Buy tomorrow (all PB Tech) | ~597 |
| AliExpress cart | ~295 |
| Other online orders (Core, Gogo, element14) | ~270 |
| Aqua column | ~115 |
| **Everything priced** | **about NZ$1,276** |

The amp (NZ$82) and the gamepad grip (NZ$78) are new to the list today. Without those two it's
about NZ$1,116. Not counted: blade fuses, the opto and MOSFET boards, Narva socket, trailer camera bits,
speakers and amp wiring, and everything under "Later".

## Cooling without the AI HAT

- **Active Cooler: yes, still buy it.** The dash will decode CarPlay video on the CPU the whole
  time it's running (the Pi 5 has no H.264 decoder), which is a long steady load, inside a closed
  box. Raspberry Pi say heavy continuous loads will throttle a bare Pi 5, and their own tests had
  the Active Cooler keeping it at 71°C where no cooler hit 83°C in 30 seconds
  ([Raspberry Pi](https://www.raspberrypi.com/news/heating-and-cooling-raspberry-pi-5/),
  [white paper](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010139-WP-1-Use-case-specific%20thermal%20performance%20of%20Raspberry%20Pi%20SBCs.pdf)).
  It's NZ$11, and it's what goes under the AI HAT later anyway. Keep your passive heatsink for
  the bench.
- **30 mm lid fan: yes, but it's less critical now.** The Active Cooler only moves air around
  inside the box; the lid fan swaps hot box air for outside air. Without the HAT the box makes
  about 7-12 W instead of up to about 16 W, so the fan matters less, but the box can sit in the
  sun and the fan mount is already in the lid. It's needed for sure once the HAT goes in.

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
| [Raspberry Pi AI HAT+ 2](https://www.pbtech.co.nz/product/SEVRBP0446/Raspberry-Pi-5-Official-AI-Hat-2) | Camera AI, local voice assistant | ~NZ$423 PB Tech (search result), or [Core Electronics](https://core-electronics.com.au/raspberry-pi-ai-hat-plus-2.html) AU$289 (~NZ$357-373 landed) | **Not buying now.** The Pi box stays 56 mm tall for it, the Pi's PCIe slot stays free, its header stays clear (the CAN board sits on the box wall), and the Pololu regulator has the spare power |
| **Huawei E3372h-607 4G USB stick** (optional, cheaper pick) | Anti-theft tracking, SMS and remote access | ~US$36-42 (~NZ$66-77) on eBay/AliExpress (search results), or second-hand on Trade Me | Bands 1/3/7/8/28/40, which covers Spark, One NZ and 2degrees including the 700 MHz B28 country band ([listing](https://ubbthreads.com/store/item/Huawei-E3372h-607-4G-LTE-FDD-TDD-B40-4GX-USB-Dongle-Mobile-Broadband-150Mbps-NEW_314457944618.html)). Shows up on the Pi as a plain network adaptor, no driver needed, and SMS works through its built-in web API. **Check the label under the cap says E3372h-607** (other versions like -153 or -320 miss B28), and that it's unlocked if second-hand. No GPS built in, but the Pi already has the GPS puck. Light data and SMS is all we need |
| Waveshare SIM7600G-H 4G Dongle (optional, dearer) | Same, plus its own GPS | US$101.99 at [waveshare.com](https://www.waveshare.com/sim7600g-h-4g-dongle.htm), or about NZ$139-179 plus shipping on Fruugo NZ | The 4G anti-theft work's first pick. Worth it only if we want a GPS fix that keeps working when the Pi's own GPS puck is unplugged or cut. Goes inside the Pi box |
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
| Phone gamepad grip | Razer Kishi V3 NZ$167.58 | GameSir G8 Galileo ~NZ$73-82 on AliExpress | **Yes**, about half |
| AI HAT+ 2 (later) | ~NZ$423 | Core Electronics ~NZ$357-373 landed | **Yes**, when the time comes |
| Everything small | | | Not worth splitting: savings would be smaller than a shipping fee |

**Note on "landed" prices from Australia:** Core's prices include Australian GST (10%). For
orders to NZ under NZ$1,000 the overseas shop normally charges NZ GST (15%) instead. I couldn't
confirm which they do, so check the total at checkout.

Not checked, or nothing found: nicegear, MicroCentre, The Warehouse, Pakronics NZ, PriceSpy NZ.
