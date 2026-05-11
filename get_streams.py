#!/usr/bin/env python3
"""
get_streams.py — v2 (official UniFi Protect Integration API)

Lists cameras and RTSPS stream URLs via the official Protect integration API,
authenticated with an X-API-KEY header. Writes camera_urls.json in a shape
that's drop-in compatible with the v1 downstream (layout_chooser.py, viewport.sh).

Usage:
  python3 get_streams.py             # write camera_urls.json (uses only cameras with RTSPS already on)
  python3 get_streams.py --list      # print JSON to stdout, no files written
  python3 get_streams.py --debug     # log API responses to stderr (for troubleshooting)
  python3 get_streams.py --enable    # opt-in: turn on RTSPS for cameras that have it disabled
"""
import argparse
import json
import os
import sys
import time

import requests
import urllib3
from dotenv import load_dotenv
from urllib3.exceptions import InsecureRequestWarning

urllib3.disable_warnings(InsecureRequestWarning)

load_dotenv()
UFP_HOST = (os.getenv("UFP_HOST") or "").rstrip("/")
UFP_API_KEY = os.getenv("UFP_API_KEY")
UFP_VERIFY_SSL = os.getenv("UFP_VERIFY_SSL", "false").lower() in ("1", "true", "yes")

if not UFP_HOST or not UFP_API_KEY or UFP_API_KEY == "your_api_key_here":
    sys.exit("[ERROR] Missing .env values: UFP_HOST and UFP_API_KEY are required")

API_BASE = f"{UFP_HOST}/proxy/protect/integration/v1"
HEADERS = {"X-API-KEY": UFP_API_KEY, "Accept": "application/json"}
CAMERA_FILE = "camera_urls.json"
CONFIG_FILE = "viewport_config.json"


def _request(session, method, path, *, body=None, debug=False):
    """Send a request, retrying on 429 with exponential backoff (NVR caps ~10 req/s)."""
    url = f"{API_BASE}{path}"
    headers = dict(HEADERS)
    if body is not None:
        headers["Content-Type"] = "application/json"
    delay = 0.2
    for attempt in range(5):
        resp = session.request(method, url, headers=headers, json=body,
                               verify=UFP_VERIFY_SSL, timeout=15)
        if debug:
            sys.stderr.write(f"[DEBUG] {method} {url} -> {resp.status_code}\n")
            if resp.text:
                sys.stderr.write(f"[DEBUG]   body: {resp.text[:600]}\n")
        if resp.status_code != 429:
            return resp
        if debug:
            sys.stderr.write(f"[DEBUG] 429 rate-limited; sleeping {delay:.2f}s and retrying\n")
        time.sleep(delay)
        delay *= 2
    return resp  # final attempt's response, even if still 429


def list_cameras(session, debug=False):
    r = _request(session, "GET", "/cameras", debug=debug)
    r.raise_for_status()
    return r.json()


def get_rtsps(session, camera_id, debug=False):
    r = _request(session, "GET", f"/cameras/{camera_id}/rtsps-stream", debug=debug)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def _has_any_url(payload):
    if isinstance(payload, dict):
        return any(isinstance(v, str) and v for v in payload.values())
    if isinstance(payload, list):
        return any(isinstance(d, dict) and d.get("url") for d in payload)
    return False


def enable_rtsps(session, camera_id, debug=False):
    body = {"qualities": ["high", "medium", "low"]}
    r = _request(session, "POST", f"/cameras/{camera_id}/rtsps-stream",
                 body=body, debug=debug)
    r.raise_for_status()
    return r.json() if r.text else {}


def _resolution_label(camera, quality):
    """Best-effort 'WxH @ fps' suffix from the camera object for a given quality."""
    channels = camera.get("channels") or []
    quality_norm = (quality or "").lower()
    for ch in channels:
        ch_quality = (ch.get("name") or ch.get("quality") or "").lower()
        if ch_quality == quality_norm:
            w, h, fps = ch.get("width"), ch.get("height"), ch.get("fps")
            if w and h and fps:
                return f"{w}x{h} @ {fps}fps"
            if w and h:
                return f"{w}x{h}"
    return None


