# OCR Book Cataloguing System

**System:** Orange Pi 5 Plus + Axelera Metis AI Accelerator
**OCR Engine:** PaddleOCR v3 (Latin)
**Database:** Open Library (55M+ books)

---

## Overview

Automatic book scanning and cataloguing via cover OCR. The system captures
book covers from an RTSP camera, runs multi-pass OCR with optional hardware
acceleration, then identifies books against a local database of 55M+ titles.

**Key features:**
- Multi-pass OCR (upscale 2x + raw image, merged by confidence)
- Three OCR modes: CPU, Metis accelerator, Hybrid ensemble
- Database identification with cascading search and fuzzy matching
- Language filtering (English, Italian, or all)
- RTSP camera with automatic buffer flush

---

## Quick Start

```bash
cd /home/orangepi/abc/software/ocr-test
source venv/bin/activate

# Calibrate loading area (one-time)
python3 calibrate.py

# Scan books (default: hybrid mode, all languages)
python3 scan_books.py

# Scan with language filter
python3 scan_books.py --lang it

# CPU-only mode (faster, no Metis needed)
python3 scan_books.py --model cpu
```

---

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

When preprocessing is enabled (default), each mode runs two passes:
1. **Pass 1:** Image upscaled 2x + light denoising - captures small text (publisher, subtitle)
2. **Pass 2:** Raw original image - captures large/artistic text (title, author)

Results are merged by picking the highest-confidence detection per text line.
Disable with `--no-preprocessing` for single-pass mode.

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

## Book Data Source

The book database is built from **Open Library** (https://openlibrary.org),
a project of the Internet Archive.

- **Data:** Open Library Editions Dump (~12GB compressed, ~55M book records)
- **License:** Open Database License (ODbL) v1.0
- **Content:** Title, author, publisher, ISBN, year, language for each edition
- **Usage:** This is public data, freely available for download and use

The data is entirely factual/bibliographic (not copyrighted text) and is
explicitly provided under an open license for any use.

### Building the Database

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
ocr-test/
  calibrate.py          # Camera calibration (X marker detection)
  scan_books.py         # Main scanner with OCR pipeline
  setup_database.py     # Database management and Open Library import
  books.db              # SQLite database (18GB, not in git)
  ocr_results.csv       # Scan results log
  test_images/
    loading_area.txt    # Calibration coordinates
    book_*.jpg          # Captured book images
  doc/
    README.md           # This file
```

---

## Troubleshooting

**"Loading area not calibrated"** - Run `python3 calibrate.py` first

**"Metis unavailable"** - System falls back to CPU automatically. Check that
Axelera device is connected and driver loaded (`lsmod | grep axl`)

**Low confidence / wrong results** - Try `--model cpu` (sometimes more
consistent), check lighting and camera focus, ensure book is centered

**H.264 decode errors** - Normal during RTSP buffer flush, suppressed
automatically. No impact on scan quality.
