# Remote access over 4G (anti-theft)

An optional 4G module on the dash Pi (a cheap bare board in the Pi box, or a USB stick), with a cheap prepaid SIM. Day to day the data is
**off** and the module just sits there able to get texts. If the Teryx goes missing, you text it
from your phone:

| Text | What happens |
|---|---|
| `WHERE 4821` | Replies with a Google Maps link, how old the GPS fix is, speed, key on/off, lock state and the 12V |
| `LOCK 4821` | Asks the control box to lock. It **never** locks while moving: it waits until the Teryx has been stopped for 10 s, or the key is off, then locks |
| `CAMS 4821` or `ONLINE 4821` | Turns the 4G data on for 30 min (change it in Settings). Your phone joins over Tailscale for live cameras, saved clips and the phone app |
| `OFF 4821` | Data off now |
| `HELP 4821` | The list of commands |

`4821` stands for your remote code (4 to 8 digits, set on the dash). Upper or lower case is fine.

**The Teryx never texts you on its own.** No alerts, no "someone's trying to start it" texts.
It only ever answers a text you send. Sentry clips (see [`sentry.md`](sentry.md)) wait on the
SSD until you look at them, on the dash or over 4G.

## Who it listens to

Every text has to pass all of these, in order, or it's ignored with no reply at all (a thief
testing the number learns nothing):

1. Remote access is turned on (Settings > Remote (4G texts)).
2. The text is less than 3 days old (stops a pile of old texts all running when the module
   comes back into coverage).
3. It's from one of up to 3 phone numbers you've listed.
4. Not blocked: 5 wrong codes in a row blocks everyone for an hour. The phone app's code
   checks count toward the same 5.
5. The first word is a command, and the code is right.
6. At most 10 replies an hour. Past that, LOCK and OFF still work but nothing is sent back.

Caller ID can be faked, which is why the code is needed as well as the number. The code is
stored only as a salted PBKDF2 hash (100,000 rounds) in `remote.json` (mode 0600), and is never
written to the log. The numbers and code can't be changed while the Teryx is locked.

### Why the lock lives in the control box

The text only *asks*. The Pi sends the control box a `REMOTE` lock command (CAN `0x705`
command 7). The Pico remembers it in flash as "lock waiting" (`0x716` bit 36) and locks only
once it's safe: the winch isn't running, and either the key is off or it's been stopped for 10 s.
Then it's the normal vehicle lock (see [`vehicle-lock.md`](vehicle-lock.md)): drive inhibit,
4WD/diff/tray/winch refused, and unlocked only with the PIN on the dash. So a hacked or
crashed Pi can't make it lock at speed, and a remote lock still holds after a power cut.

LOCK needs a dash PIN to be set first. If there isn't one, the reply says so.

## Getting in over 4G: Tailscale

The Pi and your phone both join your Tailscale network (you already use Tailscale). With the
data on, open **http://teryx:8080** on the phone for the dash: live cameras, Sentry clips,
WHERE on a map. Nothing is opened up to the internet; the Pi isn't reachable except over your
tailnet, so there's no port forwarding and the SIM doesn't need a public IP.

Being on your tailnet is the "is this one of my devices" check. Anything that drives or
changes the vehicle (like RC over 4G) also asks for the vehicle PIN on top of that.

### The phone app

