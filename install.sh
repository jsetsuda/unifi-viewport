#!/bin/bash

set -e

echo "[INFO] Updating system..."
sudo apt update && sudo apt upgrade -y

echo "[INFO] Installing dependencies..."
sudo apt install -y \
  python3 python3-pip python3-tk jq mpv xinit openbox git x11-xserver-utils \
  python3-venv ffmpeg libx11-dev xserver-xorg lxde lxdm

echo "[INFO] Creating viewport user if needed..."
if ! id -u viewport >/dev/null 2>&1; then
  sudo adduser --disabled-password --gecos "" viewport
  sudo usermod -aG video,render,input,dialout,tty viewport
fi

echo "[INFO] Cloning repository as viewport..."
sudo -u viewport -H bash <<EOF
cd ~
git clone https://github.com/jsetsuda/unifi-viewport.git
cd unifi-viewport
python3 -m pip install --user requests
EOF

echo "[INFO] Prompting for UniFi Protect credentials..."
read -p "Enter UniFi Protect host (e.g., https://192.168.5.10): " UFP_HOST
read -p "Enter UniFi Protect username: " UFP_USERNAME
read -s -p "Enter UniFi Protect password: " UFP_PASSWORD
echo

ENV_FILE="/home/viewport/unifi-viewport/.env"
sudo tee "$ENV_FILE" > /dev/null <<EOF
UFP_HOST=$UFP_HOST
UFP_USERNAME=$UFP_USERNAME
UFP_PASSWORD=$UFP_PASSWORD
EOF
sudo chown viewport:viewport "$ENV_FILE"
sudo chmod 600 "$ENV_FILE"

echo "[INFO] Setting up Openbox autostart..."
mkdir -p /home/viewport/.config/openbox
cat << 'EOL' | sudo tee /home/viewport/.config/openbox/autostart > /dev/null
#!/bin/bash
xset s off
xset -dpms
xset s noblank
cd ~/unifi-viewport
./layout_chooser.py
EOL
sudo chmod +x /home/viewport/.config/openbox/autostart
sudo chown -R viewport:viewport /home/viewport/.config

echo "[INFO] Creating X session startup..."
cat << 'EOL' | sudo tee /home/viewport/.xinitrc > /dev/null
#!/bin/bash
exec openbox-session
EOL
sudo chmod +x /home/viewport/.xinitrc
sudo chown viewport:viewport /home/viewport/.xinitrc

echo "[INFO] Configuring LXDM autologin..."
sudo sed -i 's/^#autologin-user=.*/autologin-user=viewport/' /etc/lxdm/lxdm.conf

echo "[INFO] Creating systemd service to auto-start X on boot..."
sudo tee /etc/systemd/system/viewport-display.service > /dev/null << 'EOF'
[Unit]
Description=Start X with Openbox for Viewport
After=network.target

[Service]
User=viewport
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/1000
ExecStart=/usr/bin/startx
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "[INFO] Enabling viewport-display.service..."
sudo systemctl enable viewport-display.service

echo "[DONE] Installation complete. Reboot the system to launch the viewer."
