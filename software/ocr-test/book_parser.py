#!/usr/bin/env python3
"""
Parser per estrarre titolo, autore ed editore da copertine di libri.
Usa euristiche basate su posizione, dimensione e raggruppamento del testo.
Versione autonoma senza dipendenze da LLM.
"""

import re
from dataclasses import dataclass, field
from typing import List, Tuple

from ocr_pipeline import TextBox
import config


@dataclass
class BookInfo:
    """Informazioni estratte dalla copertina."""
    title: str = ""
    author: str = ""
    publisher: str = ""
    confidence: float = 0.0
    raw_texts: list[TextBox] = field(default_factory=list)


# Pattern editori (italiano e internazionale)
PUBLISHER_PATTERNS = [
    r"\b(mondadori|feltrinelli|einaudi|adelphi|bompiani|rizzoli)\b",
    r"\b(garzanti|laterza|sellerio|newton|compton|piemme)\b",
    r"\b(longanesi|sperling|kupfer|mursia|giunti|hoepli)\b",
    r"\b(penguin|random\s*house|harper|collins|simon|schuster)\b",
    r"\b(macmillan|hachette|wiley|pearson|springer)\b",
    r"\b(edizioni?|editore|editori|casa\s+editrice)\b",
    r"\b(publisher|publishing|press|books?|verlag)\b",
    r"\b(oscar|bestsellers|tascabili|classici)\b",
]

# Pattern per identificare nomi di autori
AUTHOR_PATTERNS = [
    r"^[A-Z][a-z]+\s+[A-Z]\.?\s*[A-Z][a-z]+$",  # Nome I. Cognome
    r"^[A-Z][a-z]+\s+[A-Z][a-z]+$",  # Nome Cognome
    r"^[A-Z]\.\s*[A-Z][a-z]+$",  # J. Smith
    r"^[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+$",  # Nome Secondo Cognome
]

# Parole da escludere (rumore comune)
NOISE_WORDS = {
    "orange", "pi", "the", "a", "an", "il", "la", "lo", "le", "gli", "un", "una",
}


def is_likely_publisher(text: str) -> bool:
    """Verifica se il testo sembra un editore."""
    text_lower = text.lower()
    for pattern in PUBLISHER_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def is_likely_author(text: str) -> bool:
    """Verifica se il testo sembra un nome di autore."""
    text_clean = text.strip()
    
    if len(text_clean) < 5 or len(text_clean) > 50:
        return False
    
    if re.search(r"\d", text_clean):
        return False
    
    for pattern in AUTHOR_PATTERNS:
        if re.match(pattern, text_clean):
            return True
    
    words = text_clean.split()
    if 2 <= len(words) <= 4:
        if all(w[0].isupper() for w in words if len(w) > 1):
            # Verifica che non siano tutte maiuscole (titolo) 
            if not all(w.isupper() for w in words):
                return True
            # Se sono 2-3 parole tutte maiuscole, potrebbe essere autore
            if len(words) <= 3:
                return True
    
    return False


def is_noise(text: str) -> bool:
    """Verifica se il testo e rumore da ignorare."""
    text_lower = text.lower().strip()
    
    if len(text_lower) <= 2:
        return True
    
    if text_lower in NOISE_WORDS:
        return True
    
    if re.match(r"^[^a-zA-Z]*$", text):
        return True
    
    if "orange pi" in text_lower:
        return True
    
    return False


def boxes_on_same_line(box1: TextBox, box2: TextBox, tolerance: float = 0.5) -> bool:
    """Verifica se due box sono sulla stessa riga."""
    y1_center = (box1.bbox[1] + box1.bbox[3]) / 2
    y2_center = (box2.bbox[1] + box2.bbox[3]) / 2
    
    h1 = box1.bbox[3] - box1.bbox[1]
    h2 = box2.bbox[3] - box2.bbox[1]
    avg_height = (h1 + h2) / 2
    
    return abs(y1_center - y2_center) < avg_height * tolerance


def merge_boxes_into_lines(boxes: List[TextBox]) -> List[TextBox]:
    """Raggruppa i box sulla stessa riga e li unisce."""
    if not boxes:
        return []
    
    # Ordina per posizione Y
    sorted_boxes = sorted(boxes, key=lambda b: b.bbox[1])
    
    lines = []
    current_line = [sorted_boxes[0]]
    
    for box in sorted_boxes[1:]:
        if boxes_on_same_line(current_line[0], box):
            current_line.append(box)
        else:
            lines.append(current_line)
            current_line = [box]
    
    if current_line:
        lines.append(current_line)
    
    # Unisci i box di ogni riga
    merged = []
    for line in lines:
        # Ordina per X (sinistra -> destra)
        line_sorted = sorted(line, key=lambda b: b.bbox[0])
        
        # Unisci testo
        texts = [b.text for b in line_sorted]
        combined_text = " ".join(texts)
        
        # Calcola bbox combinato
        x1 = min(b.bbox[0] for b in line_sorted)
        y1 = min(b.bbox[1] for b in line_sorted)
        x2 = max(b.bbox[2] for b in line_sorted)
        y2 = max(b.bbox[3] for b in line_sorted)
        
        # Confidence media
        avg_conf = sum(b.confidence for b in line_sorted) / len(line_sorted)
        
        merged.append(TextBox(
            bbox=(x1, y1, x2, y2),
            text=combined_text,
            confidence=avg_conf
        ))
    
    return merged


