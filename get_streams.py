#!/usr/bin/env python3
import os
import json
import requests
import subprocess
from dotenv import load_dotenv

UFP_API = "/proxy/protect/api/cameras"
CAMERA_JSON = "camera_urls.json"
CONFIG_JSON = "viewport_config.json"

def ffprobe_info(rtsp_url):
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=avg_frame_rate,width,height,codec_name,pix_fmt,bit_rate,profile",
            "-of", "json",
            rtsp_url
        ], capture_output=True, text=True, timeout=10)

        data = json.loads(result.stdout)
        stream = data["streams"][0] if data["streams"] else {}

        return {
            "width": stream.get("width"),
            "height": stream.get("height"),
            "codec": stream.get("codec_name"),
            "profile": stream.get("profile"),
            "pix_fmt": stream.get("pix_fmt"),
            "bit_rate": stream.get("bit_rate"),
            "fps": stream.get("avg_frame_rate")
        }

    except Exception as e:
        print(f"[WARN] Failed to probe {rtsp_url}: {e}")
        return {}

def get_rtsp_streams():
    load_dotenv()

    host = os.getenv("UFP_HOST")
    username = os.getenv("UFP_USERNAME")
    password = os.getenv("UFP_PASSWORD")

    if not all([host, username, password]):
        print("[ERROR] Missing .env variables: UFP_HOST, UFP_USERNAME, or UFP_PASSWORD")
        return []

    session = requests.Session()
    session.verify = False

    try:
        r = session.post(f"{host}/api/auth/login", json={"username": username, "password": password})
        r.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to authenticate: {e}")
        return []

    try:
        r = session.get(f"{host}{UFP_API}")
        r.raise_for_status()
        cameras = r.json()
    except Exception as e:
        print(f"[ERROR] Failed to get camera list: {e}")
        return []

    streams = []
    tiles = []
    row, col = 0, 0

    for cam in cameras:
        if not cam.get("isConnected"):
            continue

        name = cam.get("name", "Unnamed Camera")
        channels = cam.get("channels", [])
        high_quality = next((ch for ch in channels if ch.get("name") == "High" and ch.get("rtspEnabled")), None)

        if not high_quality:
            continue

        url = high_quality.get("rtspUrl")
        meta = ffprobe_info(url)

        entry = {
            "name": name,
            "url": url,
            **meta
        }
        streams.append(entry)

        tiles.append({
            "row": row,
            "col": col,
            "name": f"{name} ({meta.get('width')}x{meta.get('height')})",
            "url": url
        })

        col += 1
        if col > 1:
            col = 0
            row += 1

    with open(CAMERA_JSON, "w") as f:
        json.dump(streams, f, indent=2)

    with open(CONFIG_JSON, "w") as f:
        json.dump({
            "grid": [2, 2],
            "tiles": tiles
        }, f, indent=2)

    print(f"[SUCCESS] Saved {len(streams)} camera streams to {CAMERA_JSON} and {CONFIG_JSON}")

if __name__ == "__main__":
    get_rtsp_streams()
