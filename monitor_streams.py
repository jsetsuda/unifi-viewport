#!/usr/bin/env python3
"""
monitor_streams.py
Description: Monitors and restarts stale or missing mpv RTSP stream processes based on viewport_config.json.
Supports tile multipliers (w, h) and hardware decoding on Raspberry Pi 5.
"""
import time
import subprocess
import json
import psutil
import re

# --- Section: Configuration Constants ---
CONFIG_FILE = "viewport_config.json"
LOG_FILE = "viewport.log"
MPV_BIN = "/usr/bin/mpv"
CHECK_INTERVAL = 5          # seconds between health checks
RESTART_COOLDOWN = 5        # seconds between restarts per tile

# Track last restart timestamps per tile
title_last_restart = {}

# --- Section: Logging Utility ---
def log(msg):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, "a") as f:
        f.write(f"[MONITOR {timestamp}] {msg}\n")

# --- Section: Screen and Grid Utilities ---
def get_screen_resolution():
    try:
        output = subprocess.check_output(["xdpyinfo"]).decode()
        for line in output.splitlines():
            if "dimensions:" in line:
                dims = line.split()[1]
                width, height = map(int, dims.split("x"))
                return width, height
    except Exception as e:
        log(f"xdpyinfo error: {e}")
    return 1920, 1080  # fallback


def get_grid_dimensions():
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    return config.get("grid", [1, 1])

# --- Section: Process Health Check ---
def is_process_running(title):
    for proc in psutil.process_iter(attrs=["cmdline"]):
        try:
            cmdline = proc.info.get("cmdline")
            if cmdline and any(title in arg for arg in cmdline):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

# --- Section: Stream Launcher ---
def launch_stream(row, col, name, url, tile):
    width, height = get_screen_resolution()
    grid_rows, grid_cols = get_grid_dimensions()

    w_mul = tile.get("w", 1)
    h_mul = tile.get("h", 1)
    win_w = width // grid_cols
    win_h = height // grid_rows

    TILE_W = win_w * w_mul
    TILE_H = win_h * h_mul
    x = col * win_w
    y = row * win_h
    title = f"tile_{row}_{col}"

    # Hardware decode flag for Pi 5\ n    try:
        model = open("/proc/device-tree/model").read()
        hwdec = "--hwdec=auto" if "Raspberry Pi 5" in model else ""
    except Exception:
        hwdec = ""

    # Convert RTSPS to RTSP
    url = re.sub(r"rtsps://([^:/]+):7441", r"rtsp://\1:7447", url)

    log(f"Restarting stream '{name}' as {title} at {TILE_W}x{TILE_H}+{x}+{y}")
    cmd = [
        MPV_BIN,
        "--no-border",
        f"--geometry={TILE_W}x{TILE_H}+{x}+{y}",
        "--profile=low-latency",
        "--untimed",
        "--no-correct-pts",
        "--video-sync=desync",
        "--framedrop=vo",
        "--rtsp-transport=tcp",
        "--loop=inf",
        "--no-resume-playback",
        "--no-cache",
        "--demuxer-readahead-secs=1",
        "--fps=24",
        "--force-seekable=yes",
        "--vo=gpu",
        hwdec,
        f"--title={title}",
        "--no-audio",
        "--keep-open=yes",
        url
    ]
    subprocess.Popen(cmd, stdout=open(LOG_FILE, "a"), stderr=subprocess.STDOUT)
    title_last_restart[title] = time.time()

# --- Section: Main Monitoring Loop ---
def main():
    log("Stream monitor started.")
    while True:
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)

            for tile in config.get("tiles", []):
                row = tile.get("row")
                col = tile.get("col")
                name = tile.get("name")
                url = tile.get("url")
                title = f"tile_{row}_{col}"

                if not url or url == "null":
                    continue

                now = time.time()
                cooldown = now - title_last_restart.get(title, 0)

                if not is_process_running(title) and cooldown >= RESTART_COOLDOWN:
                    launch_stream(row, col, name, url, tile)
        except Exception as e:
            log(f"Exception occurred: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
