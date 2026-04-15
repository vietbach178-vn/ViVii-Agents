"""C2 — Joke Explainer agent.

For each topic block from C1, run one LLM call that receives the full transcript
(for callback context) + the focused block, and returns a structured explanation.
"""

from config import JOKE_EXPLAINER_MODEL
from llm_utils import call_llm_json
from agents.C2_joke_explainer.prompt import JOKE_EXPLAINER_SYSTEM


def _format_transcript(sentences: list) -> str:
    lines = []
    for idx, s in enumerate(sentences):
        lines.append(f"[{idx}] ({s['start']:.2f}s) {s['text']}")
    return "\n".join(lines)


def _format_block(block: dict) -> str:
    parts = [
        f"id: {block['id']}",
        f"title: {block['title']}",
        f"premise (C1): {block['premise']}",
        f"sentence range: [{block['start_sentence_idx']}..{block['end_sentence_idx']}]",
        f"time range: {block['start_sec']:.2f}s - {block['end_sec']:.2f}s",
        "punchlines detected by C1:",
    ]
    for p in block.get("punchlines", []):
        parts.append(
            f"  - sentences [{p['start_sentence_idx']}..{p['end_sentence_idx']}] "
            f"({p['start_sec']:.2f}s) hint: {p.get('text_hint', '')}"
        )
    return "\n".join(parts)


def run_joke_explainer(transcript: dict, topic_block: dict) -> dict:
    """Explain one topic block, with full transcript available as context.

    Args:
        transcript: full transcript dict (video_id, sentences, ...).
        topic_block: one topic block from C1 output.

    Returns:
        dict: matches the C2 per-block output schema.
    """
    sentences = transcript["sentences"]
    full_text = _format_transcript(sentences)
    block_text = _format_block(topic_block)

    user_msg = f"""## Full transcript (for callback/context detection)

{full_text}

## Target topic block to explain

{block_text}

Return JSON matching the C2 schema in the system prompt."""

    data = call_llm_json(
        model=JOKE_EXPLAINER_MODEL,
        system=JOKE_EXPLAINER_SYSTEM,
        user_msg=user_msg,
        max_tokens=4096,
        temperature=0.3,
    )

    data.setdefault("id", topic_block.get("id", ""))
    return data


def explain_all_blocks(transcript: dict, c1_output: dict) -> dict:
    """Run C2 on every topic block from C1 and collate."""
    results = []
    for block in c1_output.get("topic_blocks", []):
        explained = run_joke_explainer(transcript, block)
        results.append(explained)
    return {
        "video_id": transcript.get("video_id", ""),
        "url": transcript.get("url", ""),
        "title": transcript.get("title", ""),
        "explanations": results,
    }
