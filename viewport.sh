#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# viewport.sh (one-step config)
#  - chooser writes full grid+tiles JSON
#  - launches streams directly from viewport_config.json

CONFIG_FILE="viewport_config.json"
LOG_FILE="viewport.log"
FLAG_FILE="layout_updated.flag"
CHOOSER_PY="layout_chooser.py"
MONITOR_PY="monitor_streams.py"

JQ="/usr/bin/jq"
MPV="/usr/bin/mpv"
PYTHON="/usr/bin/python3"
XDOTOOL="/usr/bin/xdotool"

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# ─── log everything ───────────────────────────────────────────────────────────
exec > >(tee -a "$LOG_FILE") 2>&1
echo "[INFO] Starting viewport.sh at $(date)"
: "${DISPLAY:=:0}"

# ─── kill old streams ────────────────────────────────────────────────────────
echo "[INFO] Killing existing mpv streams (if any)..."
pkill -f "$MPV --no-border" || true
sleep 1

# ─── validate tools ──────────────────────────────────────────────────────────
for TOOL in "$JQ" "$MPV" "$PYTHON" "$XDOTOOL"; do
  [[ -x $TOOL ]] || { echo "[ERROR] Missing tool: $TOOL"; exit 1; }
done

# ─── check for a full config (grid+tiles) ────────────────────────────────────
check_full_config(){
  $JQ -e '.grid and .tiles and (.tiles|length>0)' "$CONFIG_FILE" &>/dev/null
}

# ─── chooser (one‐step) ──────────────────────────────────────────────────────
FIRST_BOOT=0
if [[ ! -f $CONFIG_FILE ]] || ! check_full_config; then
  echo "[WARN] No valid config – launching chooser"
  FIRST_BOOT=1
  rm -f "$FLAG_FILE"
  "$PYTHON" "$CHOOSER_PY"
fi

# ─── timed chooser on subsequent boots ───────────────────────────────────────
if (( FIRST_BOOT == 0 )); then
  TIMEOUT=30
  echo "[INFO] Timed chooser (${TIMEOUT}s)..."
  rm -f "$FLAG_FILE"
  "$PYTHON" "$CHOOSER_PY" &
  CHOOSER_PID=$!
  for _ in $(seq 1 $TIMEOUT); do
    [[ -f $FLAG_FILE ]] && { echo "[INFO] Layout updated"; break; }
    sleep 1
  done
  if ps -p "$CHOOSER_PID" &>/dev/null; then
    echo "[INFO] Chooser timed out – killing"
    kill "$CHOOSER_PID"
    sleep 1
  fi
  rm -f "$FLAG_FILE"
fi

# ─── ensure we now have a full config ────────────────────────────────────────
if ! check_full_config; then
  echo "[ERROR] viewport_config.json still invalid; aborting"
  exit 1
fi

# ─── detect display resolution safely ────────────────────────────────────────
if IFS=' ' read -r WIDTH HEIGHT <<< "$($XDOTOOL getdisplaygeometry)"; then
  echo "[INFO] Detected display geometry: ${WIDTH}×${HEIGHT}"
else
  WIDTH=3840; HEIGHT=2160
  echo "[WARN] Could not detect geometry – using fallback ${WIDTH}×${HEIGHT}"
fi

# ─── parse grid with safe defaults ───────────────────────────────────────────
ROWS=$($JQ -r '.grid[0] // 1' "$CONFIG_FILE")
COLS=$($JQ -r '.grid[1] // 1' "$CONFIG_FILE")
(( ROWS<1 )) && ROWS=1
(( COLS<1 )) && COLS=1
WIN_W=$(( WIDTH / COLS ))
WIN_H=$(( HEIGHT / ROWS ))
echo "[DEBUG] Grid: ${ROWS}×${COLS}, tile size: ${WIN_W}×${WIN_H}"

# ─── hwdec hint (optional) ─────────────────────────────────────────────────
if grep -qi "raspberry pi 5" /proc/device-tree/model &>/dev/null; then
  HWDEC="--hwdec=auto"
else
  HWDEC=""
fi

# ─── launch each tile ────────────────────────────────────────────────────────
$JQ -c '.tiles[]' "$CONFIG_FILE" | while read -r tile; do
  read ROW COL W H NAME URL <<<"$(
    echo "$tile" | $JQ -r '[.row,.col,(.w//1),(.h//1),.name,.url]|@tsv'
  )"
  [[ $URL && $URL!="null" ]] || continue

  # sanitized RTSP
  URL=$(echo "$URL" | sed -E 's|rtsps://([^:/]+):7441|rtsp://\1:7447|')

  TW=$(( WIN_W * W )); TH=$(( WIN_H * H ))
  X=$(( COL * WIN_W )); Y=$(( ROW * WIN_H ))

  echo "[INFO] Launching \"$NAME\" @ ${TW}×${TH}+${X}+${Y}"
  "$MPV" --no-border --geometry=${TW}x${TH}+${X}+${Y} \
    --profile=low-latency --untimed --no-correct-pts \
    --video-sync=desync --framedrop=vo --rtsp-transport=tcp \
    --loop=inf --no-resume-playback --no-cache \
    --demuxer-readahead-secs=1 --fps=24 --force-seekable=yes \
    --vo=gpu $HWDEC --title="tile_${ROW}_${COL}" \
    --no-audio --keep-open=yes "$URL" &
done

# ─── start health monitor ───────────────────────────────────────────────────
if [[ -f $MONITOR_PY ]]; then
  echo "[INFO] Starting health monitor"
  "$PYTHON" "$MONITOR_PY" &
else
  echo "[WARN] Health monitor missing – skipping"
fi

wait
