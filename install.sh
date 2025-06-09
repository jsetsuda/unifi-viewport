#!/usr/bin/env bash
set -euo pipefail

echo "== UniFi RTSP Viewport Installer =="

# Make sure we’re running from the project’s root
cd "$(dirname "$0")"

echo "[INFO] Updating APT cache…"
sudo apt update

echo "[INFO] Installing system packages…"
sudo apt install -y \
  python3 \
  python3-pip \
  python3-psutil \
  python3-tk \
  ffmpeg \
  mpv \
  jq \
  xdotool \
  x11-utils \
  git \
  libnss3-tools \
  libgl1-mesa-glx \
  libpulse0 \
  libegl1

echo "[INFO] Installing Python packages globally…"
pip3 install --break-system-packages \
  python-dotenv \
  requests \
  psutil

# Prompt for .env if it doesn't exist
if [ ! -f .env ]; then
  echo
  echo "[INFO] Configure your UniFi Protect connection:"
  read -rp "  UFP_HOST      (e.g. https://192.168.5.10): " UFP_HOST
  read -rp "  UFP_USERNAME  : " UFP_USERNAME
  read -rsp "  UFP_PASSWORD  : " UFP_PASSWORD
  echo

  cat > .env <<EOF
UFP_HOST=$UFP_HOST
UFP_USERNAME=$UFP_USERNAME
UFP_PASSWORD=$UFP_PASSWORD
EOF

  echo "[INFO] Created .env with your credentials."
else
  echo "[INFO] .env already exists – skipping."
fi

# Ensure .env is in .gitignore
touch .gitignore
if ! grep -qxF ".env" .gitignore; then
  echo ".env" >> .gitignore
  echo "[INFO] Added .env to .gitignore"
fi

# Make sure all of our scripts are executable
chmod +x get_streams.py \
         layout_chooser.py \
         viewport.sh \
         monitor_streams.py \
         kill_stale_streams.py \
         overlay_box.py

echo
echo "[✅] Installation complete!"
echo "  • Run the chooser:   ./layout_chooser.py"
echo "  • Or launch streams: ./viewport.sh"
