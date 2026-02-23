#!/usr/bin/env python3
"""
A.B.C. Pipeline - Integrated book detection, OCR, and feedback loop.

State machine:
  WATCHING -> SCANNING -> FEEDBACK -> WAITING -> WATCHING
  (book detected)  (OCR+DB)  (gesture)  (book removed)

Requires:
  - Local venv activated (source venv/bin/activate)
  - RTSP camera reachable (config from .env)
  - Metis NPU connected
  - Pose model compiled for feedback (optional with --no-feedback)

Usage:
  cd software
  source venv/bin/activate
  python app.py --no-feedback         # Skip gesture phase
  python app.py                       # Full pipeline with gesture feedback
  python app.py --ocr-model hybrid    # Use hybrid OCR (cpu+metis ensemble)
"""

import argparse
import gc
import os
import re
import select
import sys
import time
import warnings

# Suppress harmless warnings on Orange Pi (no CUDA/ROCm, no GLX in headless)
os.environ.setdefault('ORT_LOG_LEVEL', '3')
os.environ.setdefault('LIBGL_ALWAYS_SOFTWARE', '1')
os.environ.setdefault('MESA_GL_VERSION_OVERRIDE', '3.3')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')      # silence TFLite/MediaPipe logs
os.environ.setdefault('GLOG_minloglevel', '2')           # silence MediaPipe C++ warnings
warnings.filterwarnings('ignore', message='.*device_discovery.*')

# Redirect stderr briefly to suppress libGL errors from OpenCV import
import io as _io
_stderr_backup = sys.stderr
sys.stderr = _io.StringIO()
import cv2
sys.stderr = _stderr_backup
del _stderr_backup, _io
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = _SCRIPT_DIR  # pipeline.py lives at software/ level
_OCR_DIR = os.path.join(_PROJECT_ROOT, 'ocr-module')
_SDK_DIR = os.path.join(_PROJECT_ROOT, 'voyager-sdk')

# ---------------------------------------------------------------------------
# Environment bootstrap
# ---------------------------------------------------------------------------


def _load_env(path):
    """Load KEY=VALUE pairs from a .env file into os.environ."""
    from config import load_env_file
    load_env_file(path)


def _bootstrap_axelera_env():
    """Set Axelera SDK environment variables programmatically.

    Equivalent to sourcing object-recognition-module/venv/bin/activate lines 91-123.
    Must be called before any axelera imports.
    """
    if os.environ.get('AXELERA_FRAMEWORK'):
        return  # Already set (venv activate script ran)

    runtime_dir = '/opt/axelera/runtime-1.5.2-1'
    device_dir = '/opt/axelera/device-1.5.2-1/omega'
    riscv_dir = '/opt/axelera/riscv-gnu-newlib-toolchain-409b951ba662-7'

    os.environ['AXELERA_RUNTIME_DIR'] = runtime_dir
    os.environ['AXELERA_DEVICE_DIR'] = device_dir
    os.environ['AXELERA_RISCV_TOOLCHAIN_DIR'] = riscv_dir
    os.environ['AXELERA_FRAMEWORK'] = _SDK_DIR
    os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
    os.environ['AIPU_FIRMWARE_OMEGA'] = f'{device_dir}/bin/start_axelera_runtime.elf'
    os.environ['AIPU_RUNTIME_STAGE0_OMEGA'] = f'{device_dir}/bin/start_axelera_runtime_stage0.bin'

    tvm_home = f'{runtime_dir}/tvm/tvm-src'
    os.environ['TVM_HOME'] = tvm_home

    def _prepend(var, *dirs):
        old = os.environ.get(var, '')
        new = ':'.join(dirs)
        os.environ[var] = f'{new}:{old}' if old else new

    _prepend('PYTHONPATH', _SDK_DIR, tvm_home)
    _prepend('LD_LIBRARY_PATH', f'{runtime_dir}/lib', f'{_SDK_DIR}/operators/lib')
    _prepend('GST_PLUGIN_PATH',
             f'{runtime_dir}/lib/gstreamer-1.0', f'{_SDK_DIR}/operators/lib')
    _prepend('PKG_CONFIG_PATH',
             f'{runtime_dir}/lib/pkgconfig', f'{_SDK_DIR}/operators/lib/pkgconfig')

    for d in (f'{runtime_dir}/bin', f'{riscv_dir}/bin'):
        if d not in os.environ.get('PATH', ''):
            os.environ['PATH'] = f'{d}:{os.environ["PATH"]}'

    # Also add to sys.path for Python imports
    for p in (_SDK_DIR, tvm_home):
        if p not in sys.path:
            sys.path.insert(0, p)


# Add ocr-module to sys.path FIRST (needed by _load_env -> config)
if _OCR_DIR not in sys.path:
    sys.path.insert(0, _OCR_DIR)

