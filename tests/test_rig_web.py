"""The whole-Teryx simulator page (dash/web/rig/): the Python side, run on the PC.

In the browser the same teryx/rig code runs in Pyodide with the WebAssembly build of
the firmware; tools/rig_web_check.mjs (CI: rig-web.yml) checks that end to end.
Here: the WebAssembly build is up to date with the firmware source, the python-can
stand-in behaves, and WebRig does what the page asks.
"""

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

from teryx.rig.firmware import compiler, source_hash

ROOT = Path(__file__).resolve().parents[1]
RIG = ROOT / "dash" / "web" / "rig"
needs_cc = pytest.mark.skipif(compiler() is None and not os.environ.get("TERYX_RIG_REQUIRED"),
                              reason="needs a C compiler and pthreads (Linux/macOS)")


def test_wasm_firmware_is_built_from_the_current_source():
    info = json.loads((RIG / "pico.json").read_text())
    assert info["source_sha256"] == source_hash(), (
        "the firmware changed: rebuild the browser copy with  python tools/build_rig_web.py --wasm")
    assert (RIG / "pico.wasm").stat().st_size > 10_000


def test_worker_and_check_use_the_same_pyodide():
    import re
    worker = (RIG / "worker.js").read_text()
    wf = (ROOT / ".github" / "workflows" / "rig-web.yml").read_text()
    v = re.search(r"pyodide/v([\d.]+)/full", worker).group(1)
    assert f"pyodide@{v}" in wf


def test_can_stand_in_sends_to_the_others_not_back_to_itself():
    spec = importlib.util.spec_from_file_location("web_can_test", ROOT / "teryx" / "rig" / "web_can.py")
    can = importlib.util.module_from_spec(spec)
    sys.modules["web_can_test"] = can
    spec.loader.exec_module(can)
    a, b, c = (can.Bus(interface="virtual", channel="t") for _ in range(3))
    other = can.Bus(interface="virtual", channel="elsewhere")
    a.send(can.Message(arbitration_id=0x123, data=b"\x01\x02"))
    assert a.recv(0) is None and other.recv(0) is None
    for bus in (b, c):
        m = bus.recv(0)
        assert m.arbitration_id == 0x123 and bytes(m.data) == b"\x01\x02"
    b.shutdown()
    a.send(can.Message(arbitration_id=1, data=b""))
    assert b.recv(0) is None and c.recv(0).arbitration_id == 1
    with pytest.raises(can.CanError):
        can.Bus(interface="socketcan", channel="can0")


def test_bundle_has_what_the_browser_needs(tmp_path):
    import runpy
    import zipfile
    bundle = runpy.run_path(str(ROOT / "tools" / "build_rig_web.py"), run_name="x")["bundle"]
    names = set(zipfile.ZipFile(bundle(tmp_path / "b.zip")).namelist())
    for need in ("teryx/rig/web.py", "teryx/rig/webfw.py", "teryx/rig/system.py", "teryx/dash/gateway.py",
                 "teryx/canbus/shinegle.dbc", "config/wiring.yaml", "config/io-map.yaml", "firmware/VERSION"):
        assert need in names


@pytest.fixture
def rig():
    from teryx.rig.web import WebRig
    r = WebRig()
    r.tick(0.25)
    for _ in range(12):
        r.tick(0.25)
    yield r
    r.close()


@needs_cc
def test_dash_buttons_drive_the_real_firmware(rig):
    st = rig.dash_state()
    assert st["link.online"] and st["link.rig"] and st["pico.online"]
    rig.ui({"type": "request", "id": "light.front_2", "value": 255})
    rig.tick(0.25)
    rig.tick(0.25)
    assert rig.panel_state()["lights"]["LB2"]["bar"] > 0.9
    rig.ui({"type": "setting", "key": "eps_listen", "value": 1})
    rig.tick(0.25)
    assert {"type": "setting_ack", "key": "eps_listen", "ok": True} in rig.replies


@needs_cc
def test_panel_is_the_drivers_hands_and_feet(rig):
    rig.panel({"park": False, "fnr": "forward", "throttle": 0.7})
    for _ in range(16):
        rig.tick(0.25)
    p = rig.panel_state()
    assert p["speed_kmh"] > 8 and p["shinegle"]["direction"] == "forward"
    assert rig.dash_state()["mc.speed"] > 8
    rig.panel({"throttle": 0, "steer": 4})
    for _ in range(4):
        rig.tick(0.25)
    assert rig.panel_state()["eps"]["angle_deg"] > 30
    with pytest.raises(ValueError):
        rig.panel({"fnr": "sideways"})


@needs_cc
def test_pulling_the_screen_fuse_turns_the_screen_off(rig):
    p = rig.panel_state()
    assert p["screen_on"] and p["fuses"]["FB.F1"]["amps"] == 15
    pi_fuse = next(ref for ref, f in p["fuses"].items() if "SCREEN_PSU" in f["what"])
    rig.panel({"fuse": [pi_fuse, True]})
    rig.tick(0.25)
    assert not rig.panel_state()["screen_on"]
    rig.panel({"fuse": [pi_fuse, False]})
    rig.tick(0.25)
    assert rig.panel_state()["fuses"][pi_fuse]["pulled"] is False


@needs_cc
def test_start_again(rig):
    rig.panel({"key": False, "battery": 11.0})
    rig.panel({"restart": True})
    assert rig.inputs["key"] is True and rig.inputs["battery"] == pytest.approx(12.6)


@needs_cc
def test_live_wiring_state_for_the_drawing(rig):
    """docs/wiring/ lights up from this: every pin's net and level, cut wires, pulled fuses."""
    st = rig.wiring_state()
    pins = st["pins"]
    assert pins["RAIL.BUS"][1] > 11                                # key on: the dash rail is up
    assert pins["RELAYS.COM8"][0] == pins["RELAYS.NO8"][0]         # power hold relay closed
    rig.panel({"fuse": ["FB.F12", True]})
    rig.tick(0.25)
    assert "FB.F12" in rig.wiring_state()["blown"]
    fused = next(ref for ref in rig.fuses if "." not in ref)
    rig.panel({"fuse": [fused, True]})
    rig.tick(0.25)
    assert fused in rig.wiring_state()["cut"]
