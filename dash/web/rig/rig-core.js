// Starts the whole-Teryx sim: the Pico firmware (WebAssembly) + teryx/rig in Pyodide.
// Shared by the page's web worker (worker.js) and the Node check in CI (tools/rig_web_check.mjs).
import { makeRigFw } from "./rigfw.js";

export async function startRig({ loadPyodide, indexURL, factory, zipBytes, status = () => {} }) {
  status("Loading the Pico firmware");
  const fw = await makeRigFw(factory);
  globalThis.rigfw = fw;
  status("Loading Python");
  const py = await loadPyodide(indexURL ? { indexURL } : {});
  status("Loading PyYAML");
  await py.loadPackage("pyyaml", { messageCallback: () => {} });
  status("Unpacking Teryx OS");
  py.unpackArchive(zipBytes, "zip", { extractDir: "/home/pyodide/teryx-os" });
  status("Wiring up the Teryx");
  py.runPython(`
import sys
sys.path.insert(0, "/home/pyodide/teryx-os")
import importlib.util
_spec = importlib.util.spec_from_file_location("can", "/home/pyodide/teryx-os/teryx/rig/web_can.py")
_can = importlib.util.module_from_spec(_spec)
sys.modules["can"] = _can            # before teryx imports it: python-can isn't in the browser
_spec.loader.exec_module(_can)
import json
from teryx.rig.web import WebRig
rig = WebRig()

def _rig_tick(seconds):
    rig.tick(seconds)

def _rig_ui(text):
    rig.ui(json.loads(text))

def _rig_panel(text):
    rig.panel(json.loads(text))

def _rig_out():
    out = {"dash": rig.dash_state(), "panel": rig.panel_state(), "replies": rig.replies}
    rig.replies = []
    return json.dumps(out, default=str)
`);
  const g = py.globals;
  const tick = g.get("_rig_tick"), ui = g.get("_rig_ui"), panel = g.get("_rig_panel"), out = g.get("_rig_out");
  return {
    py,
    tick: (s) => tick(s),
    ui: (msg) => ui(JSON.stringify(msg)),
    panel: (cmd) => panel(JSON.stringify(cmd)),
    out: () => JSON.parse(out()),
  };
}
