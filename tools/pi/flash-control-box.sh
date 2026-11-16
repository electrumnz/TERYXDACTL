#!/usr/bin/env bash
# Flash new firmware onto the Pico 2 control box from the Pi, over USB.
#
#   tools/pi/flash-control-box.sh teryx_control_box.uf2 [can-interface]
#
# Steps:
#   1. Check the Teryx is parked (0x710 "parked" flag). The Pico checks too.
#   2. Ask the Pico to reboot into its USB bootloader (CAN 0x71F, magic 0x5445).
#      If CAN isn't up, fall back to "picotool reboot -f -u" over USB.
#   3. picotool loads, verifies and starts the new firmware.
#   4. Wait for the Pico to come back on CAN and report its version (0x713).
#
# Needs: picotool, can-utils (cansend, candump). The Pico's USB goes to the Pi
# for data only; the Pico is powered from its own 5V buck.
set -euo pipefail

UF2="${1:?usage: $0 firmware.uf2 [can0]}"
CAN_IF="${2:-can0}"
KEEP_DIR="${TERYX_FW_DIR:-/var/lib/teryx/control-box}"

die() { echo "flash-control-box: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null || die "$1 not found (sudo apt install ${2:-$1})"; }
need picotool picotool
need cansend can-utils
need candump can-utils

[ -f "$UF2" ] || die "no such file: $UF2"
[ "$(head -c 4 "$UF2")" = "UF2"$'\n' ] || die "$UF2 is not a UF2 file"

in_bootsel() { picotool info >/dev/null 2>&1; }

frame() {  # frame <hex id> <timeout ms> -> prints the data bytes of one frame, or nothing
    timeout $(( $2 / 1000 + 1 )) candump -n 1 -L "$CAN_IF,$1:7FF" 2>/dev/null | sed -n 's/.*#//p' || true
}

if ! in_bootsel; then
    status="$(frame 710 1500)"
    if [ -n "$status" ]; then
        flags=$(( 16#${status:12:2} ))
        (( flags & 0x10 )) || die "Teryx isn't parked (stop, nothing moving, or key off) - not flashing"
        echo "Asking the control box to enter its bootloader over CAN..."
        cansend "$CAN_IF" 71F#4554
    else
        echo "No control box on $CAN_IF, trying the USB reset instead..."
        picotool reboot -f -u >/dev/null 2>&1 || true
    fi
    for _ in $(seq 1 20); do in_bootsel && break; sleep 0.5; done
    in_bootsel || die "control box didn't show up in bootloader mode (refused? check the reject reason on the dash)"
fi

mkdir -p "$KEEP_DIR" 2>/dev/null || true
echo "Loading $UF2..."
picotool load -v -x "$UF2" || die "load or verify failed. The Pico is still in bootloader mode, so run this again or load $KEEP_DIR/current.uf2"

echo "Waiting for the control box to come back..."
power="$(frame 713 15000)"
[ -n "$power" ] || die "no 0x713 from the control box after flashing. Load $KEEP_DIR/current.uf2 to roll back"
ver="$(( 16#${power:10:2} )).$(( 16#${power:12:2} ))"
echo "Control box is running firmware $ver"

# Keep the last good image so the Pi can roll back.
if [ -w "$KEEP_DIR" ]; then
    [ -f "$KEEP_DIR/current.uf2" ] && cp "$KEEP_DIR/current.uf2" "$KEEP_DIR/previous.uf2"
    cp "$UF2" "$KEEP_DIR/current.uf2"
fi
