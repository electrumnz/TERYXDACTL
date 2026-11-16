"""Record the Shinegle bus while walking Sam through the procedure.

    python -m teryx decode capture --bus slcan:/dev/ttyACM0@250000
    python -m teryx decode capture --bus socketcan:can0
    python -m teryx decode capture --free          (no procedure, just marks)

At any prompt you can also type:
    r <name> <value>   a reading off the Shinegle dash, e.g.  r batt_v 74.2
    n <text>           a note, e.g.  n dash shows E-03
    m <label>          a mark with your own label
    s                  skip this step
    q                  finish and save

Everything is saved as you go, so a crash or Ctrl+C keeps what's recorded.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

from .procedure import READING_TEXT, STEPS, Step
from .session import Frame, Phase, Reading, StepRecord, format_candump, save_steps


class _Quit(Exception):
    pass


class _Skip(Exception):
    pass


class Recorder:
    """Reads the bus in the background and appends every frame to bus.log."""

    def __init__(self, bus, log_path: Path):
        self.bus = bus
        self.log = open(log_path, "a", encoding="utf-8", buffering=1)
        self.count = 0
        self.ids: dict[int, int] = {}
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> Recorder:
        self._thread.start()
        return self

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                m = self.bus.recv(0.2)
            except Exception as e:   # adaptor unplugged etc.
                print(f"\n  !! bus error: {e}")
                time.sleep(0.5)
                continue
            if m is None or m.is_error_frame or m.is_remote_frame:
                continue
            f = Frame(time.time(), m.arbitration_id, bytes(m.data), m.is_extended_id)
            self.log.write(format_candump(f))
            self.count += 1
            self.ids[f.id] = self.ids.get(f.id, 0) + 1

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
        self.log.close()

    def status(self) -> str:
        return f"[{self.count} frames, {len(self.ids)} ids]"


class Capture:
    def __init__(self, folder: Path, recorder: Recorder | None, info: dict, input_fn=input, print_fn=print):
        self.folder = folder
        self.rec = recorder
        self.info = info
        self.steps: list[StepRecord] = []
        self.input = input_fn
        self.print = print_fn
        self.current: StepRecord | None = None

    def save(self) -> None:
        save_steps(self.folder, self.steps, self.info)

    def ask(self, prompt: str) -> str:
        """Prompt until we get a plain answer. Handles r / n / m / s / q along the way."""
        while True:
            status = self.rec.status() + " " if self.rec else ""
            text = self.input(f"  {status}{prompt} > ").strip()
            now = time.time()
            low = text.lower()
            if low == "q":
                raise _Quit
            if low == "s":
                raise _Skip
            if low.startswith("r ") and self.current:
                parts = text.split()
                try:
                    self.current.readings.append(Reading(now, parts[1], float(parts[2])))
                    self.print(f"    saved reading {parts[1]} = {parts[2]}")
                except (IndexError, ValueError):
                    self.print("    reading looks like:  r batt_v 74.2")
                self.save()
                continue
            if low.startswith("n ") and self.current:
                self.current.notes.append(text[2:].strip())
                self.save()
                continue
            if low.startswith("m ") and self.current:
                self.current.phases.append(Phase(now, text[2:].strip()))
                self.print(f"    marked '{text[2:].strip()}'")
                self.save()
                continue
            return text

    def ask_readings(self, names) -> None:
        for name in names:
            label = READING_TEXT.get(name, name)
            while True:
                text = self.ask(f"Shinegle dash {label}? (Enter if it doesn't show it)")
                if not text:
                    break
                try:
                    self.current.readings.append(Reading(time.time(), name, float(text.replace(",", "."))))
                    self.save()
                    break
                except ValueError:
                    self.print("    just the number please, e.g. 74.2")

    def run_step(self, step: Step) -> None:
        self.print("")
        self.print(f"=== {step.title}{'  (optional)' if step.optional else ''} ===")
        if step.safety:
            self.print(f"  SAFETY: {step.safety}")
        self.print(f"  {step.do}")
        rec = StepRecord(step.id, step.title, time.time())
        self.current = rec
        try:
            self.ask("Enter to start (s = skip, q = finish)")
            rec.start = time.time()
            self.steps.append(rec)
            self.save()
            numeric = all(p.replace(".", "").isdigit() for p in step.phases) if step.phases else False
            if step.phases:
                for i, label in enumerate(step.phases):
                    self.ask(f"Enter the moment it's: {label.upper()}")
                    rec.phases.append(Phase(time.time(), label))
                    self.save()
                    if step.readings and ((numeric and float(label) != 0) or (not numeric and i == 0)):
                        self.print("    When it settles, read the Shinegle dash:")
                        self.ask_readings(step.readings)
                # give the last phase a few seconds before the step ends
                self.ask(f"Keep going about {max(3, step.seconds // 6)} s, then Enter to finish the step")
            else:
                if step.readings:
                    self.print("    When it settles, read the Shinegle dash:")
                    self.ask_readings(step.readings)
                self.ask(f"Carry on for about {step.seconds} s in total, then Enter to finish the step")
            rec.end = time.time()
        except _Skip:
            rec.skipped = True
            rec.end = time.time()
            if rec not in self.steps:
                self.steps.append(rec)
            self.print("    skipped")
        self.save()

    def run(self, steps) -> None:
        try:
            for step in steps:
                self.run_step(step)
        except (_Quit, KeyboardInterrupt, EOFError):
            if self.current and self.current.end is None:
                self.current.end = time.time()
        self.save()

    def run_free(self) -> None:
        rec = StepRecord("free", "Free recording", time.time())
        self.current = rec
        self.steps.append(rec)
        self.print("Recording. Type 'm label' to mark a moment, 'r name value' for a reading, q to finish.")
        try:
            while True:
                text = self.ask("")
                if text:
                    rec.phases.append(Phase(time.time(), text))
                    self.save()
        except (_Quit, _Skip, KeyboardInterrupt, EOFError):
            pass
        rec.end = time.time()
        self.save()


def capture(bus_spec: str, out_root: str | Path = "captures", only: list[str] | None = None,
            free: bool = False, include_optional: bool = True, name: str | None = None) -> Path:
    from ..canbus.bus import open_bus
    folder = Path(out_root) / (name or datetime.now().strftime("%Y-%m-%d_%H%M"))
    folder.mkdir(parents=True, exist_ok=True)
    bus = open_bus(bus_spec, listen_only=True)
    rec = Recorder(bus, folder / "bus.log").start()
    info = {"bus": bus_spec, "started": datetime.now().isoformat(timespec="seconds")}
    cap = Capture(folder, rec, info)
    print(f"\nRecording to {folder}/bus.log  (listen only, we never send on the Shinegle bus)")
    if bus_spec.startswith("socketcan"):
        print("  Make sure the interface is listen-only:  sudo scripts/setup_can_pi.sh can0 250000 listen")
    try:
        if free:
            cap.run_free()
        else:
            steps = [s for s in STEPS if (not only or s.id in only) and (include_optional or not s.optional)]
            cap.run(steps)
    finally:
        rec.stop()
        bus.shutdown()
    print(f"\nSaved {rec.count} frames from {len(rec.ids)} ids to {folder}")
    print(f"Next:  python -m teryx decode analyse {folder}")
    return folder
