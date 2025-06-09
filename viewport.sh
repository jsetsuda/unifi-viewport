#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

CONFIG="viewport_config.json"
LOG="viewport.log"
CHOOSER_PY="layout_chooser.py"
MONITOR_PY="monitor_streams.py"

JQ="/usr/bin/jq"
MPV="/usr/bin/mpv"
PYTHON="/usr/bin/python3"
XDOTOOL="/usr/bin/xdotool"

export DISPLAY="${DISPLAY:-:0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

exec > >(tee -a "$LOG") 2>&1
echo "[INFO] Starting viewport.sh at $(date)"

echo "[INFO] Killing existing mpv streams (if any)…"
pkill -f "$MPV --no-border" || true
sleep 1

for TOOL in "$JQ" "$MPV" "$PYTHON" "$XDOTOOL"; do
  [[ -x $TOOL ]] || { echo "[ERROR] Missing tool: $TOOL"; exit 1; }
done

# ── Only “valid” if every tile has a non-empty URL ─────────────────────────
check_full_config(){
  $JQ -e '
    .grid and
    (.tiles|length>0) and
    (.tiles|all(.url != null and .url != ""))
  ' "$CONFIG" &>/dev/null
}

# ── If missing or invalid → **block** in the chooser until you hit Save ────
if [[ ! -f $CONFIG ]] || ! check_full_config; then
  echo "[WARN] No valid config – launching layout chooser"
  rm -f layout_updated.flag 2>/dev/null || true
  "$PYTHON" "$CHOOSER_PY"
fi

# ── Bail if they somehow still didn’t write URLs ───────────────────────────
if ! check_full_config; then
  echo "[ERROR] viewport_config.json still invalid; aborting"
  exit 1
fi

# ── Detect screen size ─────────────────────────────────────────────────────
if IFS=' ' read -r W H <<< "$($XDOTOOL getdisplaygeometry)"; then
  echo "[INFO] Detected geometry: ${W}×${H}"
else
  W=3840; H=2160
  echo "[WARN] Using fallback ${W}×${H}"
fi

ROWS=$($JQ -r '.grid[0] // 1' "$CONFIG")
COLS=$($JQ -r '.grid[1] // 1' "$CONFIG")
(( ROWS<1 )) && ROWS=1
(( COLS<1 )) && COLS=1
TW=$(( W / COLS ))
TH=$(( H / ROWS ))
echo "[DEBUG] Grid: ${ROWS}×${COLS}, tile: ${TW}×${TH}"

HWDEC=""
grep -qi "raspberry pi 5" /proc/device-tree/model && HWDEC="--hwdec=auto"

# ── Launch each tile ───────────────────────────────────────────────────────
$JQ -c '.tiles[]' "$CONFIG" | while read -r tile; do
  read R C w h name url <<<"$(
    echo "$tile" | $JQ -r '[.row,.col,.w,.h,.name,.url]|@tsv'
  )"
  [[ $url ]] || continue

  # sanitize secure→plain RTSP
  url=$(sed -E 's|rtsps://([^:/]+):7441|rtsp://\1:7447|' <<<"$url")

  X=$(( C * TW )); Y=$(( R * TH ))
  WW=$(( w * TW )); HH=$(( h * TH ))

  echo "[INFO] Launching \"$name\" @ ${WW}×${HH}+${X}+${Y}"
  "$MPV" --no-border --geometry=${WW}x${HH}+${X}+${Y} \
    --profile=low-latency --untimed --no-correct-pts \
    --video-sync=desync --framedrop=vo --rtsp-transport=tcp \
    --loop=inf --no-resume-playback --no-cache \
    --demuxer-readahead-secs=1 --fps=24 --force-seekable=yes \
    --vo=gpu $HWDEC --title="tile_${R}_${C}" \
    --no-audio --keep-open=yes "$url" &
done

# ── And fire up your health monitor ────────────────────────────────────────
if [[ -x $MONITOR_PY ]]; then
  echo "[INFO] Starting health monitor"
  "$PYTHON" "$MONITOR_PY" &
else
  echo "[WARN] Health monitor missing – skipping"
fi

wait
