"""Exercise Builder — 5-node workflow.

This is a Workflow (not an Agent). Control flow is code-driven, LLMs only
handle individual node tasks. Patterns used:
  - Prompt Chaining (Node 1 -> 2 -> ... -> 5)
  - Parallelization / Sectioning (one MCQ per mechanism, independent)
  - Evaluator-Optimizer (Node 2 <-> Node 3 loop, up to MAX_RETRIES)

Node map:
  1. Parse & Route         (code — skip non-dark, expand mechanisms)
  2. Generate MCQ          (LLM — graduated A/B/C)
  3. Evaluator Check       (LLM — 4-criteria pass/fail)
  4. Explanation           (LLM — why C lands, why B misses, takeaway)
  5. Aggregate & Return    (code — shuffle C position, assemble output)
"""

import random
import time

from config import JOKE_MODEL
from schemas import (
    JokeOutput,
    Exercise,
    ExerciseOptions,
    ExerciseExplanation,
    ExerciseSet,
)
from llm_utils import call_llm_json
from agents.joke.mechanism_rubric import MECHANISM_IDS
from agents.exercise_builder.prompts import (
    GENERATE_SYSTEM,
    EVALUATE_SYSTEM,
    EXPLAIN_SYSTEM,
)


MAX_EVAL_RETRIES = 2
INTER_CALL_SLEEP = 2  # seconds between LLM calls (Groq rate limit buffer)


# ---------- Node 1: Parse & Route ----------

def _parse_and_route(jokes: list[dict]) -> list[tuple[dict, str]]:
    """Return a flat list of (joke, mechanism) pairs to generate exercises for.

    Skips jokes that:
      - have empty mechanisms list (not dark humor)
      - carry taboo_intensity == 'extreme' (red line — don't teach these)
      - contain any unknown mechanism tag (drift protection)
    """
    pairs = []
    valid_mechanisms = set(MECHANISM_IDS)

    for joke in jokes:
        mechanisms = joke.get("mechanisms") or []
        intensity = (joke.get("taboo_intensity") or "").lower()

        if not mechanisms:
            continue
        if intensity == "extreme":
            continue

        for m in mechanisms:
            if m in valid_mechanisms:
                pairs.append((joke, m))

    return pairs


# ---------- Node 2: Generate MCQ ----------

def _generate_mcq(joke: dict, mechanism: str) -> dict:
    """Ask the LLM to produce a graduated MCQ for one joke + mechanism."""
    user_msg = f"""## Source joke
Transcript excerpt: {joke.get('transcript_excerpt', '')}
Explanation: {joke.get('explanation', '')}
Joke type: {joke.get('joke_type', '')}
Taboo intensity: {joke.get('taboo_intensity', '')}

## Target mechanism
{mechanism}

Generate one graduated MCQ (question + A/B/C)."""

    return call_llm_json(
        model=JOKE_MODEL,
        system=GENERATE_SYSTEM,
        user_msg=user_msg,
        max_tokens=1024,
        temperature=0.7,
    )


# ---------- Node 3: Evaluator Check ----------

def _evaluate_mcq(mcq: dict, mechanism: str) -> dict:
    """Evaluator Agent checks 4 criteria. Returns dict with *_pass flags + overall_pass."""
    user_msg = f"""## Target mechanism
{mechanism}

## Exercise under review
Question: {mcq.get('question', '')}
Option A (should be: no humor attempt, plain reaction): {mcq.get('option_a', '')}
Option B (should be: weak attempt at mechanism): {mcq.get('option_b', '')}
Option C (should be: mechanism landed fully): {mcq.get('option_c', '')}

Evaluate against the 4 criteria."""

    return call_llm_json(
        model=JOKE_MODEL,
        system=EVALUATE_SYSTEM,
        user_msg=user_msg,
        max_tokens=512,
        temperature=0.1,
    )


# ---------- Node 4: Explanation ----------

def _generate_explanation(mcq: dict, mechanism: str) -> dict:
    """Write the post-answer explanation for the student."""
    user_msg = f"""## Target mechanism
{mechanism}

## Exercise
Question: {mcq.get('question', '')}
Option A: {mcq.get('option_a', '')}
Option B: {mcq.get('option_b', '')}
Option C (correct, funniest): {mcq.get('option_c', '')}

Write the explanation (why_c_lands, why_b_misses, pattern_takeaway)."""

    return call_llm_json(
        model=JOKE_MODEL,
        system=EXPLAIN_SYSTEM,
        user_msg=user_msg,
        max_tokens=512,
        temperature=0.3,
    )


