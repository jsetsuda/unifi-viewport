#!/usr/bin/env bash
set -euo pipefail

echo "== UniFi RTSP Viewport (pip/venv) Installer =="

# Ensure script is run from project root
cd "$(dirname "$0")"

# === Required system commands ===
REQUIRED_CMDS=(python3 pip3 jq mpv xrandr xdpyinfo)

for cmd in "${REQUIRED_CMDS[@]}"; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "[ERROR] '$cmd' is not installed. Please install it before continuing."
        exit 1
    fi
done

# === Create virtual environment ===
if [ ! -d venv ]; then
    echo "[INFO] Creating Python virtual environment..."
    python3 -m venv venv
fi

# === Activate virtual environment ===
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# === Create requirements.txt if not present ===
if [ ! -f requirements.txt ]; then
    echo "[INFO] Creating default requirements.txt..."
    cat <<EOF > requirements.txt
python-dotenv
requests
psutil
EOF
fi

# === Install Python dependencies ===
echo "[INFO] Installing Python packages into venv..."
pip install --upgrade pip
pip install -r requirements.txt

# === Create .env file if missing ===
if [ ! -f .env ]; then
    echo "[INFO] Creating .env template..."
    cat <<EOF > .env
UFP_HOST=https://192.168.5.10
UFP_USERNAME=your_username
UFP_PASSWORD=your_password
EOF
    echo "[INFO] .env file created. Please edit it with your UniFi Protect login info."
else
    echo "[INFO] .env file already exists, skipping creation."
fi

# === Add .env to .gitignore if needed ===
if [ ! -f .gitignore ]; then
    touch .gitignore
fi

if ! grep -q "^.env$" .gitignore; then
    echo ".env" >> .gitignore
    echo "[INFO] .env added to .gitignore"
fi

# === Mark key scripts executable ===
chmod +x get_streams.py layout_chooser.py viewport.sh

echo "[✅ SUCCESS] Setup complete using virtualenv."
echo
echo "👉 To begin:"
echo "  source venv/bin/activate"
echo "  ./layout_chooser.py"
