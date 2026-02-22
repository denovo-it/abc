# A.B.C. - A.I. Book Cataloguer

Automatic book cataloguing system via cover OCR, built for the Axelera Challenge.

The system captures book covers from an RTSP camera, runs multi-pass OCR with
optional hardware acceleration, then identifies books against a local database
of 55M+ titles from Open Library.

**License:** MIT - Copyright 2026 Denovo s.r.l.

---

## Key Features

- Multi-pass OCR (upscale 2x + raw image, merged by confidence)
- Three OCR modes: CPU, Metis accelerator, Hybrid ensemble
- Database identification with cascading search and fuzzy matching
- Language filtering (English, Italian, or all)
- RTSP camera with automatic buffer flush
- Fully offline, no external APIs

---

## Hardware

- **Board:** Orange Pi 5 Plus (RK3588, 16GB RAM)
- **AI Accelerator:** Axelera Metis (M.2 PCIe)
- **Camera:** SONOFF CAM-S2 (RTSP, 1920x1080)
- **OS:** Ubuntu 22.04 arm64

---

## Project Structure

```
abc/
  electronics/           # Hardware setup and specifications
  mechanical/            # Mechanical design (3D printed support)
  software/
    ocr-module/            # OCR scanning and book identification
      scan_books.py      # Main scanner with OCR pipeline
      setup_database.py  # Database management and Open Library import
      calibrate.py       # Camera calibration (X marker detection)
      doc/README.md      # Software documentation
    voyager-sdk/         # Axelera Voyager SDK v1.5.2
```

---

## Quick Start

```bash
cd software/ocr-module
source venv/bin/activate

# Calibrate loading area (one-time)
python3 calibrate.py

# Scan books (default: hybrid mode, all languages)
python3 scan_books.py

# CPU-only mode (no Metis needed)
python3 scan_books.py --model cpu
```

See [software/ocr-module/doc/README.md](software/ocr-module/doc/README.md) for
detailed usage, OCR models, and troubleshooting.

---

## Book Data Source

The book database is built from **Open Library** (https://openlibrary.org),
a project of the Internet Archive.

- **Data:** Open Library Editions Dump (~12GB compressed, ~55M book records)
- **License:** Open Database License (ODbL) v1.0
- **Content:** Title, author, publisher, ISBN, year, language for each edition

The data is entirely factual/bibliographic (not copyrighted text) and is
explicitly provided under an open license for any use.
