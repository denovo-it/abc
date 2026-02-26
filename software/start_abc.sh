#!/bin/bash
# A.B.C. autostart wrapper — waits for X11, then launches the app.

set -e

# Wait for X to be available (max 30s)
for i in $(seq 1 30); do
    if xdpyinfo -display :0 >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# Allow local connections to X display
export DISPLAY=:0
xhost +local: 2>/dev/null || true

# Hide mouse cursor
unclutter -idle 0 -root &

# Launch A.B.C.
cd /home/orangepi/abc/software
exec /home/orangepi/abc/software/venv/bin/python app.py --ocr-model hybrid --no-feedback
