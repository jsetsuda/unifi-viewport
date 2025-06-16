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
  jq \
  mpv \
  cec-utils \
  x11-xserver-utils \
  ffmpeg \
  tmux \
  libxcb-util0-dev \
  libxcb1-dev \
  libxcb-randr0-dev \
  libxcb-xinerama0-dev \
  git

# (Optional) install Python dependencies via pip
echo "[INFO] Installing Python packages…"
pip3 install --user -r requirements.txt

# Make sure all of our scripts are executable
chmod +x get_streams.py \
         layout_chooser.py \
         viewport.sh \
         monitor_streams.py \
         kill_stale_streams.py \
         overlay_box.py

# ── Install systemd service for unifi-viewport ────────────────────────────────
SERVICE_USER=viewport
SERVICE_GROUP=viewport
INSTALL_DIR="$(pwd)"
SERVICE_FILE=/etc/systemd/system/unifi-viewport.service

echo
echo "[INFO] Installing systemd service → $SERVICE_FILE"

sudo tee "$SERVICE_FILE" > /dev/null << 'EOF'
[Unit]
Description=UniFi Protect Viewport
After=graphical.target network.target
Wants=graphical.target

[Service]
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${INSTALL_DIR}
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/$(id -u ${SERVICE_USER})

ExecStart=${INSTALL_DIR}/viewport.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
EOF

echo "[INFO] Reloading systemd daemon and enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable unifi-viewport.service
sudo systemctl start  unifi-viewport.service

echo
echo "[✅] Installation complete!"
echo "  • Run the chooser manually:   ./layout_chooser.py"
echo "  • Or let it auto-start at boot via systemd."
echo
echo "Manage the service with:"
echo "  sudo systemctl [start|stop|restart|status] unifi-viewport.service"
