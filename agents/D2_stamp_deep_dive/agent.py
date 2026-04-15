"""D2 — Stamp Deep-Dive agent.

Writes a long-form article (with mandatory TL;DR) for each canonical stamp
from D1. Uses a file-based cache keyed by slugified canonical_name so a
stamp seen across multiple videos only costs one LLM call total.
"""

import json
import re
from pathlib import Path

from config import JOKE_EXPLAINER_MODEL
from llm_utils import call_llm_json
from agents.D2_stamp_deep_dive.prompt import D2_SYSTEM


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "unknown"


def deep_dive_for_stamp(
    canonical_name: str,
    category: str,
    cache_dir: Path,
    force_refresh: bool = False,
) -> dict:
    """Generate or load a deep-dive article for one canonical stamp."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{_slugify(canonical_name)}.json"

    if cache_path.exists() and not force_refresh:
        return json.loads(cache_path.read_text())

    user_msg = f"""## Stamp to explain

canonical_name: {canonical_name}
category: {category}

Write the full article per the system prompt. Return JSON with keys `stamp_canonical_name`, `tl_dr`, `sections`, `word_count`."""

    data = call_llm_json(
        model=JOKE_EXPLAINER_MODEL,
        system=D2_SYSTEM,
        user_msg=user_msg,
        max_tokens=8192,
        temperature=0.4,
    )

    data.setdefault("stamp_canonical_name", canonical_name)
    cache_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return data


def run_d2(d1_output: dict, cache_dir: Path, force_refresh: bool = False) -> dict:
    """Run D2 for every unique canonical stamp across all blocks in a D1 output.

    Skips blocks with no stamps. De-duplicates by canonical_name so the same
    stamp doesn't get re-generated per block.
    """
    seen: dict[str, dict] = {}
    for block in d1_output.get("stamps_per_block", []):
        for stamp in block.get("stamps", []):
            canonical = stamp.get("canonical_name", "")
            if not canonical or canonical in seen:
                continue
            try:
                article = deep_dive_for_stamp(
                    canonical, stamp.get("category", "pop_culture"), cache_dir, force_refresh
                )
                seen[canonical] = article
            except Exception as e:
                print(f"  D2 error for stamp '{canonical}': {e}")

    return {
        "video_id": d1_output.get("video_id", ""),
        "url": d1_output.get("url", ""),
        "title": d1_output.get("title", ""),
        "articles": list(seen.values()),
    }
