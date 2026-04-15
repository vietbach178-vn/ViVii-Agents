"""Splitter agent — refines rough sentences using an LLM while preserving words verbatim."""

import time
from typing import List, Dict

from config import SPLITTER_MODEL
from llm_utils import call_llm_json
from agents.A1_splitter.prompt import SPLITTER_SYSTEM


def _normalize(text: str) -> str:
    return " ".join(text.split()).strip()


def _split_sentence_llm(text: str) -> List[str]:
    data = call_llm_json(
        model=SPLITTER_MODEL,
        system=SPLITTER_SYSTEM,
        user_msg=f'Split this into sentences. Return JSON object with key "sentences" containing an array of strings.\n\n{text}',
        temperature=0.1,
    )

    if isinstance(data, list):
        parts = data
    elif isinstance(data, dict):
        parts = data.get("sentences", data.get("result", data.get("output", data.get("items", []))))
        if not isinstance(parts, list):
            parts = [text]
    else:
        parts = [text]

    return [str(p) for p in parts if p]


def _verify_split(original: str, parts: List[str]) -> bool:
    return _normalize(" ".join(parts)) == _normalize(original)


def split_sentences_with_llm(sentences: List[Dict]) -> List[Dict]:
    """Use LLM to refine all sentences — split where speaker changes or grammar shifts.

    Anti-hallucination: if joined split text != original text, reject and keep original.
    """
    result = []

    for i, sent in enumerate(sentences):
        if i > 0 and i % 10 == 0:
            time.sleep(5)

        if sent["text"].startswith("[") and sent["text"].endswith("]"):
            result.append(sent)
            continue

        try:
            parts = _split_sentence_llm(sent["text"])
        except Exception as e:
            print(f"  Splitter error for '{sent['text'][:40]}...': {e}")
            result.append(sent)
            continue

        if _verify_split(sent["text"], parts):
            for p in parts:
                if p.strip():
                    result.append({"text": p.strip(), "start": sent["start"]})
        else:
            print(f"  Verify failed, keeping original: {sent['text'][:50]}...")
            result.append(sent)

    return result
