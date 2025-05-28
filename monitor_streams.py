# monitor_streams.py
# Monitors stream health and restarts broken mpv windows with overlay integration, with cooldown and improved ffprobe

import subprocess
import time
import json
import os
import signal
from pathlib import Path

CONFIG_FILE = Path.home() / "unifi-viewport" / "viewport_config.json"
LOG_FILE = Path.home() / "unifi-viewport" / "viewport.log"
MPV_TITLE_PREFIX = "tile_"
CHECK_INTERVAL = 30  # seconds
COOLDOWN_TIME = 120  # seconds

# Try ffprobe or fallback to curl
FFPROBE = "/usr/bin/ffprobe"
CURL = "/usr/bin/curl"

cooldowns = {}  # key: window_title, value: last restart timestamp

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[MONITOR] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")

def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception as e:
        log(f"Failed to read config: {e}")
        return None

def check_stream(url):
    try:
        if Path(FFPROBE).exists():
            result = subprocess.run([
                FFPROBE, "-v", "quiet", "-timeout", "5000000", "-show_streams", url
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return result.returncode == 0
        elif Path(CURL).exists():
            result = subprocess.run([CURL, "-m", "5", url],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return result.returncode == 0
        else:
            log("No stream-checking tool found.")
            return False
    except Exception as e:
        log(f"Check failed: {e}")
        return False

def restart_tile(row, col, name, url, grid):
    window_title = f"{MPV_TITLE_PREFIX}{row}_{col}"
    now = time.time()
    if window_title in cooldowns and now - cooldowns[window_title] < COOLDOWN_TIME:
        log(f"Skipping restart of {window_title} (cooldown active)")
        return

    cooldowns[window_title] = now
    log(f"Restarting {name} at tile {row},{col}")
    subprocess.run(["pkill", "-f", window_title])
    subprocess.run(["pkill", "-f", f"overlay_{window_title}"])
    time.sleep(1)

    WIDTH = int(os.environ.get("WIDTH", 3840))
    HEIGHT = int(os.environ.get("HEIGHT", 2160))
    win_w = WIDTH // grid[1]
    win_h = HEIGHT // grid[0]
    x = col * win_w
    y = row * win_h

    subprocess.Popen([
        "mpv", "--no-border", "--no-audio", "--no-terminal",
        f"--geometry={win_w}x{win_h}+{x}+{y}",
        "--profile=low-latency", "--untimed", "--rtsp-transport=tcp",
        f"--title={window_title}",
        url
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    subprocess.Popen([
        "python3", "overlay_box.py", window_title, "green"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    while True:
        config = load_config()
        if not config:
            time.sleep(CHECK_INTERVAL)
            continue

        grid = config.get("grid", [2, 2])

        for tile in config.get("tiles", []):
            row = tile["row"]
            col = tile["col"]
            name = tile["name"]
            url = tile["url"]

            window_title = f"{MPV_TITLE_PREFIX}{row}_{col}"

            ok = check_stream(url)
            if ok:
                subprocess.run(["pkill", "-f", f"overlay_{window_title}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.Popen([
                    "python3", "overlay_box.py", window_title, "green"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(["pkill", "-f", f"overlay_{window_title}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.Popen([
                    "python3", "overlay_box.py", window_title, "red"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                restart_tile(row, col, name, url, grid)

        time.sleep(CHECK_INTERVAL)
