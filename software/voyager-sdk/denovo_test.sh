#!/bin/bash

# Activate virtual environment if it exists
if [ -f venv/bin/activate ]; then
  source venv/bin/activate
else
  echo "Warning: venv not found, running without virtual environment"
fi

# Load environment variables from .env file
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

RTSP_URL="rtsp://${RTSP_USERNAME}:${RTSP_PASSWORD}@${RTSP_IP}:${RTSP_PORT}${RTSP_PATH}"

AXELERA_CONFIGURE_BOARD=,30 ./inference.py \
  yolov8l-coco-onnx \
  "$RTSP_URL" \
  --no-show-temp \
  --no-show-cpu-usage \
  --no-show-system-fps \
  --no-show-inference-rate \
  --no-show-device-fps \
  --no-show-host-fps \
  --no-show-latency \
  --no-show-stream-timing

