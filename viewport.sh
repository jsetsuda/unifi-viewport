#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# ──────────────────────────────────────────────────────────────────────────────
# viewport.sh
#
# - Activates project venv if present
# - Fetches camera list if needed
# - Runs layout chooser
# - Detects resolution, computes grid & tile sizes
# - Spawns up to ROWS×COLS MPV tiles with staggered startup, hardware decode,
#   lower FPS, and scaling
# - Kills any previous MPV processes aggressively
# - Starts the combined health & stale-stream monitor
# ──────────────────────────────────────────────────────────────────────────────

# 1) Locate project root
ROOT="$(cd "$(dirname "$0")" && pwd)"

# 2) Activate virtualenv if present
if [[ -f "$ROOT/venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/venv/bin/activate"
  PYTHON="$(which python3)"
  echo "[INFO] Activated venv, using Python: $PYTHON"
else
  PYTHON="/usr/bin/python3"
  echo "[INFO] No venv found, using system Python: $PYTHON"
fi

CONFIG="$ROOT/viewport_config.json"
CAMERA_JSON="$ROOT/camera_urls.json"
LOG="$ROOT/viewport.log"
CHOOSER="$ROOT/layout_chooser.py"
MONITOR="$ROOT/monitor_streams.py"
MPV_BIN="/usr/bin/mpv"
JQ_BIN="/usr/bin/jq"

export DISPLAY="${DISPLAY:-:0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# ── Logging setup ─────────────────────────────────────────────────────────────
exec > >(tee -a "$LOG") 2>&1
echo "[INFO] Starting viewport.sh at $(date)"

# ── Kill any existing MPV streams aggressively ────────────────────────────────
echo "[INFO] Killing all existing mpv processes…"
pkill -f mpv || true
sleep 1

# ── Verify required commands ──────────────────────────────────────────────────
for cmd in "$JQ_BIN" "$MPV_BIN" "$PYTHON" xrandr; do
  if ! command -v "${cmd%% *}" &>/dev/null; then
    echo "[ERROR] Required tool '${cmd%% *}' not found"; exit 1
  fi
done

# ── Fetch camera list if missing ──────────────────────────────────────────────
if [[ ! -f "$CAMERA_JSON" ]] || ! $JQ_BIN -e '. | length>0' "$CAMERA_JSON" &>/dev/null; then
  echo "[INFO] No valid $CAMERA_JSON; fetching via API…"
  $PYTHON "$ROOT/get_streams.py" \
    && echo "[INFO] camera_urls.json created" \
    || echo "[ERROR] get_streams.py failed; chooser may be empty"
fi

# ── Run layout chooser ────────────────────────────────────────────────────────
echo "[INFO] Launching layout chooser…"
$PYTHON "$CHOOSER"

# ── Validate config ──────────────────────────────────────────────────────────
if ! $JQ_BIN -e '.grid and .tiles and (.tiles|length>0)' "$CONFIG" &>/dev/null; then
  echo "[ERROR] Invalid or missing $CONFIG; aborting"
  exit 1
fi

# ── Detect display resolution ─────────────────────────────────────────────────
if command -v xrandr &>/dev/null; then
  XR_LINE=$(xrandr --current | grep " connected primary" \
            || xrandr --current | grep " connected" | head -n1)
  if [[ $XR_LINE =~ ([0-9]+)x([0-9]+)\+ ]]; then
    W=${BASH_REMATCH[1]}; H=${BASH_REMATCH[2]}
    echo "[INFO] Detected resolution: ${W}×${H}"
  else
    echo "[WARN] Could not parse xrandr; defaulting to 3840×2160"
    W=3840; H=2160
  fi
else
  echo "[WARN] xrandr not available; defaulting to 3840×2160"
  W=3840; H=2160
fi

# ── Compute grid & tile sizes ─────────────────────────────────────────────────
ROWS=$($JQ_BIN -r '.grid[0] // 1' "$CONFIG")
COLS=$($JQ_BIN -r '.grid[1] // 1' "$CONFIG")
(( ROWS<1 )) && ROWS=1
(( COLS<1 )) && COLS=1
TW=$(( W / COLS ))
TH=$(( H / ROWS ))
MAX_STREAMS=$(( ROWS * COLS ))
echo "[DEBUG] Grid ${ROWS}×${COLS}, max streams: ${MAX_STREAMS}, tile size: ${TW}×${TH}"

# ── Select hardware decode backend ─────────────────────────────────────────────
HWDEC=""
if grep -qi "Raspberry Pi 5" /proc/device-tree/model 2>/dev/null; then
  HWDEC="--hwdec=v4l2m2m-copy"
  echo "[INFO] Using Pi 5 hwdec: v4l2m2m-copy"
elif grep -qi "Raspberry Pi 4" /proc/device-tree/model 2>/dev/null; then
  HWDEC="--hwdec=v4l2m2m"
  echo "[INFO] Using Pi 4 hwdec: v4l2m2m"
else
  echo "[INFO] No Pi-specific hwdec detected; using software decode"
fi

# ── Launch up to ROWS×COLS MPV tiles with stagger ─────────────────────────────
COUNT=0
$JQ_BIN -c '.tiles[]' "$CONFIG" | while read -r tile && (( COUNT < MAX_STREAMS )); do
  (( COUNT++ ))
  read -r R C Wm Hm name url <<<"$(
    echo "$tile" | $JQ_BIN -r '[.row,.col,.w,.h,.name,.url] | @tsv'
  )"
  # Skip empty or null URLs
  if [[ -z $url || $url == "null" ]]; then
    continue
  fi

  # Convert RTSPS → RTSP
  url=$(sed -E 's|rtsps://([^:/]+):7441|rtsp://\1:7447|' <<<"$url")

  X=$(( C * TW )); Y=$(( R * TH ))
  WW=$(( Wm * TW )); HH=$(( Hm * TH ))

  echo "[INFO] Launching \"$name\" @ ${WW}×${HH}+${X}+${Y}"
  "$MPV_BIN" \
    --no-border \
    --geometry=${WW}x${HH}+${X}+${Y} \
    --profile=low-latency \
    --untimed \
    --video-sync=desync \
    --framedrop=vo \
    --rtsp-transport=tcp \
    --loop=inf \
    --no-resume-playback \
    --no-cache \
    --demuxer-readahead-secs=1 \
    --fps=12 \
    --vf=scale=${WW}:${HH} \
    --vo=gpu $HWDEC \
    --title="tile_${R}_${C}" \
    --no-audio \
    --keep-open=yes \
    "$url" &

  # Stagger startup to avoid CPU spike
  sleep 0.2
done

# ── Start health & stale‐stream monitor ───────────────────────────────────────
if [[ -x "$MONITOR" ]]; then
  echo "[INFO] Starting monitor_streams.py"
  $PYTHON "$MONITOR" &
else
  echo "[WARN] $MONITOR missing; skipping monitor"
fi

wait
