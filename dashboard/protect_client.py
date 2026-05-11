"""Thin client for the UniFi Protect Integration API.

Used by the dashboard for camera listing and per-quality RTSPS toggling.
get_streams.py has its own (CLI-shaped) implementation; we keep the
overlap intentional and small rather than coupling the two.
"""
import os
import time

import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

urllib3.disable_warnings(InsecureRequestWarning)


class ProtectClient:
    def __init__(self, host, api_key, verify_ssl=False):
        self.api_base = f"{host.rstrip('/')}/proxy/protect/integration/v1"
        self.session = requests.Session()
        self.session.headers["X-API-KEY"] = api_key
        self.session.headers["Accept"] = "application/json"
        self.verify_ssl = verify_ssl

    @classmethod
    def from_env(cls):
        host = (os.environ.get("UFP_HOST") or "").strip()
        key = (os.environ.get("UFP_API_KEY") or "").strip()
        if not host or not key or key == "your_api_key_here":
            raise RuntimeError("UFP_HOST and UFP_API_KEY must be set in .env")
        verify = os.environ.get("UFP_VERIFY_SSL", "false").lower() in ("1", "true", "yes")
        return cls(host, key, verify_ssl=verify)

    def _request(self, method, path, body=None):
        # NVR rate-limits to ~10 req/s; back off on 429.
        url = f"{self.api_base}{path}"
        delay = 0.2
        last = None
        for _ in range(5):
            headers = {}
            if body is not None:
                headers["Content-Type"] = "application/json"
            last = self.session.request(method, url, json=body, headers=headers,
                                        verify=self.verify_ssl, timeout=15)
            if last.status_code != 429:
                return last
            time.sleep(delay)
            delay *= 2
        return last

    def list_cameras(self):
        r = self._request("GET", "/cameras")
        r.raise_for_status()
        return r.json()

    def get_rtsps(self, camera_id):
        r = self._request("GET", f"/cameras/{camera_id}/rtsps-stream")
        if r.status_code == 404:
            return {}
        r.raise_for_status()
        return r.json() or {}

    def set_rtsps_qualities(self, camera_id, qualities):
        """Set which RTSPS qualities are enabled. Pass [] to disable all."""
        r = self._request("POST", f"/cameras/{camera_id}/rtsps-stream",
                          body={"qualities": list(qualities)})
        r.raise_for_status()
        return r.json() if r.text else {}
