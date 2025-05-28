#!/usr/bin/env python3
import os
import time
import json
import subprocess

CONFIG_FILE = "viewport_config.json"
CHECK_INTERVAL = 30  # seconds

def is_stream_alive(url):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-rtsp_transport", "tcp", "-i", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False

def restart_stream(title, url, x, y, width, height):
    subprocess.run(["pkill", "-f", f"--title={title}"])
    log_file = open("viewport.log", "a")
    print(f"[RESTART] Restarting {title}...", file=log_file)
    subprocess.Popen([
        "mpv",
        "--no-border",
        f"--geometry={width}x{height}+{x}+{y}",
        "--profile=low-latency",
        "--untimed",
        "--rtsp-transport=tcp",
        f"--title={title}",
        "--no-audio",
        url
    ], stdout=log_file, stderr=subprocess.STDOUT)

def main():
    while True:
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)

            width = int(os.environ.get("WIDTH", 3840))
            height = int(os.environ.get("HEIGHT", 2160))
            rows, cols = config.get("grid", [2, 2])
            win_w = width // cols
            win_h = height // rows

            for tile in config.get("tiles", []):
                row, col = tile["row"], tile["col"]
                url = tile["url"]
                title = f"tile_{row}_{col}"
                x = col * win_w
                y = row * win_h

                if not is_stream_alive(url):
                    restart_stream(title, url, x, y, win_w, win_h)

        except Exception as e:
            with open("viewport.log", "a") as log:
                log.write(f"[ERROR] {e}\n")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
