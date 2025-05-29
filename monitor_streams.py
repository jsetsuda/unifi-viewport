#!/usr/bin/env python3
import os
import time
import json
import subprocess
import logging
import psutil

# Configuration
CONFIG_FILE = "viewport_config.json"
LOG_FILE = "monitor.log"
CHECK_INTERVAL = 10  # seconds
RESTART_DELAY = 30   # seconds
MAX_RESTART_ATTEMPTS = 3
SCREEN_WIDTH = 3840
SCREEN_HEIGHT = 2160
TILE_ROWS = 2
TILE_COLS = 2

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
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {CONFIG_FILE}: {e}")
        return None

def is_process_running(title):
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if title in proc.info['cmdline']:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False

def calculate_geometry(tile):
    tile_width = SCREEN_WIDTH // TILE_COLS
    tile_height = SCREEN_HEIGHT // TILE_ROWS
    x = tile["col"] * tile_width
    y = tile["row"] * tile_height
    return x, y, tile_width, tile_height

def restart_stream(tile, restart_attempts):
    title = f"tile_{tile['row']}_{tile['col']}"
    if restart_attempts.get(title, 0) >= MAX_RESTART_ATTEMPTS:
        logging.warning(f"Max restart attempts reached for {title}. Skipping restart.")
        return

    logging.info(f"Restarting stream: {tile['name']} at position ({tile['row']}, {tile['col']})")
    try:
        x, y, width, height = calculate_geometry(tile)
        url = tile['url'].replace("rtsps:", "rtsp:")

        subprocess.Popen([
            "mpv",
            "--no-border",
            f"--geometry={width}x{height}+{x}+{y}",
            "--profile=low-latency",
            "--untimed",
            "--rtsp-transport=tcp",
            "--loop=inf",
            "--no-resume-playback",
            "--no-cache",
            "--demuxer-readahead-secs=1",
            "--fps=15",
            "--force-seekable=yes",
            f"--title={title}",
            "--no-audio",
            url
        ])
        restart_attempts[title] = restart_attempts.get(title, 0) + 1
        time.sleep(RESTART_DELAY)
    except Exception as e:
        logging.error(f"Failed to restart stream {title}: {e}")

def main():
    config = load_config()
    if not config:
        return

    tiles = config.get("tiles", [])
    if not tiles:
        logging.error("No tiles found in configuration.")
        return

    restart_attempts = {}

    while True:
        for tile in tiles:
            title = f"tile_{tile['row']}_{tile['col']}"
            if not is_process_running(title):
                restart_stream(tile, restart_attempts)
            else:
                restart_attempts[title] = 0  # Reset counter if running
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
