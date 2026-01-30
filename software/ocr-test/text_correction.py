"""
Post-processing per correzione errori OCR.
Correzioni generiche basate su pattern comuni di errori OCR.
Nessuna personalizzazione per libri specifici.
"""

import re
from difflib import SequenceMatcher

# =============================================================================
# CORREZIONI GENERICHE OCR
# =============================================================================

# Correzioni di pattern comuni (errori frequenti)
COMMON_OCR_FIXES = {
    # Articoli/preposizioni italiane
    "Dl": "DI",
    "ll": "IL",
    "Ia": "LA",
    "ln": "IN",
    # Spazi errati
    "  ": " ",
}

# Pattern rumore da rimuovere
NOISE_PATTERNS = [
    r"^[#@€\$%&\*\+=<>|\\/_~\`\^\(\)\[\]\{\}]+$",  # Solo simboli
    r"^[0-9#@€]+$",  # Solo numeri e simboli
    r"^.{1,2}$",  # Stringhe di 1-2 caratteri (spesso rumore)
    r"tv\+",  # Pattern tv+ comune
    r"Orange Pi",  # Esclude testo della board
]

# =============================================================================
# DIZIONARIO EDITORI E COLLANE (italiano + internazionale)
# =============================================================================

PUBLISHERS = {
    # Editori italiani
    "MONDADORI", "FELTRINELLI", "EINAUDI", "ADELPHI", "BOMPIANI",
    "RIZZOLI", "GARZANTI", "LONGANESI", "SPERLING", "KUPFER",
    "LATERZA", "SELLERIO", "NEWTON", "COMPTON", "PIEMME",
    "MURSIA", "GIUNTI", "HOEPLI", "FAZI", "NERI", "POZZA",
    "MARSILIO", "MINIMUM", "IPERBOREA", "NOTTETEMPO",
    # Editori internazionali
    "PENGUIN", "RANDOM", "HOUSE", "HARPER", "COLLINS",
    "SIMON", "SCHUSTER", "MACMILLAN", "HACHETTE",
    "WILEY", "PEARSON", "SPRINGER", "BLOOMSBURY",
}

COLLECTIONS = {
    # Collane italiane comuni
    "OSCAR", "BESTSELLERS", "SUPER", "CLASSICI", "TASCABILI",
    "UNIVERSALE", "ECONOMICA", "BIBLIOTECA", "NARRATIVA",
    "GIALLI", "THRILLER", "FANTASY", "ROMANZO",
}

# Parole italiane comuni (per fuzzy matching generico)
COMMON_WORDS = {
    "FIGLIO", "FIGLIA", "PADRE", "MADRE", "UOMO", "DONNA",
    "STORIA", "TEMPO", "VITA", "MORTE", "AMORE", "MONDO",
    "CASA", "NOTTE", "GIORNO", "CITTA", "MARE", "TERRA",
    "ULTIMO", "PRIMA", "DOPO", "GRANDE", "PICCOLO",
    "NUOVO", "VECCHIO", "LUNGO", "BREVE", "EROE", "EROI",
}

# Unione per fuzzy matching
KNOWN_WORDS = PUBLISHERS | COLLECTIONS | COMMON_WORDS


def similarity(a: str, b: str) -> float:
    """Calcola similarita tra due stringhe (0-1)."""
    return SequenceMatcher(None, a.upper(), b.upper()).ratio()


def find_best_match(word: str, known_words: set, threshold: float = 0.80) -> str | None:
    """Trova la parola nota piu simile se supera la soglia."""
    word_upper = word.upper()
    
    if word_upper in known_words:
        return word_upper
    
    if len(word) < 4:
        return None
    
    best_match = None
    best_score = threshold
    
    for known in known_words:
        if abs(len(word) - len(known)) > 2:
            continue
        score = similarity(word_upper, known)
        if score > best_score:
            best_score = score
            best_match = known
    
    return best_match


def is_noise(text: str) -> bool:
    """Verifica se il testo e rumore da rimuovere."""
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def fix_common_ocr_errors(text: str, debug: bool = False) -> str:
    """Applica correzioni per errori OCR comuni."""
    for wrong, correct in COMMON_OCR_FIXES.items():
        if wrong in text:
            text = text.replace(wrong, correct)
            if debug:
                print(f"  [fix] {wrong} -> {correct}")
    return text


def correct_text(text: str, debug: bool = False) -> tuple[str, float]:
    """
    Corregge il testo OCR in modo generico.
    
    Returns:
        (testo_corretto, confidence_boost)
    """
    if not text or is_noise(text):
        return "", 0.0
    
    original = text
    corrections_made = 0
    
    # 1. Correzioni errori comuni
    text = fix_common_ocr_errors(text, debug)
    if text != original:
        corrections_made += 1
    
    # 2. Fuzzy matching per parole note
    words = text.split()
    corrected_words = []
    
    for word in words:
        if len(word) < 4:
            corrected_words.append(word)
            continue
        
        match = find_best_match(word, KNOWN_WORDS, threshold=0.80)
        if match and match != word.upper():
            corrected_words.append(match)
            corrections_made += 1
            if debug:
                print(f"  [fuzzy] {word} -> {match}")
        else:
            corrected_words.append(word)
    
    text = " ".join(corrected_words)
    text = re.sub(r"\s+", " ", text).strip()
    
    confidence_boost = min(corrections_made * 0.03, 0.10)
    
    if debug and text != original:
        print(f"  [result] \"{original}\" -> \"{text}\" (+{confidence_boost:.2f})")
    
    return text, confidence_boost


def correct_textbox_list(textboxes: list, debug: bool = False) -> list:
    """Corregge una lista di TextBox."""
    from ocr_pipeline import TextBox
    
    corrected = []
    for box in textboxes:
        new_text, boost = correct_text(box.text, debug=debug)
        if new_text:
            new_conf = min(box.confidence + boost, 1.0)
            corrected.append(TextBox(
                bbox=box.bbox,
                text=new_text,
                confidence=new_conf
            ))
    
    return corrected
