#!/bin/bash

CONFIG_FILE="viewport_config.json"
LOG_FILE="viewport.log"

JQ="/usr/bin/jq"
MPV="/usr/bin/mpv"
PYTHON="/usr/bin/python3"

echo "[INFO] Starting viewport.sh at $(date)" > "$LOG_FILE"

if [ -z "$DISPLAY" ]; then
  export DISPLAY=:0
fi

for TOOL in "$JQ" "$MPV" "$PYTHON"; do
  if [ ! -x "$TOOL" ]; then
    echo "[ERROR] Required tool not found: $TOOL" >> "$LOG_FILE"
    exit 1
  fi
done

if [ ! -f "$CONFIG_FILE" ] || ! $JQ empty "$CONFIG_FILE" >/dev/null 2>&1; then
  echo "[ERROR] Invalid or missing $CONFIG_FILE" >> "$LOG_FILE"
  exit 1
fi

WIDTH=$(xdpyinfo 2>/dev/null | awk '/dimensions:/ {print $2}' | cut -d'x' -f1)
HEIGHT=$(xdpyinfo 2>/dev/null | awk '/dimensions:/ {print $2}' | cut -d'x' -f2)

if [ -z "$WIDTH" ] || [ -z "$HEIGHT" ]; then
  WIDTH=3840
  HEIGHT=2160
  echo "[WARN] Falling back to default resolution: ${WIDTH}x${HEIGHT}" >> "$LOG_FILE"
fi

ROWS=$($JQ '.grid[0]' "$CONFIG_FILE")
COLS=$($JQ '.grid[1]' "$CONFIG_FILE")

if ! [[ "$ROWS" =~ ^[0-9]+$ ]] || ! [[ "$COLS" =~ ^[0-9]+$ ]] || [ "$ROWS" -eq 0 ] || [ "$COLS" -eq 0 ]; then
  echo "[ERROR] Invalid grid in config: ROWS=$ROWS, COLS=$COLS" >> "$LOG_FILE"
  exit 1
fi

WIN_W=$((WIDTH / COLS))
WIN_H=$((HEIGHT / ROWS))

export WIN_W
export WIN_H

# Kill old mpv
pkill -9 mpv >> "$LOG_FILE" 2>&1

# Detect if on Raspberry Pi 5
IS_PI5=$(grep -i "raspberry pi 5" /proc/device-tree/model 2>/dev/null)
if [ -n "$IS_PI5" ]; then
  echo "[INFO] Raspberry Pi 5 detected, enabling hardware decoding." >> "$LOG_FILE"
  HWDEC="--hwdec=auto"
else
  HWDEC=""
fi

# Launch each stream
$JQ -c '.tiles[]' "$CONFIG_FILE" | while read -r tile; do
  ROW=$(echo "$tile" | $JQ '.row')
  COL=$(echo "$tile" | $JQ '.col')
  NAME=$(echo "$tile" | $JQ -r '.name')
  URL=$(echo "$tile" | $JQ -r '.url')

  if [ -z "$URL" ] || [ "$URL" == "null" ]; then
    echo "[WARN] Skipping null or empty URL at ($ROW,$COL) [$NAME]" >> "$LOG_FILE"
    continue
  fi

  URL=$(echo "$URL" | sed -E 's|rtsps://([^:/]+):7441|rtsp://\1:7447|')

  X=$((COL * WIN_W))
  Y=$((ROW * WIN_H))
  TITLE="tile_${ROW}_${COL}"

  echo "[INFO] Launching $NAME ($URL) (${WIN_W}x${WIN_H}) at ${X},${Y} as $TITLE" >> "$LOG_FILE"

  $MPV --no-border --geometry=${WIN_W}x${WIN_H}+${X}+${Y} \
     --profile=low-latency --untimed --no-correct-pts \
     --video-sync=desync --framedrop=vo \
     --rtsp-transport=tcp \
     --loop=inf --no-resume-playback \
     --no-cache --demuxer-readahead-secs=1 \
     --fps=24 --force-seekable=yes \
     --vo=gpu $HWDEC \
     --title="$TITLE" --no-audio \
     --length=inf --keep-open=yes \
     "$URL" >> "$LOG_FILE" 2>&1 &

done

# Launch stream monitor
if [ -f "monitor_streams.py" ]; then
  echo "[INFO] Starting monitor_streams.py..." >> "$LOG_FILE"
  $PYTHON monitor_streams.py >> "$LOG_FILE" 2>&1 &
else
  echo "[WARN] monitor_streams.py not found; skipping monitor" >> "$LOG_FILE"
fi

wait
