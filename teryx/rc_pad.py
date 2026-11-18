"""Bluetooth gamepad paired straight to the Pi: RC with no phone.

For close-range work (hitching up, lining up the trailer) Sam can pair an Xbox or
8BitDo style pad to the Pi and drive with that instead of the phone. There's no
screen in his hand, so the dash screen shows what RC is doing.

This turns the pad's Linux input events into the same `Radio` packets the phone
and the handheld send (link "bt"), so every RC rule in rc_mode.py applies as is:
the 200 ms timeout, dead-man, speed caps, wheelspin and water cut-outs. If
Bluetooth drops, the packets stop (or we send failsafe straight away when Linux
says the pad has gone) and the RC box stops and holds on the brake.

Layout (the same as the phone app's gamepad layout where it can be):

    LB (L1) held        dead-man. Let go and it stops and holds
    left stick Y        go / brake, RC-car style: push to go forward, pull to go
                        back, pull against the way you're moving to brake.
                        F-N-R follows the stick (stop and re-centre to swap)
    RT / LT             go / brake as well, if you'd rather use triggers
    right stick X       steer
    A held / B held     winch in / winch out (only when stopped, neutral, no throttle)
    D-pad up            lights on/off
    D-pad down          2WD / 4WD
    D-pad left / right  diff lock down / up 25 %
    Start held 1 s      RC on / off (arm, disarm). Arming needs LB let go and sticks centred
    Select / View       e-stop. Stays on until RC is turned off and on again

The dash buttons (lights, 4WD, diff) go to the main control box as normal dash
commands, with the same rules as pressing them on the screen.

Reading the pad needs python-evdev (BSD licence) on the Pi; the mapping itself
is plain Python so it can be tested anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .rc_mode import NEUTRAL, Radio

# Linux input codes (linux/input-event-codes.h). Kept here so tests don't need evdev.
EV_KEY, EV_ABS = 0x01, 0x03
ABS_X, ABS_Y, ABS_Z, ABS_RX, ABS_RY, ABS_RZ = 0x00, 0x01, 0x02, 0x03, 0x04, 0x05
ABS_GAS, ABS_BRAKE = 0x09, 0x0A          # some pads (xpadneo) report the triggers here
ABS_HAT0X, ABS_HAT0Y = 0x10, 0x11
BTN_SOUTH, BTN_EAST, BTN_NORTH, BTN_WEST = 0x130, 0x131, 0x133, 0x134
BTN_TL, BTN_TR, BTN_SELECT, BTN_START, BTN_MODE = 0x136, 0x137, 0x13A, 0x13B, 0x13C

DEADZONE = 0.08
ARM_HOLD_S = 1.0
DIFF_STEP = 25


@dataclass
class Axis:
    lo: int = -32768
    hi: int = 32767

    def norm(self, v: int) -> float:
        """-1..+1 for sticks."""
        mid = (self.lo + self.hi) / 2
        half = (self.hi - self.lo) / 2 or 1
        x = max(-1.0, min(1.0, (v - mid) / half))
        return 0.0 if abs(x) < DEADZONE else x

    def norm01(self, v: int) -> float:
        """0..1 for triggers."""
        x = (v - self.lo) / ((self.hi - self.lo) or 1)
        x = max(0.0, min(1.0, x))
        return 0.0 if x < DEADZONE else x


# Typical ranges. The reader overwrites these with what the pad itself reports.
DEFAULT_AXES = {
    ABS_X: Axis(), ABS_Y: Axis(), ABS_RX: Axis(), ABS_RY: Axis(),
    ABS_Z: Axis(0, 1023), ABS_RZ: Axis(0, 1023), ABS_GAS: Axis(0, 1023), ABS_BRAKE: Axis(0, 1023),
}


@dataclass
class PadMapper:
    """Pad events in, Radio packets and dash commands out."""
    axes: dict = field(default_factory=lambda: dict(DEFAULT_AXES))
    connected: bool = True
    armed: bool = False
    estop: bool = False
    _v: dict = field(default_factory=dict)        # axis code -> latest value (normalised)
    _held: set = field(default_factory=set)       # button codes held
    _start_at: float | None = None
    _start_used: bool = False
    _out: list = field(default_factory=list)      # dash commands waiting to go

    # ---- events in -------------------------------------------------------------
    def event(self, now: float, etype: int, code: int, value: int) -> None:
        if etype == EV_ABS:
            if code in (ABS_HAT0X, ABS_HAT0Y):
                self._hat(code, value)
            elif code in (ABS_Z, ABS_RZ, ABS_GAS, ABS_BRAKE):
                self._v[code] = self.axes.get(code, Axis(0, 1023)).norm01(value)
            else:
                self._v[code] = self.axes.get(code, Axis()).norm(value)
        elif etype == EV_KEY:
            if value:
                self._held.add(code)
                if code == BTN_START:
                    self._start_at, self._start_used = now, False
                elif code == BTN_SELECT:
                    self.estop = True
            else:
                self._held.discard(code)
                if code == BTN_START:
                    self._start_at = None

    def lost(self) -> None:
        """Linux says the pad has gone (Bluetooth dropped, flat battery)."""
        self.connected = False
        self._held.clear()
        self._v.clear()
        self._start_at = None

    def found(self) -> None:
        """Pad back. RC stays off until it's armed again on purpose."""
        self.connected = True
        self.armed = False
        self.estop = False

    def _hat(self, code: int, value: int) -> None:
        if value == 0:
            return
        if code == ABS_HAT0Y:
            self._out.append(("lights", "toggle") if value < 0 else ("fourwd", "toggle"))
        else:
            self._out.append(("diff", -DIFF_STEP if value < 0 else DIFF_STEP))

    # ---- packets out -------------------------------------------------------------
    def commands(self) -> list:
        """Dash commands since last time: ("lights","toggle"), ("fourwd","toggle"), ("diff", +/-25),
        ("rc","arm"|"disarm")."""
        out, self._out = self._out, []
        return out

    def packet(self, now: float) -> Radio:
        """The Radio packet to send this tick (send at 20-50 Hz)."""
        if not self.connected:
            return Radio(t=now, failsafe=True, link="bt")
        self._arm_button(now)
        v = self._v.get
        drive = -v(ABS_Y, 0.0)                    # Linux: stick up is negative
        trig = max(v(ABS_RZ, 0.0), v(ABS_GAS, 0.0)) - max(v(ABS_Z, 0.0), v(ABS_BRAKE, 0.0))
        if abs(trig) > abs(drive):
            drive = trig
        winch = 1 if BTN_SOUTH in self._held else -1 if BTN_EAST in self._held else 0
        return Radio(t=now, steer=v(ABS_RX, 0.0), direction=NEUTRAL, drive=drive,
                     deadman=BTN_TL in self._held, estop=self.estop, winch=winch, link="bt")

    def _arm_button(self, now: float) -> None:
        if self._start_at is None or self._start_used or now - self._start_at < ARM_HOLD_S:
            return
        self._start_used = True
        if self.armed:
            self.armed, self.estop = False, False
            self._out.append(("rc", "disarm"))
        elif self.ready_to_arm():
            self.armed = True
            self._out.append(("rc", "arm"))
        else:
            self._out.append(("rc", "not_centred"))

    def ready_to_arm(self) -> bool:
        """Like the phone: no arming with the dead-man held or a stick pushed."""
        sticks = (abs(self._v.get(c, 0.0)) for c in (ABS_Y, ABS_RX, ABS_Z, ABS_RZ, ABS_GAS, ABS_BRAKE))
        return BTN_TL not in self._held and not self.estop and all(s == 0.0 for s in sticks)


