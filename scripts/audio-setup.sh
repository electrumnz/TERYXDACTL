#!/usr/bin/env bash
# Sound for the dash Pi 5: Bluetooth audio from a phone, music, radio and CarPlay, out to an amp.
# pi-setup.sh runs this for you. Run it by itself to change the amp HAT:
#
#   sudo bash scripts/audio-setup.sh [options]
#
# What it does (safe to run again):
#   1. Installs PipeWire, BlueZ and friends.
#   2. Optional: turns on an I2S amp/DAC HAT (--i2s OVERLAY).
#   3. Makes the Pi a Bluetooth speaker called "Teryx". Phones can only pair while
#      Media > Phone > Pair a phone is open on the dash (2 minutes).
#   4. Lets the dash server (user teryx) reach the desktop user's sound and Bluetooth.
#   5. Lets the dash use a Carlinkit CarPlay adapter over USB with no pop-up.
#
# Options:
#   --i2s OVERLAY   I2S HAT overlay, for example hifiberry-dacplus (most PCM5122 DACs),
#                   hifiberry-amp4pro, iqaudio-dacplus or max98357a. Leave out for a USB DAC.
#   --bt-name NAME  Bluetooth name phones see (default Teryx)
#   --user NAME     Desktop user that runs the dash screen (default: the user running sudo)
#
# See docs/audio.md for which amp, speakers and adapter to buy and how to wire them.
set -euo pipefail

I2S=""
BT_NAME="Teryx"
DESK_USER="${SUDO_USER:-}"

while [ $# -gt 0 ]; do
  case "$1" in
    --i2s) I2S="$2"; shift 2 ;;
    --bt-name) BT_NAME="$2"; shift 2 ;;
    --user) DESK_USER="$2"; shift 2 ;;
    -h|--help) sed -n '2,21p' "$0"; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
done

say() { printf '\n== %s\n' "$*"; }
die() { echo "audio-setup: $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "run with sudo"
if [ -z "$DESK_USER" ] || ! id "$DESK_USER" >/dev/null 2>&1; then die "can't tell the desktop user, pass --user NAME"; fi
case "$I2S" in ""|*[!a-z0-9_-]*) [ -z "$I2S" ] || die "odd overlay name: $I2S" ;; esac
case "$BT_NAME" in *[!A-Za-z0-9\ _-]*|"") die "keep the Bluetooth name to letters, numbers, spaces and dashes" ;; esac

CONFIG=/boot/firmware/config.txt
[ -f "$CONFIG" ] || CONFIG=/boot/config.txt
DESK_HOME="$(getent passwd "$DESK_USER" | cut -d: -f6)"

say "1/5 Packages"
apt-get update -qq
apt-get install -y -qq pipewire pipewire-pulse wireplumber libspa-0.2-bluetooth pulseaudio-utils \
  bluez bluez-tools ffmpeg >/dev/null

say "2/5 I2S HAT: ${I2S:-none (USB DAC or HDMI)}"
BEGIN="# >>> teryx audio"
END="# <<< teryx audio"
sed -i "/^$BEGIN/,/^$END/d" "$CONFIG"
if [ -n "$I2S" ]; then
  cat >> "$CONFIG" <<EOF
$BEGIN
dtoverlay=$I2S
$END
EOF
  echo "Added dtoverlay=$I2S. Reboot for it to show up."
fi

say "3/5 Bluetooth speaker \"$BT_NAME\""
MAIN=/etc/bluetooth/main.conf
if grep -q '^#\?Name *=' "$MAIN"; then sed -i "s/^#\?Name *=.*/Name = $BT_NAME/" "$MAIN"; else sed -i "/^\[General\]/a Name = $BT_NAME" "$MAIN"; fi
if grep -q '^#\?DiscoverableTimeout *=' "$MAIN"; then sed -i 's/^#\?DiscoverableTimeout *=.*/DiscoverableTimeout = 120/' "$MAIN"; else sed -i '/^\[General\]/a DiscoverableTimeout = 120' "$MAIN"; fi
# Answers pairing requests with no PIN. Pairing is only open while the dash asks for it.
cat > /etc/systemd/system/teryx-bt-agent.service <<'EOF'
# Written by scripts/audio-setup.sh. Lets phones pair with no PIN, but only while the dash
# has pairing open (Media > Phone > Pair a phone, 2 minutes).
[Unit]
Description=Teryx Bluetooth pairing agent
After=bluetooth.service
Requires=bluetooth.service

