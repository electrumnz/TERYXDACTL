#!/usr/bin/env bash
# Make a Linux virtual CAN bus (vcan0) so the sim, dash and Pico host build can
# run as separate programs and you can use candump/cansniffer on it.
# Usage: sudo ./scripts/setup_vcan.sh [name]
set -euo pipefail
NAME="${1:-vcan0}"
modprobe vcan
if ! ip link show "$NAME" >/dev/null 2>&1; then
  ip link add dev "$NAME" type vcan
fi
ip link set up "$NAME"
echo "$NAME is up. Try: python -m teryx run --bus socketcan:$NAME"
