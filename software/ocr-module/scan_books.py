#!/usr/bin/env python3
"""
Continuous book scanning with OCR.
Processes one book after another with automatic preprocessing and postprocessing.

Usage:
    python3 scan_books.py                    # Manual mode, default hybrid
    python3 scan_books.py --auto             # Auto mode (3s delay between scans)
    python3 scan_books.py --model cpu        # CPU-only (faster, ~6s/book)
    python3 scan_books.py --no-preprocessing # Skip preprocessing
    python3 scan_books.py --no-color-filters # Skip color filter passes (faster)

OCR Models:
    - cpu: CPU-only PP-OCR, multi-pass upscale+raw (~6s/book)
    - metis: Metis accelerator detection + CPU recognition (~4s/book)
    - hybrid: Ensemble CPU+Metis, merge best results (~8s/book) [DEFAULT]

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
import multiprocessing as mp
import numpy as np
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from difflib import SequenceMatcher
from spellchecker import SpellChecker

# Local book database for title validation
try:
    from setup_database import BookDatabase
    BOOK_DB_AVAILABLE = True
except ImportError:
    BOOK_DB_AVAILABLE = False

from config import RTSPConfig


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

    def preprocess_for_ppocr(self, image):
        """Preprocess for PP-OCR (keeps color - PP-OCR expects RGB input)"""
        # Light color denoising
        denoised = cv2.fastNlMeansDenoisingColored(image, h=5, hColor=5)

        # Conservative sharpening
        kernel = np.array([[0, -0.5, 0], [-0.5, 3, -0.5], [0, -0.5, 0]])
        sharpened = cv2.filter2D(denoised, -1, kernel)

        return sharpened

    def preprocess_for_ppocr_upscale(self, image, scale=2.0):
        """Upscale + light denoise for PP-OCR - captures small text better"""
        h, w = image.shape[:2]
        upscaled = cv2.resize(image, (int(w * scale), int(h * scale)),
                              interpolation=cv2.INTER_CUBIC)
        denoised = cv2.fastNlMeansDenoisingColored(upscaled, h=3, hColor=3)
        return denoised

    @staticmethod
    def generate_color_filters(image):
        """
        Generate color-filtered variants to help OCR see through artistic covers.
        Returns list of (label, 3-channel BGR image) tuples.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Single channels (OpenCV BGR order)
        blue, green, red = image[:, :, 0], image[:, :, 1], image[:, :, 2]

        def to_bgr(ch):
            return cv2.cvtColor(ch, cv2.COLOR_GRAY2BGR)

        return [
            ('grayscale',  to_bgr(gray)),
            ('inverted',   to_bgr(255 - gray)),
            ('red',        to_bgr(red)),
            ('green',      to_bgr(green)),
            ('blue',       to_bgr(blue)),
            ('red_inv',    to_bgr(255 - red)),
            ('green_inv',  to_bgr(255 - green)),
            ('blue_inv',   to_bgr(255 - blue)),
        ]



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

    # OCR digit-to-letter mapping for cleaning
    OCR_DIGIT_MAP = {'0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '8': 'b'}

    # WORD_CORRECTIONS removed - using spell checking instead
    WORD_CORRECTIONS = {}

    def __init__(self, debug=False):
        self.debug = debug
        # Initialize spell checker for OCR correction
        try:
            self.spell = SpellChecker(language='en')
            self.spell.word_frequency.load_words([
                'harrow', 'riordan', 'tolkien', 'rowling', 'gaiman',
                'sanderson', 'pratchett', 'erikson', 'hobb', 'weeks',
                'alix', 'rick', 'neil', 'brandon', 'terry', 'steven',
                'january', 'february', 'thousand', 'doors', 'beautiful',
                'unbearably', 'olimpo', 'eroi', 'mondadori', 'penguin', 'harper'
            ])
        except Exception as e:
            print(f"Warning: SpellChecker init failed: {e}")
            self.spell = None

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
        """Apply word-level corrections using spell checking"""
        words = text.split()
        corrected_words = []

        for word in words:
            word_upper = word.upper()

            # Check word corrections dict first
            if word_upper in self.WORD_CORRECTIONS:
                replacement = self.WORD_CORRECTIONS[word_upper]
                if replacement:
                    corrected_words.append(replacement)
                continue

            # Try spell checking for words with OCR artifacts
            if self.spell and len(word) >= 4:
                corrected_word = self._spell_correct_ocr(word)
                if corrected_word != word:
                    corrected_words.append(corrected_word)
                    continue

            corrected_words.append(word)

        return ' '.join(corrected_words)

    def _spell_correct_ocr(self, word):
        """Use spell checking to fix OCR errors"""
        if not self.spell:
            return word

        # Skip likely proper names (short capitalized words without digits)
        if len(word) <= 5 and word[0].isupper() and word.isalpha():
            if not any(c.isdigit() for c in word):
                return word

        # Clean OCR artifacts (digits that look like letters)
        cleaned = word
        was_cleaned = False
        for digit, letter in self.OCR_DIGIT_MAP.items():
            if digit in cleaned:
                cleaned = cleaned.replace(digit, letter)
                was_cleaned = True

        # Check if cleaned word is mostly letters
        alpha_ratio = sum(c.isalpha() for c in cleaned) / len(cleaned) if cleaned else 0
        if alpha_ratio < 0.8:
            return word

        clean_lower = cleaned.lower()

        # If cleaned and valid, use it
        if was_cleaned and clean_lower in self.spell:
            if word.isupper():
                result = clean_lower.upper()
            elif word[0].isupper():
                result = clean_lower.capitalize()
            else:
                result = clean_lower
            if self.debug:
                print(f"    OCR clean: {word} -> {result}")
            return result

        # Try spell correction for unknown words
        if clean_lower not in self.spell:
            correction = self.spell.correction(clean_lower)
            if correction and correction != clean_lower:
                # Be conservative with short words
                if len(word) <= 5:
                    common = sum(a == b for a, b in zip(clean_lower, correction))
                    if common < len(clean_lower) - 1:
                        return word

                if word.isupper():
                    result = correction.upper()
                elif word[0].isupper():
                    result = correction.capitalize()
                else:
                    result = correction
                if self.debug:
                    print(f"    Spell: {word} -> {result}")
                return result

        return word

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

    def __init__(self, debug=False):
        self.debug = debug

        # Initialize book database (used for SQL queries, NOT loaded into memory)
        self.book_db = None
        if BOOK_DB_AVAILABLE:
            try:
                # Look in config/ first, then fall back to ocr-module/
                _module_dir = os.path.dirname(os.path.abspath(__file__))
                db_path = os.path.join(_module_dir, '..', 'config', 'books.db')
                if not os.path.exists(db_path):
                    db_path = os.path.join(_module_dir, 'books.db')
                if os.path.exists(db_path):
                    self.book_db = BookDatabase(db_path)
                    if self.debug:
                        print(f"Book DB connected (SQL mode)")
            except Exception as e:
                if self.debug:
                    print(f"Book DB not available: {e}")

        # Only load imprints (small table, 22 records)
        # Authors/publishers use SQL queries instead of loading into memory
        self.known_authors = set()  # Empty - use SQL queries
        self.known_publishers = set()  # Empty - use SQL queries
        self.publisher_imprints = self._load_imprints_mapping()
        self._author_cache = {}  # Cache for _matches_author_database results
        self._publisher_cache = {}  # Cache for is_known_publisher results

        if self.debug:
            print(f"Loaded: {len(self.publisher_imprints)} imprints (authors/publishers via SQL)")

    def _load_authors_database(self):
        """
        Load known authors - now returns empty set.
        Authors are queried via SQL when needed (memory efficient).
        """
        # Do NOT load all authors into memory (17M+ records)
        # Use self.book_db.is_known_author() or fuzzy_match_author_sql() instead
        return set()

    def _load_publishers_database(self):
        """
        Load known publishers - now returns empty set.
        Publishers are queried via SQL when needed (memory efficient).
        """
        # Do NOT load all publishers into memory (5M+ records)
        # Use self.book_db.is_known_publisher() or fuzzy_match_publisher_sql() instead
        return set()

    def _load_imprints_mapping(self):
        """Load imprint to publisher mapping from database"""
        if self.book_db:
            return self.book_db.get_all_imprints()
        # Fallback to txt file if database not available
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

    def _detect_imprint_pre_merge(self, text_boxes: List[TextBox], image_height: int) -> Tuple[Optional[str], List[TextBox]]:
        """
        Detect imprint/publisher in raw text boxes BEFORE merging.
        This prevents imprints from being merged with title/author text.
        Returns (imprint_text, remaining_boxes) or (None, original_boxes).
        """
        indexed = list(enumerate(text_boxes))
        indexed.sort(key=lambda x: x[1].bbox[1])  # sort by Y

        # Strategy 1: single box is an exact imprint
        for idx, box in indexed:
            text_upper = box.text.strip().upper()
            if text_upper in self.publisher_imprints:
                remaining = [b for i, b in enumerate(text_boxes) if i != idx]
                return text_upper, remaining

        # Strategy 2: two adjacent boxes on same line combine to an imprint
        for i in range(len(indexed) - 1):
            idx1, box1 = indexed[i]
            idx2, box2 = indexed[i + 1]
            h1 = box1.bbox[3] - box1.bbox[1]
            h2 = box2.bbox[3] - box2.bbox[1]
            avg_h = (h1 + h2) / 2
            if abs(box1.bbox[1] - box2.bbox[1]) < avg_h * 0.5:
                left, right = (box1, box2) if box1.bbox[0] < box2.bbox[0] else (box2, box1)
                combined = f"{left.text.strip().upper()} {right.text.strip().upper()}"
                if combined in self.publisher_imprints:
                    remove = {idx1, idx2}
                    remaining = [b for i, b in enumerate(text_boxes) if i not in remove]
                    return combined, remaining

        # Strategy 3: a single word inside a box is an imprint
        for idx, box in indexed:
            words = box.text.strip().split()
            for word in words:
                if word.upper() in self.publisher_imprints:
                    # Remove only the imprint word, keep the rest in the box
                    rest_words = [w for w in words if w.upper() != word.upper()]
                    new_boxes = list(text_boxes)
                    if rest_words:
                        new_boxes[idx] = TextBox(" ".join(rest_words), box.bbox, box.confidence)
                    else:
                        new_boxes.pop(idx)
                    return word.upper(), new_boxes

        return None, text_boxes

    def parse(self, text_boxes: List[TextBox], image_height: int, image_width: int, image=None) -> BookInfo:
        """Parse book cover from detected text boxes"""
        if not text_boxes:
            return BookInfo()

        # Clear caches for each new book
        self._author_cache = {}
        self._publisher_cache = {}

        book = BookInfo(raw_texts=text_boxes)

        # Pre-scan: detect imprint in raw text boxes BEFORE merging
        # This prevents "OSCAR BESTSELLERS" from being merged with title text
        imprint_text, remaining_boxes = self._detect_imprint_pre_merge(text_boxes, image_height)
        if imprint_text:
            book.publisher = self._resolve_imprint_to_publisher(imprint_text)

        # Merge remaining boxes (imprint boxes already removed)
        merged = self._merge_nearby_boxes(remaining_boxes, image_height)

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

        # Find publisher (only if not already found by pre-scan)
        if not book.publisher:
            for item in scored:
                if item['text'] in used_texts or item['is_quote']:
                    continue
                if self._is_likely_publisher(item['text'], item['position_y_ratio']):
                    book.publisher = item['text']
                    used_texts.add(item['text'])
                    break

        # Mark imprint-related texts as used (e.g. "BESTSELLERS" adjacent to found publisher)
        if book.publisher:
            pub_upper = book.publisher.upper()
            for item in scored:
                if item['text'] in used_texts:
                    continue
                text_upper = item['text'].upper()
                # Mark if combining with publisher forms a known imprint
                combined = f"{pub_upper} {text_upper}"
                combined2 = f"{text_upper} {pub_upper}"
                if combined in self.publisher_imprints or combined2 in self.publisher_imprints:
                    used_texts.add(item['text'])
                # Also mark individual imprint words (e.g. "Bestsellers" alone)
                elif text_upper in self.publisher_imprints:
                    used_texts.add(item['text'])

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
                # Fallback: prefer DB-matched authors over heuristic-only
                author_candidates.sort(key=lambda x: (
                    self._matches_author_database(x['text'].upper()),
                    x['position_y_ratio'] > 0.6,
                    x['prominence']
                ), reverse=True)
                book.author = author_candidates[0]['text']
                used_texts.add(book.author)

        # Find title using vertical proximity grouping.
        # Step 1: collect core title candidates (multi-word, in title zone)
        title_candidates = []
        for item in scored:
            if item['text'] in used_texts or item['is_quote']:
                continue
            if item['text'].upper() in self.publisher_imprints:
                continue
            if self._is_likely_title(item['text'], item['position_y_ratio']):
                title_candidates.append(item)

        # Step 2: also consider single-word blocks (even small/lowercase)
        # that are in the extended title zone. Proximity grouping decides membership.
        for item in scored:
            if item['text'] in used_texts or item['is_quote']:
                continue
            if item in title_candidates:
                continue
            if item['text'].upper() in self.publisher_imprints:
                continue
            words = item['text'].split()
            if len(words) == 1 and 0.1 < item['position_y_ratio'] < 0.75:
                word = words[0]
                if len(word) >= 2 and any(c.isalpha() for c in word):
                    title_candidates.append(item)

        # Step 3: group by vertical proximity + color, pick best cluster
        if title_candidates:
            title_group = self._group_title_blocks(title_candidates, image_height, image)

            # Step 4: extend title group with adjacent blocks that were
            # already claimed (e.g. publisher grabbed "JANUARY" from title).
            # If a claimed block is vertically close + color-similar to the
            # group edges, reclaim it as title.
            title_group = self._extend_title_group(title_group, scored, used_texts, image_height, image)

            book.title = " ".join(item['text'] for item in title_group)
            book.confidence = sum(item['prominence'] for item in title_group) / len(title_group) / 10

            for item in title_group:
                used_texts.add(item['text'])
                # If this was the publisher, clear it (will re-detect later)
                if book.publisher and item['text'] == book.publisher:
                    book.publisher = ""

        # Fallback: use most prominent unused text
        if not book.title:
            for item in scored:
                if item['text'] not in used_texts and not item['is_quote']:
                    book.title = item['text']
                    book.confidence = item['prominence'] / 10
                    break

        # Re-detect publisher if it was reclaimed by title
        if not book.publisher:
            for item in scored:
                if item['text'] in used_texts or item['is_quote']:
                    continue
                if self._is_likely_publisher(item['text'], item['position_y_ratio']):
                    book.publisher = item['text']
                    used_texts.add(item['text'])
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

    @staticmethod
    def _mean_color_at_bbox(image, bbox):
        """Get mean BGR color of the text region in the original image"""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        h, w = image.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return np.array([128, 128, 128], dtype=float)
        roi = image[y1:y2, x1:x2]
        return roi.mean(axis=(0, 1))

    def _group_title_blocks(self, candidates: list, img_height: int, image=None) -> list:
        """
        Group title candidates by vertical proximity and (optionally) color similarity.
        Returns the best cluster sorted by Y position.

        Criteria for same group:
        - Vertical gap between consecutive lines <= 1.5x the average line height
        - If image is available: mean text color distance < threshold
        """
        if len(candidates) <= 1:
            return candidates

        # Sort by vertical position
        candidates = sorted(candidates, key=lambda x: x['position_y'])

        # Extract color info if image available
        colors = {}
        if image is not None:
            for item in candidates:
                colors[id(item)] = self._mean_color_at_bbox(image, item['box'].bbox)

        # Build adjacency: consecutive blocks that are vertically close + color-similar
        groups = [[candidates[0]]]
        for item in candidates[1:]:
            prev = groups[-1][-1]
            prev_box = prev['box']
            curr_box = item['box']

            # Vertical gap: distance from bottom of previous to top of current
            prev_bottom = prev_box.bbox[3]
            curr_top = curr_box.bbox[1]
            gap = curr_top - prev_bottom

            # Average line height of the two blocks
            prev_h = prev_box.bbox[3] - prev_box.bbox[1]
            curr_h = curr_box.bbox[3] - curr_box.bbox[1]
            avg_h = (prev_h + curr_h) / 2

            # Close vertically: gap < 1.5x avg line height (allow some spacing)
            # Also allow overlapping lines (gap < 0)
            vertically_close = gap < avg_h * 1.5

            # Color similarity check (if image available)
            color_similar = True
            if image is not None and id(prev) in colors and id(item) in colors:
                dist = np.linalg.norm(colors[id(prev)] - colors[id(item)])
                # Threshold: ~60 in BGR space (fairly permissive)
                color_similar = dist < 60

            if vertically_close and color_similar:
                groups[-1].append(item)
            else:
                groups.append([item])

        # Pick the best group: highest total prominence
        best_group = max(groups, key=lambda g: sum(item['prominence'] for item in g))

        if self.debug:
            print(f"\n  Title grouping: {len(groups)} group(s), best has {len(best_group)} block(s)")
            for item in best_group:
                color_info = ""
                if id(item) in colors:
                    c = colors[id(item)]
                    color_info = f" color=({c[2]:.0f},{c[1]:.0f},{c[0]:.0f})"
                print(f"    [{item['position_y_ratio']:.2f}] \"{item['text']}\"{color_info}")

        return best_group

    def _extend_title_group(self, title_group: list, all_scored: list,
                            used_texts: set, img_height: int, image=None) -> list:
        """
        Extend title group by pulling in adjacent blocks that are vertically
        close and color-similar, even if already claimed (e.g. as publisher).
        Searches above and below the current group edges.
        """
        if not title_group:
            return title_group

        group = list(title_group)
        changed = True
        while changed:
            changed = False
            top_item = min(group, key=lambda x: x['position_y'])
            bot_item = max(group, key=lambda x: x['position_y'])
            top_box = top_item['box']
            bot_box = bot_item['box']
            avg_h = sum(it['box'].bbox[3] - it['box'].bbox[1] for it in group) / len(group)

            for item in all_scored:
                if item in group or item['is_quote']:
                    continue
                # Skip known imprints (OSCAR, BUR, etc.)
                if item['text'].upper() in self.publisher_imprints:
                    continue
                curr_box = item['box']

                # Check adjacency above the group top
                gap_above = top_box.bbox[1] - curr_box.bbox[3]
                # Check adjacency below the group bottom
                gap_below = curr_box.bbox[1] - bot_box.bbox[3]

                vertically_adjacent = (0 <= gap_above < avg_h * 1.5) or \
                                      (0 <= gap_below < avg_h * 1.5) or \
                                      (-avg_h * 0.3 < gap_above < 0) or \
                                      (-avg_h * 0.3 < gap_below < 0)

                if not vertically_adjacent:
                    continue

                # Color similarity with nearest edge
                color_ok = True
                if image is not None:
                    neighbor = top_item if gap_above >= 0 else bot_item
                    c1 = self._mean_color_at_bbox(image, neighbor['box'].bbox)
                    c2 = self._mean_color_at_bbox(image, curr_box.bbox)
                    color_ok = np.linalg.norm(c1 - c2) < 60

                if color_ok:
                    group.append(item)
                    changed = True
                    if self.debug:
                        print(f"    + extended title: \"{item['text']}\" (gap_above={gap_above:.0f} gap_below={gap_below:.0f})")

        # Re-sort by vertical position
        group.sort(key=lambda x: x['position_y'])
        return group

    def _is_likely_author(self, text: str, position_y_ratio: float) -> bool:
        """Check if text is likely an author name"""
        if self._is_quote_or_review(text):
            return False

        text_clean = text.strip().upper()

        # Filter out texts with no alphabetic characters (e.g. "1", "42")
        if not any(c.isalpha() for c in text_clean):
            return False

        # Cheap filters first (before any DB query)
        if len(text_clean) < 3 or len(text_clean) > 40:
            return False

        if re.search(r'\d', text_clean):
            return False

        words = text_clean.split()

        # Author names are 1-4 words (allow single surname for DB match)
        if len(words) > 4:
            return False

        # Each word ≥3 chars (blocks "DO RS")
        if len(words) >= 2 and any(len(w) < 3 for w in words):
            return False

        # DB check for texts that look like names (2-4 words, all capitalized)
        if 2 <= len(words) <= 4:
            if self._matches_author_database(text_clean):
                return True

        # Heuristics for texts not in database
        if len(text_clean) < 6:
            return False

        if not (2 <= len(words) <= 4):
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
        """Check if text matches known authors database (via SQL query, cached)"""
        if not self.book_db:
            return False

        text_clean = text.strip()
        if not text_clean:
            return False

        # Filter out very short texts (numbers, single chars, etc.)
        if len(text_clean) < 3:
            return False

        # Check cache first
        cache_key = text_clean.upper()
        if cache_key in self._author_cache:
            return self._author_cache[cache_key]

        result = False

        # Check exact match via SQL
        if self.book_db.is_known_author(text_clean):
            result = True
        else:
            # Check if any word in text is a known author surname
            words = text_clean.split()
            for word in words:
                if len(word) > 2 and self.book_db.is_known_author(word):
                    result = True
                    break

            # Fuzzy match via SQL (only if no exact match found)
            if not result:
                match = self.book_db.fuzzy_match_author_sql(text_clean, threshold=0.85)
                if match:
                    result = True

        self._author_cache[cache_key] = result
        return result

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

                    if (self._matches_author_database(text_upper) or
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

        # Check in database via SQL
        if self._matches_author_database(text):
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

        # Check imprints mapping - exact match
        if text_upper in self.publisher_imprints:
            return True

        # Check imprints - word-level match (for merged blocks)
        words = text_upper.split()
        for word in words:
            if word in self.publisher_imprints:
                return True
        for i in range(len(words) - 1):
            pair = f"{words[i]} {words[i+1]}"
            if pair in self.publisher_imprints:
                return True

        # Check database via SQL query (cached)
        # But if text is also a known author, don't classify as publisher
        # (many authors are also in publishers table as self-published)
        if self.book_db:
            if text_upper not in self._publisher_cache:
                self._publisher_cache[text_upper] = self.book_db.is_known_publisher(text_upper)
            if self._publisher_cache[text_upper]:
                if not self._matches_author_database(text_upper):
                    return True

        # Pattern matching (PENGUIN, BOOKS, PRESS, etc.)
        for pattern in self.PUBLISHER_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        # Position-based heuristic (bottom of cover)
        # Conservative: require DB match or pattern match, not just position
        if position_y_ratio > 0.85:
            if len(text) < 30 and len(text.split()) <= 3:
                # Never classify known authors as publishers
                if self.book_db and self._matches_author_database(text_upper):
                    return False
                # Require additional evidence beyond just position
                if self.book_db and self.book_db.is_known_publisher(text_upper):
                    return True

        return False


# ============================================================================
# OCR EXECUTION
# ============================================================================

_ppocr_instance = None

# Persistent worker script for subprocess-isolated PaddleOCR calls.
# Loads models ONCE, then processes images in a loop via stdin/stdout.
_PPOCR_WORKER_SCRIPT = r"""
import json, os, sys, signal, warnings
os.setpgrp()
signal.signal(signal.SIGINT, signal.SIG_IGN)
warnings.filterwarnings('ignore', category=UserWarning)
os.environ.setdefault('ORT_LOG_LEVEL', '3')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
from paddleocr import PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='latin', use_gpu=False, show_log=False)
# Signal parent that we are ready
print("READY", flush=True)
# Process images in a loop: one path per line on stdin, JSON result on stdout
for line in sys.stdin:
    image_path = line.strip()
    if not image_path:
        continue
    try:
        result = ocr.ocr(image_path, cls=True)
        out = []
        if result and result[0]:
            for r in result[0]:
                bbox = r[0]
                text = r[1][0]
                conf = float(r[1][1])
                out.append({'bbox': bbox, 'text': text, 'conf': conf})
        print(json.dumps(out), flush=True)
    except Exception as e:
        print(json.dumps({"error": str(e)}), flush=True)
"""

_ppocr_worker_proc = None


def _ensure_ppocr_worker():
    """Start or restart the persistent PaddleOCR worker subprocess."""
    global _ppocr_worker_proc

    # Check if existing worker is still alive
    if _ppocr_worker_proc is not None:
        if _ppocr_worker_proc.poll() is None:
            return _ppocr_worker_proc
        # Worker died, clean up
        _ppocr_worker_proc = None

    # Write worker script to /tmp
    script_path = '/tmp/_ppocr_worker.py'
    with open(script_path, 'w') as f:
        f.write(_PPOCR_WORKER_SCRIPT)

    proc = subprocess.Popen(
        [sys.executable, script_path],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, bufsize=1,
        env={**os.environ, 'ORT_LOG_LEVEL': '3', 'TF_CPP_MIN_LOG_LEVEL': '3'},
    )

    # Wait for READY signal (model loading)
    try:
        ready = proc.stdout.readline().strip()
        if ready != 'READY':
            proc.kill()
            proc.wait()
            raise RuntimeError(f"Worker did not start properly: {ready}")
    except Exception:
        proc.kill()
        proc.wait()
        raise

    _ppocr_worker_proc = proc
    return proc


def _safe_ppocr_ocr(image_path, timeout=60):
    """Run PaddleOCR via a persistent worker subprocess.

    The worker loads PaddlePaddle models once and stays alive across calls.
    If the worker crashes (SIGSEGV), it is automatically restarted on the
    next call. The parent process is fully isolated (no fork, no shared memory).
    """
    import json

    try:
        worker = _ensure_ppocr_worker()
    except Exception as e:
        print(f"\n   ⚠️  PaddleOCR worker failed to start: {e}")
        return None

    try:
        # Send image path
        worker.stdin.write(image_path + '\n')
        worker.stdin.flush()

        # Read result with timeout
        import selectors
        sel = selectors.DefaultSelector()
        sel.register(worker.stdout, selectors.EVENT_READ)
        events = sel.select(timeout=timeout)
        sel.close()

        if not events:
            print(f"\n   ⚠️  PaddleOCR timed out ({timeout}s), restarting worker")
            worker.kill()
            worker.wait()
            global _ppocr_worker_proc
            _ppocr_worker_proc = None
            return None

        line = worker.stdout.readline().strip()
        if not line:
            print(f"\n   ⚠️  PaddleOCR worker returned empty response, restarting")
            worker.kill()
            worker.wait()
            _ppocr_worker_proc = None
            return None

        data = json.loads(line)

        # Check for error response
        if isinstance(data, dict) and 'error' in data:
            print(f"\n   ⚠️  PaddleOCR error: {data['error']}")
            return None

        if not data:
            return None

        # Reconstruct PaddleOCR-compatible format: [[bbox, (text, conf)], ...]
        result = []
        for item in data:
            result.append([item['bbox'], (item['text'], item['conf'])])
        return [result]

    except (BrokenPipeError, OSError):
        print(f"\n   ⚠️  PaddleOCR worker crashed, will restart on next call")
        _ppocr_worker_proc = None
        return None
    except json.JSONDecodeError:
        print(f"\n   ⚠️  PaddleOCR output parse error, skipping")
        return None


def run_ocr_ppocr(image_path):
    """Run PP-OCR on image (singleton initialized by _preload_ocr_models)"""
    global _ppocr_instance

    if _ppocr_instance is None:
        # Fallback: init here if not preloaded (e.g. standalone usage)
        import warnings
        warnings.filterwarnings('ignore', category=UserWarning)
        try:
            from paddleocr import PaddleOCR
        except ImportError:
            print("❌ PaddleOCR not installed. Install with: pip install 'paddleocr>=2.7,<3'")
            sys.exit(1)
        _ppocr_instance = PaddleOCR(use_angle_cls=True, lang='latin', use_gpu=False, show_log=False)
        warnings.resetwarnings()

    results = _safe_ppocr_ocr(image_path)

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
# METIS-ACCELERATED PP-OCR (ENSEMBLE)
# ============================================================================

_metis_context = None
_metis_model_instance = None
_metis_input_info = None
_metis_output_info = None

def _init_metis_det():
    """Initialize Metis accelerator for PP-OCR detection model"""
    global _metis_context, _metis_model_instance, _metis_input_info, _metis_output_info

    if _metis_model_instance is not None:
        return _metis_model_instance

    # Set required environment variables for Axelera runtime
    device_dir = '/opt/axelera/device-1.5.2-1/omega'
    os.environ['AXELERA_DEVICE_DIR'] = device_dir
    os.environ['AIPU_RUNTIME_STAGE0_OMEGA'] = f'{device_dir}/bin/start_axelera_runtime_stage0.bin'
    os.environ['AIPU_FIRMWARE_OMEGA'] = f'{device_dir}/bin/start_axelera_runtime.elf'

    # RISC-V toolchain for kernel compilation
    riscv_path = '/opt/axelera/riscv-gnu-newlib-toolchain-409b951ba662-7/bin'
    if riscv_path not in os.environ.get('PATH', ''):
        os.environ['PATH'] = riscv_path + ':' + os.environ['PATH']

    try:
        from axelera import runtime as axrt

        # Load model
        model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  '..', 'voyager-sdk', 'build', 'ppocr-det', 'ppocr_det', '1')
        model_path = os.path.join(model_dir, 'model.json')

        if not os.path.exists(model_path):
            print(f"   Metis model not found: {model_path}")
            return None

        _metis_context = axrt.Context()
        model = _metis_context.load_model(model_path)
        _metis_input_info = model.inputs()[0]
        _metis_output_info = model.outputs()[0]
        device = _metis_context.device_connect()
        _metis_model_instance = device.load_model_instance(model)

        print("   Metis PP-OCR det model loaded")
        return _metis_model_instance

    except Exception as e:
        print(f"   Metis init failed: {e}")
        return None


def _metis_det_preprocess(image, det_size=640):
    """Preprocess image for Metis PP-OCR detection (quantized int8 NHWC)"""
    h, w = image.shape[:2]

    # Resize keeping aspect ratio
    ratio = min(det_size / h, det_size / w)
    new_h, new_w = int(h * ratio), int(w * ratio)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # Convert BGR to RGB
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

    # Pad to det_size x det_size
    padded = np.zeros((det_size, det_size, 3), dtype=np.float32)
    padded[:new_h, :new_w, :] = rgb.astype(np.float32)

    # Normalize to [-1, 1] (PP-OCRv3 style)
    padded = padded / 255.0
    padded = (padded - 0.5) / 0.5

    # Quantize: int8 = round(float / scale + zero_point)
    # From manifest: quantize_params = [0.007874015718698502, -1]
    scale = 0.007874015718698502
    zero_point = -1
    quantized = np.round(padded / scale + zero_point).clip(-128, 127).astype(np.int8)

    # NHWC layout (already in HWC, add batch dim)
    input_tensor = quantized.reshape(1, det_size, det_size, 3)

    return input_tensor, ratio, h, w


def _metis_det_postprocess(heatmap, orig_h, orig_w, det_size=640, thresh=0.3,
                            min_area=50, unclip_ratio=1.5, box_thresh=0.5):
    """Postprocess Metis detection output to bounding boxes"""
    # Threshold heatmap
    binary = (heatmap > thresh).astype(np.uint8) * 255

    # Light horizontal dilation to connect characters on same line
    dilation_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1))
    dilated = cv2.dilate(binary, dilation_kernel, iterations=1)

    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    ratio = min(det_size / orig_h, det_size / orig_w)

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        x, y, w, h = cv2.boundingRect(contour)

        # Filter by mean heatmap score inside the box
        roi = heatmap[y:y+h, x:x+w]
        if roi.size > 0 and np.mean(roi) < box_thresh:
            continue

        # Scale back to original image coordinates
        x1 = int(x / ratio)
        y1 = int(y / ratio)
        x2 = int((x + w) / ratio)
        y2 = int((y + h) / ratio)

        # Expand proportionally to box height
        expand_x = max(3, int(h * unclip_ratio * 0.3))
        expand_y = max(2, int(h * unclip_ratio * 0.2))

        x1 = max(0, x1 - expand_x)
        y1 = max(0, y1 - expand_y)
        x2 = min(orig_w, x2 + expand_x)
        y2 = min(orig_h, y2 + expand_y)

        boxes.append((x1, y1, x2, y2))

    # Merge overlapping boxes
    boxes = _merge_overlapping_boxes(boxes)

    return boxes


