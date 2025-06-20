#!/usr/bin/env python3
"""
monitor_streams.py

– Monitors and restarts missing MPV RTSP streams every CHECK_INTERVAL.
– Kills any MPV processes older than STALE_INTERVAL.
– Ensures exactly one MPV per tile_<row>_<col>.
– Detects and logs unexpected or rogue tile processes.
"""

import time
import subprocess
import json
import psutil
import re
import os
import hashlib
import logging
from logging.handlers import RotatingFileHandler

# ─── Configuration ─────────────────────────────────────────────────────────────
CONFIG_FILE      = "viewport_config.json"
LOG_FILE         = "viewport.log"
MPV_BIN          = "/usr/bin/mpv"
CHECK_INTERVAL   = 5         # seconds between health checks
RESTART_COOLDOWN = 5         # min seconds between restarts per tile
STALE_INTERVAL   = 30 * 60   # seconds before an mpv is considered stale
KILL_UNKNOWN     = True      # set True to auto-kill rogue tiles
FLAG_FILE        = "layout_updated.flag"
# ──────────────────────────────────────────────────────────────────────────────

# ─── Logging Setup ─────────────────────────────────────────────────────────────
logger = logging.getLogger("monitor")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=3)
formatter = logging.Formatter('[MONITOR %(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

def log(msg: str):
    logger.info(msg)

# ─── Globals ───────────────────────────────────────────────────────────────────
last_restart = {}        # title → timestamp
last_stale_sweep = 0.0
last_config_hash = None

# ─── Utilities ─────────────────────────────────────────────────────────────────
def hash_config(cfg):
    try:
        return hashlib.md5(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
    except Exception:
        return ""

def load_config():
    try:
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
            tiles = cfg.get("tiles", [])
            grid = cfg.get("grid", [1, 1])
            if not isinstance(tiles, list) or len(grid) != 2:
                raise ValueError("Invalid config structure")
            return cfg
    except Exception as e:
        log(f"Failed to load config: {e}")
        return {"tiles": []}

def get_resolution():
    try:
        out = subprocess.check_output("xrandr --current", shell=True).decode()
        for line in out.splitlines():
            if " connected primary" in line or " connected" in line:
                match = re.search(r"(\d+)x(\d+)\+", line)
                if match:
                    return int(match.group(1)), int(match.group(2))
    except:
        pass
    return 3840, 2160  # fallback

def is_running(title: str):
    for p in psutil.process_iter(attrs=["cmdline"]):
        try:
            if p.info["cmdline"] and any(arg == f"--title={title}" for arg in p.info["cmdline"]):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def kill_stale():
    now = time.time()
    for p in psutil.process_iter(attrs=["name", "create_time"]):
        if p.info["name"] == "mpv":
            age = now - p.info["create_time"]
            if age > STALE_INTERVAL:
                log(f"Killing stale mpv PID={p.pid}, age={int(age)}s")
                try:
                    p.kill()
                except Exception as e:
                    log(f"  error killing PID {p.pid}: {e}")

def enforce_one_per_tile():
    procs = {}
    for p in psutil.process_iter(attrs=["pid", "cmdline", "create_time"]):
        try:
            if not p.info["cmdline"]:
                continue
            for arg in p.info["cmdline"]:
                match = re.fullmatch(r"--title=tile_(\d+)_(\d+)", arg)
                if match:
                    title = match.group(0).split("=")[1]
                    procs.setdefault(title, []).append((p.info["pid"], p.info["create_time"]))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    for title, instances in procs.items():
        if len(instances) > 1:
            inst_sorted = sorted(instances, key=lambda x: x[1], reverse=True)
            for pid, _ in inst_sorted[1:]:
                log(f"Killing duplicate {title} PID={pid}")
                try:
                    os.kill(pid, 9)
                except Exception as e:
                    log(f"  error killing PID {pid}: {e}")

def find_unexpected_tiles(cfg):
    valid_titles = {f"tile_{t['row']}_{t['col']}" for t in cfg.get("tiles", [])}
    for p in psutil.process_iter(attrs=["pid", "cmdline"]):
        try:
            if not p.info["cmdline"]:
                continue
            for arg in p.info["cmdline"]:
                match = re.fullmatch(r"--title=(tile_\d+_\d+)", arg)
                if match:
                    title = match.group(1)
                    if title not in valid_titles:
                        log(f"❗ Unexpected tile detected: {title} (PID={p.pid})")
                        if KILL_UNKNOWN:
                            try:
                                os.kill(p.pid, 9)
                                log(f"  → Killed rogue tile {title}")
                            except Exception as e:
                                log(f"  → Error killing rogue tile: {e}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

def launch(tile):
    row, col = tile["row"], tile["col"]
    title = f"tile_{row}_{col}"
    url = tile.get("url", "")
    now = time.time()

    if not url or url.lower() == "null":
        return
    if now - last_restart.get(title, 0) < RESTART_COOLDOWN:
        return

    W, H = get_resolution()
    grid_rows, grid_cols = cfg.get("grid", [1, 1])
    TW = W // grid_cols
    TH = H // grid_rows
    x = col * TW
    y = row * TH
    ww = tile.get("w", 1) * TW
    hh = tile.get("h", 1) * TH

    cmd = [
        MPV_BIN,
        "--no-border",
        f"--geometry={ww}x{hh}+{x}+{y}",
        f"--title={title}",
        url
    ]
    log(f"Restarting {title}")
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    last_restart[title] = now

# ─── Main Loop ─────────────────────────────────────────────────────────────────
def main():
    global last_stale_sweep, last_config_hash, cfg
    log("Stream monitor started")

    if os.path.exists(FLAG_FILE):
        log("Detected layout_updated.flag – sleeping before enforcing streams")
        time.sleep(5)
        try:
            os.remove(FLAG_FILE)
            log("layout_updated.flag cleared")
        except Exception as e:
            log(f"Warning: could not delete layout_updated.flag – {e}")

    while True:
        cfg = load_config()
        new_hash = hash_config(cfg)
        if new_hash != last_config_hash:
            log("Detected layout config change")
            last_config_hash = new_hash

        for tile in cfg.get("tiles", []):
            title = f"tile_{tile.get('row')}_{tile.get('col')}"
            if not is_running(title):
                launch(tile)

        enforce_one_per_tile()
        find_unexpected_tiles(cfg)

        if time.time() - last_stale_sweep >= STALE_INTERVAL:
            kill_stale()
            last_stale_sweep = time.time()

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
