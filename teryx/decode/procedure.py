"""The guided capture procedure: what Sam does, in what order, while we record.

Each step is one thing changing at a time, so the analysis can line up "what
Sam did" with "which bytes moved". Steps with ``phases`` ask Sam to press Enter
as each phase starts (e.g. "forward", "neutral", "reverse"). That gives the
analysis exact labels, which is how it finds on/off flags and value tables.

``readings`` are numbers Sam reads off the Shinegle dash or programmer during
the step (battery volts, speed ...). One reading pins the scale of a signal;
two or more different readings pin the scale and the offset.

``hints`` say which Teryx signal names we expect to find in that step, and how
they behave:

    sweep   smooth rise and fall (throttle, rpm, speed, current)
    phases  takes one value per phase (direction, mode, brake, faults)
    steady  doesn't change much but has a value we can read (volts, temps, soc)
    gone    frames that vanish during this step (who sends them)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Step:
    id: str
    title: str
    do: str                                   # what Sam does, plain words
    seconds: int = 20                         # rough length
    phases: tuple[str, ...] = ()              # Enter-marked phases, in order
    readings: tuple[str, ...] = ()            # values to read off the Shinegle dash
    hints: dict = field(default_factory=dict)  # teryx signal name -> sweep | phases | steady | gone
    safety: str = ""
    optional: bool = False


READING_TEXT = {
    "batt_v": "battery volts",
    "soc": "battery % (state of charge)",
    "speed": "speed in km/h",
    "rpm": "motor rpm",
    "batt_a": "battery amps (+ when driving, - when regen or charging)",
    "motor_temp": "motor temperature in C",
    "ctrl_temp": "controller temperature in C",
    "throttle": "throttle %",
    "odometer": "odometer in km",
}

SAFETY_WHEELS_UP = ("Rear wheels (and front if 4WD is engaged) OFF THE GROUND on stands, "
                    "transfer case in 2WD, nobody near the wheels.")

STEPS: tuple[Step, ...] = (
    Step("key_off", "Key off",
         "Everything off. Sniffer plugged into the Shinegle CAN wires. Just wait.", 10,
         hints={}),
    Step("key_on", "Key on, not ready",
         "Turn the key on but don't switch to ready/run. Wait.", 20,
         readings=("batt_v", "soc", "motor_temp", "ctrl_temp", "odometer"),
         hints={"batt_v": "steady", "soc": "steady", "motor_temp": "steady",
                "ctrl_temp": "steady", "odometer": "steady"}),
    Step("ready_idle", "Ready, sitting still",
         "Switch to ready/run. Neutral, foot off everything. Don't touch anything. "
         "This is the baseline everything else is compared to.", 30,
         readings=("batt_v", "soc"), hints={"ready": "steady"}),
    Step("dash_unplugged", "Shinegle dash unplugged",
         "Still in ready. Unplug the Shinegle dash for about 15 seconds, then plug it back in. "
         "Frames that stop are sent by the dash. If everything stops, the controller only talks "
         "when asked, and we copy what the dash asks.", 30,
         phases=("unplugged", "plugged back in"), hints={"_dash_frames": "gone"}),
    Step("brake", "Brake on and off",
         "Neutral. Press Enter as you press the brake, and again as you let go. Three times.", 20,
         phases=("pressed", "released") * 3, hints={"brake": "phases"}),
    Step("direction", "Forward, neutral, reverse",
         "Foot off the throttle. Move the direction switch, pressing Enter as each one is selected.", 30,
         phases=("forward", "neutral", "reverse", "neutral", "forward", "neutral"),
         hints={"direction": "phases"}),
    Step("mode", "Drive modes",
         "Neutral. Switch through the modes, pressing Enter as each one is selected. "
         "Skip this step if your switch doesn't have modes.", 30,
         phases=("eco", "normal", "sport", "eco"), hints={"mode": "phases"}, optional=True),
    Step("throttle_sweep", "Slow throttle sweeps (wheels up)",
         "Forward. Squeeze the throttle slowly from nothing to full over about 5 seconds, then "
         "slowly back to nothing. Do it three times.", 40,
         hints={"throttle": "sweep", "rpm": "sweep", "speed": "sweep", "batt_a": "sweep"},
         safety=SAFETY_WHEELS_UP),
    Step("throttle_hold", "Throttle holds (wheels up)",
         "Forward. Hold the throttle steady at about a quarter, half and three quarters. "
         "At each hold, press Enter and type what the Shinegle dash shows.", 60,
         phases=("0", "25", "50", "75", "0"), readings=("speed", "rpm", "batt_a", "batt_v"),
         hints={"throttle": "phases", "speed": "sweep", "rpm": "sweep", "batt_a": "sweep"},
         safety=SAFETY_WHEELS_UP),
    Step("regen", "Regen (wheels up)",
         "Forward. Spin the wheels up to about half throttle, then let go of the throttle "
         "completely and press Enter as you let go. Do it three times.", 40,
         phases=("spin up", "let go") * 3, readings=("batt_a",),
         hints={"batt_a": "sweep", "rpm": "sweep"}, safety=SAFETY_WHEELS_UP),
    Step("reverse_drive", "Reverse (wheels up)",
         "Reverse. Gently squeeze the throttle to about a quarter and back, three times.", 30,
         hints={"rpm": "sweep", "speed": "sweep", "direction": "steady"}, safety=SAFETY_WHEELS_UP),
    Step("drive_flat", "Slow drive on flat ground",
         "Optional, if it's safe to drive. Wheels on the ground, drive slowly in a straight line "
         "and read the speed off the Shinegle dash a few times.", 60,
         readings=("speed", "batt_a", "batt_v"), hints={"speed": "sweep", "rpm": "sweep"},
         optional=True),
    Step("charge", "Charging",
         "Key off (or as you normally charge). Plug in the charger, leave it a minute, then unplug.", 90,
         phases=("charger in", "charger out"), readings=("batt_v", "soc", "batt_a"),
         hints={"batt_a": "phases", "batt_v": "steady"}, optional=True),
    Step("programmer", "Shinegle programmer",
         "Key on. Plug in the Shinegle programmer and read the settings. Type any numbers it shows "
         "as readings (r name value) or notes (n text). Unplug it when done.", 90,
         phases=("programmer in", "programmer out"), hints={"_programmer_frames": "gone"},
         optional=True),
    Step("fault_throttle", "Throttle fault",
         "Key on, NOT ready, wheels up. Unplug the throttle connector, wait for the fault to show "
         "on the Shinegle dash, plug it back in, then cycle the key if needed to clear it. "
         "Type the fault code the dash shows as a note.", 40,
         phases=("unplugged", "plugged back in"), hints={"fault_throttle": "phases"},
         safety="Only with the key on and not ready. Never unplug anything while the motor is turning.",
         optional=True),
    Step("key_off_end", "Key off",
         "Turn the key off and wait a few seconds.", 10, readings=("odometer",)),
)

BY_ID = {s.id: s for s in STEPS}
