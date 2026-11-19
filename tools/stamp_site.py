"""Add ?v=<build> to every local .js and .css link in the online copy of the dash.

Used by .github/workflows/dash-site.yml. Browsers (iPhone Safari above all) can keep some old
module files after a deploy; a new app.js importing an old file stops the whole dash on
"Starting". With every link stamped, each deploy is fetched as one matching set.

    python tools/stamp_site.py _site 1a2b3c4d
"""
import re
import sys
from pathlib import Path

# from "./x.js", import("../y.js"), src="js/app.js", href="css/dash.css" (local paths only)
PATTERNS = [
    re.compile(r'''((?:\bfrom\s*|\bimport\s*\(\s*|\bimport\s+)["'])(\.{1,2}/[^"'?#]+\.js)(["'])'''),
    re.compile(r'''(\b(?:src|href)=["'])((?!https?:|//|data:)[^"'?#]+\.(?:js|css))(["'])'''),
]


def stamp_text(text: str, ver: str) -> str:
    for pat in PATTERNS:
        text = pat.sub(lambda m: f"{m.group(1)}{m.group(2)}?v={ver}{m.group(3)}", text)
    return text


def main(root: str, ver: str) -> int:
    n = 0
    for f in Path(root).rglob("*"):
        if f.suffix not in (".html", ".js") or not f.is_file():
            continue
        old = f.read_text(encoding="utf-8")
        new = stamp_text(old, ver)
        if new != old:
            f.write_text(new, encoding="utf-8")
            n += 1
    print(f"stamped {n} files with v={ver}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
