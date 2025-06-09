#!/bin/bash
# viewport.sh
# Description: Launches tiled RTSP streams based on viewport_config.json
# First-boot forces layout selection; subsequent boots offer timed chooser

# --- Section: Setup paths and tools ---
CONFIG_FILE="viewport_config.json"
LOG_FILE="viewport.log"
FLAG_FILE="layout_updated.flag"

JQ="/usr/bin/jq"
MPV="/usr/bin/mpv"
PYTHON="/usr/bin/python3"
XDOTOOL="/usr/bin/xdotool"

# --- Section: Log start and environment ---
echo "[INFO] Starting viewport.sh at $(date)" > "$LOG_FILE"
if [ -z "$DISPLAY" ]; then export DISPLAY=:0; fi

# --- Section: Cleanup existing streams ---
echo "[INFO] Killing existing mpv streams..." >> "$LOG_FILE"
pkill -f "/usr/bin/mpv --no-border"
sleep 1

# --- Section: Tool validation ---
for TOOL in "$JQ" "$MPV" "$PYTHON" "$XDOTOOL"; do
  if [ ! -x "$TOOL" ]; then
    echo "[ERROR] Required tool not found: $TOOL" >> "$LOG_FILE"
    exit 1
  fi
done

# --- Section: Valid config check ---
check_valid_config() {
  # config must contain non-empty tiles array
  $JQ -e '.tiles and (.tiles | length > 0)' "$CONFIG_FILE" >/dev/null 2>&1
}

# --- Section: First-boot layout selection ---
FIRST_BOOT=0
if [ ! -f "$CONFIG_FILE" ] || ! check_valid_config; then
  echo "[WARN] Invalid or missing config, launching chooser (first boot)..." >> "$LOG_FILE"
  FIRST_BOOT=1
  rm -f "$FLAG_FILE"
  # blocking chooser until user saves
  $PYTHON layout_chooser.py >> "$LOG_FILE" 2>&1
  if [ ! -f "$CONFIG_FILE" ] || ! check_valid_config; then
    echo "[ERROR] Config still invalid after chooser." >> "$LOG_FILE"
    exit 1
  fi
fi

# --- Section: Timed chooser on subsequent boots ---
if [ "$FIRST_BOOT" -eq 0 ]; then
  echo "[INFO] Launching layout chooser with timeout..." >> "$LOG_FILE"
  rm -f "$FLAG_FILE"
  $PYTHON layout_chooser.py >> "$LOG_FILE" 2>&1 &
  CHOOSER_PID=$!
  TIMEOUT=10
  for i in $(seq 1 $TIMEOUT); do
    if [ -f "$FLAG_FILE" ]; then
      echo "[INFO] Layout updated by user." >> "$LOG_FILE"
      break
    fi
    sleep 1
  done
  if ps -p $CHOOSER_PID >/dev/null; then
    echo "[INFO] Chooser timed out, closing..." >> "$LOG_FILE"
    kill $CHOOSER_PID
    sleep 1
  fi
  rm -f "$FLAG_FILE"
fi

# --- Section: Detect display resolution ---
WIDTH=$($XDOTOOL getdisplaygeometry | awk '{print $1}')
HEIGHT=$($XDOTOOL getdisplaygeometry | awk '{print $2}')
if [ -z "$WIDTH" ] || [ -z "$HEIGHT" ]; then
  WIDTH=3840; HEIGHT=2160
  echo "[WARN] Using fallback resolution ${WIDTH}x${HEIGHT}" >> "$LOG_FILE"
fi

# --- Section: Parse grid layout ---
ROWS=$($JQ '.grid[0]' "$CONFIG_FILE")
COLS=$($JQ '.grid[1]' "$CONFIG_FILE")
WIN_W=$((WIDTH / COLS))
WIN_H=$((HEIGHT / ROWS))
export WIN_W WIN_H

# --- Section: Pi5 hardware decode ---
if grep -qi "raspberry pi 5" /proc/device-tree/model 2>/dev/null; then
  HWDEC="--hwdec=auto"
else
  HWDEC=""
fi

# --- Section: Launch stream tiles ---
$JQ -c '.tiles[]' "$CONFIG_FILE" | while read -r tile; do
  ROW=$(echo "$tile" | $JQ '.row')
  COL=$(echo "$tile" | $JQ '.col')
  W=$(echo "$tile" | $JQ '.w // 1')
  H=$(echo "$tile" | $JQ '.h // 1')
  NAME=$(echo "$tile" | $JQ -r '.name')
  URL=$(echo "$tile" | $JQ -r '.url')
  if [ -z "$URL" ] || [ "$URL" == "null" ]; then
    echo "[WARN] Skipping empty URL for $NAME" >> "$LOG_FILE"
    continue
  fi
  URL=$(echo "$URL" | sed -E 's|rtsps://([^:/]+):7441|rtsp://\1:7447|')
  TILE_W=$((WIN_W * W)); TILE_H=$((WIN_H * H))
  X=$((COL * WIN_W)); Y=$((ROW * WIN_H))
  TITLE="tile_${ROW}_${COL}"
  echo "[INFO] Launching $NAME at ${TILE_W}x${TILE_H}+${X}+${Y}" >> "$LOG_FILE"
  $MPV --no-border --geometry=${TILE_W}x${TILE_H}+${X}+${Y} \
       --profile=low-latency --untimed --no-correct-pts \
       --video-sync=desync --framedrop=vo \
       --rtsp-transport=tcp --loop=inf --no-resume-playback \
       --no-cache --demuxer-readahead-secs=1 --fps=24 \
       --force-seekable=yes --vo=gpu $HWDEC \
       --title="$TITLE" --no-audio --keep-open=yes \
       "$URL" >> "$LOG_FILE" 2>&1 &
done

# --- Section: Start health monitor ---
if [ -f monitor_streams.py ]; then
  echo "[INFO] Starting monitor_streams.py..." >> "$LOG_FILE"
  $PYTHON monitor_streams.py >> "$LOG_FILE" 2>&1 &
else
  echo "[WARN] monitor_streams.py not found; skipping" >> "$LOG_FILE"
fi

wait
