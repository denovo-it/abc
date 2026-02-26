# A.B.C. Pipeline Flow

## State Machine

The pipeline runs as a 3-state loop on the Orange Pi 5 Plus with fullscreen display (1024x600):

### 1. WATCHING
- **Engine**: YOLOv8l on Metis NPU (~45 fps) + image correlation
- **Goal**: Detect a book in the loading area
- **Book detection**: compares each frame against `empty_reference.jpg` via `cv2.matchTemplate` (correlation < 0.975 = object present)
- **Person detection**: YOLOv8l cls=0 on Metis NPU (person in loading area = "POSITIONING...")
- Requires N consecutive frames with object detected, no person (default: 15)
- **QR commands**: checked every 30 frames (~1.5s) — DIAG ON/OFF, SHUTDOWN NOW, CALIBRATE
- **Display**: live stream with loading area rectangle (green=empty, orange=object), correlation value
- On detection: captures BGR frame, transitions to SCANNING

### 2. SCANNING
- **Engine**: PaddleOCR v3 (CPU or Hybrid CPU+Metis)
- **Goal**: Read text from the book cover, identify it in the database
- Runs multi-pass OCR (2 standard + optional color filter passes)
- **Display**: animated hourglass with progress %, phase text in green on dark background
  - Phases: OCR Pass 1/N, ..., Spell check, Text analysis, Database search, Done
- Queries SQLite database (55M books) for title/author match
- **Display result**: centered book cover with Title/Author/Publisher overlay
- Transitions to WAITING

### 3. WAITING
- **Engine**: YOLOv8 on Metis NPU (person/object detection)
- **Goal**: Wait for user to take or reject the book
- With `--no-feedback`: uses correlation to detect book removal (no pose model needed)
- With feedback: YOLOv8n-pose monitors for rejection gesture (person stays ~4s)
- **QR commands**: checked every 30 frames
- **Display**: result box with Title/Author/Publisher

| Condition | Result | Visual feedback |
|-----------|--------|----------------|
| Book removed (correlation returns high) | **ACCEPT** | Green checkmark (V) fullscreen |
| Person detected for ~1.5s then leaves | **ACCEPT** | Green checkmark (V) fullscreen |
| Person stays in area ~4s (reject gesture) | **REJECT** | Red X fullscreen |
| ENTER pressed | **QUIT** | - |

After ACCEPT or REJECT, the pipeline loops back to WATCHING.

## QR Code Commands
Active during WATCHING and WAITING states:
- `DIAG ON` / `DIAG OFF` — toggle diagnostics overlay (bottom-left panel)
- `SHUTDOWN NOW` — 5 second countdown, cancellable with `CANCEL` QR
- `CALIBRATE` — re-run camera calibration (detect X markers, save new config)

## Startup Sequence
1. Splash screen with logo (immediate, before heavy imports)
2. Load Axelera SDK
3. Clean up stale Metis processes
4. Load OCR components (PaddleOCR models)
5. Enter WATCHING state

## Hardware Usage by State
| State | Metis NPU | CPU | Display |
|-------|-----------|-----|---------|
| WATCHING | YOLOv8l (detection) | Correlation | Live stream + overlays |
| SCANNING | (hybrid mode) | PaddleOCR | Hourglass + progress |
| WAITING | YOLOv8l or pose | Correlation | Result box |
