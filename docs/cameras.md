# Cameras: rear, front, trailer and cabin

> **Changed 26 Nov (Sam):** the **Pi Camera Module 3 is dropped** (PB Tech had none, and Sam
> now has 3 car cameras from AliExpress: one good, two not as good). **Every camera is now a
> 12 V car camera in CVBS/PAL mode, all into the one analogue video board** on the Pi's camera
> ribbon port (CSI1). The other ribbon port is free. See section 0 below. Older notes further
> down that talk about the Camera Module 3 on the front are out of date.

## 0. Current plan (26 Nov)

| Camera | Which one | Video board input | Notes |
|---|---|---|---|
| Front | **The good one** | 3 (`adv:3`) | Grille or bull bar, looking ahead. It's the dashcam and the trail view at speed, where detail matters most. |
| Rear | The 200 degree one (owned) | 0 (`adv:0`) | Reversing is slow and close up, so a lesser camera is fine. Mirrored, guide lines on. |
| Trailer | A lesser one | 1 (`adv:1`) | Through the round EU 7-pin. Only on with a trailer plugged in. |
| Cabin | Later | 2 (`adv:2`) | Small camera at the seats, face shot in Sentry. |

Each camera gets 12 V from the accessory relay (relay 7) through its own 2 A inline fuse,
an earth at the star point (or good chassis earth nearby), and a shielded video lead soldered
to the board. Wiring: `config/wiring.yaml` (CAM_FRONT, CAM_REAR, CAM_TRAILER, TCAM_DONGLE).

