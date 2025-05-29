#!/usr/bin/env python3
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

UFP_HOST = os.getenv("UFP_HOST")
UFP_USERNAME = os.getenv("UFP_USERNAME")
UFP_PASSWORD = os.getenv("UFP_PASSWORD")

if not all([UFP_HOST, UFP_USERNAME, UFP_PASSWORD]):
    raise ValueError("Missing one or more .env values: UFP_HOST, UFP_USERNAME, UFP_PASSWORD")

LOGIN_URL = f"{UFP_HOST}/api/auth/login"
CAMERA_URL = f"{UFP_HOST}/proxy/protect/api/cameras"
COOKIE_FILE = "cookies.txt"
HEADERS = {"Content-Type": "application/json"}

def login(session):
    print("[INFO] Logging in...")
    response = session.post(LOGIN_URL, json={
        "username": UFP_USERNAME,
        "password": UFP_PASSWORD
    }, headers=HEADERS, verify=False)

    if response.status_code != 200:
        raise Exception(f"Login failed: {response.status_code} - {response.text}")
    print("[INFO] Logged in successfully.")

def get_cameras(session):
    print("[INFO] Fetching camera list...")
    response = session.get(CAMERA_URL, headers=HEADERS, verify=False)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch cameras: {response.status_code} - {response.text}")
    return response.json()

def parse_cameras(data):
    stream_list = []

    for cam in data:
        name = cam.get("name", "Unnamed")
        state = cam.get("state", "")
        channels = cam.get("channels", [])

        if state != "CONNECTED":
            print(f"[INFO] Skipping disconnected camera: {name}")
            continue

        print(f"[INFO] Processing camera: {name}")
        for channel in channels:
            rtsp = channel.get("rtspAlias")
            resolution = f"{channel.get('width')}x{channel.get('height')}"
            fps = channel.get("fps")

            if rtsp:
                stream_list.append({
                    "name": f"{name} ({resolution} @ {fps}fps)",
                    "url": f"rtsps://{UFP_HOST.split('//')[-1]}:7441/{rtsp}"
                })

    return stream_list

def save_output(streams):
    with open("camera_urls.json", "w") as f:
        json.dump(streams, f, indent=2)
    print(f"[SUCCESS] Saved {len(streams)} camera streams to camera_urls.json")

    layout = {
        "layout": "2x2" if len(streams) <= 4 else "3x3" if len(streams) <= 9 else "4x4"
    }
    with open("viewport_config.json", "w") as f:
        json.dump(layout, f, indent=2)
    print(f"[SUCCESS] Saved layout ({layout['layout']}) to viewport_config.json")

if __name__ == "__main__":
    session = requests.Session()
    try:
        login(session)
        data = get_cameras(session)
        streams = parse_cameras(data)
        save_output(streams)
    except Exception as e:
        print(f"[ERROR] {e}")
