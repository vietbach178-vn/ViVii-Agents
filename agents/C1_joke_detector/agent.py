"""C1 — Joke Detector agent.

Takes a full transcript (list of sentences with timing) and returns nested topic blocks,
each containing punchlines. Uses one LLM call for the entire transcript.
"""

from config import JOKE_DETECTOR_MODEL
from llm_utils import call_llm_json
from agents.C1_joke_detector.prompt import JOKE_DETECTOR_SYSTEM


def _format_transcript(sentences: list) -> str:
    lines = []
    for idx, s in enumerate(sentences):
        lines.append(f"[{idx}] ({s['start']:.2f}s - {s['end']:.2f}s) {s['text']}")
    return "\n".join(lines)


def run_joke_detector(transcript: dict) -> dict:
    """Detect topic blocks + nested punchlines in a transcript.

    Args:
        transcript: dict with keys `video_id`, `sentences`. Each sentence has
            `start`, `end`, `text`.

    Returns:
        dict: {video_id, topic_blocks: [...]} matching the C1 schema.
    """
    sentences = transcript["sentences"]
    transcript_text = _format_transcript(sentences)

    user_msg = f"""## Stand-up transcript ({len(sentences)} sentences)

Each line below is: `[sentence_idx] (start_sec - end_sec) text`.

{transcript_text}

Return JSON with the `topic_blocks` array described in the system prompt."""

    data = call_llm_json(
        model=JOKE_DETECTOR_MODEL,
        system=JOKE_DETECTOR_SYSTEM,
        user_msg=user_msg,
        max_tokens=8192,
        temperature=0.2,
    )

    if "topic_blocks" not in data:
        data = {"topic_blocks": data if isinstance(data, list) else []}

    return {
        "video_id": transcript.get("video_id", ""),
        "url": transcript.get("url", ""),
        "title": transcript.get("title", ""),
        "topic_blocks": data["topic_blocks"],
    }
