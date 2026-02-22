# A.B.C. Pipeline

Integrated book cataloguing pipeline that combines object detection, OCR, and gesture feedback into a single automated loop.

## How it works

The pipeline runs a 4-state machine on the RTSP camera stream:

```
WATCHING -> SCANNING -> FEEDBACK -> WAITING -> WATCHING
```

| State | What happens | Hardware |
|-------|-------------|----------|
| **WATCHING** | YOLOv8 object detection looks for a book in the camera frame. Requires N consecutive detections above a confidence threshold. | Metis NPU |
| **SCANNING** | Captures the frame, runs multi-pass OCR (upscale + raw + optional color filters), parses title/author/publisher, searches the book database. | CPU (default) or CPU+Metis hybrid |
| **FEEDBACK** | YOLOv8-Pose watches for a "crossed wrists" rejection gesture. If detected within timeout, the result is rejected. Otherwise it is accepted. Skipped with `--no-feedback`. | Metis NPU |
| **WAITING** | Holds until the scanned book is removed (person appears or book disappears). Press ENTER to quit. | Metis NPU |

Only one model uses the Metis NPU at a time. Each state releases the device before the next one starts.

## Dependencies

### Internal (from this repository)

| Module | Path | What is used |
|--------|------|-------------|
| **ocr-test** | `../ocr-test/` | `scan_books.py` (OCR engine, preprocessor, parser, post-processor), `setup_database.py` (BookDatabase), `books.db` (18GB SQLite) |
| **voyager-sdk** | `../voyager-sdk/` | Axelera SDK framework, GStreamer pipeline, compiled models in `build/` |

### External (system)

| Component | Path | Description |
|-----------|------|-------------|
| Axelera Runtime | `/opt/axelera/runtime-1.5.2-1/` | NPU runtime libraries |
| Axelera Device | `/opt/axelera/device-1.5.2-1/omega/` | Device firmware |
| RISC-V Toolchain | `/opt/axelera/riscv-gnu-newlib-toolchain-*/` | Kernel compilation toolchain |

### Python (venv)

Key packages (full list in `requirements.txt`):

- **paddleocr 2.10.0** + **paddlepaddle 3.2.2** - OCR engine
- **opencv-python 4.11.0** - Image processing
- **numpy 2.2.6** - Array operations
- **pyspellchecker 0.8.4** - OCR error correction
- **axelera-runtime 1.5.2** - NPU inference (via .pth link to SDK cache)
- **torch 2.8.0+cpu** - ML framework (CPU only)

### AI Models

| Model | Task | Location |
|-------|------|----------|
| `yolov8l-coco-onnx` | Object detection (book, person) | `voyager-sdk/build/yolov8l-coco-onnx/` |
| `yolov8lpose-coco-onnx` | Pose estimation (gesture feedback) | `voyager-sdk/build/yolov8lpose-coco-onnx/` (must be compiled) |
| PP-OCRv3 Latin | Text detection + recognition | `~/.paddleocr/whl/` (auto-downloaded) |

## Setup

```bash
cd software/pipeline

# 1. Create/activate venv (already created)
source venv/bin/activate

# 2. Configure RTSP camera credentials
cp ../ocr-test/.env .env
# Edit .env with your RTSP_USERNAME, RTSP_PASSWORD, RTSP_IP

# 3. (Optional) Compile pose model for gesture feedback (~10-30 min)
cd ../voyager-sdk && source venv/bin/activate
./inference.py yolov8lpose-coco-onnx media/traffic1_1080p.mp4 --frames 1 --no-display
```

## Usage

```bash
source venv/bin/activate

# Basic: detect book, OCR, auto-accept (no gesture feedback)
python pipeline.py --no-feedback

# Full pipeline with gesture feedback
python pipeline.py

# Hybrid OCR (CPU + Metis ensemble, better accuracy, slower)
python pipeline.py --ocr-model hybrid --no-feedback

# Italian books only, with color filters for artistic covers
python pipeline.py --lang it --color-filters --no-feedback

# Debug mode (verbose per-frame output)
python pipeline.py --debug --no-feedback
```

### CLI options

| Flag | Default | Description |
|------|---------|-------------|
| `--ocr-model {cpu,metis,hybrid}` | `cpu` | OCR model. `cpu` avoids Metis contention with detection. |
| `--lang {en,it}` | all | Language filter for database search |
| `--confidence FLOAT` | 0.30 | Book detection confidence threshold |
| `--consecutive INT` | 5 | Consecutive frames needed to confirm a book |
| `--feedback-timeout FLOAT` | 15.0 | Seconds to wait for rejection gesture |
| `--color-filters` | off | Extra OCR passes with color channel filters (slower, better on artistic covers) |
| `--no-feedback` | off | Skip gesture feedback, auto-accept results |
| `--debug` | off | Verbose frame-by-frame output |

## Console output

During **WATCHING**: `.` = no book, `+` = book detected (building consecutive count).

During **WAITING**: `.` = book still there, `*` = scene changing (person or book gone).

Press **ENTER** during WAITING to quit the pipeline.

Press **Ctrl+C** at any time to force stop.