def _merge_overlapping_boxes(boxes):
    """Merge overlapping bounding boxes on the same text line"""
    if not boxes:
        return boxes

    # Sort by y1 then x1
    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    merged = [list(boxes[0])]

    for box in boxes[1:]:
        last = merged[-1]

        # Check if on same line (y-center proximity)
        last_cy = (last[1] + last[3]) / 2
        box_cy = (box[1] + box[3]) / 2
        last_h = last[3] - last[1]
        box_h = box[3] - box[1]
        avg_h = (last_h + box_h) / 2

        # Same line: y-centers within 50% of average height
        if abs(last_cy - box_cy) < avg_h * 0.5:
            # Check horizontal gap (don't merge if too far apart)
            gap = box[0] - last[2]
            if gap < avg_h * 2:  # Max gap = 2x average height
                # Merge
                last[0] = min(last[0], box[0])
                last[1] = min(last[1], box[1])
                last[2] = max(last[2], box[2])
                last[3] = max(last[3], box[3])
                continue

        merged.append(list(box))

    return [tuple(b) for b in merged]


def _run_metis_det_and_rec(image_path):
    """Run Metis detection + PaddleOCR recognition on detected regions"""
    model_inst = _init_metis_det()
    if model_inst is None:
        return None

    # Read image
    image = cv2.imread(image_path)
    if image is None:
        return None

    # Preprocess for Metis
    input_tensor, ratio, orig_h, orig_w = _metis_det_preprocess(image)

    try:
        # Use cached tensor info from _init_metis_det()
        input_info = _metis_input_info
        output_info = _metis_output_info

        # Pad input to match hardware tensor shape (includes padding for alignment)
        padded_shape = input_info.shape
        input_padded = np.zeros(padded_shape, dtype=np.int8)
        # Copy data (3 channels into padded input, respecting spatial padding)
        unpadded = input_info.unpadded_shape
        input_padded[:, :unpadded[1], :unpadded[2], :unpadded[3]] = input_tensor

        # Allocate output
        output_shape = output_info.shape
        output_buf = np.zeros(output_shape, dtype=np.int8)

        # Run inference
        model_inst.run([input_padded], [output_buf])

        # Dequantize output: float = (int8 - zero_point) * scale
        out_scale = output_info.scale
        out_zp = output_info.zero_point

        output_float = (output_buf.astype(np.float32) - out_zp) * out_scale

        # Output is [1, 640, 640, 64] - take first channel as heatmap
        # Remove padding: only first channel is the actual heatmap
        heatmap = output_float[0, :, :, 0]

        # Postprocess to get boxes
        boxes = _metis_det_postprocess(heatmap, orig_h, orig_w)

        if not boxes:
            return []

        # Run PaddleOCR recognition on each detected region
        global _ppocr_instance
        from paddleocr import PaddleOCR
        if _ppocr_instance is None:
            _ppocr_instance = PaddleOCR(use_angle_cls=True, lang='latin', use_gpu=False, show_log=False)

        text_boxes = []
        for (x1, y1, x2, y2) in boxes:
            # Crop region
            crop = image[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            # Save temp crop for PaddleOCR
            temp_crop = '/tmp/metis_crop_temp.jpg'
            cv2.imwrite(temp_crop, crop)

            # Run recognition only (subprocess-safe)
            rec_results = _safe_ppocr_ocr(temp_crop, timeout=30)

            if rec_results and rec_results[0]:
                for line in rec_results[0]:
                    text = line[1][0]
                    conf = line[1][1]
                    text_boxes.append(TextBox(text, (x1, y1, x2, y2), conf))
            else:
                # No text recognized in this crop
                pass

        # Clean up temp file
        try:
            os.remove('/tmp/metis_crop_temp.jpg')
        except Exception:
            pass

        return text_boxes

    except Exception as e:
        print(f"   Metis inference error: {e}")
        import traceback
        traceback.print_exc()
        return None


def _bbox_iou(a, b):
    """Compute intersection-over-union between two bboxes (x1,y1,x2,y2)"""
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter == 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter) if (area_a + area_b - inter) > 0 else 0.0


