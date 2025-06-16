#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# -----------------------------------------------------------------------------
# viewport.sh
#
# 1) Activate venv if present
# 2) Kill any stray mpv
# 3) Fetch camera list if needed
# 4) Run layout chooser (ignore non-zero exit)
# 5) Validate config
# 6) Detect resolution & grid math
# 7) Kill per-tile mpv and launch exactly one per tile
# 8) Start health monitor in background, then wait
# -----------------------------------------------------------------------------

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG="$ROOT/viewport.log"
CONFIG="$ROOT/viewport_config.json"
CAMERA_JSON="$ROOT/camera_urls.json"
CHOOSER="$ROOT/layout_chooser.py"
MONITOR="$ROOT/monitor_streams.py"
MPV_BIN="mpv"
JQ_BIN="jq"

# 1) Activate virtualenv if available
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

# 3) Aggressive global kill of any mpv
echo "[INFO] Killing all existing mpv processes (SIGKILL)"
pkill -9 -f mpv || true
sleep 1

# 4) Ensure required tools
for tool in "$JQ_BIN" "$MPV_BIN" python3 xrandr; do
  command -v "$tool" &>/dev/null || { echo "[ERROR] $tool not found"; exit 1; }
done

# 5) Fetch camera list if missing/empty
if [[ ! -f "$CAMERA_JSON" ]] || ! $JQ_BIN -e '. | length>0' "$CAMERA_JSON" &>/dev/null; then
  echo "[INFO] Fetching camera list"
  $PYTHON "$ROOT/get_streams.py" \
    && echo "[INFO] camera_urls.json created" \
    || echo "[WARN] get_streams.py failed"
fi

# 6) Run layout chooser (capture its output, but continue on error)
echo "[INFO] Launching layout chooser"
set +e
$PYTHON "$CHOOSER" >>"$LOG" 2>&1
CHOOSER_RC=$?
set -e
if (( CHOOSER_RC != 0 )); then
  echo "[WARN] layout_chooser.py exited $CHOOSER_RC; continuing"
fi

# 7) Validate config.json
if ! $JQ_BIN -e '.grid and .tiles and (.tiles|length>0)' "$CONFIG" &>/dev/null; then
  echo "[ERROR] Invalid or missing $CONFIG; dumping contents:" 
  cat "$CONFIG"
  exit 1
fi

# 8) Detect display resolution
if command -v xrandr &>/dev/null; then
  XR_LINE=$(xrandr --current | grep " connected primary" \
            || xrandr --current | grep " connected" | head -n1)
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

# 9) Compute grid and tile size
ROWS=$($JQ_BIN -r '.grid[0] // 1' "$CONFIG")
COLS=$($JQ_BIN -r '.grid[1] // 1' "$CONFIG")
(( ROWS<1 )) && ROWS=1
(( COLS<1 )) && COLS=1
TW=$(( W / COLS ))
TH=$(( H / ROWS ))
echo "[INFO] Grid: ${ROWS}×${COLS}, tile: ${TW}×${TH}"

# 10) Hardware decode hint (Pi5 / Pi4)
MODEL=$(tr -d '\0' < /proc/device-tree/model 2>/dev/null || echo "")
HWDEC=""
[[ $MODEL == *"Raspberry Pi 5"* ]] && HWDEC="--hwdec=v4l2m2m-copy"
[[ $MODEL == *"Raspberry Pi 4"* ]] && HWDEC="--hwdec=v4l2m2m"
echo "[INFO] HWDEC: ${HWDEC:-none}"

# 11) Read tiles into an array (no subshell)
mapfile -t TILES < <($JQ_BIN -c '.tiles[]' "$CONFIG")

# 12) For each tile: kill any old mpv with that title, then launch one
for tile in "${TILES[@]}"; do
  read -r R C Wm Hm name url < <(
    printf '%s' "$tile" | $JQ_BIN -r '[.row,.col,.w,.h,.name,.url] | @tsv'
  )
  [[ -n $url && $url != "null" ]] || continue

  TITLE="tile_${R}_${C}"
  echo "[INFO] Killing old $TITLE instances"
  pkill -9 -f "--title=${TITLE}" || true

  url=$(printf '%s' "$url" | sed -E 's|rtsps://([^:/]+):7441|rtsp://\1:7447|')
  X=$(( C * TW )); Y=$(( R * TH ))
  WW=$(( Wm * TW )); HH=$(( Hm * TH ))

  echo "[INFO] Launching '$name' as $TITLE @ ${WW}×${HH}+${X}+${Y}"
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
    --keep-open=yes \
    "$url" &

  sleep 0.2
done

# 13) Start the health monitor and wait
echo "[INFO] Starting monitor_streams.py"
$PYTHON "$MONITOR" &
wait
