#!/bin/bash
set -e

echo "== UniFi Viewport GUI Setup =="

# Ensure we're in project root
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

echo "[INFO] Configuring LightDM to autologin as 'viewport'..."

sudo mkdir -p /etc/lightdm/lightdm.conf.d

cat <<EOF | sudo tee /etc/lightdm/lightdm.conf.d/50-viewport.conf
[Seat:*]
autologin-user=viewport
autologin-user-timeout=0
autologin-session=openbox
user-session=openbox
EOF

echo "[INFO] Creating Openbox autostart script for viewport..."

mkdir -p /home/viewport/.config/openbox

cat <<'EOF' > /home/viewport/.config/openbox/autostart
#!/bin/bash
xset s off
xset -dpms
xset s noblank
unclutter &
cd /home/viewport/unifi-viewport
python3 layout_chooser.py &
EOF

chmod +x /home/viewport/.config/openbox/autostart
chown -R viewport:viewport /home/viewport/.config/openbox

echo "[SUCCESS] GUI environment configured. On reboot, the system will launch the layout chooser automatically."
