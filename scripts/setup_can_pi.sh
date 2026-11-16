#!/usr/bin/env bash
# Bring up the real CAN bus on the Pi (CAN HAT / MCP2515 overlay already set in
# /boot/firmware/config.txt). Bit rate must match the Shinegle (likely 250k, TBC).
# Usage: sudo ./scripts/setup_can_pi.sh [can0] [250000] [listen]
#   add "listen" for listen-only (never sends or ACKs): use it when sniffing the Shinegle.
set -euo pipefail
NAME="${1:-can0}"
RATE="${2:-250000}"
MODE="${3:-}"
LISTEN=()
if [ "$MODE" = "listen" ]; then LISTEN=(listen-only on); fi
ip link set "$NAME" down 2>/dev/null || true
ip link set "$NAME" up type can bitrate "$RATE" restart-ms 100 "${LISTEN[@]}"
ip -details link show "$NAME" | head -5
echo "Listen only first! e.g. candump -l $NAME   (records to a log file you can replay)"
