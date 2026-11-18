# Shopping list for Thursday 19 November (PB Tech and the rest)

Updated **18 November 2026** (NZ time). Prices are NZ$ incl GST. "Checked 17 Nov" means I
opened the shop's page then. "Search result" means the shop's page wouldn't open for me on
18 Nov (PB Tech blocks my requests), so the price came from a search engine's copy of the
page and **may be out of date**. Check each link before you pay. Why each part is needed:
[`shopping-list.md`](shopping-list.md). Spreadsheet copy: [`pbtech-order.csv`](pbtech-order.csv).

**What changed today:** the AI HAT+ 2 is off the list for now (moved to "Later"), the CarPlay
dongle is on, a fourth CAN board is added for the power steering column, and the 4G modem
and video SSD are listed as "later". The Pi box stays sized for the AI HAT. Later on 18 Nov: the Pi box went sealed and fanless for wash-downs, so the 30 mm fan and the Active Cooler are out and heatsink parts are in the AliExpress cart.

## Buy tomorrow (in store or click and collect)

| # | Part | Shop | SKU | Qty | Price | Price from | Stock / notes |
|---|---|---|---|---|---|---|---|
| 1 | [Raspberry Pi 5 8GB](https://www.pbtech.co.nz/product/SEVRBP0502/Raspberry-Pi-5-8GB-LPDDR4-24GHz-Quad-Core-ARM-Cort) | PB Tech | SEVRBP0502 | 1 | NZ$371.39 | Checked 17 Nov | Was on order, ships about 30 Nov. Ask in store if any have come in. A search result showed NZ$254.15, maybe an old price |
| 2 | ~~[Raspberry Pi Active Cooler](https://www.pbtech.co.nz/product/SEVRBP0531)~~ | PB Tech | SEVRBP0531 | 0 | ~~NZ$11.21~~ | Checked 17 Nov | **Not now (18 Nov).** The Pi box is now sealed and fanless: an aluminium pillar takes the chip's heat to a heatsink on the outside of the lid ([`pi-box-cooling.md`](pi-box-cooling.md)). Buy it later with the AI HAT. Keep your passive heatsink for the bench |
| 3 | [Raspberry Pi A2 SD card 128GB](https://www.pbtech.co.nz/product/SEVRBP0538/Raspberry-Pi-Official-A2---Class-UltraSD-Card-128G) | PB Tech | SEVRBP0538 | 1 | NZ$47.32 | Search result | In stock when indexed |
| 4 | [Camera Module 3 Wide](https://www.pbtech.co.nz/product/SEVRBP0398/Raspberry-Pi-Official-Camera-Module-3-Wide-Version) | PB Tech | SEVRBP0398 | 1 | NZ$80.71 | Search result | **Out of stock** when indexed. Alternative: [element14 NZ SC0874](https://nz.element14.com/raspberry-pi/sc0874/rpi-wide-camera-mod-3-wide-lens/dp/4132320) ~NZ$69, also out then. Not needed for the first bench tests, so skip it if there's none |
| 5 | [Pi 5 camera cable 200 mm](https://www.pbtech.com/pacific/product/SEVRBP0541) | PB Tech | SEVRBP0541 | 1 | ~NZ$2.12 | Search result | Only with the camera |
| 6 | [Raspberry Pi Pico 2, 5-pack](https://www.pbtech.co.nz/product/SEVRBP0628/Raspberry-Pi-Kit-Pack-Microcontrollers-Board---Pic) | PB Tech | SEVRBP0628 | 1 | NZ$47.20 | Checked 17 Nov | In stock. Control box, CAN sniffer, power steering bench test, 2 spares |
| 7 | [Raspberry Pi 27W USB-C power supply](https://www.pbtech.co.nz/product/SEVRBP0512) | PB Tech | SEVRBP0512 | 1 | ~NZ$24.90 | Search result | Bench only. In the Teryx the Pololu regulator powers the Pi |
| 8 | [Raspberry Pi official micro HDMI to HDMI cable, 1 m, white](https://www.pbtech.co.nz/product/SEVRBP0207/Raspberry-Pi-Official-1M-White-Cable-Micro-HDMI-to) | PB Tech | SEVRBP0207 | 1 | NZ$11.80 | Search result | Stock not confirmed. Same cable in black: [SEVRBP0262](https://www.pbtech.co.nz/product/SEVRBP0262/Raspberry-Pi-Official-1M-Black-Cable-Micro-HDMI-to) ~NZ$11.10. If neither is in, [Jaycar PA3649 adaptor](https://jaycar.co.nz/micro-hdmi-plug-to-hdmi-socket-adaptor/p/PA3649) NZ$20.90 plus any HDMI cable. Use a **cable**, not a plug-in adaptor: a stiff adaptor hanging off the micro HDMI socket will work loose or crack the socket on the trail. The screen sits right over the Pi box, so 1 m is plenty; zip-tie the cable down close to the plug. Stay with HDMI, not VGA: the Pi has no VGA out, so it would need an active converter box, which is one more thing to fail and gives a softer picture. A printed clamp for the plug in the Pi box is a follow-up |
| | **Buy tomorrow total (all PB Tech)** | | | | **about NZ$585** | | NZ$505 if the camera is out of stock |

Everything for tomorrow is at PB Tech now. The fuse block moved to the AliExpress cart (Sam,
18 Nov), as it isn't needed until wiring the Teryx. The lid fan and the Active Cooler are off the
list: the Pi box is now sealed for wash-downs with a heatsink on the outside, no fan (see
"Cooling" below).

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
| **8-channel 5V relay board, opto-isolated, JD-VCC jumper** (Songle SRD-05VDC type, 10 A contacts with NO and NC) | "8 channel 5V relay module optocoupler JD-VCC" | 1 | ~US$8.29 (~NZ$15). [Treedix 8-channel listing](https://reach.dog/shop/treedix-official/products/treedix-dc-5v-8-channel-relay-board-module-isolated-optocoupler-high-and-low-level-h-l-level-trigger-module-triggered-compatible-with-arduino-raspberry-pi-8-channel); a [similar board](https://sigmanortec.ro/en/5v-relay-module-8-channels-with-optocoupler-high-and-low-trigger-settable) lists 10 A at 30 V DC | Relays 1-8 in the wiring plan. **Must be mechanical relays** (the blue cubes), not the black solid state ones. Look for a **JD-VCC / VCC / GND header with a removable jumper**: that's what keeps the Pico side isolated. Board VCC goes to the Pico's 3.3 V and JD-VCC to the 5 V buck, so a 3.3 V output switches it cleanly. Most are active low, which the firmware already expects (setting 18). The MCP23017 starts up with its outputs floating, so the relays stay off at power-up. Keep loads under about 5 A for long life |
| **4-channel 5V relay board**, same type | "4 channel 5V relay module optocoupler JD-VCC" | 1 | ~US$5 (~NZ$9), my estimate | Relays 9 and 10 (steering enable, drive lock on the NC contact) plus 2 spares. Same checks as the 8-channel |
| **Blade fuse block, 20-way, with cover and negative bus** | "20 way blade fuse box negative bus cover" | 1 | ~US$15-25 (~NZ$27-46), my estimate. AliExpress search pages show bait prices like [US$1.09](https://www.aliexpress.com/w/wholesale-Modular%20Fuse%20Block.html); a similar 12-way Nilight is [US$22.99 at Walmart](https://www.walmart.com/c/kp/electrical-box-bus) | The wiring plan has **13 fused circuits** (`config/wiring.yaml`, F1-F13), so get a 20-way for spares. Look for: clip-on cover (ideally a seal), built-in negative bus, 30 A per way and 100 A total, studs or screw terminals for the feed (not a push-on spade), and blown-fuse LEDs are a bonus. A proper brand (Blue Sea, Narva) is better if it'll live where it gets wet |
| **Finned heatsink, 100 x 100 x 40 mm, black anodised** | "heatsink 100x100x40 aluminium" | 1 | ~NZ$20, my estimate | Pi box lid, outside. **Flat base 5 mm or thicker** (it gets tapped M3). Straight fins, not pins. The rated version is the Fischer SK 92/100 SA (1.4 K/W) from [element14 NZ](https://nz.element14.com/fischer-elektronik/sk-92-100-sa/heat-sink-100mm-1-4-c-w/dp/4621580) if you'd rather. Replaces the 30 mm fan, which is gone |
| Thermal pad, 1 mm, 4 W/mK or better | "thermal pad 1mm 6W/mK" | 1 sheet | ~NZ$5, my estimate | 20 x 20 mm piece on the Pi's chip, under the pillar |
| Solid aluminium block, 20 x 20 mm, about 50 mm long | "aluminium block 20x20x50" | 1-2 | ~NZ$5, my estimate | The pillar from the Pi's chip to the lid. Or any 20 x 20 solid offcut. Cut to about 45.3 mm |
| Thermal paste, small tube | "thermal paste" | 1 | ~NZ$3, my estimate | Lid plate to heatsink |
| M12 x 1.5 breather vent plug, membrane type | "M12 waterproof breathable vent plug" | 2 | ~NZ$4, my estimate | Pi box bottom wall. Stops the sealed box sucking in water as it cools. One spare |
| **4G module board, SIMCom A7670SA** (Sam's pick: a bare board to solder in, not a stick) | "A7670SA core board B28" | 1 | ~US$15.46 (~NZ$28). [Listing with B1/B2/B3/B4/B5/B7/B8/B28/B66](https://www.aliexpress.us/item/3256808314829525.html) | **Must be the A7670SA**, and the listing must show **B28** (700 MHz, the NZ country band). The A7670E and some "A7670SA" listings only have B1/B3/B5/B7/B8/B20, no B28 ([SIMCom table via manuals.plus](https://manuals.plus/ae/1005008976290540)). Cat-1 LTE, about 10 Mbps down: plenty for light data and SMS. SIM slot and TTL UART on the board. Talks plain AT commands, so SMS is easy on Linux. **Over UART only it does texts, WHERE and LOCK, but the data is far too slow for live cameras or RC over 4G.** Better buy if you can find one: an A7670SA board whose USB-C goes to the module's **own USB pins** (not a CH340-type USB-serial chip), so it plugs into the Pi over USB at full speed. **Pick the GPS option ("FASE" or "GNSS"; "LASE" has no GPS)**: it can track with the key off for anti-theft. Keep the TEL0138 puck for the dash until the module's GPS proves itself. Skip the flat FPC antenna option. Sam found a candidate at ~NZ$34, still to check against these points |
| 4-channel BSS138 level shifter | "BSS138 level shifter 4 channel" | 1 | ~NZ$2 (estimate) | **Probably not needed.** Sam's board has its own regulator and TTL serial pins. Before wiring T to the Pi, power the board and measure the T pin against G with a multimeter: about 3.3 V is fine straight to the Pi; 5 V or 1.8 V needs this shifter. It's NZ$2, so worth having in the cart anyway |
| Active GPS antenna, IPEX/u.FL (only with the GPS version) | "active GPS antenna ipex" | 1 | ~NZ$8 (estimate) | Check the board powers an active antenna |
| LTE antenna, wideband 698-2700 MHz, u.FL to SMA lead | "4G LTE antenna 698-2700 SMA" | 1 | ~NZ$12 (estimate) | The little PCB stick antennas are poor at 700 MHz (B28), which is what you'll be on out in the country. Mount it outside the metal, near the GPS puck |
| | | | **about NZ$322** | Dongle NZ$65, amp NZ$82, 2 x BTS7960 NZ$24, fuse block ~NZ$40, relay boards ~NZ$24, Pi box heatsink parts ~NZ$37, 4G board, level shifter, LTE and GPS antennas ~NZ$50. Opto and MOSFET boards on top |

**The 8-channel solid state relay board you've got coming won't work here.** Those boards use Omron G3MB-202P relays, which are for AC only. On 12 V DC they switch on but never switch off again until the power is cut ([Omron FAQ](https://www.ia.omron.com/support/faq/answer/18/faq02101/index.html)). Keep it for a mains project, or send it back if you can.

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
| [Mini560 5V 5A buck](https://sparks.gogo.co.nz/catalog/DC-Power-260/Fixed-Output-Step-Down-Converter-Out-5v-up-to-5A-Continuous-In-7-20v-1009.html) | Gogo:Tronics | 2 | NZ$2.95 each | Pico control box power, and the second one powers the 4G board (5 V into its V pin). Grab a third (NZ$2.95) if you want a spare |
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
| Buy tomorrow (all PB Tech) | ~585 |
| AliExpress cart | ~322 |
| Other online orders (Core, Gogo, element14) | ~270 |
| Aqua column | ~115 |
| **Everything priced** | **about NZ$1,292** |

The amp (NZ$82) is new to the list today. Without it, it's about NZ$1,210. Not counted: blade fuses, the opto and MOSFET boards, Narva socket, trailer camera bits,
speakers and amp wiring, and everything under "Later".

## Wiring the 4G board

Sam's board (from its datasheet): a 6-pin header marked **S** (sleep), **G** (ground), **V** (power,
**5-10 V**), **K** (power key), **T** (TX out), **R** (RX in), **G** (ground). It has its own regulator, a
470 µF tantalum capacitor for the transmit peaks, a GPS antenna plug, a micro USB and runs at 115200 baud.

- **Power:** feed **V** from the spare **Mini560 5 V buck**, with both grounds joined. No separate 3.8 V
  buck or big capacitor needed: the board does that itself. **Never put raw 12 V on V**, as 10 V is its
  limit and a car's 12 V runs at 14.4 V when charging, with spikes on top.
- **Power key (K):** tied to ground on the board by default (R104), so the module starts by itself when
  power comes on. Leave it unconnected.
- **Sleep (S):** leave it unconnected for now. It can go to a spare GPIO later to save battery when parked.
- **To the Pi:** T goes to the Pi's RX (GPIO 15), R goes to the Pi's TX (GPIO 14), G to ground. **Measure
  T first** (see the level shifter row): about 3.3 V is fine straight in. The code supports this (PR #42).
  The Pi sends AT commands for SMS and can run PPP over it for light data.
- **Or always on, off a spare Pico:** the Pi is off when the key is off, so for "text the Teryx to
  lock it" while parked, the module has to stay powered from the 12V battery and something small
  has to listen. The control box Pico has no spare pins, but the Pico 5-pack has spares. A spare
  Pico 2 could run just the modem and talk to the control box over the existing CAN bus, which
  needs a **5th CAN board** (~NZ$23, Core Electronics). That's a design choice for the 4G
  anti-theft work, so it's not in the totals. Standby draw has to be checked against the 12V
  battery.

## Cooling: sealed and fanless (18 Nov)

Sam wants the Pi box to survive hosing the Teryx down, and no fan noise. So the box is now sealed:
no vents, no lid fan. The lid is a 3 mm aluminium plate (cut with the back plate) with a finned
heatsink on the outside, and a 20 x 20 mm aluminium pillar carries the Pi chip's heat straight up
to it through a thermal pad. Full write-up, sums and assembly: [`pi-box-cooling.md`](pi-box-cooling.md).

- **Active Cooler: not now.** The pillar does its job. It comes back with the AI HAT, under the HAT,
  as Raspberry Pi say. Keep your passive heatsink for the bench.
- **30 mm lid fan: gone** from the AliExpress cart. The heatsink parts are in its place.
- **Heat:** about 9 W in normal driving puts the heatsink near 56°C and the Pi chip near 62°C on a
  40°C day, well under the 80°C point where the Pi slows down. Everything flat out at once on a hot
  day just touches it. A quiet optional fan on the outside of the fins (Noctua NF-A4x10 5V PWM,
  "Later") is the fix if the logs say so, and it'll be needed with the AI HAT.

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
| GameSir G8 Galileo phone gamepad grip, USB-C (GameSir official store on AliExpress) | RC mode | US$40-45 on deals (~NZ$73-82), list [US$79.99](https://gamesir.com/collections/all-products/products/gamesir-g8-galileo) | **Not now (Sam, 18 Nov).** RC mode uses on-screen sticks until then; gamepad support stays in the code. Half the price of the Razer Kishi V3 (NZ$167.58 at PB Tech) |
| Samsung Galaxy XCover 5, second-hand, lives in the ATV as the RC remote (Android 14, 4 GB RAM / 64 GB, IP68, 5.3" screen works with gloves, swappable battery, 5 GHz wifi) | RC mode | NZ$187 on Trade Me, 90 day warranty | **Bought (Sam, 18 Nov).** Fully Kiosk Browser licence optional (price not checked). See docs/rc-beach-launch.md section 4b |
| [Raspberry Pi Active Cooler](https://www.pbtech.co.nz/product/SEVRBP0531) | Goes under the AI HAT+ 2 | NZ$11.21 at PB Tech (checked 17 Nov) | Only with the HAT. Not needed for the sealed box now |
| Noctua NF-A4x10 5V PWM 40 mm fan (optional) | Blows on the Pi box heatsink fins if it runs hot, and with the AI HAT | about NZ$22 at [Newegg NZ](https://www.newegg.com/global/nz-en/noctua-nf-a4x10-5v-pwm/p/1YF-000T-000N2) (search result) | Outside the sealed box, so the seal doesn't care. Runs off the Pi 5 fan connector (needs an adaptor), off below 50°C |
| [Raspberry Pi AI HAT+ 2](https://www.pbtech.co.nz/product/SEVRBP0446/Raspberry-Pi-5-Official-AI-Hat-2) | Camera AI, local voice assistant | ~NZ$423 PB Tech (search result), or [Core Electronics](https://core-electronics.com.au/raspberry-pi-ai-hat-plus-2.html) AU$289 (~NZ$357-373 landed) | **Not buying now.** The Pi box stays 56 mm tall for it, the Pi's PCIe slot stays free, its header stays clear (the CAN board sits on the box wall), and the Pololu regulator has the spare power |
| Huawei E3372h-607 4G USB stick (plug-in alternative to the A7670SA board in the AliExpress cart) | Anti-theft tracking, SMS and remote access | ~US$36-42 (~NZ$66-77) on eBay/AliExpress (search results), or second-hand on Trade Me | Bands 1/3/7/8/28/40, which covers Spark, One NZ and 2degrees including the 700 MHz B28 country band ([listing](https://ubbthreads.com/store/item/Huawei-E3372h-607-4G-LTE-FDD-TDD-B40-4GX-USB-Dongle-Mobile-Broadband-150Mbps-NEW_314457944618.html)). Shows up on the Pi as a plain network adaptor, no driver needed, and SMS works through its built-in web API. **Check the label under the cap says E3372h-607** (other versions like -153 or -320 miss B28), and that it's unlocked if second-hand. No GPS built in, but the Pi already has the GPS puck. Light data and SMS is all we need |
| Waveshare SIM7600G-H 4G Dongle (dearer alternative) | Same, plus its own GPS | US$101.99 at [waveshare.com](https://www.waveshare.com/sim7600g-h-4g-dongle.htm), or about NZ$139-179 plus shipping on Fruugo NZ | The 4G anti-theft work's first pick. Worth it only if we want a GPS fix that keeps working when the Pi's own GPS puck is unplugged or cut. Goes inside the Pi box |
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
| Phone gamepad grip (later) | Razer Kishi V3 NZ$167.58 | GameSir G8 Galileo ~NZ$73-82 on AliExpress | **Yes**, about half, when you get one |
| AI HAT+ 2 (later) | ~NZ$423 | Core Electronics ~NZ$357-373 landed | **Yes**, when the time comes |
| Everything small | | | Not worth splitting: savings would be smaller than a shipping fee |

**Note on "landed" prices from Australia:** Core's prices include Australian GST (10%). For
orders to NZ under NZ$1,000 the overseas shop normally charges NZ GST (15%) instead. I couldn't
confirm which they do, so check the total at checkout.

Not checked, or nothing found: nicegear, MicroCentre, The Warehouse, Pakronics NZ, PriceSpy NZ.
