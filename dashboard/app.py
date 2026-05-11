"""Flask camera-management dashboard for unifi-viewport.

Lists cameras from the UniFi Protect Integration API, shows connection
state, lets you toggle RTSPS qualities per camera, and triggers a
regeneration of camera_urls.json on demand.
"""
import json
import os
import secrets
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Allow `from dashboard.protect_client import ...` when launched as a script.
sys.path.insert(0, str(PROJECT_ROOT))
from dashboard.protect_client import ProtectClient  # noqa: E402
import layouts  # noqa: E402  (shared module at PROJECT_ROOT)

QUALITIES = ("high", "medium", "low")

app = Flask(__name__)
app.secret_key = os.environ.get("DASHBOARD_SECRET", secrets.token_hex(16))


def _client():
    return ProtectClient.from_env()


def _regenerate_camera_urls():
    """Run get_streams.py against the kiosk dir and flash a one-line summary."""
    get_streams = PROJECT_ROOT / "get_streams.py"
    venv_py = PROJECT_ROOT / "venv" / "bin" / "python3"
    python = str(venv_py) if venv_py.exists() else "python3"
    proc = subprocess.run(
        [python, str(get_streams)],
        cwd=str(_kiosk_root()),
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        flash(f"Auto-regenerate failed (rc={proc.returncode}): "
              f"{(proc.stderr or '').strip()[:200]}", "err")
        return
    import re
    m = re.search(r"Found (\d+) streams?", proc.stdout)
    n = m.group(1) if m else "?"
    flash(f"camera_urls.json regenerated — {n} stream(s).", "ok")


KIOSK_SERVICE = "unifi-viewport.service"


def _kiosk_root():
    """Discover the kiosk service's WorkingDirectory at runtime.

    Lets the dashboard manage the live kiosk even when the dashboard is
    deployed from a different checkout. Falls back to the dashboard's own
    project root if systemctl can't tell us.
    """
    try:
        proc = subprocess.run(
            ["systemctl", "show", KIOSK_SERVICE, "-p", "WorkingDirectory", "--value"],
            capture_output=True, text=True, timeout=5,
        )
        path = (proc.stdout or "").strip()
        if path:
            return Path(path)
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    return PROJECT_ROOT


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


@app.route("/cameras/save", methods=["POST"])
def save_cameras():
    """Apply the checked-quality state for one or all cameras at once.

    Form fields:
      camera_ids — repeated; the cameras under management on the form
      q_<id>     — repeated; the qualities checked for that camera
      only       — optional; if present, only that camera is saved
    """
    only = (request.form.get("only") or "").strip()
    camera_ids = [only] if only else request.form.getlist("camera_ids")
    if not camera_ids:
        flash("No cameras submitted.", "err")
        return redirect(url_for("index"))

    client = _client()
    saved, errors = 0, []
    for cam_id in camera_ids:
        if not cam_id:
            continue
        qualities = [q for q in request.form.getlist(f"q_{cam_id}") if q in QUALITIES]
        try:
            client.set_rtsps_qualities(cam_id, qualities)
            saved += 1
        except Exception as e:
            errors.append(f"{cam_id[:8]}…: {e}")

    if errors:
        flash(f"Saved {saved} camera(s); {len(errors)} error(s): " + " | ".join(errors[:3]), "err")
    elif only:
        flash("Saved camera.", "ok")
    else:
        flash(f"Saved {saved} camera(s).", "ok")

    if saved:
        _regenerate_camera_urls()
    return redirect(url_for("index"))


@app.route("/cameras/<camera_id>/rtsps/enable", methods=["POST"])
def enable_one(camera_id):
    try:
        _client().set_rtsps_qualities(camera_id, list(QUALITIES))
        flash(f"Enabled all RTSPS qualities ({camera_id[:8]}…)", "ok")
        _regenerate_camera_urls()
    except Exception as e:
        flash(f"Failed to enable: {e}", "err")
    return redirect(url_for("index"))


@app.route("/cameras/<camera_id>/rtsps/disable", methods=["POST"])
def disable_one(camera_id):
    try:
        _client().set_rtsps_qualities(camera_id, [])
        flash(f"Disabled RTSPS ({camera_id[:8]}…)", "ok")
        _regenerate_camera_urls()
    except Exception as e:
        flash(f"Failed to disable: {e}", "err")
    return redirect(url_for("index"))


def _bulk_set_qualities(target_qualities, verb):
    try:
        client = _client()
        cameras = client.list_cameras()
    except Exception as e:
        flash(f"Failed to list cameras: {e}", "err")
        return

    touched, skipped, errors = 0, 0, []
    for cam in cameras:
        if cam.get("state") != "CONNECTED":
            skipped += 1
            continue
        try:
            client.set_rtsps_qualities(cam["id"], list(target_qualities))
            touched += 1
        except Exception as e:
            errors.append(f"{cam.get('name') or cam.get('id')}: {e}")

    parts = [f"{verb} RTSPS on {touched} camera(s)"]
    if skipped:
        parts.append(f"{skipped} offline skipped")
    msg = "; ".join(parts)
    if errors:
        flash(msg + f"; {len(errors)} error(s): " + " | ".join(errors[:3]), "err")
    else:
        flash(msg, "ok")


@app.route("/cameras/enable-all", methods=["POST"])
def enable_all():
    _bulk_set_qualities(QUALITIES, "Enabled")
    _regenerate_camera_urls()
    return redirect(url_for("index"))


@app.route("/cameras/disable-all", methods=["POST"])
def disable_all():
    _bulk_set_qualities([], "Disabled")
    _regenerate_camera_urls()
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


@app.route("/restart-kiosk", methods=["POST"])
def restart_kiosk():
    """Reset the saved layout and restart the kiosk service, so the next
    boot of viewport.sh comes up on a clean layout-chooser screen."""
    kiosk_root = _kiosk_root()
    config = kiosk_root / "viewport_config.json"

    backup = None
    if config.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = kiosk_root / f"viewport_config.{ts}.bak"
        try:
            shutil.move(str(config), str(backup))
        except OSError as e:
            return render_template(
                "restart.html",
                kiosk_root=str(kiosk_root),
                backup_path=None,
                returncode=None,
                stdout="",
                stderr=f"Could not back up {config}: {e}",
            ), 500

    proc = subprocess.run(
        ["sudo", "-n", "/bin/systemctl", "restart", KIOSK_SERVICE],
        capture_output=True, text=True, timeout=30,
    )
    return render_template(
        "restart.html",
        kiosk_root=str(kiosk_root),
        backup_path=str(backup) if backup else None,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def _load_cameras(kiosk_root):
    """Read camera_urls.json from the kiosk dir; return [{name, url}, ...]."""
    p = kiosk_root / "camera_urls.json"
    if not p.exists():
        return []
    try:
        cams = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    return [{"name": c["name"], "url": c.get("url", "")}
            for c in cams if isinstance(c, dict) and "name" in c]


def _load_current_layout(kiosk_root):
    p = kiosk_root / "viewport_config.json"
    if not p.exists():
        return None
    try:
        cfg = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if cfg.get("grid") and cfg.get("tiles"):
        return cfg
    return None


@app.route("/layout", methods=["GET"])
def layout_page():
    kiosk_root = _kiosk_root()
    cameras = _load_cameras(kiosk_root)
    current = _load_current_layout(kiosk_root)

    # Determine which layout to render: explicit ?layout=X wins; otherwise
    # default to whatever's currently saved (the dashboard now records the
    # layout name when it pushes a config; legacy configs fall back to a
    # WxH derived from the saved grid).
    layout_name = request.args.get("layout")
    if not layout_name and current:
        layout_name = current.get("layout") or f"{current['grid'][0]}x{current['grid'][1]}"
    active_name = (current.get("layout") if current else None) or (
        f"{current['grid'][0]}x{current['grid'][1]}" if current else None
    )

    expanded = layouts.expand(layout_name) if layout_name else None
    prefill = {}
    if expanded and current and current.get("tiles"):
        if len(current["tiles"]) == len(expanded["tiles"]):
            for i, t in enumerate(current["tiles"]):
                if t.get("name"):
                    prefill[i] = t["name"]

    return render_template(
        "layout.html",
        kiosk_root=str(kiosk_root),
        options=layouts.ALL_OPTIONS,
        cameras=cameras,
        layout_name=layout_name,
        active_name=active_name,
        expanded=expanded,
        prefill=prefill,
        current=current,
    )


@app.route("/layout", methods=["POST"])
def save_layout():
    kiosk_root = _kiosk_root()
    layout_name = (request.form.get("layout") or "").strip()
    expanded = layouts.expand(layout_name)
    if not expanded:
        flash(f"Unknown layout: {layout_name!r}", "err")
        return redirect(url_for("layout_page"))

    cameras = _load_cameras(kiosk_root)
    cam_by_name = {c["name"]: c["url"] for c in cameras}

    tile_picks = request.form.getlist("tile_cam")
    if len(tile_picks) != len(expanded["tiles"]):
        flash(f"Got {len(tile_picks)} tile picks, layout needs {len(expanded['tiles'])}", "err")
        return redirect(url_for("layout_page", layout=layout_name))

    for tile, picked in zip(expanded["tiles"], tile_picks):
        if not picked:
            flash("Every tile needs a camera assigned.", "err")
            return redirect(url_for("layout_page", layout=layout_name))
        if picked not in cam_by_name:
            flash(f"Camera not found in camera_urls.json: {picked!r}. Run Regenerate first.", "err")
            return redirect(url_for("layout_page", layout=layout_name))
        tile["name"] = picked
        tile["url"] = cam_by_name[picked]

    # Record the layout name so the manager UI can highlight it later.
    expanded["layout"] = layout_name

    config_path = kiosk_root / "viewport_config.json"
    try:
        config_path.write_text(json.dumps(expanded, indent=2))
        (kiosk_root / "layout_updated.flag").touch()
        # Tell layout_chooser.py to skip its GUI on next launch — the kiosk
        # should boot straight into the streams with the pushed layout.
        (kiosk_root / "layout_skip_chooser.flag").touch()
    except OSError as e:
        flash(f"Failed to write {config_path}: {e}", "err")
        return redirect(url_for("layout_page", layout=layout_name))

    flash(f"Saved {len(expanded['tiles'])}-tile layout → {config_path}", "ok")

    if request.form.get("restart"):
        proc = subprocess.run(
            ["sudo", "-n", "/bin/systemctl", "restart", KIOSK_SERVICE],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0:
            flash("Kiosk service restarted; new layout is loading.", "ok")
        else:
            flash(f"Kiosk restart failed (rc={proc.returncode}): {(proc.stderr or '').strip()[:200]}", "err")

    return redirect(url_for("layout_page", layout=layout_name))


@app.route("/health")
def health():
    return {"status": "ok"}


def main():
    port = int(os.environ.get("DASHBOARD_PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
