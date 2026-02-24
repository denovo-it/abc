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
| Person stays ~4s (not taking book) | `P` + countdown | 80 (~4s) | **REJECT** |
| Person appeared then left (took book) | `*` | 30 (~1.5s) | **ACCEPT** |
| No person seen yet | `.` | - | Keep waiting |
| ENTER pressed | - | immediate | **QUIT** |

After ACCEPT or REJECT, the pipeline loops back to WATCHING.

## Reject Gesture (Person Presence)
Uses YOLOv8n-pose on Metis NPU for person detection:
1. Person bounding box must overlap the loading area
2. Person must remain present for 80 consecutive frames (~4 seconds)
3. If the person leaves before 4s (took the book), it's an accept

This approach was chosen because from the overhead camera, individual
keypoint positions (wrists, elbows) are too noisy for reliable gesture
tracking — wrist positions can jump 200-500px between frames even when
hands are perfectly still. Person-level detection, however, is very
reliable (0.70-0.88 confidence).

## Hardware Usage by State
| State | Metis NPU | CPU | Camera |
|-------|-----------|-----|--------|
| WATCHING | YOLOv8l (detection) | - | RTSP stream |
| SCANNING | (hybrid mode) | PaddleOCR | Single frame |
| WAITING | YOLOv8n-pose (keypoints) | - | RTSP stream |
