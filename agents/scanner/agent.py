"""Scanner agent — discovers candidate rich points from transcript chunks."""

import re

from config import SCANNER_MODEL
from schemas import ScannerOutput
from llm_utils import call_llm_json
from agents.scanner.prompt import SCANNER_SYSTEM


def scan_chunk(chunk_text: str) -> ScannerOutput:
    """Scan a transcript chunk for candidate rich points."""
    data = call_llm_json(
        model=SCANNER_MODEL,
        system=SCANNER_SYSTEM,
        user_msg=f"Analyze this transcript chunk for rich points. Return JSON with key \"candidates\" containing an array of objects. ONLY include words that literally appear in this text.\n\n{chunk_text}",
    )
    if "candidates" not in data and isinstance(data, list):
        data = {"candidates": data}
    return ScannerOutput(**data)


def word_exists_in_text(word: str, text: str) -> bool:
    """Check if a word/phrase actually exists in the transcript text (case-insensitive)."""
    escaped = re.escape(word.lower())
    if ' ' in word:
        return word.lower() in text.lower()
    return bool(re.search(r'\b' + escaped + r'\b', text.lower()))


def scan_all_chunks(chunks: list, full_text: str) -> list:
    """Scan all chunks, verify against transcript, dedup by (word, sense_tag)."""
    all_candidates = []
    seen = set()
    dropped = []

    for chunk in chunks:
        result = scan_chunk(chunk["text"])
        for c in result.candidates:
            key = (c.word.lower(), c.sense_tag)
            if key in seen:
                continue
            seen.add(key)

            if not word_exists_in_text(c.word, full_text):
                dropped.append(c.word)
                continue

            all_candidates.append(c.model_dump())

    if dropped:
        print(f"  Dropped (not in transcript): {', '.join(dropped)}")

    return all_candidates
