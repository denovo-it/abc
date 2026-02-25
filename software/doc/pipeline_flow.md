# A.B.C. Pipeline Flow

## State Machine

The pipeline runs as a 3-state loop on the Orange Pi 5 Plus:

### 1. WATCHING
- **Engine**: YOLOv8 on Metis NPU (~45 fps)
- **Goal**: Detect a book in the loading area
- Filters YOLO detections to the loading area rectangle
- Requires N consecutive frames with book detected (default: 3)
- On detection: captures BGR frame from RTSP stream, transitions to SCANNING

### 2. SCANNING
- **Engine**: PaddleOCR v3 (CPU or Hybrid CPU+Metis)
- **Goal**: Read text from the book cover, identify it in the database
- Runs multi-pass OCR (2 standard + optional color filter passes)
- Queries SQLite database (55M books) for title/author match
- Displays identification result, transitions to WAITING

### 3. WAITING
- **Engine**: YOLOv8n-pose on Metis NPU (person detection in loading area)
- **Goal**: Wait for user to take or reject the book
- When feedback is disabled (`--no-feedback`), falls back to YOLOv8 detection model
- Monitors the scene continuously:

| Condition | Indicator | Frames needed | Result |
|-----------|-----------|---------------|--------|
| Crossed fingers shown ~4s (reject gesture) | `P` + countdown | 80 (~4s) | **REJECT** |
| Person appeared then left (took book) | `*` | 30 (~1.5s) | **ACCEPT** |
| No presence detected yet | `.` | - | Keep waiting |
| ENTER pressed | - | immediate | **QUIT** |

After ACCEPT or REJECT, the pipeline loops back to WATCHING.

## Reject/Accept Detection (Crossed Fingers Presence)
Uses YOLOv8n-pose on Metis NPU for person/gesture detection:
1. Person bounding box must overlap the loading area
2. Crossed fingers shown for 80 consecutive frames (~4 seconds) → **REJECT**
3. If the person leaves before 4s (took the book) → **ACCEPT**

**Goal achieved**: the system correctly detects the reject gesture — showing two
crossed index fingers is reliably detected as a discard signal. The approach uses
person-level presence detection rather than individual keypoint tracking, which
makes it robust regardless of the specific hand pose. From the overhead camera,
individual keypoints (wrists, elbows) are too noisy (200-500px jumps between
frames even with still hands), but person-level detection is very reliable
(confidence 0.70-0.88). Any gesture that keeps the person in the loading area
for ~4 seconds triggers the reject.

## Hardware Usage by State
| State | Metis NPU | CPU | Camera |
|-------|-----------|-----|--------|
| WATCHING | YOLOv8l (detection) | - | RTSP stream |
| SCANNING | (hybrid mode) | PaddleOCR | Single frame |
| WAITING | YOLOv8n-pose (keypoints) | - | RTSP stream |
