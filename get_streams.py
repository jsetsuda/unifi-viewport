#!/usr/bin/env python3
import os
import json
import requests
from dotenv import load_dotenv
import subprocess

# Load credentials from .env
load_dotenv()

UFP_HOST = os.getenv("UFP_HOST")
UFP_USERNAME = os.getenv("UFP_USERNAME")
UFP_PASSWORD = os.getenv("UFP_PASSWORD")

OUTPUT_FILE = "camera_urls.json"

def authenticate():
    url = f"{UFP_HOST}/api/auth/login"
    data = {"username": UFP_USERNAME, "password": UFP_PASSWORD}
    try:
        response = requests.post(url, json=data, verify=False, timeout=10)
        response.raise_for_status()
        return response.cookies
    except requests.RequestException as e:
        print(f"[ERROR] Authentication failed: {e}")
        exit(1)

def get_cameras(cookies):
    url = f"{UFP_HOST}/proxy/protect/api/cameras"
    try:
        response = requests.get(url, cookies=cookies, verify=False, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch camera list: {e}")
        exit(1)

def get_metadata(rtsp_url):
    try:
        result = subprocess.run([
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=avg_frame_rate,width,height,codec_name,pix_fmt,bit_rate,profile",
            "-of", "json",
            rtsp_url
        ], capture_output=True, text=True, timeout=20)

        parsed = json.loads(result.stdout)
        stream = parsed.get("streams", [{}])[0]
        return {
            "width": stream.get("width"),
            "height": stream.get("height"),
            "codec_name": stream.get("codec_name"),
            "pix_fmt": stream.get("pix_fmt"),
            "avg_frame_rate": stream.get("avg_frame_rate"),
            "profile": stream.get("profile")
        }
    except Exception as e:
        print(f"[WARN] Failed to probe {rtsp_url}: {e}")
        return {}

def extract_rtsp_streams(cameras):
    camera_data = []

    for cam in cameras:
        name = cam.get("name", "Unknown")
        channels = cam.get("channels", [])
        stream_url = None

        for ch in channels:
            if ch.get("isRtspEnabled") and ch.get("name") == "High":
                stream_url = ch.get("rtspAlias")
                break

        if not stream_url and channels:
            for ch in channels:
                if ch.get("isRtspEnabled"):
                    stream_url = ch.get("rtspAlias")
                    break

        if stream_url:
            url = f"rtsp://{UFP_HOST.replace('https://', '').replace('http://', '')}:7447/{stream_url}"
            metadata = get_metadata(url)

            camera_data.append({
                "name": name,
                "url": url,
                "metadata": metadata
            })

    return camera_data

def main():
    print("[INFO] Authenticating with UniFi Protect...")
    cookies = authenticate()

    print("[INFO] Fetching camera list...")
    cameras = get_cameras(cookies)

    print("[INFO] Extracting RTSP URLs and probing metadata...")
    camera_data = extract_rtsp_streams(cameras)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(camera_data, f, indent=2)

    print(f"[SUCCESS] Saved {len(camera_data)} camera streams with metadata to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
