#!/bin/bash
# Record A.B.C. session — captures the full screen while the app runs.
# Usage: ./record_abc.sh [output_file.mp4]
#
# Starts ffmpeg screen recording, then launches the app.
# When the app exits, the recording stops automatically.
# Press Ctrl+C to force stop both.

set -e

RECORDINGS_DIR="/home/orangepi/recordings"
mkdir -p "$RECORDINGS_DIR"
OUTPUT="${1:-$RECORDINGS_DIR/recording_$(date +%Y%m%d_%H%M%S).mp4}"
DISPLAY_TARGET=":0"
RESOLUTION="1024x600"
FRAMERATE=15

# Ensure X11 is ready
export DISPLAY="$DISPLAY_TARGET"
for i in $(seq 1 30); do
    if xdpyinfo -display "$DISPLAY_TARGET" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

xhost +local: 2>/dev/null || true

echo "=== A.B.C. Screen Recorder ==="
echo "  Output:     $OUTPUT"
echo "  Resolution: $RESOLUTION @ ${FRAMERATE}fps"
echo ""

# Start ffmpeg recording in background
ffmpeg -y -video_size "$RESOLUTION" -framerate "$FRAMERATE" \
    -f x11grab -i "$DISPLAY_TARGET" \
    -c:v libx264 -preset ultrafast -crf 23 \
    -pix_fmt yuv420p \
    "$OUTPUT" </dev/null >/dev/null 2>&1 &
FFMPEG_PID=$!

# Give ffmpeg a moment to initialize
sleep 1

if ! kill -0 "$FFMPEG_PID" 2>/dev/null; then
    echo "ERROR: ffmpeg failed to start"
    exit 1
fi
echo "  Recording started (PID $FFMPEG_PID)"

# Stop recording on exit (app quit or Ctrl+C)
cleanup() {
    echo ""
    echo "  Stopping recording..."
    kill -INT "$FFMPEG_PID" 2>/dev/null
    wait "$FFMPEG_PID" 2>/dev/null
    if [ -f "$OUTPUT" ]; then
        SIZE=$(du -h "$OUTPUT" | cut -f1)
        echo "  Saved: $OUTPUT ($SIZE)"
    fi
}
trap cleanup EXIT

# Launch A.B.C.
echo "  Launching A.B.C...."
echo ""
cd /home/orangepi/abc/software
/home/orangepi/abc/software/venv/bin/python app.py --ocr-model hybrid --debug
