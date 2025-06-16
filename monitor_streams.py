#!/usr/bin/env python3
"""
monitor_streams.py

– Monitors and restarts missing MPV RTSP streams (health check every 5 s).
– Kills any MPV processes older than STALE_INTERVAL (30 min) once every STALE_INTERVAL.
"""

import time
import subprocess
import json
import psutil
import re
import os

# --- Configuration Constants ---
CONFIG_FILE       = "viewport_config.json"
LOG_FILE          = "viewport.log"
MPV_BIN           = "/usr/bin/mpv"
CHECK_INTERVAL    = 5         # seconds between health checks
RESTART_COOLDOWN  = 5         # seconds between restarts per tile
STALE_INTERVAL    = 30 * 60   # seconds before considering an MPV process stale

# Track last restart timestamps per tile title
last_restart = {}
last_stale_sweep = 0.0

# --- Logging Utility ---
def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[MONITOR {ts}] {msg}\n")

# --- Screen and Grid Utilities ---
def get_screen_resolution():
    try:
        out = subprocess.check_output(["xdpyinfo"], stderr=subprocess.DEVNULL).decode()
        for line in out.splitlines():
            if "dimensions:" in line:
                dims = line.split()[1]
                w,h = map(int, dims.split("x"))
                return w, h
    except Exception as e:
        log(f"xdpyinfo error: {e}")
    return 1920, 1080  # fallback

def get_grid_dimensions():
    try:
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        rows, cols = cfg.get("grid", [1,1])
        return int(rows), int(cols)
    except Exception as e:
        log(f"Grid read error: {e}")
        return 1,1

# --- Process Health Check ---
def is_process_running(title: str) -> bool:
    for proc in psutil.process_iter(attrs=["cmdline"]):
        try:
            cmd = proc.info["cmdline"] or []
            if any(title in arg for arg in cmd):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

# --- Stream Launcher ---
def launch_stream(tile: dict):
    row = tile.get("row", 0)
    col = tile.get("col", 0)
    name = tile.get("name", "Unnamed")
    url  = tile.get("url", "")
    title = f"tile_{row}_{col}"

    # Skip null URLs
    if not url or url.lower() == "null":
        return

    now = time.time()
    if now - last_restart.get(title, 0) < RESTART_COOLDOWN:
        return

    # Screen/grid geometry
    sw, sh = get_screen_resolution()
    gr, gc = get_grid_dimensions()
    w_mul = tile.get("w", 1)
    h_mul = tile.get("h", 1)

    cell_w = sw // gc
    cell_h = sh // gr
    win_w = cell_w * w_mul
    win_h = cell_h * h_mul
    x = col * cell_w
    y = row * cell_h

    # Hardware decode hint for Pi 5
    try:
        model = open("/proc/device-tree/model").read()
        hwdec = "--hwdec=auto" if "Raspberry Pi 5" in model else ""
    except:
        hwdec = ""

    # Convert RTSPS → RTSP
    url = re.sub(r"rtsps://([^:/]+):7441", r"rtsp://\1:7447", url)

    log(f"Restarting '{name}' ({title}) at {win_w}x{win_h}+{x}+{y}")
    cmd = [
        MPV_BIN,
        "--no-border",
        f"--geometry={win_w}x{win_h}+{x}+{y}",
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
    # Launch detached
    subprocess.Popen(cmd, stdout=open(LOG_FILE, "a"), stderr=subprocess.STDOUT)
    last_restart[title] = now

# --- Stale-Stream Cleanup ---
def kill_stale_streams():
    now = time.time()
    for proc in psutil.process_iter(['name','create_time']):
        if proc.info['name'] == 'mpv':
            age = now - proc.info['create_time']
            if age > STALE_INTERVAL:
                log(f"Killing stale mpv (PID={proc.pid}, age={int(age)}s)")
                try:
                    proc.kill()
                except Exception as e:
                    log(f"Failed to kill PID {proc.pid}: {e}")

# --- Main Loop ---
def main():
    log("Stream monitor started.")
    global last_stale_sweep

    while True:
        # 1) Health check & restart missing streams
        try:
            cfg = json.load(open(CONFIG_FILE))
            for tile in cfg.get("tiles", []):
                launch_stream(tile)
        except Exception as e:
            log(f"Config/read error: {e}")

        # 2) Stale cleanup every STALE_INTERVAL
        now = time.time()
        if now - last_stale_sweep >= STALE_INTERVAL:
            try:
                kill_stale_streams()
            except Exception as e:
                log(f"Stale cleanup error: {e}")
            last_stale_sweep = now

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
