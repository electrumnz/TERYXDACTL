#!/bin/bash
# Rebuilds dash/web/lib/node-carplay.js (the CarPlay / Android Auto dongle driver) from npm.
# Only needed to change the node-carplay version. The built file is committed, so the Pi needs no Node.
set -euo pipefail
cd "$(dirname "$0")"
npm install --no-audit --no-fund --ignore-scripts
OUT=../../web/lib
mkdir -p "$OUT"
# node-carplay's package.json doesn't export the deep paths, so point esbuild at the files directly.
npx esbuild entry.js --bundle --format=esm --platform=browser --minify --legal-comments=eof \
  --alias:node-carplay/dist=./node_modules/node-carplay/dist \
  --inject:./buffer-shim.js --outfile="$OUT/node-carplay.js"
{
  echo "node-carplay 4.1.0 (MIT), bundled with buffer 6.0.3 (MIT) and events 3.3.0 (MIT)."
  echo "Built by dash/vendor-src/carplay/build.sh. Licences follow."
  for p in node-carplay buffer events; do echo; echo "==== $p ===="; cat "node_modules/$p/LICENSE"*; done
} > "$OUT/node-carplay.LICENSES.txt"
echo "Built $OUT/node-carplay.js"
