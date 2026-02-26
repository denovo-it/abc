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
import subprocess
import sys
import threading
import time
import warnings
from collections import deque

# Ensure X11 display is available (needed when launching via SSH)
if not os.environ.get('DISPLAY'):
    os.environ['DISPLAY'] = ':0'
# Allow any user to access the local display (for SSH sessions)
import subprocess as _sp
try:
    _sp.run(['xhost', '+local:'], capture_output=True, timeout=3,
            env={**os.environ, 'DISPLAY': os.environ['DISPLAY']})
    # Hide mouse cursor (requires unclutter)
    _sp.Popen(['unclutter', '-idle', '0', '-root'],
              stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
              env={**os.environ, 'DISPLAY': os.environ['DISPLAY']})
except Exception:
    pass

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

# Add tools/ to sys.path early (display, calibrate, config live there)
_tools_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools')
if _tools_path not in sys.path:
    sys.path.insert(0, _tools_path)

import display

# Show splash screen immediately (before heavy imports)
display.init_window()
display.draw_splash("Starting up...")

# ---------------------------------------------------------------------------
# QR code detection & diagnostics
# ---------------------------------------------------------------------------

_qr_detector = cv2.QRCodeDetector()
_diag_mode = False
_diag_lines = deque(maxlen=25)


def _diag_log(msg):
    """Log a diagnostic message (print + store for overlay)."""
    ts = time.strftime('%H:%M:%S')
    line = f"{ts} {msg}"
    print(f"  [DIAG] {line}")
    _diag_lines.append(line)


def _check_qr_command(frame_bgr):
    """Check for QR code in frame, return recognized command or None."""
    try:
        data, _, _ = _qr_detector.detectAndDecode(frame_bgr)
        if data:
            cmd = data.strip().upper()
            if cmd in ('DIAG ON', 'DIAG OFF', 'SHUTDOWN NOW', 'CANCEL',
                       'CALIBRATE'):
                return cmd
    except Exception:
        pass
    return None


def _handle_shutdown(rtsp_url_or_stream, get_frame_func):
    """Run 5-second shutdown countdown. Returns True if shutdown proceeds."""
    _diag_log("SHUTDOWN countdown started (5s)")
    deadline = time.time() + 5
    while time.time() < deadline:
        remaining = max(0, int(deadline - time.time()) + 1)
        frame = get_frame_func()
        if frame is not None:
            vis = frame.copy()
            display.draw_shutdown_countdown(vis, remaining)
            if _diag_mode:
                display.draw_diag_overlay(vis, list(_diag_lines))
            display.show(vis)
            # Check for CANCEL QR
            cmd = _check_qr_command(frame)
            if cmd == 'CANCEL':
                _diag_log("SHUTDOWN cancelled")
                return False
        time.sleep(0.1)
    _diag_log("SHUTDOWN executing")
    subprocess.run(['sudo', 'shutdown', '-h', 'now'], timeout=10)
    return True


def _handle_calibration():
    """Run calibration from QR command. Returns True if successful."""
    global _loading_area, _empty_ref
    _diag_log("CALIBRATION started")

    # Show status on screen
    frame = np.zeros((display.SCREEN_H, display.SCREEN_W, 3), dtype=np.uint8)
    cv2.putText(frame, "CALIBRATING...", (200, 280),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 165, 255), 3, cv2.LINE_AA)
    cv2.putText(frame, "Keep X markers visible", (220, 340),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 1, cv2.LINE_AA)
    display.show(frame)

    try:
        from calibrate import calibrate_camera, save_calibration
        rtsp_url = _rtsp_url()
        result = calibrate_camera(rtsp_url, debug=False, show_gui=False)
        if result is None:
            _diag_log("CALIBRATION FAILED: no markers found")
            # Show error for 3 seconds
            frame = np.zeros((display.SCREEN_H, display.SCREEN_W, 3), dtype=np.uint8)
            cv2.putText(frame, "CALIBRATION FAILED", (180, 280),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 255), 3, cv2.LINE_AA)
            cv2.putText(frame, "Could not detect 4 X markers", (180, 340),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 1, cv2.LINE_AA)
            display.show(frame)
            time.sleep(3)
            return False

        rectangle, cal_frame = result
        save_calibration(rectangle, cal_frame)

        # Reset cached calibration data so it reloads
        _loading_area = None
        _empty_ref = None
        _load_loading_area()
        _load_empty_reference()

        x1, y1, x2, y2 = rectangle
        _diag_log(f"CALIBRATION OK: ({x1},{y1})-({x2},{y2})")

        # Show success for 3 seconds
        frame = np.zeros((display.SCREEN_H, display.SCREEN_W, 3), dtype=np.uint8)
        cv2.putText(frame, "CALIBRATION OK", (210, 260),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 200, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, f"Area: {x2-x1}x{y2-y1}px", (300, 320),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 1, cv2.LINE_AA)
        display.show(frame)
        time.sleep(3)
        return True

    except Exception as e:
        _diag_log(f"CALIBRATION error: {e}")
        return False


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = _SCRIPT_DIR  # pipeline.py lives at software/ level
_TOOLS_DIR = os.path.join(_PROJECT_ROOT, 'tools')
_SDK_DIR = os.path.join(_PROJECT_ROOT, 'voyager-sdk')
_CONFIG_DIR = os.path.join(_PROJECT_ROOT, 'config')

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