# Load .env and bootstrap SDK environment BEFORE any axelera imports
_load_env(os.path.join(_SCRIPT_DIR, '.env'))
_bootstrap_axelera_env()

# Now safe to import axelera and OCR modules
from axelera.app import config as ax_config  # noqa: E402
from axelera.app import create_inference_stream  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BOOK_CLASS_ID = 73
PERSON_CLASS_ID = 0
DETECTION_MODEL = 'yolov8l-coco-onnx'

# ---------------------------------------------------------------------------
# Loading area (detection region filter)
# ---------------------------------------------------------------------------

_loading_area = None


def _load_loading_area():
    """Load calibrated loading area from ocr-module config."""
    global _loading_area
    if _loading_area is not None:
        return _loading_area

    config_file = os.path.join(_OCR_DIR, 'test_images', 'loading_area.txt')
    if not os.path.exists(config_file):
        print("  WARNING: No loading_area.txt found, detection uses full frame")
        _loading_area = ()  # empty tuple = disabled
        return _loading_area

    with open(config_file, 'r') as f:
        coords = f.readline().strip()
        _loading_area = tuple(map(int, coords.split(',')))
    return _loading_area


def _det_in_loading_area(det_box, loading_area):
    """Check if detection bounding box overlaps with loading area."""
    if not loading_area:
        return True  # no loading area configured, accept all
    dx1, dy1, dx2, dy2 = det_box
    lx1, ly1, lx2, ly2 = loading_area
    return dx1 < lx2 and dx2 > lx1 and dy1 < ly2 and dy2 > ly1


# ---------------------------------------------------------------------------
# RTSP URL
# ---------------------------------------------------------------------------

def _rtsp_url():
    """Build RTSP URL from environment variables."""
    from config import RTSPConfig
    return RTSPConfig.get_url()


def _rtsp_url_safe(url):
    """Return URL with credentials hidden."""
    if '@' in url and '//' in url:
        return f"{url.split('@')[0].split('//')[0]}//<credentials>@{url.split('@')[1]}"
    return url


# ---------------------------------------------------------------------------
# Startup checks
# ---------------------------------------------------------------------------

def _kill_stale_metis():
    """Kill processes holding Metis device to avoid allocation failures."""
    import subprocess
    try:
        result = subprocess.run(
            ['fuser', '/dev/metis-0:1:0'],
            capture_output=True, text=True, timeout=5
        )
        pids = result.stdout.strip().split()
        my_pid = str(os.getpid())
        for pid in pids:
            pid = pid.strip()
            if pid and pid != my_pid:
                print(f"  Killing stale process {pid} holding Metis device")
                subprocess.run(['kill', '-9', pid], capture_output=True, timeout=5)
                time.sleep(0.5)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# STATE: WATCHING - detect book via YOLOv8 on Metis NPU
# ---------------------------------------------------------------------------

def watch_for_book(rtsp_url, confidence_threshold=0.30, consecutive_needed=5,
                   debug=False):
    """Watch RTSP stream for a book. Returns captured BGR frame when found.

    Uses YOLOv8 object detection on Metis NPU. Requires N consecutive frames
    with a book detection above the confidence threshold.
    """
    print("\n" + "=" * 60)
    print("  WATCHING for book...")
    print("=" * 60)

    pipeline_cfg = ax_config.PipelineConfig(
        network=DETECTION_MODEL,
        sources=[rtsp_url],
        pipe_type='gst',
    )
    stream_cfg = ax_config.InferenceStreamConfig(
        timeout=10,
        frames=0,  # continuous
    )

    stream = create_inference_stream(
        stream_config=stream_cfg,
        pipeline_configs=pipeline_cfg,
    )

    loading_area = _load_loading_area()
    consecutive_book = 0
    frame_count = 0
    captured_frame = None
    dot_count = 0

    try:
        for frame_result in stream:
            if frame_result.image is None and frame_result.meta is None:
                continue

            frame_count += 1
            has_book = False
            book_score = 0.0
            person_score = 0.0

            for det in frame_result.detections:
                cid = int(det.class_id)
                score = float(det.score)
                if not _det_in_loading_area(det.box.tolist(), loading_area):
                    continue  # ignore detections outside loading area
                if cid == BOOK_CLASS_ID and score >= confidence_threshold:
                    has_book = True
                    book_score = max(book_score, score)
                if cid == PERSON_CLASS_ID:
                    person_score = max(person_score, score)

            if has_book:
                consecutive_book += 1
                if debug:
                    print(f"  Frame {frame_count}: book {book_score*100:.0f}%"
                          f" person {person_score*100:.0f}%"
                          f" [{consecutive_book}/{consecutive_needed}]")
                else:
                    sys.stdout.write('+')
                    sys.stdout.flush()
                    dot_count += 1

                if consecutive_book >= consecutive_needed:
                    # Capture the frame
                    try:
                        captured_frame = frame_result.image.asarray('BGR').copy()
                    except Exception as e:
                        print(f"\n  Frame capture failed: {e}")
                        consecutive_book = 0
                        continue
                    if not debug:
                        print()  # newline after dots
                    print(f"  Book detected! ({book_score*100:.0f}% confidence,"
                          f" {consecutive_needed} consecutive frames)")
                    break
            else:
                if consecutive_book > 0 and debug:
                    print(f"  Frame {frame_count}: no book (reset)")
                consecutive_book = 0
                if not debug:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                    dot_count += 1
                    if dot_count >= 80:
                        print()
                        dot_count = 0

    except KeyboardInterrupt:
        if not debug and dot_count > 0:
            print()
        raise
    except RuntimeError as e:
        if not debug and dot_count > 0:
            print()
        print(f"  Inference stream error: {e}")
        print("  Retrying...")
    finally:
        stream.stop()

    return captured_frame


