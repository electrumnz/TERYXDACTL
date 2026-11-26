#!/usr/bin/env bash
# One-shot setup for the dash Pi 5 (Raspberry Pi OS Bookworm 64-bit, desktop).
#
#   sudo bash scripts/pi-setup.sh [options]
#
# What it does (safe to run again):
#   1. Installs the packages the dash needs.
#   2. Turns on SPI and the MCP2515 CAN HAT overlay in /boot/firmware/config.txt.
#   3. Brings can0 up at boot at the right bit rate (systemd-networkd).
#   4. Turns off screen blanking.
#   5. Installs the dash into /opt/teryx (release folders + rollback) and starts it.
#   6. Opens the dash full screen when the desktop user logs in.
#   7. Sound: Bluetooth phone audio, CarPlay adapter, amp output (scripts/audio-setup.sh).
#
# Options:
#   --version TAG     Release tag or branch to install (default: main)
#   --repo URL        Git URL (default: this repo on GitHub)
#   --can-osc HZ      Crystal on the Pi's CAN HAT/module (default 8000000, the blue MCP2515 boards; 16000000 for Seeed, 12000000
#                     for some Waveshare HATs. Read
#                     the number on the crystal)
#   --can-int GPIO    CAN HAT interrupt pin (default 25)
#   --bitrate BPS     CAN bit rate (default 250000, must match the Shinegle)
#   --user NAME       Desktop user that sees the dash (default: the user running sudo)
#   --i2s OVERLAY     I2S amp/DAC HAT overlay, e.g. hifiberry-dac (the PCM5102 board, see docs/audio.md)
#
# Wifi is set in Raspberry Pi Imager or the desktop, never in this repo.
set -euo pipefail

VERSION=main
REPO_URL=https://github.com/electrumnz/TERYXDACTL.git
CAN_OSC=8000000
CAN_INT=25
BITRATE=250000
DESK_USER="${SUDO_USER:-}"
I2S=""

while [ $# -gt 0 ]; do
  case "$1" in
    --version) VERSION="$2"; shift 2 ;;
    --repo) REPO_URL="$2"; shift 2 ;;
    --can-osc) CAN_OSC="$2"; shift 2 ;;
    --can-int) CAN_INT="$2"; shift 2 ;;
    --bitrate) BITRATE="$2"; shift 2 ;;
    --user) DESK_USER="$2"; shift 2 ;;
    --i2s) I2S="$2"; shift 2 ;;
    -h|--help) sed -n '2,27p' "$0"; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
done

say() { printf '\n== %s\n' "$*"; }
die() { echo "pi-setup: $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "run with sudo"
if [ -z "$DESK_USER" ] || ! id "$DESK_USER" >/dev/null 2>&1; then die "can't tell the desktop user, pass --user NAME"; fi
grep -q "Raspberry Pi 5" /proc/device-tree/model 2>/dev/null \
  || echo "warning: this doesn't look like a Pi 5, carrying on anyway"

HERE="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG=/boot/firmware/config.txt
[ -f "$CONFIG" ] || CONFIG=/boot/config.txt

say "1/7 Packages"
apt-get update -qq
apt-get install -y -qq git python3-venv python3-pip can-utils ffmpeg picotool curl \
  >/dev/null
command -v chromium >/dev/null || command -v chromium-browser >/dev/null \
  || apt-get install -y -qq chromium >/dev/null

say "2/7 CAN HAT overlay ($CAN_OSC Hz crystal, interrupt GPIO$CAN_INT)"
BEGIN="# >>> teryx can"
END="# <<< teryx can"
sed -i "/^$BEGIN/,/^$END/d" "$CONFIG"
cat >> "$CONFIG" <<EOF
$BEGIN
dtparam=spi=on
dtoverlay=mcp2515-can0,oscillator=$CAN_OSC,interrupt=$CAN_INT
$END
EOF

say "3/7 can0 at $BITRATE bit/s on boot"
cat > /etc/systemd/network/80-teryx-can0.network <<EOF
# Written by scripts/pi-setup.sh
[Match]
Name=can0

[CAN]
BitRate=$BITRATE
RestartSec=100ms
EOF
systemctl enable -q systemd-networkd

say "4/7 Screen blanking off"
if command -v raspi-config >/dev/null; then
  raspi-config nonint do_blanking 1 || true
fi

say "5/7 Dash into /opt/teryx (version $VERSION)"
# (Ignore its last lines about the kiosk service: step 6 does that a simpler way.)
bash "$HERE/dash/deploy/install-pi.sh" "$REPO_URL" "$VERSION"

say "6/7 Full-screen dash for $DESK_USER"
DESK_HOME="$(getent passwd "$DESK_USER" | cut -d: -f6)"
install -d -o "$DESK_USER" -g "$DESK_USER" "$DESK_HOME/.config/autostart"
cat > "$DESK_HOME/.config/autostart/teryx-dash.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Teryx dash
Exec=/opt/teryx/current/dash/deploy/kiosk.sh
X-GNOME-Autostart-enabled=true
EOF
chown "$DESK_USER:$DESK_USER" "$DESK_HOME/.config/autostart/teryx-dash.desktop"
# Turn on desktop auto-login so the dash comes up with no keyboard.
if command -v raspi-config >/dev/null; then
  raspi-config nonint do_boot_behaviour B4 || true
fi

say "7/7 Sound (Bluetooth phone audio, CarPlay adapter, amp output)"
if [ -n "$I2S" ]; then
  bash "$HERE/scripts/audio-setup.sh" --user "$DESK_USER" --i2s "$I2S"
else
  bash "$HERE/scripts/audio-setup.sh" --user "$DESK_USER"
fi

say "Done"
echo "Reboot now (sudo reboot). After the reboot:"
echo "  - the dash opens full screen on its own"
echo "  - 'ip -details link show can0' should show the bit rate $BITRATE"
echo "  - 'systemctl status teryx-dash' shows the dash server"
echo "Check the crystal on your CAN HAT matches $CAN_OSC Hz, or CAN won't work."
