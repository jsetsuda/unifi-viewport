#!/bin/bash

CONFIG_FILE="viewport_config.json"
LOG_FILE="viewport.log"

JQ="/usr/bin/jq"
MPV="/usr/bin/mpv"
PYTHON="/usr/bin/python3"

# Start fresh log
echo "[INFO] Starting viewport.sh at $(date)" > "$LOG_FILE"

# Ensure DISPLAY is set (assume :0)
if [ -z "$DISPLAY" ]; then
  export DISPLAY=:0
fi

# Check required tools
for TOOL in "$JQ" "$MPV" "$PYTHON"; do
  if [ ! -x "$TOOL" ]; then
    echo "[ERROR] Required tool not found: $TOOL" >> "$LOG_FILE"
    exit 1
  fi
done

# Validate config file
if [ ! -f "$CONFIG_FILE" ] || ! $JQ empty "$CONFIG_FILE" >/dev/null 2>&1; then
  echo "[ERROR] Invalid or missing $CONFIG_FILE" >> "$LOG_FILE"
  exit 1
fi

# Attempt to read screen dimensions from X
WIDTH=$(xdpyinfo 2>/dev/null | awk '/dimensions:/ {print $2}' | cut -d'x' -f1)
HEIGHT=$(xdpyinfo 2>/dev/null | awk '/dimensions:/ {print $2}' | cut -d'x' -f2)

# Fallback if xdpyinfo fails
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

# Kill any existing MPV instances
pkill -9 mpv >> "$LOG_FILE" 2>&1

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

  # Convert rtsps://IP:7441 to rtsp://IP:7447
  URL=$(echo "$URL" | sed -E 's|rtsps://([^:/]+):7441|rtsp://\1:7447|')

  X=$((COL * WIN_W))
  Y=$((ROW * WIN_H))
  TITLE="tile_${ROW}_${COL}"

  echo "[INFO] Launching $NAME at ${X},${Y} as $TITLE" >> "$LOG_FILE"

  $MPV --no-border --geometry=${WIN_W}x${WIN_H}+${X}+${Y} \
       --profile=low-latency --untimed --rtsp-transport=tcp \
       --loop=inf --no-resume-playback \
       --no-cache --demuxer-readahead-secs=1 \
       --fps=24 --force-seekable=yes \
       --vo=gpu \
       --title="$TITLE" --no-audio "$URL" >> "$LOG_FILE" 2>&1 &
done

# Launch monitor if available
if [ -f "monitor_streams.py" ]; then
  echo "[INFO] Starting monitor_streams.py..." >> "$LOG_FILE"
  $PYTHON monitor_streams.py >> "$LOG_FILE" 2>&1 &
else
  echo "[WARN] monitor_streams.py not found; skipping monitor" >> "$LOG_FILE"
fi

wait
