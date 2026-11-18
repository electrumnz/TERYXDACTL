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
  (idea 6 below, plus "ask the camera" and better voice in the wind). If voice is only ever going to be short commands like "front
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

## 2. The top 10 (the "no way" list)

**Which HAT:** *Any HAT* = the cheaper AI HAT+ does it too. *HAT+ 2* = needs the HAT+ 2.
*No HAT* = the Pi alone. **Effort:** S = days, M = a week or two plus bench testing,
L = needs our own training footage.

Nothing here drives the vehicle by itself. Anything that changes 4WD, diff or winch is a
*suggestion* you tap to accept, or a *request* to the Pico, which keeps its own safety
rules. The hand switches always win.

| # | Idea | Which HAT | Effort | Honest catch |
|---|---|---|---|---|
| 1 | **Track reader.** Front cam reads the trail ahead (mud, puddle, deep water, rock, grass) and pops up "mud ahead: 4WD + diff 60%?" before you get there. One tap to accept. | Any HAT | L | Off-road training sets exist (RELLIS-3D even splits "puddle" from "deep water"), but the best models only score about 52% on it vs about 81% on city roads ([RELLIS-3D paper](https://arxiv.org/abs/2011.12954)). Advice only, and it needs our own footage to get good |
| 2 | **Water crossing mode.** Spots water ahead, offers 4WD + diff lock + slow mode, starts recording, and checks for wheel slip on the way out. | Any HAT | M | A camera can't see the bottom of muddy water, so it can't tell you the depth. Real depth needs a wading sensor on the body (not priced) |
| 3 | **"Take me home."** Every ride leaves a breadcrumb trail. Say "hey Teryx, take me home" and get arrows back the way you came, with no signal. Snapshots at each fork so you recognise them. | No HAT | M | Needs the GPS puck (PR #30). Thick bush can throw GPS off, so the photos help |
| 4 | **Night pest hunter.** Thermal camera + HAT spots pigs, deer, goats and possums in the dark, pins each one on the map with a count, and the T. rex calls "pig, left side". | Any HAT | L | Needs a USB thermal camera (not priced). No ready-made possum or pig model found; deer-on-thermal has been done ([arXiv](https://arxiv.org/abs/2509.18779)) so we'd train our own. A hobbyist ran a Pi 5 + thermal + YOLO at night at about 10 W ([WILDLABS](https://wildlabs.net/en/comment/12893)) |
| 5 | **Stock counter.** Drive along the fence and it counts the mob: "142 sheep in the back paddock, 3 fewer than last week." | Any HAT | M | Sheep and cows are in YOLO's standard set, so it works day one, but a tight mob overlaps and will undercount. Test against a hand count |
| 6 | **T. rex co-pilot.** Proper personality: banter, a roar when the diff locks at 100%, battery warnings in character, answers "why won't it go into 4WD?" from live data. | HAT+ 2 | M | Small models get facts wrong, so it only reads numbers we give it and picks from a fixed list of actions. Starts talking in about 0.4 s on the HAT vs about 2 s on the CPU |
| 7 | **Auto highlight reel.** Records the front cam and auto-cuts a 60 s clip of the best bits (steep climbs, splashes, animals, winch pulls, big lean) with speed, lean and diff % on screen. Straight to your phone. | Any HAT | M-L | The Pi 5 has no video encoder chip; software 1080p30 uses about 60% of the CPU ([Raspberry Pi white paper](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010033-WP-1-H.264%20encoding%20performance%20on%20Raspberry%20Pi%205_series%20computers.pdf)). So one camera at a time, and a USB SSD |
| 8 | **Crash cam.** Big jolt, near-rollover lean or a hard stop saves the last 30 s from every camera plus all the CAN data. | No HAT | M | Needs a tilt/jolt sensor (IMU), not on the parts list yet. Same CPU limit as #7 |
| 9 | **Trail scores and "will I make it back?"** Every trail gets a difficulty score (grade, slip, diff use, Wh/km). Head down one you've done and it says "used 1.8 kWh last time, you'll be back with 34%." Plus coaching: "lock the diff before that climb, you spun 3 times." | No HAT | M | Only for trails you've driven before. Builds on the learned Wh/km in PR #24 |
| 10 | **Winch spotter.** Front cam watches the line and the danger zone. Talks you through rigging, calls "person in the zone" and asks the Pico to pause the pull. | Any HAT | M | Advisory only. Depends on how much of the line the front camera can actually see |

**Also fun:** guard mode where the T. rex wakes, tracks and roars at anyone poking around
the locked Teryx and sends you a photo (about 7 W while watching, so on a timer); T. rex
eyes that follow you; "ask the camera" ("is the gate shut?", HAT+ 2 only); Whisper Small
so voice works in the wind (HAT+ 2 only); auto-dipping the light bars for oncoming
vehicles (if they turn out dimmable).

**Notice the pattern:** of these 10, only #6 truly needs the HAT+ 2. Most need *a* HAT,
and #3, #8 and #9 need none. That's why the verdict below hasn't changed.

**Not worth it yet:** rock or step height from one camera. Single-camera depth only knows
"nearer" and "further", not centimetres.

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

The extra ~NZ$200 over the 26 TOPS board buys the T. rex co-pilot (idea 6), "ask the camera" and Whisper Small, and nothing else.
Geerling's own conclusion was "it's hard to say 'yes, buy this thing'", and CNX thought it
suits security camera setups more than chat.

**My call:** for your "buy once, with headroom" rule and a voice assistant that's
definitely happening, the HAT+ 2 is defensible. It's the only one that can grow into a
proper co-pilot, and it keeps speech and chat off a CPU that will already be busy with
CarPlay and cameras. But if you're honest that voice will mostly be "lights on, 4WD in",
the AI HAT+ 26 TOPS does everything else the same for about NZ$200 less. Nothing is bought
yet, so either choice is easy. Every camera idea in the top 10 works on both, so
the code we write doesn't depend on which you pick.
