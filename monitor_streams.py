#!/usr/bin/env python3
import os
import time
import json
import subprocess
import logging
import psutil
import re

# Configuration
CONFIG_FILE = "viewport_config.json"
LOG_FILE = "monitor.log"
CHECK_INTERVAL = 30  # seconds
RESTART_DELAY = 10   # seconds
MAX_RESTART_ATTEMPTS = 3

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def load_config():
    if not os.path.isfile(CONFIG_FILE):
        logging.error(f"Configuration file {CONFIG_FILE} not found.")
        return None
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {CONFIG_FILE}: {e}")
        return None

def is_process_running(title):
    for proc in psutil.process_iter(['cmdline']):
        try:
            if any(title in arg for arg in proc.info['cmdline']):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False

def calculate_geometry(tile, screen_width, screen_height, rows, cols):
    tile_width = screen_width // cols
    tile_height = screen_height // rows
    x = tile["col"] * tile_width
    y = tile["row"] * tile_height
    return x, y, tile_width, tile_height

def extract_fps_from_name(name):
    match = re.search(r"@ (\d+)fps", name)
    if match:
        return match.group(1)
    return None

def restart_stream(tile, restart_attempts, screen_width, screen_height, rows, cols):
    title = f"tile_{tile['row']}_{tile['col']}"
    if restart_attempts.get(title, 0) >= MAX_RESTART_ATTEMPTS:
        logging.warning(f"Max restart attempts reached for {title}. Skipping.")
        return

    logging.info(f"Restarting stream: {tile['name']} at position ({tile['row']}, {tile['col']})")
    try:
        x, y, width, height = calculate_geometry(tile, screen_width, screen_height, rows, cols)
        url = tile['url'].replace("rtsps://", "rtsp://")

        cmd = [
            "mpv",
            "--no-border",
            f"--geometry={width}x{height}+{x}+{y}",
            "--profile=low-latency",
            "--rtsp-transport=tcp",
            "--loop=inf",
            "--no-resume-playback",
            "--no-cache",
            "--demuxer-readahead-secs=1",
            "--force-seekable=yes",
            "--video-sync=display-resample",
            f"--title={title}",
            "--no-audio"
        ]

        fps = extract_fps_from_name(tile['name'])
        if fps:
            cmd.append(f"--fps={fps}")

        cmd.append(url)

        subprocess.Popen(cmd)
        restart_attempts[title] = restart_attempts.get(title, 0) + 1
        time.sleep(RESTART_DELAY)
    except Exception as e:
        logging.error(f"Failed to restart stream {title}: {e}")

def main():
    config = load_config()
    if not config:
        return

    tiles = config.get("tiles", [])
    rows, cols = config.get("grid", [2, 2])

    try:
        dims = subprocess.check_output("xdpyinfo | awk '/dimensions:/ {print $2}'", shell=True).decode().strip()
        screen_width, screen_height = map(int, dims.split('x'))
    except Exception as e:
        logging.error(f"Unable to detect screen resolution: {e}")
        screen_width, screen_height = 1920, 1080

    restart_attempts = {}

    while True:
        for tile in tiles:
            title = f"tile_{tile['row']}_{tile['col']}"
            if not is_process_running(title):
                restart_stream(tile, restart_attempts, screen_width, screen_height, rows, cols)
            else:
                restart_attempts[title] = 0  # Reset on success
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
