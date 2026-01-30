"""
Correzione OCR tramite LLM locale (Ollama).
Usa Llama 3.2 3B per correggere errori OCR su copertine di libri.
"""

import json
import requests
from typing import List, Optional
from dataclasses import dataclass

# Configurazione Ollama
OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2:3b"
TIMEOUT = 60  # secondi


@dataclass
class CorrectionResult:
    """Risultato della correzione LLM."""
    original: str
    corrected: str
    title: str = ""
    author: str = ""
    publisher: str = ""
    confidence: float = 0.0


SYSTEM_PROMPT = """You are an OCR correction assistant for Italian book covers.
Fix OCR errors in the text provided. Common errors include:
- Wrong letters (PCRCY -> PERCY, FIGLO -> FIGLIO)
- Missing spaces or extra characters
- Misspelled author names and titles

Return ONLY a JSON object with these fields:
- title: the book title (corrected)
- author: the author name (corrected)
- publisher: the publisher/collection name (corrected)
- all_text: all text lines corrected, joined by newline

Do not add explanations, only the JSON."""


def check_ollama_running() -> bool:
    """Verifica se Ollama server e in esecuzione."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        return resp.status_code == 200
    except:
        return False


def correct_with_llm(
    text_lines: List[str],
    model: str = DEFAULT_MODEL,
    debug: bool = False
) -> Optional[CorrectionResult]:
    """
    Corregge il testo OCR usando LLM.
    
    Args:
        text_lines: Lista di righe di testo OCR
        model: Modello Ollama da usare
        debug: Se True, stampa info di debug
    
    Returns:
        CorrectionResult con testo corretto, o None se errore
    """
    if not text_lines:
        return None
    
    if not check_ollama_running():
        if debug:
            print("[LLM] Ollama non in esecuzione")
        return None
    
    # Prepara il prompt
    ocr_text = "\n".join(text_lines)
    prompt = f"""{SYSTEM_PROMPT}

OCR text to correct:
{ocr_text}

JSON response:"""
    
    if debug:
        print(f"[LLM] Invio a {model}...")
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Bassa temperatura per output deterministico
                    "num_predict": 200,  # Max token output
                }
            },
            timeout=TIMEOUT
        )
        
        if response.status_code != 200:
            if debug:
                print(f"[LLM] Errore HTTP: {response.status_code}")
            return None
        
        result = response.json()
        llm_output = result.get("response", "").strip()
        
        if debug:
            print(f"[LLM] Output: {llm_output[:200]}...")
        
        # Parsing JSON response
        try:
            # Cerca il JSON nella risposta
            json_start = llm_output.find("{")
            json_end = llm_output.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = llm_output[json_start:json_end]
                data = json.loads(json_str)
                
                return CorrectionResult(
                    original=ocr_text,
                    corrected=data.get("all_text", ocr_text),
                    title=data.get("title", ""),
                    author=data.get("author", ""),
                    publisher=data.get("publisher", ""),
                    confidence=0.8  # Confidence fissa per LLM
                )
        except json.JSONDecodeError:
            if debug:
                print("[LLM] Errore parsing JSON, uso output grezzo")
            # Fallback: usa output grezzo come correzione
            return CorrectionResult(
                original=ocr_text,
                corrected=llm_output,
                confidence=0.5
            )
        
    except requests.Timeout:
        if debug:
            print("[LLM] Timeout")
        return None
    except Exception as e:
        if debug:
            print(f"[LLM] Errore: {e}")
        return None
    
    return None


def correct_book_info(text_boxes: list, debug: bool = False) -> Optional[CorrectionResult]:
    """
    Corregge le informazioni del libro dai TextBox OCR.
    
    Args:
        text_boxes: Lista di TextBox dalla pipeline OCR
        debug: Se True, stampa info di debug
    
    Returns:
        CorrectionResult con info libro corrette
    """
    # Estrai testo dai box, ordinati per posizione Y
    sorted_boxes = sorted(text_boxes, key=lambda b: b.bbox[1])
    text_lines = [box.text for box in sorted_boxes if box.text.strip()]
    
    # Filtra rumore
    filtered_lines = []
    for line in text_lines:
        # Salta linee troppo corte o che sembrano rumore
        if len(line) < 3:
            continue
        if "orange pi" in line.lower():
            continue
        filtered_lines.append(line)
    
    if not filtered_lines:
        return None
    
    return correct_with_llm(filtered_lines, debug=debug)


# Test standalone
if __name__ == "__main__":
    print("=== Test LLM Correction ===\n")
    
    if not check_ollama_running():
        print("ERRORE: Ollama non in esecuzione!")
        print("Avvia con: ollama serve")
        exit(1)
    
    # Test con errori OCR tipici
    test_lines = [
        "PCRCY JACKSON",
        "RICK RIORDAN",
        "IL FIGLO DI NETTUNO",
        "EROF DELL OLIMPO",
        "BESTSELERS"
    ]
    
    print("Input OCR:")
    for line in test_lines:
        print(f"  {line}")
    
    print("\nCorrezione in corso...")
    result = correct_with_llm(test_lines, debug=True)
    
    if result:
        print(f"\n=== Risultato ===")
        print(f"Titolo:   {result.title}")
        print(f"Autore:   {result.author}")
        print(f"Editore:  {result.publisher}")
        print(f"\nTesto corretto:\n{result.corrected}")
    else:
        print("Correzione fallita")
