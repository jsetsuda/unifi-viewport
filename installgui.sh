#!/bin/bash
# installgui.sh – Sets up lightweight X11 GUI environment for UniFi Viewport

set -e

echo "[INFO] Installing X11, Openbox, LightDM, and dependencies..."
sudo apt update
sudo apt install -y \
  xserver-xorg x11-xserver-utils xinit openbox lightdm \
  tk python3-tk mpv jq git curl ffmpeg python3-venv

echo "[INFO] Setting Openbox as default session..."
echo "openbox-session" > ~/.xsession

echo "[INFO] Creating Openbox autostart directory..."
mkdir -p ~/.config/openbox

echo "[INFO] Adding layout chooser to Openbox autostart..."
cat <<EOF > ~/.config/openbox/autostart
python3 /home/viewport/unifi-viewport/layout_chooser.py &
EOF

echo "[DONE] GUI environment is installed. Please run 'sudo raspi-config' to enable Desktop Autologin manually."
