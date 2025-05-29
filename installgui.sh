#!/bin/bash
set -euo pipefail

echo "== UniFi Viewport All-in-One Setup for Raspberry Pi OS Lite =="

# Ensure we're in the project root
cd "$(dirname "$0")"

# === Install system dependencies ===
echo "[INFO] Installing GUI, display, and runtime dependencies..."
sudo apt update
sudo apt install -y \
  python3 \
  python3-pip \
  python3-tk \
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

# === Prompt for .env setup ===
if [ ! -f ".env" ]; then
  echo "[INFO] Creating .env file..."
  read -p "Enter UniFi Protect Host (e.g. https://192.168.1.1): " host
  read -p "Enter UniFi Protect Username: " username
  read -s -p "Enter UniFi Protect Password: " password
  echo
  cat <<EOF > .env
UFP_HOST=$host
UFP_USERNAME=$username
UFP_PASSWORD=$password
EOF
  echo "[INFO] .env file created."
fi

# === Install Python packages ===
echo "[INFO] Installing Python packages..."
pip3 install --break-system-packages \
  python-dotenv \
  requests \
  uiprotect

# === Create 'viewport' user for GUI login ===
if ! id "viewport" &>/dev/null; then
  echo "[INFO] Creating 'viewport' user..."
  sudo useradd -m -s /bin/bash viewport
  echo "viewport:viewport" | sudo chpasswd
  sudo usermod -aG sudo viewport
fi

# === Configure LightDM for autologin ===
echo "[INFO] Configuring LightDM for autologin..."
sudo mkdir -p /etc/lightdm/lightdm.conf.d
cat <<EOF | sudo tee /etc/lightdm/lightdm.conf.d/50-viewport.conf
[Seat:*]
autologin-user=viewport
autologin-user-timeout=0
autologin-session=openbox
user-session=openbox
EOF

# === Create Openbox autostart script ===
echo "[INFO] Creating Openbox autostart script..."
sudo -u viewport mkdir -p /home/viewport/.config/openbox
cat <<'EOF' | sudo tee /home/viewport/.config/openbox/autostart > /dev/null
#!/bin/bash
xset s off
xset -dpms
xset s noblank
unclutter &
cd /home/viewport/unifi-viewport
./layout_chooser.py &
EOF

sudo chmod +x /home/viewport/.config/openbox/autostart
sudo chown -R viewport:viewport /home/viewport/.config/openbox

echo "[✅ COMPLETE] All-in-one installation done!"
echo "➡️  Reboot now. The system will auto-login as 'viewport' and launch the layout chooser."
