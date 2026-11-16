#!/bin/bash
# Run by the OTA updater inside a new release folder before switching to it.
# Keeps one shared venv; installs this release's Python bits into it.
set -euo pipefail
VENV=/opt/teryx/venv
"$VENV/bin/pip" install --quiet -r requirements.txt
# Keep the rollback helper current (it's a standalone copy outside the releases).
install -m 0755 dash/server/teryx_dash/ota.py /opt/teryx/bin/teryx-ota-boot.py
