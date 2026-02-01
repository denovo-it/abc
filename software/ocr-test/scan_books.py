#!/usr/bin/env python3
"""
Continuous book scanning with OCR.
Processes one book after another with automatic preprocessing and postprocessing.

Usage:
    python3 scan_books.py                    # Manual mode (press ENTER for each book)
    python3 scan_books.py --auto             # Auto mode (3s delay between scans)
    python3 scan_books.py --model tesseract  # Use specific OCR model
    python3 scan_books.py --no-preprocessing # Skip preprocessing

OCR Models:
    - tesseract: Fast, good for clean images (~8s/book)
    - ppocr: Very fast, handles rotations (~3-5s/book)
    - easyocr: Most accurate, slow (~15-18s/book) [DEFAULT]

Database-Enhanced Parsing:
    - 18,500+ known authors for accurate detection
    - 189 known publishers with imprint resolution
    - Word-level OCR error corrections
    - Intelligent author block combination
"""

import cv2
import sys
import time
import os
import re
import argparse
import subprocess
import numpy as np
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from difflib import SequenceMatcher


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

        # Default values
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
# IMAGE PREPROCESSING
# ============================================================================

class BookCoverPreprocessor:
    """
    Advanced preprocessing for book covers to improve OCR accuracy.
    Handles artistic covers, low contrast, complex backgrounds.
    """

    def __init__(self, debug=False):
        self.debug = debug

    def preprocess_for_tesseract(self, image):
        """Preprocess for Tesseract OCR (needs high contrast binary)"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Denoise
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)

        # CLAHE for contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        # Morphological gradient to enhance text edges
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        gradient = cv2.morphologyEx(enhanced, cv2.MORPH_GRADIENT, kernel)

        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Morphological cleanup
        kernel_clean = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_clean)

        return cleaned

    def preprocess_for_ppocr(self, image):
        """Preprocess for PP-OCR (handles color, needs less aggressive processing)"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Light denoising
        denoised = cv2.fastNlMeansDenoising(gray, h=10)

        # CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        # Sharpen
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)

        return sharpened

    def preprocess_for_easyocr(self, image):
        """Preprocess for EasyOCR (deep learning, needs minimal preprocessing)"""
        # EasyOCR works better with color images and minimal preprocessing
        # Keep original color, apply only light enhancement

        # Very light denoising on color image
        denoised = cv2.fastNlMeansDenoisingColored(image, h=3, hColor=3)

        # Optional: slight sharpening (very conservative)
        kernel = np.array([[0, -0.5, 0], [-0.5, 3, -0.5], [0, -0.5, 0]])
        sharpened = cv2.filter2D(denoised, -1, kernel)

        return sharpened


# ============================================================================
# OCR POST-PROCESSING
# ============================================================================

