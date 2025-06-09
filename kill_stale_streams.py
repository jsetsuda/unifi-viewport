#!/usr/bin/env python3
import psutil
from datetime import datetime

MAX_RUNTIME_SECONDS = 3600  # 1 hour
now = datetime.now()

for proc in psutil.process_iter(['pid', 'name', 'create_time']):
    try:
        if proc.info['name'] == 'mpv':
            runtime = (now.timestamp() - proc.info['create_time'])
            if runtime > MAX_RUNTIME_SECONDS:
                print(f"[{datetime.now()}] Killing stale mpv PID {proc.pid} running for {int(runtime // 60)} min")
                proc.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue
