# Remote access over 4G (anti-theft)

An optional 4G USB stick on the dash Pi, with a cheap prepaid SIM. Day to day the data is
**off** and the stick just sits there able to get texts. If the Teryx goes missing, you text it
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
2. The text is less than 3 days old (stops a pile of old texts all running when the stick
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

## Which 4G stick

NZ turned off 3G by 31 March 2026 [1], so it has to be **4G (LTE)** with the NZ bands:
Spark uses bands 1, 3, 7, 28 and 40, with band 28 (700 MHz) carrying most of its coverage
[2]; One NZ uses 28, 3, 1 and 7 [3]. Band 28 is the one that matters out in the country.

**Pick: Waveshare SIM7600G-H 4G Dongle** (SKU 18165) [4, 5].

- LTE bands 1/2/3/4/5/7/8/12/13/18/19/20/25/26/28/66, so all of Spark's and One NZ's FDD
  bands, including 28 [6].
- Plain USB stick, 89 x 45 x 15 mm, 134 g, with an LTE antenna and a 20 cm USB extension in
  the box. Nano SIM. Built-in GPS (GNSS antenna extra).
- Works with Linux and ModemManager; Waveshare's wiki shows texts by AT command and the
  RNDIS/NDIS/ECM modes [5, 7].
- Power: about 150 mA average at 5 V, up to 300 mA on data; under 5 mA asleep [5, 6].
- US$101.99 from Waveshare [4]; about NZ$139 to 179 plus shipping on Fruugo NZ [8].

Ruled out:

- **D-Link DWM-222** at PB Tech: bands 1/3/7/28/40 are fine, but it only lists Windows and
  macOS, and texts on it under Linux are a gamble [9].
- **Quectel EC25-AU** (GoWiFi NZ): good bands (1/2/3/4/5/7/8/28/40) but it's a mini PCIe card,
  so it needs a USB carrier board as well [10]. Never use the Pi's PCIe slot: that's kept for
  the AI HAT+ 2.

It plugs into a USB 2 port on the Pi and sits outside the Pi box on its 20 cm lead, so the
antenna isn't inside the box and the box keeps its airflow and room for the AI HAT+ 2.

## The SIM

Any NZ prepaid SIM that does texts and data. The catch is keeping it alive when you never
use it:

| Network | Goes dead after | Notes |
|---|---|---|
| Spark / Skinny | 12 months with no top-up | Inactive SIM: top up $5 within a month to bring it back. Credit expires after 12 months [11]. Texts 20c on Skinny [12] |
| One NZ | 360 days with no top-up | Then the number is gone [13]. Minimum top-up $10 online |

So **set a yearly reminder to top it up**. A $10 to $20 top-up a year covers it, since data
is off nearly all the time. If it's ever stolen, top it up more then.

If the stick is off or out of coverage when you text, the network keeps trying to deliver it,
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

With the key off, the Pi and the stick are only on while Sentry is holding power (locked, for
up to 12 hours, or until the 12V drops under 12.2 V; see [`sentry.md`](sentry.md)). In that
time texts are answered straight away. After that the power hold relay drops both, and a text
waits at the network until the next key-on (for up to about 3 days, see above). Keeping just
the Pi and stick awake to listen costs about 8.6 Ah a day, which would flatten the 12V in a
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
| Text rules, modem, data timer, phone link API | `dash/server/teryx_dash/remote.py` |
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
