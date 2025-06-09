# UniFi RTSP Viewport for Raspberry Pi

A lightweight RTSP viewer system for UniFi Protect cameras, designed to emulate the UniFi Protect Viewport experience on a Raspberry Pi with minimal overhead.

---

## 🧰 Initial Raspberry Pi Setup

**Recommended OS:** Raspberry Pi OS Lite (64‑bit)
Ideal for headless or kiosk‑style deployments.

### 1. Flash Raspberry Pi OS Lite

Use the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to install **Raspberry Pi OS Lite (64‑bit)**.

### 2. Log in via SSH or directly

Set hostname, timezone, Wi‑Fi, etc. via `raspi-config`:

```bash
sudo raspi-config
```

### 3. Expand Filesystem (Optional)

```bash
sudo raspi-config   # Advanced Options → Expand Filesystem
```

### 4. Clone the Repository

```bash
sudo apt install git -y
cd ~
git clone https://github.com/jsetsuda/unifi-viewport.git
cd unifi-viewport
```

---

## 📦 Installation Options

Choose the one that best fits your OS and preferences:

### 🅰️ Option 1: Full GUI Setup on Raspberry Pi OS Lite

Installs a minimal GUI (LightDM + Openbox), dependencies, a dedicated `viewport` user with autologin, and configures everything to launch on boot.

```bash
chmod +x installgui.sh
./installgui.sh
```

**Best for:** Clean Raspberry Pi OS Lite (64‑bit) with no existing desktop.

---

### 🅱️ Option 2: System‑Wide Install on Desktop/GUI OS

Installs all required system packages and Python libraries globally.

```bash
chmod +x install.sh
./install.sh
```

**Best for:** Raspberry Pi OS with Desktop already installed, or any Debian‑based GUI system.

---

### 🅾️ Option 3: Developer Mode with Virtualenv

Creates an isolated Python virtual environment and installs only the Python libraries you need.

```bash
chmod +x installpip.sh
./installpip.sh
source venv/bin/activate
```

**Best for:** Developers, CI/testing, or when you don’t want to modify system Python.

---

## 🚀 First Run

If autolaunch doesn’t occur (or you’re using virtualenv), manually fetch your cameras and choose a layout:

```bash
source venv/bin/activate   # Skip if you did a system‑wide install
./layout_chooser.py
```

After you save a grid once, subsequent reboots will auto‑launch the last layout after a 30 s timeout.

---

## 📌 Project Components

| File                    | Description                                                                        |
| ----------------------- | ---------------------------------------------------------------------------------- |
| `layout_chooser.py`     | GUI to select grid size, assign cameras to tiles, and save `viewport_config.json`. |
| `get_streams.py`        | Fetches UniFi Protect RTSP URLs and writes `camera_urls.json`.                     |
| `viewport.sh`           | Shell script to launch all tiles in MPV and start health monitor.                  |
| `monitor_streams.py`    | Monitors each tile’s MPV process and restarts stale streams.                       |
| `overlay_box.py`        | (Optional) Draws a red overlay on any tile that is down.                           |
| `kill_stale_streams.py` | (Optional) Helper to terminate orphaned MPV processes.                             |

---

## 🎛 Configuring UniFi Protect for RTSP

1. In UniFi Protect → Camera → Settings → Advanced
2. Enable **H.264** RTSP (“High”, “Medium”, or “Low”).
3. Avoid HEVC (H.265) unless your Pi can handle it.
4. Recording Settings → **Encoding = Standard**.

To refresh your camera list after adding or removing cameras:

```bash
source venv/bin/activate   # or skip if system‑wide
python3 get_streams.py
```

---

## 🧪 Development Notes

* All Python dependencies are in `requirements.txt`.
* `installpip.sh` creates a `venv/` and installs `python-dotenv`, `requests`, `psutil`.
* Ensure you have `python3-tk`, `python3-psutil`, `xdotool`, `xrandr`, `xdpyinfo`, `mpv`, and `jq` installed for full functionality.

---

## 🔐 GitHub Contributors

When pushing code you’ll need a Personal Access Token (PAT) instead of your password. Generate one [here](https://github.com/settings/tokens) and use it in place of your GitHub password.
