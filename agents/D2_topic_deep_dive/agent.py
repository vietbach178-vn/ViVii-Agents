"""D2 — Cultural Topic Deep-Dive agent.

Writes a long-form article (TL;DR + 4 sections) for each topic from D1.
Uses a file-based cache keyed by slugified topic title — shared cross-video,
so a topic that recurs across uploads only costs one LLM call total.
"""

import json
import re
from pathlib import Path

from config import TOPIC_DEEP_DIVE_MODEL
from llm_utils import call_llm_json
from agents.D2_topic_deep_dive.prompt import D2_SYSTEM


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "unknown"


def deep_dive_for_topic(
    topic: dict,
    cache_dir: Path,
    force_refresh: bool = False,
) -> dict:
    """Generate or load a deep-dive article for one cultural topic.

    Cache key = slug(title), shared across videos. If two videos surface the
    same topic title, the second one hits the cache.
    """
    title = topic.get("title", "").strip()
    if not title:
        raise ValueError("Topic title is required")

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{_slugify(title)}.json"

    if cache_path.exists() and not force_refresh:
        return json.loads(cache_path.read_text())

    evidence = topic.get("evidence_quotes") or []
    evidence_block = "\n".join(f"- \"{q}\"" for q in evidence) or "(no quotes)"

    user_msg = f"""## Topic to explain

title: {title}
short: {topic.get('short', '')}

Verbatim evidence quotes from the transcript:
{evidence_block}

Write the full article per the system prompt. Return JSON with keys `topic_title`, `tl_dr`, `sections`, `word_count`."""

    data = call_llm_json(
        model=TOPIC_DEEP_DIVE_MODEL,
        system=D2_SYSTEM,
        user_msg=user_msg,
        max_tokens=8192,
        temperature=0.4,
    )

    data.setdefault("topic_title", title)
    cache_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return data


def run_d2(d1_output: dict, cache_dir: Path, force_refresh: bool = False) -> dict:
    """Run D2 for every topic in a D1 output and collate articles.

    De-duplicates by slug(title) within this run so the same topic doesn't
    get re-generated within the same video.
    """
    seen: dict[str, dict] = {}
    for topic in d1_output.get("topics", []):
        title = topic.get("title", "").strip()
        if not title:
            continue
        slug = _slugify(title)
        if slug in seen:
            continue
        try:
            article = deep_dive_for_topic(topic, cache_dir, force_refresh)
            seen[slug] = article
        except Exception as e:
            print(f"  D2 error for topic '{title}': {e}")

    return {
        "video_id": d1_output.get("video_id", ""),
        "url": d1_output.get("url", ""),
        "title": d1_output.get("title", ""),
        "articles": list(seen.values()),
    }
