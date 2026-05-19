"""D1 — Cultural Topic Detector agent.

One LLM call sees the full transcript and returns N cultural topics, each
grounded to a contiguous sentence range. No catalog, no canonicalization —
topics are free-form per video.
"""

import json

from config import TOPIC_DETECTOR_MODEL
from llm_utils import call_llm_json
from agents.D1_topic_detector.prompt import D1_SYSTEM


def _format_transcript(sentences: list) -> str:
    """Render sentences as `[idx] [mm:ss] text` lines for the prompt."""
    lines = []
    for i, sent in enumerate(sentences):
        start = sent.get("start", 0) or 0
        mins = int(start // 60)
        secs = int(start % 60)
        text = sent.get("text", "").strip()
        lines.append(f"[{i}] [{mins:02d}:{secs:02d}] {text}")
    return "\n".join(lines)


def _derive_time_range(topic: dict, sentences: list) -> list:
    """Backfill time_range from sentence_range if LLM omitted or mis-set it."""
    sr = topic.get("sentence_range") or []
    if len(sr) != 2 or not sentences:
        return topic.get("time_range") or [0, 0]
    start_idx = max(0, min(int(sr[0]), len(sentences) - 1))
    end_idx = max(0, min(int(sr[1]), len(sentences) - 1))
    start_sec = sentences[start_idx].get("start", 0) or 0
    end_sent = sentences[end_idx]
    end_sec = (end_sent.get("start", 0) or 0) + (end_sent.get("duration", 0) or 0)
    return [int(start_sec * 1000), int(end_sec * 1000)]


def run_d1(transcript: dict) -> dict:
    """Detect cultural topics across a full transcript in a single LLM call.

    Args:
        transcript: dict with `sentences` list (each: `{text, start, duration}`).

    Returns:
        dict with `video_id`, `url`, `title`, and `topics` list. Each topic has
        `title`, `short`, `sentence_range`, `time_range`, `confidence`, `evidence_quotes`.
    """
    sentences = transcript.get("sentences", [])
    user_msg = f"""## Full transcript (indexed sentences)

{_format_transcript(sentences)}

Return JSON with the `topics` array described in the system prompt."""

    data = call_llm_json(
        model=TOPIC_DETECTOR_MODEL,
        system=D1_SYSTEM,
        user_msg=user_msg,
        max_tokens=4096,
        temperature=0.2,
    )

    raw_topics = data.get("topics", []) if isinstance(data, dict) else []
    topics = []
    for t in raw_topics:
        title = (t.get("title") or "").strip()
        if not title:
            continue
        topics.append(
            {
                "title": title,
                "short": t.get("short", ""),
                "sentence_range": t.get("sentence_range") or [0, 0],
                "time_range": _derive_time_range(t, sentences),
                "confidence": float(t.get("confidence", 0.0) or 0.0),
                "evidence_quotes": t.get("evidence_quotes") or [],
            }
        )

    return {
        "video_id": transcript.get("video_id", ""),
        "url": transcript.get("url", ""),
        "title": transcript.get("title", ""),
        "topics": topics,
    }
