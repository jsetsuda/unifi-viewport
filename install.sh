#!/bin/bash

set -e

echo "[INFO] Updating system..."
sudo apt update && sudo apt upgrade -y

echo "[INFO] Installing dependencies..."
sudo apt install -y \
  python3 python3-pip python3-tk jq mpv xinit openbox git x11-xserver-utils \
  python3-venv ffmpeg libx11-dev

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

echo "[INFO] Setting up autostart with Openbox..."
mkdir -p /home/viewport/.config/openbox
cat << 'EOL' > /home/viewport/.config/openbox/autostart
#!/bin/bash
xset s off
xset -dpms
xset s noblank
cd ~/unifi-viewport
./layout_chooser.py
EOL
chmod +x /home/viewport/.config/openbox/autostart
chown -R viewport:viewport /home/viewport/.config

echo "[INFO] Creating X session startup..."
cat << 'EOL' > /home/viewport/.xinitrc
#!/bin/bash
exec openbox-session
EOL
chmod +x /home/viewport/.xinitrc
chown viewport:viewport /home/viewport/.xinitrc

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