# ---------------------------------------------------------------------------
# STATE: SCANNING - run OCR pipeline on captured frame
# ---------------------------------------------------------------------------

# Lazy-loaded OCR globals
_ocr_components = None


def _init_ocr_components(ocr_model, debug=False):
    """Import and initialize OCR components from ocr-module."""
    global _ocr_components
    if _ocr_components is not None:
        return _ocr_components

    print("  Loading OCR components...")

    # Import from ocr-module
    from scan_books import (
        BookCoverPreprocessor,
        BookCoverParser,
        OCRPostProcessor,
        TextBox,
        run_ocr_ppocr,
        run_ocr_metis,
        run_ocr_ppocr_metis,
        _merge_ensemble_results,
    )
    from setup_database import BookDatabase

    preprocessor = BookCoverPreprocessor(debug=debug)
    parser = BookCoverParser(debug=debug)
    postprocessor = OCRPostProcessor(debug=debug)

    # Preload PaddleOCR model
    print("  Loading PP-OCR models...", end='', flush=True)
    import scan_books as sb
    if sb._ppocr_instance is None:
        import warnings
        warnings.filterwarnings('ignore', category=UserWarning)
        from paddleocr import PaddleOCR
        sb._ppocr_instance = PaddleOCR(
            use_angle_cls=True, lang='latin', use_gpu=False, show_log=False
        )
        # Warmup
        dummy = '/tmp/_pipeline_warmup.jpg'
        cv2.imwrite(dummy, np.zeros((64, 200, 3), dtype=np.uint8))
        sb._ppocr_instance.ocr(dummy, cls=True)
        try:
            os.remove(dummy)
        except OSError:
            pass
        warnings.resetwarnings()
    print(" done")

    # Load Metis det model if needed
    if ocr_model in ('metis', 'hybrid'):
        print("  Loading Metis OCR det model...", end='', flush=True)
        result = sb._init_metis_det()
        if result:
            print(" done")
        else:
            print(" (unavailable, will fall back to CPU)")

    _ocr_components = {
        'preprocessor': preprocessor,
        'parser': parser,
        'postprocessor': postprocessor,
        'TextBox': TextBox,
        'run_ocr_ppocr': run_ocr_ppocr,
        'run_ocr_metis': run_ocr_metis,
        'run_ocr_ppocr_metis': run_ocr_ppocr_metis,
        'merge_ensemble': _merge_ensemble_results,
        'BookDatabase': BookDatabase,
        'scan_books_module': sb,
    }
    return _ocr_components


def _select_ocr_func(components, ocr_model):
    """Return the OCR function for the given model name."""
    if ocr_model == 'cpu':
        return components['run_ocr_ppocr']
    elif ocr_model == 'metis':
        return components['run_ocr_metis']
    elif ocr_model == 'hybrid':
        return components['run_ocr_ppocr_metis']
    raise ValueError(f"Unknown OCR model: {ocr_model}")


