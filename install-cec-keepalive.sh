#!/bin/bash
set -euo pipefail

echo "🔧 Installing HDMI-CEC Keepalive and Scheduler..."

# === Prompt for schedule ===
read -rp "🕐 Enter ON time (24h format, e.g. 07:00): " ON_TIME
read -rp "🌙 Enter OFF time (24h format, e.g. 22:00): " OFF_TIME

# Validate time format
[[ "$ON_TIME" =~ ^([01]?[0-9]|2[0-3]):[0-5][0-9]$ ]] || { echo "❌ Invalid ON time"; exit 1; }
[[ "$OFF_TIME" =~ ^([01]?[0-9]|2[0-3]):[0-5][0-9]$ ]] || { echo "❌ Invalid OFF time"; exit 1; }

# Extract hour and minute
ON_HOUR="${ON_TIME%:*}"
ON_MIN="${ON_TIME#*:}"
OFF_HOUR="${OFF_TIME%:*}"
OFF_MIN="${OFF_TIME#*:}"

# === Variables ===
USER_HOME="/home/viewport"
LOG_FILE="$USER_HOME/cec_keepalive.log"
KEEPALIVE_SCRIPT="$USER_HOME/keep_display_awake.py"
CONTROL_SCRIPT="$USER_HOME/cec_control.py"
SERVICE_FILE="/etc/systemd/system/cec-keepalive.service"
PYTHON_BIN="/usr/bin/python3"

# === 1. Install required packages ===
echo "📦 Installing required packages..."
sudo apt update
sudo apt install -y cec-utils python3

# === 2. Create keep_display_awake.py ===
echo "📝 Creating $KEEPALIVE_SCRIPT..."
cat << EOF | sudo tee "$KEEPALIVE_SCRIPT" > /dev/null
#!/usr/bin/env python3

import subprocess
import time
import logging

PING_INTERVAL = 300  # seconds

logging.basicConfig(filename='$LOG_FILE', level=logging.INFO)

def is_display_on():
    result = subprocess.run(
        ['cec-client', '-s', '-d', '1'],
        input=b'pow 0\n',
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return b'on' in result.stdout.lower()

def send_cec_ping():
    if is_display_on():
        subprocess.run(['cec-client', '-s', '-d', '1'], input=b'on 0\n', check=True)
        logging.info("Display ON: sent keepalive ping at %s", time.ctime())
    else:
        logging.info("Display is OFF — skipping ping at %s", time.ctime())

if __name__ == "__main__":
    while True:
        send_cec_ping()
        time.sleep(PING_INTERVAL)
EOF

sudo chmod +x "$KEEPALIVE_SCRIPT"
sudo chown viewport:viewport "$KEEPALIVE_SCRIPT"

# === 3. Create cec_control.py ===
echo "📝 Creating $CONTROL_SCRIPT..."
cat << EOF | sudo tee "$CONTROL_SCRIPT" > /dev/null
#!/usr/bin/env python3

import sys
import subprocess
import logging
from datetime import datetime

logging.basicConfig(filename='$LOG_FILE', level=logging.INFO)

def cec_command(cmd):
    subprocess.run(['cec-client', '-s', '-d', '1'], input=f"{cmd} 0\n".encode(), check=True)

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("on", "off"):
        print("Usage: cec_control.py [on|off]")
        sys.exit(1)

    cmd = sys.argv[1]
    action = "on" if cmd == "on" else "standby"
    cec_command(action)

    logging.info("Manual trigger: Display %s at %s", cmd.upper(), datetime.now().ctime())
EOF

sudo chmod +x "$CONTROL_SCRIPT"
sudo chown viewport:viewport "$CONTROL_SCRIPT"

# === 4. Create systemd service ===
echo "🔧 Creating systemd service at $SERVICE_FILE..."
cat << EOF | sudo tee "$SERVICE_FILE" > /dev/null
[Unit]
Description=Keep HDMI display awake via CEC
After=network.target

[Service]
ExecStart=$PYTHON_BIN $KEEPALIVE_SCRIPT
Restart=always
User=viewport

[Install]
WantedBy=default.target
EOF

# === 5. Enable and start the service ===
echo "🚀 Enabling and starting cec-keepalive service..."
sudo systemctl daemon-reexec
sudo systemctl enable cec-keepalive
sudo systemctl start cec-keepalive

# === 6. Add cron jobs for scheduled on/off ===
echo "🕰️ Adding cron jobs to turn screen ON at $ON_TIME and OFF at $OFF_TIME..."
CRON_JOB_ON="$ON_MIN $ON_HOUR * * * $PYTHON_BIN $CONTROL_SCRIPT on"
CRON_JOB_OFF="$OFF_MIN $OFF_HOUR * * * $PYTHON_BIN $CONTROL_SCRIPT off"

( crontab -l 2>/dev/null | grep -v -F "$CONTROL_SCRIPT" || true
  echo "$CRON_JOB_ON"
  echo "$CRON_JOB_OFF"
) | crontab -

echo "✅ Setup complete."
echo "📜 Log: $LOG_FILE"
