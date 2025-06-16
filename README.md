UniFi RTSP Viewport for Raspberry Pi

A lightweight Raspberry Pi–based viewport for displaying UniFi Protect RTSP/S streams in a tiled layout, with automatic resolution detection, health monitoring, and HDMI‑CEC support.

🧰 Initial Raspberry Pi Setup

Recommended OS: Raspberry Pi OS Lite (64‑bit)Ideal for headless or kiosk‑style deployments.

1. Flash Raspberry Pi OS Lite

Use the Raspberry Pi Imager to install Raspberry Pi OS Lite (64‑bit).

2. Log in via SSH or directly

Configure hostname, timezone, Wi‑Fi, etc. via raspi-config:

sudo raspi-config

3. Expand Filesystem (Optional)

sudo raspi-config   # Advanced Options → Expand Filesystem

Quickstart

Clone the repository

git clone https://github.com/jsetsuda/unifi-viewport.git
cd unifi-viewport

Install with the unified installer

chmod +x installmain.sh
sudo ./installmain.sh --all

Reboot or start the service

sudo systemctl start unifi-viewport.service

Installation Flags

Run installmain.sh with one or more of these flags:

--pip

Creates a Python 3 virtual environment in ./venv/.

Installs Python dependencies (python-dotenv, requests, psutil, uiprotect, Pillow).

Prompts to configure .env with UniFi Protect credentials.

Adds .env to .gitignore and marks entry‑point scripts executable.

--gui

Installs LightDM, Openbox, X11, and display utilities (x11-xserver-utils, xdotool, unclutter).

Creates a viewport user (if missing) and configures autologin on display :0.

Sets up Openbox autostart to launch the layout chooser at login.

--cec

Installs and configures HDMI‑CEC keepalive via cec-utils.

Ensures the TV remains powered on and responsive to CEC commands.

--all

Shorthand for running --pip, --gui, and --cec together.

Example:

sudo ./installmain.sh --pip --gui

Installs Python deps and GUI without CEC.

🎛 Configuring UniFi Protect for RTSP

In UniFi Protect → Camera → Settings → Advanced

Enable H.264 RTSP (“High”, “Medium”, or “Low”).

Avoid HEVC (H.265) unless your Pi can handle it.

Recording Settings → Encoding = Standard.

To refresh your camera list after changes:

source venv/bin/activate   # if using venv
python3 get_streams.py

🚀 First Run

If autolaunch doesn’t occur (or you’re in virtualenv mode), manually fetch cameras and choose a layout:

source venv/bin/activate   # skip if system‑wide install
./layout_chooser.py

After saving a layout, reboots will auto‑launch the last configuration after a brief timeout.

Project Components

File

Description

layout_chooser.py

GUI for selecting grid size, assigning cameras to tiles, and saving viewport_config.json.

get_streams.py

Fetches UniFi Protect RTSP URLs and writes to camera_urls.json.

viewport.sh

Detects display resolution, launches MPV tiles, and starts the health monitor.

monitor_streams.py

Periodically checks each stream’s health and restarts stalled streams.

kill_stale_streams.py

Terminates orphaned MPV processes.

overlay_box.py

Draws status overlays on each tile indicating stream health.

installmain.sh

Unified installer for pip, GUI, and CEC components with command‑line flags.

How It Works

┌───────────────┐   ┌───────────────┐   ┌────────────────┐
│ UniFi Protect │──▶│ get_streams.py│──▶│ camera_urls.json│
└───────────────┘   └───────────────┘   └────────────────┘
                             │
                             ▼
                       ┌───────────────┐   ┌───────────────┐
                       │ viewport.sh   │──▶│   mpv windows │
                       └───────────────┘   └───────────────┘
                             │
         ┌───────────────────┴──────────────────┐
         ▼                                      ▼
┌──────────────────┐                   ┌────────────────┐
│ monitor_streams.py│                   │ overlay_box.py │
└──────────────────┘                   └────────────────┘

Troubleshooting

Service logs:

sudo journalctl -u unifi-viewport.service -f

Application logs:Check viewport.log in the repository root.

Resolution detection:Ensure xrandr (X11) or tvservice (RPi) is installed.

CEC issues:Verify cec-utils and that your TV supports HDMI‑CEC.

API errors:Confirm .env credentials and network connectivity to your UniFi Protect controller.

License

This project is licensed under the MIT License – see LICENSE for details.
