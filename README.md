# UniFi RTSP Viewport

This project emulates the UniFi Protect Viewport device by displaying multiple RTSP streams in a tiled grid layout using a Raspberry Pi. It features automatic health monitoring, stream restart logic, a GUI layout selector, and overlay indicators.

## Features
- Multi-camera RTSP viewer using `mpv`
- Grid layout chooser with stream preview and JSON-based config
- Automatic stream health checking and restart
- Overlay box per stream with health indicator (green/red)
- Auto-fallback to last layout if idle for 10 seconds

---

## 🔧 Initial Raspberry Pi Setup

These instructions assume a **fresh install of Raspberry Pi OS Lite 64-bit** on a Raspberry Pi 5 or 4.

### 1. System Update & Install Dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3 python3-pip python3-tk mpv jq x11-utils xinit xserver-xorg x11-xserver-utils unclutter
```

You may optionally install a minimal GUI:
```bash
sudo apt install -y openbox
```

### 2. Clone the Project
```bash
cd ~
git clone https://github.com/jsetsuda/unifi-viewport.git
cd unifi-viewport
```

### 3. Run the Installer
```bash
chmod +x install.sh
./install.sh
```

---

## 🖥️ Usage

### GUI Layout Selector
To select camera layout and launch the viewer:
```bash
cd ~/unifi-viewport
./layout_chooser.py
```

- You can preview each stream before assigning
- After saving, it launches the full tiled viewer
- If idle for 10 seconds, it defaults to the last layout

### Auto-Start at Boot
To enable viewer launch at boot:
```bash
sudo raspi-config
```
- Enable GUI autologin under **System Options > Boot / Auto Login**

Edit the autostart script:
```bash
nano ~/.config/lxsession/LXDE-pi/autostart
```
Append this line:
```bash
@bash -c 'cd /home/viewport/unifi-viewport && ./layout_chooser.py'
```

---

## 🗂️ Files
- `camera_urls.json`: Live camera stream list (fetched via `get_streams.py`)
- `camera_urls.txt`: Used to manually specify cameras (optional)
- `viewport_config.json`: Grid layout and stream assignments
- `viewport.sh`: Launches the tiled grid
- `monitor_streams.py`: Automatically checks and restarts failed streams
- `overlay_box.py`: Displays colored box over each stream indicating status

---

## 📦 install.sh
Installs required packages, sets up permissions, and copies service files if needed.

---

## ✅ Status
Fully functional. Additional features like sound suppression, more control protocols, or GPU acceleration tuning are under exploration.

---

## License
MIT License
