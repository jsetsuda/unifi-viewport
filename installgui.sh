#!/usr/bin/env bash
set -euo pipefail

echo "== UniFi Viewport All-in-One Setup for Raspberry Pi OS Lite =="

# Ensure we're in the project root
cd "$(dirname "$0")"

# --- Install system dependencies ---
echo "[INFO] Installing GUI, display, and runtime dependencies..."
sudo apt update
sudo apt install -y \
  python3 \
  python3-pip \
  python3-tk \
  python3-psutil \
  ffmpeg \
  mpv \
  jq \
  lightdm \
  openbox \
  xserver-xorg \
  x11-xserver-utils \
  x11-utils \
  xinit \
  xdotool \
  unclutter \
  policykit-1 \
  lxappearance \
  gtk2-engines-pixbuf \
  libnss3-tools \
  libgl1-mesa-glx \
  libpulse0 \
  libegl1 \
  git

# --- Prompt for .env setup if needed ---
if [ ! -f .env ]; then
  echo
  echo "[INFO] Creating .env file for UniFi Protect credentials..."
  read -rp "  UFP_HOST     (e.g. https://192.168.5.10): " host
  read -rp "  UFP_USERNAME : " username
  read -rsp "  UFP_PASSWORD : " password
  echo
  cat > .env <<EOF
UFP_HOST=$host
UFP_USERNAME=$username
UFP_PASSWORD=$password
EOF
  echo "[INFO] .env file created."
else
  echo "[INFO] .env already exists — skipping."
fi

# --- Install Python packages ---
echo "[INFO] Installing Python libraries..."
pip3 install --break-system-packages \
  python-dotenv \
  requests \
  psutil

# --- Ensure viewport user exists ---
if ! id "viewport" &>/dev/null; then
  echo "[INFO] Creating 'viewport' user..."
  sudo useradd -m -s /bin/bash viewport
  echo "viewport:viewport" | sudo chpasswd
  sudo usermod -aG sudo viewport
fi

# --- Configure LightDM for autologin ---
echo "[INFO] Configuring LightDM for autologin..."
sudo mkdir -p /etc/lightdm/lightdm.conf.d
cat <<EOF | sudo tee /etc/lightdm/lightdm.conf.d/50-viewport.conf >/dev/null
[Seat:*]
autologin-user=viewport
autologin-user-timeout=0
autologin-session=openbox
user-session=openbox
EOF

# --- Create Openbox autostart script ---
echo "[INFO] Creating Openbox autostart for layout chooser..."
sudo -u viewport mkdir -p /home/viewport/.config/openbox
cat <<'EOF' | sudo tee /home/viewport/.config/openbox/autostart >/dev/null
#!/usr/bin/env bash
# disable screen blanking
xset s off
xset -dpms
xset s noblank

# hide mouse when idle
unclutter &

# launch layout chooser on login
cd /home/viewport/unifi-viewport
./layout_chooser.py &
EOF

sudo chmod +x /home/viewport/.config/openbox/autostart
sudo chown -R viewport:viewport /home/viewport/.config/openbox

# --- Mark all scripts executable ---
echo "[INFO] Marking entry-point scripts executable..."
chmod +x get_streams.py \
         layout_chooser.py \
         viewport.sh \
         monitor_streams.py \
         kill_stale_streams.py \
         overlay_box.py

# ── Install systemd service for unifi-viewport ───────────────────────────────
SERVICE_USER=viewport
SERVICE_GROUP=viewport
INSTALL_DIR="$(pwd)"
SERVICE_FILE=/etc/systemd/system/unifi-viewport.service

echo
echo "[INFO] Installing systemd service → $SERVICE_FILE"

sudo tee "$SERVICE_FILE" > /dev/null <<EOF
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
echo "[✅ COMPLETE] All-in-one GUI install finished!"
echo "  • Your Pi will auto-login as 'viewport' and launch the layout chooser."
echo "  • The viewport service will start at boot and restart on failure."
echo
echo "Manage the service with:"
echo "  sudo systemctl [start|stop|restart|status] unifi-viewport.service"
