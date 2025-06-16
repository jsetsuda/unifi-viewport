#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# ──────────────────────────────────────────────────────────────────────────────
# viewport.sh
# Description: Detects display resolution, fetches camera list if needed,
#              launches layout chooser, spawns MPV tiles, and starts health monitor.
# ──────────────────────────────────────────────────────────────────────────────

CONFIG="viewport_config.json"
CAMERA_JSON="camera_urls.json"
LOG="viewport.log"
CHOOSER="layout_chooser.py"
MONITOR="monitor_streams.py"

JQ="/usr/bin/jq"
MPV="/usr/bin/mpv"
PYTHON="/usr/bin/python3"

export DISPLAY="${DISPLAY:-:0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# ── Logging setup ─────────────────────────────────────────────────────────────
exec > >(tee -a "$LOG") 2>&1
echo "[INFO] Starting viewport.sh at $(date)"

# ── Kill any existing MPV streams ────────────────────────────────────────────
echo "[INFO] Killing existing mpv streams…"
pkill -f "$MPV --no-border" || true
sleep 1

# ── Check required tools ──────────────────────────────────────────────────────
for tool in jq mpv python3 xrandr; do
  if ! command -v $tool &>/dev/null; then
    echo "[ERROR] Required tool '$tool' not found"; exit 1
  fi
done

# ── Ensure we have a camera list ─────────────────────────────────────────────
if [[ ! -f "$CAMERA_JSON" ]] || ! jq -e '. | length > 0' "$CAMERA_JSON" >/dev/null 2>&1; then
  echo "[INFO] No valid $CAMERA_JSON found; fetching camera list…"
  "$PYTHON" get_streams.py || {
    echo "[ERROR] get_streams.py failed – layout chooser may have no cameras"
  }
fi

# ── Launch layout chooser ────────────────────────────────────────────────────
echo "[INFO] Launching layout chooser…"
"$PYTHON" "$CHOOSER"

# ── Validate the generated config ────────────────────────────────────────────
if ! $JQ -e '.grid and .tiles and (.tiles|length>0)' "$CONFIG" &>/dev/null; then
  echo "[ERROR] Invalid or missing $CONFIG; aborting"
  exit 1
fi

# ── Detect display resolution ─────────────────────────────────────────────────
if command -v xrandr &>/dev/null; then
  XR_LINE=$(xrandr --current | grep " connected primary" || xrandr --current | grep " connected" | head -n1)
  if [[ $XR_LINE =~ ([0-9]+)x([0-9]+)\+ ]]; then
    W=${BASH_REMATCH[1]}; H=${BASH_REMATCH[2]}
    echo "[INFO] Detected resolution via xrandr: ${W}×${H}"
  else
    echo "[WARN] Could not parse xrandr; defaulting to 3840×2160"
    W=3840; H=2160
  fi
else
  echo "[WARN] xrandr not available; defaulting to 3840×2160"
  W=3840; H=2160
fi

# ── Compute grid & tile sizes ─────────────────────────────────────────────────
ROWS=$($JQ -r '.grid[0] // 1' "$CONFIG")
COLS=$($JQ -r '.grid[1] // 1' "$CONFIG")
(( ROWS<1 )) && ROWS=1
(( COLS<1 )) && COLS=1
TW=$(( W / COLS ))
TH=$(( H / ROWS ))
echo "[DEBUG] Grid: ${ROWS}×${COLS}, tile size: ${TW}×${TH}"

# ── Hardware decode hint for Pi 5 ────────────────────────────────────────────
HWDEC=""
if grep -q "Raspberry Pi 5" /proc/device-tree/model 2>/dev/null; then
  HWDEC="--hwdec=auto"
fi

# ── Launch each tile ──────────────────────────────────────────────────────────
$JQ -c '.tiles[]' "$CONFIG" | while read -r tile; do
  read -r R C Wm Hm name url <<<"$(
    echo "$tile" | $JQ -r '[.row,.col,.w,.h,.name,.url] | @tsv'
  )"
  [[ $url && $url != "null" ]] || continue

  # Convert secure→plain RTSP if needed
  url=$(sed -E 's|rtsps://([^:/]+):7441|rtsp://\1:7447|' <<<"$url")

  X=$(( C * TW ))
  Y=$(( R * TH ))
  WW=$(( Wm * TW ))
  HH=$(( Hm * TH ))

  echo "[INFO] Launching \"$name\" @ ${WW}×${HH}+${X}+${Y}"
  "$MPV" \
    --no-border --geometry=${WW}x${HH}+${X}+${Y} \
    --profile=low-latency --untimed --no-correct-pts \
    --video-sync=desync --framedrop=vo --rtsp-transport=tcp \
    --loop=inf --no-resume-playback --no-cache \
    --demuxer-readahead-secs=1 --fps=24 --force-seekable=yes \
    --vo=gpu $HWDEC --title="tile_${R}_${C}" --no-audio --keep-open=yes \
    "$url" &
done

# ── Start health & stale-stream monitor ────────────────────────────────────────
if [[ -x "$MONITOR" ]]; then
  echo "[INFO] Starting monitor_streams.py"
  "$PYTHON" "$MONITOR" &
else
  echo "[WARN] $MONITOR missing – skipping health monitor"
fi

wait