def _text_quality_score(text):
    """Score text quality: real words score higher than garbled text.
    Returns a 0-1 score based on ratio of alphabetic chars and word length."""
    if not text or not text.strip():
        return 0.0
    words = text.strip().split()
    if not words:
        return 0.0
    # Ratio of alphabetic characters (penalizes random symbols)
    alpha_ratio = sum(1 for c in text if c.isalpha()) / max(len(text), 1)
    # Average word length (very short fragments = lower quality)
    avg_word_len = sum(len(w) for w in words) / len(words)
    word_len_score = min(avg_word_len / 4.0, 1.0)  # 4+ chars avg = full score
    # Longer text is generally better (more complete reading)
    length_score = min(len(text) / 10.0, 1.0)
    return alpha_ratio * 0.4 + word_len_score * 0.3 + length_score * 0.3


def _pick_best_box(candidates):
    """Pick the best box from overlapping candidates.
    Uses a combined score: text quality (60%) + OCR confidence (40%).
    This prevents high-confidence garbled text from winning over
    lower-confidence but correct readings."""
    if len(candidates) == 1:
        return candidates[0]
    best = max(candidates, key=lambda b: (
        _text_quality_score(b.text) * 0.6 + b.confidence * 0.4
    ))
    return best


def _merge_ensemble_results(*box_lists):
    """Merge multiple OCR results with spatial overlap + text quality correlation.

    For overlapping detections (IoU > 0.3), picks the reading with best
    combined score (text quality + confidence) rather than confidence alone.
    This ensures correct readings like 'IL FIGLIO DI NETTUNO' win over
    garbled high-confidence variants."""
    # Flatten all non-empty lists
    all_boxes = []
    for blist in box_lists:
        if blist:
            all_boxes.extend(blist)

    if not all_boxes:
        return []
    if len(all_boxes) == 1:
        return all_boxes

    # Group overlapping boxes using spatial IoU
    # Mark each box as not yet assigned to a cluster
    n = len(all_boxes)
    assigned = [False] * n
    clusters = []

    for i in range(n):
        if assigned[i]:
            continue
        cluster = [all_boxes[i]]
        assigned[i] = True
        for j in range(i + 1, n):
            if assigned[j]:
                continue
            # Check spatial overlap with any box in the cluster
            for cb in cluster:
                iou = _bbox_iou(cb.bbox, all_boxes[j].bbox)
                if iou > 0.3:
                    cluster.append(all_boxes[j])
                    assigned[j] = True
                    break
                # Also check y-center proximity (same line, similar x range)
                cy_a = (cb.bbox[1] + cb.bbox[3]) / 2
                cy_b = (all_boxes[j].bbox[1] + all_boxes[j].bbox[3]) / 2
                h_a = cb.bbox[3] - cb.bbox[1]
                if abs(cy_a - cy_b) < max(h_a * 0.5, 15):
                    # Same line - check x overlap
                    x_overlap = (min(cb.bbox[2], all_boxes[j].bbox[2]) -
                                 max(cb.bbox[0], all_boxes[j].bbox[0]))
                    w_min = min(cb.bbox[2] - cb.bbox[0],
                                all_boxes[j].bbox[2] - all_boxes[j].bbox[0])
                    if w_min > 0 and x_overlap / w_min > 0.3:
                        cluster.append(all_boxes[j])
                        assigned[j] = True
                        break
        clusters.append(cluster)

    # For each cluster, pick the best reading
    result = []
    for cluster in clusters:
        best = _pick_best_box(cluster)
        result.append(best)

    # Sort by y-center for consistent output order
    result.sort(key=lambda b: (b.bbox[1] + b.bbox[3]) / 2)

    return result