# ---------- Node 5: Aggregate, shuffle C position ----------

def _build_exercise(
    joke: dict, mechanism: str, mcq: dict, explanation: dict
) -> Exercise:
    """Shuffle the correct answer position and return a validated Exercise."""
    # Preserve mapping of semantic roles (miss, almost, land) to the shuffled letters.
    semantic = {
        "miss": mcq.get("option_a", ""),
        "almost": mcq.get("option_b", ""),
        "land": mcq.get("option_c", ""),
    }

    positions = ["A", "B", "C"]
    roles = ["miss", "almost", "land"]
    random.shuffle(positions)

    letter_by_role = dict(zip(roles, positions))
    options = {letter_by_role[r]: semantic[r] for r in roles}
    correct_letter = letter_by_role["land"]

    return Exercise(
        source_joke_timestamp=float(joke.get("timestamp") or 0.0),
        mechanism=mechanism,
        question=mcq.get("question", ""),
        options=ExerciseOptions(
            A=options.get("A", ""),
            B=options.get("B", ""),
            C=options.get("C", ""),
        ),
        correct=correct_letter,
        explanation=ExerciseExplanation(
            why_c_lands=explanation.get("why_c_lands", ""),
            why_b_misses=explanation.get("why_b_misses", ""),
            pattern_takeaway=explanation.get("pattern_takeaway", ""),
        ),
    )


# ---------- Orchestration: single pair, with retry loop ----------

def _process_pair(joke: dict, mechanism: str) -> Exercise | None:
    """Run Generate -> Evaluate (with retry) -> Explain for one pair."""
    mcq = None
    for attempt in range(MAX_EVAL_RETRIES + 1):
        try:
            mcq = _generate_mcq(joke, mechanism)
            time.sleep(INTER_CALL_SLEEP)
            eval_result = _evaluate_mcq(mcq, mechanism)
        except Exception as e:
            print(f"    Exercise Builder error (generate/eval, attempt {attempt + 1}): {e}")
            time.sleep(INTER_CALL_SLEEP)
            continue

        if eval_result.get("overall_pass"):
            break

        reasons = eval_result.get("reasons", "(no reason)")
        print(f"    Evaluator rejected (attempt {attempt + 1}): {reasons}")
        time.sleep(INTER_CALL_SLEEP)
    else:
        # all retries exhausted without pass
        return None

    if mcq is None:
        return None

    try:
        explanation = _generate_explanation(mcq, mechanism)
    except Exception as e:
        print(f"    Exercise Builder error (explain): {e}")
        return None

    return _build_exercise(joke, mechanism, mcq, explanation)


# ---------- Public entry point ----------

def run_exercise_builder(joke_output: JokeOutput) -> ExerciseSet:
    """Entry point. Take Joke Agent output, return list of graduated MCQ exercises.

    Returns empty ExerciseSet if the video has no dark-humor jokes tagged with
    at least one of the 5 core mechanisms.
    """
    jokes = [j.model_dump() for j in joke_output.jokes]
    pairs = _parse_and_route(jokes)

    if not pairs:
        print("  No dark humor mechanisms tagged — skipping Exercise Builder.")
        return ExerciseSet(exercises=[])

    print(f"  {len(pairs)} (joke, mechanism) pair(s) to process")

    exercises = []
    for i, (joke, mechanism) in enumerate(pairs, 1):
        ts = joke.get("timestamp") or 0
        mins = int(ts // 60)
        secs = int(ts % 60)
        print(f"  [{i}/{len(pairs)}] {mechanism} @ {mins:02d}:{secs:02d}")

        if i > 1:
            time.sleep(INTER_CALL_SLEEP)

        ex = _process_pair(joke, mechanism)
        if ex is not None:
            exercises.append(ex)

        time.sleep(INTER_CALL_SLEEP)

    print(f"  Produced {len(exercises)} exercise(s) out of {len(pairs)} pair(s)")
    return ExerciseSet(exercises=exercises)