# tools/ already in sys.path (added before display import)

# Load .env and bootstrap SDK environment BEFORE any axelera imports
_load_env(os.path.join(_SCRIPT_DIR, '.env'))
_bootstrap_axelera_env()

# Now safe to import axelera and OCR modules
display.draw_splash("Loading Axelera SDK...")
from axelera.app import config as ax_config  # noqa: E402
from axelera.app import create_inference_stream  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BOOK_CLASS_ID = 73
PERSON_CLASS_ID = 0
DETECTION_MODEL = 'yolov8l-coco-onnx'
MIN_BOOK_AREA_PCT = 3.0  # minimum book bbox area as % of frame (filters false positives)

# ---------------------------------------------------------------------------
# Loading area (detection region filter)
# ---------------------------------------------------------------------------

_loading_area = None


def _load_loading_area():
    """Load calibrated loading area from tools/ config."""
    global _loading_area
    if _loading_area is not None:
        return _loading_area

    config_file = os.path.join(_CONFIG_DIR, 'loading_area.txt')
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
# Empty area reference (false-positive filter)
# ---------------------------------------------------------------------------

_empty_ref = None  # grayscale crop of empty loading area


def _load_empty_reference():
    """Load empty area reference image from calibration."""
    global _empty_ref
    if _empty_ref is not None:
        return _empty_ref

    ref_path = os.path.join(_CONFIG_DIR, 'empty_reference.jpg')
    if not os.path.exists(ref_path):
        _empty_ref = ()  # empty tuple = not available
        return _empty_ref

    img = cv2.imread(ref_path)
    if img is not None:
        _empty_ref = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        print(f"  Empty area reference loaded: {_empty_ref.shape[1]}x{_empty_ref.shape[0]}px")
    else:
        _empty_ref = ()
    return _empty_ref


def _area_correlation(frame_bgr, loading_area):
    """Compare loading area crop with empty reference.

    Returns correlation (0.0-1.0) or None if reference not available.
    High correlation = area looks empty, low = something is there.
    """
    ref = _load_empty_reference()
    if not isinstance(ref, np.ndarray):
        return None

    if not loading_area:
        return None

    x1, y1, x2, y2 = loading_area
    crop = frame_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    # Resize to match reference dimensions
    if gray.shape != ref.shape:
        gray = cv2.resize(gray, (ref.shape[1], ref.shape[0]))

    # Normalized cross-correlation
    result = cv2.matchTemplate(gray, ref, cv2.TM_CCORR_NORMED)
    return float(result[0][0])


# Thresholds for area change detection
EMPTY_THRESHOLD = 0.985   # above this = area is empty (matches reference)
OBJECT_THRESHOLD = 0.975  # below this = something was placed in area


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


def _check_metis():
    """Check if Metis NPU device is available and usable."""
    import subprocess
    dev = '/dev/metis-0:1:0'
    if not os.path.exists(dev):
        return False, "Metis NPU device not found.\nCheck hardware connection and driver."
    # Check if kernel thread is stuck in D state
    try:
        result = subprocess.run(
            ['fuser', dev], capture_output=True, text=True, timeout=5
        )
        pids = result.stdout.strip().split()
        for pid in [p.strip() for p in pids if p.strip()]:
            try:
                with open(f'/proc/{pid}/status') as f:
                    for line in f:
                        if line.startswith('State:') and 'D' in line.split()[1]:
                            return False, "Metis NPU is locked by a stuck process.\nReboot the device to recover."
            except (OSError, IndexError):
                pass
    except Exception:
        pass
    return True, ""