def _run_ocr_multipass(image, ocr_func, preprocessor, merge_fn, color_filters=False,
                       debug=False):
    """Multi-pass OCR replicating ContinuousScanner._run_ocr_multipass() logic."""
    all_pass_boxes = []
    temp_files = []
    scale = 2.0
    total_passes = 2 + (8 if color_filters else 0)

    # Pass 1: Upscale 2x + denoise
    print(f"   Pass 1/{total_passes}: Upscale {scale:.0f}x + denoise...",
          end='', flush=True)
    upscaled = preprocessor.preprocess_for_ppocr_upscale(image, scale)
    temp_up = '/tmp/pipeline_ocr_upscale.jpg'
    cv2.imwrite(temp_up, upscaled)
    temp_files.append(temp_up)

    from scan_books import TextBox
    boxes_upscale = ocr_func(temp_up)
    boxes_upscale = [
        TextBox(b.text,
                (b.bbox[0] / scale, b.bbox[1] / scale,
                 b.bbox[2] / scale, b.bbox[3] / scale),
                b.confidence)
        for b in boxes_upscale
    ]
    all_pass_boxes.append(boxes_upscale)
    print(f" done ({len(boxes_upscale)} blocks)")

    # Pass 2: Raw image
    print(f"   Pass 2/{total_passes}: Raw image...", end='', flush=True)
    temp_raw = '/tmp/pipeline_ocr_raw.jpg'
    cv2.imwrite(temp_raw, image)
    temp_files.append(temp_raw)
    boxes_raw = ocr_func(temp_raw)
    all_pass_boxes.append(boxes_raw)
    print(f" done ({len(boxes_raw)} blocks)")

    # Color filter passes (optional)
    if color_filters:
        filters = preprocessor.generate_color_filters(image)
        for i, (label, filtered) in enumerate(filters, start=3):
            print(f"   Pass {i}/{total_passes}: {label}...", end='', flush=True)
            temp_f = f'/tmp/pipeline_ocr_{label}.jpg'
            cv2.imwrite(temp_f, filtered)
            temp_files.append(temp_f)
            boxes_f = ocr_func(temp_f)
            all_pass_boxes.append(boxes_f)
            print(f" done ({len(boxes_f)} blocks)")

    # Merge all passes
    merged = merge_fn(*all_pass_boxes)
    total_input = sum(len(b) for b in all_pass_boxes)
    print(f"   Merged: {len(merged)} blocks (from {total_input} total"
          f" across {len(all_pass_boxes)} passes)")

    # Cleanup temp files
    for f in temp_files:
        try:
            os.remove(f)
        except OSError:
            pass

    return merged


def _fuzzy_correct_with_databases(text, parser):
    """Apply fuzzy matching with databases for OCR error correction.

    Only queries DB for words with OCR artifacts (digits mixed with letters).
    Replicates ContinuousScanner._fuzzy_correct_with_databases() logic.
    """
    from difflib import SequenceMatcher

    words = text.split()
    corrected_words = []

    for word in words:
        if len(word) < 3:
            corrected_words.append(word)
            continue

        word_upper = word.upper()

        if word_upper in parser.publisher_imprints:
            corrected_words.append(word)
            continue

        has_digits = any(c.isdigit() for c in word)
        has_letters = any(c.isalpha() for c in word)
        has_ocr_artifacts = has_digits and has_letters

        if not has_ocr_artifacts:
            corrected_words.append(word)
            continue

        best_match = None

        for imprint in parser.publisher_imprints.keys():
            ratio = SequenceMatcher(None, word_upper, imprint).ratio()
            if ratio >= 0.80:
                best_match = imprint
                break

        if not best_match and parser.book_db:
            match = parser.book_db.fuzzy_match_author_sql(word, threshold=0.80)
            if match:
                best_match = match.upper()
            else:
                match = parser.book_db.fuzzy_match_publisher_sql(word, threshold=0.80)
                if match:
                    best_match = match.upper()

        if best_match:
            corrected_words.append(best_match.title())
        else:
            corrected_words.append(word)

    return ' '.join(corrected_words)


def _identify_book(book_info, parser, lang=None):
    """Identify book from OCR results using database.

    Replicates ContinuousScanner.identify_book() logic.
    """
    if not parser.book_db:
        return {'matched': False, 'book': None, 'match_confidence': 0.0,
                'alternatives': []}

    from scan_books import ContinuousScanner

    raw_text = book_info.get('raw_text', '')
    title = book_info.get('title', '')
    author = book_info.get('author', '')
    publisher = book_info.get('publisher', '')

    exclude_words = set(ContinuousScanner.STOPWORDS)
    for imprint in parser.publisher_imprints:
        for w in imprint.lower().split():
            if len(w) >= 3:
                exclude_words.add(w)
    if publisher and publisher != '[not identified]':
        for w in publisher.lower().split():
            if len(w) >= 3:
                exclude_words.add(w)
    exclude_words.update(['bestsellers', 'bestseller', 'edition', 'edizione'])

    raw_words = []
    if raw_text:
        for word in re.split(r'[\s\n]+', raw_text):
            word_clean = re.sub(r'[^\w]', '', word).lower()
            if len(word_clean) >= 3 and word_clean not in exclude_words:
                raw_words.append(word_clean)

    return parser.book_db.identify_book(title, author, publisher, raw_words,
                                        language=lang)


