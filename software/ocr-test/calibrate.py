#!/usr/bin/env python3
"""
Automatic calibration of loading area using 4 X markers.
Detects X markers at corners and saves configuration.

Usage: python3 calibrate.py [--debug]
"""

import cv2
import numpy as np
import sys
import os
import argparse


# ============================================================================
# CONFIGURATION
# ============================================================================

def load_env_file(env_file='.env'):
    """Load environment variables from .env file if it exists"""
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        os.environ[key] = value


class RTSPConfig:
    """RTSP camera configuration"""

    @staticmethod
    def get_url():
        """Get RTSP URL with credentials"""
        # Load .env file if exists
        load_env_file()

        # Default camera settings
        ip = "192.168.1.199"
        port = 554
        username = "sonoff"
        password = "gr4jl096"
        path = "/av_stream/ch0"

        # Read from .env (RTSP_* variables)
        ip = os.getenv('RTSP_IP', ip)
        port = int(os.getenv('RTSP_PORT', port))
        username = os.getenv('RTSP_USERNAME', username)
        password = os.getenv('RTSP_PASSWORD', password)
        path = os.getenv('RTSP_PATH', path)

        return f"rtsp://{username}:{password}@{ip}:{port}{path}"


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


def find_rectangle_geometric(markers, image_shape, debug=False):
    """
    Find rectangle using geometric constraints.
    Uses bottom 2 markers and projects vertically to find top markers.

    Args:
        markers: List of (x, y) marker coordinates
        image_shape: Tuple of (height, width)
        debug: Enable debug output

    Returns:
        Tuple of (x1, y1, x2, y2) or None if not found
    """
    if len(markers) < 4:
        return None

    h, w = image_shape[:2]

    # Separate markers into top and bottom halves
    y_mid = h / 2
    bottom_markers = [(x, y) for x, y in markers if y > y_mid]
    top_markers = [(x, y) for x, y in markers if y < y_mid]

    if len(bottom_markers) < 2:
        if debug:
            print(f"  ❌ Need at least 2 bottom markers, found {len(bottom_markers)}")
        return None

    # Sort bottom markers by X coordinate
    bottom_markers.sort(key=lambda p: p[0])

    # Take leftmost and rightmost bottom markers
    bottom_left = bottom_markers[0]
    bottom_right = bottom_markers[-1]

    if debug:
        print(f"  Bottom left:  {bottom_left}")
        print(f"  Bottom right: {bottom_right}")

    # Expected X coordinates for top markers (same as bottom)
    expected_left_x = bottom_left[0]
    expected_right_x = bottom_right[0]

    # Find top markers by vertical projection
    # Look for markers with similar X coordinates
    x_tolerance = w * 0.05  # 5% tolerance

    top_left_candidates = [(x, y) for x, y in top_markers
                           if abs(x - expected_left_x) < x_tolerance]
    top_right_candidates = [(x, y) for x, y in top_markers
                            if abs(x - expected_right_x) < x_tolerance]

    if not top_left_candidates or not top_right_candidates:
        if debug:
            print(f"  ❌ Cannot find top markers aligned with bottom")
            print(f"     Top left candidates:  {len(top_left_candidates)}")
            print(f"     Top right candidates: {len(top_right_candidates)}")
        return None

    # Pick topmost (smallest Y) from each side
    top_left = min(top_left_candidates, key=lambda p: p[1])
    top_right = min(top_right_candidates, key=lambda p: p[1])

    if debug:
        print(f"  Top left:  {top_left}")
        print(f"  Top right: {top_right}")

    # Validate rectangle geometry
    rect_width = max(bottom_right[0], top_right[0]) - min(bottom_left[0], top_left[0])
    rect_height = max(bottom_left[1], bottom_right[1]) - min(top_left[1], top_right[1])

    if rect_width < w * 0.1 or rect_height < h * 0.1:
        if debug:
            print(f"  ❌ Rectangle too small: {rect_width}x{rect_height}")
        return None

    if rect_width > w * 0.9 or rect_height > h * 0.9:
        if debug:
            print(f"  ❌ Rectangle too large: {rect_width}x{rect_height}")
        return None

    # Calculate bounding box from 4 corners
    x1 = min(top_left[0], bottom_left[0])
    y1 = min(top_left[1], top_right[1])
    x2 = max(top_right[0], bottom_right[0])
    y2 = max(bottom_left[1], bottom_right[1])

    # Validate alignment (top markers should be roughly aligned horizontally)
    top_y_diff = abs(top_left[1] - top_right[1])
    bottom_y_diff = abs(bottom_left[1] - bottom_right[1])

    if top_y_diff > h * 0.05 or bottom_y_diff > h * 0.05:
        if debug:
            print(f"  ⚠️  Warning: Horizontal alignment off (top: {top_y_diff}px, bottom: {bottom_y_diff}px)")

    return (x1, y1, x2, y2)


