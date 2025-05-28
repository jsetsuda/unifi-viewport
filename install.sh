#!/bin/bash
set -e

echo "== UniFi RTSP Viewport Installer =="

# Ensure script is run from project root
cd "$(dirname "$0")"

echo "[INFO] Updating package list..."
sudo apt update

echo "[INFO] Installing required system packages..."
sudo apt install -y \
  python3 \
  python3-pip \
  python3-tk \
  ffmpeg \
  mpv \
  jq \
  libnss3-tools \
  libgl1-mesa-glx \
  libpulse0 \
  libegl1 \
  x11-utils \
  xdotool \
  git

echo "[INFO] Installing Python packages globally with --break-system-packages..."
pip3 install --break-system-packages \
  python-dotenv \
  requests \
  uiprotect

# Create .env if not present
if [ ! -f .env ]; then
  echo "[INFO] Creating .env template..."
  cat <<EOF > .env
# UniFi Protect API credentials
UFP_HOST=https://192.168.5.10
UFP_USERNAME=your_username
UFP_PASSWORD=your_password
EOF
  echo "[INFO] .env file created. Please edit it with your UniFi Protect login info."
else
  echo "[INFO] .env file already exists, skipping creation."
fi

# Add .env to .gitignore if missing
if [ ! -f .gitignore ]; then
  touch .gitignore
fi

if ! grep -q "^.env$" .gitignore; then
  echo ".env" >> .gitignore
  echo "[INFO] .env added to .gitignore"
fi

echo "[SUCCESS] Setup complete. You can now run:"
echo "  python3 get_streams.py"
