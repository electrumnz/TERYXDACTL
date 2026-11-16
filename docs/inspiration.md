# Inspiration: open-source projects worth learning from

Projects where people have already solved bits of what we're building: the dash
UI, CAN decoding of Chinese motor controllers, the Pico control box, accessory
control and OTA updates.

Checked on 2026-11-16. "Stars" and "Last push" come from GitHub on that date,
so treat them as a rough guide to how alive a project is.

## Licence rule for this repo

This repo is **MIT**. That decides what we can do with each project:

| Licence | What we can do | Marked as |
|---|---|---|
| MIT, BSD, Apache-2.0 | Copy or adapt code. Keep their copyright notice next to anything we copy (e.g. in a `THIRD_PARTY.md` or the file header). | **Copy OK** |
| LGPL | Use it as a separate library or tool (install it, link to it, call it). Don't paste its code into our files. | **Use as a tool/library** |
| GPL, AGPL | Run it as a separate tool on the bench or Pi is fine. Read it for ideas, then write our own. Never paste its code into this repo. | **Ideas only** |
| No licence file | All rights reserved by default. Read for ideas, don't copy. | **Ideas only** |

Also: nothing personal in the repo (no names, addresses, phone numbers, wifi
passwords, VIN, rego, home location in GPS logs or screenshots). CAN logs we
commit should be trimmed to the frames we need.

---

## 1. CAN sniffing and decoding (for the Shinegle controller)

There is **no public code for Shinegle controllers** (searched GitHub on
2026-11-16, zero hits). The nearest relatives are other Chinese controllers
(Votol, Kelly, Fardriver), and people decode those the same way we'll do
Shinegle: plug in, record, change one thing at a time, spot which bytes move.

