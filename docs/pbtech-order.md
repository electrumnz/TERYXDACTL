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
| | **PB Tech subtotal** | | | | **NZ$584.85** | | |
| 8 | [Micro HDMI to HDMI adaptor](https://jaycar.co.nz/micro-hdmi-plug-to-hdmi-socket-adaptor/p/PA3649) | Jaycar | PA3649 | 1 | NZ$20.90 | Checked 17 Nov | PB Tech's [Vention cable VNT1306](https://www.pbtech.co.nz/product/VNT1306/Vention-VAA-D03-B200-Micro-HDMI-Cable---2m---Black) (NZ$12.41) has no stock until about 28 Jan. Use with any normal HDMI cable you've got |
| 9 | [30 mm 5V fan](https://www.jaycar.co.nz/5vdc-30mm-thin-2-wire-fan/p/YX2500) | Jaycar | YX2500 | 1 | NZ$31.90 | Checked 17 Nov | Pi box lid. **Still worth it without the AI HAT**, see "Cooling" below |
| 10 | [12-way fuse block](https://www.jaycar.co.nz/12-way-fuse-block-with-bus-bar/p/SZ2032) | Jaycar | SZ2032 | 1 | NZ$53.90 | Checked 17 Nov | |
| | **Jaycar subtotal** | | | | **NZ$106.70** | | |
| | **Buy tomorrow total** | | | | **about NZ$692** | | NZ$611 if the camera is out of stock |

**CarPlay dongle, if you want it now:** [Audio City](https://www.audiocity.co.nz/ottocast/carlinkit-android-system-to-wireless-apple-carplay-android-auto-dongle.html)
(Auckland and Christchurch) lists a "Carlinkit Android system to wireless CarPlay / Android Auto
dongle" at **NZ$180** (was NZ$199), in stock. That name fits the right type, but the page gives
**no model number**, so ring them first and ask: "Is it the CPC200-CCPA that uses the Autokit
app?" If yes, it's about NZ$60 dearer than ordering online but you have it now with NZ returns.
If no or not sure, order online (next section). It's not in the totals below either way.
**Not these:** the Carlinkit 5.0 / 2Air at Mighty Ape, or the MINIX CA525 at PB Tech (see
"Getting the right CarPlay dongle").

## Order online this week (not in NZ shops)

| Part | Where | Qty | Price | Notes |
|---|---|---|---|---|
| **Carlinkit CPC200-CCPA** (also sold as "Autokit") CarPlay / Android Auto dongle | [Carlinkit's Autokit store](https://autokitcarplay.com/products/autokit-ccpa-wireless-carplay-dongle-special-for-android-head-unit), or AliExpress | 1 | US$65 (~NZ$118 at 1.822) on the store. AliExpress listings US$45-66 (search results) | Only if Audio City's one turns out not to be the CCPA. PB Tech and Mighty Ape don't have the right type. See "Getting the right CarPlay dongle" below |
| [Seeed MCP2515 + SN65HVD230 CAN board](https://core-electronics.com.au/seeed-studio-can-bus-breakout-board-for-xiao-and-qt-py-mcp2515-controller-sn65hvd230-transceiver-chip.html) | Core Electronics (AU) | **4** | AU$18.45 each (~NZ$91 for 4) | Pi, control box, sniffer, and **new: the Pico's own CAN link to the Toyota Aqua power steering column** ([`power-steering-wrecker.md`](power-steering-wrecker.md)). Check the crystal |
| [MCP23017 board](https://core-electronics.com.au/catalog/product/view/sku/WS-15391) | Core Electronics (AU) | 1 | AU$10.90 (~NZ$13) | Control box inputs and relays |
| [DFRobot USB GPS TEL0138](https://core-electronics.com.au/catalog/product/view/sku/TEL0138) | Core Electronics (AU) | 1 | AU$21.05 (~NZ$26) | Search result. Or [RS NZ](https://nz.rs-online.com/web/p/gnss-gps-modules/2473251) NZ$30.85 |
| [Pololu D36V50F5 5V 5.5A regulator](https://core-electronics.com.au/catalog/product/view/sku/POLOLU-4091) | Core Electronics (AU) | 1 | AU$90.11 (~NZ$111) | Powers the Pi from the 12V battery. Big enough for the AI HAT later |
| Core Electronics shipping | | | ~NZ$15-20 | Check at checkout |
| [Mini560 5V 5A buck](https://sparks.gogo.co.nz/catalog/DC-Power-260/Fixed-Output-Step-Down-Converter-Out-5v-up-to-5A-Continuous-In-7-20v-1009.html) | Gogo:Tronics | 2 | NZ$2.95 each | Pico control box power and a spare |
| [1.5KE18A TVS diode](https://nz.element14.com/stmicroelectronics/1-5ke18a/diode-tvs-1-5kw-18v/dp/9884831) | element14 NZ | 2 | NZ$2.24 each | Spike clamp on the dash 12V |
| [Narva 7-pin flat socket with reed switch 82043BL](https://narva.com.au/products/narva-7-pin-flat-quickfit-trailer-socket-with-reed-switch-for-use-with-normally-closed-circuits-1-pack) | Narva stockists | 1 | **Not priced** | Trailer detect |
| BTS7960 x2, 8-ch opto board, MOSFET board | AliExpress | | **Not priced** | See `shopping-list.md` section 6 |
| | | | **about NZ$388** | Priced items, with the dongle at NZ$118 |

AUD to NZD at 1.234 (Wise, 17 Nov). USD to NZD at 1.822 (Wise, 18 Nov, no time shown on the
page). The Carlinkit store may add NZ GST or shipping at checkout, so allow up to about NZ$136.

## Separate pickup

| Part | Where | Price | Notes |
|---|---|---|---|
| Toyota Aqua power steering column, ECU 89650-52B51 | Dodson's, Trade Me | about NZ$115 | Picking up 19 Nov. A cheap gamble, see [`power-steering-wrecker.md`](power-steering-wrecker.md). Needs the 4th CAN board above to bench test |

## Totals

| | NZ$ |
|---|---|
| Buy tomorrow | ~692 |
| Order online this week | ~388 |
| Aqua column | ~115 |
| **Everything priced** | **about NZ$1,195** |

Not counted: the Narva socket, AliExpress parts, trailer camera bits, and everything under "Later".
That's about NZ$160 less than yesterday's list, mostly from dropping the AI HAT+ 2 (NZ$423)
and adding the dongle (NZ$118), the 4th CAN board (NZ$23) and the column (NZ$115).

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
| **Waveshare SIM7600G-H 4G Dongle** (optional) | Anti-theft tracking and remote access | US$101.99 at [waveshare.com](https://www.waveshare.com/sim7600g-h-4g-dongle.htm), or about NZ$139-179 plus shipping on Fruugo NZ | Picked by the 4G anti-theft work. Not at PB Tech. Goes inside the Pi box |
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
| CarPlay dongle | Not stocked (CA525 is the wrong type) | Audio City NZ$180 (model to confirm), Carlinkit store US$65 (~NZ$118), AliExpress US$45-66 | Audio City if they confirm CCPA and you want it now. Otherwise the Carlinkit store (1-year warranty, 30-day returns) |
| AI HAT+ 2 (later) | ~NZ$423 | Core Electronics ~NZ$357-373 landed | **Yes**, when the time comes |
| Everything small | | | Not worth splitting: savings would be smaller than a shipping fee |

**Note on "landed" prices from Australia:** Core's prices include Australian GST (10%). For
orders to NZ under NZ$1,000 the overseas shop normally charges NZ GST (15%) instead. I couldn't
confirm which they do, so check the total at checkout.

Not checked, or nothing found: nicegear, MicroCentre, The Warehouse, Pakronics NZ, PriceSpy NZ.