def run_ocr_metis(image_path):
    """
    Metis-only: accelerated detection + CPU recognition.
    Falls back to CPU PP-OCR if Metis is unavailable.
    """
    boxes_metis = _run_metis_det_and_rec(image_path)
    if boxes_metis is None:
        print("   (Metis unavailable, using CPU only)")
        return run_ocr_ppocr(image_path)
    return boxes_metis


def run_ocr_ppocr_metis(image_path):
    """
    Ensemble PP-OCR: run both CPU and Metis detection, merge best results.
    CPU provides full PP-OCR pipeline, Metis provides accelerated detection.
    For each text line, the highest-confidence result is selected.
    """
    # Run CPU PP-OCR (full pipeline)
    boxes_cpu = run_ocr_ppocr(image_path)

    # Run Metis detection + CPU recognition
    boxes_metis = _run_metis_det_and_rec(image_path)

    if boxes_metis is None:
        print("   (Metis unavailable, using CPU only)")
        return boxes_cpu

    # Merge: pick best per line
    return _merge_ensemble_results(boxes_cpu, boxes_metis)


# ============================================================================
# CONTINUOUS SCANNER
# ============================================================================

class ContinuousScanner:
    """Continuous book OCR scanner"""

    def __init__(self, model='hybrid', auto_mode=False, preprocessing=True, debug=False, lang=None, color_filters=True):
        self.model = model
        self.auto_mode = auto_mode
        self.preprocessing = preprocessing
        self.debug = debug
        self.lang = lang
        self.color_filters = color_filters
        self.book_count = 0
        self.session_start = datetime.now()

        # Cleanup old temporary files
        self._cleanup_temp_files()
        self._cleanup_on_startup()

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

        # Preload OCR models before user interaction
        self._preload_ocr_models()

        # Open camera
        self.rtsp_url = RTSPConfig.get_url()
        self.cap = cv2.VideoCapture(self.rtsp_url)
        if not self.cap.isOpened():
            print(f"❌ Error: Cannot open camera: {self.rtsp_url}")
            sys.exit(1)

    def _preload_ocr_models(self):
        """Preload OCR models at startup (before user interaction)"""
        if self.model in ('cpu', 'metis', 'hybrid'):
            global _ppocr_instance
            if _ppocr_instance is None:
                import warnings
                warnings.filterwarnings('ignore', category=UserWarning)
                try:
                    from paddleocr import PaddleOCR
                except ImportError:
                    print("❌ PaddleOCR not installed. Install with: pip install 'paddleocr>=2.7,<3'")
                    sys.exit(1)

                model_dir = os.path.expanduser('~/.paddleocr/whl')
                first_download = not os.path.isdir(model_dir) or len(os.listdir(model_dir)) < 3
                if first_download:
                    print("⬇️  Downloading PP-OCR models (Latin, ~150MB)...")
                    _ppocr_instance = PaddleOCR(use_angle_cls=True, lang='latin', use_gpu=False, show_log=True)
                    print("✅ Download complete")
                else:
                    print("⏳ Loading PP-OCR models (Latin)...", end='', flush=True)
                    _ppocr_instance = PaddleOCR(use_angle_cls=True, lang='latin', use_gpu=False, show_log=False)

                # Force full model init with a dummy inference (file path required)
                dummy_path = '/tmp/_ppocr_warmup.jpg'
                cv2.imwrite(dummy_path, np.zeros((64, 200, 3), dtype=np.uint8))
                _ppocr_instance.ocr(dummy_path, cls=True)
                try:
                    os.remove(dummy_path)
                except Exception:
                    pass
                if not first_download:
                    print(" ✅")
                warnings.resetwarnings()

        if self.model in ('metis', 'hybrid'):
            print("⏳ Loading Metis accelerator...", end='', flush=True)
            result = _init_metis_det()
            if result:
                print(" ✅")
            else:
                print(" (unavailable, falling back to CPU)")

    def _cleanup_temp_files(self):
        """Remove temporary files"""
        temp_files = [
            'temp_ocr_input.jpg',
            'test_images/debug_preprocessed_last.jpg',
            '/tmp/scan_preview_temp.jpg',
            '/tmp/metis_crop_temp.jpg',
            '/tmp/ocr_pass_upscale.jpg',
            '/tmp/ocr_pass_raw.jpg',
        ]
        for f in temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    def _cleanup_on_startup(self):
        """
        Clean up old files at application startup.
        Removes:
        - All temporary files
        - Old book images (keeps last 10)
        - Debug images
        - Old log files
        """
        import glob

        print("Cleaning up temporary files...")
        cleaned = 0

        # 1. Remove temp files
        temp_patterns = [
            'temp_*.jpg',
            'debug_*.jpg',
            '*.tmp',
        ]
        for pattern in temp_patterns:
            for f in glob.glob(pattern):
                try:
                    os.remove(f)
                    cleaned += 1
                except Exception:
                    pass

        # 2. Clean old book images (keep last 10)
        book_images = sorted(glob.glob('test_images/book_*.jpg'))
        keep_last = 10
        if len(book_images) > keep_last:
            for f in book_images[:-keep_last]:
                try:
                    os.remove(f)
                    cleaned += 1
                except Exception:
                    pass

        # 3. Clean debug images in test_images
        for f in glob.glob('test_images/debug_*.jpg'):
            try:
                os.remove(f)
                cleaned += 1
            except Exception:
                pass

        if cleaned > 0:
            print(f"  Removed {cleaned} files")
        else:
            print("  No files to remove")

    def _delete_last_capture(self, capture_path):
        """Delete the last captured image after processing"""
        if capture_path and os.path.exists(capture_path):
            try:
                os.remove(capture_path)
            except Exception:
                pass

    def _fuzzy_correct_with_databases(self, text):
        """
        Apply fuzzy matching with databases to automatically correct OCR errors.
        Only queries DB for words with OCR artifacts (digits mixed with letters).
        Clean words are left as-is (the parser does its own DB lookups later).

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

            # Skip if word is a known imprint (exact match)
            if word_upper in self.parser.publisher_imprints:
                corrected_words.append(word)
                continue

            # Only do expensive DB lookups for words with OCR artifacts
            # (digits mixed with letters, e.g. "RIORD4N", "PCRC4")
            has_digits = any(c.isdigit() for c in word)
            has_letters = any(c.isalpha() for c in word)
            has_ocr_artifacts = has_digits and has_letters

            if not has_ocr_artifacts:
                corrected_words.append(word)
                continue

            best_match = None

            # Check fuzzy match with imprints (small in-memory table)
            for imprint in self.parser.publisher_imprints.keys():
                ratio = SequenceMatcher(None, word_upper, imprint).ratio()
                if ratio >= 0.80:
                    best_match = imprint
                    break

            # Try SQL fuzzy match for authors/publishers if no imprint match
            if not best_match and self.parser.book_db:
                # Try author match
                match = self.parser.book_db.fuzzy_match_author_sql(word, threshold=0.80)
                if match:
                    best_match = match.upper()
                else:
                    # Try publisher match
                    match = self.parser.book_db.fuzzy_match_publisher_sql(word, threshold=0.80)
                    if match:
                        best_match = match.upper()

            # Use best match if found, otherwise keep original
            if best_match:
                corrected_words.append(best_match.title())
            else:
                corrected_words.append(word)

        return ' '.join(corrected_words)

    # Italian + English stopwords for filtering OCR raw text
    STOPWORDS = {
        # English
        'the', 'a', 'an', 'of', 'and', 'in', 'on', 'at', 'to', 'for', 'is', 'it',
        'by', 'with', 'from', 'or', 'not', 'but', 'was', 'are', 'be', 'has', 'had',
        'that', 'this', 'his', 'her', 'its', 'all', 'can', 'new', 'one', 'two',
        # Italian
        'il', 'lo', 'la', 'le', 'gli', 'un', 'uno', 'una', 'di', 'da', 'del',
        'dei', 'della', 'delle', 'degli', 'dal', 'dalla', 'dai', 'dalle',
        'nel', 'nella', 'nei', 'nelle', 'sul', 'sulla', 'sui', 'sulle',
        'con', 'per', 'tra', 'fra', 'che', 'non', 'sono', 'come', 'anche',
        'più', 'piu', 'suo', 'sua', 'suoi', 'mio', 'mia',
    }

    def identify_book(self, book_info: dict) -> dict:
        """
        Identify book from OCR results by searching the database.

        Collects ALL raw OCR words, filters stopwords and short words,
        then calls BookDatabase.identify_book() for cascading search.

        Returns: {matched, book, match_confidence, alternatives}
        """
        if not self.parser.book_db:
            return {'matched': False, 'book': None, 'match_confidence': 0.0, 'alternatives': []}

        # Collect raw words from OCR text, excluding publisher/imprint/author words
        raw_text = book_info.get('raw_text', '')
        title = book_info.get('title', '')
        author = book_info.get('author', '')
        publisher = book_info.get('publisher', '')

        # Build set of words to exclude (publisher, imprints, author)
        exclude_words = set(self.STOPWORDS)
        for imprint in self.parser.publisher_imprints:
            for w in imprint.lower().split():
                if len(w) >= 3:
                    exclude_words.add(w)
        if publisher and publisher != '[not identified]':
            for w in publisher.lower().split():
                if len(w) >= 3:
                    exclude_words.add(w)
        # Also exclude common imprint-related words
        exclude_words.update(['bestsellers', 'bestseller', 'edition', 'edizione'])

        raw_words = []
        if raw_text:
            for word in re.split(r'[\s\n]+', raw_text):
                word_clean = re.sub(r'[^\w]', '', word).lower()
                if len(word_clean) >= 3 and word_clean not in exclude_words:
                    raw_words.append(word_clean)

        return self.parser.book_db.identify_book(title, author, publisher, raw_words,
                                                language=self.lang)

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
        # Suppress ffmpeg H.264 decode warnings during flush/read.
        # After grab() flush, the first decoded frames are often corrupt
        # (partial P-frames without keyframe reference) which triggers
        # harmless but noisy ffmpeg warnings on stderr.
        stderr_fd = os.dup(2)
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 2)

        try:
            # Flush RTSP buffer by grabbing (no decode) for 2 seconds.
            # During OCR (3-8s) the buffer accumulates hundreds of frames;
            # grab() is fast (~0.5ms) vs read() (~15ms) so we can drain it quickly.
            flush_duration = 2.0
            flush_start = time.time()
            flushed = 0
            while time.time() - flush_start < flush_duration:
                if not self.cap.grab():
                    # Stream lost, try reconnect
                    self.cap.release()
                    self.cap = cv2.VideoCapture(self.rtsp_url)
                    if not self.cap.isOpened():
                        return None, None
                    break
                flushed += 1

            # Get fresh frame (decode only this one)
            # Retry up to 3 times to skip corrupt frames after flush.
            frame = None
            for _ in range(3):
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    break
            if frame is None:
                return None, None
        finally:
            # Restore stderr
            os.dup2(stderr_fd, 2)
            os.close(stderr_fd)
            os.close(devnull)

        # Crop to loading area
        x1, y1, x2, y2 = self.loading_area
        cropped = frame[y1:y2, x1:x2]

        return frame, cropped

    def _run_ocr_multipass(self, image, ocr_func):
        """
        Multi-pass OCR: different preprocessings capture different text types.
        Pass 1: Upscale 2x + light denoise → small text (publisher, subtitle)
        Pass 2: Raw original image → large artistic text (title)
        Passes 3-10: Color filters on original (disable with --no-color-filters)
        Merge by spatial overlap + text quality correlation.
        """
        all_pass_boxes = []
        temp_files = []
        scale = 2.0
        total_passes = 2 + (8 if self.color_filters else 0)

        # Pass 1: Upscale 2x + denoise
        print(f"   └─ Pass 1/{total_passes}: Upscale {scale:.0f}x + denoise + OCR...", end='', flush=True)
        upscaled = self.preprocessor.preprocess_for_ppocr_upscale(image, scale)
        temp_up = '/tmp/ocr_pass_upscale.jpg'
        cv2.imwrite(temp_up, upscaled)
        temp_files.append(temp_up)
        if self.debug:
            cv2.imwrite('test_images/debug_upscaled_last.jpg', upscaled)
        boxes_upscale = ocr_func(temp_up)
        boxes_upscale = [
            TextBox(b.text,
                    (b.bbox[0]/scale, b.bbox[1]/scale, b.bbox[2]/scale, b.bbox[3]/scale),
                    b.confidence)
            for b in boxes_upscale
        ]
        all_pass_boxes.append(boxes_upscale)
        print(f" done ({len(boxes_upscale)} blocks)")

        # Pass 2: Raw image
        print(f"   └─ Pass 2/{total_passes}: Raw image OCR...", end='', flush=True)
        temp_raw = '/tmp/ocr_pass_raw.jpg'
        cv2.imwrite(temp_raw, image)
        temp_files.append(temp_raw)
        boxes_raw = ocr_func(temp_raw)
        all_pass_boxes.append(boxes_raw)
        print(f" done ({len(boxes_raw)} blocks)")

        # Color filter passes on original image (optional)
        if self.color_filters:
            filters = self.preprocessor.generate_color_filters(image)
            for i, (label, filtered) in enumerate(filters, start=3):
                print(f"   └─ Pass {i}/{total_passes}: {label}...", end='', flush=True)
                temp_f = f'/tmp/ocr_pass_{label}.jpg'
                cv2.imwrite(temp_f, filtered)
                temp_files.append(temp_f)
                if self.debug:
                    cv2.imwrite(f'test_images/debug_filter_{label}.jpg', filtered)
                boxes_f = ocr_func(temp_f)
                all_pass_boxes.append(boxes_f)
                print(f" done ({len(boxes_f)} blocks)")

        # Merge all passes: pick best confidence per text line
        merged = _merge_ensemble_results(*all_pass_boxes)
        total_input = sum(len(b) for b in all_pass_boxes)
        print(f"   └─ Merged: {len(merged)} blocks (from {total_input} total across {len(all_pass_boxes)} passes)")

        # Cleanup temp files
        for f in temp_files:
            try:
                os.remove(f)
            except OSError:
                pass

        return merged

    def run_ocr(self, image, timestamp=None):
        """Run OCR with preprocessing and postprocessing"""
        # Select OCR function
        if self.model == 'cpu':
            ocr_func = run_ocr_ppocr
        elif self.model == 'metis':
            ocr_func = run_ocr_metis
        elif self.model == 'hybrid':
            ocr_func = run_ocr_ppocr_metis
        else:
            raise ValueError(f"Unknown OCR model: {self.model}")

        # Multi-pass OCR with preprocessing (upscale 2x + raw)
        if self.preprocessing:
            text_boxes = self._run_ocr_multipass(image, ocr_func)
        else:
            # No preprocessing: single pass on raw image
            temp_path = 'temp_ocr_input.jpg'
            cv2.imwrite(temp_path, image)

            print(f"   └─ Text detection & recognition...", end='', flush=True)
            text_boxes = ocr_func(temp_path)
            print(" ✅")

        # Apply word corrections AND fuzzy matching before parsing
        # This ensures parser sees corrected text (OLIMPO not OLMRQ)
        print(f"   └─ Fuzzy DB correction ({len(text_boxes)} blocks)...", end='', flush=True)
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

        print(" ✅")

        # Parse
        print(f"🧠 [4/6] Parsing book information...", end='', flush=True)
        img_h, img_w = image.shape[:2]
        book_info = self.parser.parse(corrected_text_boxes, img_h, img_w, image=image)

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

    def display_result(self, book_info, show_raw=True, db_result=None):
        """Display OCR result: best identification on top, debug details below"""
        MIN_DB_CONFIDENCE = 0.60

        # Determine best result to show in the main box
        db_matched = (db_result and db_result.get('matched') and db_result.get('book'))
        db_confident = db_matched and db_result['match_confidence'] >= MIN_DB_CONFIDENCE

        print("\n" + "="*70)
        print(f"   📚 BOOK #{self.book_count}")
        print("="*70)

        if db_confident:
            # Best case: DB match with high confidence
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
                lang_names = {'en': 'English', 'it': 'Italiano', 'fr': 'Français',
                              'es': 'Español', 'de': 'Deutsch'}
                print(f"  Language:   {lang_names.get(book.language, book.language)}")
            print(f"  Match:      {confidence_pct}%")
        else:
            # No DB match or low confidence: show OCR result
            print(f"  Title:      {book_info['title']}")
            print(f"  Author:     {book_info['author']}")
            print(f"  Publisher:  {book_info['publisher']}")
            if db_matched:
                print(f"  Match:      {int(db_result['match_confidence'] * 100)}% (uncertain)")
            else:
                print(f"  Match:      not found in DB")

        print("="*70)

        # Debug section: OCR data, DB search, reasoning
        print(f"\n  Details:")
        print(f"  ├─ OCR read:    {book_info['title']} / {book_info['author']} / {book_info['publisher']}")

        if db_matched:
            book = db_result['book']
            confidence_pct = int(db_result['match_confidence'] * 100)
            if db_confident:
                print(f"  ├─ DB match:    {book.title} - {book.author} ({confidence_pct}%)")
                print(f"  └─ Result:      DB match used (>= {int(MIN_DB_CONFIDENCE*100)}% threshold)")
            else:
                print(f"  ├─ DB candidate: {book.title} - {book.author} ({confidence_pct}%)")
                print(f"  └─ Result:      OCR data used (DB match below {int(MIN_DB_CONFIDENCE*100)}% threshold)")
        else:
            print(f"  ├─ DB match:    none")
            print(f"  └─ Result:      OCR data used (no DB match)")

        # Alternatives
        if db_matched:
            alternatives = db_result.get('alternatives', [])
            if alternatives:
                print(f"\n  Alternatives:")
                for alt_book, alt_score in alternatives:
                    alt_pct = int(alt_score * 100)
                    pub_info = f" ({alt_book.publisher})" if alt_book.publisher else ""
                    print(f"    [{alt_pct}%] {alt_book.title} - {alt_book.author}{pub_info}")

        # Raw OCR text blocks
        if show_raw and 'raw_text' in book_info:
            print(f"\n  Raw OCR blocks:")
            raw_lines = book_info['raw_text'].split('\n') if book_info['raw_text'] else []
            for i, line in enumerate(raw_lines[:10], 1):
                if line.strip():
                    print(f"    {i}. {line.strip()}")
            if len(raw_lines) > 10:
                print(f"    ... and {len(raw_lines) - 10} more")

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
        model_label = 'hybrid (cpu + metis)' if self.model == 'hybrid' else self.model
        print(f"Model:         {model_label}")
        print(f"Preprocessing: {'Enabled' if self.preprocessing else 'Disabled'}")
        lang_display = {'en': 'English', 'it': 'Italian'}.get(self.lang, 'All')
        print(f"DB language:   {lang_display}")
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
                print("\n📷 [1/6] Flushing camera buffer...", end='', flush=True)
                full_frame, cropped = self.capture_and_crop()

                if cropped is None:
                    print(" ❌ Failed")
                    continue

                print(" ✅")
                print(f"📐 [2/6] Cropping to {cropped.shape[1]}x{cropped.shape[0]}px...", end='', flush=True)

                # Save capture
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                os.makedirs('test_images', exist_ok=True)
                capture_path = f"test_images/book_{timestamp}.jpg"
                cv2.imwrite(capture_path, cropped)
                # Note: image will be deleted after OCR processing to save space
                print(" ✅")

                # OCR + DB identification (protected against OCR crashes)
                try:
                    print(f"🔍 [3/6] Running OCR ({self.model})...")
                    book_info = self.run_ocr(cropped, timestamp)
                    print("✅ [5/6] OCR completed")

                    # Database identification
                    print("🔎 [6/6] Searching database...", end='', flush=True)
                    db_result = self.identify_book(book_info)
                    if db_result['matched']:
                        print(" ✅")
                    else:
                        print(" (not found)")

                    # Display
                    self.book_count += 1
                    self.display_result(book_info, db_result=db_result)

                    # Save to log
                    self._log_result(timestamp, book_info, db_result=db_result)
                except Exception as e:
                    print(f"\n⚠️  OCR/identification error: {e}")
                    print("   Skipping this scan, returning to watch mode...")

                # Delete captured image to save space
                self._delete_last_capture(capture_path)

                # Auto mode delay
                if self.auto_mode:
                    print("\nWaiting 3 seconds... (Ctrl+C to stop)")
                    time.sleep(3)

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user")

        finally:
            self.cap.release()
            self._cleanup_temp_files()
            self.show_stats()
            print("\n✅ Session ended")

    def _log_result(self, timestamp, book_info, db_result=None):
        """Log result to CSV file"""
        log_file = 'ocr_results.csv'

        # Create header if needed
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write("timestamp,title,author,publisher,confidence,matched_title,matched_isbn,match_confidence\n")

        # Append result
        with open(log_file, 'a') as f:
            title = book_info['title'].replace(',', ';')
            author = book_info['author'].replace(',', ';')
            publisher = book_info['publisher'].replace(',', ';')
            confidence = book_info['confidence']

            matched_title = ''
            matched_isbn = ''
            match_confidence = ''
            if db_result and db_result.get('matched') and db_result.get('book'):
                matched_title = db_result['book'].title.replace(',', ';')
                matched_isbn = db_result['book'].isbn
                match_confidence = f"{db_result['match_confidence']:.2f}"

            f.write(f"{timestamp},{title},{author},{publisher},{confidence:.2f},{matched_title},{matched_isbn},{match_confidence}\n")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Continuous book scanning with OCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scan_books.py                        # Manual mode with PP-OCR
  python3 scan_books.py --auto                 # Auto mode (3s delay)
  python3 scan_books.py --model cpu             # CPU-only
  python3 scan_books.py --model metis          # Metis accelerator only
  python3 scan_books.py --no-preprocessing     # Skip multi-pass, single raw pass
  python3 scan_books.py --no-color-filters      # 2 passes only: upscale + raw (skip color filters)
        """
    )
    parser.add_argument(
        '--model',
        choices=['cpu', 'metis', 'hybrid'],
        default='hybrid',
        help="OCR model: cpu (CPU-only), metis (accelerator), hybrid (ensemble, default)"
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
        '--lang',
        choices=['en', 'it'],
        default=None,
        help="Filter DB search by language (default: all languages)"
    )
    parser.add_argument(
        '--no-color-filters',
        action='store_true',
        help="Disable color filter passes (default: enabled, 10 passes total)"
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
        debug=args.debug,
        lang=args.lang,
        color_filters=not args.no_color_filters
    )

    scanner.run()


if __name__ == "__main__":
    main()
