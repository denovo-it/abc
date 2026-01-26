#!/usr/bin/env python3
"""
OCR Pipeline for book cover text recognition.
Supports both CPU (ONNX Runtime) and Metis (Voyager SDK) inference.
"""

import sys
import argparse
from pathlib import Path
from dataclasses import dataclass
from abc import ABC, abstractmethod

import cv2
import numpy as np

import config

# Try to import ONNX Runtime
try:
    import onnxruntime as ort
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False

# Try to import Voyager SDK
try:
    if config.check_voyager_env():
        from axelera.app import create_inference_stream, config as ax_config
        HAS_METIS = True
    else:
        HAS_METIS = False
except ImportError:
    HAS_METIS = False


@dataclass
class TextBox:
    """Represents a detected text box."""
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    text: str
    confidence: float


class OCRBackend(ABC):
    """Abstract base class for OCR backends."""

    @abstractmethod
    def detect_text(self, image: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Detect text regions in image."""
        pass

    @abstractmethod
    def recognize_text(self, image: np.ndarray) -> tuple[str, float]:
        """Recognize text in cropped image region."""
        pass


class ONNXBackend(OCRBackend):
    """ONNX Runtime backend for CPU inference."""

    def __init__(self):
        if not HAS_ONNX:
            raise RuntimeError("onnxruntime not installed")

        self.det_session = None
        self.rec_session = None
        self.char_dict = None

        self._load_models()
        self._load_char_dict()

    def _load_models(self):
        """Load ONNX models."""
        # Detection model
        det_path = config.ocr.det_model_path
        if det_path.exists():
            self.det_session = ort.InferenceSession(
                str(det_path),
                providers=['CPUExecutionProvider']
            )
            if config.app.debug:
                print(f"Detection model loaded: {det_path}")

        # Recognition model
        rec_path = config.ocr.rec_model_path
        if rec_path.exists():
            self.rec_session = ort.InferenceSession(
                str(rec_path),
                providers=['CPUExecutionProvider']
            )
            if config.app.debug:
                print(f"Recognition model loaded: {rec_path}")
        else:
            print(f"Warning: Recognition model not found: {rec_path}")
            print("Run: cd models && ./download_models.sh")

    def _load_char_dict(self):
        """Load character dictionary for CTC decoding."""
        dict_path = config.ocr.rec_char_dict
        if dict_path.exists():
            with open(dict_path, 'r', encoding='utf-8') as f:
                chars = [line.strip() for line in f if line.strip()]
            # PP-OCRv3 format: blank (0), space (1), then dictionary chars (2+)
            self.char_dict = ['', ' '] + chars
            if config.app.debug:
                print(f"Dictionary loaded: {len(self.char_dict)} characters")
        else:
            # Fallback to basic Latin characters
            self.char_dict = ['', ' '] + list(
                "0123456789"
                "abcdefghijklmnopqrstuvwxyz"
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                ".,;:!?'-\"()"
            )
            print(f"Warning: Dictionary not found, using fallback")

    def _preprocess_detection(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for text detection."""
        # Resize to standard size
        target_size = 960
        h, w = image.shape[:2]
        scale = target_size / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)

        # Pad to multiple of 32
        new_w = (new_w + 31) // 32 * 32
        new_h = (new_h + 31) // 32 * 32

        img = cv2.resize(image, (new_w, new_h))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = (img - 0.5) / 0.5  # Normalize to [-1, 1]
        img = img.transpose(2, 0, 1)  # HWC -> CHW
        img = np.expand_dims(img, 0)  # Add batch dim

        return img, scale

    def _preprocess_recognition(self, image: np.ndarray) -> np.ndarray:
        """Preprocess cropped text region for recognition (PP-OCRv3 format)."""
        target_h = 48  # PP-OCRv3 recognition height
        max_w = 320    # Max width

        # Convert to RGB
        img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Resize keeping aspect ratio
        img_h, img_w = img.shape[:2]
        ratio = target_h / float(img_h)
        new_w = int(img_w * ratio)

        # Limit width
        if new_w > max_w:
            new_w = max_w

        img = cv2.resize(img, (new_w, target_h))

        # Pad to width divisible by 8 (or use max_w)
        pad_w = max_w
        padded = np.zeros((target_h, pad_w, 3), dtype=np.float32)
        padded[:, :new_w, :] = img

        # PP-OCRv3 normalization: (img / 255.0 - 0.5) / 0.5 = img / 127.5 - 1
        padded = padded.astype(np.float32) / 255.0
        padded = (padded - 0.5) / 0.5

        # Transpose to NCHW
        padded = padded.transpose(2, 0, 1)
        padded = np.expand_dims(padded, 0)

        return padded.astype(np.float32)

    def _ctc_decode(self, logits: np.ndarray) -> tuple[str, float]:
        """Decode CTC output to text (PP-OCRv3 format)."""
        # logits shape: [batch, seq_len, num_classes]
        # Apply softmax to get probabilities
        logits = logits[0]  # Remove batch dim: [seq_len, num_classes]

        # Softmax
        exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        probs = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)

        # Greedy decoding
        preds = np.argmax(probs, axis=-1)
        max_probs = np.max(probs, axis=-1)

        # CTC decode: remove blanks (index 0) and duplicates
        chars = []
        confs = []
        prev = 0  # blank index

        for pred, prob in zip(preds, max_probs):
            # Skip blank (index 0)
            if pred == 0:
                prev = pred
                continue
            # Skip duplicates
            if pred == prev:
                continue
            # Add character
            if pred < len(self.char_dict):
                char = self.char_dict[pred]
                if char:  # Skip empty strings
                    chars.append(char)
                    confs.append(prob)
            prev = pred

        text = ''.join(chars)
        confidence = float(np.mean(confs)) if confs else 0.0

        return text, confidence

    def detect_text(self, image: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Detect text regions using PP-OCRv3 detection model."""
        h, w = image.shape[:2]

        # For small images, use full image (recognition works on text crops)
        if h < 100 or w < 200:
            return [(0, 0, w, h)]

        if self.det_session is None:
            return self._fallback_detection(image)

        input_tensor, scale = self._preprocess_detection(image)

        # Run detection
        input_name = self.det_session.get_inputs()[0].name
        outputs = self.det_session.run(None, {input_name: input_tensor})

        # Post-process detection output
        boxes = self._postprocess_detection(outputs[0], scale, h, w)

        # If detection found nothing, use fallback
        if not boxes:
            return self._fallback_detection(image)

        return boxes

    def _fallback_detection(self, image: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Fallback detection using simple edge/contour analysis."""
        h, w = image.shape[:2]

        # For small images, just return the whole image
        if h < 100 or w < 200:
            return [(0, 0, w, h)]

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply adaptive threshold
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )

        # Dilate to connect text regions (larger kernel for book covers)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 10))
        dilated = cv2.dilate(thresh, kernel, iterations=3)

        # Find contours
        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        boxes = []
        min_box_height = 20  # Minimum box height for text
        min_box_width = 50   # Minimum box width

        for contour in contours:
            x, y, bw, bh = cv2.boundingRect(contour)
            # Filter: must be wide enough, tall enough, and wider than tall
            if bw > min_box_width and bh > min_box_height:
                # Add generous padding
                pad_x = 10
                pad_y = 5
                x1 = max(0, x - pad_x)
                y1 = max(0, y - pad_y)
                x2 = min(w, x + bw + pad_x)
                y2 = min(h, y + bh + pad_y)
                boxes.append((x1, y1, x2, y2))

        # Sort by y position (top to bottom)
        boxes.sort(key=lambda b: b[1])

        # If no boxes found, return full image
        return boxes if boxes else [(0, 0, w, h)]

    def _postprocess_detection(self, output, scale, orig_h, orig_w):
        """Post-process PP-OCRv3 detection model output."""
        # Output is probability map [1, 1, H, W]
        prob_map = output[0, 0]

        # Binarize with threshold
        binary = (prob_map > 0.3).astype(np.uint8) * 255

        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        boxes = []
        min_box_area = 100  # Minimum area in scaled pixels
        min_box_width = 10
        min_box_height = 5

        for contour in contours:
            x, y, cw, ch = cv2.boundingRect(contour)

            # Filter tiny boxes in scaled space
            if cw < min_box_width or ch < min_box_height:
                continue
            if cw * ch < min_box_area:
                continue

            # Scale back to original size
            x1 = int(x / scale)
            y1 = int(y / scale)
            x2 = int((x + cw) / scale)
            y2 = int((y + ch) / scale)

            # Add padding
            pad = 5
            x1 = max(0, x1 - pad)
            y1 = max(0, y1 - pad)
            x2 = min(orig_w, x2 + pad)
            y2 = min(orig_h, y2 + pad)

            # Filter too small boxes in original space
            box_w = x2 - x1
            box_h = y2 - y1
            if box_w < 20 or box_h < 10:
                continue

            boxes.append((x1, y1, x2, y2))

        # Sort by y position (top to bottom)
        boxes.sort(key=lambda b: b[1])

        return boxes

    def recognize_text(self, image: np.ndarray) -> tuple[str, float]:
        """Recognize text in cropped image."""
        if self.rec_session is None:
            return "", 0.0

        input_tensor = self._preprocess_recognition(image)

        input_name = self.rec_session.get_inputs()[0].name
        output = self.rec_session.run(None, {input_name: input_tensor})

        text, conf = self._ctc_decode(output[0])

        return text, conf


