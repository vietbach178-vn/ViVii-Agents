"""C3 — Comprehension MCQ agent.

For each bit in C2's tier_2_bits, generate one 3-option MCQ that tests
whether the student understands why that bit is funny. Code shuffles
A/B/C position after LLM call so the correct letter is randomized.
"""

import json
import random

from config import JOKE_EXPLAINER_MODEL
from llm_utils import call_llm_json
from agents.C3_comprehension_mcq.prompt import C3_SYSTEM


def _mcq_for_bit(bit: dict, topic_label: str) -> dict:
    """Generate one MCQ for a single bit."""
    user_msg = f"""## Topic context
{topic_label}

## Bit to quiz (from C2.tier_2_bits)
{json.dumps(bit, indent=2, ensure_ascii=False)}

Generate ONE 3-option MCQ. Return JSON with keys `question`, `options`, `correct`, `explanation`."""

    data = call_llm_json(
        model=JOKE_EXPLAINER_MODEL,
        system=C3_SYSTEM,
        user_msg=user_msg,
        max_tokens=1024,
        temperature=0.6,
    )
    return _shuffle_correct_position(data)


def _shuffle_correct_position(mcq: dict) -> dict:
    """Randomize which letter holds the correct answer.

    LLM can bias toward always putting correct at B. Shuffle so downstream
    students cannot game the pattern.
    """
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


def mcqs_for_block(c2_block: dict) -> dict:
    """Generate 1 MCQ per bit in a single C2 topic block."""
    topic_label = c2_block.get("tier_1_topic", {}).get("topic_label", "")
    bits = c2_block.get("tier_2_bits", []) or []

    mcqs = []
    for bit in bits:
        try:
            mcq = _mcq_for_bit(bit, topic_label)
            mcq["bit_id"] = bit.get("bit_id", "")
            mcqs.append(mcq)
        except Exception as e:
            print(f"  C3 error for bit {bit.get('bit_id', '?')}: {e}")

    return {"id": c2_block.get("id", ""), "mcqs": mcqs}


def run_c3(c2_output: dict) -> dict:
    """Run C3 on every topic block in a C2 output and collate."""
    results = [mcqs_for_block(block) for block in c2_output.get("explanations", [])]
    return {
        "video_id": c2_output.get("video_id", ""),
        "url": c2_output.get("url", ""),
        "title": c2_output.get("title", ""),
        "mcqs_per_block": results,
    }
