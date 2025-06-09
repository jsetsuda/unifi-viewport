#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# ── Configuration ─────────────────────────────────────────────────────────────
CONFIG="viewport_config.json"
LOG="viewport.log"
FLAG="layout_updated.flag"
CHOOSER="layout_chooser.py"
MONITOR="monitor_streams.py"

JQ="/usr/bin/jq"
MPV="/usr/bin/mpv"
PYTHON="/usr/bin/python3"
XDOTOOL="/usr/bin/xdotool"

export DISPLAY="${DISPLAY:-:0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# ── Logging ───────────────────────────────────────────────────────────────────
exec > >(tee -a "$LOG") 2>&1
echo "[INFO] Starting viewport.sh at $(date)"

# ── Kill any leftover mpv streams ─────────────────────────────────────────────
echo "[INFO] Killing existing mpv streams..."
pkill -f "$MPV --no-border" || true
sleep 1

# ── Verify required tools ─────────────────────────────────────────────────────
for TOOL in "$JQ" "$MPV" "$PYTHON" "$XDOTOOL"; do
  [[ -x $TOOL ]] || { echo "[ERROR] Missing tool: $TOOL"; exit 1; }
done

# ── Always launch the chooser (blocks here until you Save or timeout) ───────
rm -f "$FLAG" 2>/dev/null || true
echo "[INFO] Launching layout chooser…"
"$PYTHON" "$CHOOSER"

# ── Validate that chooser wrote a full grid+tiles config ────────────────────
if ! $JQ -e '.grid and .tiles and (.tiles|length>0)' "$CONFIG" &>/dev/null; then
  echo "[ERROR] viewport_config.json invalid or missing—aborting"
  exit 1
fi

# ── Detect display resolution ────────────────────────────────────────────────
if IFS=' ' read -r WIDTH HEIGHT <<< "$($XDOTOOL getdisplaygeometry)"; then
  echo "[INFO] Detected display geometry: ${WIDTH}×${HEIGHT}"
else
  WIDTH=3840; HEIGHT=2160
  echo "[WARN] Could not detect geometry—using fallback ${WIDTH}×${HEIGHT}"
fi

# ── Compute per-tile dimensions ──────────────────────────────────────────────
ROWS=$($JQ -r '.grid[0] // 1' "$CONFIG")
COLS=$($JQ -r '.grid[1] // 1' "$CONFIG")
(( ROWS<1 )) && ROWS=1
(( COLS<1 )) && COLS=1
WIN_W=$(( WIDTH  / COLS ))
WIN_H=$(( HEIGHT / ROWS ))
echo "[DEBUG] Grid: ${ROWS}×${COLS}, tile size: ${WIN_W}×${WIN_H}"

# ── Hardware decode hint for Pi 5 ────────────────────────────────────────────
HWDEC=""
grep -qi "raspberry pi 5" /proc/device-tree/model &>/dev/null && HWDEC="--hwdec=auto"

# ── Launch each tile in background ──────────────────────────────────────────
$JQ -c '.tiles[]' "$CONFIG" | while read -r tile; do
  read R C w h name url <<<"$(
    echo "$tile" | $JQ -r '[.row,.col,.w,.h,.name,.url]|@tsv'
  )"
  [[ $url && $url != "null" ]] || continue

  # convert RTSPS port
  url=$(sed -E 's|rtsps://([^:/]+):7441|rtsp://\1:7447|' <<<"$url")

  X=$(( C * WIN_W )) Y=$(( R * WIN_H ))
  TW=$(( w * WIN_W ))  TH=$(( h * WIN_H ))

  echo "[INFO] Launching \"$name\" @ ${TW}×${TH}+${X}+${Y}"
  "$MPV" \
    --no-border --geometry=${TW}x${TH}+${X}+${Y} \
    --profile=low-latency --untimed --no-correct-pts \
    --video-sync=desync --framedrop=vo --rtsp-transport=tcp \
    --loop=inf --no-resume-playback --no-cache \
    --demuxer-readahead-secs=1 --fps=24 --force-seekable=yes \
    --vo=gpu $HWDEC --title="tile_${R}_${C}" \
    --no-audio --keep-open=yes "$url" &
done

# ── Start health monitor if present ──────────────────────────────────────────
if [[ -x $MONITOR ]]; then
  echo "[INFO] Starting health monitor"
  "$PYTHON" "$MONITOR" &
else
  echo "[WARN] monitor_streams.py missing—skipping health monitor"
fi

wait
