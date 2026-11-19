"""Trailer camera check (trailercam.py) and the video board's sharing (videoboard.py)."""

import asyncio

from teryx_dash import videoboard
from teryx_dash.trailercam import PERIOD_S, RETRY_S, TrailerWatch


def test_parse_std():
    assert videoboard.parse_std("Video Standard = 0x000000ff\n\tPAL-B/B1/G/H/I/D/D1/K/N/Nc/60") is True
    assert videoboard.parse_std("Video Standard = 0x00000000") is False
    assert videoboard.parse_std("VIDIOC_QUERYSTD: failed: Device or resource busy") is None


def test_uses_board():
    assert videoboard.uses_board(["sh", "-c", videoboard.shell_prefix(1) + "exec ffmpeg"])
    assert not videoboard.uses_board(["rpicam-vid", "--camera", "0"])


def run(coro):
    return asyncio.run(coro)


def test_watch_probes_and_resets_on_plug():
    t = {"now": 100.0}
    plug = {"v": False}
    answers = []

    async def probe(inp):
        answers.append(inp)
        return probe.result

    probe.result = False
    w = TrailerWatch(lambda: "adv:1", lambda: plug["v"], probe, lambda: t["now"])
    assert run(w.step()) == {"plug": False, "signal": False, "checked": 100.0}
    assert answers == [1]
    # Not again until PERIOD_S is up
    t["now"] += 1
    run(w.step())
    assert answers == [1]
    # Plug in: look straight away, and say "not known" until then
    plug["v"] = True
    probe.result = True
    t["now"] += 1
    assert run(w.step())["signal"] is True
    assert answers == [1, 1]
    # Board busy: keep the answer, try again soon
    probe.result = None
    t["now"] += PERIOD_S
    assert run(w.step())["signal"] is True
    assert w.next == t["now"] + RETRY_S


def test_watch_no_camera_on_board():
    async def probe(inp):
        raise AssertionError("no board camera, shouldn't probe")

    w = TrailerWatch(lambda: "", lambda: True, probe, lambda: 0.0)
    assert run(w.step()) == {"plug": True, "signal": None, "checked": None}


def test_probe_leaves_busy_board_alone(monkeypatch):
    class P:
        returncode = None

    b = videoboard.BOARD
    old = b.viewer
    try:
        b.viewer = P()
        assert b.watching() and b.busy()
        assert run(videoboard.probe(1)) is None
    finally:
        b.viewer = old
