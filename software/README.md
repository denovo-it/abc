# A.B.C. Software

Integrated book cataloguing pipeline that combines object detection, OCR, and gesture feedback into a single automated loop.

## Voyager SDK setup

* [Voyager SDK on Orange Pi 5 Plus](https://support.axelera.ai/hc/en-us/articles/27059519168146-Bring-up-Voyager-SDK-in-Orange-Pi-5-Plus)
* [Axelera Voyager SDK repo](https://github.com/denovo-it/voyager-sdk)
* [Generate a token](https://github.com/axelera-ai-hub/voyager-sdk/blob/release/v1.2.5/docs/tutorials/install.md#generate-a-token-for-the-installer)

NOTE: run the dpkg install indicated and check the `cfg/config-ubuntu-2204-arm64.yaml` if is in line with the guide before proceeding.

In `voyager-sdk/` you can find `install_voyager.sh` that requires `.env` populated (see `env_example.txt`) to install the SDK as indicated in the guide. After the install and a reboot, launch `denovo_test.sh` in X environment to verify.

## How the pipeline works

The pipeline (`app.py`) runs a 3-state machine on the RTSP camera stream with fullscreen display (1024x600):

```
WATCHING -> SCANNING -> WAITING -> WATCHING
```

| State | What happens | Hardware |
|-------|-------------|----------|
| **WATCHING** | Image correlation detects objects in the loading area. YOLOv8 detects people. Requires N consecutive frames with object and no person. | Metis NPU + CPU |
| **SCANNING** | Captures the frame, runs multi-pass OCR (upscale + raw + optional color filters), parses title/author/publisher, searches the book database. Shows animated hourglass with progress. | CPU (default) or CPU+Metis hybrid |
| **WAITING** | Shows result (Title/Author/Publisher). Waits for book removal (correlation) or person presence (YOLO). Accept shows green V, reject shows red X. | Metis NPU + CPU |

Only one model uses the Metis NPU at a time. Each state releases the device before the next one starts.

## Dependencies

### Internal (from this repository)

| Module | Path | What is used |
|--------|------|-------------|
| **display** | `./display.py` | OpenCV display overlay module (imported by `app.py`) |
| **tools** | `./tools/` | `scan_books.py` (OCR engine), `display.py` (fullscreen UI), `calibrate.py` (camera calibration), `config.py` (env loader), `setup_database.py` (BookDatabase) |
| **voyager-sdk** | `./voyager-sdk/` | Axelera SDK framework, GStreamer pipeline, compiled models in `build/` |

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
| `yolov8l-coco-onnx` | Object detection (person) | `voyager-sdk/build/yolov8l-coco-onnx/` |
| `yolov8lpose-coco-onnx` | Pose estimation (gesture feedback) | `voyager-sdk/build/yolov8lpose-coco-onnx/` (must be compiled) |
| PP-OCRv3 Latin | Text detection + recognition | `~/.paddleocr/whl/` (auto-downloaded) |

## Setup

### System optimization (recommended)

Disable or remove unnecessary services to free CPU and memory:

```bash
# Remove crash reporter (can consume 100% CPU on two cores)
sudo apt remove -y apport apport-gtk

# Remove Bluetooth manager (not needed for headless operation)
sudo apt remove -y blueman

# Disable unused services
sudo systemctl disable --now xrdp xrdp-sesman   # Remote desktop
sudo systemctl disable --now cups                # Print server
sudo systemctl disable --now kerneloops          # Kernel crash reporter
sudo systemctl disable --now smartmontools       # Disk SMART monitoring
```

### Application setup

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

This detects the X markers (using solidity and convexity defect filters to reject non-X shapes), saves the loading area coordinates to `config/loading_area.txt`, and captures an empty area reference image (`config/empty_reference.jpg`) for book detection.

Options:
- `--debug` — Save intermediate debug images
- `--no-display` — Skip GUI preview (headless mode)

Calibration can also be triggered at runtime via the `CALIBRATE` QR code command.

## Usage

```bash
source venv/bin/activate

# Basic: detect book, OCR, auto-accept (no gesture feedback)
python3 app.py --no-feedback

# Full pipeline with gesture feedback
python3 app.py

# Hybrid OCR (CPU + Metis ensemble, better accuracy, slower)
python3 app.py --ocr-model hybrid --no-feedback

# Italian books only, with color filters for artistic covers
python3 app.py --lang it --color-filters --no-feedback

# Debug mode (activates diagnostics overlay on screen)
python3 app.py --debug --no-feedback
```

### CLI options

| Flag | Default | Description |
|------|---------|-------------|
| `--ocr-model {cpu,metis,hybrid}` | `hybrid` | OCR model. `hybrid` = CPU+Metis ensemble (best accuracy). |
| `--lang {en,it}` | all | Language filter for database search |
| `--confidence FLOAT` | 0.40 | Book detection confidence threshold |
| `--consecutive INT` | 5 | Consecutive frames needed to confirm a book |
| `--color-filters` | off | Extra OCR passes with color channel filters (slower, better on artistic covers) |
| `--no-feedback` | off | Skip gesture feedback, auto-accept results |
| `--debug` | off | Activates diagnostics overlay and verbose output |

## QR code commands

During WATCHING and WAITING states, the camera checks for QR codes every ~1.5 seconds. Supported commands:

| QR content | Action |
|------------|--------|
| `DIAG ON` | Enable diagnostics overlay (log panel at bottom-left) |
| `DIAG OFF` | Disable diagnostics overlay |
| `SHUTDOWN NOW` | Start 5-second shutdown countdown (visual on screen) |
| `CANCEL` | Cancel a pending shutdown countdown |
| `CALIBRATE` | Re-run loading area calibration without restarting the app |

Printable QR code images are available in `doc/qr-code/`.

## Tools

### `tools/calibrate.py` — Camera calibration

Detects 4 X markers at the loading area corners and saves calibration data to `config/`.

```bash
python3 tools/calibrate.py [--debug] [--no-display]
```

### `tools/setup_database.py` — Book database management

Downloads and imports the Open Library dump (~12GB, 55M+ books) into a local SQLite database.

```bash
python3 tools/setup_database.py download              # Download OL dump
python3 tools/setup_database.py import [--lang it]     # Import (optionally filter by language)
python3 tools/setup_database.py create-fts             # Build full-text search index
python3 tools/setup_database.py stats                  # Show database statistics
python3 tools/setup_database.py search "query"         # Search books
python3 tools/setup_database.py add "Title" "Author" "Publisher"  # Add manually
python3 tools/setup_database.py add-imprint "OSCAR" "MONDADORI"   # Add publisher imprint
```

### `tools/record_abc.sh` — Screen recording

Records the full screen (ffmpeg x11grab) while running the app. Stops automatically when the app exits.

```bash
tools/record_abc.sh                    # Auto-named recording
tools/record_abc.sh my_session.mp4     # Custom filename
```

Recordings are saved to `/home/orangepi/recordings/`.

### `tools/start_abc.sh` — Autostart wrapper

Waits for X11 to be available (max 30s), sets up display permissions, hides the cursor, and launches the app. Used by the systemd service `abc.service`.

### `tools/scan_books.py` — Standalone OCR scanner

Can be used independently of the pipeline for manual scanning sessions:

```bash
python3 tools/scan_books.py [--model {cpu,metis,hybrid}] [--lang {en,it}] [--auto] [--debug]
```

## Console output

During **WATCHING**: `.` = no book, `+` = book detected (building consecutive count).

During **WAITING**: `.` = book still there, `*` = scene changing (person or book gone).

Press **ENTER** during WAITING to quit the pipeline.

Press **Ctrl+C** at any time to force stop.
