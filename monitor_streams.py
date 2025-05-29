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

def calculate_geometry(tile, screen_width, screen_height, rows, cols):
    tile_width = screen_width // cols
    tile_height = screen_height // rows
    x = tile["col"] * tile_width
    y = tile["row"] * tile_height
    return x, y, tile_width, tile_height

def parse_fps_string(fps_str):
    try:
        num, denom = fps_str.split('/')
        return round(float(num) / float(denom))
    except Exception:
        return None

def restart_stream(tile, restart_attempts, screen_width, screen_height, rows, cols):
    title = f"tile_{tile['row']}_{tile['col']}"
    if restart_attempts.get(title, 0) >= MAX_RESTART_ATTEMPTS:
        logging.warning(f"Max restart attempts reached for {title}. Skipping restart.")
        return

    logging.info(f"Restarting stream: {tile['name']} at position ({tile['row']}, {tile['col']})")
    try:
        x, y, width, height = calculate_geometry(tile, screen_width, screen_height, rows, cols)
        cmd = [
            "mpv",
            "--no-border",
            f"--geometry={width}x{height}+{x}+{y}",
            "--profile=low-latency",
            "--rtsp-transport=tcp",
            "--loop=inf",
            "--no-resume-playback",
            f"--title={title}",
            "--no-audio",
            "--video-sync=display-resample"
        ]

        # Add FPS if available
        if "fps" in tile and tile["fps"]:
            cmd.append(f"--fps={tile['fps']}")

        cmd.append(tile['url'])
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
    if not tiles:
        logging.error("No tiles found in configuration.")
        return

    # Detect screen resolution
    try:
        screen_info = subprocess.check_output("xdpyinfo | awk '/dimensions:/ {print $2}'", shell=True).decode().strip()
        screen_width, screen_height = map(int, screen_info.split('x'))
    except Exception as e:
        logging.error(f"Unable to determine screen resolution: {e}")
        screen_width, screen_height = 1920, 1080  # fallback

    restart_attempts = {}

    while True:
        for tile in tiles:
            title = f"tile_{tile['row']}_{tile['col']}"
            if not is_process_running(title):
                restart_stream(tile, restart_attempts, screen_width, screen_height, rows, cols)
            else:
                restart_attempts[title] = 0  # Reset counter if running
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
