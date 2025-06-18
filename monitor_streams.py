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

# ─── Configuration ─────────────────────────────────────────────────────────────
CONFIG_FILE      = "viewport_config.json"
LOG_FILE         = "viewport.log"
MPV_BIN          = "/usr/bin/mpv"
CHECK_INTERVAL   = 5         # seconds between health checks
RESTART_COOLDOWN = 5         # min seconds between restarts per tile
STALE_INTERVAL   = 30 * 60   # seconds before an mpv is considered stale
KILL_UNKNOWN     = False     # set True to auto-kill rogue tiles
# ──────────────────────────────────────────────────────────────────────────────

last_restart = {}        # title → timestamp
last_stale_sweep = 0.0
last_config_hash = None

def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[MONITOR {ts}] {msg}\n")

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

def is_running(title: str):
    """Return True if exactly one MPV is running for this tile title."""
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
    """Ensure at most one mpv process per tile_<r>_<c>."""
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
    """Log and optionally kill mpv tiles that aren't in config."""
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

    cmd = [
        MPV_BIN,
        "--no-border",
        f"--title={title}",
        url
    ]
    log(f"Restarting {title}")
    subprocess.Popen(cmd, stdout=open(LOG_FILE, "a"), stderr=subprocess.STDOUT)
    last_restart[title] = now

def main():
    global last_stale_sweep, last_config_hash
    log("Stream monitor started")

    while True:
        cfg = load_config()
        new_hash = hash_config(cfg)
        if new_hash != last_config_hash:
            log("Detected layout config change")
            last_config_hash = new_hash

        # 1) Restart any missing tiles
        for tile in cfg.get("tiles", []):
            title = f"tile_{tile.get('row')}_{tile.get('col')}"
            if not is_running(title):
                launch(tile)

        # 2) Kill duplicate tiles
        enforce_one_per_tile()

        # 3) Kill unexpected tiles
        find_unexpected_tiles(cfg)

        # 4) Kill stale processes
        if time.time() - last_stale_sweep >= STALE_INTERVAL:
            kill_stale()
            last_stale_sweep = time.time()

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
