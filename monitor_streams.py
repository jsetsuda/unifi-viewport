import time
import subprocess
import json
import os
import psutil
import re

CONFIG_FILE = "viewport_config.json"
LOG_FILE = "viewport.log"
MPV_BIN = "/usr/bin/mpv"
CHECK_INTERVAL = 5  # seconds to check all tiles
RESTART_COOLDOWN = 15  # seconds between restarts per tile

# Track last restart times per tile
last_restart = {}

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[MONITOR] {msg}\n")

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
        return config["grid"]

def is_process_running(title):
    for proc in psutil.process_iter(attrs=["cmdline"]):
        try:
            cmdline = proc.info.get("cmdline")
            if cmdline and any(title in arg for arg in cmdline):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def launch_stream(row, col, name, url):
    width, height = get_screen_resolution()
    grid_rows, grid_cols = get_grid_dimensions()
    win_w = width // grid_cols
    win_h = height // grid_rows

    x = col * win_w
    y = row * win_h
    title = f"tile_{row}_{col}"

    # Convert RTSPS to RTSP and port
    url = re.sub(r"rtsps://([^:/]+):7441", r"rtsp://\1:7447", url)

    log(f"Restarting stream: {name} ({url}) at {x},{y} as {title}")
    cmd = [
    MPV_BIN,
        "--no-border",
        f"--geometry={win_w}x{win_h}+{x}+{y}",
        "--profile=low-latency",
        "--untimed",
        "--rtsp-transport=tcp",
        "--loop=inf",
        "--no-resume-playback",
        "--no-cache",
        "--demuxer-readahead-secs=1",
        "--fps=24",
        "--force-seekable=yes",
        "--vo=gpu",
        f"--title={title}",
        "--no-audio",
        url
    ]
    subprocess.Popen(cmd, stdout=open(LOG_FILE, "a"), stderr=subprocess.STDOUT)
    last_restart[title] = time.time()

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
                cooldown_passed = (now - last_restart.get(title, 0)) >= RESTART_COOLDOWN

                if not is_process_running(title) and cooldown_passed:
                    launch_stream(row, col, name, url)

        except Exception as e:
            log(f"Exception occurred: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
