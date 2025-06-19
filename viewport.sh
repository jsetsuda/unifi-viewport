#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# -----------------------------------------------------------------------------
# viewport.sh
# Unifi Viewport launcher: cleans up old streams, starts new ones
# -----------------------------------------------------------------------------

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG="$ROOT/viewport.log"
CONFIG="$ROOT/viewport_config.json"
CAMERA_JSON="$ROOT/camera_urls.json"
CHOOSER="$ROOT/layout_chooser.py"
MONITOR="$ROOT/monitor_streams.py"
MPV_BIN="mpv"
JQ_BIN="jq"
FLAG="$ROOT/layout_updated.flag"

# 1) Activate venv if available
if [[ -f "$ROOT/venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/venv/bin/activate"
  PYTHON="$(which python3)"
  echo "[INFO] Activated venv, using Python: $PYTHON"
else
  PYTHON="/usr/bin/python3"
  echo "[INFO] No venv found, using system Python: $PYTHON"
fi

# 2) Logging
exec > >(tee -a "$LOG") 2>&1
echo "[INFO] Starting viewport.sh at $(date)"

# 3) Handle recent layout update flag
if [[ -f "$FLAG" ]]; then
  echo "[INFO] Detected layout_updated.flag. Waiting to allow layout to stabilize..."
  sleep 3
  rm -f "$FLAG"
  echo "[INFO] layout_updated.flag cleared"
fi

# 4) Kill all existing mpv processes
echo "[INFO] Killing all existing mpv processes"
pkill -9 -f mpv || true
sleep 1

# 5) Kill ghost windows left behind from crashed/stale mpv
echo "[INFO] Searching for stale tile windows"
if command -v xdotool &>/dev/null; then
  TILE_WIDS=$(xdotool search --name '^tile_') || true
  for wid in $TILE_WIDS; do
    echo "[INFO] Killing stale window ID: $wid"
    xdotool windowkill "$wid"
    sleep 0.1
  done
elif command -v wmctrl &>/dev/null; then
  wmctrl -l | awk '$0 ~ /tile_/ {print $1}' | while read -r wid; do
    echo "[INFO] Killing stale window ID: $wid"
    wmctrl -ic "$wid"
    sleep 0.1
  done
else
  echo "[WARN] No xdotool or wmctrl available to kill stale windows"
fi

# 6) Check for required tools
for tool in "$JQ_BIN" "$MPV_BIN" python3 xrandr; do
  command -v "$tool" &>/dev/null || { echo "[ERROR] $tool missing"; exit 1; }
done

# 7) Fetch camera list if missing/empty
if [[ ! -f "$CAMERA_JSON" ]] || ! $JQ_BIN -e '. | length>0' "$CAMERA_JSON" &>/dev/null; then
  echo "[INFO] Fetching camera list"
  $PYTHON "$ROOT/get_streams.py" && echo "[INFO] camera_urls.json created" || echo "[WARN] get_streams.py failed"
fi

# 8) Run layout chooser only if --choose-layout is passed or no config
if [[ ! -f "$CONFIG" || "${1:-}" == "--choose-layout" ]]; then
  echo "[INFO] Launching layout chooser"
  set +e
  $PYTHON "$CHOOSER" >>"$LOG" 2>&1
  set -e
else
  echo "[INFO] Using existing layout config"
fi

# 9) Validate configuration
if ! $JQ_BIN -e '.grid and .tiles and (.tiles|length>0)' "$CONFIG" &>/dev/null; then
  echo "[ERROR] Invalid or missing $CONFIG; aborting"
  exit 1
fi

# 10) Detect display resolution
if command -v xrandr &>/dev/null; then
  XR_LINE=$(xrandr --current | grep " connected primary" || xrandr --current | grep " connected" | head -n1)
  if [[ $XR_LINE =~ ([0-9]+)x([0-9]+)\+ ]]; then
    W=${BASH_REMATCH[1]}; H=${BASH_REMATCH[2]}
  else
    echo "[WARN] Could not parse xrandr; defaulting 3840×2160"
    W=3840; H=2160
  fi
else
  echo "[WARN] xrandr missing; defaulting 3840×2160"
  W=3840; H=2160
fi
echo "[INFO] Resolution: ${W}×${H}"

# 11) Compute grid size
ROWS=$($JQ_BIN -r '.grid[0] // 1' "$CONFIG")
COLS=$($JQ_BIN -r '.grid[1] // 1' "$CONFIG")
(( ROWS<1 )) && ROWS=1
(( COLS<1 )) && COLS=1
TW=$(( W / COLS ))
TH=$(( H / ROWS ))
echo "[INFO] Grid: ${ROWS}×${COLS}, tile: ${TW}×${TH}"

# 12) HWDEC for Raspberry Pi 5
MODEL=$(tr -d '\0' < /proc/device-tree/model 2>/dev/null || echo "")
if [[ $MODEL == *"Raspberry Pi 5"* ]]; then
  HWDEC="--hwdec=v4l2m2m-copy"
else
  HWDEC=""
fi
echo "[INFO] HWDEC: ${HWDEC:-none}"

# 13) Read tiles into Bash array
mapfile -t TILES < <($JQ_BIN -c '.tiles[]' "$CONFIG")

# 14) Launch MPV for each tile
for tile in "${TILES[@]}"; do
  read -r R C Wm Hm name url < <(printf '%s' "$tile" | $JQ_BIN -r '[.row,.col,.w,.h,.name,.url] | @tsv')
  [[ -n $url && $url != "null" ]] || continue

  TITLE="tile_${R}_${C}"
  pkill -9 -f -- "--title=${TITLE}" || true

  url=$(printf '%s' "$url" | sed -E 's|rtsps://([^:/]+):7441|rtsp://\1:7447|')
  X=$(( C * TW )); Y=$(( R * TH ))
  WW=$(( Wm * TW )); HH=$(( Hm * TH ))

  echo "[INFO] Launching '$name' as ${TITLE} @ ${WW}×${HH}+${X}+${Y}"
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
    --fps=24 \
    --vo=gpu $HWDEC \
    --title="${TITLE}" \
    --no-audio \
    --mute=yes \
    --ao=null \
    --keep-open=yes \
    "$url" &
  sleep 0.2
done

# 15) Start monitor_streams.py in background
echo "[INFO] Starting monitor_streams.py"
$PYTHON "$MONITOR" &
wait
