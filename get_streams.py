#!/usr/bin/env python3
import requests
import json
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === CONFIGURATION ===
UNIFI_HOST = "https://192.168.5.10"  # Replace with your NVR IP
USERNAME = "viewport"
PASSWORD = "ProtectViewer1!"


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
        results.append({
            "name": name,
            "url": url
        })

    return results


def save_camera_list(cameras):
    if not cameras:
        print("[ERROR] No valid camera streams found. File not saved.")
        return

    with open("camera_urls.json", "w") as f:
        json.dump(cameras, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

    print(f"[INFO] Saved {len(cameras)} camera stream(s) to camera_urls.json")


if __name__ == "__main__":
    cams = fetch_camera_streams()
    save_camera_list(cams)
