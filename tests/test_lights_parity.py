"""The Pico's C light rules (firmware/control-box/src/core/lights.c) must match teryx/lights.py.

Builds a tiny host program with the system C compiler. Skipped if there isn't one.
"""

import random
import shutil
import subprocess
from pathlib import Path

import pytest

from teryx.lights import FRONT, LAMPS, Lights, LightsReq, LightsState, show_level

FW = Path(__file__).resolve().parent.parent / "firmware" / "control-box"


@pytest.fixture(scope="module")
def harness(tmp_path_factory):
    cc = shutil.which("cc") or shutil.which("gcc")
    if not cc:
        pytest.skip("no C compiler")
    exe = tmp_path_factory.mktemp("lights") / "lights_parity"
    subprocess.run([cc, "-std=c11", "-Wall", "-Werror", "-I", str(FW / "src" / "core"),
                    str(FW / "tests" / "lights_parity.c"), str(FW / "src" / "core" / "lights.c"),
                    "-o", str(exe)], check=True)
    return exe


def ask(exe, lines):
    out = subprocess.run([str(exe)], input="\n".join(lines) + "\n", capture_output=True, text=True, check=True)
    return out.stdout.splitlines()


def test_show_patterns_match(harness):
    names = LAMPS + FRONT
    cases = [(show, u, t) for show in range(5) for u in range(len(names)) for t in range(0, 8200, 17)]
    got = ask(harness, [f"L {s} {u} {t}" for s, u, t in cases])
    for (s, u, t), g in zip(cases, got):
        assert int(g) == show_level(s, names[u], t), (s, names[u], t)


def test_rules_match(harness):
    rng = random.Random(7)
    L = Lights()
    lines, want = [], []
    now = 0
    for _ in range(3000):
        now += rng.choice((5, 5, 5, 40, 333))
        lv = lambda: rng.choice((0, 0, 1, 60, 128, 255))   # noqa: E731
        r = LightsReq(head_low=lv(), head_high=lv(), tail=lv(), rear=lv(), trailer_bar=lv(), beacon=lv(), beacon_white=lv(),
                      show=rng.choice((0, 0, 1, 2, 3, 4)), rear_on=rng.random() < 0.5, rear_auto=rng.random() < 0.5,
                      flash=rng.choice((0, 0, 0, 1, 2)))
        b = lambda p=0.5: rng.random() < p   # noqa: E731
        st = LightsState(brake=b(0.2), reverse=b(0.2), trailer=b(), stopped=b(0.7), park=b(0.7), ignition=b(0.9),
                         locked=b(0.1), dash_ok=b(0.9), front_on=b(), now_ms=now, interior=lv())
        o = L.step(r, st)
        front = " ".join(str(o.front[k]) for k in FRONT) if o.front is not None else "-"
        want.append(" ".join(str(o.level[k]) for k in LAMPS)
                    + f" {int(o.show_running)} {int(o.show_blocked)} {int(o.flash_running)} {front}")
        vals = [r.head_low, r.head_high, r.tail, r.rear, r.trailer_bar, r.beacon, r.show, r.rear_on, r.rear_auto,
                st.brake, st.reverse, st.trailer, st.stopped, st.park, st.ignition, st.locked, st.dash_ok,
                st.front_on, st.now_ms, r.beacon_white, r.flash, st.interior]
        lines.append("S " + " ".join(str(int(v)) for v in vals))
    got = [g.strip() for g in ask(harness, lines)]
    for i, (g, w) in enumerate(zip(got, want)):
        assert g == w, (i, lines[i])