**The video board needs enough inputs.** The chips have plenty: ADV7280-M has 8 analogue inputs
([Analog Devices](https://www.analog.com/en/products/adv7280.html)), ADV7281-M and ADV7282-M
have 6 ([Analog Devices](https://www.analog.com/en/products/adv7282.html)). But cheap boards
only bring some of them out to plugs or pads. **Count them in the listing photos: 3 needed now
(front, rear, trailer), 4 with the cabin camera.**

**One decoder, one live picture.** The chip can only decode one input at a time, and changing
input takes up to 250 ms to lock
([AN-1337](https://www.analog.com/en/resources/app-notes/an-1337.html)). So:

- The combined (ALL) view shows one live picture and the others pause on their last picture.
  By default the live one follows what you're doing: the **front driving forward**, the
  **trailer or rear in reverse**. Tap a paused picture to swap.
- Settings > Cameras > **Combined view** can make them take turns every 3, 5 or 10 s instead
  (not in reverse: the camera behind you stays live).
- The dashcam and Sentry record **one camera at a time**, front first (then rear, trailer,
  cabin). A live picture on the Cameras screen takes the board off the dashcam until you leave.

**CVBS, not AHD.** The ADV chips only decode plain analogue video (CVBS, PAL or NTSC). An AHD
picture won't show. How to check a camera or its listing:

- Good signs: "CVBS", "PAL/NTSC", "analogue", a TVL number (like "700TVL" or "1000TVL"), or
  a yellow RCA plug.
- AHD only ("AHD 720P", "AHD 1080P", "2MP AHD") is no good, unless it also says it can switch
  to CVBS: a switch wire or loop on the lead, a button, or an OSD menu (joystick on the lead).
- On the bench: plug it into any old TV's yellow AV input. If you get a picture, it's CVBS.
  If you get rolling lines or nothing, it's in AHD mode, so switch it.
- Set them to **PAL**.

> **Changed 18 Nov (Sam):** three cameras: front (CSI ribbon), rear (Sam's 200 degree camera) and trailer (only when a trailer is on). Cabin camera moved to "later" (the 2nd ribbon port stays free for it). Sam: no USB for cameras. The front stays a Camera Module 3 on ribbon port 1. The rear and trailer cameras (AHD) are set to their CVBS/PAL mode and soldered into one ADV7280-M analogue-to-ribbon board on ribbon port 2, which picks rear or trailer in software, so only two streams ever record. Nobody makes an AHD-to-ribbon board with Pi drivers, and CVBS boards on the Pi 5 are not proven yet, so bench test it first. The cabin camera is 'later', on a spare input of that board.

Researched 18 November 2026 (NZ time). Prices incl GST unless it says otherwise. Each price
says where it came from. Some came from search results because the shop page wouldn't open,
so check the link before you buy.

## Short answer

- **Yes, the dash takes more than one camera.** It now has three: rear, front and trailer
  (Settings > Cameras). One shows at a time, picked with the buttons along the top of the
  Cameras screen. Cameras that aren't fitted are greyed out.
- **Yes, a camera can go on the trailer.** It shows when a trailer is plugged in, and in
  reverse it takes over from the rear camera.
- **There's no spare core in a 7-pin plug for video.** All seven pins have a job. Pin 2
  (reversing) is the usual "spare" on small trailers, and it's a good **power feed** for a
  trailer reverse camera, but the picture still needs its own way back: wireless, a kit that
  sends video down the power wire, or a small extra plug.

## 1. The NZ 7-pin flat plug

NZ uses the Australian 7-pin flat plug (AS 4177.5)
([Couplemate](https://www.couplemate.com.au/7-pin-trailer-plug),
[Narva](https://narva.com.au/resources/trailer-plug-wiring-diagram),
[Action Outdoors NZ](https://actionoutdoors.kiwi/blogs/news/how-to-wire-a-trailer-nz-4-5-7-12-pin-diagrams)):

| Pin | Job | Colour |
|---|---|---|
| 1 | Left indicator | Yellow |
| 2 | Reversing (also called auxiliary) | Black |
| 3 | Earth | White |
| 4 | Right indicator | Green |
| 5 | Electric brakes | Blue |
| 6 | Stop lights | Red |
| 7 | Tail lights | Brown |

- **Pin 2 and pin 5 are often not used on basic trailers**
  ([Action Outdoors NZ](https://actionoutdoors.kiwi/blogs/news/how-to-wire-a-trailer-nz-4-5-7-12-pin-diagrams)).
- **Pin 2 is meant for the reversing signal.** The Australian standard says not to put
  permanent auxiliary power on it, even when the trailer has no reversing lights
  ([Wikipedia: Trailer connectors in Australia](https://wiki.riteme.site/wiki/Trailer_connectors_in_Australia)).
  A trailer **reverse camera** powered from pin 2 is exactly what pin 2 is for, so that's fine.
- I found no NZTA document on trailer plug wiring, only shop guides. Some low-quality pages
  claim a new NZTA standard is coming; I couldn't confirm it.

### Can video go down pin 2 or pin 5?

- **Pin 5 for video: no.** If you ever tow a braked trailer, the brake controller puts
  voltage on pin 5 and would cook the camera input. The 7-pin earth (pin 3) is also shared
  with the lights, so the picture would be noisy. One installer only fixed trailer camera
  noise by earthing the camera at the hitch
  ([the12volt forum](https://www.the12volt.com/installbay/forum_posts.asp?tid=136029), anecdote).
- **Pin 2 with a power-line kit: possible.** Kits like the Brigade Pulse PLC-1000 send
  composite video down the existing reversing light wire, so no extra cable or plug is
  needed. 10-36 V, PAL. Catches: the camera only works while reversing (it's on the
  reversing feed), and the maker says not to use it with CAN body-bus wiring
  ([Brigade PLC-1000 guide](https://brigade-electronics-product-support.s3.amazonaws.com/Camera%20Monitor%20Systems/Ancillaries/Power%20Line%20Communication/PLC%20Reciever/PLC-1000R%20(2593)/User%20Manual/PLC-1000%20(2593)%20-%20Instruction%20Guide.pdf)).
  Our reversing feed is a plain relay, so that warning shouldn't bite, but **price not
  found**: it's a trade product. Cheaper "video over power line" units exist
  ([TadiBrothers](https://www.TadiBrothers.com/products/video-transmitters-over-power-line-for-backup-camera-95ft-range)), not checked for NZ.
- **A 12-pin flat plug** has spare pins (Narva rates pins 8-12 at 35 A), but the pin jobs
  vary by maker and I couldn't confirm Narva's own table
  ([Supercheap NZ](https://www.supercheapauto.co.nz/p/narva-narva-trailer-socket---12-pin-flat/515422.html),
  [Narva blog](https://www.narva.com.au/blogs/blogs/2020/Jul/13/trailer-connectors)). Overkill
  for a Teryx trailer.

## 2. Telling the dash a trailer is plugged in

Narva sell a 7-pin flat socket with a **reed switch** built in (part **82043BL**). It's made to
turn reversing sensors off when a trailer is plugged in
([Narva](https://narva.com.au/products/narva-7-pin-flat-quickfit-trailer-socket-with-reed-switch-for-use-with-normally-closed-circuits-1-pack)).
We use that switch as an input instead: it's wired to the control box's last spare input
(was MCP23017 B7, moved to the second MCP23017 B0 on 19 Nov because newer chips say GPB7 is output only), now called **`in.trailer`**. Narva's page doesn't say how the switch is
triggered or which way it switches, so **check it on the bench** before wiring.

With that, the dash:

- greys out the trailer camera with "NO TRAILER" when nothing is plugged in,
- says "Trailer plugged in. Trailer camera ready." when you plug in,
- shows the trailer camera in reverse when a trailer is on (Settings > Cameras can turn that off),
- drops back to the rear camera if the trailer is unplugged while you're watching it.

That uses up the control box's last spare digital input. If we need more later, the MCP23017's
port A has free pins, or a second one can go on the same I2C bus.

## 3. Trailer camera: three ways to do it

| | Wireless | Power-line kit | Own plug |
|---|---|---|---|
| How | Camera on the trailer sends the picture by radio to a receiver in the Teryx, which goes into the Pi through a USB capture dongle | Video goes down the pin 2 wire to a box in the Teryx | Small waterproof 4-pin plug next to the 7-pin, carrying video and power |
| Power | Pin 2 (reverse only), or its own battery | Pin 2 (reverse only) | Its own pin, so it can run while driving to check the load |
| Picture | Good on digital 2.4 GHz kits. Can drop out | Analogue, PAL | Best, nothing to drop out |
| Wiring | Easiest | Easy | One more plug and cable |
| NZ example | Jaycar QM3842 5" digital kit, about [NZ$359](https://www.jaycar.co.nz/p/QM3842) (from search results). Oricom WRC001 magnetic, battery, [NZ$289](https://www.marine-deals.co.nz/oricom-wrc001-ipx6-wireless-reversing-camera-with-magnetic-base) | Brigade PLC-1000, price not found | Not priced: an M12 or "aviation" 4-pin plug plus any 12 V AHD camera |

**Catch with the wireless kits:** they come with their own little screen. I couldn't confirm
from Jaycar's pages that the receiver has an RCA video output to feed the Pi
([Jaycar](https://www.jaycar.co.nz/p/QM3842)), so check the manual before buying.

**My pick: own plug.** It's the only one that gives a solid picture while driving as well as
reversing, it costs the least, and you control both ends (the Teryx and your own trailer).
Power the camera from a switched 12 V pin on that plug. If you'd rather not add a plug, the
wireless kit is next best, as long as its receiver has an AV out.

## 4. How many cameras the Pi 5 can take

- **USB:** the Pi 5 has **two separate USB controllers**, each with one USB 3 and one USB 2
  port, so two cameras on different sides don't fight over bandwidth like they did on the
  Pi 4 ([Raspberry Pi docs](https://raspberrypi.com/documentation/computers/io-controllers.html),
  [CNX Software](https://www.cnx-software.com/2023/10/07/raspberry-pi-rp1-datasheet-block-diagram/)).
  Webcams usually run at USB 2 speed, and a USB 2 bus only gives about 384 Mbps to cameras
  ([The Good Penguin](https://www.thegoodpenguin.co.uk/?p=251)). MJPEG at 720p fits two or
  three per bus. People report about three USB cameras per Pi before power runs out, so use a
  powered hub past three ([Blue Robotics forum](https://discuss.bluerobotics.com/t/using-two-cameras-simultaneously-on-raspberry-pi-blue-robotics-low-light-usb-camera/22070), about a Pi 4).
- **Ribbon (CSI):** the Pi 5 has two camera ribbon ports, but the official cable only comes
  up to **500 mm** ([Raspberry Pi](https://www.raspberrypi.com/products/camera-cable/)), and
  people report trouble past about 70 cm
  ([Industrial Monitor Direct](https://industrialmonitordirect.com/blogs/knowledgebase/extending-raspberry-pi-camera-ffc-cable-alternatives)).
  Fine for a camera inside the screen housing; no good for the back of the Teryx.
- **RCA / AHD cameras:** need a USB capture dongle each. Get one that says **UVC**, so Linux
  sees it as a plain webcam ([LinuxTV wiki](https://linuxtv.org/wiki/index.php/UVC_compliant_capture_devices)).
  Many AHD-to-USB modules claim UVC, but I found no independent Pi test of one
  ([Cirkit Designer](https://docs.cirkitdesigner.com/component/ecf4d35b-cb01-441c-896a-86bddb8fa7c8/ahd-to-type-c-usb-capture-analog-signal-to-digital-usb-camera-module-uvc-free)),
  so test it on the bench. The cheapest NZ one is the EasyCAP DC60 at
  [NZ$28.75 at PB Tech](https://www.pbtech.co.nz/product/SEVOEM9701) (composite only, not AHD).

So **three cameras is comfortable**: rear and trailer on USB (one per controller), front on the
ribbon port.

## 5. Recommended setup

| Camera | What | Where it plugs in | Notes |
|---|---|---|---|
| Rear | The 2K camera you have | USB 3 port A (USB) or a UVC capture dongle (RCA/AHD) | Still need to find out which type it is |
| Front | Raspberry Pi **Camera Module 3 Wide**, ~[NZ$81 at PB Tech](https://www.pbtech.co.nz/product/SEVRBP0398/Raspberry-Pi-Official-Camera-Module-3-Wide-Version) (out of stock when checked, price from search results) | Ribbon port, 200-300 mm cable | Inside the screen housing, looking over the bonnet through a clear window. It's also the camera for camera AI on the AI HAT+ 2. Not waterproof, so it must stay inside |
| Front, low (optional) | Waterproof 12 V camera, same type as the rear one | USB port B | On the bull bar, for seeing over crests |
| Trailer | 12 V AHD or analogue reversing camera | Own 4-pin plug, then a UVC capture dongle on USB port B | See section 3 |

## 6. What's in the dash now

- Settings > Cameras: each camera (rear, front, trailer) has Fitted, Which device, Mirror and
  Guide lines. Plus "Trailer camera in reverse".
- Cameras screen: REAR / FRONT / TRAILER buttons along the top. Greyed with NOT FITTED or
  NO TRAILER when they can't be used.
- A ribbon camera works by setting its device to `csi0` or `csi1` (served by `rpicam-vid`).
- Try it: `?demo=reverse&trailer=1`, or switch on `in.trailer` in the simulator.

## 7. Cabin camera, recording and Sentry

- A fourth camera, **Cabin**, looks at the seats from near the screen: Camera Module 3 NoIR Wide
  on the second ribbon port (`csi1`). It takes the face shot if someone tries the key while
  it's locked. Ribbon, not USB or PCIe, so the AI HAT+ 2 can still go on later.
- Every fitted camera records to the Pi's high-endurance microSD card: a dashcam loop with the key on, and
  Sentry when locked. See [`sentry.md`](sentry.md) for sizes, battery use and CPU load.
- A USB camera that sends **H.264** itself costs the Pi almost nothing to record (it's just
  copied). MJPEG cameras are encoded on the CPU, since the Pi 5 has no H.264 encoder. Worth
  favouring H.264 when buying the rear or trailer camera.

## 8. Combined view (ALL)

> Added 19 Nov (Sam: "combined screen option, dynamic to if trailer fitted/connected", front bar
> controls on the front picture). Try it on the online sim: Cameras > ALL, then the
> DEMO: PLUG IN TRAILER button top right.

- **ALL** is the first button on the Cameras screen. With no trailer it shows **front and rear**
  side by side. With a trailer on it shows **front down the left, trailer and rear on the right**.
- **Rear and trailer can't both be live.** They share the analogue video board, and its chip
  (ADV7280-M) has several inputs but one decoder, so it decodes one input at a time. Changing
  input takes up to 250 ms to lock in fast switch mode, over 500 ms with autodetect
  ([Analog Devices AN-1337](https://www.analog.com/en/resources/app-notes/an-1337.html)), so
  flicking between them would give each about one picture a second at best. So one of the two
  is live and the other keeps its last picture with **PAUSED, tap to show live**. With a trailer
  on, the trailer camera starts live (the rear one mostly sees the drawbar). **Since 26 Nov the
  front camera is on the board too**, so only one of all of them is live (see section 0).
- **Lights on the pictures:** front bars 1-4 and ALL on the front picture, rear lights on the
  rear, trailer bar on the trailer, cab light on the cabin. In reverse, on a single rear or
  trailer picture, the rear lights button goes big like before.
- **Reverse:** if you're already on ALL it stays there and makes the camera behind you live.
  Settings > Cameras > **Reverse shows** can make reverse always pop up the combined view.
- **Leaving the Cameras screen stops the pictures.** A live video board camera on screen takes
  the board off the dashcam (the dashcam can't use it at the same time), and gives it back when
  you leave.

### How the dash knows the trailer camera is there

Two plugs go to the trailer: the flat 7-pin (lights, with the reed switch, `in.trailer`) and
the round EU 7-pin (camera and light bar). A trailer can be on with no camera, so the dash
also checks for a **picture**:

- The dash server asks the video board if there's a picture on the trailer input
  (`v4l2-ctl --get-detected-standard`; the adv7180 driver reports "unknown" when it hasn't
  locked onto a signal). That needs no extra wire. Code: `dash/server/teryx_dash/trailercam.py`.
- It only checks while nobody is using the board (switching input under the dashcam or a live
  picture would glitch it): straight away when the trailer plug goes in or out, then every 10 s.
  While it can't check, the dash goes by the reed switch.
- Settings > Cameras > **Trailer detect**: Either (default), Picture only, or Plug only.
- If the Pi 5 driver only answers on the decoder's own node, set `TERYX_VIDEO_SUBDEV=/dev/v4l-subdevN`.
- Spare option if the picture check doesn't work on the bench: EU pin 7 is spare. Loop pin 7 to
  pin 3 (camera earth) inside the trailer's plug and wire pin 7 to a spare input, and the dash
  knows the camera plug is in. Not wired: it would need a spare input on the control box (MCP23017
  port A has free pins) and firmware changes, so only do it if the bench test says so.

## 9. Could it do a 360 (bird's eye) view?

Researched 19 Nov 2026. Short answer: **not with the cameras we have, and not by stitching on
the Pi without big changes. The easy way is a ready-made 360 box.** Nothing bought.

What a 360 view needs: four wide (about 180 degree) cameras, one on each side, all live at the
same time, and something that warps and joins them into a top-down picture, calibrated once
with a mat on the ground.

What we're missing:

- **Cameras:** we have front (narrow, behind the screen), rear (200 degree) and trailer. A 360
  needs a wide front camera low on the grille, and left and right cameras (mirrors or cage).
- **Four live pictures at once:** the Pi 5 has two camera ribbon ports. One is the front Camera
  Module 3, the other the analogue video board, which only decodes one camera at a time. I found
  no 4-channel AHD/analogue to ribbon board with Pi 5 drivers (TP2855-type boards exist for
  other boards, with their own drivers
  ([TI forum](https://e2e.ti.com/support/processors-group/processors/f/processors-forum/1463131/sk-am62p-lp-enabling-4-ahd-cameras),
  [Toradex forum](https://community.toradex.com/t/mipi-csi-2-camera-gstreamer-error-virtual-channels-with-tp2855/20391))).

Three ways, best first:

| | How | Pi load | Catch |
|---|---|---|---|
| **A. 360 box** (pick) | A universal 360 kit: 4 cameras + its own box that does the stitching and calibration, giving one video out. Its video out goes into a **spare input on our video board** (the ADV7280-M has 8 ([Analog Devices](https://www.analog.com/en/products/adv7280.html))). The dash shows it as a fifth camera, "360". | Same as one analogue camera. None of the stitching is on the Pi. | Its picture shares the board with rear and trailer, so in the combined view it's one more "tap to show live". Must have a CVBS/RCA (not just AHD) output, PAL. Prices seen: about AU$76-197 on eBay AU ([eBay AU](https://www.ebay.com.au/itm/353602594868), [eBay AU](https://www.ebay.com.au/itm/354622659506)), from listings only, outputs not confirmed. Cameras would need to be IP67 for the Teryx. |
| B. GMSL board | Waveshare GMSL 4-channel board: 4 cameras on long coax, all live, made for the Pi 5, US$269.99 ([Waveshare](https://www.waveshare.com/product/ai/cameras/gmsl-module-board-4ch-a.htm)), plus 4 GMSL cameras. The Pi does the stitching on its GPU. | High: four camera streams plus warping, on top of CarPlay and recording. Would want the AI HAT+ 2 for any camera smarts. | It takes **both** ribbon ports, so the front Camera Module 3 and the analogue video board (rear, trailer) would have to go, all cameras become GMSL. A big rebuild and a lot of our own code. |
| C. Fake it | No new cameras: show a drawn top-down Teryx with the front and rear pictures above and below it. | None | Not a real 360: nothing at the sides. |

None of these use USB or the PCIe slot, so the AI HAT+ 2 can still go on later. **My pick: A**,
when you want it: one more input on the board we're already fitting and no extra Pi work, apart
from adding "360" as a camera on the dash. Before buying, check the box has an RCA video out and
PAL, and that the cameras are waterproof.

## Still to check

- Each of the 3 car cameras: CVBS/PAL, or AHD with a CVBS mode? (TV test above.)
- How many video inputs the video board actually has (3 needed, 4 with the cabin camera).
- Which way the Narva reed switch switches, and what triggers it.
- Whether a wireless kit's receiver has an AV out (if you go wireless).
- Any AHD-to-USB dongle on the real Pi before buying more than one.
- Video board on the Pi 5: does `--get-detected-standard` say 0 with the trailer camera unplugged
  and PAL with it in? Does switching rear/trailer in the combined view come up within a second?