def scan_book(frame, ocr_model='cpu', color_filters=False, lang=None,
              debug=False):
    """Run the full OCR pipeline on a captured frame.

    Returns (book_info_dict, db_result_dict).
    """
    components = _init_ocr_components(ocr_model, debug=debug)
    preprocessor = components['preprocessor']
    parser = components['parser']
    postprocessor = components['postprocessor']
    merge_fn = components['merge_ensemble']
    ocr_func = _select_ocr_func(components, ocr_model)

    model_label = 'hybrid (cpu + metis)' if ocr_model == 'hybrid' else ocr_model
    print(f"\n  SCANNING ({model_label})...")

    # Multi-pass OCR
    text_boxes = _run_ocr_multipass(
        frame, ocr_func, preprocessor, merge_fn,
        color_filters=color_filters, debug=debug,
    )

    # Fuzzy DB correction
    print(f"   Fuzzy DB correction ({len(text_boxes)} blocks)...",
          end='', flush=True)
    from scan_books import TextBox
    corrected_text_boxes = []
    for box in text_boxes:
        corrected_text = postprocessor._correct_words(box.text)
        corrected_text = _fuzzy_correct_with_databases(corrected_text, parser)
        from collections import namedtuple
        CorrectedBox = namedtuple('TextBox', ['text', 'confidence', 'bbox'])
        corrected_box = CorrectedBox(corrected_text, box.confidence, box.bbox)
        corrected_text_boxes.append(corrected_box)
    print(" done")

    # Parse
    print(f"   Parsing book information...", end='', flush=True)
    img_h, img_w = frame.shape[:2]
    book_info_obj = parser.parse(corrected_text_boxes, img_h, img_w, image=frame)

    book_dict = {
        'title': book_info_obj.title or '[not identified]',
        'author': book_info_obj.author or '[not identified]',
        'publisher': book_info_obj.publisher or '[not identified]',
        'confidence': book_info_obj.confidence,
        'raw_text': '\n'.join(b.text for b in text_boxes),
    }
    print(" done")

    # Post-processing
    improved = postprocessor.improve_result(book_dict)

    # Database identification
    print(f"   Searching database...", end='', flush=True)
    db_result = _identify_book(improved, parser, lang=lang)
    if db_result['matched']:
        print(" found!")
    else:
        print(" not found")

    return improved, db_result


def display_result(book_info, db_result, book_count):
    """Display OCR result in the same format as scan_books.py."""
    MIN_DB_CONFIDENCE = 0.60

    db_matched = (db_result and db_result.get('matched') and db_result.get('book'))
    db_confident = db_matched and db_result['match_confidence'] >= MIN_DB_CONFIDENCE

    print("\n" + "=" * 70)
    print(f"   BOOK #{book_count}")
    print("=" * 70)

    if db_confident:
        book = db_result['book']
        confidence_pct = int(db_result['match_confidence'] * 100)
        print(f"  Title:      {book.title}")
        print(f"  Author:     {book.author}")
        if book.publisher:
            print(f"  Publisher:  {book.publisher}")
        if book.isbn:
            print(f"  ISBN:       {book.isbn}")
        if book.year:
            print(f"  Year:       {book.year}")
        if book.language:
            lang_names = {'en': 'English', 'it': 'Italiano', 'fr': 'Francais',
                          'es': 'Espanol', 'de': 'Deutsch'}
            print(f"  Language:   {lang_names.get(book.language, book.language)}")
        print(f"  Match:      {confidence_pct}%")
    else:
        print(f"  Title:      {book_info['title']}")
        print(f"  Author:     {book_info['author']}")
        print(f"  Publisher:  {book_info['publisher']}")
        if db_matched:
            print(f"  Match:      {int(db_result['match_confidence'] * 100)}% (uncertain)")
        else:
            print(f"  Match:      not found in DB")

    print("=" * 70)

    # Details
    print(f"\n  Details:")
    print(f"  |- OCR read:    {book_info['title']} / {book_info['author']}"
          f" / {book_info['publisher']}")

    if db_matched:
        book = db_result['book']
        confidence_pct = int(db_result['match_confidence'] * 100)
        if db_confident:
            print(f"  |- DB match:    {book.title} - {book.author} ({confidence_pct}%)")
            print(f"  \\- Result:      DB match used (>= {int(MIN_DB_CONFIDENCE*100)}% threshold)")
        else:
            print(f"  |- DB candidate: {book.title} - {book.author} ({confidence_pct}%)")
            print(f"  \\- Result:      OCR data used (DB match below {int(MIN_DB_CONFIDENCE*100)}% threshold)")
    else:
        print(f"  |- DB match:    none")
        print(f"  \\- Result:      OCR data used (no DB match)")

    # Alternatives
    if db_matched:
        alternatives = db_result.get('alternatives', [])
        if alternatives:
            print(f"\n  Alternatives:")
            for alt_book, alt_score in alternatives:
                alt_pct = int(alt_score * 100)
                pub_info = f" ({alt_book.publisher})" if alt_book.publisher else ""
                print(f"    [{alt_pct}%] {alt_book.title} - {alt_book.author}{pub_info}")

    # Raw OCR blocks
    if 'raw_text' in book_info:
        print(f"\n  Raw OCR blocks:")
        raw_lines = book_info['raw_text'].split('\n') if book_info['raw_text'] else []
        for i, line in enumerate(raw_lines[:10], 1):
            if line.strip():
                print(f"    {i}. {line.strip()}")
        if len(raw_lines) > 10:
            print(f"    ... and {len(raw_lines) - 10} more")


