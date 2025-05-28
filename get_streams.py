#!/usr/bin/env python3
import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

UFP_HOST = os.getenv("UFP_HOST")
UFP_USERNAME = os.getenv("UFP_USERNAME")
UFP_PASSWORD = os.getenv("UFP_PASSWORD")

if not all([UFP_HOST, UFP_USERNAME, UFP_PASSWORD]):
    raise Exception("UFP_HOST, UFP_USERNAME, and UFP_PASSWORD must be set in .env")

session = requests.Session()
session.verify = False  # Disable SSL verification for local network

# Authenticate with UniFi Protect
login_payload = {
    "username": UFP_USERNAME,
    "password": UFP_PASSWORD
}

print("[INFO] Logging into UniFi Protect...")
resp = session.post(f"{UFP_HOST}/api/auth/login", json=login_payload)
resp.raise_for_status()

# Get camera list
print("[INFO] Fetching camera list...")
resp = session.get(f"{UFP_HOST}/proxy/protect/api/camera")
resp.raise_for_status()
cameras = resp.json()

camera_list = []
for cam in cameras:
    name = cam.get("name")
    rtsp_streams = cam.get("channels", [])
    for channel in rtsp_streams:
        if "rtspAlias" in channel and channel.get("isRtspEnabled", False):
            rtsp_url = f"{UFP_HOST.replace('https://', 'rtsps://')}/" + channel["rtspAlias"]
            camera_list.append({
                "name": name,
                "url": rtsp_url
            })
            break

# Convert rtsps:7441 → rtsp:7447 for MPV
for cam in camera_list:
    url = cam.get("url", "")
    if url.startswith("rtsps://") and ":7441" in url:
        url = url.replace("rtsps://", "rtsp://").replace(":7441", ":7447")
        cam["url"] = url

# Save to file
with open("camera_urls.json", "w") as f:
    json.dump(camera_list, f, indent=2)

print(f"[SUCCESS] Saved {len(camera_list)} camera streams to camera_urls.json")