[Service]
ExecStartPre=/usr/bin/bluetoothctl pairable off
ExecStart=/usr/bin/bt-agent -c NoInputNoOutput
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable -q --now bluetooth teryx-bt-agent
systemctl restart bluetooth

say "4/5 Dash server can reach the sound and Bluetooth"
id teryx >/dev/null 2>&1 || useradd --system --home /opt/teryx --shell /usr/sbin/nologin teryx
usermod -aG bluetooth teryx
groupadd -f teryx-audio
usermod -aG teryx-audio teryx
usermod -aG teryx-audio "$DESK_USER"
# The desktop user's PipeWire also listens on a socket the dash server can use.
cat > /etc/tmpfiles.d/teryx-audio.conf <<EOF
d /run/teryx-audio 2770 $DESK_USER teryx-audio -
EOF
systemd-tmpfiles --create /etc/tmpfiles.d/teryx-audio.conf
install -d -o "$DESK_USER" -g "$DESK_USER" "$DESK_HOME/.config/pipewire/pipewire-pulse.conf.d"
cat > "$DESK_HOME/.config/pipewire/pipewire-pulse.conf.d/50-teryx.conf" <<'EOF'
# Written by scripts/audio-setup.sh: a second socket so the dash server (user teryx) can
# list outputs, set the volume and turn phone audio down under alerts.
pulse.properties = {
    server.address = [ "unix:native" "unix:/run/teryx-audio/pulse" ]
}
EOF
chown "$DESK_USER:$DESK_USER" "$DESK_HOME/.config/pipewire/pipewire-pulse.conf.d/50-teryx.conf"
# Bass EQ for the printed speaker pods (docs/speaker-pods.md): a "Teryx speaker pods" output.
POD_EQ="$(dirname "$(readlink -f "$0")")/pipewire/50-teryx-pod-eq.conf"
if [ -f "$POD_EQ" ]; then
  install -d -o "$DESK_USER" -g "$DESK_USER" "$DESK_HOME/.config/pipewire/pipewire.conf.d"
  install -o "$DESK_USER" -g "$DESK_USER" -m 644 "$POD_EQ" "$DESK_HOME/.config/pipewire/pipewire.conf.d/"
fi
install -d /etc/systemd/system/teryx-dash.service.d
cat > /etc/systemd/system/teryx-dash.service.d/audio.conf <<EOF
# Written by scripts/audio-setup.sh
[Service]
Environment=PULSE_SERVER=unix:/run/teryx-audio/pulse
Environment=TERYX_AUDIO=pi
SupplementaryGroups=bluetooth teryx-audio
EOF
systemctl daemon-reload
loginctl enable-linger "$DESK_USER" || true

say "5/5 CarPlay adapter over USB"
cat > /etc/udev/rules.d/60-teryx-carplay.rules <<'EOF'
# Carlinkit CarPlay / Android Auto adapters, for the dash (WebUSB in Chromium).
SUBSYSTEM=="usb", ATTRS{idVendor}=="1314", ATTRS{idProduct}=="1520", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="usb", ATTRS{idVendor}=="1314", ATTRS{idProduct}=="1521", MODE="0666", TAG+="uaccess"
EOF
udevadm control --reload-rules || true
# Chromium lets the dash page open the adapter without asking (0x1314 = 4884, 0x1520/0x1521 = 5408/5409).
for d in /etc/chromium/policies/managed /etc/chromium-browser/policies/managed; do
  install -d "$d"
  cat > "$d/teryx-carplay.json" <<'EOF'
{
  "WebUsbAllowDevicesForUrls": [
    { "devices": [ { "vendor_id": 4884, "product_id": 5408 }, { "vendor_id": 4884, "product_id": 5409 } ],
      "urls": [ "http://localhost:8080" ] }
  ]
}
EOF
done

say "Done"
echo "Reboot (sudo reboot), then on the dash:"
echo "  - Settings > Audio and media: pick the output (USB DAC, I2S HAT or HDMI)"
echo "  - Media > Phone > Pair a phone, and pick \"$BT_NAME\" on the phone"
echo "  - Media > CarPlay with the Carlinkit adapter plugged in"
echo "'pactl list short sinks' (as $DESK_USER) lists the outputs if one is missing."
