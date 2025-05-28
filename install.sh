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
  python3-venv \
  ffmpeg \
  mpv \
  jq \
  libnss3-tools \
  libgl1-mesa-glx \
  libpulse0

# Create and activate virtual environment
echo "[INFO] Creating Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
echo "[INFO] Installing Python packages..."
pip install --upgrade pip
pip install python-dotenv requests

# Prompt user for .env configuration
echo "[INFO] Setting up .env configuration..."

read -p "Enter your UniFi Protect host (e.g., https://192.168.5.10): " UNIFI_HOST
read -p "Enter your UniFi Protect username: " USERNAME
read -s -p "Enter your UniFi Protect password: " PASSWORD
echo

cat > .env <<EOF
UNIFI_HOST=$UNIFI_HOST
USERNAME=$USERNAME
PASSWORD=$PASSWORD
EOF

echo "[INFO] .env file created."

# Add .env to .gitignore if missing
if [ ! -f .gitignore ]; then
  touch .gitignore
fi

if ! grep -q "^.env$" .gitignore; then
  echo ".env" >> .gitignore
  echo "[INFO] .env added to .gitignore"
fi

echo "[SUCCESS] Setup complete. You can now run:"
echo "  source .venv/bin/activate"
echo "  python get_streams.py"
