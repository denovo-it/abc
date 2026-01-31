# 📚 OCR Book Cataloguing System

**Version:** 1.0
**System:** Orange Pi 5 Plus with RTSP Camera
**Last Update:** 2026-01-31

Automatic book scanning and cataloguing system with OCR on Orange Pi 5 Plus with RTSP camera.

---

## 📋 Requirements

### Hardware
- Orange Pi 5 Plus
- IP Camera with RTSP stream (e.g., 192.168.1.199)
- Loading area marked with 4 X markers at corners

### Software
- Python 3.8+
- OpenCV (`pip install opencv-python`)
- One of the following OCR engines:
  - **EasyOCR** (recommended): `pip install easyocr`
  - **Tesseract**: `pip install pytesseract pillow` + `apt install tesseract-ocr`
  - **PP-OCR**: `pip install paddlepaddle paddleocr`
- NumPy: `pip install numpy`

---

## 🚀 Initial Setup

### 1. Loading Area Preparation

**IMPORTANT:** Before calibration, create a loading area with **4 X markers at the corners**.

**Materials:**
- Light-colored masking tape (beige/white)
- Black permanent marker (thick tip)

**Procedure:**
1. Position masking tape under camera to define a rectangle
   - Recommended size: 25x35cm (slightly larger than books)
   - Center in camera view

2. **Draw 4 large X markers at the 4 corners of the rectangle**
   - **Size: 5-8cm per side** (larger = better detection)
   - Use **black** marker with **bold** lines (go over 2-3 times)
   - Position **exactly at corners** of the tape
   - Must be well-visible and high contrast

**Visual reference:**
```
┌─────X─────────────────X─────┐
│     ╲ ╱               ╲ ╱   │
│      ╳                 ╳    │
│     ╱ ╲               ╱ ╲   │
│                             │
│     LOADING AREA            │
│   (light tape on table)     │
│                             │
│     ╲ ╱               ╲ ╱   │
│      ╳                 ╳    │
│     ╱ ╲               ╱ ╲   │
└─────X─────────────────X─────┘
```

**Checklist:**
- ✅ X markers 5-8cm in size (not 2-3cm!)
- ✅ Thick, bold black lines
- ✅ All 4 X visible in camera view
- ✅ Good contrast (black on light background)
- ✅ Uniform lighting (no shadows on X markers)

---

### 2. Camera Configuration

Modify credentials in the files if needed:

```python
# In calibrate.py and scan_books.py, CONFIGURATION section
ip = "192.168.1.199"      # Camera IP
port = 554                # RTSP port
username = "admin"        # Username
password = "admin123"     # Password
```

**Or** use environment variables:
```bash
export CAMERA_IP=192.168.1.199
export CAMERA_PORT=554
export CAMERA_USER=admin
export CAMERA_PASS=admin123
```

---

### 3. Calibration

**PREREQUISITES:**
- 4 X markers drawn on loading area
- No book in the area
- Good lighting

**Execute:**
```bash
python3 calibrate.py
```

**Expected output:**
```
====================================================================
   📐 LOADING AREA CALIBRATION
====================================================================

📷 Connecting to camera...
✅ Camera connected

📸 Capturing frame...
✅ Frame captured: 1920x1080px

🔍 Detecting X markers...
✅ Found 4 markers

🔧 Calculating loading area...
✅ Loading area: 640x680px (32.7% of frame)
✅ Preview saved: test_images/calibration_preview.jpg
✅ Configuration saved: test_images/loading_area.txt

====================================================================
   ✅ CALIBRATION COMPLETE
====================================================================
```

**Verification:**
- Check `test_images/calibration_preview.jpg`
- Green rectangle should cover entire tape area
- 4 red circles should mark the X markers

**If calibration fails:**
```bash
# Debug mode to see what's detected
python3 calibrate.py --debug

# Check debug_*.jpg files for diagnostics
```

**Common issues:**
- **"Found only X markers, need 4"** → Make X larger (5-8cm), thicker lines
- **"Cannot determine loading area"** → Improve lighting, check X visibility
- **Area too small/large** → Reposition X markers

---

## 📖 Daily Usage

### Manual Scanning (Recommended)

```bash
python3 scan_books.py
```

**Workflow:**
1. System shows instructions
2. Position book in loading area
3. Press **ENTER** to scan
4. Wait for result (~15-18s with EasyOCR)
5. Remove book
6. Repeat from step 2

**Commands during scanning:**
- `ENTER` → Scan book
- `s` + ENTER → Show session statistics
- `q` + ENTER → Quit

**Example output:**
```
====================================================================
   📚 BOOK #1
====================================================================
Title:      The Ten Thousand Doors of January
Author:     Alix E Harrow
Publisher:  Orbit Books
Confidence: 0.67
====================================================================

📝 All detected text blocks:
----------------------------------------------------------------------
  1. THE
  2. TEN THOUSAND
  3. DOORS
  4. OF JANUARY
  5. ALIX E HARROW
  ...
----------------------------------------------------------------------
```

---

### Automatic Scanning

```bash
python3 scan_books.py --auto
```

- Scans automatically every 3 seconds
- Useful for large volumes
- Press **Ctrl+C** to stop

---

### OCR Model Selection

#### EasyOCR (Default) - Maximum Accuracy
```bash
python3 scan_books.py --model easyocr
```
- ✅ Accuracy 90-95%
- ✅ Handles complex fonts and artistic covers
- ❌ Slow (~15-18s per book)
- **Recommended for:** Artistic covers, maximum quality