# ---------------------------------------------------------------------------
# STATE: FEEDBACK - detect crossed index fingers via MediaPipe Hands
# ---------------------------------------------------------------------------

_mp_hands = None


def _init_mediapipe_hands():
    """Lazy-init MediaPipe Hands detector (singleton)."""
    global _mp_hands
    if _mp_hands is not None:
        return _mp_hands

    # Suppress noisy C++ warnings from TFLite/abseil/cpuinfo during init
    stderr_fd = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 2)
    try:
        import mediapipe as mp
        _mp_hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.4,
        )
    finally:
        os.dup2(stderr_fd, 2)
        os.close(stderr_fd)
        os.close(devnull)

    return _mp_hands


def _detect_crossed_fingers(frame, hands, debug=False):
    """Detect crossed index fingers gesture using MediaPipe Hands.

    Returns True if both hands are visible with index fingers extended and
    crossing each other (forming an X shape).

    MediaPipe hand landmarks:
      5 = INDEX_FINGER_MCP (base)
      6 = INDEX_FINGER_PIP
      7 = INDEX_FINGER_DIP
      8 = INDEX_FINGER_TIP
    """
    # MediaPipe expects RGB; suppress C++ warnings during inference
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    stderr_fd = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 2)
    try:
        result = hands.process(rgb)
    finally:
        os.dup2(stderr_fd, 2)
        os.close(stderr_fd)
        os.close(devnull)

    n_hands = len(result.multi_hand_landmarks) if result.multi_hand_landmarks else 0
    if debug:
        print(f"  [mp] hands={n_hands}", end='')
    if n_hands < 2:
        if debug:
            print()
        return False

    h, w = frame.shape[:2]
    fingers = []

    for hand_lms in result.multi_hand_landmarks[:2]:
        lm = hand_lms.landmark

        # Index finger landmarks (normalized 0-1)
        mcp = lm[5]   # base
        pip_ = lm[6]  # middle joint
        tip = lm[8]   # tip

        # Check index finger is extended: tip is further from wrist than PIP
        wrist = lm[0]
        tip_d = np.sqrt((tip.x - wrist.x)**2 + (tip.y - wrist.y)**2)
        pip_d = np.sqrt((pip_.x - wrist.x)**2 + (pip_.y - wrist.y)**2)
        extended = tip_d > pip_d * 1.1
        if debug:
            print(f" idx_ext={extended}({tip_d:.2f}/{pip_d:.2f})", end='')
        if not extended:
            continue  # finger not extended

        # Store finger line (base to tip) in pixel coords
        fingers.append({
            'base': (mcp.x * w, mcp.y * h),
            'tip': (tip.x * w, tip.y * h),
        })

    if debug:
        print(f" valid_fingers={len(fingers)}")
    if len(fingers) < 2:
        return False

    f1, f2 = fingers[0], fingers[1]

    # Check tips are close together (within 15% of frame width)
    tip_dist = np.sqrt((f1['tip'][0] - f2['tip'][0])**2 +
                       (f1['tip'][1] - f2['tip'][1])**2)
    close_threshold = w * 0.15
    if tip_dist > close_threshold:
        if debug:
            print(f"  Tips too far: {tip_dist:.0f}px (threshold {close_threshold:.0f})")
        return False

    # Check fingers cross: the two line segments (base→tip) intersect.
    # Use cross product to detect opposite orientations.
    d1 = (f1['tip'][0] - f1['base'][0], f1['tip'][1] - f1['base'][1])
    d2 = (f2['tip'][0] - f2['base'][0], f2['tip'][1] - f2['base'][1])
    cross = d1[0] * d2[1] - d1[1] * d2[0]

    # Non-parallel fingers with significant cross product = crossing
    len1 = np.sqrt(d1[0]**2 + d1[1]**2)
    len2 = np.sqrt(d2[0]**2 + d2[1]**2)
    if len1 < 1 or len2 < 1:
        return False

    sin_angle = abs(cross) / (len1 * len2)
    crossed = sin_angle > 0.3  # angle > ~17 degrees

    if debug:
        print(f"  Fingers: tips_dist={tip_dist:.0f}px"
              f" sin_angle={sin_angle:.2f} crossed={crossed}")

    return crossed


# ---------------------------------------------------------------------------
# STATE: WAITING - wait for removal OR detect rejection gesture
# ---------------------------------------------------------------------------

