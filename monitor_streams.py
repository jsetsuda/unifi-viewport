#!/usr/bin/env python3
"""
monitor_streams.py

– Monitors and restarts missing MPV RTSP streams every CHECK_INTERVAL.
– Kills any MPV processes older than STALE_INTERVAL once every STALE_INTERVAL.
– Ensures at most one MPV per tile_<row>_<col> by killing duplicates.
"""

import time
import subprocess
import json
import psutil
import re
import os

# ─── Configuration ─────────────────────────────────────────────────────────────
CONFIG_FILE      = "viewport_config.json"
LOG_FILE         = "viewport.log"
MPV_BIN          = "/usr/bin/mpv"
CHECK_INTERVAL   = 5          # health check interval (s)
RESTART_COOLDOWN = 5          # min seconds between restarts per tile
STALE_INTERVAL   = 30 * 60    # seconds before an mpv is considered stale
# ──────────────────────────────────────────────────────────────────────────────

last_restart = {}        # title → timestamp of last restart
last_stale_sweep = 0.0

def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[MONITOR {ts}] {msg}\n")

def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception as e:
        log(f"Failed to load config: {e}")
        return {"tiles": []}

def is_running(title: str):
    for p in psutil.process_iter(attrs=["cmdline"]):
        try:
            if p.info["cmdline"] and any(title in arg for arg in p.info["cmdline"]):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def kill_stale():
    now = time.time()
    for p in psutil.process_iter(attrs=["name","create_time"]):
        if p.info["name"] == "mpv":
            age = now - p.info["create_time"]
            if age > STALE_INTERVAL:
                log(f"Killing stale mpv PID={p.pid}, age={int(age)}s")
                try: p.kill()
                except Exception as e: log(f"  error killing PID {p.pid}: {e}")

def enforce_one_per_tile():
    """
    For each tile_<r>_<c>, ensure only the newest mpv remains.
    Kill extras if found.
    """
    # Map title -> list of (pid, create_time)
    procs = {}
    for p in psutil.process_iter(attrs=["pid","cmdline","create_time"]):
        try:
            if not p.info["cmdline"]: continue
            for arg in p.info["cmdline"]:
                m = re.match(r"--title=tile_(\d+)_(\d+)", arg)
                if m:
                    title = m.group(0).split("=",1)[1]
                    procs.setdefault(title, []).append((p.info["pid"], p.info["create_time"]))
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # For each title with >1 processes, kill all but the newest
    for title, instances in procs.items():
        if len(instances) > 1:
            # sort by create_time descending: keep first, kill the rest
            inst_sorted = sorted(instances, key=lambda x: x[1], reverse=True)
            for pid, _ in inst_sorted[1:]:
                log(f"Killing duplicate {title} PID={pid}")
                try: os.kill(pid, 9)
                except Exception as e: log(f"  error killing PID {pid}: {e}")

def launch(tile):
    row, col = tile["row"], tile["col"]
    title = f"tile_{row}_{col}"
    url   = tile.get("url","")
    now   = time.time()

    if not url or url.lower()=="null":
        return
    if now - last_restart.get(title, 0) < RESTART_COOLDOWN:
        return

    # geometry calc
    # (we only need the MPV command here—screen math lives in viewport.sh)
    cmd = [
        MPV_BIN,
        "--no-border",
        f"--title={title}",
        url
    ]
    log(f"Restarting {title}")
    subprocess.Popen(cmd, stdout=open(LOG_FILE,"a"), stderr=subprocess.STDOUT)
    last_restart[title] = now

def main():
    log("Stream monitor started")
    global last_stale_sweep

    while True:
        cfg = load_config()

        # 1) Health check & restart missing
        for tile in cfg.get("tiles", []):
            title = f"tile_{tile.get('row')}_{tile.get('col')}"
            if not is_running(title):
                launch(tile)

        # 2) Enforce one mpv process per tile
        enforce_one_per_tile()

        # 3) Stale cleanup on interval
        if time.time() - last_stale_sweep >= STALE_INTERVAL:
            kill_stale()
            last_stale_sweep = time.time()

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
