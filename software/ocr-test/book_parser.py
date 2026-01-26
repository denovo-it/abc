#!/usr/bin/env python3
"""
Parser to extract title, author, and publisher from book covers.
Uses heuristics based on position, size, and text content.
"""

import re
from dataclasses import dataclass, field

from ocr_pipeline import TextBox
import config


@dataclass
class BookInfo:
    """Information extracted from book cover."""
    title: str = ""
    author: str = ""
    publisher: str = ""
    confidence: float = 0.0
    raw_texts: list[TextBox] = field(default_factory=list)


# Common publisher patterns (Italian and international)
PUBLISHER_PATTERNS = [
    r'\b(mondadori|feltrinelli|einaudi|adelphi|bompiani|rizzoli)\b',
    r'\b(garzanti|laterza|sellerio|newton|compton|piemme)\b',
    r'\b(longanesi|sperling|kupfer|mursia|giunti|hoepli)\b',
    r'\b(penguin|random\s*house|harper|collins|simon|schuster)\b',
    r'\b(macmillan|hachette|wiley|pearson|springer)\b',
    r'\b(edizioni?|editore|editori|editor[ie]|casa\s+editrice)\b',
    r'\b(publisher|publishing|press|books?|verlag)\b',
]

# Patterns to identify author names
AUTHOR_PATTERNS = [
    r'^[A-Z][a-z]+\s+[A-Z][a-z]+$',  # First Last
    r'^[A-Z]\.\s*[A-Z][a-z]+$',  # J. Smith
    r'^[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z][a-z]+$',  # John R. Smith
]


def is_likely_publisher(text: str) -> bool:
    """Check if text looks like a publisher name."""
    text_lower = text.lower()
    for pattern in PUBLISHER_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def is_likely_author(text: str) -> bool:
    """Check if text looks like an author name."""
    # Too short or too long
    if len(text) < 5 or len(text) > 50:
        return False

    # Contains numbers -> probably not an author
    if re.search(r'\d', text):
        return False

    # Match typical patterns
    for pattern in AUTHOR_PATTERNS:
        if re.match(pattern, text):
            return True

    # Two or three words starting with uppercase
    words = text.split()
    if 2 <= len(words) <= 4:
        if all(w[0].isupper() for w in words if w):
            return True

    return False


def calculate_text_prominence(box: TextBox, image_height: int, image_width: int) -> float:
    """
    Calculate a prominence score for text.
    Considers box size, position, and text length.
    """
    x1, y1, x2, y2 = box.bbox
    box_height = y2 - y1
    box_width = x2 - x1

    # Normalize dimensions
    height_ratio = box_height / image_height
    width_ratio = box_width / image_width

    # Relative area
    area_score = height_ratio * width_ratio * 10

    # Vertical position (center = more important for title)
    center_y = (y1 + y2) / 2
    center_ratio = center_y / image_height
    # Max score for text in central third
    if 0.25 <= center_ratio <= 0.6:
        position_score = 1.0
    elif 0.15 <= center_ratio <= 0.75:
        position_score = 0.7
    else:
        position_score = 0.3

    # Text length
    text_len = len(box.text)
    if text_len > 5:
        length_score = min(text_len / 30, 1.0)
    else:
        length_score = 0.2

    # Combine scores
    prominence = (
        area_score * 0.4 +
        position_score * 0.3 +
        length_score * 0.2 +
        box.confidence * 0.1
    )

    return prominence


def parse_book_cover(
    text_boxes: list[TextBox],
    image_height: int,
    image_width: int
) -> BookInfo:
    """
    Analyze extracted texts and identify title, author, and publisher.

    Args:
        text_boxes: List of TextBox from OCR
        image_height: Original image height
        image_width: Original image width

    Returns:
        BookInfo with extracted information
    """
    if not text_boxes:
        return BookInfo()

    book = BookInfo(raw_texts=text_boxes)

    # Calculate prominence for each box
    scored_boxes = []
    for box in text_boxes:
        prominence = calculate_text_prominence(box, image_height, image_width)
        scored_boxes.append((box, prominence))

    # Sort by prominence
    scored_boxes.sort(key=lambda x: x[1], reverse=True)

    # Identify publisher (usually at bottom)
    for box, _ in scored_boxes:
        if is_likely_publisher(box.text):
            book.publisher = box.text
            break

    # If not found with pattern, look at bottom
    if not book.publisher:
        bottom_boxes = [
            (box, score) for box, score in scored_boxes
            if box.bbox[1] > image_height * 0.7  # In bottom 30%
        ]
        if bottom_boxes:
            # Take most prominent text at bottom
            book.publisher = bottom_boxes[0][0].text

    # Identify author
    for box, _ in scored_boxes:
        if box.text == book.publisher:
            continue
        if is_likely_author(box.text):
            book.author = box.text
            break

    # If not found, look at top
    if not book.author:
        top_boxes = [
            (box, score) for box, score in scored_boxes
            if box.bbox[3] < image_height * 0.3  # In top 30%
            and box.text != book.publisher
        ]
        if top_boxes:
            # Prefer short texts (names)
            for box, _ in top_boxes:
                if len(box.text.split()) <= 4:
                    book.author = box.text
                    break

    # Identify title (most prominent remaining text)
    for box, score in scored_boxes:
        if box.text not in (book.author, book.publisher):
            book.title = box.text
            book.confidence = score
            break

    return book


def format_book_info(book: BookInfo) -> str:
    """Format book info for output."""
    lines = []
    lines.append("=" * 50)
    lines.append("BOOK INFORMATION")
    lines.append("=" * 50)

    if book.title:
        lines.append(f"Title:     {book.title}")
    else:
        lines.append("Title:     [not identified]")

    if book.author:
        lines.append(f"Author:    {book.author}")
    else:
        lines.append("Author:    [not identified]")

    if book.publisher:
        lines.append(f"Publisher: {book.publisher}")
    else:
        lines.append("Publisher: [not identified]")

    lines.append("-" * 50)
    lines.append(f"Confidence: {book.confidence:.2f}")
    lines.append("=" * 50)

    return "\n".join(lines)


def main():
    """Test parser with sample data."""
    # Test data
    test_boxes = [
        TextBox(bbox=(50, 20, 350, 60), text="Stephen King", confidence=0.9),
        TextBox(bbox=(30, 100, 370, 200), text="IT", confidence=0.95),
        TextBox(bbox=(100, 450, 300, 480), text="Sperling & Kupfer", confidence=0.85),
    ]

    book = parse_book_cover(test_boxes, image_height=500, image_width=400)
    print(format_book_info(book))

    print("\nRaw texts:")
    for box in book.raw_texts:
        print(f"  - {box.text} @ {box.bbox}")


if __name__ == "__main__":
    main()
