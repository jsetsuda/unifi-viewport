# UniFi RTSP Viewport for Raspberry Pi

A lightweight Raspberry Pi–based viewport for displaying UniFi Protect RTSP/S streams in a tiled layout, with automatic resolution detection, health monitoring, and HDMI-CEC support.

---

## 🧰 Initial Raspberry Pi Setup

**Recommended OS:** Raspberry Pi OS (Full, 64-bit, with Desktop)
The full image ships with LightDM and the X11 stack already wired up, which avoids hand-configuration of the GUI components the layout chooser depends on.

> Raspberry Pi OS **Lite** can also work for advanced setups, but you will need to install and configure LightDM, X11, and a desktop manually. Most user-reported issues come from the Lite path.

### 1. Flash Raspberry Pi OS

Use the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to install **Raspberry Pi OS (64-bit, with Desktop)**.

> **Tip:** In the Imager's advanced options (gear/⚙ icon), set the default username to `viewport`. The installer and systemd service are written around that account, so SSH'ing in as `viewport` and running the install as that user is the smoothest path.

### 2. Log in via SSH or directly

Configure hostname, timezone, Wi-Fi, etc. via `raspi-config`:

```bash
sudo raspi-config
```

### 3. Expand Filesystem (Optional)

```bash
sudo raspi-config   # Advanced Options → Expand Filesystem
```

---

## Quickstart

1. **Update your system**

   ```bash
   sudo apt update && sudo apt upgrade -y && sudo apt install -y git
   ```
2. **Clone the repository**

   ```bash
   git clone https://github.com/jsetsuda/unifi-viewport.git ~/unifi-viewport
   cd ~/unifi-viewport
   ```
3. **Install with the unified installer**

   ```bash
   chmod +x install.sh
   sudo ./install.sh --all
   ```
4. **Reboot or start the service**

   ```bash
   sudo systemctl start unifi-viewport.service
   ```

> **Note:** If you installed a lightweight OS without a GUI, after install run `sudo raspi-config`, set **Boot Options → Desktop / CLI**. Then **Boot Options → Desktop Autologin → Yes for CLI and GUI**.

---

## Installation Flags

Run `install.sh` with one or more of these flags:

* `--pip`

  * Creates a Python 3 virtual environment in `./venv/`.
  * Installs Python dependencies (`python-dotenv`, `requests`, `psutil`).
  * Prompts for `UFP_HOST` and `UFP_API_KEY` and writes `.env`.
  * Adds `.env` to `.gitignore` and marks entry-point scripts executable.

* `--gui`

  * Installs LightDM, Openbox, X11, and display utilities (`x11-xserver-utils`, `xdotool`, `unclutter`).
  * Creates a `viewport` user (if missing) and configures autologin on display `:0`.
  * Sets up Openbox `autostart` to launch the layout chooser at login.

* `--cec`

  * Installs and configures HDMI-CEC keepalive via `cec-utils`.
  * Ensures the TV remains powered on and responsive to CEC commands.

* `--all`

  * Shorthand for running `--pip`, `--gui`, and `--cec` together.

Example:

```bash
sudo ./install.sh --pip --gui
```

Installs Python deps and GUI without CEC.

---

## 🎛 Configuring UniFi Protect

This branch (`v2-api`) uses the **official UniFi Protect Integration API**, not the legacy reverse-engineered endpoints. Authentication is via an API key in the `X-API-KEY` header — no more storing a username/password on the Pi.

### 1. Generate an API key

In the UniFi Protect web UI:
- **Settings → Control Plane → Integrations → Create API Key**
- (Older firmware: **Settings → Admins & Users → API Keys**)

Copy the key — it's only displayed once. Paste it into `.env` as `UFP_API_KEY` (the installer will prompt for it, or you can copy `.env.example` and fill it in by hand).

### 2. Pick a video codec on each camera

The kiosk plays streams with `mpv` and the Raspberry Pi's hardware decoder:
- Set **Recording Settings → Encoding = Standard** (H.264) per camera.
- Avoid **HEVC (H.265)** unless your Pi can decode it.

### 3. Enable RTSPS streams

You have two options:

