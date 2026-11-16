#!/usr/bin/env bash
# Bring up the real CAN bus on the Pi (CAN HAT / MCP2515 overlay already set in
# /boot/firmware/config.txt). Bit rate must match the Shinegle (likely 250k, TBC).
# Usage: sudo ./scripts/setup_can_pi.sh [can0] [250000]
set -euo pipefail
NAME="${1:-can0}"
RATE="${2:-250000}"
ip link set "$NAME" down 2>/dev/null || true
ip link set "$NAME" up type can bitrate "$RATE" restart-ms 100
ip -details link show "$NAME" | head -5
echo "Listen only first! e.g. candump -l $NAME   (records to a log file you can replay)"
