#!/usr/bin/env python
"""Object detection (person + book) via Axelera Metis NPU.

Detects person and book objects from RTSP camera using YOLOv8 on Metis NPU.
Prints detections with confidence % and bounding box to console.

Requires:
  - Local venv activated (source venv/bin/activate)
  - RTSP camera reachable (config from .env)
  - Metis NPU connected

Usage:
  cd software/object-recognition
  source venv/bin/activate
  python test_detection.py              # Run 30 frames
  python test_detection.py --frames 60  # Run 60 frames
"""

import argparse
import os
import sys
import time

# ---------------------------------------------------------------------------
# Environment bootstrap
# ---------------------------------------------------------------------------

_ENV_PATH = os.path.join(os.path.dirname(__file__), '.env')


def _load_env(path):
    """Load KEY=VALUE pairs from a .env file into os.environ."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env(_ENV_PATH)

if not os.environ.get('AXELERA_FRAMEWORK'):
    sys.exit(
        "ERROR: Voyager SDK environment not active.\n"
        "Run:  source venv/bin/activate"
    )

from axelera.app import config, create_inference_stream  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PERSON_CLASS_ID = 0
BOOK_CLASS_ID = 73

COCO_LABELS = (
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train',
    'truck', 'boat', 'traffic light', 'fire hydrant', 'stop sign',
    'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
    'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag',
    'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball', 'kite',
    'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
    'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon',
    'bowl', 'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot',
    'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch', 'potted plant',
    'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote',
    'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
    'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear',
    'hair drier', 'toothbrush',
)

TARGET_CLASSES = {PERSON_CLASS_ID, BOOK_CLASS_ID}

MODEL_NAME = 'yolov8l-coco-onnx'


def _rtsp_url():
    """Build RTSP URL from environment variables."""
    ip = os.getenv('RTSP_IP', '192.168.1.199')
    port = os.getenv('RTSP_PORT', '554')
    username = os.getenv('RTSP_USERNAME', 'sonoff')
    password = os.getenv('RTSP_PASSWORD', '')
    path = os.getenv('RTSP_PATH', '/av_stream/ch0')
    return f"rtsp://{username}:{password}@{ip}:{port}{path}"


# ---------------------------------------------------------------------------
# Detection loop
# ---------------------------------------------------------------------------

def run_detection(n_frames):
    """Run object detection for n_frames and print results."""
    url = _rtsp_url()
    url_safe = f"{url.split('@')[0].split('//')[0]}//<credentials>@{url.split('@')[1]}"

    print(f"\n{'='*60}")
    print(f"  Model : {MODEL_NAME} (Metis NPU)")
    print(f"  Source: {url_safe}")
    print(f"  Target: person (id {PERSON_CLASS_ID}), book (id {BOOK_CLASS_ID})")
    print(f"  Frames: {n_frames}")
    print(f"{'='*60}\n")

    # Create stream using the same API as inference.py
    pipeline_config = config.PipelineConfig(
        network=MODEL_NAME,
        sources=[url],
        pipe_type='gst',
    )

    stream_config = config.InferenceStreamConfig(
        timeout=10,
        frames=n_frames,
    )

    stream = create_inference_stream(
        stream_config=stream_config,
        pipeline_configs=pipeline_config,
    )

    detections = []
    processed = 0
    t_start = time.time()

    for frame_result in stream:
        if frame_result.image is None and frame_result.meta is None:
            continue

        processed += 1

        # Access detections via task name from YAML pipeline
        frame_dets = []
        for det in frame_result.detections:
            cid = int(det.class_id)
            if cid not in TARGET_CLASSES:
                continue
            score = float(det.score)
            bbox = det.box.tolist()
            label = COCO_LABELS[cid] if cid < len(COCO_LABELS) else str(cid)
            frame_dets.append({
                'frame': processed,
                'class_id': cid,
                'label': label,
                'score': score,
                'bbox': bbox,
            })

        if frame_dets:
            print(f"  --- Frame {processed}/{n_frames} ---")
            for d in frame_dets:
                x1, y1, x2, y2 = d['bbox']
                w, h = x2 - x1, y2 - y1
                print(f"    {d['label']:>8s}  {d['score']*100:5.1f}%  "
                      f"  box=({x1:.0f},{y1:.0f}) {w:.0f}x{h:.0f}")
            detections.extend(frame_dets)

        if processed >= n_frames:
            break

    elapsed = time.time() - t_start

    # Summary
    persons = [d for d in detections if d['class_id'] == PERSON_CLASS_ID]
    books = [d for d in detections if d['class_id'] == BOOK_CLASS_ID]

    print(f"\n{'='*60}")
    print(f"  SUMMARY: {processed} frames in {elapsed:.1f}s ({processed/max(elapsed,0.1):.1f} fps)")
    if persons:
        avg_p = sum(d['score'] for d in persons) / len(persons)
        max_p = max(d['score'] for d in persons)
        print(f"    person : {len(persons):3d} detections, "
              f"avg {avg_p*100:.1f}%, max {max_p*100:.1f}%")
    else:
        print(f"    person :   0 detections")
    if books:
        avg_b = sum(d['score'] for d in books) / len(books)
        max_b = max(d['score'] for d in books)
        print(f"    book   : {len(books):3d} detections, "
              f"avg {avg_b*100:.1f}%, max {max_b*100:.1f}%")
    else:
        print(f"    book   :   0 detections")
    print(f"{'='*60}\n")

    stream.stop()
    return detections, processed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Detect person and book from RTSP camera via Metis NPU"
    )
    parser.add_argument(
        '--frames', type=int, default=30,
        help="Number of frames to process (default: 30)"
    )
    args = parser.parse_args()

    run_detection(args.frames)


if __name__ == '__main__':
    main()
