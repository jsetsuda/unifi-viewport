# UniFi RTSP Viewport for Raspberry Pi

A lightweight RTSP viewer system for UniFi cameras, designed to emulate the UniFi Protect Viewport experience using a Raspberry Pi with minimal overhead.

---

## 🎯 Features

- Auto-launching tiled RTSP stream display
- Automatic stream health monitoring and restart
- Graphical layout selector and camera assignment tool
- Low-latency `mpv` playback for real-time responsiveness
- Stream validation to ensure H.264 compatibility
- Central `.env` configuration for easy updates
- Works with Raspberry Pi OS Lite + minimal X11 setup

---

## 🧰 Initial Raspberry Pi Setup

**Recommended OS:** Raspberry Pi OS Lite 64-bit (for performance and minimal footprint)

### 1. Flash Raspberry Pi OS Lite
Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to install **Raspberry Pi OS Lite (64-bit)**.

### 2. Initial Setup
Login and configure:
```bash
sudo raspi-config
# Set hostname, timezone, Wi-Fi, expand filesystem (optional)
```

---

## 🖥️ Lightweight GUI Setup (No Full Desktop Required)

Install a minimal X11 environment and supporting tools:

```bash
sudo apt update && sudo apt install -y \
  xserver-xorg x11-xserver-utils xinit openbox lightdm \
  tk python3-tk mpv jq git curl ffmpeg python3-venv
```

Enable autologin:
```bash
sudo raspi-config
# System Options → Boot / Auto Login → Desktop Autologin
```

Set Openbox session:
```bash
echo "openbox-session" > ~/.xsession
```

Autostart the layout chooser GUI:
```bash
mkdir -p ~/.config/openbox
nano ~/.config/openbox/autostart
```
Add:
```bash
python3 /home/viewport/unifi-viewport/layout_chooser.py &
```

---

## 🚀 Project Installation

### 1. Clone the repository
```bash
cd ~
git clone https://github.com/jsetsuda/unifi-viewport.git
cd unifi-viewport
```

### 2. Run the install script
```bash
chmod +x install.sh
./install.sh
```
This will:
- Create a Python virtual environment
- Install dependencies
- Prompt you to set `.env` (host, username, password)
- Add `.env` to `.gitignore`

---

## 🔄 Reboot to Apply Changes
```bash
sudo reboot
```

System will auto-launch the layout GUI. After 10 seconds, it defaults to the saved layout if no input is received.

---

## ⚙️ `.env` Configuration

All credentials are stored in `.env`:

```ini
UNIFI_HOST=https://192.168.5.10
USERNAME=viewport
PASSWORD=your_password
```

Never check this file into Git. It is ignored via `.gitignore`.

---

## 🧪 Scripts and Usage

Run scripts from the virtual environment:

```bash
source .venv/bin/activate
python get_streams.py       # Pull & validate streams
./viewport.sh               # Launch all tile windows
python monitor_streams.py   # (Optional) Monitor and recover dead streams
```

---

## 📁 File Overview

| File                     | Purpose                                      |
|--------------------------|----------------------------------------------|
| `install.sh`             | Installs system + Python dependencies        |
| `.env`                   | Stores UniFi connection credentials          |
| `.gitignore`             | Prevents secrets and layout data from commit|
| `get_streams.py`         | Pull and validate RTSP streams from UniFi   |
| `camera_urls.json`       | Auto-generated list of usable streams        |
| `viewport.sh`            | Launches all streams in tiled layout        |
| `layout_chooser.py`      | GUI to configure stream layout and mapping  |
| `monitor_streams.py`     | Watches and restarts failed `mpv` processes |
| `overlay_box.py`         | Stream status overlays (optional)           |
| `viewport_config.json`   | Layout configuration saved by GUI           |

---

## 🧑‍💻 GitHub Setup

To push changes:
1. [Create a GitHub Personal Access Token](https://github.com/settings/tokens)
2. Use the token in place of your GitHub password when pushing.

---

## 📸 Optional Screenshot

_Add a screenshot of your tiled RTSP camera display here._

---

## 📄 License

MIT License  
© 2025 Jason Setsuda
