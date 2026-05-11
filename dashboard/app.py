"""Flask camera-management dashboard for unifi-viewport.

Lists cameras from the UniFi Protect Integration API, shows connection
state, lets you toggle RTSPS qualities per camera, and triggers a
regeneration of camera_urls.json on demand.
"""
import os
import secrets
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Allow `from dashboard.protect_client import ...` when launched as a script.
sys.path.insert(0, str(PROJECT_ROOT))
from dashboard.protect_client import ProtectClient  # noqa: E402

QUALITIES = ("high", "medium", "low")

app = Flask(__name__)
app.secret_key = os.environ.get("DASHBOARD_SECRET", secrets.token_hex(16))


def _client():
    return ProtectClient.from_env()


def _camera_rows(client):
    rows = []
    for cam in client.list_cameras():
        cam_id = cam.get("id")
        state = cam.get("state", "UNKNOWN")
        if state == "CONNECTED":
            rtsps = client.get_rtsps(cam_id)
        else:
            rtsps = {}
        rows.append({
            "id": cam_id,
            "name": cam.get("name") or "Unnamed",
            "model": cam.get("modelKey") or cam.get("type") or "",
            "mac": cam.get("mac") or "",
            "state": state,
            "enabled": {q: bool(rtsps.get(q)) for q in QUALITIES},
            "urls": {q: rtsps.get(q) for q in QUALITIES},
        })
    rows.sort(key=lambda r: r["name"].lower())
    return rows


@app.route("/")
def index():
    try:
        rows = _camera_rows(_client())
    except RuntimeError as e:
        return render_template("error.html", message=str(e)), 500
    return render_template("index.html", rows=rows, qualities=QUALITIES)


@app.route("/cameras/<camera_id>/rtsps", methods=["POST"])
def update_rtsps(camera_id):
    qualities = [q for q in request.form.getlist("qualities") if q in QUALITIES]
    try:
        _client().set_rtsps_qualities(camera_id, qualities)
        flash(f"Updated RTSPS qualities: {', '.join(qualities) if qualities else 'none (disabled)'}", "ok")
    except Exception as e:
        flash(f"Failed to update camera: {e}", "err")
    return redirect(url_for("index"))


@app.route("/refresh", methods=["POST"])
def refresh_streams():
    get_streams = PROJECT_ROOT / "get_streams.py"
    venv_py = PROJECT_ROOT / "venv" / "bin" / "python3"
    python = str(venv_py) if venv_py.exists() else "python3"
    proc = subprocess.run(
        [python, str(get_streams)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return render_template(
        "refresh.html",
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


@app.route("/health")
def health():
    return {"status": "ok"}


def main():
    port = int(os.environ.get("DASHBOARD_PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