class OCRPostProcessor:
    """Post-process OCR results to fix common errors"""

    # Common OCR character substitution errors
    CHAR_CORRECTIONS = {
        '0': 'O', '1': 'I', '5': 'S', '7': 'T', '8': 'B',
        '|': 'I', '!': 'I', '@': 'A', '©': 'C', '®': 'R',
    }

    # Common word-level OCR errors (especially Italian)
    WORD_CORRECTIONS = {
        'OLMRQ': 'OLIMPO',
        'OLMDQ': 'OLIMPO',
        'OLMTQ': 'OLIMPO',
        'OLMQ': 'OLIMPO',  # Yet another variant
        'OL1MPO': 'OLIMPO',
        'OLMPO': 'OLIMPO',
        'EROL': 'EROI',
        'EROA': 'EROI',
        'EROX': 'EROI',  # New variant
        'ER0I': 'EROI',
        'GLMIQ': 'GLI',
        'GL1': 'GLI',
        'R10RDAN': 'RIORDAN',
        'R1ORDAN': 'RIORDAN',
        'MONDADOR1': 'MONDADORI',
        'MONOADORI': 'MONDADORI',
        'PENGU1N': 'PENGUIN',
        'BLSTSELLERS': '',  # Remove series name (directly, not via BESTSELLERS)
        'BESTSELLERS': '',  # Remove series name
        # OSCAR not removed - needed for publisher imprint mapping (now filtered in parser)
        'DELL': "DELL'",  # Often missing apostrophe
    }

    def __init__(self, debug=False):
        self.debug = debug

    def correct_text(self, text, text_type='title'):
        """Correct OCR errors in text"""
        if not text or text == '[not identified]':
            return text

        # Word-level corrections (common OCR errors)
        corrected = self._correct_words(text)

        # Character-level corrections
        corrected = self._correct_characters(corrected)

        # Pattern-based corrections (spacing)
        corrected = self._apply_patterns(corrected, text_type)

        # Capitalization normalization
        corrected = self._normalize_capitalization(corrected, text_type)

        return corrected

    def _correct_words(self, text):
        """Apply word-level corrections for common OCR mistakes"""
        corrected = text

        # Replace whole words
        words = corrected.split()
        corrected_words = []

        for word in words:
            word_upper = word.upper()
            # Check direct match
            if word_upper in self.WORD_CORRECTIONS:
                replacement = self.WORD_CORRECTIONS[word_upper]
                if replacement:  # Only add if not empty string
                    corrected_words.append(replacement)
            else:
                corrected_words.append(word)

        return ' '.join(corrected_words)

    def _correct_characters(self, text):
        """Apply character-level corrections"""
        corrected = text

        for wrong, right in self.CHAR_CORRECTIONS.items():
            # Replace in all-caps words (likely titles)
            pattern = r'\b([A-Z]*' + re.escape(wrong) + r'[A-Z]*)\b'

            def replace_in_caps(match):
                word = match.group(1)
                letter_count = sum(c.isalpha() for c in word)
                if letter_count > len(word) * 0.5:
                    return word.replace(wrong, right)
                return word

            corrected = re.sub(pattern, replace_in_caps, corrected)

        return corrected

    def _apply_patterns(self, text, text_type):
        """Apply pattern-based corrections"""
        if text_type == 'title':
            text = re.sub(r'\s+OF\s+', ' OF ', text, flags=re.IGNORECASE)
            text = re.sub(r'\s+THE\s+', ' THE ', text, flags=re.IGNORECASE)
            text = re.sub(r'\s+AND\s+', ' AND ', text, flags=re.IGNORECASE)
            text = re.sub(r'\s+', ' ', text).strip()
        elif text_type == 'author':
            text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _normalize_capitalization(self, text, text_type):
        """Normalize capitalization based on context"""
        if text_type == 'title' and text.isupper():
            words = text.split()
            lowercase_words = {'of', 'the', 'and', 'in', 'on', 'at', 'to', 'a', 'an'}
            title_cased = []

            for i, word in enumerate(words):
                if i == 0 or word.lower() not in lowercase_words:
                    title_cased.append(word.capitalize())
                else:
                    title_cased.append(word.lower())

            return ' '.join(title_cased)

        elif text_type == 'author' and (text.isupper() or text.islower()):
            return text.title()

        elif text_type == 'publisher' and text.islower():
            return text.upper()

        return text

    def improve_result(self, book_info):
        """Improve entire book information result"""
        improved = book_info.copy()

        if improved.get('title') and improved['title'] != '[not identified]':
            improved['title'] = self.correct_text(improved['title'], 'title')

        if improved.get('author') and improved['author'] != '[not identified]':
            improved['author'] = self.correct_text(improved['author'], 'author')

        if improved.get('publisher') and improved['publisher'] != '[not identified]':
            improved['publisher'] = self.correct_text(improved['publisher'], 'publisher')

        # Boost confidence if corrections made
        original_title = book_info.get('title', '')
        improved_title = improved.get('title', '')

        if original_title and improved_title and original_title != improved_title:
            old_confidence = improved.get('confidence', 0.0)
            similarity = SequenceMatcher(None, original_title, improved_title).ratio()

            if similarity > 0.7:
                boost = 0.05 * similarity
                improved['confidence'] = min(1.0, old_confidence + boost)

        return improved


# ============================================================================
# LLM CORRECTION
# ============================================================================

# ============================================================================
# BOOK COVER PARSER
# ============================================================================

@dataclass
class TextBox:
    """Represents a detected text region"""
    text: str
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    confidence: float = 0.0


@dataclass
class BookInfo:
    """Book information extracted from cover"""
    title: str = ""
    author: str = ""
    publisher: str = ""
    confidence: float = 0.0
    raw_texts: List[TextBox] = field(default_factory=list)


