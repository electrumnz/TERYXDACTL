"""A capture session on disk: the CAN log plus what was happening when.

    captures/2026-11-20_1012/
        bus.log      every frame, candump format (works with canplayer, SavvyCAN,
                     python -m teryx replay)
        steps.json   step start/end times, phase marks, readings, notes

Logs recorded with other tools can be analysed too: candump (.log), SavvyCAN
CSV (.csv) and anything python-can reads (.asc, .blf, .trc). Without a
steps.json there are no markers, so the analysis can only list ids and spot
counters.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Frame:
    t: float
    id: int
    data: bytes
    ext: bool = False


@dataclass
class Phase:
    t: float
    label: str


@dataclass
class Reading:
    t: float
    name: str
    value: float


@dataclass
class StepRecord:
    id: str
    title: str
    start: float
    end: float | None = None
    phases: list[Phase] = field(default_factory=list)
    readings: list[Reading] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    skipped: bool = False

    def phase_at(self, t: float) -> str | None:
        label = None
        for p in self.phases:
            if p.t <= t:
                label = p.label
        return label


@dataclass
class Session:
    frames: list[Frame]
    steps: list[StepRecord] = field(default_factory=list)
    info: dict = field(default_factory=dict)
    path: Path | None = None

    @property
    def readings(self) -> list[tuple[StepRecord, Reading]]:
        return [(s, r) for s in self.steps for r in s.readings]

    def step(self, step_id: str) -> StepRecord | None:
        return next((s for s in self.steps if s.id == step_id and not s.skipped), None)

    def step_at(self, t: float) -> StepRecord | None:
        for s in self.steps:
            if not s.skipped and s.start <= t < (s.end if s.end is not None else float("inf")):
                return s
        return None


# --------------------------------------------------------------------------- candump format

def format_candump(f: Frame, channel: str = "can0") -> str:
    ident = f"{f.id:08X}" if f.ext else f"{f.id:03X}"
    return f"({f.t:.6f}) {channel} {ident}#{f.data.hex().upper()}\n"


def parse_candump_line(line: str) -> Frame | None:
    parts = line.split()
    if len(parts) < 3 or not parts[0].startswith("("):
        return None
    try:
        t = float(parts[0].strip("()"))
        ident, _, data = parts[2].partition("#")
        if data.startswith("R"):
            data = ""   # remote frame: no data
        return Frame(t, int(ident, 16), bytes.fromhex(data), ext=len(ident) > 3)
    except ValueError:
        return None


def read_candump(path: Path) -> list[Frame]:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return [f for f in map(parse_candump_line, fh) if f is not None]


def read_savvycan_csv(path: Path) -> list[Frame]:
    """SavvyCAN's own CSV: Time Stamp,ID,Extended,Dir,Bus,LEN,D1..D8 (time in microseconds)."""
    frames = []
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        rows = csv.reader(fh)
        header = [h.strip().lower() for h in next(rows, [])]
        ts, idc = header.index("time stamp"), header.index("id")
        ext, ln = header.index("extended"), header.index("len")
        for row in rows:
            if len(row) <= ln:
                continue
            n = int(row[ln])
            data = bytes(int(x, 16) for x in row[ln + 1: ln + 1 + n])
            frames.append(Frame(int(row[ts]) / 1e6, int(row[idc], 16), data,
                                ext=row[ext].strip().lower() in ("true", "1")))
    return frames


def read_log(path: str | Path) -> list[Frame]:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        head = path.read_text(encoding="utf-8", errors="replace")[:200].lower()
        if head.startswith("time stamp"):
            return read_savvycan_csv(path)
    if path.suffix.lower() in (".log", ".txt", ""):
        frames = read_candump(path)
        if frames:
            return frames
    import can  # python-can handles .asc, .blf, .trc and its own .csv
    return [Frame(m.timestamp, m.arbitration_id, bytes(m.data), m.is_extended_id)
            for m in can.LogReader(str(path)) if not m.is_error_frame and not m.is_remote_frame]


# --------------------------------------------------------------------------- sessions

def save_steps(folder: Path, steps: list[StepRecord], info: dict) -> None:
    out = {"info": info, "steps": [asdict(s) for s in steps]}
    tmp = folder / "steps.json.tmp"
    tmp.write_text(json.dumps(out, indent=1), encoding="utf-8")
    tmp.replace(folder / "steps.json")


def load_steps(path: Path) -> tuple[list[StepRecord], dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    steps = []
    for s in raw.get("steps", []):
        steps.append(StepRecord(
            s["id"], s.get("title", s["id"]), s["start"], s.get("end"),
            [Phase(**p) for p in s.get("phases", [])],
            [Reading(**r) for r in s.get("readings", [])],
            list(s.get("notes", [])), bool(s.get("skipped", False))))
    return steps, raw.get("info", {})


def load(path: str | Path) -> Session:
    """A session folder, or a bare log file (with an optional steps.json beside it)."""
    path = Path(path)
    if path.is_dir():
        logs = [p for p in (path / "bus.log",) if p.exists()] or sorted(
            p for p in path.iterdir() if p.suffix.lower() in (".log", ".csv", ".asc", ".blf", ".trc"))
        if not logs:
            raise FileNotFoundError(f"no CAN log in {path}")
        log, steps_file = logs[0], path / "steps.json"
    else:
        log, steps_file = path, path.with_name("steps.json")
    frames = sorted(read_log(log), key=lambda f: f.t)
    steps, info = load_steps(steps_file) if steps_file.exists() else ([], {})
    return Session(frames, steps, info, path)