class MetisBackend(OCRBackend):
    """Hybrid backend: Uses Voyager SDK environment with CPU ONNX fallback.

    Note: PP-OCRv3 detection model was compiled for Metis but requires
    additional work to properly handle the quantized output format.
    Recognition model is not Metis-compatible (uses unsupported operators).

    Current implementation uses CPU ONNX for both detection and recognition
    when running in the Voyager SDK environment.
    """

    def __init__(self):
        if not HAS_METIS:
            raise RuntimeError(
                "Voyager SDK not available. "
                "Activate with: source ../voyager-sdk/venv/bin/activate"
            )

        # Use ONNX for both detection and recognition
        # PP-OCRv3 rec model has unsupported operators (MatMul, ReduceMean)
        # Detection model output format needs additional post-processing work
        self._onnx_backend = ONNXBackend()

        # Check if compiled detection model exists
        voyager_sdk_path = Path(__file__).parent.parent / "voyager-sdk"
        det_build_path = voyager_sdk_path / "build" / "ppocr-det"

        if det_build_path.exists():
            if config.app.debug:
                print("Metis detection model found (using CPU for PoC)")
        else:
            if config.app.debug:
                print("Metis detection model not compiled")

    def detect_text(self, image: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Detect text using CPU ONNX backend."""
        return self._onnx_backend.detect_text(image)

    def recognize_text(self, image: np.ndarray) -> tuple[str, float]:
        """Recognize text using CPU ONNX backend."""
        return self._onnx_backend.recognize_text(image)


class OCRPipeline:
    """OCR Pipeline with backend selection."""

    def __init__(self, use_metis: bool = False):
        """
        Initialize OCR pipeline.

        Args:
            use_metis: If True, use Metis hardware acceleration
        """
        if use_metis:
            self.backend = MetisBackend()
        else:
            self.backend = ONNXBackend()

    def process_image(self, image: np.ndarray) -> list[TextBox]:
        """
        Process image and return detected text boxes.

        Args:
            image: BGR image

        Returns:
            List of TextBox with text and position
        """
        # Detect text regions
        boxes = self.backend.detect_text(image)

        if config.app.debug:
            print(f"Detected {len(boxes)} text regions")

        results = []
        for bbox in boxes:
            x1, y1, x2, y2 = bbox

            # Crop region
            region = image[y1:y2, x1:x2]
            if region.size == 0:
                continue

            # Recognize text
            text, conf = self.backend.recognize_text(region)

            if text.strip():
                results.append(TextBox(
                    bbox=bbox,
                    text=text.strip(),
                    confidence=conf
                ))

        # Sort by vertical position
        results.sort(key=lambda b: b.bbox[1])

        return results


def main():
    """Entry point for standalone OCR test."""
    parser = argparse.ArgumentParser(description="Test OCR on image")
    parser.add_argument(
        "image",
        type=str,
        help="Image path to process"
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

    # Load image
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: file not found: {image_path}")
        sys.exit(1)

    image = cv2.imread(str(image_path))
    if image is None:
        print(f"Error: cannot read image: {image_path}")
        sys.exit(1)

    print(f"Image loaded: {image.shape}")

    # Initialize pipeline
    try:
        pipeline = OCRPipeline(use_metis=args.metis)
    except Exception as e:
        print(f"Error initializing pipeline: {e}")
        sys.exit(1)

    # Process image
    print("\nRunning OCR...")
    results = pipeline.process_image(image)

    # Show results
    print(f"\nFound {len(results)} text blocks:\n")
    for i, box in enumerate(results, 1):
        print(f"{i}. [{box.confidence:.2f}] {box.text}")
        print(f"   Box: {box.bbox}")
        print()


if __name__ == "__main__":
    main()
