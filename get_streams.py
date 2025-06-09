#!/usr/bin/env python3
import argparse
import os
import json
import requests
from dotenv import load_dotenv

"""
get_streams.py

Description:
  - Fetches camera streams from UniFi Protect API and outputs camera_urls.json.
  - Optionally generates a default viewport_config.json based on camera count.
  - Supports a `--list` flag to print the camera list JSON to stdout without saving files.
"""

# --- Load environment ---
load_dotenv()
UFP_HOST = os.getenv("UFP_HOST")
UFP_USERNAME = os.getenv("UFP_USERNAME")
UFP_PASSWORD = os.getenv("UFP_PASSWORD")

# --- Validate environment ---
if not all([UFP_HOST, UFP_USERNAME, UFP_PASSWORD]):
    raise ValueError("Missing one or more .env values: UFP_HOST, UFP_USERNAME, UFP_PASSWORD")

# --- API endpoints ---
LOGIN_URL = f"{UFP_HOST}/api/auth/login"
CAMERA_URL = f"{UFP_HOST}/proxy/protect/api/cameras"

# --- Output files ---
CAMERA_FILE = "camera_urls.json"
CONFIG_FILE = "viewport_config.json"

# --- Request headers ---
HEADERS = {"Content-Type": "application/json"}

# --- Arg parsing ---
parser = argparse.ArgumentParser(description="Fetch UniFi Protect camera streams.")
parser.add_argument("--list", action="store_true", help="Print camera list JSON to stdout and exit.")
args = parser.parse_args()

# --- Suppress insecure warnings ---
from urllib3.exceptions import InsecureRequestWarning
import urllib3
urllib3.disable_warnings(InsecureRequestWarning)


def login(session):
    resp = session.post(
        LOGIN_URL,
        json={"username": UFP_USERNAME, "password": UFP_PASSWORD},
        headers=HEADERS,
        verify=False
    )
    resp.raise_for_status()


def get_cameras(session):
    resp = session.get(CAMERA_URL, headers=HEADERS, verify=False)
    resp.raise_for_status()
    return resp.json()


def parse_cameras(data):
    streams = []
    for cam in data:
        name = cam.get("name", "Unnamed")
        if cam.get("state") != "CONNECTED":
            continue
        channels = cam.get("channels", [])
        for ch in channels:
            rtsp_alias = ch.get("rtspAlias")
            width = ch.get("width")
            height = ch.get("height")
            fps = ch.get("fps")
            if not rtsp_alias:
                continue
            url = f"rtsps://{UFP_HOST.split('://')[-1]}:7441/{rtsp_alias}"
            label = f"{name} ({width}x{height} @ {fps}fps)"
            streams.append({"name": label, "url": url})
    return streams


def save_camera_list(streams):
    with open(CAMERA_FILE, "w") as f:
        json.dump(streams, f, indent=2)


def save_default_layout(streams):
    count = len(streams)
    if count <= 4:
        layout = "2x2"
    elif count <= 9:
        layout = "3x3"
    else:
        layout = "4x4"
    config = {"layout": layout}
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def main():
    session = requests.Session()
    login(session)
    data = get_cameras(session)
    streams = parse_cameras(data)

    if args.list:
        print(json.dumps(streams, indent=2))
        return

    save_camera_list(streams)
    save_default_layout(streams)
    print(f"[SUCCESS] Found {len(streams)} streams; wrote {CAMERA_FILE} and {CONFIG_FILE}")


if __name__ == "__main__":
    main()
