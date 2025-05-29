# UniFi RTSP Viewport for Raspberry Pi

A lightweight RTSP viewer system for UniFi cameras, designed to emulate the UniFi Protect Viewport experience using a Raspberry Pi with minimal overhead.

---

## 🧰 Initial Raspberry Pi Setup

**Recommended OS:** Raspberry Pi OS Lite (64-bit)
Ideal for headless or kiosk-style deployments.

### 1. Flash Raspberry Pi OS Lite

Use the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to install **Raspberry Pi OS Lite (64-bit)**.

### 2. Log in via SSH or directly

Set hostname, timezone, WiFi, etc. via `raspi-config`:

```bash
sudo raspi-config
```

### 3. Expand Filesystem (Optional)

```bash
sudo raspi-config  # Choose: Advanced Options → Expand Filesystem
```

### 4. Clone the GitHub Repository

Ensure you have Git installed, then clone the project:

```bash
sudo apt install git -y
cd ~
git clone https://github.com/jsetsuda/unifi-viewport.git
cd unifi-viewport
```

---

## 📦 Installation Options

Choose one of the following installation paths based on your Raspberry Pi OS type and desired complexity.

---

### 🅰️ Option 1: Full Setup on Raspberry Pi OS Lite (Headless or Minimal GUI)

This installs everything needed for a lightweight GUI-based RTSP viewport on a clean Raspberry Pi OS Lite system.

```bash
chmod +x installgui.sh
./installgui.sh
```

This script will:
- Install a minimal GUI (Openbox + LightDM)
- Create a `viewport` user with autologin
- Set up the UniFi Viewport environment and dependencies
- Prompt for UniFi Protect credentials to create `.env`
- Configure automatic launch of the layout selector

💡 After setup, reboot the Pi and it will boot directly into the RTSP viewer GUI.

**Best for:** Clean Raspberry Pi Lite OS (64-bit) installs with no desktop environment.

---

### 🅱️ Option 2: Install on Desktop or GUI System (System-Wide)

If you already have a full Raspberry Pi OS with Desktop or another Linux GUI installed, use this method:

```bash
chmod +x install.sh
./install.sh
```

This script will:
- Install all system-wide packages (e.g. mpv, jq, python3-tk)
- Install Python dependencies globally using pip
- Prompt for UniFi Protect credentials to create `.env`
- Prepare scripts for launch

**Best for:** Users with Raspberry Pi OS (with Desktop) or a GUI-capable Linux system already configured.

---

### 🅾️ Option 3: Developer Mode with Virtualenv

Install using a virtual environment for isolated testing or CI workflows.

```bash
chmod +x installpip.sh
./installpip.sh
source venv/bin/activate
```

This method:
- Creates a `venv/` virtual environment
- Installs Python requirements from `requirements.txt`
- Prompts for UniFi Protect `.env` credentials
- Avoids modifying system Python or using `sudo pip`

**Best for:** Developers, advanced users, testing environments.


## 🚀 First Run

Once installed, if autolaunch does not occur, launch the layout selector to pull your camera streams and configure your grid:

```bash
./layout_chooser.py
```

On subsequent boots, after 10 seconds of inactivity, it will auto-launch the last saved layout.

---

## 📌 Project Components

* `layout_chooser.py`: GUI to choose grid layout and assign camera streams
* `get_streams.py`: Pulls available RTSP streams from UniFi Protect using `.env`
* `viewport.sh`: Launches all selected streams in tiled view
* `monitor_streams.py`: Monitors stream health and restarts failed tiles
* `overlay_box.py`: Draws red overlays on tiles that are down

---

## 📁 Key Files

| File                   | Description                         |
| ---------------------- | ----------------------------------- |
| `.env`                 | Stores UniFi Protect host/user/pass |
| `camera_urls.json`     | Auto-generated list of RTSP URLs    |
| `viewport_config.json` | Layout assignment (tile → camera)   |
| `camera_urls.txt`      | Optional fallback for raw RTSP URLs |

---

## 🎛 Configuring UniFi Protect for RTSP

To ensure compatibility and performance:

1. Go to UniFi Protect → Camera → Settings → Advanced
2. Enable a **H.264** RTSP stream ("High", "Medium", or "Low")
3. Avoid HEVC (H.265) unless you know your Pi can decode it
4. Under "Recording Settings", set **Encoding = Standard**

To refresh your camera list after changes:

```bash
source venv/bin/activate  # or skip if system-wide
python get_streams.py
```

---

## 🧪 Development Notes

For developers:

* All Python dependencies are listed in `requirements.txt`
* Use `pipinstall.sh` to avoid touching system Python
* Consider contributing improvements via pull requests

---

## 🔐 GitHub Authentication for Contributors

GitHub requires a personal access token (PAT) instead of a password when pushing code.
Generate one [here](https://github.com/settings/tokens) and use it instead of your GitHub password.
