"""D1 — Culture Stamp Detector agent.

Two-step process per topic block:
  1. LLM proposes culture stamps with open naming.
  2. Code canonicalizes each proposed name against a persisted catalog
     (exact match → fuzzy match via rapidfuzz → auto-add new entry).

The catalog grows organically across pipeline runs.
"""

import json
from datetime import date
from pathlib import Path

from config import JOKE_DETECTOR_MODEL
from llm_utils import call_llm_json
from agents.D1_stamp_detector.prompt import D1_SYSTEM


CATALOG_PATH = Path(__file__).parent / "catalog.json"
FUZZY_THRESHOLD = 85  # rapidfuzz score ≥ this → treat as alias of existing canonical


def _load_catalog() -> dict:
    if not CATALOG_PATH.exists():
        return {}
    return json.loads(CATALOG_PATH.read_text())


def _save_catalog(catalog: dict) -> None:
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False))


def _normalize(name: str) -> str:
    return " ".join(name.lower().strip().split())


def canonicalize(llm_name: str, category: str, catalog: dict) -> str:
    """Map an LLM-proposed stamp name to a canonical form.

    Exact lowercase match → fuzzy match ≥ FUZZY_THRESHOLD → new entry.
    Mutates `catalog` in place: records alias or creates new entry.
    Returns the canonical_name.
    """
    normalized = _normalize(llm_name)

    # Exact match against canonical keys or aliases
    for canonical, entry in catalog.items():
        if _normalize(canonical) == normalized:
            entry["seen_count"] = entry.get("seen_count", 0) + 1
            return canonical
        for alias in entry.get("aliases", []):
            if _normalize(alias) == normalized:
                entry["seen_count"] = entry.get("seen_count", 0) + 1
                return canonical

    # Fuzzy match against canonical keys
    try:
        from rapidfuzz import fuzz
    except ImportError:
        fuzz = None

    if fuzz is not None and catalog:
        best_canonical = None
        best_score = 0
        for canonical in catalog:
            score = fuzz.ratio(normalized, _normalize(canonical))
            if score > best_score:
                best_score = score
                best_canonical = canonical
        if best_score >= FUZZY_THRESHOLD and best_canonical:
            entry = catalog[best_canonical]
            aliases = entry.setdefault("aliases", [])
            if llm_name not in aliases:
                aliases.append(llm_name)
            entry["seen_count"] = entry.get("seen_count", 0) + 1
            return best_canonical

    # New entry — use LLM name as canonical
    catalog[llm_name] = {
        "aliases": [],
        "category": category,
        "first_seen": date.today().isoformat(),
        "seen_count": 1,
    }
    return llm_name


def detect_stamps_for_block(c2_block: dict) -> dict:
    """Run D1 on one C2 topic block. Returns stamps with canonicalized names.

    Mutates the shared catalog file on disk.
    """
    user_msg = f"""## C2 output for one topic block

{json.dumps(c2_block, indent=2, ensure_ascii=False)}

Return JSON with the `stamps` array described in the system prompt."""

    data = call_llm_json(
        model=JOKE_DETECTOR_MODEL,
        system=D1_SYSTEM,
        user_msg=user_msg,
        max_tokens=2048,
        temperature=0.2,
    )

    raw_stamps = data.get("stamps", []) if isinstance(data, dict) else []

    catalog = _load_catalog()
    canonicalized = []
    for s in raw_stamps:
        llm_name = s.get("llm_proposed_name", "")
        if not llm_name:
            continue
        category = s.get("category", "pop_culture")
        canonical = canonicalize(llm_name, category, catalog)
        canonicalized.append(
            {
                "canonical_name": canonical,
                "llm_proposed_name": llm_name,
                "category": category,
                "confidence": s.get("confidence", "medium"),
                "evidence": s.get("evidence", ""),
                "source_tier": s.get("source_tier", "tier_1"),
            }
        )
    _save_catalog(catalog)

    return {"id": c2_block.get("id", ""), "stamps": canonicalized}


def run_d1(c2_output: dict) -> dict:
    """Run D1 on every topic block in a C2 output and collate."""
    results = []
    for block in c2_output.get("explanations", []):
        results.append(detect_stamps_for_block(block))
    return {
        "video_id": c2_output.get("video_id", ""),
        "url": c2_output.get("url", ""),
        "title": c2_output.get("title", ""),
        "stamps_per_block": results,
    }
