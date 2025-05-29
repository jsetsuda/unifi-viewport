#!/usr/bin/env python3
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("UFP_HOST")
USERNAME = os.getenv("UFP_USERNAME")
PASSWORD = os.getenv("UFP_PASSWORD")

if not all([HOST, USERNAME, PASSWORD]):
    raise Exception("UFP_HOST, UFP_USERNAME, and UFP_PASSWORD must be set in .env")

session = requests.Session()
session.verify = False  # Disable SSL verification for local NVRs

print("[INFO] Authenticating with UniFi Protect...")

# Get authentication token
auth_resp = session.post(
    f"{HOST}/api/auth/login",
    json={"username": USERNAME, "password": PASSWORD}
)

if auth_resp.status_code != 200:
    raise Exception(f"[ERROR] Login failed: {auth_resp.status_code} {auth_resp.text}")

# Confirm token set
token = auth_resp.cookies.get("TOKEN")
if not token:
    raise Exception("[ERROR] Failed to retrieve auth token.")

session.cookies.set("TOKEN", token)

# Get camera list
print("[INFO] Fetching camera list...")
cam_resp = session.get(f"{HOST}/proxy/protect/api/cameras")

if cam_resp.status_code != 200:
    raise Exception(f"[ERROR] Failed to fetch cameras: {cam_resp.status_code} {cam_resp.text}")

cameras = cam_resp.json()
output = []

for cam in cameras:
    name = cam.get("name")
    channels = cam.get("channels", [])

    for ch in channels:
        if ch.get("isRtspEnabled") and ch.get("rtspAlias"):
            rtsp_url = f"rtsp://{HOST.replace('https://', '').replace('http://', '')}:7447/{ch['rtspAlias']}"
            output.append({"name": name, "url": rtsp_url})
            break  # Only take first working channel

# Write to file
with open("camera_urls.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"[SUCCESS] Saved {len(output)} camera streams to camera_urls.json")