#### Tesseract - Good Compromise
```bash
python3 scan_books.py --model tesseract
```
- ✅ Fast (~8s per book)
- ✅ Good accuracy on clean images (85-90%)
- ❌ Issues with rotations and complex fonts
- **Recommended for:** Calibrated setup, simple covers

#### PP-OCR - Maximum Speed
```bash
python3 scan_books.py --model ppocr
```
- ✅ Very fast (~3-5s per book)
- ✅ Multi-threaded (uses all 8 cores)
- ✅ Handles rotations
- ❌ Average accuracy (80-85%)
- **Recommended for:** Large volumes, speed priority

---

### Advanced Options

#### Disable Preprocessing
```bash
python3 scan_books.py --no-preprocessing
```
- Uses raw images without enhancement
- Faster but less accurate
- Useful for debugging

#### Combinations
```bash
# Auto mode with Tesseract
python3 scan_books.py --auto --model tesseract

# PP-OCR without preprocessing
python3 scan_books.py --model ppocr --no-preprocessing
```

---

## 📊 Results

### Generated Files

**During scanning:**
- `test_images/book_YYYYMMDD_HHMMSS.jpg` → Cropped image of each book
- `temp_ocr_input.jpg` → Preprocessed image (overwritten)
- `ocr_results.csv` → CSV log of all books

**CSV format:**
```csv
timestamp,title,author,publisher,confidence
20260131_143022,The Ten Thousand Doors of January,Alix E Harrow,Orbit Books,0.67
20260131_143145,1984,George Orwell,Penguin Books,0.82
```

### Session Statistics

Press `s` + ENTER during scanning or at the end:

```
====================================================================
   📊 SESSION STATISTICS
====================================================================
Books processed: 15
Session time:    247s (4.1min)
Avg time/book:   16.5s
Throughput:      3.7 books/min
====================================================================
```

---

## 🔧 Troubleshooting

### ❌ Calibration Fails

**Error:** "Found only X markers, need 4"

**Solutions:**
1. **Make X markers larger (5-8cm)** (most common cause)
2. Go over X with thick black marker multiple times
3. Improve lighting (no shadows)
4. Verify all 4 X are visible in camera view
5. Use debug mode: `python3 calibrate.py --debug`

---

### ❌ "Cannot open camera"

**Solutions:**
1. Verify camera is on (green LED)
2. Test connection: `ping 192.168.1.199`
3. Check credentials in CONFIGURATION section
4. Check firewall/network

---

### ⚠️ Confidence Always Low (<0.50)

**Solutions:**
1. Verify calibration (correct area?)
2. Improve lighting (no reflections)
3. Center book in area
4. Try different model (EasyOCR for maximum accuracy)
5. Check camera focus

---

### ⚠️ Wrong Title/Author/Publisher

**Common causes:**
- Very artistic/complex cover
- Decorative fonts
- Text over background images

**Solutions:**
1. Check raw text blocks in output
2. Try EasyOCR (better for complex fonts)
3. Ensure preprocessing is enabled
4. Check lighting and focus

---

### ⚠️ Old Frame Captured

**Symptom:** When changing book, previous book is scanned

**Solution:** System already flushes buffer (30 frames).
If persists:
- Wait 2-3 seconds before pressing ENTER
- Verify stream is not delayed

---

## 📈 Expected Performance

### With Optimal Setup

**Image quality:**
- Sharpness: >300
- Contrast: >70
- Rotation: <2°

**OCR Performance:**
- **EasyOCR:** ~15-18s/book, 3-4 books/min, confidence >0.70
- **Tesseract:** ~8s/book, 7 books/min, confidence >0.70
- **PP-OCR:** ~3-5s/book, 12-15 books/min, confidence >0.65

**Daily throughput:**
- Manual mode: ~200-300 books/hour
- Auto mode: ~180-240 books/hour (with EasyOCR)

---

## 🎯 Best Practices

### For Maximum Accuracy
1. Use `--model easyocr`
2. Keep preprocessing enabled
3. Uniform lighting (no reflections)
4. Center book in area
5. Check camera focus (sharpness >300)

### For Maximum Speed
1. Use `--model ppocr` or `--model tesseract`
2. Auto mode: `--auto`
3. Consider `--no-preprocessing` if images already optimal

### For Production
1. Calibrate area once at start
2. Verify with 3-5 test books
3. Use manual mode for quality control
4. Periodic backup of `ocr_results.csv`

---

## 📁 File Structure

```
.
├── calibrate.py              # Calibration script (standalone)
├── scan_books.py             # Continuous scanning script (standalone)
├── README.md                 # This file
├── test_images/              # Images and config directory
│   ├── loading_area.txt      # Calibrated area coordinates
│   ├── calibration_preview.jpg
│   └── book_*.jpg            # Scanned book images
└── ocr_results.csv           # Results log
```

---

## 🆘 Support

**For issues:**
1. Check QUICK_START.md for detailed setup
2. Use debug mode: `python3 calibrate.py --debug`
3. Check debug images in `debug_*.jpg`
4. See CLAUDE.md for complete technical context

---

## ✅ Quick Checklist

### Initial Setup
- [ ] 4 X markers drawn (5-8cm, black, bold)
- [ ] Camera on and connected
- [ ] Lighting verified
- [ ] Calibration executed: `python3 calibrate.py`
- [ ] Preview verified (green rectangle correct)
- [ ] OCR model installed

### Each Session
- [ ] Loading area clean
- [ ] Uniform lighting
- [ ] Test on first book (validation)
- [ ] Verify confidence >0.70

### End of Session
- [ ] Backup `ocr_results.csv`
- [ ] Check final statistics

---

**System ready!** 🚀

Setup time: ~30 minutes
Time per book: ~8-18s (depends on model)
Throughput: ~180-420 books/hour