class BookCoverParser:
    """Parse book cover to extract title, author, publisher"""

    # Common title words
    TITLE_WORDS = {
        'THE', 'OF', 'AND', 'IN', 'TO', 'A', 'AN', 'FOR', 'ON', 'WITH', 'AT', 'BY',
        'THOUSAND', 'HUNDRED', 'DOOR', 'DOORS', 'BOOK', 'TALE', 'STORY', 'LIFE',
        'WORLD', 'TIME', 'NIGHT', 'DAY', 'YEAR', 'HISTORY', 'CHRONICLES'
    }

    # Publisher patterns
    PUBLISHER_PATTERNS = [
        r'^(PENGUIN|VINTAGE|HARPER|RANDOM|SIMON|MACMILLAN|HACHETTE|SCHOLASTIC)',
        r'(BOOKS?|PRESS|PUBLISHING|PUBLISHERS?|HOUSE|EDITIONS?)$',
    ]

    # Quote patterns (to filter reviews)
    QUOTE_PATTERNS = [
        r"^['\"].*['\"]$",
        r"(?i)(beautiful|brilliant|stunning|masterpiece|compelling)",
    ]

    def __init__(self):
        # Load authors database
        self.known_authors = self._load_authors_database()
        # Load publishers database
        self.known_publishers = self._load_publishers_database()
        # Load publisher imprints mapping
        self.publisher_imprints = self._load_imprints_mapping()

    def _load_authors_database(self):
        """Load known authors from file"""
        authors = set()
        try:
            if os.path.exists('known_authors.txt'):
                with open('known_authors.txt', 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            authors.add(line.upper())
        except Exception:
            pass  # Continue without database if file missing
        return authors

    def _load_publishers_database(self):
        """Load known publishers from file"""
        publishers = set()
        try:
            if os.path.exists('known_publishers.txt'):
                with open('known_publishers.txt', 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            publishers.add(line.upper())
        except Exception:
            pass
        return publishers

    def _load_imprints_mapping(self):
        """Load imprint to publisher mapping"""
        mapping = {}
        try:
            if os.path.exists('publisher_imprints.txt'):
                with open('publisher_imprints.txt', 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            imprint, publisher = line.split('=', 1)
                            mapping[imprint.strip().upper()] = publisher.strip().upper()
        except Exception:
            pass
        return mapping

    def parse(self, text_boxes: List[TextBox], image_height: int, image_width: int) -> BookInfo:
        """Parse book cover from detected text boxes"""
        if not text_boxes:
            return BookInfo()

        # Merge nearby boxes
        merged = self._merge_nearby_boxes(text_boxes, image_height)

        book = BookInfo(raw_texts=text_boxes)

        # Calculate scores
        scored = []
        for box in merged:
            position_y = (box.bbox[1] + box.bbox[3]) / 2
            position_y_ratio = position_y / image_height

            prominence = self._calculate_prominence(box, image_height, image_width)

            scored.append({
                'box': box,
                'text': box.text,
                'prominence': prominence,
                'position_y': position_y,
                'position_y_ratio': position_y_ratio,
                'is_quote': self._is_quote_or_review(box.text)
            })

        # Sort by prominence
        scored.sort(key=lambda x: x['prominence'], reverse=True)

        used_texts = set()

        # Find publisher
        for item in scored:
            if item['text'] in used_texts or item['is_quote']:
                continue
            if self._is_likely_publisher(item['text'], item['position_y_ratio']):
                book.publisher = item['text']
                used_texts.add(item['text'])
                break

        # Find author (with multi-block combination)
        author_candidates = []
        for item in scored:
            if item['text'] in used_texts or item['is_quote']:
                continue

            # Skip known imprints (OSCAR, BUR, etc.) - they're for publisher, not author
            if item['text'].upper() in self.publisher_imprints:
                continue

            if self._is_likely_author(item['text'], item['position_y_ratio']):
                author_candidates.append(item)

        if author_candidates:
            # Try to combine adjacent author blocks (e.g., "RICK" + "RIORDAN")
            combined_author = self._combine_author_blocks(author_candidates, scored, image_height)

            if combined_author:
                book.author = combined_author['text']
                # Mark all used parts
                for part in combined_author['parts']:
                    used_texts.add(part)
            else:
                # Fallback: use single best candidate
                author_candidates.sort(key=lambda x: (
                    x['position_y_ratio'] > 0.6,
                    x['prominence']
                ), reverse=True)
                book.author = author_candidates[0]['text']
                used_texts.add(book.author)

        # Find title
        title_candidates = []
        for item in scored:
            if item['text'] in used_texts or item['is_quote']:
                continue
            if self._is_likely_title(item['text'], item['position_y_ratio']):
                title_candidates.append(item)

        if title_candidates:
            title_candidates.sort(key=lambda x: x['position_y'])
            title_parts = title_candidates[:3]
            book.title = " ".join(item['text'] for item in title_parts)
            book.confidence = sum(item['prominence'] for item in title_parts) / len(title_parts) / 10

            for item in title_parts:
                used_texts.add(item['text'])

        # Fallback: use most prominent unused text
        if not book.title:
            for item in scored:
                if item['text'] not in used_texts and not item['is_quote']:
                    book.title = item['text']
                    book.confidence = item['prominence'] / 10
                    break

        # Resolve imprints to actual publishers
        if book.publisher:
            book.publisher = self._resolve_imprint_to_publisher(book.publisher)

        return book

    def _resolve_imprint_to_publisher(self, publisher_text: str) -> str:
        """Resolve imprint/series name to actual publisher"""
        publisher_upper = publisher_text.upper().strip()

        # Direct lookup in imprints mapping
        if publisher_upper in self.publisher_imprints:
            return self.publisher_imprints[publisher_upper]

        # Check if any part of the text is an imprint
        words = publisher_upper.split()
        for word in words:
            if word in self.publisher_imprints:
                return self.publisher_imprints[word]

        # Check multi-word imprints (e.g., "BEST SELLERS OSCAR" contains "OSCAR")
        for imprint, real_publisher in self.publisher_imprints.items():
            if imprint in publisher_upper:
                return real_publisher

        # No imprint found, return as-is
        return publisher_text

    def _merge_nearby_boxes(self, boxes: List[TextBox], img_h: int) -> List[TextBox]:
        """Merge text boxes on same line (conservative)"""
        if not boxes:
            return []

        sorted_boxes = sorted(boxes, key=lambda b: b.bbox[1])
        merged = []
        current_line = [sorted_boxes[0]]

        for box in sorted_boxes[1:]:
            prev_box = current_line[-1]

            y_threshold = img_h * 0.02
            horizontal_gap = box.bbox[0] - prev_box.bbox[2]
            max_gap = img_h * 0.15

            if abs(box.bbox[1] - prev_box.bbox[1]) < y_threshold and horizontal_gap < max_gap:
                current_line.append(box)
            else:
                if len(current_line) > 1:
                    current_line.sort(key=lambda b: b.bbox[0])
                    merged_text = " ".join(b.text for b in current_line)
                    merged_bbox = (
                        min(b.bbox[0] for b in current_line),
                        min(b.bbox[1] for b in current_line),
                        max(b.bbox[2] for b in current_line),
                        max(b.bbox[3] for b in current_line)
                    )
                    merged_conf = sum(b.confidence for b in current_line) / len(current_line)
                    merged.append(TextBox(merged_text, merged_bbox, merged_conf))
                else:
                    merged.append(current_line[0])

                current_line = [box]

        # Last line
        if len(current_line) > 1:
            current_line.sort(key=lambda b: b.bbox[0])
            merged_text = " ".join(b.text for b in current_line)
            merged_bbox = (
                min(b.bbox[0] for b in current_line),
                min(b.bbox[1] for b in current_line),
                max(b.bbox[2] for b in current_line),
                max(b.bbox[3] for b in current_line)
            )
            merged_conf = sum(b.confidence for b in current_line) / len(current_line)
            merged.append(TextBox(merged_text, merged_bbox, merged_conf))
        else:
            merged.append(current_line[0])

        return merged

    def _calculate_prominence(self, box: TextBox, img_h: int, img_w: int) -> float:
        """Calculate how prominent a text box is"""
        x1, y1, x2, y2 = box.bbox

        # Size score
        box_height = y2 - y1
        box_width = x2 - x1
        area = box_width * box_height
        area_ratio = area / (img_w * img_h)
        size_score = min(area_ratio * 100, 10.0)

        # Font size
        font_score = min(box_height / 10, 5.0)

        # Position score (center more prominent for title)
        center_y = (y1 + y2) / 2
        center_y_ratio = center_y / img_h

        if 0.2 < center_y_ratio < 0.6:
            position_score = 3.0
        elif 0.1 < center_y_ratio < 0.7:
            position_score = 2.0
        else:
            position_score = 1.0

        # Confidence score
        conf_score = box.confidence * 2

        return size_score + font_score + position_score + conf_score

    def _is_quote_or_review(self, text: str) -> bool:
        """Check if text is a quote or review"""
        for pattern in self.QUOTE_PATTERNS:
            if re.search(pattern, text):
                return True

        if text.startswith(('\"', "'", '"', '"', ''', ''')) and \
           text.endswith(('\"', "'", '"', '"', ''', ''')):
            return True

        if len(text) > 20 and any(word in text.lower() for word in
                                 ['beautiful', 'brilliant', 'stunning', 'masterpiece',
                                  'compelling', 'gripping', 'unforgettable']):
            return True

        return False

    def _is_likely_title(self, text: str, position_y_ratio: float) -> bool:
        """Check if text is likely the title"""
        if self._is_quote_or_review(text):
            return False

        words = text.split()

        if len(words) < 2:
            return False

        words_upper = [w.upper() for w in words]
        if any(w in self.TITLE_WORDS for w in words_upper):
            return True

        if 0.1 < position_y_ratio < 0.65:
            if len(words) >= 2 and sum(1 for w in words if w and w[0].isupper()) >= 2:
                return True

        return False

    def _is_likely_author(self, text: str, position_y_ratio: float) -> bool:
        """Check if text is likely an author name"""
        if self._is_quote_or_review(text):
            return False

        text_clean = text.strip().upper()

        # Check database first (strongest signal)
        if self._matches_author_database(text_clean):
            return True

        # Original heuristics for texts not in database
        if len(text_clean) < 6 or len(text_clean) > 40:
            return False

        if re.search(r'\d', text_clean):
            return False

        words = text_clean.split()

        if not (2 <= len(words) <= 4):
            return False

        # Each word ≥3 chars (blocks "DO RS")
        if any(len(w) < 3 for w in words):
            return False

        if not all(w[0].isupper() for w in words if w):
            return False

        if position_y_ratio < 0.35:
            return False

        if len(words) == 2:
            if all(w[0].isupper() and not w.isupper() for w in words):
                return True
            elif all(w.isupper() for w in words):
                if position_y_ratio > 0.6:
                    return True

        if 3 <= len(words) <= 4:
            if position_y_ratio > 0.5:
                return True

        return False

    def _matches_author_database(self, text: str) -> bool:
        """Check if text matches known authors database"""
        if not self.known_authors:
            return False

        text_upper = text.upper()

        # Exact match (full name or surname)
        if text_upper in self.known_authors:
            return True

        # Check if any word in text is a known surname
        words = text_upper.split()
        for word in words:
            if len(word) > 2 and word in self.known_authors:
                return True

        # Fuzzy match for common OCR errors
        # Check if text is very similar to known author (edit distance ≤ 2)
        for known in self.known_authors:
            if len(known) < 4:  # Skip short entries for fuzzy
                continue
            if abs(len(text_upper) - len(known)) > 2:
                continue
            # Simple similarity check
            if self._similarity(text_upper, known) > 0.85:
                return True

        return False

    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity (0-1)"""
        if not s1 or not s2:
            return 0.0
        # Use SequenceMatcher from difflib (already imported)
        return SequenceMatcher(None, s1, s2).ratio()

    def _combine_author_blocks(self, author_candidates: list, all_scored: list, img_height: int) -> dict:
        """
        Try to combine adjacent blocks that are all author parts.
        E.g., "RICK" + "RIORDAN" -> "RICK RIORDAN"
        """
        if not author_candidates:
            return None

        # Look for blocks in similar vertical position that could be name parts
        for candidate in author_candidates:
            # Find nearby blocks (within 10% vertical distance)
            y_pos = candidate['position_y']
            y_threshold = img_height * 0.1

            nearby_blocks = []
            for item in all_scored:
                if item['text'] == candidate['text']:
                    nearby_blocks.append(item)
                    continue

                # Check if vertically close
                if abs(item['position_y'] - y_pos) < y_threshold:
                    # Check if could be author part (in database or looks like name)
                    text_upper = item['text'].upper()

                    # Skip if it's a known imprint/series (OSCAR, BUR, etc.)
                    if text_upper in self.publisher_imprints:
                        continue

                    if (text_upper in self.known_authors or
                        self._looks_like_name_part(item['text'])):
                        nearby_blocks.append(item)

            # If we found multiple nearby blocks, combine them
            if len(nearby_blocks) >= 2:
                # Sort left to right
                nearby_blocks.sort(key=lambda x: x['box'].bbox[0])

                # Combine texts
                combined_text = " ".join(b['text'] for b in nearby_blocks)

                # Check if combined result makes sense
                if self._is_valid_author_name(combined_text):
                    return {
                        'text': combined_text,
                        'parts': [b['text'] for b in nearby_blocks],
                        'prominence': max(b['prominence'] for b in nearby_blocks)
                    }

        return None

    def _looks_like_name_part(self, text: str) -> bool:
        """Check if text looks like it could be part of a name"""
        text_clean = text.strip()

        # Single word, 3-15 chars, starts with capital
        if len(text_clean) < 3 or len(text_clean) > 15:
            return False

        if not text_clean[0].isupper():
            return False

        # No numbers
        if re.search(r'\d', text_clean):
            return False

        # All letters or all caps
        words = text_clean.split()
        if len(words) == 1:
            return True

        return False

    def _is_valid_author_name(self, text: str) -> bool:
        """Check if combined text is a valid author name"""
        words = text.split()

        # 2-4 words for author name
        if not (2 <= len(words) <= 4):
            return False

        # Check in database
        text_upper = text.upper()
        if text_upper in self.known_authors:
            return True

        # Check if at least one word is in database (surname)
        for word in words:
            if word.upper() in self.known_authors:
                return True

        # Fallback: standard name pattern
        if len(words) == 2:
            # Each word capitalized, 3+ chars
            if all(w[0].isupper() and len(w) >= 3 for w in words):
                return True

        return False

    def _is_likely_publisher(self, text: str, position_y_ratio: float) -> bool:
        """Check if text is likely a publisher"""
        text_upper = text.strip().upper()

        # Check database first (strongest signal)
        if text_upper in self.known_publishers:
            return True

        # Check imprints mapping (e.g., "OSCAR" -> "MONDADORI")
        if text_upper in self.publisher_imprints:
            return True

        # Check for partial matches in database
        for known_pub in self.known_publishers:
            if known_pub in text_upper or text_upper in known_pub:
                return True

        # Original pattern matching
        for pattern in self.PUBLISHER_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        # Position-based heuristic (bottom of cover)
        if position_y_ratio > 0.85:
            if len(text) < 30 and len(text.split()) <= 3:
                return True

        return False


# ============================================================================
# OCR EXECUTION
# ============================================================================

def run_ocr_easyocr(image_path):
    """Run EasyOCR on image"""
    try:
        import easyocr
    except ImportError:
        print("❌ EasyOCR not installed. Install with: pip install easyocr")
        sys.exit(1)

    reader = easyocr.Reader(['en'], gpu=False)
    results = reader.readtext(image_path)

    text_boxes = []
    for (bbox, text, conf) in results:
        # Convert bbox to x1,y1,x2,y2
        x1 = min(p[0] for p in bbox)
        y1 = min(p[1] for p in bbox)
        x2 = max(p[0] for p in bbox)
        y2 = max(p[1] for p in bbox)

        text_boxes.append(TextBox(text, (x1, y1, x2, y2), conf))

    return text_boxes


def run_ocr_tesseract(image_path):
    """Run Tesseract OCR on image"""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        print("❌ Tesseract not installed. Install with: pip install pytesseract pillow")
        sys.exit(1)

    img = Image.open(image_path)
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

    text_boxes = []
    for i in range(len(data['text'])):
        if int(data['conf'][i]) > 0:
            text = data['text'][i].strip()
            if text:
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                conf = int(data['conf'][i]) / 100.0
                text_boxes.append(TextBox(text, (x, y, x + w, y + h), conf))

    return text_boxes


def run_ocr_ppocr(image_path):
    """Run PP-OCR on image"""
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        print("❌ PaddleOCR not installed. Install with: pip install paddlepaddle paddleocr")
        sys.exit(1)

    ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False, show_log=False)
    results = ocr.ocr(image_path, cls=True)

    text_boxes = []
    if results and results[0]:
        for line in results[0]:
            bbox = line[0]
            text = line[1][0]
            conf = line[1][1]

            x1 = min(p[0] for p in bbox)
            y1 = min(p[1] for p in bbox)
            x2 = max(p[0] for p in bbox)
            y2 = max(p[1] for p in bbox)

            text_boxes.append(TextBox(text, (x1, y1, x2, y2), conf))

    return text_boxes


# ============================================================================
# CONTINUOUS SCANNER
# ============================================================================

class ContinuousScanner:
    """Continuous book OCR scanner"""

    def __init__(self, model='easyocr', auto_mode=False, preprocessing=True, debug=False):
        self.model = model
        self.auto_mode = auto_mode
        self.preprocessing = preprocessing
        self.debug = debug
        self.book_count = 0
        self.session_start = datetime.now()

        # Cleanup old temporary files
        self._cleanup_temp_files()

        # Load calibration
        self.loading_area = self._load_loading_area()
        if self.loading_area is None:
            print("❌ Error: Loading area not calibrated!")
            print("   Run: python3 calibrate.py")
            sys.exit(1)

        # Initialize processors
        self.preprocessor = BookCoverPreprocessor(debug=debug)
        self.postprocessor = OCRPostProcessor(debug=debug)
        self.parser = BookCoverParser()

        # Open camera
        self.rtsp_url = RTSPConfig.get_url()
        self.cap = cv2.VideoCapture(self.rtsp_url)
        if not self.cap.isOpened():
            print(f"❌ Error: Cannot open camera: {self.rtsp_url}")
            sys.exit(1)

    def _cleanup_temp_files(self):
        """Remove old temporary and debug files"""
        temp_files = [
            'temp_ocr_input.jpg',
            'test_images/debug_preprocessed_last.jpg'
        ]
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)

    def _fuzzy_correct_with_databases(self, text):
        """
        Apply fuzzy matching with databases to automatically correct OCR errors

        Instead of manually maintaining WORD_CORRECTIONS for every variant (OLMRQ, OLMDQ, OLMTQ, etc.),
        this uses fuzzy matching to find similar words in author/publisher databases.

        Example: "RIORD4N" → fuzzy match → "RIORDAN" (from database)
        """
        from difflib import SequenceMatcher

        words = text.split()
        corrected_words = []

        for word in words:
            if len(word) < 3:  # Skip very short words
                corrected_words.append(word)
                continue

            word_upper = word.upper()

            # Skip if word is a known imprint (exact match - will be handled by parser)
            if word_upper in self.parser.publisher_imprints:
                corrected_words.append(word)
                continue

            best_match = None
            best_ratio = 0.80  # Minimum similarity threshold

            # First check fuzzy match with imprints (catch common OCR errors like OSEAR → OSCAR)
            for imprint in self.parser.publisher_imprints.keys():
                ratio = SequenceMatcher(None, word_upper, imprint).ratio()
                if ratio > 0.80:  # 80% threshold for imprints (OSEAR → OSCAR = 4/5 = 0.80)
                    best_ratio = ratio
                    best_match = imprint

            # Check against known authors
            for author in self.parser.known_authors:
                ratio = SequenceMatcher(None, word_upper, author).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = author

            # Check against known publishers
            for publisher in self.parser.known_publishers:
                ratio = SequenceMatcher(None, word_upper, publisher).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = publisher

            # Check against publisher imprints
            for imprint in self.parser.publisher_imprints.keys():
                ratio = SequenceMatcher(None, word_upper, imprint).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = imprint

            # Use best match if found, otherwise keep original
            if best_match:
                corrected_words.append(best_match.title())  # Title case for readability
            else:
                corrected_words.append(word)

        return ' '.join(corrected_words)

    def _load_loading_area(self):
        """Load loading area coordinates"""
        config_file = 'test_images/loading_area.txt'
        if not os.path.exists(config_file):
            return None

        with open(config_file, 'r') as f:
            coords = f.readline().strip()
            return tuple(map(int, coords.split(',')))

    def capture_and_crop(self):
        """Capture FRESH frame and crop to loading area"""
        # Wait for camera stabilization
        time.sleep(0.5)

        # Flush RTSP buffer (30 frames = 1 second at 30fps)
        for _ in range(30):
            ret, frame = self.cap.read()
            if not ret:
                return None, None
            time.sleep(0.01)

        # Get fresh frame
        ret, frame = self.cap.read()
        if not ret:
            return None, None

        # Crop to loading area
        x1, y1, x2, y2 = self.loading_area
        cropped = frame[y1:y2, x1:x2]

        return frame, cropped

    def run_ocr(self, image, timestamp=None):
        """Run OCR with preprocessing and postprocessing"""
        # Preprocess
        if self.preprocessing:
            print(f"   └─ Preprocessing image...", end='', flush=True)
            if self.model == 'tesseract':
                preprocessed = self.preprocessor.preprocess_for_tesseract(image)
            elif self.model == 'ppocr':
                preprocessed = self.preprocessor.preprocess_for_ppocr(image)
            else:  # easyocr
                preprocessed = self.preprocessor.preprocess_for_easyocr(image)

            temp_path = 'temp_ocr_input.jpg'
            cv2.imwrite(temp_path, preprocessed)

            # Save debug image if debug mode (overwrite same file each time)
            if self.debug:
                debug_path = 'test_images/debug_preprocessed_last.jpg'
                cv2.imwrite(debug_path, preprocessed)
                print(f" ✅ (debug: {debug_path})")
            else:
                print(" ✅")
        else:
            temp_path = 'temp_ocr_input.jpg'
            cv2.imwrite(temp_path, image)

        # Run OCR
        print(f"   └─ Text detection & recognition...", end='', flush=True)

        if self.model == 'tesseract':
            text_boxes = run_ocr_tesseract(temp_path)
        elif self.model == 'ppocr':
            text_boxes = run_ocr_ppocr(temp_path)
        else:  # easyocr
            text_boxes = run_ocr_easyocr(temp_path)

        print(" ✅")

        # Apply word corrections AND fuzzy matching before parsing
        # This ensures parser sees corrected text (OLIMPO not OLMRQ)
        corrected_text_boxes = []
        for box in text_boxes:
            # First apply exact word corrections
            corrected_text = self.postprocessor._correct_words(box.text)

            # Then apply fuzzy matching with databases
            corrected_text = self._fuzzy_correct_with_databases(corrected_text)

            # Create new TextBox with corrected text
            from collections import namedtuple
            CorrectedBox = namedtuple('TextBox', ['text', 'confidence', 'bbox'])
            corrected_box = CorrectedBox(corrected_text, box.confidence, box.bbox)
            corrected_text_boxes.append(corrected_box)

        # Parse
        print(f"🧠 [4/5] Parsing book information...", end='', flush=True)
        img_h, img_w = image.shape[:2]
        book_info = self.parser.parse(corrected_text_boxes, img_h, img_w)

        # Convert to dict for postprocessing
        book_dict = {
            'title': book_info.title or '[not identified]',
            'author': book_info.author or '[not identified]',
            'publisher': book_info.publisher or '[not identified]',
            'confidence': book_info.confidence,
            'raw_text': '\n'.join([f"{b.text}" for b in text_boxes])
        }
        print(" ✅")

        # Post-processing
        improved = self.postprocessor.improve_result(book_dict)

        return improved

    def display_result(self, book_info, show_raw=True):
        """Display OCR result"""
        print("\n" + "="*70)
        print(f"   📚 BOOK #{self.book_count}")
        print("="*70)
        print(f"Title:      {book_info['title']}")
        print(f"Author:     {book_info['author']}")
        print(f"Publisher:  {book_info['publisher']}")
        print(f"Confidence: {book_info['confidence']:.2f}")
        print("="*70)

        if show_raw and 'raw_text' in book_info:
            print("\n📝 All detected text blocks:")
            print("-" * 70)
            raw_lines = book_info['raw_text'].split('\n') if book_info['raw_text'] else []
            for i, line in enumerate(raw_lines[:10], 1):
                if line.strip():
                    print(f"  {i}. {line.strip()}")
            if len(raw_lines) > 10:
                print(f"  ... and {len(raw_lines) - 10} more")
            print("-" * 70)

    def show_stats(self):
        """Show session statistics"""
        elapsed = (datetime.now() - self.session_start).total_seconds()

        print("\n" + "="*70)
        print("   📊 SESSION STATISTICS")
        print("="*70)
        print(f"Books processed: {self.book_count}")
        print(f"Session time:    {elapsed:.0f}s ({elapsed/60:.1f}min)")
        if self.book_count > 0:
            print(f"Avg time/book:   {elapsed/self.book_count:.1f}s")
            print(f"Throughput:      {self.book_count/(elapsed/60):.1f} books/min")
        print("="*70)

    def run(self):
        """Main continuous loop"""
        print("="*70)
        print("   📚 CONTINUOUS BOOK SCANNER")
        print("="*70)
        print(f"Model:         {self.model}")
        print(f"Preprocessing: {'Enabled' if self.preprocessing else 'Disabled'}")
        print(f"Debug mode:    {'Enabled' if self.debug else 'Disabled'}")
        print(f"Auto mode:     {'Yes' if self.auto_mode else 'No (manual)'}")
        print(f"Loading area:  {self.loading_area[2]-self.loading_area[0]}x{self.loading_area[3]-self.loading_area[1]}px")
        print("="*70)
        print()

        if not self.auto_mode:
            print("📖 INSTRUCTIONS:")
            print("   1. Position book in loading area")
            print("   2. Press ENTER to scan")
            print("   3. Remove book and repeat")
            print("   4. Type 'q' + ENTER to quit")
            print()

        try:
            while True:
                if not self.auto_mode:
                    user_input = input(f"\n[Book #{self.book_count + 1}] Press ENTER to scan (or 'q' to quit, 's' for stats): ").strip().lower()

                    if user_input == 'q':
                        break
                    elif user_input == 's':
                        self.show_stats()
                        continue

                # Capture
                print("\n📷 [1/5] Flushing camera buffer...", end='', flush=True)
                full_frame, cropped = self.capture_and_crop()

                if cropped is None:
                    print(" ❌ Failed")
                    continue

                print(" ✅")
                print(f"📐 [2/5] Cropping to {cropped.shape[1]}x{cropped.shape[0]}px...", end='', flush=True)

                # Save capture
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                os.makedirs('test_images', exist_ok=True)
                capture_path = f"test_images/book_{timestamp}.jpg"
                cv2.imwrite(capture_path, cropped)
                print(" ✅")

                # OCR
                print(f"🔍 [3/5] Running OCR ({self.model})...")
                book_info = self.run_ocr(cropped, timestamp)
                print("✅ [5/5] OCR completed")

                # Display
                self.book_count += 1
                self.display_result(book_info)

                # Save to log
                self._log_result(timestamp, book_info)

                # Auto mode delay
                if self.auto_mode:
                    print("\nWaiting 3 seconds... (Ctrl+C to stop)")
                    time.sleep(3)

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user")

        finally:
            self.cap.release()
            self.show_stats()
            print("\n✅ Session ended")

    def _log_result(self, timestamp, book_info):
        """Log result to CSV file"""
        log_file = 'ocr_results.csv'

        # Create header if needed
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write("timestamp,title,author,publisher,confidence\n")

        # Append result
        with open(log_file, 'a') as f:
            title = book_info['title'].replace(',', ';')
            author = book_info['author'].replace(',', ';')
            publisher = book_info['publisher'].replace(',', ';')
            confidence = book_info['confidence']

            f.write(f"{timestamp},{title},{author},{publisher},{confidence:.2f}\n")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Continuous book scanning with OCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scan_books.py                    # Manual mode with EasyOCR
  python3 scan_books.py --auto             # Auto mode (3s delay)
  python3 scan_books.py --model tesseract  # Use Tesseract
  python3 scan_books.py --model ppocr      # Use PP-OCR
  python3 scan_books.py --no-preprocessing # Skip preprocessing
        """
    )
    parser.add_argument(
        '--model',
        choices=['tesseract', 'ppocr', 'easyocr'],
        default='easyocr',
        help="OCR model (default: easyocr)"
    )
    parser.add_argument(
        '--auto',
        action='store_true',
        help="Auto mode (3s delay between scans)"
    )
    parser.add_argument(
        '--no-preprocessing',
        action='store_true',
        help="Disable preprocessing"
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help="Enable debug mode (save intermediate images)"
    )

    args = parser.parse_args()

    scanner = ContinuousScanner(
        model=args.model,
        auto_mode=args.auto,
        preprocessing=not args.no_preprocessing,
        debug=args.debug
    )

    scanner.run()


if __name__ == "__main__":
    main()
