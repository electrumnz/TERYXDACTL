#!/bin/bash
# First-time setup on the Pi 5 (Raspberry Pi OS Bookworm, desktop).
# Usage: sudo bash install-pi.sh <git url of the repo> <first version tag, eg v0.1.0>
set -euo pipefail
REPO_URL="${1:?repo url}"
TAG="${2:?version tag}"
ROOT=/opt/teryx
id teryx >/dev/null 2>&1 || useradd --system --groups video,dialout --home "$ROOT" teryx
mkdir -p "$ROOT"/{releases,bin}
[ -d "$ROOT/repo" ] || git clone "$REPO_URL" "$ROOT/repo"
git -C "$ROOT/repo" fetch --tags
[ -d "$ROOT/releases/$TAG" ] || git -C "$ROOT/repo" worktree add --detach "$ROOT/releases/$TAG" "$TAG"
ln -sfn "$ROOT/releases/$TAG" "$ROOT/current"
[ -d "$ROOT/venv" ] || python3 -m venv "$ROOT/venv"
(cd "$ROOT/current" && bash dash/deploy/post-install.sh)
apt-get install -y ffmpeg can-utils >/dev/null
chown -R teryx:teryx "$ROOT"
install -m 0440 "$ROOT/current/dash/deploy/sudoers-teryx" /etc/sudoers.d/teryx
cp "$ROOT/current/dash/deploy/teryx-dash.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now teryx-dash
echo "Dash server running. Now, as the desktop user:"
echo "  mkdir -p ~/.config/systemd/user && cp $ROOT/current/dash/deploy/teryx-kiosk.service ~/.config/systemd/user/"
echo "  systemctl --user enable --now teryx-kiosk"
