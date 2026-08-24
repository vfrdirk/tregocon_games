#!/usr/bin/env bash
# TregoCon Phase 1 bootstrap — run as root on a fresh Ubuntu 22.04 Lightsail instance.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/peach/tregocon/main/scripts/bootstrap.sh | sudo bash
#   (or: scp this file to the box and run `sudo bash bootstrap.sh`)
# Prereqs (do in Lightsail console first):
#   - Ubuntu 22.04 + Docker image (or any Ubuntu 22.04; script installs Docker)
#   - Attach a static IP
#   - Open firewall ports 80 (HTTP) and 443 (HTTPS)
#   - Point DNS A record play.tregocon.games -> the static IP
set -euo pipefail

APP_DIR=/opt/tregocon
REPO=https://github.com/peach/tregocon.git   # <-- update to your actual repo URL

echo "==> Installing Docker (if missing)"
if ! command -v docker >/dev/null; then
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
docker --version

echo "==> Cloning repo"
mkdir -p "$APP_DIR"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO" "$APP_DIR"
fi
cd "$APP_DIR"

echo "==> Writing .env (EDIT THESE VALUES)"
if [ ! -f .env ]; then
  cat > .env <<'EOF'
POSTGRES_USER=tregocon
POSTGRES_PASSWORD=CHANGE_ME_strong_password
POSTGRES_DB=tregocon
PUBLIC_URL=https://play.tregocon.games
ACME_EMAIL=you@example.com
SES_REGION=
SES_FROM_EMAIL=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
EOF
  echo "!!! EDIT /opt/tregocon/.env with real secrets, then re-run this script's last step."
fi

echo "==> Bringing up the stack (TLS via Caddy auto-provisioning)"
docker compose -f docker-compose.prod.yml --env-file .env up -d

echo "==> Done. Verify:"
echo "    curl -fsS https://play.tregocon.games/api/event/status"
echo "    If DNS isn't propagated yet, test the box directly: curl -fsS http://localhost/api/event/status"