def wait_for_removal(rtsp_url, confidence_threshold=0.30, feedback=True,
                     debug=False):
    """Wait until the scanned book is removed from the scene.

    Uses YOLOv8 object detection on Metis NPU (same as WATCHING).
    When a person is detected AND feedback is enabled, grabs the frame and
    checks for crossed index fingers via MediaPipe (reject gesture).

    Exits when:
      - Crossed fingers detected (person + gesture) -> 'reject'
      - A person appears without gesture (removing book) -> 'continue'
      - The book disappears from the scene -> 'continue'
      - The user presses ENTER -> 'quit'

    Returns 'continue', 'reject', or 'quit'.
    """
    print("\n" + "=" * 60)
    if feedback:
        print("  WAITING - Cross fingers to REJECT, remove book to continue")
    else:
        print("  WAITING - Remove book to continue (ENTER to quit)")
    print("=" * 60)

    pipeline_cfg = ax_config.PipelineConfig(
        network=DETECTION_MODEL,
        sources=[rtsp_url],
        pipe_type='gst',
    )
    stream_cfg = ax_config.InferenceStreamConfig(
        timeout=10,
        frames=0,  # continuous
    )

    stream = create_inference_stream(
        stream_config=stream_cfg,
        pipeline_configs=pipeline_cfg,
    )

    hands = _init_mediapipe_hands() if feedback else None
    loading_area = _load_loading_area()
    consecutive_clear = 0
    consecutive_gesture = 0
    clear_frames_needed = 30   # ~1.5s at ~20fps — gives time to show gesture
    gesture_frames_needed = 5  # ~0.25s — quick reject once detected
    frame_count = 0
    dot_count = 0
    result = 'continue'

    try:
        for frame_result in stream:
            # Check if user pressed ENTER (non-blocking stdin poll)
            if select.select([sys.stdin], [], [], 0)[0]:
                sys.stdin.readline()
                if not debug and dot_count > 0:
                    print()
                result = 'quit'
                break

            if frame_result.image is None and frame_result.meta is None:
                continue

            frame_count += 1
            has_book = False
            has_person = False

            for det in frame_result.detections:
                cid = int(det.class_id)
                score = float(det.score)
                if not _det_in_loading_area(det.box.tolist(), loading_area):
                    continue  # ignore detections outside loading area
                if cid == BOOK_CLASS_ID and score >= confidence_threshold:
                    has_book = True
                if cid == PERSON_CLASS_ID and score >= 0.30:
                    has_person = True

            # When person detected + feedback enabled, check for gesture
            # Use FULL frame for MediaPipe (hands may be outside loading area)
            gesture_detected = False
            if has_person and hands is not None:
                try:
                    frame_bgr = frame_result.image.asarray('BGR')

                    # Save first person frame for debugging
                    if debug and consecutive_clear == 0 and consecutive_gesture == 0:
                        dbg_path = '/tmp/gesture_debug_frame.jpg'
                        cv2.imwrite(dbg_path, frame_bgr)
                        print(f"\n  [debug] Saved gesture frame: {dbg_path}"
                              f" ({frame_bgr.shape[1]}x{frame_bgr.shape[0]})")

                    gesture_detected = _detect_crossed_fingers(
                        frame_bgr, hands, debug=debug)
                except Exception as e:
                    if debug:
                        print(f"\n  [debug] Gesture check error: {e}")

            if gesture_detected:
                consecutive_gesture += 1
                consecutive_clear = 0
                if not debug:
                    sys.stdout.write('X')
                    sys.stdout.flush()
                    dot_count += 1
                else:
                    print(f"  Frame {frame_count}: GESTURE"
                          f" [{consecutive_gesture}/{gesture_frames_needed}]")

                if consecutive_gesture >= gesture_frames_needed:
                    if not debug and dot_count > 0:
                        print()
                    print("  Crossed fingers detected!")
                    result = 'reject'
                    break
            else:
                consecutive_gesture = 0

                # Exit condition: person appeared (removing book) OR book gone
                scene_changed = has_person or not has_book

                if scene_changed:
                    consecutive_clear += 1
                    if debug:
                        reason = "person" if has_person else "no book"
                        print(f"  Frame {frame_count}: {reason}"
                              f" [{consecutive_clear}/{clear_frames_needed}]")
                    else:
                        sys.stdout.write('*')
                        sys.stdout.flush()
                        dot_count += 1

                    if consecutive_clear >= clear_frames_needed:
                        if not debug and dot_count > 0:
                            print()
                        reason = "person detected" if has_person else "book removed"
                        print(f"  Scene changed ({reason}), resuming...")
                        break
                else:
                    consecutive_clear = 0
                    if not debug:
                        sys.stdout.write('.')
                        sys.stdout.flush()
                        dot_count += 1
                        if dot_count >= 80:
                            print()
                            dot_count = 0

    except KeyboardInterrupt:
        if not debug and dot_count > 0:
            print()
        raise
    except RuntimeError as e:
        if not debug and dot_count > 0:
            print()
        print(f"  Inference stream error: {e}")
        print("  Continuing...")
    finally:
        stream.stop()

    return result