def _check_camera(rtsp_url):
    """Check if RTSP camera is reachable and credentials are valid."""
    try:
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
        if not cap.isOpened():
            return False, "Cannot connect to camera.\nCheck network and RTSP URL in .env"
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            return False, "Camera connected but no frames received.\nCheck RTSP credentials in .env"
        return True, ""
    except Exception as e:
        return False, f"Camera error: {e}\nCheck .env configuration"


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _collect_vis_detections(frame_result, loading_area):
    """Extract detections from frame_result into display-friendly format.

    Includes all book/person detections; marks those outside loading area.
    """
    vis_dets = []
    for det in frame_result.detections:
        cid = int(det.class_id)
        score = float(det.score)
        box = det.box.tolist()
        if cid not in (BOOK_CLASS_ID, PERSON_CLASS_ID):
            continue
        in_area = _det_in_loading_area(box, loading_area)
        vis_dets.append({'class_id': cid, 'score': score, 'box': box,
                         'in_area': in_area})
    return vis_dets


# ---------------------------------------------------------------------------
# STATE: WATCHING - detect object in loading area via reference comparison
# ---------------------------------------------------------------------------

def watch_for_book(rtsp_url, confidence_threshold=0.40, consecutive_needed=5,
                   debug=False):
    """Watch RTSP stream for an object in the loading area.

    Uses image correlation with empty reference to detect when something is
    placed in the loading area.  YOLO is used only for person detection
    (positioning vs ready).  Returns captured BGR frame (cropped to loading
    area) when triggered.
    """
    global _diag_mode
    print("\n" + "=" * 60)
    print("  WATCHING for book... (press ENTER to quit)")
    print("=" * 60)

    loading_area = _load_loading_area()
    ref = _load_empty_reference()
    if not isinstance(ref, np.ndarray):
        print("  ERROR: No empty_reference.jpg — run calibrate.py first")
        return None

    pipeline_cfg = ax_config.PipelineConfig(
        network=DETECTION_MODEL,
        sources=[rtsp_url],
        pipe_type='gst',
        low_latency=True,
        rtsp_latency=100,
    )
    stream_cfg = ax_config.InferenceStreamConfig(
        timeout=10,
        frames=0,  # continuous
    )

    stream = create_inference_stream(
        stream_config=stream_cfg,
        pipeline_configs=pipeline_cfg,
    )

    consecutive_book = 0
    frame_count = 0
    captured_frame = None
    dot_count = 0

    try:
        for frame_result in stream:
            # Check if user pressed ENTER (non-blocking stdin poll)
            if sys.stdin.isatty() and select.select([sys.stdin], [], [], 0)[0]:
                sys.stdin.readline()
                if not debug and dot_count > 0:
                    print()
                captured_frame = 'quit'
                break

            if frame_result.image is None and frame_result.meta is None:
                continue

            frame_count += 1

            # Get raw frame
            try:
                frame_bgr = frame_result.image.asarray('BGR').copy()
            except Exception:
                continue

            # --- Detect object via correlation with empty reference ---
            corr = _area_correlation(frame_bgr, loading_area)
            has_object = corr is not None and corr < OBJECT_THRESHOLD

            # --- Detect person via YOLO (for positioning logic) ---
            has_person = False
            for det in frame_result.detections:
                cid = int(det.class_id)
                score = float(det.score)
                if cid == PERSON_CLASS_ID and score >= 0.30:
                    box = (int(det.bbox.x1), int(det.bbox.y1),
                           int(det.bbox.x2), int(det.bbox.y2))
                    if _det_in_loading_area(box, loading_area):
                        has_person = True
                        break

            # -- QR code check (every 30 frames, ~1.5s) --
            if frame_count % 30 == 0:
                qr_cmd = _check_qr_command(frame_bgr)
                if qr_cmd:
                    _diag_log(f"QR: {qr_cmd}")
                    if qr_cmd == 'DIAG ON':
                        _diag_mode = True
                    elif qr_cmd == 'DIAG OFF':
                        _diag_mode = False
                    elif qr_cmd == 'SHUTDOWN NOW':
                        _last_frame = [frame_bgr]
                        _handle_shutdown(None, lambda: _last_frame[0])
                    elif qr_cmd == 'CALIBRATE':
                        _handle_calibration()
                        # Restart WATCHING with new calibration
                        captured_frame = None
                        break

            # -- Display overlay (throttled: every 5th frame) --
            if frame_count % 5 == 0:
                try:
                    vis = frame_bgr.copy()
                    # Draw loading area
                    if loading_area:
                        x1, y1, x2, y2 = loading_area
                        color = (0, 255, 0) if not has_object else (0, 200, 255)
                        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
                    # Correlation info
                    if corr is not None:
                        corr_text = f"corr={corr:.3f} {'EMPTY' if not has_object else 'OBJECT'}"
                        cv2.putText(vis, corr_text, (10, 60),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    if has_object and has_person:
                        status = "POSITIONING... (remove hand to scan)"
                    elif has_object:
                        status = f"WATCHING [{consecutive_book}/{consecutive_needed}] (press ENTER to quit)"
                    else:
                        status = "WATCHING — area empty (press ENTER to quit)"
                    display.draw_status(vis, status,
                                        display.COLORS['status_watching'])
                    if _diag_mode:
                        display.draw_diag_overlay(vis, list(_diag_lines))
                    display.show(vis)
                except Exception:
                    pass

            # --- Logic ---
            if has_object and not has_person:
                consecutive_book += 1
                if debug:
                    print(f"  Frame {frame_count}: object detected"
                          f" corr={corr:.3f}"
                          f" [{consecutive_book}/{consecutive_needed}]")
                else:
                    sys.stdout.write('+')
                    sys.stdout.flush()
                    dot_count += 1

                if consecutive_book >= consecutive_needed:
                    # Capture cropped frame (loading area only)
                    if loading_area:
                        x1, y1, x2, y2 = loading_area
                        captured_frame = frame_bgr[y1:y2, x1:x2].copy()
                    else:
                        captured_frame = frame_bgr.copy()
                    if not debug:
                        print()
                    print(f"  Object detected in loading area!"
                          f" (corr={corr:.3f},"
                          f" {consecutive_needed} consecutive frames)")
                    _diag_log(f"WATCHING->SCANNING corr={corr:.3f}")
                    break

            elif has_object and has_person:
                # Someone is positioning — wait
                consecutive_book = 0
                if not debug:
                    sys.stdout.write('h')
                    sys.stdout.flush()
                    dot_count += 1
            else:
                # Area empty
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
    """Import and initialize OCR components from tools/."""
    global _ocr_components
    if _ocr_components is not None:
        return _ocr_components

    print("  Loading OCR components...")

    # Import from tools/
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
                       debug=False, progress_cb=None):
    """Multi-pass OCR replicating ContinuousScanner._run_ocr_multipass() logic."""
    all_pass_boxes = []
    temp_files = []
    scale = 2.0
    total_passes = 2 + (8 if color_filters else 0)

    def _progress(pass_num, label):
        if progress_cb:
            progress_cb(pass_num / total_passes, label)

    # Pass 1: Upscale 2x + denoise
    _progress(0, f"OCR Pass 1/{total_passes}")
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
    _progress(1, f"OCR Pass 2/{total_passes}")
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
            _progress(i - 1, f"OCR Pass {i}/{total_passes}")
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
              debug=False, progress_cb=None):
    """Run the full OCR pipeline on a captured frame.

    progress_cb: optional callback(progress_0_to_1, phase_text) for display.
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

    # Calculate total steps for progress: OCR passes + correction + parse + DB
    total_passes = 2 + (8 if color_filters else 0)
    total_steps = total_passes + 3  # +correction +parse +DB

    def _progress(step, phase_text):
        if progress_cb:
            progress_cb(step / total_steps, phase_text)

    _progress(0, "Starting OCR...")

    # Multi-pass OCR (with per-pass progress)
    text_boxes = _run_ocr_multipass(
        frame, ocr_func, preprocessor, merge_fn,
        color_filters=color_filters, debug=debug,
        progress_cb=lambda p, t: _progress(p * total_passes, t),
    )

    # Fuzzy DB correction
    _progress(total_passes, f"Spell check ({len(text_boxes)} blocks)")
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
    _progress(total_passes + 1, "Text analysis")
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
    _progress(total_passes + 2, "Database search")
    print(f"   Searching database...", end='', flush=True)
    db_result = _identify_book(improved, parser, lang=lang)
    if db_result['matched']:
        print(" found!")
    else:
        print(" not found")

    _progress(total_steps, "Done")
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

def wait_for_removal(rtsp_url, confidence_threshold=0.40, feedback=True,
                     debug=False, book_display_info=None):
    """Wait until the scanned book is removed from the scene.

    Uses YOLOv8 object detection on Metis NPU (same as WATCHING).
    When a person is detected AND feedback is enabled, grabs the frame and
    checks for crossed index fingers via MediaPipe (reject gesture).

    book_display_info: dict with 'title', 'author', 'publisher' for overlay.

    Exits when:
      - Crossed fingers detected (person + gesture) -> 'reject'
      - A person appears without gesture (removing book) -> 'continue'
      - The book disappears from the scene -> 'continue'
      - The user presses ENTER -> 'quit'

    Returns 'continue', 'reject', or 'quit'.
    """
    global _diag_mode
    print("\n" + "=" * 60)
    if feedback:
        print("  WAITING - Person presence to REJECT, remove book to ACCEPT (press ENTER to quit)")
    else:
        print("  WAITING - Remove book to continue (press ENTER to quit)")
    print("=" * 60)

    pipeline_cfg = ax_config.PipelineConfig(
        network=DETECTION_MODEL,
        sources=[rtsp_url],
        pipe_type='gst',
        low_latency=True,
        rtsp_latency=100,
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
    grace_frames = 80          # ~4s grace period to show result before accepting
    consecutive_person = 0
    REJECT_FRAMES = 30         # ~1.5s of person presence → reject
    consecutive_gone = 0
    GONE_FRAMES_NEEDED = 15    # ~0.75s confirmation that book is really gone
    frame_count = 0
    dot_count = 0
    result = 'continue'
    wait_vis_base = None  # cached base frame for smooth bar updates

    try:
        for frame_result in stream:
            # Check if user pressed ENTER (non-blocking stdin poll)
            if sys.stdin.isatty() and select.select([sys.stdin], [], [], 0)[0]:
                sys.stdin.readline()
                if not debug and dot_count > 0:
                    print()
                result = 'quit'
                break

            if frame_result.image is None and frame_result.meta is None:
                continue

            frame_count += 1

            # Get raw frame
            try:
                frame_bgr = frame_result.image.asarray('BGR').copy()
            except Exception:
                continue

            # --- Detect object via correlation ---
            corr = _area_correlation(frame_bgr, loading_area)
            has_object = corr is not None and corr < OBJECT_THRESHOLD
            is_empty = corr is not None and corr >= EMPTY_THRESHOLD

            # --- Detect person via YOLO ---
            has_person = False
            for det in frame_result.detections:
                cid = int(det.class_id)
                score = float(det.score)
                if cid == PERSON_CLASS_ID and score >= 0.30:
                    box = (int(det.bbox.x1), int(det.bbox.y1),
                           int(det.bbox.x2), int(det.bbox.y2))
                    if _det_in_loading_area(box, loading_area):
                        has_person = True
                        break

            # -- QR code check (every 30 frames) --
            if frame_count % 30 == 0:
                qr_cmd = _check_qr_command(frame_bgr)
                if qr_cmd:
                    _diag_log(f"QR: {qr_cmd}")
                    if qr_cmd == 'DIAG ON':
                        _diag_mode = True
                    elif qr_cmd == 'DIAG OFF':
                        _diag_mode = False
                    elif qr_cmd == 'SHUTDOWN NOW':
                        _last_frame = [frame_bgr]
                        _handle_shutdown(None, lambda: _last_frame[0])
                    elif qr_cmd == 'CALIBRATE':
                        _handle_calibration()

            # -- Display overlay --
            try:
                if frame_count % 5 == 0:
                    wait_vis_base = frame_bgr.copy()
                    if loading_area:
                        x1, y1, x2, y2 = loading_area
                        cv2.rectangle(wait_vis_base, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    if book_display_info:
                        display.draw_result_box(
                            wait_vis_base,
                            book_display_info.get('title', ''),
                            book_display_info.get('author', ''),
                            book_display_info.get('publisher', ''))
                    display.draw_status(wait_vis_base, "WAITING",
                                        display.COLORS['status_waiting'])
                vis_frame = wait_vis_base.copy() if wait_vis_base is not None else frame_bgr.copy()
                # Reject bar when person detected
                if has_person and consecutive_person > 0:
                    ratio = 1.0 - consecutive_person / REJECT_FRAMES
                    display.draw_countdown_bar(vis_frame, ratio, mode='reject')
                # Accept bar when area clearing
                elif is_empty and consecutive_gone > 0:
                    ratio = 1.0 - consecutive_gone / GONE_FRAMES_NEEDED
                    display.draw_countdown_bar(vis_frame, ratio, mode='accept')
                if _diag_mode:
                    display.draw_diag_overlay(vis_frame, list(_diag_lines))
                display.show(vis_frame)
            except Exception:
                pass

            # Grace period: show result but don't act yet
            in_grace = frame_count <= grace_frames
            if in_grace:
                if not debug:
                    sys.stdout.write('_')
                    sys.stdout.flush()
                    dot_count += 1
                    if dot_count >= 80:
                        print()
                        dot_count = 0
                continue

            # --- Post-grace logic ---

            # Person detected → reject countdown
            if has_person:
                consecutive_person += 1
                consecutive_gone = 0
                if debug:
                    print(f"  Frame {frame_count}: person"
                          f" [{consecutive_person}/{REJECT_FRAMES}]")
                else:
                    sys.stdout.write('P')
                    sys.stdout.flush()
                    dot_count += 1

                if consecutive_person >= REJECT_FRAMES:
                    if not debug and dot_count > 0:
                        print()
                    print("  Person detected — REJECTED")
                    _diag_log("WAITING: REJECTED (person)")
                    result = 'reject'
                    break
            else:
                consecutive_person = 0

            # Area empty (matches reference) → accept countdown
            if is_empty:
                consecutive_gone += 1
                if debug:
                    print(f"  Frame {frame_count}: area empty"
                          f" corr={corr:.3f}"
                          f" [{consecutive_gone}/{GONE_FRAMES_NEEDED}]")
                else:
                    sys.stdout.write('*')
                    sys.stdout.flush()
                    dot_count += 1

                if consecutive_gone >= GONE_FRAMES_NEEDED:
                    if not debug and dot_count > 0:
                        print()
                    print("  Book removed, accepting...")
                    _diag_log("WAITING->WATCHING (accepted)")
                    break
            else:
                consecutive_gone = 0

            # Idle (object still there, no person)
            if has_object and not has_person:
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
    global _diag_mode

    # Activate diagnostics overlay if --debug
    if args.debug:
        _diag_mode = True
        _diag_log("Diagnostics mode ON (--debug)")

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

    use_feedback = not args.no_feedback
    loading_steps = [
        ("Metis NPU check", False),
        ("Camera check", False),
        ("Metis NPU cleanup", False),
        ("OCR components", False),
        ("PP-OCR models", False),
    ]
    if args.ocr_model in ('metis', 'hybrid'):
        loading_steps.append(("Metis OCR model", False))

    def _splash(status, step_idx=None):
        if step_idx is not None:
            loading_steps[step_idx] = (loading_steps[step_idx][0], True)
        display.draw_splash(status, loading_steps)

    _splash("Starting up...")

    # Pre-flight checks
    _splash("Checking Metis NPU...")
    metis_ok, metis_err = _check_metis()
    if not metis_ok:
        print(f"  FATAL: {metis_err}")
        display.show_error(metis_err)
        return
    _splash("Metis NPU OK", step_idx=0)

    _splash("Checking camera...")
    cam_ok, cam_err = _check_camera(rtsp_url)
    if not cam_ok:
        print(f"  FATAL: {cam_err}")
        display.show_error(cam_err)
        return
    _splash("Camera OK", step_idx=1)

    _splash("Cleaning up Metis...")
    _kill_stale_metis()
    _splash("Metis cleanup done", step_idx=2)

    # Pre-initialize OCR components
    _splash("Loading OCR components...")
    print("\n  Initializing OCR...")
    _init_ocr_components(args.ocr_model, debug=args.debug)
    print("  OCR ready.\n")
    # Mark remaining OCR steps as done
    for i in range(3, len(loading_steps)):
        loading_steps[i] = (loading_steps[i][0], True)
    _splash("Ready!")

    book_count = 0

    try:
        while True:
            # --- WATCHING ---
            gc.collect()

            frame = watch_for_book(
                rtsp_url,
                confidence_threshold=args.confidence,
                consecutive_needed=args.consecutive,
                debug=args.debug,
            )

            if frame is None:
                print("  No frame captured, retrying...")
                continue

            if isinstance(frame, str) and frame == 'quit':
                print(f"\n  Books scanned: {book_count}")
                print("  Pipeline stopped.\n")
                return

            # --- SCANNING ---

            # Run OCR in background thread, animate hourglass in main thread
            scan_state = {'progress': 0.0, 'phase': 'Starting...',
                          'done': False, 'result': None}

            def _scan_progress(progress, phase_text):
                scan_state['progress'] = progress
                scan_state['phase'] = phase_text

            def _scan_worker():
                try:
                    result = scan_book(
                        frame,
                        ocr_model=args.ocr_model,
                        color_filters=args.color_filters,
                        lang=args.lang,
                        debug=args.debug,
                        progress_cb=_scan_progress,
                    )
                    scan_state['result'] = result
                finally:
                    scan_state['done'] = True

            scan_thread = threading.Thread(target=_scan_worker, daemon=True)
            scan_thread.start()

            # Animate hourglass while OCR runs
            scan_frame_base = display.frame_on_canvas(frame)
            tick = 0
            while not scan_state['done']:
                tick += 1
                vis = scan_frame_base.copy()
                display.draw_hourglass(vis, tick=tick,
                                       progress=scan_state['progress'],
                                       phase_text=scan_state['phase'])
                display.draw_status(vis, "SCANNING",
                                    display.COLORS['status_scanning'])
                if _diag_mode:
                    display.draw_diag_overlay(vis, list(_diag_lines))
                display.show(vis)
                time.sleep(0.05)  # ~20fps animation

            scan_thread.join()
            book_info, db_result = scan_state['result']

            book_count += 1
            display_result(book_info, db_result, book_count)

            # Show result on display
            MIN_DB_CONFIDENCE = 0.60
            db_matched = (db_result and db_result.get('matched')
                          and db_result.get('book'))
            db_confident = (db_matched
                            and db_result['match_confidence'] >= MIN_DB_CONFIDENCE)
            if db_confident:
                book = db_result['book']
                bdi = {'title': book.title, 'author': book.author,
                       'publisher': book.publisher or ''}
            else:
                bdi = {'title': book_info['title'],
                       'author': book_info['author'],
                       'publisher': book_info['publisher']}

            _diag_log(f"OCR: {bdi['title'][:30]} / {bdi['author'][:20]}")

            result_display = display.frame_on_canvas(frame)
            display.draw_result_box(result_display, bdi['title'],
                                    bdi['author'], bdi['publisher'])
            display.draw_status(result_display, "RESULT",
                                display.COLORS['status_scanning'])
            if _diag_mode:
                display.draw_diag_overlay(result_display, list(_diag_lines))
            display.show(result_display)

            # --- WAITING (with integrated gesture detection) ---
            gc.collect()

            wait_result = wait_for_removal(
                rtsp_url,
                confidence_threshold=args.confidence,
                feedback=not args.no_feedback,
                debug=args.debug,
                book_display_info=bdi,
            )

            if wait_result == 'quit':
                print(f"\n  Books scanned: {book_count}")
                print("  Pipeline stopped.\n")
                return
            elif wait_result == 'reject':
                print("  >> REJECTED by user gesture")
                display.show_rejected()
            else:
                print("  >> ACCEPTED")
                display.show_accepted()

            print()

    except KeyboardInterrupt:
        print("\n\n  Interrupted by user")
        print(f"  Books scanned: {book_count}")
        print("  Pipeline stopped.\n")
    finally:
        display.destroy()


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
        '--confidence', type=float, default=0.40,
        help='Book detection confidence threshold (default: 0.40)')
    parser.add_argument(
        '--consecutive', type=int, default=15,
        help='Consecutive frames to confirm book detection (default: 5)')
    parser.add_argument(
        '--color-filters', action='store_true',
        help='Enable extra OCR passes with color filters (slower, better on artistic covers)')
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