def run(device_path: str, send, on_command, hz: float = 50.0) -> None:  # pragma: no cover (needs a pad)
    """Read a pad with python-evdev and send packets until stopped.

    send(radio) goes on to the RC box the same way phone packets do; on_command(cmd)
    handles lights/4WD/diff and arm/disarm like a dash button press. If the pad drops,
    a failsafe packet goes out straight away, then we wait for it to come back.
    """
    import select
    import time

    import evdev  # BSD licence. pip install evdev

    m = PadMapper()
    period = 1.0 / hz
    while True:
        try:
            dev = evdev.InputDevice(device_path)
            for code in list(m.axes):
                info = dev.absinfo(code) if code in dict(dev.capabilities().get(EV_ABS, [])) else None
                if info:
                    m.axes[code] = Axis(info.min, info.max)
            m.found()
            on_command(("rc", "pad_connected"))
            nxt = time.monotonic()
            while True:
                r, _, _ = select.select([dev.fd], [], [], max(0.0, nxt - time.monotonic()))
                if r:
                    for e in dev.read():
                        m.event(time.monotonic(), e.type, e.code, e.value)
                now = time.monotonic()
                if now >= nxt:
                    send(m.packet(now))
                    for c in m.commands():
                        on_command(c)
                    nxt = now + period
        except (OSError, FileNotFoundError):
            m.lost()
            send(m.packet(time.monotonic()))
            on_command(("rc", "pad_lost"))
            time.sleep(0.5)
