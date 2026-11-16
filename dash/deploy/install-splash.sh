#!/bin/bash
# Quick, quiet boot: Teryx logo instead of scrolling text, then straight into the dash.
# Usage: sudo bash install-splash.sh   (safe to run again)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
apt-get install -y plymouth plymouth-themes >/dev/null
DEST=/usr/share/plymouth/themes/teryx
mkdir -p "$DEST"
install -m 0644 "$HERE/splash/teryx.plymouth" "$HERE/splash/teryx.script" "$HERE/splash/logo.png" "$DEST/"
plymouth-set-default-theme teryx
# Quiet kernel boot with the splash. cmdline.txt is a single line.
CMDLINE=/boot/firmware/cmdline.txt
[ -f "$CMDLINE" ] || CMDLINE=/boot/cmdline.txt
for opt in quiet splash plymouth.ignore-serial-consoles logo.nologo vt.global_cursor_default=0; do
  grep -qw -- "$opt" "$CMDLINE" || sed -i "1 s/\$/ $opt/" "$CMDLINE"
done
# No rainbow square at power on.
CONFIG=/boot/firmware/config.txt
[ -f "$CONFIG" ] || CONFIG=/boot/config.txt
grep -q '^disable_splash=1' "$CONFIG" || echo 'disable_splash=1' >> "$CONFIG"
update-initramfs -u >/dev/null 2>&1 || true
echo "Boot splash installed. It shows from the next reboot."
