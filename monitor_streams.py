import time
import subprocess
import json
import os
import psutil

CONFIG_FILE = "viewport_config.json"
LOG_FILE = "viewport.log"
MPV_BIN = "/usr/bin/mpv"
CHECK_INTERVAL = 30  # seconds
WIN_W = None
WIN_H = None

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[MONITOR] {msg}\n")

def get_screen_resolution():
    output = subprocess.check_output(["xdpyinfo"]).decode()
    for line in output.splitlines():
        if "dimensions:" in line:
            dims = line.split()[1]
            width, height = map(int, dims.split("x"))
            return width, height
    return 1920, 1080  # fallback

def is_process_running(title):
    for proc in psutil.process_iter(attrs=["cmdline"]):
        cmdline = proc.info.get("cmdline")
        if cmdline and any(title in arg for arg in cmdline):
            return True
    return False

def launch_stream(row, col, name, url):
    global WIN_W, WIN_H

    width, height = get_screen_resolution()
    grid_rows, grid_cols = get_grid_dimensions()
    WIN_W = width // grid_cols
    WIN_H = height // grid_rows

    x = col * WIN_W
    y = row * WIN_H
    title = f"tile_{row}_{col}"
    url = url.replace("rtsps://", "rtsp://")

    log(f"Restarting stream: {name} ({url}) at {x},{y} as {title}")
    cmd = [
        MPV_BIN,
        "--no-border",
        f"--geometry={WIN_W}x{WIN_H}+{x}+{y}",
        "--profile=low-latency",
        "--untimed",
        "--rtsp-transport=tcp",
        "--loop=inf",
        "--no-resume-playback",
        "--no-cache",
        "--demuxer-readahead-secs=1",
        "--fps=15",
        "--force-seekable=yes",
        "--vo=sdl",
        f"--title={title}",
        "--no-audio",
        url
    ]
    subprocess.Popen(cmd, stdout=open(LOG_FILE, "a"), stderr=subprocess.STDOUT)

def get_grid_dimensions():
    with open(CONFIG_FILE) as f:
        config = json.load(f)
        return config["grid"]

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def main():
    log("Stream monitor started.")
    while True:
        try:
            config = load_config()
            for tile in config["tiles"]:
                row = tile["row"]
                col = tile["col"]
                name = tile["name"]
                url = tile["url"]
                title = f"tile_{row}_{col}"

                if not url or url == "null":
                    continue

                if not is_process_running(title):
                    launch_stream(row, col, name, url)

        except Exception as e:
            log(f"Exception occurred: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
