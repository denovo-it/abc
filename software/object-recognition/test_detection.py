#!/usr/bin/env python
"""Unit tests for object detection (person + book) via Axelera Metis NPU.

Requires:
  - Local venv activated (source venv/bin/activate)
  - RTSP camera reachable (config from .env)
  - Metis NPU connected

Usage:
  cd software/object-recognition
  source venv/bin/activate
  python -m pytest test_detection.py -v -s
  # or:
  python test_detection.py
"""

import os
import sys
import time
import unittest

# ---------------------------------------------------------------------------
# Environment bootstrap
# ---------------------------------------------------------------------------

# Load RTSP credentials from local .env
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

# Verify Voyager SDK environment is active
if not os.environ.get('AXELERA_FRAMEWORK'):
    sys.exit(
        "ERROR: Voyager SDK environment not active.\n"
        "Run:  source ../voyager-sdk/venv/bin/activate"
    )

from axelera.app import config  # noqa: E402
from axelera.app.stream import create_inference_stream  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# COCO class IDs we care about
PERSON_CLASS_ID = 0
BOOK_CLASS_ID = 73

# COCO label names (index == class_id)
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

# How many frames to analyse per test
FRAMES_TO_PROCESS = 30

# Pre-compiled model (Metis)
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
# Test class
# ---------------------------------------------------------------------------

class TestObjectDetection(unittest.TestCase):
    """Integration tests: detect person/book from RTSP via Metis NPU."""

    stream = None

    @classmethod
    def setUpClass(cls):
        """Create the Metis inference stream once for all tests."""
        url = _rtsp_url()
        print(f"\n{'='*70}")
        print(f"  Model : {MODEL_NAME} (Metis NPU)")
        print(f"  Source: {url.split('@')[0].split('//')[0]}//<credentials>@{url.split('@')[1]}")
        print(f"  Target: person (id {PERSON_CLASS_ID}), book (id {BOOK_CLASS_ID})")
        print(f"{'='*70}\n")

        cls.stream = create_inference_stream(
            network=MODEL_NAME,
            sources=[url],
            pipe_type='gst',           # runs on Metis NPU
            specified_frame_rate=-1,   # downstream-leaky: drop if slow
        )

    @classmethod
    def tearDownClass(cls):
        """Shut down the inference stream."""
        if cls.stream is not None:
            cls.stream.stop()
            print("\nStream stopped.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _collect_detections(self, n_frames):
        """Run inference for *n_frames* and return all target-class detections.

        Returns:
            list of dicts with keys: frame, class_id, label, score, bbox
        """
        results = []
        processed = 0

        for frame_result in self.stream:
            if frame_result.meta is None:
                continue

            processed += 1
            try:
                det_meta = frame_result.meta['detections']
            except (KeyError, TypeError):
                continue

            for i in range(len(det_meta)):
                cid = int(det_meta.class_ids[i])
                if cid not in TARGET_CLASSES:
                    continue
                score = float(det_meta.scores[i])
                bbox = det_meta.boxes[i].tolist()
                label = COCO_LABELS[cid] if cid < len(COCO_LABELS) else str(cid)
                results.append({
                    'frame': processed,
                    'class_id': cid,
                    'label': label,
                    'score': score,
                    'bbox': bbox,
                })

            if processed >= n_frames:
                break

        return results, processed

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_stream_produces_frames(self):
        """The Metis pipeline should produce at least one frame."""
        count = 0
        for frame_result in self.stream:
            if frame_result.meta is not None:
                count += 1
            if count >= 3:
                break
        self.assertGreater(count, 0, "No frames received from Metis pipeline")
        print(f"  [OK] Stream alive - received {count} frames")

    def test_detect_person_and_book(self):
        """Run detection on RTSP stream, print person/book with confidence."""
        detections, total_frames = self._collect_detections(FRAMES_TO_PROCESS)

        print(f"\n  Processed {total_frames} frames, "
              f"found {len(detections)} target detections\n")

        # Summary per class
        persons = [d for d in detections if d['class_id'] == PERSON_CLASS_ID]
        books = [d for d in detections if d['class_id'] == BOOK_CLASS_ID]

        # Print all detections frame by frame
        current_frame = None
        for d in detections:
            if d['frame'] != current_frame:
                current_frame = d['frame']
                print(f"  --- Frame {current_frame}/{total_frames} ---")
            x1, y1, x2, y2 = d['bbox']
            w, h = x2 - x1, y2 - y1
            print(f"    {d['label']:>8s}  {d['score']*100:5.1f}%  "
                  f"  box=({x1:.0f},{y1:.0f}) {w:.0f}x{h:.0f}")

        # Summary
        print(f"\n  {'='*50}")
        print(f"  SUMMARY over {total_frames} frames:")
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
        print(f"  {'='*50}\n")

        # The test passes regardless - it's a live camera, objects may or may not
        # be present. The key assertion is that inference ran successfully.
        self.assertGreater(total_frames, 0, "No frames processed")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main(verbosity=2)
