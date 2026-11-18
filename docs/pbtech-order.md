# PB Tech order list (and where to save money)

Made **18 November 2026** (NZ time). Prices are NZ$ incl GST. "Checked 17 Nov" means I
opened the PB Tech page then. "Search result" means PB Tech's page wouldn't open for me on
18 Nov, so the price came from a search engine's copy of the page and **may be out of date**.
Check each link before you pay. Why each part is needed: [`shopping-list.md`](shopping-list.md).
Spreadsheet copy: [`pbtech-order.csv`](pbtech-order.csv).

## 1. PB Tech order

| # | Part | PB Tech SKU | Qty | Price | Where the price came from | Stock / notes |
|---|---|---|---|---|---|---|
| 1 | [Raspberry Pi 5 8GB](https://www.pbtech.co.nz/product/SEVRBP0502/Raspberry-Pi-5-8GB-LPDDR4-24GHz-Quad-Core-ARM-Cort) | SEVRBP0502 | 1 | NZ$371.39 | Checked 17 Nov | On order then, ships about 30 Nov. A search result on 18 Nov showed NZ$254.15, maybe an old price |
| 2 | [Raspberry Pi AI HAT+ 2](https://www.pbtech.co.nz/product/SEVRBP0446/Raspberry-Pi-5-Official-AI-Hat-2) | SEVRBP0446 | 1 | NZ$423.43 | Search result | 0 at Albany when indexed. **Cheaper at Core Electronics**, see section 3 |
| 3 | [Raspberry Pi Active Cooler](https://www.pbtech.co.nz/product/SEVRBP0531) | SEVRBP0531 | 1 | NZ$11.21 | Checked 17 Nov | In stock. Needed under the AI HAT |
| 4 | [Raspberry Pi A2 SD card 128GB](https://www.pbtech.co.nz/product/SEVRBP0538/Raspberry-Pi-Official-A2---Class-UltraSD-Card-128G) | SEVRBP0538 | 1 | NZ$47.32 | Search result | In stock when indexed |
| 5 | [Camera Module 3 Wide](https://www.pbtech.co.nz/product/SEVRBP0398/Raspberry-Pi-Official-Camera-Module-3-Wide-Version) | SEVRBP0398 | 1 | NZ$80.71 | Search result | **Out of stock** when indexed. Alternative: [element14 NZ SC0874](https://nz.element14.com/raspberry-pi/sc0874/rpi-wide-camera-mod-3-wide-lens/dp/4132320) ~NZ$69, also out then |
| 6 | [Pi 5 camera cable 200 mm](https://www.pbtech.com/pacific/product/SEVRBP0541) | SEVRBP0541 | 1 | ~NZ$2.12 | Search result (NZ$1.84, probably ex GST) | Ships today when indexed |
| 7 | [Raspberry Pi Pico 2, 5-pack](https://www.pbtech.co.nz/product/SEVRBP0628/Raspberry-Pi-Kit-Pack-Microcontrollers-Board---Pic) | SEVRBP0628 | 1 | NZ$47.20 | Checked 17 Nov | In stock. Control box, CAN sniffer, 3 spares |
| 8 | [Vention micro HDMI to HDMI 2 m](https://www.pbtech.co.nz/product/VNT1306/Vention-VAA-D03-B200-Micro-HDMI-Cable---2m---Black) | VNT1306 | 1 | NZ$12.41 | Checked 17 Nov | **No stock**, ships about 28 Jan. Now: [Jaycar PA3649 adaptor](https://jaycar.co.nz/micro-hdmi-plug-to-hdmi-socket-adaptor/p/PA3649) NZ$20.90 plus an HDMI cable |
| 9 | [Raspberry Pi 27W USB-C power supply (bench)](https://www.pbtech.co.nz/product/SEVRBP0512) | SEVRBP0512 | 1 | ~NZ$24.90 | Search result (NZ$21.65, probably ex GST) | For the bench only. In the Teryx the Pololu regulator (section 2) powers it |
| | **PB Tech total** | | | **~NZ$1,020.69** | | |

Only if the rear camera turns out to be RCA/AHD, not USB:

| Part | PB Tech SKU | Price | Notes |
|---|---|---|---|
| [EasyCAP DC60 USB video capture](https://www.pbtech.co.nz/product/SEVOEM9701) | SEVOEM9701 | NZ$28.75 | Composite (RCA) only, not AHD. Not tested on a Pi. See [`cameras.md`](cameras.md) |

## 2. Not sold at PB Tech

I couldn't find these at PB Tech. AUD to NZD at 1.234 (Wise, 17 Nov).

| Part | Where | Qty | Price | Notes |
|---|---|---|---|---|
| [Seeed MCP2515 + SN65HVD230 CAN board](https://core-electronics.com.au/seeed-studio-can-bus-breakout-board-for-xiao-and-qt-py-mcp2515-controller-sn65hvd230-transceiver-chip.html) | Core Electronics (AU) | 3 | AU$18.45 each (~NZ$68 for 3) | One for the Pi (instead of the CAN HAT, which can't stack over the AI HAT's heatsink), one for the control box, one for the sniffer. Check the crystal |
| [MCP23017 board](https://core-electronics.com.au/catalog/product/view/sku/WS-15391) | Core Electronics (AU) | 1 | AU$10.90 (~NZ$13) | Control box inputs and relays |
| [DFRobot USB GPS receiver TEL0138](https://core-electronics.com.au/catalog/product/view/sku/TEL0138) | Core Electronics (AU) | 1 | AU$21.05 (~NZ$26) | Search result. Or [RS NZ](https://nz.rs-online.com/web/p/gnss-gps-modules/2473251) NZ$30.85. See `shopping-list.md` 4b |
| [Pololu D36V50F5 5V 5.5A regulator](https://core-electronics.com.au/catalog/product/view/sku/POLOLU-4091) | Core Electronics (AU) | 1 | AU$90.11 (~NZ$111) | Powers the Pi from the 12V battery |
| Core Electronics shipping to NZ | | | ~AU$12-16 (~NZ$15-20) | From their product page, check at checkout |
| [30 mm 5V fan](https://www.jaycar.co.nz/5vdc-30mm-thin-2-wire-fan/p/YX2500) | Jaycar | 1 | NZ$31.90 | Pi box lid. Needed with the AI HAT |
| [12-way fuse block](https://www.jaycar.co.nz/12-way-fuse-block-with-bus-bar/p/SZ2032) | Jaycar | 1 | NZ$53.90 | |
| [Mini560 5V 5A buck](https://sparks.gogo.co.nz/catalog/DC-Power-260/Fixed-Output-Step-Down-Converter-Out-5v-up-to-5A-Continuous-In-7-20v-1009.html) | Gogo:Tronics | 2 | NZ$2.95 each | Pico control box power and a spare |
| [1.5KE18A TVS diode](https://nz.element14.com/stmicroelectronics/1-5ke18a/diode-tvs-1-5kw-18v/dp/9884831) | element14 NZ | 2 | NZ$2.24 each | Spike clamp on the dash 12V |
| [Narva 7-pin flat socket with reed switch 82043BL](https://narva.com.au/products/narva-7-pin-flat-quickfit-trailer-socket-with-reed-switch-for-use-with-normally-closed-circuits-1-pack) | Narva stockists | 1 | **Not priced** | Trailer detect |
| BTS7960 x2, 8-ch opto board, MOSFET board | AliExpress | | **Not priced** | See `shopping-list.md` section 6 |
| | **Known total outside PB Tech** | | **~NZ$330-335** | Includes Core shipping |

**Grand total, everything priced: about NZ$1,355.** Not counted: the Narva socket, AliExpress
parts, trailer camera bits, the capture dongle and a powered USB hub.

## 3. Cheaper places, part by part

| Part | PB Tech | Best other I found | Better? |
|---|---|---|---|
| Pi 5 8GB | NZ$371.39 | [Core Electronics](https://core-electronics.com.au/raspberry-pi-5-model-b-8gb.html) AU$283.85 (~NZ$350-366 landed, see note) + shipping. [Mighty Ape](https://www.mightyape.co.nz/mn/buy/mighty-ape-raspberry-pi-5-101-38626121/) NZ$624.98 | **No.** About the same once shipping is on. Buy at PB Tech for the local warranty |
| AI HAT+ 2 | ~NZ$423.43 | [Core Electronics](https://core-electronics.com.au/raspberry-pi-ai-hat-plus-2.html) AU$289 (~NZ$357-373 landed), limit 1 per customer. [Pakronics AU](https://pakronics.com.au/products/raspberry-pi-ai-hat-2-rpi-sc2166) AU$352, out of stock | **Yes, about NZ$50-65 cheaper at Core**, and it can go in the same parcel as the CAN and power bits, so no extra shipping |
| Camera Module 3 Wide | ~NZ$80.71, out of stock | element14 NZ ~NZ$69, out of stock | Whoever has stock first |
| Everything small (cooler, card, cable, Pico, PSU) | | Not worth splitting: the savings would be smaller than a shipping fee | **No** |

**Note on "landed" prices from Australia:** Core's prices include Australian GST (10%). For
orders to NZ under NZ$1,000 the overseas shop normally charges NZ GST (15%) instead, so the
low end assumes they swap AU GST for NZ GST and the high end assumes they don't take the AU
GST off. I couldn't confirm which they do. Check the total at checkout before paying.

**So the cheapest sensible way:**

1. **PB Tech:** Pi 5 8GB, Active Cooler, SD card, Camera Module 3 Wide, camera cable, Pico 2
   5-pack, micro HDMI cable, 27W bench supply.
2. **Core Electronics, one order:** AI HAT+ 2, 3 CAN boards, MCP23017, Pololu regulator, GPS.
3. **Jaycar:** fan and fuse block (and the micro HDMI adaptor if PB Tech's cable is still out).
4. **Gogo:Tronics and element14:** the tiny bits, or skip and grab them with something else.

That saves roughly **NZ$50-65** against buying the AI HAT+ 2 at PB Tech. Everything else is
already at its cheapest place, as far as I could find.

Not checked, or nothing found: nicegear (only old Pi 3/4 pages turned up), MicroCentre,
The Warehouse, Pakronics NZ, and PriceSpy NZ for the Pi 5 8GB.
