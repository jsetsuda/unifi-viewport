#!/usr/bin/env python3

import json
import os
from dotenv import load_dotenv
from uiprotect import ProtectApiClient
from uiprotect.exceptions import NotAuthorized

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CAMERA_FILE = os.path.join(SCRIPT_DIR, "camera_urls.json")
ENV_FILE = os.path.join(SCRIPT_DIR, ".env")

load_dotenv(ENV_FILE)

host = os.getenv("UFP_HOST")
username = os.getenv("UFP_USERNAME")
password = os.getenv("UFP_PASSWORD")

if not all([host, username, password]):
    raise Exception("UFP_HOST, UFP_USERNAME, and UFP_PASSWORD must be set in .env")

try:
    client = ProtectApiClient(host, username, password, ignore_warnings=True)
    client.update()
except NotAuthorized as e:
    raise SystemExit(f"[ERROR] Login failed: {e}")
except Exception as e:
    raise SystemExit(f"[ERROR] Failed to connect: {e}")

camera_data = []
for cam in client.bootstrap.cameras.values():
    try:
        if cam.is_adopted and cam.is_online and cam.is_recording:
            camera_data.append({
                "name": cam.name,
                "url": cam.rtsps_uri
            })
    except Exception as e:
        print(f"[WARN] Could not add camera {cam.name}: {e}")

if not camera_data:
    raise SystemExit("[ERROR] No valid cameras retrieved.")

with open(CAMERA_FILE, "w") as f:
    json.dump(camera_data, f, indent=2)

print(f"[INFO] Saved {len(camera_data)} cameras to {CAMERA_FILE}")