# ============================================================================
# CALIBRATION
# ============================================================================

def calibrate_camera(rtsp_url, debug=False):
    """
    Calibrate loading area from camera stream.

    Returns:
        Tuple of (x1, y1, x2, y2) coordinates or None
    """
    print("\n📷 Connecting to camera...")
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        print(f"❌ Error: Cannot connect to camera: {rtsp_url}")
        return None

    print("✅ Camera connected")
    print("\n📸 Capturing frame...")

    # Skip first few frames to let camera stabilize
    for _ in range(10):
        ret, frame = cap.read()
        if not ret:
            print("❌ Error: Cannot read frame")
            cap.release()
            return None

    cap.release()

    h, w = frame.shape[:2]
    print(f"✅ Frame captured: {w}x{h}px")

    if debug:
        cv2.imwrite('debug_0_original.jpg', frame)

    # Detect markers
    print("\n🔍 Detecting X markers...")
    markers = detect_x_markers(frame, debug=debug)

    if len(markers) < 4:
        print(f"❌ Error: Found only {len(markers)} markers, need 4")
        print("\n💡 Troubleshooting:")
        print("   1. Ensure 4 large X markers (5-8cm) at loading area corners")
        print("   2. Use black marker on light background")
        print("   3. Check lighting (no shadows on markers)")
        print("   4. All 4 X must be visible in camera view")
        if debug:
            print(f"   5. Check debug_3_markers.jpg to see what was detected")
        return None

    print(f"✅ Found {len(markers)} markers")

    # Find rectangle
    print("\n🔧 Calculating loading area...")
    rectangle = find_rectangle_geometric(markers, frame.shape, debug=debug)

    if rectangle is None:
        print("❌ Error: Cannot determine loading area from markers")
        return None

    x1, y1, x2, y2 = rectangle
    area_w = x2 - x1
    area_h = y2 - y1
    area_pct = (area_w * area_h) / (w * h) * 100

    print(f"✅ Loading area: {area_w}x{area_h}px ({area_pct:.1f}% of frame)")

    # Save preview
    preview = frame.copy()
    cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 0), 3)

    # Mark detected corners
    for mx, my in markers:
        cv2.circle(preview, (mx, my), 8, (0, 0, 255), -1)

    os.makedirs('test_images', exist_ok=True)
    preview_path = 'test_images/calibration_preview.jpg'
    cv2.imwrite(preview_path, preview)
    print(f"✅ Preview saved: {preview_path}")

    if debug:
        cv2.imwrite('debug_4_final.jpg', preview)

    return rectangle


def save_calibration(rectangle):
    """Save calibration to file"""
    os.makedirs('test_images', exist_ok=True)

    config_file = 'test_images/loading_area.txt'
    with open(config_file, 'w') as f:
        f.write(f"{rectangle[0]},{rectangle[1]},{rectangle[2]},{rectangle[3]}\n")

    print(f"✅ Configuration saved: {config_file}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Automatic loading area calibration"
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help="Enable debug mode (save intermediate images)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("   📐 LOADING AREA CALIBRATION")
    print("=" * 70)

    # Get camera URL
    rtsp_url = RTSPConfig.get_url()

    # Calibrate
    rectangle = calibrate_camera(rtsp_url, debug=args.debug)

    if rectangle is None:
        print("\n❌ Calibration failed")
        sys.exit(1)

    # Save
    save_calibration(rectangle)

    print("\n" + "=" * 70)
    print("   ✅ CALIBRATION COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Verify preview: test_images/calibration_preview.jpg")
    print("  2. Run book scanning: python3 scan_books.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
