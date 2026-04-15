"""C4 — Transfer Practice MCQ agent.

Has two modes:
  - STAMP mode: each canonical stamp from D1 → one 3-option MCQ testing
    recognition of that stamp in a new context.
  - TOPIC fallback mode: when D1 returned no stamps for a block, fall back
    to C2's tier_1_topic.topic_label and generate one topic-level MCQ.

Input per block: (d1_block, c2_block).
"""

import json
import random

from config import JOKE_EXPLAINER_MODEL
from llm_utils import call_llm_json
from agents.C4_transfer_practice.prompt import C4_STAMP_SYSTEM, C4_TOPIC_SYSTEM


def _shuffle_correct_position(mcq: dict) -> dict:
    """Randomize which letter holds the correct answer."""
    options = mcq.get("options") or {}
    correct_letter = mcq.get("correct", "A")
    if not options or correct_letter not in options:
        return mcq

    correct_text = options[correct_letter]
    wrong_texts = [options[k] for k in ("A", "B", "C") if k != correct_letter and k in options]
    if len(wrong_texts) != 2:
        return mcq

    letters = ["A", "B", "C"]
    new_correct = random.choice(letters)
    wrongs_iter = iter(wrong_texts)
    new_options = {}
    for letter in letters:
        if letter == new_correct:
            new_options[letter] = correct_text
        else:
            new_options[letter] = next(wrongs_iter)

    mcq["options"] = new_options
    mcq["correct"] = new_correct
    return mcq


def _stamp_mode_mcq(stamp: dict, c2_block: dict) -> dict:
    """Generate one MCQ in stamp mode."""
    user_msg = f"""## Target stamp
canonical_name: {stamp.get('canonical_name', '')}
category: {stamp.get('category', '')}
evidence: {stamp.get('evidence', '')}

## Original joke context (C2 tier_1_topic, for grounding only — do NOT quote)
{json.dumps(c2_block.get('tier_1_topic', {}), indent=2, ensure_ascii=False)}

Generate ONE stamp-mode transfer MCQ. Return JSON."""

    data = call_llm_json(
        model=JOKE_EXPLAINER_MODEL,
        system=C4_STAMP_SYSTEM,
        user_msg=user_msg,
        max_tokens=1024,
        temperature=0.7,
    )
    data.setdefault("stamp_canonical_name", stamp.get("canonical_name", ""))
    data.setdefault("mode", "stamp")
    return _shuffle_correct_position(data)


def _topic_mode_mcq(c2_block: dict) -> dict:
    """Generate one MCQ in topic fallback mode."""
    tier_1 = c2_block.get("tier_1_topic", {}) or {}
    topic_label = tier_1.get("topic_label", "")
    user_msg = f"""## Topic (fallback — no stamps detected)
topic_label: {topic_label}
topic_summary: {tier_1.get('topic_summary', '')}
cultural_domain: {tier_1.get('cultural_domain', '')}

Generate ONE topic-mode transfer MCQ. Return JSON."""

    data = call_llm_json(
        model=JOKE_EXPLAINER_MODEL,
        system=C4_TOPIC_SYSTEM,
        user_msg=user_msg,
        max_tokens=1024,
        temperature=0.7,
    )
    data.setdefault("topic_label", topic_label)
    data.setdefault("mode", "topic")
    return _shuffle_correct_position(data)


def transfer_mcqs_for_block(d1_block: dict, c2_block: dict) -> dict:
    """Generate transfer MCQs for one block.

    Stamp mode: one MCQ per stamp.
    Topic mode: one MCQ when D1 returned no stamps.
    """
    stamps = d1_block.get("stamps", []) or []
    mcqs = []

    if stamps:
        for stamp in stamps:
            try:
                mcqs.append(_stamp_mode_mcq(stamp, c2_block))
            except Exception as e:
                print(f"  C4 stamp-mode error for '{stamp.get('canonical_name', '?')}': {e}")
    else:
        try:
            mcqs.append(_topic_mode_mcq(c2_block))
        except Exception as e:
            print(f"  C4 topic-mode error for block {c2_block.get('id', '?')}: {e}")

    return {"id": c2_block.get("id", ""), "mcqs": mcqs}


def run_c4(c2_output: dict, d1_output: dict) -> dict:
    """Run C4 on every topic block, matching C2 blocks with D1 blocks by id."""
    d1_by_id = {b.get("id", ""): b for b in d1_output.get("stamps_per_block", [])}

    results = []
    for c2_block in c2_output.get("explanations", []):
        block_id = c2_block.get("id", "")
        d1_block = d1_by_id.get(block_id, {"id": block_id, "stamps": []})
        results.append(transfer_mcqs_for_block(d1_block, c2_block))

    return {
        "video_id": c2_output.get("video_id", ""),
        "url": c2_output.get("url", ""),
        "title": c2_output.get("title", ""),
        "mcqs_per_block": results,
    }
