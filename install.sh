#!/bin/bash

# install.sh - UniFi RTSP Viewport Installer

set -e

echo "=== UniFi RTSP Viewport Setup ==="

# 1. Update packages
echo "[1/7] Updating system packages..."
sudo apt update && sudo apt full-upgrade -y

# 2. Install required packages
echo "[2/7] Installing dependencies..."
sudo apt install -y python3 python3-pip python3-tk python3-requests python3-pil python3-opencv \
                    mpv jq git ffmpeg x11-utils

# 3. Setup autostart (for Desktop GUI only)
if [ -d /etc/xdg/autostart ]; then
    echo "[3/7] Setting up autostart..."
    AUTOSTART_FILE="/etc/xdg/autostart/unifi-viewport.desktop"
    sudo tee "$AUTOSTART_FILE" > /dev/null <<EOF
[Desktop Entry]
Type=Application
Exec=/home/viewport/unifi-viewport/layout_chooser.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=UniFi Viewport
Comment=Start UniFi RTSP Viewport
EOF
    sudo chmod +x "$AUTOSTART_FILE"
fi

# 4. Set executable permissions
echo "[4/7] Setting permissions..."
chmod +x ~/unifi-viewport/*.py
chmod +x ~/unifi-viewport/*.sh

# 5. Create logs directory if needed
mkdir -p ~/unifi-viewport/logs

# 6. Optional: Create Python virtualenv (not required for now)
# python3 -m venv ~/unifi-viewport/venv
# source ~/unifi-viewport/venv/bin/activate
# pip install -r requirements.txt

# 7. Done
echo "✅ Install complete. You can now run:"
echo "    ~/unifi-viewport/layout_chooser.py"
echo
echo "If running from GUI, it will auto-start on reboot."
