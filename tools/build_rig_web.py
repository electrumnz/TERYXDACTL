#!/usr/bin/env python3
"""Build the phone sim (dash/web/rig/): the Pico firmware for the browser + the Python bundle.

    python tools/build_rig_web.py            # the Python bundle (teryx-py.zip), needs nothing extra
    python tools/build_rig_web.py --wasm     # also rebuild pico.js + pico.wasm (needs Emscripten's emcc)
    python tools/build_rig_web.py --check    # fail if pico.wasm is older than the firmware source

pico.js / pico.wasm are kept in git (so Pages and a plain laptop don't need Emscripten).
pico.json records which firmware source they came from; tests/test_rig_web.py fails
when the firmware changes and they weren't rebuilt. CI (.github/workflows/rig-web.yml)
rebuilds them with Emscripten and runs the whole sim in Pyodide under Node.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from teryx.rig.firmware import FW, SOURCES, _version, source_hash  # noqa: E402

OUT = ROOT / "dash" / "web" / "rig"
# The Python the sim needs in the browser. Kept small: no dash server, no decode kit, no web assets.
PY_PACKAGES = ["teryx/__init__.py", "teryx/config.py", "teryx/wiring.py", "teryx/lights.py",
               "teryx/vehicle_lock.py", "teryx/eps_toyota.py", "teryx/canbus", "teryx/dash/__init__.py",
               "teryx/dash/gateway.py", "teryx/rig", "teryx/sim"]
DATA = ["config/io-map.yaml", "config/wiring.yaml", "config/shinegle-faults.yaml", "firmware/VERSION"]


def exports() -> list[str]:
    text = (FW / "src/rig/rig_board.c").read_text(encoding="utf-8")
    names = sorted(set(re.findall(r"RIG_API\s+[\w\s\*]+?\b(rig_\w+)\s*\(", text)))
    return [f"_{n}" for n in names] + ["_malloc", "_free"]


def build_wasm() -> None:
    emcc = shutil.which("emcc")
    if not emcc:
        sys.exit("emcc not found: install Emscripten (https://emscripten.org) or run without --wasm")
    major, minor = _version()
    cmd = [emcc, "-O2", "-std=gnu11", "-Wall", "-Wextra", "-Wno-unused-parameter",
           f"-I{FW / 'src/rig/sdk'}", f"-I{FW / 'src/core'}",
           "-Dmain=pico_main", f"-DFW_VERSION_MAJOR={major}", f"-DFW_VERSION_MINOR={minor}",
           *(str(FW / s) for s in SOURCES),
           "-sASYNCIFY", "-sMODULARIZE=1", "-sEXPORT_ES6=1", "-sEXPORT_NAME=TeryxPico", "-sENVIRONMENT=web,worker,node",
           "-sEXPORTED_FUNCTIONS=" + ",".join(exports()),
           "-sEXPORTED_RUNTIME_METHODS=HEAPU8,UTF8ToString,stringToUTF8",
           "-sINITIAL_MEMORY=16MB", "-sSTACK_SIZE=256KB",
           "-o", str(OUT / "pico.js")]
    subprocess.run(cmd, check=True)
    ver = subprocess.run([emcc, "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    (OUT / "pico.json").write_text(json.dumps({"source_sha256": source_hash(), "emcc": ver}, indent=2) + "\n")
    print("wrote dash/web/rig/pico.js, pico.wasm, pico.json")


def wasm_is_current() -> bool:
    try:
        info = json.loads((OUT / "pico.json").read_text())
    except FileNotFoundError:
        return False
    return info.get("source_sha256") == source_hash() and (OUT / "pico.wasm").exists()


def bundle(out: Path = OUT / "teryx-py.zip") -> Path:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for item in PY_PACKAGES + DATA:
            p = ROOT / item
            files = [p] if p.is_file() else sorted(f for f in p.rglob("*")
                                                   if f.is_file() and f.suffix in (".py", ".dbc")
                                                   and "__pycache__" not in f.parts)
            for f in files:
                z.write(f, f.relative_to(ROOT).as_posix())
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wasm", action="store_true", help="rebuild pico.wasm with emcc")
    ap.add_argument("--check", action="store_true", help="only check pico.wasm matches the firmware")
    a = ap.parse_args()
    if a.check:
        if not wasm_is_current():
            sys.exit("dash/web/rig/pico.wasm is out of date: run python tools/build_rig_web.py --wasm")
        print("pico.wasm matches the firmware source")
        return
    if a.wasm:
        build_wasm()
    elif not wasm_is_current():
        print("warning: pico.wasm is older than the firmware source (run with --wasm)")
    bundle()


if __name__ == "__main__":
    main()
