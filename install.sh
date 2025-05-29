#!/bin/bash
set -e

echo "== UniFi RTSP Viewport Installer (GUI OS Preinstalled) =="

# Ensure script is run from project root
cd "$(dirname "$0")"

echo "[INFO] Updating package list..."
sudo apt update

echo "[INFO] Installing required system packages..."
sudo apt install -y \
  python3 \
  python3-pip \
  python3-tk \
  python3-psutil \
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
  
echo "[INFO] Installing Python packages globally (with --break-system-packages)..."
pip3 install --break-system-packages \
  python-dotenv \
  requests \
  uiprotect

# === Prompt user for .env values ===
if [ ! -f .env ]; then
  echo "[INFO] Let's configure your UniFi Protect connection:"
  read -rp "Enter UFP_HOST (e.g. https://192.168.5.10): " UFP_HOST
  read -rp "Enter UFP_USERNAME: " UFP_USERNAME
  read -rsp "Enter UFP_PASSWORD: " UFP_PASSWORD
  echo

  cat <<EOF > .env
UFP_HOST=$UFP_HOST
UFP_USERNAME=$UFP_USERNAME
UFP_PASSWORD=$UFP_PASSWORD
EOF

  echo "[INFO] .env file created with your credentials."
else
  echo "[INFO] .env file already exists, skipping prompt."
fi

# Add .env to .gitignore if missing
if [ ! -f .gitignore ]; then
  touch .gitignore
fi

if ! grep -q "^.env$" .gitignore; then
  echo ".env" >> .gitignore
  echo "[INFO] .env added to .gitignore"
fi

# Mark scripts executable
chmod +x get_streams.py layout_chooser.py viewport.sh

echo
echo "[✅ SUCCESS] Setup complete!"
echo "You can now run the layout chooser with:"
echo "  ./layout_chooser.py"
