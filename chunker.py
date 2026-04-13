"""Merge transcript segments into complete sentences, then group into chunks.

Note: the LLM-based sentence splitter has moved to agents/splitter/.
This file now only contains pure-Python heuristics.
"""

from __future__ import annotations

import re
from typing import List, Dict

from config import CHUNK_SIZE


# --- Step 1: Segments → Sentences (heuristic, no LLM) ---

PAUSE_THRESHOLD = 1.0
MAX_SENTENCE_WORDS = 80

SENTENCE_START_PATTERNS = re.compile(
    r'^(so |but |and then |okay |all right |yeah |no |hey |like |'
    r'oh |man |dude |wait |now |anyway |look |well )',
    re.IGNORECASE
)


def segments_to_sentences(segments: List[Dict]) -> List[Dict]:
    """Merge YouTube transcript segments into complete sentences.

    YouTube auto-captions come as short fragments (2-5 words each).
    This function merges them into natural sentence-like units based on:
    - Time gaps between segments (pause = new sentence)
    - Punctuation (. ? ! at end of segment text)
    - Bracketed markers like [Laughter], [Music]

    Returns list of: { text: str, start: float }
    """
    if not segments:
        return []

    sentences = []
    current_text_parts = []
    current_start = segments[0]["start"]

    for i, seg in enumerate(segments):
        text = seg["text"].strip()
        if not text:
            continue

        if text.startswith("[") and text.endswith("]"):
            if current_text_parts:
                sentences.append({
                    "text": " ".join(current_text_parts),
                    "start": current_start,
                })
                current_text_parts = []
            sentences.append({"text": text, "start": seg["start"]})
            if i + 1 < len(segments):
                current_start = segments[i + 1]["start"]
            continue

        is_new_sentence = False

        if not current_text_parts:
            current_start = seg["start"]
        else:
            prev = segments[i - 1]
            prev_end = prev["start"] + prev.get("duration", 0)
            gap = seg["start"] - prev_end

            if gap > PAUSE_THRESHOLD:
                is_new_sentence = True

            prev_text = prev["text"].strip()
            if prev_text and prev_text[-1] in ".?!":
                is_new_sentence = True

        current_word_count = sum(len(p.split()) for p in current_text_parts)
        if current_word_count >= MAX_SENTENCE_WORDS:
            is_new_sentence = True

        if is_new_sentence and current_text_parts:
            sentences.append({
                "text": " ".join(current_text_parts),
                "start": current_start,
            })
            current_text_parts = []
            current_start = seg["start"]

        current_text_parts.append(text)

    if current_text_parts:
        sentences.append({
            "text": " ".join(current_text_parts),
            "start": current_start,
        })

    return sentences


# --- Step 2: Sentences → Chunks (for Scanner) ---

def sentences_to_chunks(sentences: List[Dict]) -> List[Dict]:
    """Group sentences into chunks of ~CHUNK_SIZE words for the Scanner.

    Never splits mid-sentence. Each chunk is a list of complete sentences.

    Returns list of: { text: str, start_time: float }
    """
    if not sentences:
        return []

    total_words = sum(len(s["text"].split()) for s in sentences)
    if total_words <= CHUNK_SIZE:
        full_text = " ".join(s["text"] for s in sentences)
        return [{
            "text": full_text,
            "start_time": sentences[0]["start"],
        }]

    chunks = []
    current_texts = []
    current_words = 0
    current_start = sentences[0]["start"]

    for sent in sentences:
        sent_words = len(sent["text"].split())

        if current_words > 0 and current_words + sent_words > CHUNK_SIZE:
            chunks.append({
                "text": " ".join(current_texts),
                "start_time": current_start,
            })
            current_texts = []
            current_words = 0
            current_start = sent["start"]

        current_texts.append(sent["text"])
        current_words += sent_words

    if current_texts:
        chunks.append({
            "text": " ".join(current_texts),
            "start_time": current_start,
        })

    return chunks
