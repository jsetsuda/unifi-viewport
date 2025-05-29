#!/usr/bin/env python3
import os
import time
import json
import subprocess
import logging
import psutil
import re

CONFIG_FILE = "viewport_config.json"
LOG_FILE = "monitor.log"
VIEWPORT_LOG = "viewport.log"
CHECK_INTERVAL = 10
RESTART_DELAY = 30
MAX_RESTART_ATTEMPTS = 3
SCREEN_WIDTH = 3840
SCREEN_HEIGHT = 2160

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
        logging.error(f"Error decoding JSON: {e}")
        return None

def is_process_running(title):
    for proc in psutil.process_iter(['cmdline']):
        try:
            if title in proc.info['cmdline']:
                return True
        except:
            continue
    return False

def calculate_geometry(tile, rows, cols):
    tile_width = SCREEN_WIDTH // cols
    tile_height = SCREEN_HEIGHT // rows
    x = tile["col"] * tile_width
    y = tile["row"] * tile_height
    return x, y, tile_width, tile_height

def parse_viewport_log():
    if not os.path.exists(VIEWPORT_LOG):
        return {}

    frozen_tiles = {}
    progress_pattern = re.compile(r"V: (\d+:\d+:\d+|\d+:\d+) /")

    with open(VIEWPORT_LOG, "r") as f:
        lines = f.readlines()

    tile_playback = {}
    for line in lines[::-1]:  # reverse search for latest entries
        match = progress_pattern.search(line)
        if match:
            for tile in ["tile_0_0", "tile_0_1", "tile_1_0", "tile_1_1"]:
                if tile in line:
                    timestamp = match.group(1)
                    if tile not in tile_playback:
                        tile_playback[tile] = timestamp
                    elif tile_playback[tile] == timestamp:
                        frozen_tiles[tile] = True
                    else:
                        frozen_tiles[tile] = False
    return frozen_tiles

def restart_stream(tile, restart_attempts, rows, cols):
    title = f"tile_{tile['row']}_{tile['col']}"
    if restart_attempts.get(title, 0) >= MAX_RESTART_ATTEMPTS:
        logging.warning(f"Max restart attempts for {title}")
        return

    x, y, w, h = calculate_geometry(tile, rows, cols)
    logging.info(f"Restarting stream: {tile['name']} at position ({tile['row']}, {tile['col']})")

    try:
        subprocess.Popen([
            "mpv",
            "--no-border",
            f"--geometry={w}x{h}+{x}+{y}",
            "--profile=low-latency",
            "--untimed",
            "--rtsp-transport=tcp",
            "--loop=inf",
            "--no-resume-playback",
            f"--title=tile_{tile['row']}_{tile['col']}",
            "--no-audio",
            tile['url']
        ])
        restart_attempts[title] = restart_attempts.get(title, 0) + 1
        time.sleep(RESTART_DELAY)
    except Exception as e:
        logging.error(f"Failed to restart {title}: {e}")

def main():
    config = load_config()
    if not config:
        return

    tiles = config.get("tiles", [])
    rows, cols = config.get("grid", [2, 2])
    restart_attempts = {}
    last_seen_timestamps = {}

    while True:
        frozen_tiles = parse_viewport_log()

        for tile in tiles:
            title = f"tile_{tile['row']}_{tile['col']}"
            running = is_process_running(title)
            frozen = frozen_tiles.get(title, False)

            if not running or frozen:
                logging.warning(f"Stream {title} needs restart (running={running}, healthy={not frozen})")
                restart_stream(tile, restart_attempts, rows, cols)
            else:
                restart_attempts[title] = 0  # Reset if healthy

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
