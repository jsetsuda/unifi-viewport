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

### 🅰️ Step 1 - Option 1: System-Wide Install (Recommended for Raspberry Pi)

```bash
chmod +x install.sh
./install.sh
```

This installs required system packages and Python dependencies globally. It will:

* Prompt for UniFi Protect credentials and create a `.env` file
* Add `.env` to `.gitignore`
* Install tools like `mpv`, `jq`, `ffmpeg`, `python3-tk`
* Run without needing virtualenvs

**Best for:** users who want simplicity and are running on Raspberry Pi OS.

---

### 🅱️ Step 1 - Option 2: Isolated Virtualenv Install (Recommended for Developers)

```bash
chmod +x pipinstall.sh
./pipinstall.sh
source venv/bin/activate
```

This method avoids installing Python packages globally by using a virtual environment. It will:

* Create `venv/` for isolated dependencies
* Prompt for `.env` credentials
* Use `requirements.txt` to install Python packages

**Best for:** developers, CI environments, or when avoiding global Python changes.

---

### 🅾️ Step 2: GUI Autostart Setup (Optional if full desktop or GUI already installed and active)

```bash
chmod +x installgui.sh
./installgui.sh
```

This enables auto-login into the GUI and launches the layout chooser automatically.

Then run:

```bash
sudo raspi-config
# System Options → Boot / Auto Login → Desktop Autologin
```

**Best for:** users setting up a dedicated screen or unattended viewer station.

---

## 🚀 First Run

Once installed, launch the layout selector to configure your grid (must be done on pi, not SSH):

```bash
./layout_chooser.py
```

After 10 seconds of inactivity, it will auto-launch the last saved layout.

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
