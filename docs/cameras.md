# Cameras: rear, front and trailer

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
(MCP23017 B7), now called **`in.trailer`**. Narva's page doesn't say how the switch is
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

## Still to check

- Rear camera: USB or RCA/AHD?
- Which way the Narva reed switch switches, and what triggers it.
- Whether a wireless kit's receiver has an AV out (if you go wireless).
- Any AHD-to-USB dongle on the real Pi before buying more than one.
