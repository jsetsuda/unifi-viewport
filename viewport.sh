#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

CONFIG="viewport_config.json"
LOG="viewport.log"
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

# ── Kill leftover MPV windows ────────────────────────────────────────────────
echo "[INFO] Killing existing mpv streams…"
pkill -f "$MPV --no-border" || true
sleep 1

# ── Check dependencies ───────────────────────────────────────────────────────
for tool in jq mpv python3 xdotool; do
  command -v $tool >/dev/null || { echo "[ERROR] $tool missing"; exit 1; }
done

# ── Always launch chooser in the foreground ─────────────────────────────────
echo "[INFO] Launching layout chooser…"
"$PYTHON" "$CHOOSER"

# ── Validate that the chooser wrote a proper grid+tiles JSON ────────────────
if ! $JQ -e '.grid and .tiles and (.tiles|length>0)' "$CONFIG" &>/dev/null; then
  echo "[ERROR] Invalid or missing $CONFIG; aborting"
  exit 1
fi

# ── Get display size ────────────────────────────────────────────────────────
if IFS=' ' read -r W H <<< "$($XDOTOOL getdisplaygeometry)"; then
  echo "[INFO] Detected display geometry: ${W}×${H}"
else
  W=3840; H=2160
  echo "[WARN] Using fallback ${W}×${H}"
fi

# ── Compute per-tile size ───────────────────────────────────────────────────
ROWS=$($JQ -r '.grid[0] // 1' "$CONFIG")
COLS=$($JQ -r '.grid[1] // 1' "$CONFIG")
(( ROWS<1 )) && ROWS=1
(( COLS<1 )) && COLS=1
TW=$(( W  / COLS ))
TH=$(( H  / ROWS ))
echo "[DEBUG] Grid: ${ROWS}×${COLS}, tile size: ${TW}×${TH}"

# ── Hardware decode hint for Pi 5 ──────────────────────────────────────────
HWDEC=""
grep -qi "raspberry pi 5" /proc/device-tree/model &>/dev/null && HWDEC="--hwdec=auto"

# ── Launch each tile ────────────────────────────────────────────────────────
$JQ -c '.tiles[]' "$CONFIG" | while read -r tile; do
  read R C w h name url <<<"$(
    echo "$tile" | $JQ -r '[.row,.col,.w,.h,.name,.url]|@tsv'
  )"
  [[ $url && $url != "null" ]] || continue

  # convert secure→plain RTSP
  url=$(sed -E 's|rtsps://([^:/]+):7441|rtsp://\1:7447|' <<<"$url")

  X=$(( C * TW )) Y=$(( R * TH ))
  WW=$(( w * TW ))  HH=$(( h * TH ))

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

# ── Start health monitor if available ───────────────────────────────────────
if [[ -x $MONITOR ]]; then
  echo "[INFO] Starting health monitor"
  "$PYTHON" "$MONITOR" &
else
  echo "[WARN] $MONITOR missing – skipping health monitor"
fi

wait
