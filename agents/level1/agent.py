"""Level 1 agent — 'Understand the word' (definition, context meaning, timestamp)."""

import json

from config import LEVEL1_MODEL
from schemas import Level1Output
from llm_utils import call_llm_json
from agents.level1.prompt import LEVEL1_SYSTEM


def run_level1(candidates: list, transcript_text: str, sentences: list) -> Level1Output:
    """Run Level 1 analysis on all candidates for a single video."""

    candidate_words = [c["word"].lower() for c in candidates]
    relevant = _extract_relevant_sentences(sentences, candidate_words)

    user_msg = f"""## Candidate rich points found in this video:
{json.dumps(candidates, indent=2)}

## Relevant transcript excerpts with timestamps:
{relevant}

Return JSON with key "rich_points" containing an array of objects."""

    data = call_llm_json(
        model=LEVEL1_MODEL,
        system=LEVEL1_SYSTEM,
        user_msg=user_msg,
        max_tokens=8192,
    )
    if "rich_points" not in data:
        data = {"rich_points": data if isinstance(data, list) else []}
    return Level1Output(**data)


def _extract_relevant_sentences(sentences: list, candidate_words: list) -> str:
    """Extract sentences containing candidate words, with 1 sentence context."""
    relevant_indices = set()

    for i, sent in enumerate(sentences):
        text_lower = sent["text"].lower()
        for word in candidate_words:
            if word in text_lower:
                for j in range(max(0, i - 1), min(len(sentences), i + 2)):
                    relevant_indices.add(j)

    lines = []
    prev_idx = -2
    for idx in sorted(relevant_indices):
        if idx > prev_idx + 1:
            lines.append("...")
        sent = sentences[idx]
        mins = int(sent["start"] // 60)
        secs = int(sent["start"] % 60)
        lines.append(f"[{mins:02d}:{secs:02d}] {sent['text']}")
        prev_idx = idx

    return "\n".join(lines) if lines else "(no relevant sentences found)"