- **Manual** (matches v1 behavior): in Protect → Camera → Settings → Advanced, toggle the RTSP/RTSPS qualities you want streamed. Run `python3 get_streams.py` to pull the URLs.
- **Automatic via API**: run `python3 get_streams.py --enable` once. The script will POST to `/cameras/{id}/rtsps-stream` for each camera missing a stream and enable high/medium/low qualities. Reversible from the Protect UI.

By default (no flag), `get_streams.py` only reports cameras that *already* have RTSPS on, so subsequent kiosk restarts never silently change NVR config.

---

## 🚀 First Run

If autolaunch doesn’t occur (or you’re in virtualenv mode), manually fetch cameras and choose a layout:

```bash
source venv/bin/activate   # skip if system-wide install
./layout_chooser.py
```

After saving a layout, reboots will auto-launch the last configuration after a brief timeout.

> **Note:** The first-run layout chooser is a GUI and requires a connected **mouse** to operate (touch input also works). The chooser only blocks first-time setup — subsequent reboots will skip past it automatically once a layout has been saved.

---

## Deployment Notes

These are tips collected from running the project on real hardware.

### Skip the layout chooser delay on reboot

After your first successful run, the layout chooser waits 20 seconds before auto-loading the previous layout. To shorten or skip that wait, set `VIEWPORT_AUTO_TIMEOUT` (milliseconds) in the systemd unit:

```bash
sudo systemctl edit unifi-viewport.service
```

Then add:

```ini
[Service]
Environment=VIEWPORT_AUTO_TIMEOUT=1
```

A value of `1` ms effectively bypasses the chooser entirely on every reboot.

### `policykit-1` package errors during install

Some Raspberry Pi OS variants no longer ship the `policykit-1` meta-package, which can cause the `--gui` install step to fail. `install.sh` now tries to fall back to `pkexec` + `polkitd` (or `policykit-1-gnome`) automatically. If you still hit issues, see the workaround discussion at [PJ-Singh-001/Cubic#389](https://github.com/PJ-Singh-001/Cubic/issues/389).

### Network-wait host

`viewport.sh` waits for the NVR to be reachable before launching streams. The host is parsed from `UFP_HOST` in `.env` — if that file is missing or malformed, the network wait is skipped with a warning. (Earlier versions of this script hard-coded an IP, which broke deployments on different networks.)

---

## Project Components

| File                    | Description                                                                                 |
| ----------------------- | ------------------------------------------------------------------------------------------- |
| `layout_chooser.py`     | GUI for selecting grid size, assigning cameras to tiles, and saving `viewport_config.json`. |
| `get_streams.py`        | Fetches UniFi Protect RTSP URLs and writes to `camera_urls.json`.                           |
| `viewport.sh`           | Detects display resolution, launches MPV tiles, and starts the health monitor.              |
| `monitor_streams.py`    | Periodically checks each stream’s health and restarts stalled streams.                      |
| `install.sh`            | Unified installer for pip, GUI, and CEC components with command-line flags.                 |

---

## How It Works

```text
┌───────────────┐   ┌────────────────┐   ┌──────────────────┐
│ UniFi Protect │──▶│ get_streams.py│──▶│ camera_urls.json│
└───────────────┘   └────────────────┘   └──────────────────┘
                             │
                             ▼
                       ┌───────────────┐   ┌────────────────┐
                       │ viewport.sh   │──▶│  mpv windows │
                       └───────────────┘   └────────────────┘
                             │
                             ▼
                   ┌────────────────────┐
                   │ monitor_streams.py │
                   └────────────────────┘
```

---

## Troubleshooting

* **Service logs**:

  ```bash
  sudo journalctl -u unifi-viewport.service -f
  ```
* **Application logs**:
  Check `viewport.log` in the repository root.
* **Resolution detection**:
  Ensure `xrandr` (X11) or `tvservice` (RPi) is installed.
* **CEC issues**:
  Verify `cec-utils` and that your TV supports HDMI-CEC.
* **API errors**:
  Confirm `.env` credentials and network connectivity to your UniFi Protect controller.

---

## License

This project is licensed under the MIT License – see [LICENSE](LICENSE) for details.
