"""
Text image preprocessing for improved OCR recognition.
Applies a pipeline of image enhancements to cropped text regions
before feeding them to recognition models.
"""

import cv2
import numpy as np


class TextPreprocessor:
    """Configurable preprocessing pipeline for text crop images.

    Steps (in order):
    0. Pad      - replicate-border padding so Tesseract sees letter edges
    1. Upscale  - enlarge small crops so OCR models see more detail
    2. CLAHE    - adaptive contrast equalization (handles shadows/uneven lighting)
    3. Denoise  - bilateral filter (preserves edges, smooths noise)
    4. Sharpen  - unsharp mask to emphasize character contours
    5. Binarize - Otsu threshold to separate text from illustrated backgrounds
    """

    def __init__(self, *, pad: int = 10,
                 min_height: int = 32, upscale_target: int = 64,
                 clahe_clip: float = 2.0, clahe_grid: int = 8,
                 denoise_strength: int = 10,
                 sharpen_amount: float = 1.5,
                 binarize: bool = True,
                 debug: bool = False):
        self.pad = pad
        self.min_height = min_height
        self.upscale_target = upscale_target
        self.clahe_clip = clahe_clip
        self.clahe_grid = clahe_grid
        self.denoise_strength = denoise_strength
        self.sharpen_amount = sharpen_amount
        self.binarize = binarize
        self.debug = debug

    def process(self, image: np.ndarray) -> np.ndarray:
        """Apply full preprocessing pipeline.

        Args:
            image: BGR crop of a text region.

        Returns:
            Preprocessed BGR image (or grayscale converted back to BGR if binarized).
        """
        img = image.copy()

        img = self._pad(img)
        img = self._upscale(img)
        img = self._clahe(img)
        img = self._denoise(img)
        img = self._sharpen(img)
        if self.binarize:
            img = self._binarize(img)

        return img

    # ------------------------------------------------------------------
    # Individual steps
    # ------------------------------------------------------------------

    def _pad(self, img: np.ndarray) -> np.ndarray:
        """Add replicate-border padding so characters near the edge are readable."""
        if self.pad > 0:
            img = cv2.copyMakeBorder(
                img, self.pad, self.pad, self.pad, self.pad,
                cv2.BORDER_REPLICATE,
            )
            if self.debug:
                print(f"  [preprocess] pad {self.pad}px")
        return img

    def _upscale(self, img: np.ndarray) -> np.ndarray:
        """Enlarge crops smaller than min_height using LANCZOS interpolation."""
        h = img.shape[0]
        if h < self.min_height:
            scale = self.upscale_target / h
            new_w = int(img.shape[1] * scale)
            new_h = self.upscale_target
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
            if self.debug:
                print(f"  [preprocess] upscale {h} -> {new_h}px")
        return img

    def _clahe(self, img: np.ndarray) -> np.ndarray:
        """Adaptive histogram equalization on the L channel (LAB)."""
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(
            clipLimit=self.clahe_clip,
            tileGridSize=(self.clahe_grid, self.clahe_grid),
        )
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    def _denoise(self, img: np.ndarray) -> np.ndarray:
        """Bilateral filter: smooths flat regions while preserving edges."""
        if self.denoise_strength <= 0:
            return img
        return cv2.bilateralFilter(img, 9, 75, 75)

    def _sharpen(self, img: np.ndarray) -> np.ndarray:
        """Unsharp mask: sharpen edges without amplifying noise too much."""
        if self.sharpen_amount <= 0:
            return img
        blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=3)
        return cv2.addWeighted(img, 1.0 + self.sharpen_amount,
                               blurred, -self.sharpen_amount, 0)

    def _binarize(self, img: np.ndarray) -> np.ndarray:
        """Otsu binarization to separate text from background.

        Returns a 3-channel BGR image so downstream code doesn't need changes.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