| Project | Licence | Activity | What we can borrow |
|---|---|---|---|
| [collin80/SavvyCAN](https://github.com/collin80/SavvyCAN) | MIT, **Copy OK** | 1.9k stars, pushed 2026-11-04 | **The main tool for step 4.** Record, filter, graph signals, "sniffer" view that highlights changing bits, DBC editor, replay. Runs on a laptop or the Pi. Works with SocketCAN adaptors. |
| [trnila/rp2040-can-mcp2515](https://github.com/trnila/rp2040-can-mcp2515) | no licence, **Ideas only** (fine to just flash and use) | 40 stars, pushed 2025-06 | Turns a **Pico + MCP2515 into a USB CAN adaptor** (gs_usb, shows up as `can0` on Linux). Means a spare Pico + MCP2515 becomes our sniffer for SavvyCAN with no extra kit to buy. |
| [collin80/ESP32RET](https://github.com/collin80/ESP32RET) | MIT, **Copy OK** | 419 stars, pushed 2026-10-22 | The GVRET serial protocol SavvyCAN talks. If we ever want the Pico to stream CAN to SavvyCAN over USB serial, this is the reference. |
| [linux-can/can-utils](https://github.com/linux-can/can-utils) | GPL-2.0 / BSD mix, **use as a tool** | 3k stars, pushed 2026-10-14 | `candump -l`, `cansniffer -c` (live view of changing bytes), `canplayer` (replay logs into the sim). Install on the Pi with `apt install can-utils`. |
| [cantools/cantools](https://github.com/cantools/cantools) | MIT, **Copy OK** | 2.3k stars, pushed 2026-11-16 | Python DBC encode/decode. Write what we learn into `shinegle.dbc` and `teryx.dbc`, then the dash, the sim and tests all decode from one file. Has `cantools monitor` for a live decoded view. |
| [hardbyte/python-can](https://github.com/hardbyte/python-can) | LGPL-3.0, **use as a library** | 1.6k stars, pushed 2026-11-15 | Standard Python CAN library (SocketCAN, virtual bus, log files). `pip install` it, don't copy it. |
| [commaai/opendbc](https://github.com/commaai/opendbc) | MIT, **Copy OK** | 3.6k stars, pushed 2026-11-16 | Hundreds of real car DBC files. Good examples of how to lay out signals, scaling, counters and checksums. |
| [MatthewKuKanich/CAN_Commander](https://github.com/MatthewKuKanich/CAN_Commander) | no licence, **Ideas only** | 1.1k stars, pushed 2026-11-15 | Reverse-engineering workflow ideas: filtering, "what changed when I pressed this" capture. |
| [brent-stone/CAN_Reverse_Engineering](https://github.com/brent-stone/CAN_Reverse_Engineering) | GPL-3.0, **Ideas only** | 460 stars, pushed 2024-04 | Automatic signal boundary finding from logs. Useful idea if manual decoding gets slow. |
| [CaringCaribou/caringcaribou](https://github.com/CaringCaribou/caringcaribou) | GPL-3.0, **use as a tool** | 975 stars, pushed 2026-06 | Can scan for UDS / diagnostic services. Handy if the Shinegle programmer talks a diagnostic protocol rather than plain broadcast frames. |

### Chinese controller decoding, closest to Shinegle

| Project | Licence | Activity | What we can borrow |
|---|---|---|---|
| [jackhumbert/fardriver-controllers](https://github.com/jackhumbert/fardriver-controllers) | MIT, **Copy OK** | 62 stars, pushed 2026-01 | Write-up of Fardriver's protocol and register map. Good model for how to document Shinegle as we decode it. |
| [zexry619/votol-esp32-can-bus](https://github.com/zexry619/votol-esp32-can-bus) | no licence, **Ideas only** | 25 stars, pushed 2026-04 | Reads all Votol EM100 data over CAN. Shows the typical layout: a request frame, then status frames with RPM, voltage, current, temps, fault bits. |
| [virgilm/votol_bt_interface](https://github.com/virgilm/votol_bt_interface) | unclear, **Ideas only** | 9 stars, pushed 2025-11 | Votol CAN to Bluetooth bridge. Same idea as our Pi reading the controller. |
| [EV-Project/KellyCAN](https://github.com/EV-Project/KellyCAN) | no licence, **Ideas only** | old (2015) | Kelly's request/response CAN scheme. Some Chinese controllers only answer when asked, so if Shinegle goes quiet without its dash, try replaying what the dash sends. |
| [intute-ai-811/kelly-brake-control](https://github.com/intute-ai-811/kelly-brake-control) | no licence, **Ideas only** | pushed 2026-04 | Decodes speed, motor current and throttle from Kelly CAN. |
| [evcollector/kajo-dash](https://github.com/evcollector/kajo-dash) | GPL-3.0, **Ideas only** | pushed 2026-10 | Small VESC/Fardriver dash. Good list of which values riders actually want on screen. |

**What this means for step 4 (decode Shinegle):**
1. Sniffer = spare Pico + MCP2515 flashed with the gs_usb firmware above, or the Pi's own CAN HAT.
2. Find the bitrate first: try 250k and 500k, then 125k and 1M, in listen-only mode so we never ACK or disturb the bus.
3. Record with the Shinegle dash on, then off. If frames stop without the dash, the controller is request/response (Kelly style) and we need to copy what the dash sends.
4. Use the Shinegle programmer while recording. Each setting it reads tells us an ID and a value we already know.
5. Change one thing at a time (throttle, brake, direction switch, key) and watch SavvyCAN's sniffer.
6. Write findings straight into `shinegle.dbc` with cantools, and the dash picks them up.

---

## 2. EV conversion control (VCU logic, safety, parameter systems)

| Project | Licence | Activity | What we can borrow |
|---|---|---|---|
| [damienmaguire/Stm32-vcu](https://github.com/damienmaguire/Stm32-vcu) (ZombieVerter VCU) | GPL-3.0, **Ideas only** | 268 stars, pushed 2026-11-14 | Real-world VCU state machine: startup checks, precharge, run, fault, limp. How it handles lost CAN messages and timeouts is a good pattern for the Pico's failsafe rules. |
| [jsphuebner/stm32-sine](https://github.com/jsphuebner/stm32-sine) (OpenInverter) | GPL-3.0, **Ideas only** | 210 stars, pushed 2026-09 | Inverter firmware. Read for its error handling and its "spot values" list (live readings) vs "parameters" (settings) split. |
| [jsphuebner/libopeninv](https://github.com/jsphuebner/libopeninv) | LGPL-3.0, **Ideas only** (it's written for STM32, not usable as-is) | pushed 2026-10 | Parameter system with IDs, min/max/default, saved to flash, readable and writable over CAN and serial. Copy the **idea** for our 0x704 settings message. |
| [jsphuebner/esp32-web-interface](https://github.com/jsphuebner/esp32-web-interface) | no licence detected, **Ideas only** | pushed 2026-09 | Web page that edits OpenInverter parameters and updates firmware over wifi. Same shape as our Pi updating the Pico. |
| [vedderb/bldc](https://github.com/vedderb/bldc) (VESC firmware) | GPL-3.0, **Ideas only** | 3.6k stars, pushed 2026-11-16 | VESC's CAN status messages (packed, scaled, fixed rate) are a clean example of a telemetry layout. Also good fault code naming. |
| [vedderb/vesc_tool](https://github.com/vedderb/vesc_tool) | GPL-3.0, **Ideas only** | 1.1k stars, pushed 2026-11-16 | Qt/QML app with gauges, live plots and firmware upload. Ideas for our settings and diagnostics screens. |
| [dalathegreat/Battery-Emulator](https://github.com/dalathegreat/Battery-Emulator) | GPL-3.0, **Ideas only** | 3k stars, pushed 2026-11-16 | Decodes dozens of EV battery packs over CAN. Good reference if the Shinegle pack/BMS has its own CAN traffic. |
| [openvehicles/Open-Vehicle-Monitoring-System-3](https://github.com/openvehicles/Open-Vehicle-Monitoring-System-3) | MIT (most of it), **Copy OK** with care, check each file | 880 stars, pushed 2026-11-15 | Big one. Vehicle "modules" that decode many EVs' CAN, a shared "metrics" model (speed, SoC, temps), web dashboard, OTA. Its metrics naming is a nice model for our signal list. |
| [victronenergy/dbus-canopen-motordrive](https://github.com/victronenergy/dbus-canopen-motordrive) | no licence detected, **Ideas only** | pushed 2026-11-02 | Reads Sevcon/Curtis controllers over CANopen. Only relevant if Shinegle turns out to speak CANopen. |

---

## 3. Dash UI (Pi 5, touch, Tesla-like)

Most "Tesla dashboard" repos on GitHub have **no licence**, so they're for
looks only. The useful thing to take from them is layout and feel, not code.

| Project | Licence | Activity | What we can borrow |
|---|---|---|---|
| [microeinhundert/tesla-dashboard](https://github.com/microeinhundert/tesla-dashboard) | no licence, **Ideas only** | 52 stars, old (2018) | HTML/CSS/Vue recreation of the Model S/X screen. Layout ideas: big speed, side car view, card-style controls. |
| [cppqtdev/Tesla-Dashboard-UI-3](https://github.com/cppqtdev/Tesla-Dashboard-UI-3) | no licence, **Ideas only** | 43 stars, pushed 2024-09 | Qt 6 / QML Tesla-style layout. Shows how to do the "car in the middle, controls round it" look in QML. |
| [cppqtdev/Qt-HMI-Display-UI](https://github.com/cppqtdev/Qt-HMI-Display-UI) | no licence, **Ideas only** | 57 stars | Gauges and cluster screens in QML. |
| [cjtejada/QtDigitalInstrumentCluster](https://github.com/cjtejada/QtDigitalInstrumentCluster) | no licence, **Ideas only** | 70 stars | Qt cluster fed by live data (OBD). Pattern for C++ data model to QML. |
| [MHamiid/Automotive_Instrument_Cluster_HMI](https://github.com/MHamiid/Automotive_Instrument_Cluster_HMI) | Apache-2.0, **Copy OK** | small, 2023 | Qt/QML cluster with C++ backend and a simulator feeding it. Small, but we can actually reuse bits. |
| [Lindu666666/In-vehicle-virtual-cockpit-dashboard-system](https://github.com/Lindu666666/In-vehicle-virtual-cockpit-dashboard-system) | MIT, **Copy OK** | pushed 2026-06 | Closest match to our design: **Pi + CAN + DBC parsing + data middle layer + QML gauges + fault/alarm engine + black box logging**. Worth reading end to end. (Docs are in Chinese.) |
| [rdoromaljr/can-dash-lab](https://github.com/rdoromaljr/can-dash-lab) | MIT, **Copy OK** | pushed 2026-10 | Virtual instrument cluster driven by opendbc profiles. Good model for "the dash reads a DBC and a fake CAN feed". |
| [jande483/SUNK-N-COST-SOCIETY---PI-DASH](https://github.com/jande483/SUNK-N-COST-SOCIETY---PI-DASH) | no licence, **Ideas only** | pushed 2026-08 | Configurable Pi cluster in Python/Pygame. Shows a config-driven layout. |
| [erikhedb/WE-EV-CAN-Dashboard_POC](https://github.com/erikhedb/WE-EV-CAN-Dashboard_POC) | no licence, **Ideas only** | pushed 2025-09 | EV conversion dash on a Pi reading CAN from an Orion BMS and Tesla drive unit. |
| [MikeMontana1968/mgb-dash-2026](https://github.com/MikeMontana1968/mgb-dash-2026) | no licence, **Ideas only** | pushed 2026-03 | EV conversion dash for a classic car, CAN driven. |
| [opencardev/crankshaft](https://github.com/opencardev/crankshaft) | GPL-3.0, **Ideas only** | 2.7k stars, pushed 2026-10 | Pi head unit (Android Auto). Read for Pi boot speed tricks, read-only root, and how they handle power loss. |
| [guysoft/FullPageOS](https://github.com/guysoft/FullPageOS) | GPL-3.0, **use as a tool** or ideas | 4.5k stars, pushed 2026-11-11 | Pi image that boots straight into a full-screen browser. If the dash is a web app, this shows the kiosk setup (or we just copy the approach with `cage` + Chromium). |
| [lvgl/lvgl](https://github.com/lvgl/lvgl) | MIT, **Copy OK** | 25k stars, pushed 2026-11-16 | Fast embedded UI library. Overkill on a Pi 5, but an option if we ever want a small screen on the Pico box. |
| [slint-ui/slint](https://github.com/slint-ui/slint) | GPL-3.0 / royalty-free / commercial, **check before use** | 24k stars, pushed 2026-11-16 | Modern native UI toolkit, runs well on Pi. Its royalty-free licence covers desktop/mobile/web apps, but embedded use needs a careful read. Not our first pick for an MIT repo. |

**Take-aways for the screens:**
- Every serious project splits it the same way: CAN reader, then a data layer
  (one "signal store"), then the UI binds to signals. The UI never touches CAN.
- Drive everything from a DBC file so mock data, the sim and the real bus all
  share one definition.
- Keep a black box log (last N minutes of CAN) on the Pi for fault finding.
- Read-only root filesystem (Crankshaft, FullPageOS) so a hard power cut
  can't corrupt the Pi.

---

## 4. Pico 2 control box (RP2350 + MCP2515)

| Project | Licence | Activity | What we can borrow |
|---|---|---|---|
| [adamczykpiotr/pico-mcp2515](https://github.com/adamczykpiotr/pico-mcp2515) | MIT, **Copy OK** | 106 stars, pushed 2024-03 | **Best starting point.** MCP2515 driver for the Pico C SDK. Quiet lately but small and stable. Vendor it with its notice. |
| [KevinOConnor/can2040](https://github.com/KevinOConnor/can2040) | GPL-3.0, **Ideas only** | 875 stars, pushed 2026-03 | Software CAN using the Pico's PIO (no MCP2515 needed). Used by Klipper 3D printers, very solid. Can't go in our repo, but good to know if the MCP2515 gives trouble. |
| [calberoni/OTA_by_CAN_RP2040](https://github.com/calberoni/OTA_by_CAN_RP2040) | MIT, **Copy OK** | pushed 2025-10 | **Firmware update over CAN** for RP2040 using the Pico SDK. Very close to our 0x71F "Pi updates the Pico" plan. |
| [c0de111/pico_bootloader](https://github.com/c0de111/pico_bootloader) | Apache-2.0, **Copy OK** | pushed 2026-08 | Dual-slot (A/B) bootloader: boots the newer valid image, falls back if it's bad. Exactly the safety we want for Pico updates. |
| [JZimnol/pico_fota_bootloader](https://github.com/JZimnol/pico_fota_bootloader) | MIT, **Copy OK** | 101 stars, pushed 2026-07 | Over-the-air bootloader with rollback for Pico W. The swap-and-confirm logic carries over even though our Pico 2 has no wifi. |
| [usedbytes/picowota](https://github.com/usedbytes/picowota) | BSD-3-Clause, **Copy OK** | 139 stars, pushed 2024-07 | Wifi bootloader for Pico W. Clean, well written reference for a small bootloader. |
| [L1tPanda/esp32-can-relay-box](https://github.com/L1tPanda/esp32-can-relay-box) | GPL-3.0, **Ideas only** | pushed 2026-11-15 | CAN-controlled relay/MOSFET box with configurable IDs and saved state. Same job as our control box, different chip. |
| [siujacky/can-ota-stm32](https://github.com/siujacky/can-ota-stm32) | no licence, **Ideas only** | pushed 2026-06 | CAN bootloader with a Pico 2 as the bridge. Its README lists "31 bugs fixed", worth reading for traps to avoid. |

**Notes for the firmware thread:**
- The **RP2350 (Pico 2) has A/B partitions and "try before you buy" built into
  its boot ROM**. A new image has to confirm itself after boot or the chip
  falls back to the old one. That may let us skip writing our own bootloader.
  See the RP2350 datasheet, section on partition tables and `picotool partition`.
- Simplest first version of "Pi updates Pico": Pi drives the Pico's RUN pin and
  holds BOOTSEL (or sends 0x71F), Pico shows up over USB, Pi runs `picotool load`.
  Over-CAN updates (OTA_by_CAN_RP2040) can come later.
- Watchdog: use the hardware watchdog, and only feed it from the main loop
  after the safety checks pass.

---

## 5. Off-road accessories (lights, winch, actuators)

Honest finding: **there isn't much open source here.** The good switch panels
(sPOD, Switch-Pros) are closed. Most hobby projects are single Arduinos with
relays. We'll mostly write our own, but these have useful bits:

| Project | Licence | Activity | What we can borrow |
|---|---|---|---|
| [gitcnd/Auxbeam_Driver](https://github.com/gitcnd/Auxbeam_Driver) | unclear, **Ideas only** | old (2021) | Sits inline on an Auxbeam switch panel. Shows how those panels signal (handy if any of the light bars came with an Auxbeam-style controller). |
| [timschloemer109-max/rc-schleppseilwinde-v2](https://github.com/timschloemer109-max/rc-schleppseilwinde-v2) | no licence, **Ideas only** | pushed 2026-10 | Winch controller with **stall detection** and learned rope length. Stall detection is worth having for the XBull winch (watch current, cut out on a sudden jump). |
| [brian-greeson/winch-remote-arduino](https://github.com/brian-greeson/winch-remote-arduino) | MIT, **Copy OK** | old (2023) | Simple winch remote: hold-to-run with timeouts, like our 0x703. |
| [L1tPanda/esp32-can-relay-box](https://github.com/L1tPanda/esp32-can-relay-box) | GPL-3.0, **Ideas only** | pushed 2026-11-15 | (Also above.) CAN to relay mapping, saved config. |

**Patterns to use (no code needed from anyone):**
- Actuator with pot (front diff): a simple position loop with a deadband, a
  max run time, and a current limit through the BTS7960's current sense pins.
- Actuators without feedback (4WD, tray): drive for a timed amount, then stop,
  and track an estimated position (already in our 0x712 design).
- Light bar dimming: PWM a logic-level MOSFET at ~200 Hz to 1 kHz, but only if
  the bars are plain LED arrays. If they have their own driver (most effect
  bars do), PWM on the power line may flicker or confuse them, so test first.
- Winch: hold-to-run with a dead-man timeout, arm switch, stall cut-out.

---

## 6. OTA updates for the Pi 5

| Project | Licence | Activity | What we can borrow |
|---|---|---|---|
| [rauc/rauc](https://github.com/rauc/rauc) | LGPL-2.1, **use as a tool** | 1.3k stars, pushed 2026-11-13 | A/B updates for embedded Linux: install to the spare slot, reboot, fall back if it doesn't boot. Signed bundles. Industry standard. |
| [sbabic/swupdate](https://github.com/sbabic/swupdate) | GPL-2.0, **use as a tool** | 1.9k stars, pushed 2026-11-13 | Same job as RAUC, more options, has a built-in web upload page. |
| [mendersoftware/mender](https://github.com/mendersoftware/mender) + [mender-convert](https://github.com/mendersoftware/mender-convert) | mixed (client mostly Apache-2.0), **use as a tool** | pushed 2026-11-16 | Easiest full OTA on a Pi: converts a normal Raspberry Pi OS image to A/B. Needs a server (hosted or self-run). |
| [UpstreamDataInc/goosebit](https://github.com/UpstreamDataInc/goosebit) | Apache-2.0, **Copy OK** | pushed 2026-11-09 | Small self-hosted update server that works with RAUC/SWUpdate. |
| [rauc/rauc-hawkbit-updater](https://github.com/rauc/rauc-hawkbit-updater) | LGPL-2.1, **use as a tool** | pushed 2026-10 | Links RAUC to an update server. |

**Suggested path:**
1. **v1 (now):** app-level updates only. The dash app lives in its own folder
   as versioned releases (`/opt/teryx/releases/<version>`) with a `current`
   symlink. Update = download, check signature/hash, unpack, switch symlink,
   restart the service. If the new one fails its health check, switch back.
   Simple, works on stock Raspberry Pi OS, covers 95% of updates.
2. **Later:** full system A/B with RAUC, using the Pi 5's built-in `tryboot`
   A/B boot support (`autoboot.txt` with `tryboot_a_b=1`) so a bad OS update
   rolls back on its own.
3. Pico firmware rides along inside the Pi update, and the Pi flashes it
   (see section 4).

---

## Top picks, in one list

1. **SavvyCAN** + **Pico gs_usb firmware**: our Shinegle sniffing kit.
2. **cantools** + **DBC files**: one definition of every CAN signal, shared by sim, dash and tests.
3. **pico-mcp2515** (MIT): the Pico's CAN driver.
4. **RP2350 boot ROM A/B** + **OTA_by_CAN_RP2040** / **pico_bootloader**: safe Pico updates.
5. **ZombieVerter** and **OpenInverter**: ideas for state machine, failsafes and settings.
6. **Lindu666666 cockpit** (MIT) and **OVMS** (MIT): Pi dash architecture with alarms, logging and metrics.
7. **Tesla UI repos**: look and layout only.
8. **Release-folder OTA now, RAUC + Pi 5 tryboot later.**
