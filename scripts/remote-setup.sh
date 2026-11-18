#!/usr/bin/env bash
# 4G stick, video drive and Tailscale for the dash Pi 5 (docs/remote-access.md, docs/sentry.md).
# Safe to run again. Run it after pi-setup.sh:
#
#   sudo bash scripts/remote-setup.sh [options]
#
# What it does:
#   1. Installs ModemManager (texts and data on the 4G stick) and lets the dash use it.
#   2. Makes a NetworkManager 4G connection called teryx-4g that is OFF unless a text
#      turns it on (autoconnect off, so the SIM's data isn't used day to day).
#   3. Optional: mounts the video SSD at /mnt/teryx-video by its label (--ssd-label).
#      Format it first, for example: sudo mkfs.ext4 -L teryx-video /dev/sda1
#   4. Tells you how to put the Pi on Tailscale, so your phone can reach it over 4G.
#
# Options:
#   --apn NAME        4G APN. Leave out to let the stick and NetworkManager pick it from the SIM.
#                     Skinny is wapaccess.co.nz if it needs setting by hand.
#   --ssd-label NAME  Filesystem label of the video SSD (default: skip the SSD step)
#   --no-modem        Skip steps 1 and 2 (no 4G stick fitted)
set -euo pipefail

APN=""
SSD_LABEL=""
MODEM=1

while [ $# -gt 0 ]; do
  case "$1" in
    --apn) APN="$2"; shift 2 ;;
    --ssd-label) SSD_LABEL="$2"; shift 2 ;;
    --no-modem) MODEM=0; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
done

say() { printf '\n== %s\n' "$*"; }
die() { echo "remote-setup: $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "run with sudo"
case "$APN" in *[!A-Za-z0-9._-]*) die "odd APN: $APN" ;; esac
case "$SSD_LABEL" in *[!A-Za-z0-9_-]*) die "keep the SSD label to letters, numbers, dashes" ;; esac
HERE="$(cd "$(dirname "$0")/.." && pwd)"
id teryx >/dev/null 2>&1 || useradd --system --home /opt/teryx --shell /usr/sbin/nologin teryx

if [ "$MODEM" -eq 1 ]; then
  say "1/4 ModemManager"
  apt-get update -qq
  apt-get install -y -qq modemmanager network-manager >/dev/null
  systemctl enable -q --now ModemManager
  install -m 0644 "$HERE/dash/deploy/51-teryx-modem.rules" /etc/polkit-1/rules.d/
  install -m 0644 "$HERE/dash/deploy/50-teryx-wifi.rules" /etc/polkit-1/rules.d/

  say "2/4 4G connection teryx-4g (APN ${APN:-from the SIM}, off until a text turns it on)"
  if nmcli -t -f NAME connection show | grep -qx teryx-4g; then
    nmcli connection modify teryx-4g connection.autoconnect no
  else
    nmcli connection add type gsm ifname '*' con-name teryx-4g \
      connection.autoconnect no ipv4.route-metric 700 ipv6.route-metric 700
  fi
  [ -z "$APN" ] || nmcli connection modify teryx-4g gsm.apn "$APN"
  # Higher route metric: Wi-Fi wins when both are up, so media never eats the SIM's data.
  if mmcli -L 2>/dev/null | grep -q Modem; then
    echo "4G stick found:"; mmcli -L
  else
    echo "No 4G stick seen yet. Plug it in; it shows up in mmcli -L within a minute."
  fi
else
  say "1-2/4 Skipped (no 4G stick)"
fi

if [ -n "$SSD_LABEL" ]; then
  say "3/4 Video SSD (label $SSD_LABEL) at /mnt/teryx-video"
  mkdir -p /mnt/teryx-video
  LINE="LABEL=$SSD_LABEL /mnt/teryx-video ext4 defaults,noatime,nofail,x-systemd.device-timeout=10s 0 2"
  sed -i '\|[[:space:]]/mnt/teryx-video[[:space:]]|d' /etc/fstab
  echo "$LINE" >> /etc/fstab
  systemctl daemon-reload
  if mount /mnt/teryx-video 2>/dev/null; then
    chown teryx:teryx /mnt/teryx-video
    df -h /mnt/teryx-video
  else
    echo "Couldn't mount it yet (not plugged in, or not formatted with label $SSD_LABEL)."
    echo "Sentry and dashcam stay off until it mounts. The Pi still boots fine without it (nofail)."
  fi
else
  say "3/4 Video SSD skipped (pass --ssd-label teryx-video once it's formatted)"
fi

say "4/4 Tailscale"
if command -v tailscale >/dev/null 2>&1; then
  tailscale status >/dev/null 2>&1 && echo "Tailscale is on." || echo "Run: sudo tailscale up --hostname teryx"
else
  cat <<'TXT'
Tailscale isn't installed. Follow the Linux steps at https://tailscale.com/download/linux
then run:  sudo tailscale up --hostname teryx
Your phone (also on Tailscale) can then open http://teryx:8080 whenever the 4G data is on.
TXT
fi
echo
echo "Done. Set your number and code on the dash: Settings > Remote (4G)."
