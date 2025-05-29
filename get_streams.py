#!/usr/bin/env python3
import os
import json
import requests
import urllib3
from dotenv import load_dotenv

# Suppress warnings for unverified HTTPS requests (local NVRs)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

HOST = os.getenv("UFP_HOST")
USERNAME = os.getenv("UFP_USERNAME")
PASSWORD = os.getenv("UFP_PASSWORD")

if not all([HOST, USERNAME, PASSWORD]):
    raise Exception("UFP_HOST, UFP_USERNAME, and UFP_PASSWORD must be set in .env")

session = requests.Session()
session.verify = False  # Don't verify SSL for local IPs with self-signed certs

print("[INFO] Authenticating with UniFi Protect...")

# Authenticate and get session cookie
auth_resp = session.post(
    f"{HOST}/api/auth/login",
    json={"username": USERNAME, "password": PASSWORD}
)

if auth_resp.status_code != 200:
    raise Exception(f"[ERROR] Login failed: {auth_resp.status_code} {auth_resp.text}")

# Get auth token
token = auth_resp.cookies.get("TOKEN")
if not token:
    raise Exception("[ERROR] Failed to retrieve auth token.")

session.cookies.set("TOKEN", token)

# Fetch camera list
print("[INFO] Fetching camera list...")
cam_resp = session.get(f"{HOST}/proxy/protect/api/cameras")

if cam_resp.status_code != 200:
    raise Exception(f"[ERROR] Failed to fetch cameras: {cam_resp.status_code} {cam_resp.text}")

cameras = cam_resp.json()
output = []

for cam in cameras:
    name = cam.get("name", "Unnamed Camera")
    channels = cam.get("channels", [])

    for ch in channels:
        if ch.get("isRtspEnabled") and ch.get("rtspAlias"):
            width = ch.get("width", "?")
            height = ch.get("height", "?")
            resolution = f"{width}x{height}"
            rtsp_url = f"rtsp://{HOST.replace('https://', '').replace('http://', '')}:7447/{ch['rtspAlias']}"
            output.append({
                "name": f"{name} ({resolution})",
                "url": rtsp_url
            })

# Save results
with open("camera_urls.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"[SUCCESS] Saved {len(output)} camera streams to camera_urls.json")