def streams_for(camera, rtsps_payload):
    """Normalize the rtsps-stream payload into [{name, url}, ...]."""
    if not rtsps_payload:
        return []
    cam_name = camera.get("name") or camera.get("displayName") or "Camera"

    if isinstance(rtsps_payload, dict):
        pairs = list(rtsps_payload.items())
    elif isinstance(rtsps_payload, list):
        pairs = [(d.get("quality") or d.get("name"), d.get("url")) for d in rtsps_payload]
    else:
        return []

    out = []
    for quality, url in pairs:
        if not url or not isinstance(url, str):
            continue
        suffix = _resolution_label(camera, quality)
        label = f"{cam_name} ({quality}"
        if suffix:
            label += f", {suffix}"
        label += ")"
        out.append({"name": label, "url": url})
    return out


def write_default_layout_if_needed(stream_count):
    """Write a hint config only when there isn't already a valid grid+tiles layout."""
    try:
        existing = json.load(open(CONFIG_FILE))
        if existing.get("grid") and existing.get("tiles"):
            return
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    if stream_count <= 4:
        layout = "2x2"
    elif stream_count <= 9:
        layout = "3x3"
    else:
        layout = "4x4"
    with open(CONFIG_FILE, "w") as f:
        json.dump({"layout": layout}, f, indent=2)


def main():
    p = argparse.ArgumentParser(description="Fetch UniFi Protect camera RTSPS URLs (official API).")
    p.add_argument("--list", action="store_true", help="Print JSON to stdout, do not write files.")
    p.add_argument("--debug", action="store_true", help="Log raw API responses to stderr.")
    p.add_argument("--enable", action="store_true",
                   help="Opt-in: enable RTSPS on cameras that have it disabled.")
    args = p.parse_args()

    session = requests.Session()
    try:
        cameras = list_cameras(session, debug=args.debug)
    except requests.HTTPError as e:
        sys.exit(f"[ERROR] Failed to list cameras: {e.response.status_code} {e.response.text[:200]}")
    except requests.RequestException as e:
        sys.exit(f"[ERROR] Network error talking to {API_BASE}: {e}")

    if args.debug:
        sys.stderr.write(f"[DEBUG] Found {len(cameras)} cameras in /cameras response\n")

    streams = []
    for cam in cameras:
        cam_id = cam.get("id")
        cam_name = cam.get("name") or cam.get("displayName") or cam_id
        if not cam_id:
            continue
        if cam.get("state") and cam.get("state") != "CONNECTED":
            sys.stderr.write(f"[INFO] Skipping {cam_name}: state={cam.get('state')}\n")
            continue

        rtsps = get_rtsps(session, cam_id, debug=args.debug)
        # "all qualities null" means RTSPS is disabled for this camera.
        if not _has_any_url(rtsps) and args.enable:
            sys.stderr.write(f"[INFO] Enabling RTSPS streams for {cam_name}…\n")
            try:
                rtsps = enable_rtsps(session, cam_id, debug=args.debug)
            except requests.HTTPError as e:
                sys.stderr.write(f"[WARN] Could not enable RTSPS for {cam_name}: "
                                 f"{e.response.status_code} {e.response.text[:200]}\n")
                continue
        if not _has_any_url(rtsps):
            sys.stderr.write(f"[INFO] Skipping {cam_name}: RTSPS not enabled (pass --enable to turn on)\n")
            continue

        cam_streams = streams_for(cam, rtsps)
        if not cam_streams:
            sys.stderr.write(f"[WARN] {cam_name}: rtsps-stream returned no usable URLs "
                             f"(payload: {json.dumps(rtsps)[:200]})\n")
        streams.extend(cam_streams)

    if args.list:
        print(json.dumps(streams, indent=2))
        return

    with open(CAMERA_FILE, "w") as f:
        json.dump(streams, f, indent=2)
    write_default_layout_if_needed(len(streams))
    print(f"[SUCCESS] Found {len(streams)} streams; wrote {CAMERA_FILE}")


if __name__ == "__main__":
    main()