A phone app (the "pocket" side, see the RC thread's `docs/rc-beach-launch.md`) uses this path,
so turning things on doesn't depend on being at the dash:

1. The app opens a text to the Teryx with `ONLINE <code>` filled in. You press send.
2. The data comes up. The app connects over Tailscale.
3. `GET /api/remote/link` says whether the 4G link is up: `{up, minutes_left, off_at, enabled}`.
   No secrets in it.
4. `POST /api/remote/link` with `{"code": "4821", "minutes": 60}` keeps it up longer
   (5 to 240 min), or `{"code": "4821", "off": true}` drops it. Same code and the same
   wrong-code block as texts.

Other dash plugins read the link state with `app[REMOTE_KEY].link()`.

## Which 4G module

NZ turned off 3G by 31 March 2026 [1], so it has to be **4G (LTE)** with the NZ bands:
Spark uses bands 1, 3, 7, 28 and 40, with band 28 (700 MHz) carrying most of its coverage
[2]; One NZ uses 28, 3, 1 and 7 [3]. Band 28 is the one that matters out in the country.

**Pick: a SIMCom A7670SA core board** (about US$15 on AliExpress [18]), soldered up and
mounted inside the Pi box. The A7670SA has LTE bands 1/2/3/4/5/7/8/28/66, so band 28 is
there [19]. **Not the A7670E**: it's the European version and has no band 28. Check the
band list on the listing before you buy.

Two ways to hook it up. The code does both:

| | Pi UART (GPIO 14/15) | USB |
|---|---|---|
| Texts: WHERE, LOCK, OFF | Yes | Yes |
| Live cameras, saved clips, phone app | **Too slow**: about 11 KB/s at 115 200 baud, 90 KB/s at 921 600. One camera at 2 Mb/s needs about 250 KB/s | Yes |
| RC over 4G (needs live video) | **No** | Yes |
| Wiring | 4 wires plus a level shifter if the board doesn't have one | One USB lead |

So **if the board has a USB-C port wired to the module's own USB pins, use that**. The A7670
has a real USB 2.0 port (pins 27 and 28) [20]; some cheap boards only have a USB-serial chip
on the USB-C port, which is no faster than the UART. If the board you get is UART only, texts
and LOCK work fine, and CAMS replies that there's no data.

**Plug-in alternative: Waveshare SIM7600G-H 4G Dongle** (SKU 18165) [4, 5], about NZ$139 to
179 [8]. Same NZ bands including 28 [6], plain USB stick, no soldering. Dearer, which is why
it's the backup now.

Ruled out:

- **D-Link DWM-222** at PB Tech: bands 1/3/7/28/40 are fine, but it only lists Windows and
  macOS, and texts on it under Linux are a gamble [9].
- **Quectel EC25-AU** (GoWiFi NZ): good bands (1/2/3/4/5/7/8/28/40) but it's a mini PCIe card,
  so it needs a USB carrier board as well [10]. Never use the Pi's PCIe slot: that's kept for
  the AI HAT+ 2.

## Bare module on the UART: wiring and power

**Power. Give it its own supply.** The A7670 runs on 3.4 to 4.2 V (3.8 V recommended), and
its current can spike to **2.8 A** when it transmits [20]. Don't take that from the Pi's 5 V
rail or a Pi GPIO pin.

- A small buck (MP1584 type, rated 3 A) from the fused 12V feed in the Pi box, set to
  **3.8 V** with a meter before the module goes on. If the board has its own regulator and
  a "5V" or "VIN" pin, feed that instead and follow the board's label.
- A **1000 µF** low-ESR cap across the supply right at the module. SIMCom asks for at least
  100 µF to keep the dip under 300 mV during a burst [20]; more is fine.
- Common ground with the Pi.

**Signals. Watch the voltage.** The A7670's own UART pins are **1.8 V** [20]. The Pi's GPIO
is 3.3 V. Many core boards already have a level shifter and say "TTL" or have a VCCIO pin;
check before wiring. If the pins go straight to the module, put a level shifter between
(a 4-channel BSS138 board is fine at 115 200 baud).

| Pi 5 | Module board |
|---|---|
| GPIO 14 (pin 8, TXD) | RXD |
| GPIO 15 (pin 10, RXD) | TXD |
| GND (pin 6) | GND |
| | VBAT/VIN from the buck above |

This uses UART0 on GPIO 14/15, which shows as `/dev/ttyAMA0` once it's turned on. On a Pi 5
the default serial port is the separate debug header (`ttyAMA10`), so this doesn't clash with
the console [21]. GPIO 14/15 aren't used by the AI HAT+ 2, the CAN board or anything else in
this build (see the Pi header table in `docs/wiring.md`).

**Antenna.** Most boards have a small u.FL socket. Use a u.FL to SMA bulkhead lead out through
the Pi box wall, and a wideband 698 to 2700 MHz antenna on the outside, away from metal. Band
28 is 700 MHz, so the antenna has to go that low. Never power the module up without the
antenna on.

**Mounting.** Inside the Pi box, on the opposite side of the lid from the SSD cradle, clear of
the AI HAT+ 2 space and the fan's air path. Measure the board when it turns up and the box
mount gets added to the CAD.

**Setup.**

```bash
sudo bash scripts/remote-setup.sh --uart          # ModemManager drives it: texts and (slow) data
sudo reboot
mmcli -L                                          # should list the module
```

`--uart` turns on UART0 (`dtparam=uart0=on`) and adds a udev rule so ModemManager looks at
`ttyAMA0` (it ignores plain serial ports unless told to [22, 23]). Data then runs as PPP
through the same `teryx-4g` connection.

If ModemManager won't take it, `--uart-direct` skips ModemManager and the dash talks AT
commands to the module itself (`TERYX_MODEM=at:/dev/ttyAMA0:115200`): texts only, no data.
The module's default is 115 200 baud [20].

## The SIM

Any NZ prepaid SIM that does texts and data. The catch is keeping it alive when you never
use it:

| Network | Goes dead after | Notes |
|---|---|---|
| Spark / Skinny | 12 months with no top-up | Inactive SIM: top up $5 within a month to bring it back. Credit expires after 12 months [11]. Texts 20c on Skinny [12] |
| One NZ | 360 days with no top-up | Then the number is gone [13]. Minimum top-up $10 online |

So **set a yearly reminder to top it up**. A $10 to $20 top-up a year covers it, since data
is off nearly all the time. If it's ever stolen, top it up more then.

If the module is off or out of coverage when you text, the network keeps trying to deliver it,
usually for 24 to 72 hours depending on the network [14]. That's why texts more than 3 days
old are ignored.

## Setting it up

```bash
sudo bash scripts/remote-setup.sh --ssd-label teryx-video
```

That installs ModemManager, lets the dash read and send texts (`dash/deploy/51-teryx-modem.rules`),
makes a NetworkManager 4G connection called `teryx-4g` with **autoconnect off**, mounts the
video SSD, and tells you how to put the Pi on Tailscale (`sudo tailscale up --hostname teryx`).
The APN normally comes from the SIM; if not, pass `--apn` (Skinny's is `wapaccess.co.nz` [15]).
The 4G connection gets a higher route metric than Wi-Fi, so when both are up Wi-Fi is used.

Then on the dash: **Settings > Remote (4G texts)**: add your number, set a code, turn it on. In the
simulator there's a box there to send a pretend text and see the reply.

## Battery

With the key off, the Pi and the 4G module are only on while Sentry is holding power (locked, for
up to 12 hours, or until the 12V drops under 12.2 V; see [`sentry.md`](sentry.md)). In that
time texts are answered straight away. After that the power hold relay drops both, and a text
waits at the network until the next key-on (for up to about 3 days, see above). Keeping just
the Pi and module awake to listen costs about 8.6 Ah a day, which would flatten the 12V in a
week or two, so it isn't done. The backup below covers the long gaps.

## Backup: a hidden tracker

A thief who finds the Pi or pulls the 12V stops all of the above. A cheap backup is a tracker
hidden somewhere else on its own battery:

- **AirTag** (about NZ$47 to 68 [16]): a year on a coin cell, no subscription. It only reports
  when an Apple device passes nearby, so it's not real time, and a thief with an iPhone gets an
  "AirTag found moving with you" warning after a while [17].
- **4G GPS tracker**: real time, but usually needs its own SIM or a subscription, and its own
  battery to charge.

## Where things are

| Part | File |
|---|---|
| Text rules, modem (ModemManager, or AT commands on the UART), data timer, phone link API | `dash/server/teryx_dash/remote.py` |
| Remote lock (firmware) | `firmware/control-box/src/core/lock.c` (`vlock_remote_check`), `controller.c` (`remote_safe`) |
| Remote lock (simulator) | `teryx/vehicle_lock.py`, `teryx/sim/controlbox.py` |
| Dash | Settings > Remote (4G texts) in `dash/web/js/screens/settings.js` |
| Setup | `scripts/remote-setup.sh`, `dash/deploy/51-teryx-modem.rules` |
| Tests | `dash/tests/test_remote.py`, `tests/test_vehicle_lock.py`, `firmware/control-box/tests/test_controller.c` (`test_lock_remote`) |

## Sources

1. [2degrees: things to know about the 3G shutdown](https://2degrees.nz/help/mobile-help/troubleshooting/things-to-know-about-our-3g-shutdown), and [PB Tech: 3G network shutdown](https://hardwired.pbtech.co.nz/article/2624/3g-network-shutdown).
2. [Spark 4G network](https://spark.co.nz/4g): bands and band 28 coverage.
3. [One NZ mobile network frequencies](https://one.nz/faq/one-nz-mobile-network-frequencies).
4. [Waveshare SIM7600G-H 4G Dongle](https://www.waveshare.com/sim7600g-h-4g-dongle.htm): price, size, what's in the box.
5. [Waveshare wiki: SIM7600G-H 4G Dongle](https://www.waveshare.com/wiki/SIM7600G-H_4G_DONGLE): USB modes, SMS AT commands, current draw.
6. [SIMCom SIM7600G/G-H hardware design](https://files.waveshare.com/upload/e/e6/SIM7600G_SIM7600G-H_Hardware_Design_V1.00.pdf): LTE bands, sleep current.
7. [Waveshare wiki: SIM7600G-H for Jetson Nano](https://waveshare.com/wiki/SIM7600G-H_4G_for_Jetson_Nano): Linux setup.
8. [Fruugo NZ: Waveshare SIM7600G-H dongle](https://www.fruugo.co.nz/waveshare-sim7600g-h-4g-dongle-module-an-internet-access-module-for-raspberry-pi-gnss-global-communication/p-431287027).
9. [PB Tech: D-Link DWM-222](https://www.pbtech.co.nz/product/MODDLK4222).
10. [GoWiFi NZ: Quectel EC25-AU](https://www.gowifi.co.nz/wireless-cards/ec25-au.html).
11. [Spark: inactive SIM](https://spark.co.nz/help/mobile-help/phone-sim-number/sim/inactive-sim).
12. [Skinny rates](https://www.skinny.co.nz/pricing/rates).
13. [One NZ: when does prepay credit expire](https://one.nz/faq/when-does-prepay-credit-expire).
14. [seven.io: SMS validity period](https://help.seven.io/en/validity-period-how-long-will-you-try-to-deliver-my-sms), and [Wikipedia: Short message service centre](https://en.wikipedia.org/wiki/Short_Message_service_center).
15. [Skinny: how to manually set APN settings](https://www.skinny.co.nz/help/device-help/devices/nokia/nokia-3-4/internet/how-to-manually-set-apn-settings/).
16. [PriceMe: Apple AirTag](https://www.priceme.co.nz/search.aspx?q=airtag).
17. [Apple: what to do if you get an alert that an AirTag is with you](https://support.apple.com/en-nz/HT212227).
18. [AliExpress: SIMCom A7670SA core board](https://www.aliexpress.us/item/3256808314829525.html): price and band list from the listing title only (the page didn't open from here).
19. [LCSC: SIMCom A7670SA-LASC](https://www.lcsc.com/product-detail/C18548276.html): LTE-FDD B1/2/3/4/5/7/8/28/66.
20. [SIMCom A7670 Series Hardware Design V1.00](https://www.elecrow.com/download/product/CRT01260S/A7670_Series_Hardware_Design_V1.00.pdf): VBAT 3.4 to 4.2 V, 2.8 A peak, 1.8 V UART, USB 2.0 pins, baud rates.
21. [HatLabs HALPI2: Pi 5 interfaces](https://docs.hatlabs.fi/halpi2/technical-reference/interfaces/): UART0 on GPIO 14/15 is `/dev/ttyAMA0`, turned on with `dtparam=uart0=on`.
22. [ModemManager: common udev tags](https://distributions.freedesktop.org/software/ModemManager/api/1.10.0/ModemManager-Common-udev-tags.html).
23. [balena forum: ModemManager and a 4G HAT over UART](https://forums.balena.io/t/modemmanager-4g-hat-communication-over-uart/60532).
