# OCR Software Documentation

## OCR Models

| Model | Command | Speed | Description |
|-------|---------|-------|-------------|
| **hybrid** (default) | `--model hybrid` | ~8s/book | CPU + Metis ensemble, best accuracy |
| **cpu** | `--model cpu` | ~6s/book | CPU-only PP-OCR, no accelerator needed |
| **metis** | `--model metis` | ~4s/book | Metis detection + CPU recognition |

All modes use PaddleOCR v3 Latin for text recognition. The difference is in
text detection: CPU uses PaddleOCR's built-in detector, Metis uses the Axelera
hardware accelerator, and Hybrid runs both and merges the best results per
text line.

### Multi-Pass OCR

When preprocessing is enabled (default), each mode runs 10 passes:
1. **Pass 1:** Image upscaled 2x + light denoising - captures small text (publisher, subtitle)
2. **Pass 2:** Raw original image - captures large/artistic text (title, author)
3. **Passes 3-10:** Color filter variants (grayscale, inverted, R/G/B channels, inverted R/G/B) - reveals text hidden by artistic colors

Results are merged by picking the highest-confidence detection per text line.
Disable color filters with `--no-color-filters` for 2-pass mode. Disable all preprocessing with `--no-preprocessing` for single-pass mode.

---

## Hardware Usage by OCR Mode

### CPU Mode (`--model cpu`)

PP-OCR v3 Latin, full pipeline on CPU.

```
CPU:     19-48% (all 8 cores active)
Metis:   0% - IDLE
RAM:     ~1.2 GB
Speed:   ~6s/book (with multi-pass)
```

### Metis Mode (`--model metis`)

Metis accelerated text detection + CPU text recognition.

```
CPU:     10-25% (recognition only)
Metis:   ACTIVE (text detection)
RAM:     ~1.2 GB
Speed:   ~4s/book (with multi-pass)
```

The compiled PP-OCR detection model (`ppocr_det.axnet`) runs on the Metis
accelerator. Input is preprocessed to quantized int8 NHWC format, output
heatmap is dequantized and postprocessed on CPU. Text regions are then
cropped and sent to PaddleOCR CPU recognition.

### Hybrid Mode (`--model hybrid`) - DEFAULT

Runs both CPU and Metis detection in parallel, merges best results per line.

```
CPU:     25-50% (full PP-OCR + recognition)
Metis:   ACTIVE (text detection)
RAM:     ~1.2 GB
Speed:   ~8s/book (with multi-pass)
```

For each text line detected, the result with the highest confidence is selected
from either the CPU or Metis pipeline. This provides the best overall accuracy
at the cost of slightly more processing time.

### Performance Summary

| Mode | Speed | CPU | Metis | Best for |
|------|-------|-----|-------|----------|
| cpu | ~6s/book | 48% | idle | No accelerator available |
| metis | ~4s/book | 25% | active | Speed priority |
| hybrid | ~8s/book | 50% | active | Maximum accuracy (default) |

All times include multi-pass OCR. With `--no-preprocessing`: roughly half.

---

## Database Identification

After OCR, the system searches a local SQLite database (18GB, 55M+ books) to
identify the scanned book. The search uses a cascading strategy:

1. Author exact match (indexed)
2. Author + title prefix (indexed)
3. FTS5 keyword search on raw OCR words
4. OL key resolution (author name to Open Library key)
5. Scoring with title, author, publisher, and raw word overlap

Results below 60% confidence are shown as "UNCERTAIN MATCH" with OCR data
displayed as primary information.

### Language Filter

Use `--lang` to restrict database search to a specific language:

```bash
python3 scan_books.py --lang it    # Italian books only
python3 scan_books.py --lang en    # English books only
python3 scan_books.py               # All languages (default)
```

---

## Building the Database

```bash
# Download Open Library dump (~12GB, takes a while)
python3 setup_database.py download

# Import into SQLite (all languages)
python3 setup_database.py import

# Import only Italian books
python3 setup_database.py import --lang it

# Build full-text search index (recommended, ~20-40 min)
python3 setup_database.py create-fts

# Check statistics
python3 setup_database.py stats
```

---

## Command Line Reference

```
python3 scan_books.py [OPTIONS]

Options:
  --model {cpu,metis,hybrid}  OCR model (default: hybrid)
  --lang {en,it}              Filter DB by language (default: all)
  --auto                      Auto mode (3s between scans)
  --no-preprocessing          Single pass, no upscale
  --no-color-filters          Skip color filter passes (2 passes instead of 10)
  --debug                     Save intermediate images
```

### Interactive Commands

During manual scanning:
- `ENTER` - Scan next book
- `s` + ENTER - Show session statistics
- `q` + ENTER - Quit

---

## File Structure

```
software/
  app.py                # Main pipeline (state machine)
  .env                  # Configuration (from doc/env_example.txt)
  results.csv           # Scan results log (not in git)
  config/
    loading_area.txt    # Calibration coordinates
    empty_reference.jpg # Empty area reference for correlation
    calibration_preview.jpg  # Visual preview of calibrated area
    books.db            # SQLite database (18GB, not in git)
  tools/
    calibrate.py        # Camera calibration (X marker detection)
    display.py          # Fullscreen UI overlays and rendering
    config.py           # .env loader and RTSP configuration
    scan_books.py       # OCR engine with preprocessing and parsing
    setup_database.py   # Database management and Open Library import
    start_abc.sh        # Autostart wrapper (waits for X11)
    doc/
      README.md         # This file (OCR documentation)
  doc/
    env_example.txt     # Environment configuration template
    flow/               # Pipeline flow documentation
    qr-code/            # QR code images for runtime commands
  voyager-sdk/          # Axelera SDK (external fork, do not modify)
```

---

## Troubleshooting

**"Loading area not calibrated"** - Run `python3 tools/calibrate.py` first

**"Metis unavailable"** - System falls back to CPU automatically. Check that
Axelera device is connected and driver loaded (`lsmod | grep axl`)

**Low confidence / wrong results** - Try `--model cpu` (sometimes more
consistent), check lighting and camera focus, ensure book is centered

**H.264 decode errors** - Normal during RTSP buffer flush, suppressed
automatically. No impact on scan quality.
