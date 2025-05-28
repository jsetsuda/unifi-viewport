#!/bin/bash
set -e

echo "== UniFi Viewport GUI Setup =="

# Ensure we're in the project root
cd "$(dirname "$0")"

echo "[INFO] Installing GUI and display dependencies..."
sudo apt update
sudo apt install -y \
  openbox \
  lightdm \
  xserver-xorg \
  x11-xserver-utils \
  x11-utils \
  xinit \
  xdotool \
  unclutter \
  policykit-1 \
  lxappearance \
  gtk2-engines-pixbuf

# Create 'viewport' user if it doesn't exist
if ! id "viewport" &>/dev/null; then
  echo "[INFO] Creating 'viewport' user..."
  sudo useradd -m -s /bin/bash viewport
  echo "viewport:viewport" | sudo chpasswd
  sudo usermod -aG sudo viewport
fi

echo "[INFO] Configuring LightDM for autologin..."
sudo mkdir -p /etc/lightdm/lightdm.conf.d
cat <<EOF | sudo tee /etc/lightdm/lightdm.conf.d/50-viewport.conf
[Seat:*]
autologin-user=viewport
autologin-user-timeout=0
autologin-session=openbox
user-session=openbox
EOF

echo "[INFO] Creating Openbox autostart script..."
sudo -u viewport mkdir -p /home/viewport/.config/openbox

cat <<'EOF' | sudo tee /home/viewport/.config/openbox/autostart > /dev/null
#!/bin/bash
xset s off
xset -dpms
xset s noblank
unclutter &
cd /home/viewport/unifi-viewport
python3 layout_chooser.py &
EOF

sudo chmod +x /home/viewport/.config/openbox/autostart
sudo chown -R viewport:viewport /home/viewport/.config/openbox

echo "[SUCCESS] GUI environment configured."
echo "On next reboot, the system will auto-login as 'viewport' and launch the layout chooser."
