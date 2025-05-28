# UniFi RTSP Viewport for Raspberry Pi

A lightweight RTSP viewer system for UniFi cameras, designed to emulate the UniFi Protect Viewport experience using a Raspberry Pi with minimal overhead.

## Features
- Auto-launching tiled RTSP stream display
- Automatic stream health monitoring and restart
- Graphical layout selector and camera assignment tool
- Low-latency `mpv` playback
- Works with Raspberry Pi OS Lite + minimal X11 setup

---

## 🧰 Initial Raspberry Pi Setup

**Recommended OS:** Raspberry Pi OS Lite 64-bit (for performance and minimal footprint)

### 1. Flash Raspberry Pi OS Lite
Use the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to install **Raspberry Pi OS Lite (64-bit)**.

### 2. Log in via SSH or directly
Set hostname, timezone, WiFi, etc. via `raspi-config` if needed:
```bash
sudo raspi-config
```

### 3. Expand Filesystem
(Optional but recommended):
```bash
sudo raspi-config  # Choose: Advanced Options → Expand Filesystem
```

---

## 🖥️ Lightweight GUI Setup (No Full Desktop Required)

Install a minimal GUI stack with X11 and a lightweight window manager:

```bash
sudo apt update && sudo apt install -y \
  xserver-xorg x11-xserver-utils xinit openbox \
  lightdm tk python3-tk mpv jq git curl ffmpeg
```

Enable autologin to desktop environment:
```bash
sudo raspi-config
# System Options → Boot / Auto Login → Desktop Autologin (B4)
```

Set Openbox as the window manager:
```bash
echo "openbox-session" > ~/.xsession
```

Autostart layout chooser:
```bash
mkdir -p ~/.config/openbox
nano ~/.config/openbox/autostart
```
Add this line:
```bash
python3 /home/viewport/unifi-viewport/layout_chooser.py &
```

---

## 🚀 Project Setup

### 1. Clone the repository:
```bash
sudo apt install git -y
cd ~
git clone https://github.com/jsetsuda/unifi-viewport.git
cd unifi-viewport
```

### 2. Run install script:
```bash
chmod +x install.sh
./install.sh
```

---

## 🔄 Reboot
```bash
sudo reboot
```

The system will boot into the layout chooser GUI. After 10 seconds, it will default to the last saved layout if no interaction occurs.

---

## 🧪 Development and Testing
This system includes:
- `layout_chooser.py`: UI to select layout and assign cameras
- `get_streams.py`: Fetches camera info from UniFi Protect
- `monitor_streams.py`: Monitors stream health and restarts crashed streams
- `overlay_box.py`: Adds on-screen overlay indicators
- `viewport.sh`: Starts and tiles all streams

---

## 🔐 GitHub Authentication
GitHub requires a personal access token (PAT) instead of a password. [Generate a token here](https://github.com/settings/tokens) and use it in place of your password when pushing code.

---

## 📂 Files Used
- `camera_urls.json`: Auto-generated camera list
- `viewport_config.json`: Layout config created by GUI
- `camera_urls.txt`: (Optional) fallback text file for URLs
