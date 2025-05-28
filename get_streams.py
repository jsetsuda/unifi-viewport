#!/usr/bin/env python3
import os
import json
from dotenv import load_dotenv
from unifi.protect import ProtectApiClient
from unifi.protect.exceptions import NvrError

# Load .env values
load_dotenv()
HOST = os.getenv("UNIFI_HOST")
USER = os.getenv("UNIFI_USER")
PASS = os.getenv("UNIFI_PASS")

if not all([HOST, USER, PASS]):
    raise Exception("UNIFI_HOST, UNIFI_USER, and UNIFI_PASS must be set in .env")

print("[INFO] Connecting to UniFi Protect...")
try:
    protect = ProtectApiClient(
        host=HOST.replace("https://", ""),
        username=USER,
        password=PASS,
        port=443,
        verify_ssl=False,
    )
    protect.update()  # Load initial data

    camera_list = []
    for cam in protect.bootstrap.cameras.values():
        if cam.channels:
            for ch in cam.channels:
                if ch.is_rtsp_enabled and ch.rtsp_alias:
                    rtsp_url = f"rtsps://{HOST.replace('https://', '')}:7441/{ch.rtsp_alias}"
                    # Convert rtsps:7441 → rtsp:7447 for mpv
                    rtsp_url = rtsp_url.replace("rtsps://", "rtsp://").replace(":7441", ":7447")
                    camera_list.append({
                        "name": cam.name,
                        "url": rtsp_url
                    })
                    break  # Only grab first working RTSP stream
except NvrError as e:
    print(f"[ERROR] Failed to connect to UniFi Protect: {e}")
    exit(1)

# Save to file
with open("camera_urls.json", "w") as f:
    json.dump(camera_list, f, indent=2)

print(f"[SUCCESS] Saved {len(camera_list)} camera streams to camera_urls.json")
