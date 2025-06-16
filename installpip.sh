#!/usr/bin/env bash
set -euo pipefail

echo "== UniFi RTSP Viewport (pip/venv) Installer =="

cd "$(dirname "$0")"

# ─── Check required system commands ──────────────────────────────────────────
REQUIRED_CMDS=(python3 pip3 jq mpv xrandr xdpyinfo xdotool)

for cmd in "${REQUIRED_CMDS[@]}"; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "[ERROR] '$cmd' is not installed. Please install it before continuing."
    exit 1
  fi
done

# ─── Ensure OS packages for psutil & tkinter ────────────────────────────────
PKGS=(python3-psutil python3-tk)
for pkg in "${PKGS[@]}"; do
  if ! dpkg -s "$pkg" &>/dev/null; then
    echo "[INFO] Installing system package: $pkg"
    sudo apt update
    sudo apt install -y "$pkg"
  fi
done

# ─── Create & activate virtualenv ───────────────────────────────────────────
if [ ! -d venv ]; then
  echo "[INFO] Creating Python virtual environment..."
  python3 -m venv venv
fi

echo "[INFO] Activating virtual environment..."
# shellcheck disable=SC1091
source venv/bin/activate

# ─── Generate requirements.txt if missing ───────────────────────────────────
if [ ! -f requirements.txt ]; then
  echo "[INFO] Writing default requirements.txt..."
  cat > requirements.txt <<EOF
python-dotenv
requests
psutil
EOF
fi

# ─── Install Python dependencies ────────────────────────────────────────────
echo "[INFO] Upgrading pip and installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# ─── Prompt for .env variables ──────────────────────────────────────────────
if [ ! -f .env ]; then
  echo
  echo "[INFO] Let's configure your UniFi Protect connection:"
  read -rp "  UFP_HOST     (e.g. https://192.168.5.10): " UFP_HOST
  read -rp "  UFP_USERNAME : " UFP_USERNAME
  read -rsp "  UFP_PASSWORD : " UFP_PASSWORD
  echo
  cat > .env <<EOF
UFP_HOST=$UFP_HOST
UFP_USERNAME=$UFP_USERNAME
UFP_PASSWORD=$UFP_PASSWORD
EOF
  echo "[INFO] .env file created."
else
  echo "[INFO] .env already exists — skipping."
fi

# ─── Add .env to .gitignore if needed ───────────────────────────────────────
if [ ! -f .gitignore ]; then touch .gitignore; fi
if ! grep -q "^.env$" .gitignore; then
  echo ".env" >> .gitignore
  echo "[INFO] .env added to .gitignore"
fi

# ─── Make all entry‐point scripts executable ────────────────────────────────
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

echo "[INFO] Reloading systemd daemon and enabling service…"
sudo systemctl daemon-reload
sudo systemctl enable unifi-viewport.service
sudo systemctl start  unifi-viewport.service

echo
echo "[✅ SUCCESS] Virtualenv setup complete and viewport service installed!"
echo
echo "👉 To get started:"
echo "   source venv/bin/activate"
echo "   ./layout_chooser.py"
echo
echo "Manage the viewport service with:"
echo "   sudo systemctl [start|stop|restart|status] unifi-viewport.service"
