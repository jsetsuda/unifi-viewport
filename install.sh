#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# ------------------------------------------------------------------------------
# UniFi-Viewport Consolidated Installer
# Usage: ./install.sh [--pip] [--gui] [--cec] [--all] [--help]
# ------------------------------------------------------------------------------

usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --pip       Set up Python virtualenv, deps, .env, and fetch camera list
  --gui       Install GUI/display environment and prompt for .env
  --cec       Install HDMI-CEC keepalive
  --all       Run pip + gui + cec steps
  -h, --help  Show this message
EOF
  exit 1
}

# — Parse flags —
DO_PIP=false
DO_GUI=false
DO_CEC=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --pip) DO_PIP=true ;;
    --gui) DO_GUI=true ;;
    --cec) DO_CEC=true ;;
    --all) DO_PIP=true; DO_GUI=true; DO_CEC=true ;;
    -h|--help) usage ;;
    *) echo "[ERROR] Unknown option: $1"; usage ;;
  esac
  shift
done

# If no flags provided, show help
if ! $DO_PIP && ! $DO_GUI && ! $DO_CEC; then
  usage
fi

# Ensure we're in the repo root
cd "$(dirname "$0")"

# ------------------------------------------------------------------------------
# Install core system packages (required by all modes)
# ------------------------------------------------------------------------------
echo "[INFO] Updating apt cache…"
sudo apt update

echo "[INFO] Installing core packages…"
sudo apt install -y \
  python3 \
  python3-venv \
  python3-pip \
  python3-psutil \
  python3-tk \
  jq \
  mpv \
  ffmpeg \
  x11-xserver-utils \
  xdotool \
  git

# ------------------------------------------------------------------------------
# Helper: prompt for .env credentials if missing
# ------------------------------------------------------------------------------
prompt_env() {
  if [[ ! -f .env ]]; then
    echo
    echo "  • Configuring UniFi Protect credentials (.env)…"
    read -rp "    UFP_HOST     (e.g. https://192.168.5.10): " UFP_HOST
    read -rp "    UFP_USERNAME : " UFP_USERNAME
    read -rsp "    UFP_PASSWORD : " UFP_PASSWORD
    echo
    cat > .env <<EOF
UFP_HOST=$UFP_HOST
UFP_USERNAME=$UFP_USERNAME
UFP_PASSWORD=$UFP_PASSWORD
EOF
    echo "    → .env created"
  else
    echo "  • .env exists, skipping"
  fi
}

# ------------------------------------------------------------------------------
# Section: Python / pip / venv setup (and initial camera fetch)
# ------------------------------------------------------------------------------
if $DO_PIP; then
  echo
  echo "[STEP] Python virtualenv & dependencies →"

  # 1) Create venv if needed
  if [[ ! -d venv ]]; then
    echo "  • Creating venv…"
    python3 -m venv venv
  fi

  # 2) Activate venv
  echo "  • Activating venv…"
  # shellcheck disable=SC1091
  source venv/bin/activate

  # 3) Ensure requirements.txt
  if [[ ! -f requirements.txt ]]; then
    cat > requirements.txt <<EOF
python-dotenv>=1.0.0
requests>=2.25.1
psutil>=5.9.0
uiprotect>=0.4.0
Pillow>=9.0.0
EOF
    echo "  • Wrote default requirements.txt"
  fi

  # 4) Install Python packages
  echo "  • Upgrading pip & installing requirements…"
  pip install --upgrade pip
  pip install -r requirements.txt

  # 5) Prompt for .env
  prompt_env

  # 6) Add .env to .gitignore
  grep -qxF '.env' .gitignore 2>/dev/null || {
    echo ".env" >> .gitignore
    echo "  • Added .env to .gitignore"
  }

  # 7) Mark entry scripts executable
  chmod +x get_streams.py layout_chooser.py viewport.sh monitor_streams.py
  echo "  • Marked entry-point scripts executable"

  # 8) Fetch initial camera list
  echo "  • Fetching initial camera list…"
  python3 get_streams.py && echo "  → camera_urls.json created" || echo "  ! get_streams.py failed"

  # 9) Deactivate venv
  deactivate
fi

# ------------------------------------------------------------------------------
# Section: GUI/display (LightDM + Openbox)
# ------------------------------------------------------------------------------
if $DO_GUI; then
  echo
  echo "[STEP] GUI/display environment →"

  echo "  • Installing GUI packages…"
  sudo apt install -y \
    lightdm \
    openbox \
    xserver-xorg \
    x11-utils \
    unclutter \
    policykit-1 \
    lxappearance \
    gtk2-engines-pixbuf

  # Prompt for .env here as well
  prompt_env

  # Create 'viewport' user if missing
  if ! id viewport &>/dev/null; then
    echo "  • Creating 'viewport' user…"
    sudo useradd -m -s /bin/bash viewport
    echo "viewport:viewport" | sudo chpasswd
  fi

  echo "  • Configuring LightDM autologin…"
  sudo mkdir -p /etc/lightdm/lightdm.conf.d
  sudo tee /etc/lightdm/lightdm.conf.d/50-viewport.conf >/dev/null <<EOF
[Seat:*]
autologin-user=viewport
autologin-user-timeout=0
user-session=openbox
EOF

  echo "  • Creating Openbox autostart…"
  sudo -u viewport mkdir -p /home/viewport/.config/openbox
  sudo tee /home/viewport/.config/openbox/autostart >/dev/null <<'EOF'
#!/usr/bin/env bash
# disable screen blanking
xset s off
xset -dpms
xset s noblank

# hide mouse when idle
unclutter &
EOF
  sudo chmod +x /home/viewport/.config/openbox/autostart
  sudo chown -R viewport:viewport /home/viewport/.config
fi

# ------------------------------------------------------------------------------
# Section: HDMI-CEC keepalive
# ------------------------------------------------------------------------------
if $DO_CEC; then
  echo
  echo "[STEP] HDMI-CEC keepalive →"
  sudo bash install-cec-keepalive.sh
fi

# ------------------------------------------------------------------------------
# Section: systemd service for viewport.sh
# ------------------------------------------------------------------------------
echo
echo "[STEP] Installing systemd service → /etc/systemd/system/unifi-viewport.service"

SERVICE_USER=viewport
INSTALL_DIR="$(pwd)"

sudo tee /etc/systemd/system/unifi-viewport.service >/dev/null <<EOF
[Unit]
Description=UniFi Protect Viewport
After=graphical.target network.target
Wants=graphical.target

[Service]
User=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/$(id -u ${SERVICE_USER})
ExecStart=${INSTALL_DIR}/viewport.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
EOF

echo "Reloading systemd daemon & enabling service…"
sudo systemctl daemon-reload
sudo systemctl enable unifi-viewport.service
sudo systemctl start  unifi-viewport.service

# ── Fix permissions so the viewport user can write configs ────────────────────
echo "[INFO] Fixing permissions on project directory…"
sudo chown -R viewport:viewport "${INSTALL_DIR}"

echo
echo "[✅ Done!]"
echo "Next steps:"
echo "  • To reconfigure .env, re-run with --pip or --gui"
echo "  • To tweak GUI autostart, re-run with --gui"
echo "  • To adjust CEC, re-run with --cec"
echo
echo "Control the viewport service with:"
echo "  sudo systemctl [start|stop|restart|status] unifi-viewport.service"
