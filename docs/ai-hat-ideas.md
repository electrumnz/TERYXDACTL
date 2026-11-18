# What the AI HAT+ 2 could do on the Teryx

Written 18 November 2026. Research only, nothing here is built yet.

## The short answer

- **The HAT is really good at camera AI** (spotting people, animals, vehicles, poses) on
  several cameras at once without loading the Pi's CPU. But the cheaper AI HAT+ (26 TOPS)
  does camera AI just as well
  ([Raspberry Pi](https://www.raspberrypi.com/products/ai-hat-plus-2/): the HAT+ 2's vision
  is "comparable to the Raspberry Pi AI HAT+ (26 TOPS)").
- **The only things the HAT+ 2 adds** over the old one are small chat models (LLMs),
  "ask the camera" models (VLMs) and the bigger Whisper speech models, all running on the
  HAT's own 8GB so the Pi's CPU and RAM stay free.
- **It's not faster than the Pi's CPU at writing chat answers.** Every review found the
  Pi 5's CPU writes words faster (more on this below). Where the HAT wins is how quickly
  it *starts* answering, and that it leaves the CPU alone for the dash, CarPlay and cameras.
- **Verdict:** keep the HAT+ 2 only if you want the Teryx to be a proper talking co-pilot
  (ideas 3 to 5 below). If voice is only ever going to be short commands like "front
  lightbar medium", swap to the AI HAT+ 26 TOPS and save about NZ$200. See
  [section 4](#4-is-it-worth-nz423).

## 1. What the HAT+ 2 can actually run (checked, not guessed)

Hardware: Hailo-10H chip, 40 TOPS (INT4), 8GB of its own RAM, PCIe to the Pi 5, made
until at least January 2036
([Raspberry Pi product page](https://www.raspberrypi.com/products/ai-hat-plus-2/)).

Ready-made models from Hailo's own list
([hailo_model_zoo_genai MODELS.rst](https://github.com/hailo-ai/hailo_model_zoo_genai/blob/main/docs/MODELS.rst),
Hailo's figures, HailoRT 5.5.0):

| Model | What it is | Time to first word | Words per sec (tokens/s) |
|---|---|---|---|
| Qwen2.5-1.5B-Instruct | Small chat model | 0.37 s | 7.3 |
| Qwen2-1.5B-Instruct-Function-Calling | Chat model trained to call "tools" (good for "turn on X") | 0.40 s | 7.0 |
| Llama3.2-1B-Instruct | Small chat model | 0.35 s | 9.8 |
| Gemma4-E2B-Instruct | Newer small chat model | 0.55 s | 5.5 |
| Qwen3-4B-Instruct | Biggest chat model so far | 1.53 s | 2.1 |
| Qwen2-VL-2B / Qwen3-VL-2B | "Ask the camera" (image + question in, answer out) | 1.0 to 1.5 s | 4.9 to 7.1 |
| Qwen3-VL-4B | Bigger "ask the camera" | 3.6 s | 2.3 |
| Whisper Tiny / Base / Small / Medium | Speech to text | n/a | 47 / 25 / 10 / 4.4 |

Hailo's example apps
([hailo-apps, running applications](https://github.com/hailo-ai/hailo-apps/blob/main/doc/user_guide/running_applications.md))
cover object detection with tracking, pose (people's joints), segmentation, depth from one
camera, CLIP (search pictures by words), face recognition (beta), text reading (beta),
multi-camera, lane detection, a voice assistant, and a "voice to action" demo: wake word,
Whisper, an LLM that picks a tool, then Piper speech back. That last one is very close to
what we want for "hey Teryx".

### What reviewers found

- **Chat speed: the CPU wins.** CNX Software measured tokens/s on the CPU vs the HAT:
  Qwen2.5 1.5B 11.73 vs 6.74, DeepSeek R1 1.5B 9.04 vs 6.72, Llama3.2 3B 4.78 vs 2.60. They
  called it "more like an AI decelerator than an AI accelerator" for LLMs
  ([CNX Software review](https://www.cnx-software.com/2026/01/20/raspberry-pi-ai-hat-2-review-a-40-tops-ai-accelerator-tested-with-computer-vision-llm-and-vlm-workloads/)).
  Jeff Geerling found the same: "The Pi's built-in CPU trounces the Hailo 10H". The HAT is
  capped at about 3 W, the Pi's chip can use about 10 W
  ([Jeff Geerling](https://jeffgeerling.com/blog/2026/raspberry-pi-ai-hat-2)).
- **Starting to answer: the HAT wins.** Hailo's figures for a 96-word prompt on Qwen2.5
  1.5B: 2.04 s on the Pi CPU vs 0.32 s on the HAT
  ([Raspberry Pi / Hailo blog](https://www.raspberrypi.com/news/when-and-why-you-might-need-the-raspberry-pi-ai-hat-plus-2/),
  vendor written). For voice, where the answer is one short sentence, the start delay
  matters more than words per second. Feeding the model the dash state (battery, speed,
  4WD, lights) makes the prompt long, which is exactly where the CPU is slow.
- **Camera AI: about 10x the CPU.** Geerling: "It all ran quite fast, and 10x faster than
  on the Pi's CPU". For scale, Ultralytics measured their smallest YOLO model at 67 ms per
  frame on the Pi 5 CPU at its best setting
  ([Ultralytics Pi guide](https://docs.ultralytics.com/guides/raspberry-pi/)), so the CPU
  could just about do one camera at a low frame rate while doing nothing else.
- **Running camera AI and a chat model together didn't work for Geerling in January**:
  "segmentation faults or 'device not ready'". Hailo's software has had several releases
  since (the model list above is much longer than at launch), but **this is the first
  thing to test on the bench**.
- **Power:** CNX measured a whole Pi 5 + HAT+ 2 running an LLM at about 7.2 to 7.6 W.

### Speech on the CPU, for comparison

whisper.cpp Tiny and Base run at about real time on a Pi 5 using all 4 cores; Small runs
slower than real time
([PromptQuorum comparison](https://www.promptquorum.com/power-local-llm/local-whisper-stt-comparison-2026),
secondary source, I found no first-hand Pi 5 benchmark). So simple commands with a small
word list are fine on the CPU, as already planned, but the CPU is flat out while it
listens. Bigger Whisper models (Small, Medium) are Hailo-10H only in Hailo's GenAI list.
The older Hailo-8 can run Whisper Tiny/Base through Hailo's speech app
([Hailo community](https://community.hailo.ai/t/automatic-speech-recognition-pipeline-with-whisper-model/13127?page=2)).

## 2. Ideas, ranked

Ranked by how useful it is on the Teryx, then how easy. "Which HAT" says what's really
needed: **CPU** = the Pi can do it alone, **Any HAT** = the cheaper AI HAT+ does it too,
**HAT+ 2** = only the HAT+ 2 can do it well.

Effort: **S** = a day or two of thread work, **M** = a week-ish plus bench testing,
**L** = needs our own training data or lots of testing.

None of these touch safety controls directly. Anything that stops something (like the
winch) sends a *request* to the Pico, same as a screen button, and the hand switches and
the Pico's own rules still win.

| # | Idea | Needs | Which HAT | Effort |
|---|---|---|---|---|
| 1 | **Smart reverse and trailer camera** | Rear cam (+ trailer cam) | Any HAT | M |
| 2 | **Winch safety watch** | Front cam | Any HAT | M |
| 3 | **Talking co-pilot** | Mic, speaker, dash state | HAT+ 2 | M |
| 4 | **Voice that works in the wind** | Mic | HAT+ 2 (Whisper Small) | S |
| 5 | **"Ask the camera"** | Any cam | HAT+ 2 | M |
| 6 | **Guard mode when locked** | Cams, Tailscale | Any HAT | M |
| 7 | **Stock and oncoming-vehicle spotter for the light bars** | Front cam | Any HAT | M (L for deer) |
| 8 | **Ride diary** | Trip logs | CPU | S |
| 9 | **T. rex eyes that follow you** | Front cam | Any HAT | S |
| 10 | **Rock / step height ahead** | Front cam | Any HAT | L, not reliable |

### 1. Smart reverse and trailer camera

Boxes around people, dogs, stock and vehicles behind you, with a beep when something
is close and moving in while you're in reverse. Works on the trailer camera too, which is
where you can't see a kid or dog behind the trailer. Hailo's `hailo-detect` app already
does detection with tracking on several streams; we'd send the boxes to the dash over the
existing websocket and draw them on the camera view.

Why the HAT: doing this on the CPU at a useful frame rate would eat the CPU that CarPlay
video already needs (the Pi 5 has no H.264 hardware decoder, see
[`shopping-list.md`](shopping-list.md)).

### 2. Winch safety watch

When the winch is running, the front camera watches the area around the line. If a
person walks into it, the dash flashes a big warning and asks the Pico to pause the pull.
Uses pose/person detection (`hailo-pose`). It only warns and requests: the winch hand
switches and the Pico stay in charge. Ties in with the timed pull already built (PR #22).
Needs testing for how well the front camera actually sees the line area.

### 3. Talking co-pilot

Beyond fixed commands: "how far can I get and still make it back?", "why won't it go into
4WD?", "what's the battery temp doing?". A small function-calling model (Qwen2 1.5B
function-calling is in Hailo's list) gets the dash state and a list of safe "tools"
(read range, set lights, start a guided check) and answers in a sentence through Piper
speech. Hailo's voice-to-action demo is basically this already.

Why the HAT+ 2: the prompt with all the dash state is long, so the CPU would take a couple
of seconds to start answering and hog all 4 cores while doing it. On the HAT it starts in
about 0.4 s.

Honest limits: 1 to 2B models get things wrong. Hailo's own forum has users saying the
small models "are simply not very accurate"
([Hailo community](https://community.hailo.ai/t/qwen-3-4b-on-hailo10h/18818)). So the
model only *picks* from our fixed list of actions and reads numbers we give it. It never
makes up numbers or controls anything directly.

### 4. Voice that works in the wind

Even for simple commands, Whisper Small hears far better than Tiny/Base, and an open
side-by-side on a gravel track with the motor whining is a hard place for speech. Whisper
Small runs on the HAT+ 2 at about 10 tokens/s and leaves the CPU free. Cheapest of the
HAT+ 2 ideas to try: record some real cab audio on the first drive and test Base on the
CPU vs Small on the HAT.

### 5. "Ask the camera"

Tap a camera and ask: "is the gate shut?", "is the load still strapped?", "what's on the
track ahead?". A 2B vision model answers in a sentence or two, taking about 1 to 1.5 s to
start. More fun than essential, and like the chat model it can be wrong, so never for
anything safety related. CNX got Hailo's VLM demo working, though with odd camera colours.

### 6. Guard mode when locked

When the vehicle lock is on (PR #29), cameras watch for people near the Teryx. On a hit:
the T. rex lock screen wakes, a snapshot is saved, and a notification goes to your phone
over Tailscale. Hailo's face recognition app (beta) could skip alarms for you and family.

Catch: the Pi + HAT draws about 7 W while doing this (CNX), so leave it as an option with
a timer, and check what the 12V side can spare. The traction pack is much bigger, but
only if a DC-DC stays on when parked, which isn't decided.

### 7. Stock and oncoming-vehicle spotter for the light bars

Front camera at night picks out cattle, sheep, horses, dogs and vehicles (all in the
standard COCO set YOLO is trained on), warns on the dash, and could drop the light bars
to low when a vehicle's coming. Deer, goats and pigs aren't in the standard set, so those
would need our own training photos (that's the L). Depends on the open question of
whether the light bars are dimmable.

### 8. Ride diary

After each ride, a short write-up: where you went, kWh used, Wh/km, steepest bit, how long
in 4WD and diff lock, winch pulls. The numbers come from our logs and the model only
writes the sentences. No HAT needed: it can run on the CPU when parked, where time
doesn't matter.

### 9. T. rex eyes that follow you

On the lock screen, the T. rex's eye follows whoever walks past the front. Pure fun,
cheap once detection is running for other ideas. Fits the dash theme.

### 10. Rock or step height ahead (not recommended yet)

Hailo has depth-from-one-camera and segmentation demos. But depth from a single camera
only knows "nearer" and "further", not centimetres, and the segmentation models are
trained on city roads, not bush tracks. Wouldn't trust it for clearance. Worth revisiting
only if a second camera is added for stereo depth (Hailo has a stereo depth demo too).

### What the HAT won't help with

Decoding the Shinegle CAN bus, range maths, maps, the 4WD/diff logic, CarPlay video
decode. All of that is normal code on the CPU.

## 3. First bench tests once the Pi and HAT arrive

1. `hailo-detect` on the rear camera **while** the dash and a CarPlay-sized video are
   running. Check CPU load and frame rate.
2. Camera AI and a chat model **at the same time** (Geerling's segfault). If it still
   fails, ideas 1 and 3 can't both run, which matters a lot for the verdict.
3. Record real cab audio with the motor running; compare Whisper Base on the CPU with
   Small on the HAT.
4. HAT temperature in the sealed Pi box on a hot day. The box has a fan for this
   ([`shopping-list.md`](shopping-list.md)).

## 4. Is it worth NZ$423?

Prices (PB Tech NZ, inc GST, from search results so check live before buying):

| Board | Chip | Price | Camera AI | Chat / ask-the-camera | Big Whisper |
|---|---|---|---|---|---|
| AI HAT+ 13 TOPS | Hailo-8L | ~NZ$132 to 144 ([PB Tech](https://www.pbtech.co.nz/product/SEVRBP0543/Raspberry-Pi-Official-AI-HAT-13-TOPS-Hallo-AI-Acce)) | Yes, fewer cameras | No | No |
| AI HAT+ 26 TOPS | Hailo-8 | ~NZ$225 ([PB Tech](https://www.pbtech.co.nz/product/SEVRBP0545/Raspberry-Pi-5-Official-AI-HAT-26-TOPS-Hailo-AI-Ac)) | Yes | No | No |
| **AI HAT+ 2** | Hailo-10H | ~NZ$423 ([PB Tech](https://www.pbtech.co.nz/product/SEVRBP0446/Raspberry-Pi-5-Official-AI-Hat-2)) | Yes, same as 26 TOPS | Yes | Yes |

The extra ~NZ$200 over the 26 TOPS board buys ideas 3, 4 and 5 and nothing else.
Geerling's own conclusion was "it's hard to say 'yes, buy this thing'", and CNX thought it
suits security camera setups more than chat.

**My call:** for your "buy once, with headroom" rule and a voice assistant that's
definitely happening, the HAT+ 2 is defensible. It's the only one that can grow into a
proper co-pilot, and it keeps speech and chat off a CPU that will already be busy with
CarPlay and cameras. But if you're honest that voice will mostly be "lights on, 4WD in",
the AI HAT+ 26 TOPS does everything else the same for about NZ$200 less. Nothing is bought
yet, so either choice is easy. Everything in ideas 1, 2, 6, 7 and 9 works on both, so
the code we write doesn't depend on which you pick.
