#!/usr/bin/env python3
"""
Capture frame from RTSP camera (SONOFF CAM S2).
"""

import sys
import time
import argparse
from pathlib import Path

import cv2
import numpy as np

import config


def capture_frame(
    rtsp_url: str = None,
    timeout: float = 10.0,
    retries: int = 3
) -> np.ndarray | None:
    """
    Capture a single frame from RTSP camera.

    Args:
        rtsp_url: RTSP URL (default from config)
        timeout: Connection timeout in seconds
        retries: Number of attempts

    Returns:
        Frame as BGR numpy array, or None if failed
    """
    if rtsp_url is None:
        rtsp_url = config.rtsp.get_url()

    for attempt in range(retries):
        if config.app.debug:
            print(f"Attempt {attempt + 1}/{retries} connecting to {rtsp_url}")

        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            print(f"Error: cannot open RTSP stream")
            time.sleep(1)
            continue

        # Read a few frames to stabilize
        for _ in range(5):
            cap.grab()

        ret, frame = cap.read()
        cap.release()

        if ret and frame is not None:
            if config.app.debug:
                print(f"Frame captured: {frame.shape}")
            return frame

        print(f"Error reading frame, retrying...")
        time.sleep(1)

    print("Cannot capture frame after all attempts")
    return None


def capture_from_file(image_path: str | Path) -> np.ndarray | None:
    """
    Load image from file.

    Args:
        image_path: Image path

    Returns:
        Image as BGR numpy array, or None if failed
    """
    path = Path(image_path)
    if not path.exists():
        print(f"Error: file not found: {path}")
        return None

    frame = cv2.imread(str(path))
    if frame is None:
        print(f"Error: cannot read image: {path}")
        return None

    if config.app.debug:
        print(f"Image loaded: {frame.shape}")
    return frame


def save_frame(frame: np.ndarray, output_path: str | Path = None) -> Path:
    """
    Save frame to disk.

    Args:
        frame: Frame to save
        output_path: Output path (default: test_images/capture.jpg)

    Returns:
        Path of saved file
    """
    if output_path is None:
        output_path = config.TEST_IMAGES_DIR / "capture.jpg"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), frame)

    if config.app.debug:
        print(f"Frame saved: {output_path}")
    return output_path


def main():
    """Entry point for standalone capture."""
    parser = argparse.ArgumentParser(description="Capture frame from RTSP camera")
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output path (default: test_images/capture.jpg)"
    )
    parser.add_argument(
        "-u", "--url",
        type=str,
        default=None,
        help="RTSP URL (default from .env)"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show captured frame"
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug"
    )
    args = parser.parse_args()

    if args.debug:
        config.app.debug = True

    print("Capturing frame from camera...")
    frame = capture_frame(rtsp_url=args.url)

    if frame is None:
        sys.exit(1)

    output_path = save_frame(frame, args.output)
    print(f"Frame saved to: {output_path}")

    if args.show:
        cv2.imshow("Capture", frame)
        print("Press any key to close...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
