#!/bin/bash

CONFIG_FILE="viewport_config.json"
LOG_FILE="viewport.log"

JQ="/usr/bin/jq"
MPV="/usr/bin/mpv"

# Clear old logs
echo "[INFO] Starting viewport.sh at $(date)" > "$LOG_FILE"

# Ensure DISPLAY is set
if [ -z "$DISPLAY" ]; then
  echo "[ERROR] DISPLAY not set. Are you running inside a GUI session?" >> "$LOG_FILE"
  exit 1
fi

# Check for required tools
if [ ! -x "$JQ" ]; then
  echo "[ERROR] jq not found. Install with: sudo apt install -y jq" >> "$LOG_FILE"
  exit 1
fi

if [ ! -x "$MPV" ]; then
  echo "[ERROR] mpv not found. Install with: sudo apt install -y mpv" >> "$LOG_FILE"
  exit 1
fi

# Validate config
if [ ! -f "$CONFIG_FILE" ] || ! $JQ empty "$CONFIG_FILE" >/dev/null 2>&1; then
  echo "[ERROR] Invalid or missing $CONFIG_FILE" >> "$LOG_FILE"
  exit 1
fi

# Get screen dimensions
WIDTH=$(xdpyinfo | awk '/dimensions:/ {print $2}' | cut -d'x' -f1)
HEIGHT=$(xdpyinfo | awk '/dimensions:/ {print $2}' | cut -d'x' -f2)

export WIDTH
export HEIGHT

ROWS=$($JQ '.grid[0]' "$CONFIG_FILE")
COLS=$($JQ '.grid[1]' "$CONFIG_FILE")

# Validate grid
if ! [[ "$ROWS" =~ ^[0-9]+$ ]] || ! [[ "$COLS" =~ ^[0-9]+$ ]] || [ "$ROWS" -eq 0 ] || [ "$COLS" -eq 0 ]; then
  echo "[ERROR] Invalid grid size in config: ROWS=$ROWS, COLS=$COLS" >> "$LOG_FILE"
  exit 1
fi

WIN_W=$((WIDTH / COLS))
WIN_H=$((HEIGHT / ROWS))

# Kill existing mpv windows
pkill -9 mpv >> "$LOG_FILE" 2>&1

# Launch each stream
$JQ -c '.tiles[]' "$CONFIG_FILE" | while read -r tile; do
  ROW=$(echo "$tile" | $JQ '.row')
  COL=$(echo "$tile" | $JQ '.col')
  NAME=$(echo "$tile" | $JQ -r '.name')
  URL=$(echo "$tile" | $JQ -r '.url')

  if [ -z "$URL" ] || [ "$URL" == "null" ]; then
    echo "[WARN] Skipping empty or null URL for tile: $NAME" >> "$LOG_FILE"
    continue
  fi

  # Replace rtsps with rtsp to avoid TLS errors
  URL=${URL//rtsps:/rtsp:}

  X=$((COL * WIN_W))
  Y=$((ROW * WIN_H))
  TITLE="tile_${ROW}_${COL}"

  echo "[INFO] Launching $NAME at ${X},${Y} as $TITLE" >> "$LOG_FILE"

  $MPV --no-border --geometry=${WIN_W}x${WIN_H}+${X}+${Y} \
     --profile=low-latency --untimed --rtsp-transport=tcp \
     --loop=inf --no-resume-playback \
     --no-cache --demuxer-readahead-secs=1 \
     --fps=15 --force-seekable=yes \
     --title="$TITLE" --no-audio "$URL" >> "$LOG_FILE" 2>&1 &

done

# Start stream monitor
python3 monitor_streams.py >> "$LOG_FILE" 2>&1 &

wait
