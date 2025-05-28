#!/usr/bin/env python3
import os
import json
import requests
import subprocess
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()  # Load environment variables from .env

# === CONFIGURATION ===
UNIFI_HOST = os.getenv("UNIFI_HOST")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")


def is_h264_stream(url):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        codec = result.stdout.decode().strip()
        return codec == "h264"
    except Exception as e:
        print(f"[WARN] Codec check failed for {url}: {e}")
        return False


def fetch_camera_streams():
    session = requests.Session()
    session.verify = False

    print(f"[INFO] Connecting to {UNIFI_HOST} as {USERNAME}...")

    # Login
    login_resp = session.post(f"{UNIFI_HOST}/api/auth/login", json={
        "username": USERNAME,
        "password": PASSWORD
    })

    if not login_resp.ok:
        print(f"[ERROR] Login failed: {login_resp.status_code}")
        return []

    # Get camera list
    cam_resp = session.get(f"{UNIFI_HOST}/proxy/protect/api/cameras")
    if not cam_resp.ok:
        print(f"[ERROR] Failed to retrieve camera list: {cam_resp.status_code}")
        return []

    cameras = cam_resp.json()
    results = []

    for cam in cameras:
        name = cam.get("name")
        channels = cam.get("channels", [])

        if not channels:
            continue

        rtsp_id = channels[0].get("rtspAlias")
        if not rtsp_id or rtsp_id == "None":
            continue

        url = f"rtsps://{UNIFI_HOST.split('//')[1]}:7441/{rtsp_id}"

        print(f"[INFO] Checking codec for: {name}")
        if is_h264_stream(url):
            results.append({
                "name": name,
                "url": url
            })
        else:
            print(f"[SKIP] {name} is not H.264")

    return results


def save_camera_list(cameras):
    if not cameras:
        print("[ERROR] No valid camera streams found. File not saved.")
        return

    with open("camera_urls.json", "w") as f:
        json.dump(cameras, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

    print(f"[INFO] Saved {len(cameras)} H.264 camera stream(s) to camera_urls.json")


if __name__ == "__main__":
    try:
        cams = fetch_camera_streams()
        save_camera_list(cams)
        print("[INFO] Camera fetch and save completed successfully.")
    except Exception as e:
        print(f"[ERROR] Unhandled exception: {e}")
        exit(1)

