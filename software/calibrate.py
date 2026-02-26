#!/usr/bin/env python3
"""
Automatic calibration of loading area using 4 X markers.
Detects X markers at corners and saves configuration.

Usage: python3 calibrate.py [--debug] [--no-display]

Options:
    --debug        Save intermediate debug images
    --no-display   Never show preview window (use in headless mode)
"""

import os
# Suppress fontconfig warnings
os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.qpa.*=false'

import argparse
import glob
import subprocess
import sys
import warnings

import cv2
import numpy as np

# Resolve paths relative to this script's directory
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_OCR_DIR = os.path.join(_SCRIPT_DIR, 'ocr-module')
_CONFIG_DIR = os.path.join(_SCRIPT_DIR, 'config')

# Add ocr-module to path for config import
sys.path.insert(0, _OCR_DIR)
from config import RTSPConfig

# Suppress OpenCV warnings
warnings.filterwarnings('ignore', category=UserWarning)


# ============================================================================
# DISPLAY UTILITIES
# ============================================================================

def has_display():
    """Check if we're running in a graphical environment"""
    if os.environ.get('DISPLAY'):
        return True
    if os.environ.get('WAYLAND_DISPLAY'):
        return True
    if sys.platform == 'darwin':
        return True
    if sys.platform == 'win32':
        return True
    return False


def can_show_gui():
    """Check if we can show images (have display + viewer)"""
    if not has_display():
        return False
    # Check for image viewers
    for viewer in ['feh', 'eog', 'gpicview', 'viewnior', 'xdg-open']:
        try:
            result = subprocess.run(['which', viewer], capture_output=True)
            if result.returncode == 0:
                return True
        except OSError:
            pass
    return False


