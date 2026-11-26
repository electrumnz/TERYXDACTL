"""Front bar stack maths shared by the dash and the phone remote (dash/web/js/barstack.js)."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("node") is None and not os.environ.get("TERYX_RIG_REQUIRED"),
                    reason="needs node")
def test_barstack_js():
    r = subprocess.run(["node", str(ROOT / "tests" / "js" / "barstack.test.mjs")], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
