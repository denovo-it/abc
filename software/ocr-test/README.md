# OCR Test - Book Cover Recognition PoC

PoC for recognizing title, author, and publisher from book covers using Axelera Metis hardware accelerator and SONOFF CAM S2 RTSP camera.

## Prerequisites

- Orange Pi 5 Plus with Axelera Metis
- Python 3.10+
- SONOFF CAM S2 camera configured (RTSP)
- Voyager SDK installed in `../voyager-sdk/`

## Quick Start

```bash
cd /home/orangepi/abc/software/ocr-test

# Activate Voyager SDK environment (required)
source ../voyager-sdk/venv/bin/activate

# Download OCR models (first time only)
cd models && ./download_models.sh && cd ..

# Run with RTSP camera
python3 main.py --no-display
```

## Usage

### Single capture from RTSP camera

```bash
source ../voyager-sdk/venv/bin/activate

# Capture and process (place book in front of camera)
python3 main.py --no-display

# With debug output
python3 main.py --no-display -d
```

### Continuous mode with live preview (requires X11)

```bash
source ../voyager-sdk/venv/bin/activate
python3 main.py --continuous
# Press SPACE to capture, Q to quit
```

### Test with existing image

```bash
source ../voyager-sdk/venv/bin/activate

# Process image file
python3 main.py -i test_images/book_test.jpg --no-display

# Save annotated result
python3 main.py -i test_images/book_test.jpg -o test_images/result.jpg --no-display
```

### Capture only (no OCR)

```bash
source ../voyager-sdk/venv/bin/activate
python3 capture.py
# Saves to test_images/capture.jpg
```

### Test OCR pipeline standalone

```bash
source ../voyager-sdk/venv/bin/activate
python3 ocr_pipeline.py test_images/capture.jpg -d
```

## Configuration

Camera settings are in `.env`:

```bash
# RTSP Camera (SONOFF CAM S2)
RTSP_USERNAME=sonoff
RTSP_PASSWORD=your_password
RTSP_IP=192.168.1.199
RTSP_PORT=554
RTSP_PATH=/av_stream/ch0
```

## Project Structure

```
ocr-test/
├── README.md           # This documentation
├── requirements.txt    # Python dependencies
├── .env                # Camera configuration
├── config.py           # Centralized configuration
├── capture.py          # RTSP frame capture
├── ocr_pipeline.py     # OCR pipeline (detection + recognition)
├── book_parser.py      # Title/author/publisher extraction
├── main.py             # Entry point
├── models/
│   ├── download_models.sh          # Model download script
│   ├── ch_PP-OCRv3_det_infer.onnx  # Detection model
│   ├── latin_PP-OCRv3_rec_infer.onnx # Recognition model
│   └── latin_dict.txt              # Character dictionary
└── test_images/
    ├── capture.jpg     # Latest camera capture
    └── result.jpg      # Annotated result
```

## OCR Pipeline

1. **Capture**: Frame from RTSP camera (SONOFF CAM S2)
2. **Detection**: Text region localization (PP-OCRv3 detection)
3. **Recognition**: Text recognition (PP-OCRv3 Latin)
4. **Parsing**: Title/author/publisher identification based on position

## Metis Integration Status

### Compiled for Metis
- **Detection model**: PP-OCRv3 detection compiled successfully
  - Location: `../voyager-sdk/build/ppocr-det/`
  - Note: Output format requires additional post-processing work

### Not compatible with Metis
- **Recognition model**: PP-OCRv3 uses unsupported operators (MatMul, ReduceMean)
  - Currently running on CPU via ONNX Runtime

### Current implementation
- Uses CPU ONNX for both detection and recognition
- Metis backend available but falls back to CPU

## Troubleshooting

### No text detected
- Ensure book is well-lit and in focus
- Check camera is pointing at the book cover
- Try adjusting camera position for better contrast

### Camera connection failed
- Verify RTSP credentials in `.env`
- Check camera is on the same network
- Test with: `ffplay rtsp://user:pass@ip:554/av_stream/ch0`

### Recognition errors
- PP-OCRv3 works best with clear, printed text
- Handwritten or stylized fonts may not be recognized well
- Low confidence results indicate uncertain recognition

## License

MIT - Copyright 2026 Denovo s.r.l.
