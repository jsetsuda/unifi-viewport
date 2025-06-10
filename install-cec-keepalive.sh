#!/bin/bash
set -euo pipefail

echo "🔧 Installing HDMI-CEC Keepalive Script for Raspberry Pi..."

# === Variables ===
SCRIPT_NAME="keep_display_awake.py"
SCRIPT_PATH="/home/pi/${SCRIPT_NAME}"
SERVICE_NAME="cec-keepalive"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
LOG_FILE="/home/pi/cec_keepalive.log"

# === 1. Install required packages ===
echo "📦 Installing required packages..."
sudo apt update
sudo apt install -y cec-utils python3

# === 2. Create the keepalive Python script ===
echo "📝 Creating Python script at $SCRIPT_PATH..."
cat << EOF | sudo tee "$SCRIPT_PATH" > /dev/null
#!/usr/bin/env python3

import subprocess
import time
import logging

PING_INTERVAL = 300  # seconds

logging.basicConfig(filename='$LOG_FILE', level=logging.INFO)

def send_cec_ping():
    try:
        subprocess.run(['cec-client', '-s', '-d', '1'], input=b'on 0\n', check=True)
        logging.info("Sent CEC ping at %s", time.ctime())
    except subprocess.CalledProcessError as e:
        logging.error("Failed to send CEC ping: %s", str(e))

if __name__ == "__main__":
    while True:
        send_cec_ping()
        time.sleep(PING_INTERVAL)
EOF

sudo chmod +x "$SCRIPT_PATH"
sudo chown pi:pi "$SCRIPT_PATH"

# === 3. Create systemd service file ===
echo "🔧 Creating systemd service at $SERVICE_FILE..."
cat << EOF | sudo tee "$SERVICE_FILE" > /dev/null
[Unit]
Description=Keep HDMI display awake via CEC
After=network.target

[Service]
ExecStart=/usr/bin/python3 $SCRIPT_PATH
Restart=always
User=pi

[Install]
WantedBy=default.target
EOF

# === 4. Enable and start the service ===
echo "🚀 Enabling and starting the $SERVICE_NAME service..."
sudo systemctl daemon-reexec
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

echo "✅ Done. CEC keepalive service is now running."
echo "📝 Log file: $LOG_FILE"