def calculate_text_prominence(box: TextBox, image_height: int, image_width: int) -> float:
    """Calcola un punteggio di prominenza per il testo."""
    x1, y1, x2, y2 = box.bbox
    box_height = y2 - y1
    box_width = x2 - x1
    
    height_ratio = box_height / image_height
    width_ratio = box_width / image_width
    area_score = height_ratio * width_ratio * 10
    
    center_y = (y1 + y2) / 2
    center_ratio = center_y / image_height
    
    if 0.25 <= center_ratio <= 0.6:
        position_score = 1.0
    elif 0.15 <= center_ratio <= 0.75:
        position_score = 0.7
    else:
        position_score = 0.3
    
    text_len = len(box.text)
    length_score = min(text_len / 30, 1.0) if text_len > 3 else 0.2
    
    prominence = (
        area_score * 0.35 +
        position_score * 0.25 +
        length_score * 0.25 +
        box.confidence * 0.15
    )
    
    return prominence


def parse_book_cover(
    text_boxes: List[TextBox],
    image_height: int,
    image_width: int
) -> BookInfo:
    """
    Analizza i testi estratti e identifica titolo, autore ed editore.
    
    Pipeline:
    1. Filtra rumore
    2. Raggruppa box sulla stessa riga
    3. Identifica editore (pattern + posizione bassa)
    4. Identifica autore (pattern nome)
    5. Il resto e titolo (prominenza)
    """
    if not text_boxes:
        return BookInfo()
    
    # 1. Filtra rumore
    filtered = [box for box in text_boxes if not is_noise(box.text)]
    
    if not filtered:
        return BookInfo(raw_texts=text_boxes)
    
    # 2. Raggruppa box sulla stessa riga
    merged = merge_boxes_into_lines(filtered)
    
    book = BookInfo(raw_texts=text_boxes)
    
    # 3. Calcola prominenza
    scored = []
    for box in merged:
        score = calculate_text_prominence(box, image_height, image_width)
        scored.append((box, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    
    used_texts = set()
    
    # 4. Identifica editore (pattern o posizione bassa)
    for box, _ in scored:
        if is_likely_publisher(box.text):
            book.publisher = box.text
            used_texts.add(box.text)
            break
    
    if not book.publisher:
        bottom_boxes = [
            (box, score) for box, score in scored
            if box.bbox[1] > image_height * 0.75
        ]
        if bottom_boxes:
            book.publisher = bottom_boxes[0][0].text
            used_texts.add(book.publisher)
    
    # 5. Identifica autore
    for box, _ in scored:
        if box.text in used_texts:
            continue
        if is_likely_author(box.text):
            book.author = box.text
            used_texts.add(box.text)
            break
    
    # Se non trovato, cerca in alto
    if not book.author:
        top_boxes = [
            (box, score) for box, score in scored
            if box.bbox[3] < image_height * 0.35
            and box.text not in used_texts
        ]
        for box, _ in top_boxes:
            words = box.text.split()
            if 2 <= len(words) <= 4:
                book.author = box.text
                used_texts.add(box.text)
                break
    
    # 6. Identifica titolo (testo piu prominente rimanente)
    title_parts = []
    for box, score in scored:
        if box.text in used_texts:
            continue
        # Aggiungi al titolo se nella zona centrale
        center_y = (box.bbox[1] + box.bbox[3]) / 2
        if 0.2 < center_y / image_height < 0.85:
            title_parts.append((box, score))
            used_texts.add(box.text)
    
    if title_parts:
        # Ordina per posizione Y per ricostruire ordine
        title_parts.sort(key=lambda x: x[0].bbox[1])
        book.title = " ".join(box.text for box, _ in title_parts)
        book.confidence = sum(score for _, score in title_parts) / len(title_parts)
    
    return book


def format_book_info(book: BookInfo) -> str:
    """Formatta le info del libro per output."""
    lines = []
    lines.append("=" * 50)
    lines.append("BOOK INFORMATION")
    lines.append("=" * 50)
    
    lines.append(f"Title:     {book.title or [not identified]}")
    lines.append(f"Author:    {book.author or [not identified]}")
    lines.append(f"Publisher: {book.publisher or [not identified]}")
    
    lines.append("-" * 50)
    lines.append(f"Confidence: {book.confidence:.2f}")
    lines.append("=" * 50)
    
    return "\n".join(lines)