# ---------------------------------------------------------------------------
# Main pipeline loop
# ---------------------------------------------------------------------------

def run_pipeline(args):
    """Main pipeline state machine loop."""
    rtsp_url = _rtsp_url()

    print("=" * 60)
    print("  A.B.C. PIPELINE")
    print("=" * 60)
    model_label = 'hybrid (cpu + metis)' if args.ocr_model == 'hybrid' else args.ocr_model
    print(f"  OCR model:     {model_label}")
    lang_display = {'en': 'English', 'it': 'Italian'}.get(args.lang, 'All') if args.lang else 'All'
    print(f"  DB language:   {lang_display}")
    print(f"  Detection:     {DETECTION_MODEL} (Metis NPU)")
    print(f"  Confidence:    >= {args.confidence*100:.0f}%")
    print(f"  Consecutive:   {args.consecutive} frames")
    print(f"  Color filters: {'Yes' if args.color_filters else 'No'}")
    feedback_desc = "Crossed fingers (MediaPipe Hands)" if not args.no_feedback else "No (auto-accept)"
    print(f"  Feedback:      {feedback_desc}")
    print(f"  Camera:        {_rtsp_url_safe(rtsp_url)}")
    loading_area = _load_loading_area()
    if loading_area:
        lx1, ly1, lx2, ly2 = loading_area
        print(f"  Loading area:  ({lx1},{ly1})-({lx2},{ly2})"
              f" {lx2-lx1}x{ly2-ly1}px")
    else:
        print(f"  Loading area:  FULL FRAME (no calibration)")
    print("=" * 60)

    # Pre-init MediaPipe Hands for gesture feedback
    if not args.no_feedback:
        print("\n  Loading MediaPipe Hands...", end='', flush=True)
        _init_mediapipe_hands()
        print(" done")

    _kill_stale_metis()

    # Pre-initialize OCR components
    print("\n  Initializing OCR...")
    _init_ocr_components(args.ocr_model, debug=args.debug)
    print("  OCR ready.\n")

    book_count = 0

    try:
        while True:
            # --- WATCHING ---
            gc.collect()
            time.sleep(0.5)

            frame = watch_for_book(
                rtsp_url,
                confidence_threshold=args.confidence,
                consecutive_needed=args.consecutive,
                debug=args.debug,
            )

            if frame is None:
                print("  No frame captured, retrying...")
                continue

            # --- SCANNING ---
            gc.collect()
            time.sleep(0.5)

            book_info, db_result = scan_book(
                frame,
                ocr_model=args.ocr_model,
                color_filters=args.color_filters,
                lang=args.lang,
                debug=args.debug,
            )

            book_count += 1
            display_result(book_info, db_result, book_count)

            # --- WAITING (with integrated gesture detection) ---
            gc.collect()
            time.sleep(0.5)

            wait_result = wait_for_removal(
                rtsp_url,
                confidence_threshold=args.confidence,
                feedback=not args.no_feedback,
                debug=args.debug,
            )

            if wait_result == 'quit':
                print(f"\n  Books scanned: {book_count}")
                print("  Pipeline stopped.\n")
                return
            elif wait_result == 'reject':
                print("  >> REJECTED by user gesture")
            else:
                print("  >> ACCEPTED")

            print()

    except KeyboardInterrupt:
        print("\n\n  Interrupted by user")
        print(f"  Books scanned: {book_count}")
        print("  Pipeline stopped.\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='A.B.C. Pipeline - Integrated book detection, OCR, and feedback'
    )
    parser.add_argument(
        '--ocr-model', choices=['cpu', 'metis', 'hybrid'], default='hybrid',
        help='OCR model (default: hybrid, CPU+Metis ensemble)')
    parser.add_argument(
        '--lang', choices=['en', 'it'], default=None,
        help='Language filter for DB search')
    parser.add_argument(
        '--confidence', type=float, default=0.30,
        help='Book detection confidence threshold (default: 0.30)')
    parser.add_argument(
        '--consecutive', type=int, default=5,
        help='Consecutive frames to confirm book detection (default: 5)')
    parser.add_argument(
        '--color-filters', action='store_true',
        help='Enable extra OCR passes with color filters (slower)')
    parser.add_argument(
        '--no-feedback', action='store_true',
        help='Skip gesture feedback phase (auto-accept)')
    parser.add_argument(
        '--debug', action='store_true',
        help='Enable verbose debug output')

    args = parser.parse_args()
    run_pipeline(args)


if __name__ == '__main__':
    main()
