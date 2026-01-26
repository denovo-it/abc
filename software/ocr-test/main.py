#!/usr/bin/env python3
"""
A.B.C. OCR Test - Main entry point.
Captures image from camera and recognizes title/author/publisher.
"""

import sys
import argparse
from pathlib import Path

import cv2
import numpy as np

import config
from capture import capture_frame, capture_from_file, save_frame
from ocr_pipeline import OCRPipeline, TextBox
from book_parser import parse_book_cover, format_book_info, BookInfo


def draw_results(image: np.ndarray, book: BookInfo) -> np.ndarray:
    """
    Draw results on image.

    Args:
        image: BGR image
        book: Extracted book info

    Returns:
        Annotated image
    """
    result = image.copy()
    h, w = result.shape[:2]

    # Colors (BGR)
    COLOR_TITLE = (0, 255, 0)      # Green
    COLOR_AUTHOR = (0, 165, 255)   # Orange
    COLOR_PUBLISHER = (255, 0, 0)  # Blue
    COLOR_OTHER = (128, 128, 128)  # Gray

    # Draw box for each detected text
    for box in book.raw_texts:
        x1, y1, x2, y2 = box.bbox

        # Choose color based on type
        if box.text == book.title:
            color = COLOR_TITLE
            label = "TITLE"
        elif box.text == book.author:
            color = COLOR_AUTHOR
            label = "AUTHOR"
        elif box.text == book.publisher:
            color = COLOR_PUBLISHER
            label = "PUBLISHER"
        else:
            color = COLOR_OTHER
            label = ""

        # Draw rectangle
        cv2.rectangle(result, (x1, y1), (x2, y2), color, 2)

        # Label
        if label:
            cv2.putText(
                result, label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
            )

    # Info box at bottom
    info_h = 100
    overlay = result.copy()
    cv2.rectangle(overlay, (0, h - info_h), (w, h), (0, 0, 0), -1)
    result = cv2.addWeighted(overlay, 0.7, result, 0.3, 0)

    # Info text
    y_offset = h - info_h + 25
    cv2.putText(result, f"Title: {book.title or 'N/A'}",
                (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.putText(result, f"Author: {book.author or 'N/A'}",
                (10, y_offset + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.putText(result, f"Publisher: {book.publisher or 'N/A'}",
                (10, y_offset + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    return result


def process_single_image(
    image: np.ndarray,
    pipeline: OCRPipeline,
    show: bool = True,
    save_path: Path = None
) -> BookInfo:
    """
    Process a single image.

    Args:
        image: BGR image
        pipeline: Initialized OCR pipeline
        show: Whether to show result
        save_path: Path to save result

    Returns:
        BookInfo with extracted data
    """
    h, w = image.shape[:2]
    print(f"Processing image {w}x{h}...")

    # OCR
    text_boxes = pipeline.process_image(image)
    print(f"Found {len(text_boxes)} text blocks")

    # Parse book info
    book = parse_book_cover(text_boxes, h, w)

    # Text output
    print("\n" + format_book_info(book))

    # Visualization
    if show or save_path:
        result_image = draw_results(image, book)

        if save_path:
            cv2.imwrite(str(save_path), result_image)
            print(f"\nResult saved: {save_path}")

        if show:
            window_name = "A.B.C. OCR Result"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.imshow(window_name, result_image)
            print("\nPress 'q' or ESC to exit, 's' to save...")

            while True:
                key = cv2.waitKey(0) & 0xFF
                if key == ord('q') or key == 27:  # q or ESC
                    break
                elif key == ord('s'):
                    output = config.TEST_IMAGES_DIR / "result.jpg"
                    cv2.imwrite(str(output), result_image)
                    print(f"Saved: {output}")

            cv2.destroyAllWindows()

    return book


def run_continuous(pipeline: OCRPipeline):
    """
    Continuous mode: capture and process frames from camera.
    """
    print("Continuous mode - Press 'q' to exit, SPACE to capture")

    rtsp_url = config.rtsp.get_url()
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

    if not cap.isOpened():
        print(f"Error: cannot open stream {rtsp_url}")
        return

    window_name = "A.B.C. Preview"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error reading frame")
                continue

            # Show preview
            cv2.imshow(window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
            elif key == ord(' '):
                # Capture and process
                print("\n--- Capture ---")
                process_single_image(frame, pipeline, show=False)
                print("---------------\n")

    finally:
        cap.release()
        cv2.destroyAllWindows()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="A.B.C. OCR Test - Book cover recognition"
    )
    parser.add_argument(
        "--image", "-i",
        type=str,
        default=None,
        help="Image path (default: capture from camera)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output image path"
    )
    parser.add_argument(
        "--continuous", "-c",
        action="store_true",
        help="Continuous mode with camera preview"
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="No window display (text output only)"
    )
    parser.add_argument(
        "--metis",
        action="store_true",
        help="Use Metis hardware acceleration"
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug"
    )
    args = parser.parse_args()

    if args.debug:
        config.app.debug = True

    # Banner
    print("=" * 50)
    print("  A.B.C. - A.I. Book Cataloguer")
    print("  OCR PoC Test")
    print("=" * 50)
    print()

    # Initialize pipeline
    print("Initializing OCR pipeline...")
    try:
        pipeline = OCRPipeline(use_metis=args.metis)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Operating mode
    if args.continuous:
        run_continuous(pipeline)
    elif args.image:
        # Load from file
        image = capture_from_file(args.image)
        if image is None:
            sys.exit(1)

        output_path = Path(args.output) if args.output else None
        process_single_image(
            image, pipeline,
            show=not args.no_display,
            save_path=output_path
        )
    else:
        # Single capture from camera
        print("Capturing frame from camera...")
        image = capture_frame()
        if image is None:
            print("Error capturing frame")
            sys.exit(1)

        # Save captured frame
        save_frame(image, config.TEST_IMAGES_DIR / "capture.jpg")

        output_path = Path(args.output) if args.output else None
        process_single_image(
            image, pipeline,
            show=not args.no_display,
            save_path=output_path
        )


if __name__ == "__main__":
    main()
