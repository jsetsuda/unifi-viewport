# UniFi RTSP Viewport for Raspberry Pi

This project creates a lightweight, GUI-based RTSP viewer on a Raspberry Pi to emulate the functionality of the UniFi Protect Viewport. It supports:
- Grid-based RTSP camera layouts (1x1 to 4x4)
- Auto-refresh and failure detection with stream restart
- Overlay status indicators (green/yellow/red)
- Auto-start on boot (GUI mode)
- Stream preview and easy drag-and-drop layout configuration

---

## 📦 Features

- 🔧 Layout chooser with auto-fallback to last config after 10 seconds
- 🎥 Hardware-accelerated `mpv` playback of RTSP streams
- 🔁 Automatic stream health monitoring and restart
- 🟥 Visual status overlays for each tile
- 💻 Works on Raspberry Pi 4 and 5 (64-bit Raspberry Pi OS)
- 🔐 Local-only; no cloud or internet required

---

## 💾 Installation

### Prerequisites

- Raspberry Pi 4 or 5
- Raspberry Pi OS 64-bit (Lite or Desktop)
- GUI required for windowed view

### Steps

1. Clone this repository:
   ```bash
   git clone https://github.com/jsetsuda/unifi-viewport.git ~/unifi-viewport
   cd ~/unifi-viewport