def show_image(image, wait_key=True):
    """
    Show image using external viewer (OpenCV GUI not available in venv).

    Returns:
        True if image was shown, False otherwise
    """
    temp_path = '/tmp/calibration_preview_temp.jpg'
    try:
        cv2.imwrite(temp_path, image)
    except Exception as e:
        print(f"Cannot save preview: {e}")
        return False

    viewers = ['feh', 'eog', 'gpicview', 'viewnior', 'xdg-open']
    proc = None
    for viewer in viewers:
        try:
            result = subprocess.run(['which', viewer], capture_output=True)
            if result.returncode == 0:
                proc = subprocess.Popen(
                    [viewer, temp_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                break
        except OSError:
            continue

    if proc is None:
        return False

    if wait_key:
        print("\nPreview opened in external viewer.")
        input("Press ENTER to close preview and continue...")
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            pass

    return True


# ============================================================================
# X MARKER DETECTION
# ============================================================================

def detect_x_markers(image, debug=False):
    """
    Detect X markers in image using blob detection.

    Returns:
        List of (x, y) coordinates of detected markers
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Threshold to get black markers
    _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)

    if debug:
        cv2.imwrite('debug_1_binary.jpg', binary)

    # Morphological operations to clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)

    if debug:
        cv2.imwrite('debug_2_cleaned.jpg', cleaned)

    # Find contours
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours by area and aspect ratio
    markers = []
    h, w = image.shape[:2]
    min_area = (h * w) * 0.0002  # 0.02% of image
    max_area = (h * w) * 0.01    # 1% of image

    debug_img = image.copy() if debug else None

    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)

        if area < min_area or area > max_area:
            continue

        # Get bounding box
        x, y, w_box, h_box = cv2.boundingRect(contour)
        aspect_ratio = float(w_box) / h_box if h_box > 0 else 0

        # X markers should be roughly square
        if 0.5 < aspect_ratio < 2.0:
            # Center of marker
            M = cv2.moments(contour)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                markers.append((cx, cy))

                if debug:
                    cv2.circle(debug_img, (cx, cy), 10, (0, 255, 0), -1)
                    cv2.putText(debug_img, f"{i+1}", (cx + 15, cy),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    if debug and debug_img is not None:
        cv2.imwrite('debug_3_markers.jpg', debug_img)
        print(f"  Found {len(markers)} potential markers")

    return markers


def find_rectangle_from_markers(markers, image_shape, debug=False):
    """
    Find rectangle from detected markers using角度-based corner assignment.
    Assigns markers to TL/TR/BR/BL based on angle from centroid.

    Args:
        markers: List of (x, y) marker coordinates
        image_shape: Tuple of (height, width)
        debug: Enable debug output

    Returns:
        Tuple of (x1, y1, x2, y2) or None if not found
    """
    import math

    if len(markers) < 4:
        return None

    h, w = image_shape[:2]

    if debug:
        print(f"  All {len(markers)} markers:")
        for i, (mx, my) in enumerate(markers):
            print(f"    [{i}] ({mx}, {my})")

    # If more than 4 markers, pick the 4 that form the largest area
    if len(markers) > 4:
        from itertools import combinations
        best_area = 0
        best_four = None
        for combo in combinations(markers, 4):
            pts = list(combo)
            # Shoelace area
            cx = sum(p[0] for p in pts) / 4
            cy = sum(p[1] for p in pts) / 4
            sorted_pts = sorted(pts, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
            area = 0
            for i in range(4):
                j = (i + 1) % 4
                area += sorted_pts[i][0] * sorted_pts[j][1]
                area -= sorted_pts[j][0] * sorted_pts[i][1]
            area = abs(area) / 2
            if area > best_area:
                best_area = area
                best_four = pts
        markers = best_four
        if debug:
            print(f"  Selected 4 markers with largest area ({best_area:.0f}px²)")

    # Compute centroid
    cx = sum(p[0] for p in markers) / len(markers)
    cy = sum(p[1] for p in markers) / len(markers)

    if debug:
        print(f"  Centroid: ({cx:.0f}, {cy:.0f})")

    # Assign corners by angle from centroid
    # atan2 gives: right=0, bottom=pi/2, left=±pi, top=-pi/2
    # We want: TL (top-left), TR (top-right), BR (bottom-right), BL (bottom-left)
    angles = [(math.atan2(y - cy, x - cx), (x, y)) for x, y in markers]

    # Sort by angle: -pi to +pi
    # TL ~ -3pi/4 (-135°), TR ~ -pi/4 (-45°), BR ~ pi/4 (45°), BL ~ 3pi/4 (135°)
    top_left = min(angles, key=lambda a: abs(a[0] - (-3 * math.pi / 4)))[1]
    top_right = min(angles, key=lambda a: abs(a[0] - (-math.pi / 4)))[1]
    bottom_right = min(angles, key=lambda a: abs(a[0] - (math.pi / 4)))[1]
    bottom_left = min(angles, key=lambda a: abs(a[0] - (3 * math.pi / 4)))[1]

    if debug:
        print(f"  Corners assigned:")
        print(f"    TL: {top_left}")
        print(f"    TR: {top_right}")
        print(f"    BR: {bottom_right}")
        print(f"    BL: {bottom_left}")

    # Check we got 4 distinct points
    corners = {top_left, top_right, bottom_right, bottom_left}
    if len(corners) < 4:
        if debug:
            print(f"  Error: Only {len(corners)} distinct corners (markers too close?)")
        return None

    # Bounding box from corners
    x1 = min(top_left[0], bottom_left[0])
    y1 = min(top_left[1], top_right[1])
    x2 = max(top_right[0], bottom_right[0])
    y2 = max(bottom_left[1], bottom_right[1])

    # Validate size
    rect_width = x2 - x1
    rect_height = y2 - y1

    if rect_width < w * 0.05 or rect_height < h * 0.05:
        if debug:
            print(f"  Rectangle too small: {rect_width}x{rect_height}")
        return None

    if rect_width > w * 0.95 or rect_height > h * 0.95:
        if debug:
            print(f"  Rectangle too large: {rect_width}x{rect_height}")
        return None

    if debug:
        print(f"  Rectangle: ({x1},{y1}) - ({x2},{y2}) = {rect_width}x{rect_height}")

    return (x1, y1, x2, y2)


# ============================================================================
# CALIBRATION
# ============================================================================

def calibrate_camera(rtsp_url, debug=False, show_gui=False):
    """
    Calibrate loading area from camera stream.

    Args:
        rtsp_url: RTSP camera URL
        debug: Save intermediate debug images
        show_gui: Show preview in GUI window

    Returns:
        Tuple of (x1, y1, x2, y2) coordinates or None
    """
    print("\nConnecting to camera...")
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        print(f"Error: Cannot connect to camera: {rtsp_url}")
        return None

    print("Camera connected")
    print("\nCapturing frame...")

    # Skip first few frames to let camera stabilize
    for _ in range(10):
        ret, frame = cap.read()
        if not ret:
            print("Error: Cannot read frame")
            cap.release()
            return None

    cap.release()

    h, w = frame.shape[:2]
    print(f"Frame captured: {w}x{h}px")

    if debug:
        cv2.imwrite('debug_0_original.jpg', frame)

    # Detect markers
    print("\nDetecting X markers...")
    markers = detect_x_markers(frame, debug=debug)

    if len(markers) < 4:
        print(f"Error: Found only {len(markers)} markers, need 4")
        print("\nTroubleshooting:")
        print("   1. Ensure 4 large X markers (5-8cm) at loading area corners")
        print("   2. Use black marker on light background")
        print("   3. Check lighting (no shadows on markers)")
        print("   4. All 4 X must be visible in camera view")
        if debug:
            print(f"   5. Check debug_3_markers.jpg to see what was detected")
        return None

    print(f"Found {len(markers)} markers")

    # Find rectangle
    print("\nCalculating loading area...")
    rectangle = find_rectangle_from_markers(markers, frame.shape, debug=debug)

    if rectangle is None:
        print("Error: Cannot determine loading area from markers")
        return None

    x1, y1, x2, y2 = rectangle
    area_w = x2 - x1
    area_h = y2 - y1
    area_pct = (area_w * area_h) / (w * h) * 100

    print(f"Loading area: {area_w}x{area_h}px ({area_pct:.1f}% of frame)")

    # Create preview image
    preview = frame.copy()
    cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 0), 3)

    # Mark detected corners
    for mx, my in markers:
        cv2.circle(preview, (mx, my), 8, (0, 0, 255), -1)

    # Add text overlay with coordinates
    text = f"Area: ({x1},{y1}) - ({x2},{y2}) | {area_w}x{area_h}px"
    cv2.putText(preview, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (0, 255, 0), 2)

    # Save preview in config/ directory
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    preview_path = os.path.join(_CONFIG_DIR, 'calibration_preview.jpg')
    cv2.imwrite(preview_path, preview)
    print(f"Preview saved: {preview_path}")

    if debug:
        cv2.imwrite('debug_4_final.jpg', preview)

    # Show GUI preview if requested
    if show_gui:
        # Resize for display if too large
        display_img = preview.copy()
        max_display_h = 800
        if display_img.shape[0] > max_display_h:
            scale = max_display_h / display_img.shape[0]
            new_w = int(display_img.shape[1] * scale)
            display_img = cv2.resize(display_img, (new_w, max_display_h))

        show_image(display_img)

    return rectangle, frame


def save_calibration(rectangle, frame):
    """Save calibration coordinates and empty area reference image."""
    os.makedirs(_CONFIG_DIR, exist_ok=True)

    # Save coordinates
    config_file = os.path.join(_CONFIG_DIR, 'loading_area.txt')
    with open(config_file, 'w') as f:
        f.write(f"{rectangle[0]},{rectangle[1]},{rectangle[2]},{rectangle[3]}\n")
    print(f"Configuration saved: {config_file}")

    # Save cropped empty area as reference for false-positive filtering
    x1, y1, x2, y2 = rectangle
    crop = frame[y1:y2, x1:x2]
    ref_path = os.path.join(_CONFIG_DIR, 'empty_reference.jpg')
    cv2.imwrite(ref_path, crop)
    print(f"Empty area reference saved: {ref_path}")


# ============================================================================
# MAIN
# ============================================================================

def cleanup_temp_files():
    """Remove temporary files created by calibration"""
    for f in ['/tmp/calibration_preview_temp.jpg'] + glob.glob('debug_*.jpg'):
        try:
            os.remove(f)
        except OSError:
            pass


def main():
    cleanup_temp_files()

    parser = argparse.ArgumentParser(
        description="Automatic loading area calibration"
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help="Enable debug mode (save intermediate images)"
    )
    parser.add_argument(
        '--no-display',
        action='store_true',
        help="Never show preview window (use in headless mode)"
    )

    args = parser.parse_args()

    # Determine if we should show GUI
    if args.no_display:
        args.show_gui = False
    else:
        args.show_gui = can_show_gui()
        if args.show_gui:
            print("Graphical environment detected - will show preview")

    print("=" * 70)
    print("   LOADING AREA CALIBRATION")
    print("=" * 70)

    # Get camera URL
    rtsp_url = RTSPConfig.get_url()

    # Calibrate
    result = calibrate_camera(rtsp_url, debug=args.debug, show_gui=args.show_gui)

    if result is None:
        print("\nCalibration failed")
        sys.exit(1)

    rectangle, frame = result

    # Save
    save_calibration(rectangle, frame)

    print("\n" + "=" * 70)
    print("   CALIBRATION COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Verify preview: config/calibration_preview.jpg")
    print("  2. Run pipeline: python3 app.py")
    print("=" * 70)

    cleanup_temp_files()


if __name__ == "__main__":
    main()
