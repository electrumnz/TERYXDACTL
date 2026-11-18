# Fun: camp mode, games, streaming and easter eggs

Sam asked (18 Nov 2026) for Tesla-style fun on the dash: games, easter eggs, Netflix/YouTube,
a camp mode with a fire, and anything else that fits. This is what's built, what's still an idea,
and what's known (with sources) about streaming and battery use.

**One rule for all of it:** Fun only runs when the Teryx is parked: park brake on (`in.park`),
stopped (speed under 0.5 km/h) and the speed is known (motor controller talking). The page checks
it (`dash/web/js/fun/park.js`) and so does the Pi (`dash/server/teryx_dash/fun.py`), so a video
window shuts even if the dash page is hidden behind it.

## What's in the dash now (Fun button on the bottom bar)

| Thing | What it does |
| --- | --- |
| **Camp mode** | Full-screen campfire (drawn live, no video file) with crackle sound (made with Web Audio, no sound file). Pick cab light and front bars (off / low / full), fire sound, auto-off timer (1 to 8 h), screen bright / dim / off. Shows how long the battery lasts at the current draw. Turns its lights off if the 12V battery drops below 11.9 V for 15 s. Ends by itself if the Teryx moves, and then leaves the lights as they are (switching lights off on the move isn't safe). Ending it by hand puts the lights back how they were. |
| **Fossil Dig** | One-player puzzle. A T. rex skeleton is buried in a 10 x 6 dig site. Each tap brushes one square; dirt glows hot near a bone you haven't found and cold far away. 24 brushes to find all 9 bones. Best score saved. |
| **Roar Duel** | Two-player reaction game (driver left, passenger right), or solo for your reaction time. Wait for the roar; slapping early or on a fake-out snarl gives the point away. First to 5. Uses the T. rex head art we already have. |
| **Watch** | Launcher for YouTube, Netflix, Disney+, Prime Video, Neon, TVNZ+, ThreeNow, Spotify. Names only, no logos. On the Pi it opens a separate Chrome window under the top bar, with a "back to dash" chip in the top bar. More can be added in the settings file (`fun.streams`, https only). |
| **Light show** | 30 s of the four front bars dancing to a beat, then a roar. Parked only, and only if Lights is switched on in Settings > Features. Puts the bars back how they were. |
| **Easter eggs** | Four hidden ones, counted on the Fun screen with a hint each. Parked only. |

All games and art are original. No names, characters, art or sounds from existing games.

### The easter eggs (spoilers)

- **Roar:** tap the TERYX badge 5 times quickly. The T. rex wakes up and roars, the dash shakes.
- **Extinction:** press and hold the look name (Predator / Fossil / Night Hunt) for 2 s. A meteor hits. "Still here."
- **Tiny arms:** tap the clock 7 times. T. rex arm jokes.
- **Sue's day:** on 12 August the splash says happy find-day to SUE, the Field Museum's T. rex, found by Sue Hendrickson on 12 Aug 1990 in South Dakota ([Field Museum](https://www.fieldmuseum.org/blog/sue-t-rex), [Wikipedia](https://en.wikipedia.org/wiki/Sue_Hendrickson)).

## Streaming on a Pi 5: what's known

- **YouTube** needs no DRM, so it plays in plain Chromium. The Pi 5 has no hardware decoder for
  H.264 or VP9 (only HEVC), so YouTube's VP9/AV1 is decoded on the CPU. 1080p is fine in Kodi; in a
  browser window people report it gets rough above 1080p30
  ([Jeff Geerling](https://www.jeffgeerling.com/blog/2024/can-raspberry-pi-5-handle-4k/),
  [LibreELEC forum](https://forum.libreelec.tv/thread/29903-rpi5-slow-playback-of-even-720p-from-youtube/)).
  The dash's own RAM test already flags CarPlay video as the first CPU test on the bench.
- **Netflix, Disney+, Prime, Neon, TVNZ+, ThreeNow, Spotify** need Widevine. Raspberry Pi OS's own
  `libwidevinecdm0` package was 32-bit only and doesn't work on 64-bit OS
  ([Pi My Life Up](https://pimylifeup.com/raspberry-pi-widevine)). In 2026 Google started shipping
  Chrome for Arm64 Linux with a native Widevine module; on a Pi 5 that played BBC iPlayer and
  1080p/2K YouTube smoothly, with Netflix capped at about 720p to 1080p (software DRM, no 4K/HDR)
  ([OSFY, 27 Jul 2026](https://www.opensourceforu.com/2026/07/google-ends-widevine-workarounds-on-arm64-linux/)).
  Google hasn't formally announced it, so it might change.
- So the Pi side looks for Google Chrome first, then Chromium. **Each service still needs testing on
  the bench** before we call it working. Disney+ and the NZ apps haven't been seen working on a Pi 5
  in anything we found.
- **Data:** Netflix says up to 3 GB an hour in HD, 1 GB in SD. Worth knowing on a phone hotspot.

## Camp mode battery: the maths and the guesses

`dash/web/js/fun/campcalc.js` works out the draw and the hours left. Every wattage is a guess
until it's measured, and can be changed in Camp mode > Battery setup.

| Load | Default | Where it's from |
| --- | --- | --- |
| Pi 5 with the dash | 6 W | Raspberry Pi says the Pi 5's minimum is about 4-5 W ([Raspberry Pi white paper](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010139-WP-1-Use-case-specific%20thermal%20performance%20of%20Raspberry%20Pi%20SBCs.pdf)); video playback pushes it to 7-8 W (Geerling, above) |
| 10.1" screen | 12 W | Guess. Its brick isn't known yet. Measure it. Dimming the picture doesn't save much on an LCD, so "Screen off" turns the HDMI output off (`wlr-randr`, touch still wakes it) |
| Amp | 8 W | Guess at campsite volume, counted when music or the fire sound is on |
| Each front bar at full | 40 W | Guess. Check the bars' labels |
| Cab light at full | 15 W | Guess |

**Where the power comes from** (pick in Battery setup):

- **12V battery** (default). Size is not known yet: default 35 Ah, change it. Uses only the safe
  share: 50% for lead/AGM, 80% for lithium (LiFePO4). How full it is at the start is guessed from
  its voltage before the lights come on (12.7 V full, 12.2 V half for lead; voltage charts vary by
  a tenth or two and only mean much on a rested battery,
  [Energy Matters](https://www.energymatters.com.au/?p=1881),
  [Victron community](https://communityarchive.victronenergy.com/questions/48330/state-of-charge-vs-resting-voltage-agm.html)).
  The real safety net is the low-voltage cut at 11.9 V.
- **EV pack** through the Shinegle DC-DC. Keeps 40% in the pack for the drive out. Adds the DC-DC
  loss (88% guess) and 15 W for the controller and contactor being awake. **Big unknown:** whether
  the Shinegle's DC-DC runs with the key off. If it needs the key on, camp mode on the pack means
  leaving the key on. Check on the bench.

Examples with the defaults: cab light low + fire sound, screen on = about 30 W. From a full 35 Ah
lead battery that's about 7 hours. From the pack at 80% (keeping 40%, 3 kWh to use) it's about 60
hours. The 12V battery is the weak spot, which is a good reason to find out about the DC-DC.

## More ideas (not built yet)

- **Boombox / horn sounds:** play a roar out of an external speaker. Needs a speaker outside; check
  noise rules at campsites.
- **Rex alarm (sentry):** when locked and parked, if the tilt sensor or a camera sees movement,
  roar and flash the lights. Fits with the vehicle lock (PR #29) and the AI HAT+ 2 cameras.
- **Pet / dog mode:** keep a fan or the cab light on with a big "back soon" screen. Less use in an
  open UTV, so low priority.
- **Star map:** the night sky for where you're parked, from GPS and the time. Offline star data.
- **Trail trophies:** badges from the trip log (first 100 km, biggest climb from the tilt sensor,
  furthest from home).
- **Drawing pad** for kids, **trivia** about dinosaurs, a **stopwatch** for hill climbs (parked
  start only).
- **Light show to your own music:** sync the bars to the beat of whatever's playing.

## Files

- `dash/web/js/screens/fun.js`: the Fun screen, camp mode, light show
- `dash/web/js/fun/`: `park.js` (the rule), `campcalc.js`, `campfire.js`, `dig.js`, `duel.js`, `eggs.js`, `streams.js`
- `dash/web/css/fun.css`
- `dash/server/teryx_dash/fun.py`: `/api/fun`, `/api/fun/watch`, `/api/fun/close`, `/api/fun/screen`
- Tests: `dash/tests/test_fun.py` (runs `dash/tests/fun_js.test.mjs` with node too)

## Bench checks to do

1. Install Google Chrome for Arm64 on the Pi and try each service. Note which ones play and at what quality.
2. Check the window lands under the top bar on labwc (Wayland may ignore `--window-position`).
3. Check `wlr-randr --output HDMI-A-1 --off` blanks the screen and a touch brings it back.
4. Measure the screen, Pi, amp, bars and cab light with a clamp meter; put the numbers in Battery setup.
5. Find the 12V battery's size and type, and whether the Shinegle DC-DC runs with the key off.
