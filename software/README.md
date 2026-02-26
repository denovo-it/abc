# A.B.C. Software

Integrated book cataloguing pipeline that combines object detection, OCR, and gesture feedback into a single automated loop.

## Voyager SDK setup

* [Voyager SDK on Orange Pi 5 Plus](https://support.axelera.ai/hc/en-us/articles/27059519168146-Bring-up-Voyager-SDK-in-Orange-Pi-5-Plus)
* [Axelera Voyager SDK repo](https://github.com/denovo-it/voyager-sdk)
* [Generate a token](https://github.com/axelera-ai-hub/voyager-sdk/blob/release/v1.2.5/docs/tutorials/install.md#generate-a-token-for-the-installer)

NOTE: run the dpkg install indicated and check the `cfg/config-ubuntu-2204-arm64.yaml` if is in line with the guide before proceeding.

In `voyager-sdk/` you can find `install_voyager.sh` that requires `.env` populated (see `env_example.txt`) to install the SDK as indicated in the guide. After the install and a reboot, launch `denovo_test.sh` in X environment to verify.

## How the pipeline works

The pipeline (`app.py`) runs a 4-state machine on the RTSP camera stream:

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
| **tools** | `./tools/` | `scan_books.py` (OCR engine), `display.py` (fullscreen UI), `calibrate.py` (camera calibration), `config.py` (env loader), `setup_database.py` (BookDatabase) |
| **voyager-sdk** | `./voyager-sdk/` | Axelera SDK framework, GStreamer pipeline, compiled models in `build/` |

### External (system)

| Component | Path | Description |
|-----------|------|-------------|
| Axelera Runtime | `/opt/axelera/runtime-1.5.2-1/` | NPU runtime libraries |
| Axelera Device | `/opt/axelera/device-1.5.2-1/omega/` | Device firmware |
| RISC-V Toolchain | `/opt/axelera/riscv-gnu-newlib-toolchain-*/` | Kernel compilation toolchain |

### Python (venv)

Key packages (full list in `tools/requirements.txt`):

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
cd software

# 1. Configure environment (REQUIRED first step)
cp doc/env_example.txt .env
# Edit .env with your RTSP camera credentials and settings

# 2. Activate venv
source venv/bin/activate

# 3. (Optional) Compile pose model for gesture feedback (~10-30 min)
cd voyager-sdk && source venv/bin/activate
./inference.py yolov8lpose-coco-onnx media/traffic1_1080p.mp4 --frames 1 --no-display
```

## Calibration

Before first use, calibrate the loading area by placing 4 X markers at the corners:

```bash
source venv/bin/activate
python3 tools/calibrate.py
```

This detects the X markers, saves the loading area coordinates to `config/loading_area.txt`,
and captures an empty area reference image (`config/empty_reference.jpg`) for book detection.

Options:
- `--debug` — Save intermediate debug images
- `--no-display` — Skip GUI preview (headless mode)

Calibration can also be triggered at runtime via the `CALIBRATE` QR code command.

## Usage

```bash
source venv/bin/activate

# Basic: detect book, OCR, auto-accept (no gesture feedback)
python app.py --no-feedback

# Full pipeline with gesture feedback
python app.py

# Hybrid OCR (CPU + Metis ensemble, better accuracy, slower)
python app.py --ocr-model hybrid --no-feedback

# Italian books only, with color filters for artistic covers
python app.py --lang it --color-filters --no-feedback

# Debug mode (verbose per-frame output)
python app.py --debug --no-feedback
```

### CLI options

| Flag | Default | Description |
|------|---------|-------------|
| `--ocr-model {cpu,metis,hybrid}` | `hybrid` | OCR model. `hybrid` = CPU+Metis ensemble (best accuracy). |
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
