"""Joke Explainer agent — explains all jokes/bits in standup comedy transcripts."""

import time

from config import JOKE_MODEL
from schemas import JokeOutput, JokeBlock
from llm_utils import call_llm_json
from agents.joke.prompt import JOKE_SYSTEM


def run_joke_agent(sentences: list, level1_rich_points: list) -> JokeOutput:
    """Analyze full transcript for jokes. Processes in batches for long transcripts."""

    transcript_lines = []
    for s in sentences:
        mins = int(s["start"] // 60)
        secs = int(s["start"] % 60)
        transcript_lines.append(f"[{mins:02d}:{secs:02d}] {s['text']}")
    transcript_text = "\n".join(transcript_lines)

    rp_summary = ""
    if level1_rich_points:
        rp_items = [f"- {p.get('word', '')}: {p.get('definition', '')}" for p in level1_rich_points]
        rp_summary = "\n## Rich points found in this video (for context):\n" + "\n".join(rp_items)

    words = transcript_text.split()
    BATCH_WORDS = 3000
    all_jokes = []

    if len(words) <= BATCH_WORDS:
        batches = [transcript_text]
    else:
        batches = []
        current_batch = []
        current_words = 0
        for line in transcript_lines:
            line_words = len(line.split())
            if current_words + line_words > BATCH_WORDS and current_batch:
                batches.append("\n".join(current_batch))
                current_batch = []
                current_words = 0
            current_batch.append(line)
            current_words += line_words
        if current_batch:
            batches.append("\n".join(current_batch))

    for i, batch in enumerate(batches):
        if i > 0:
            time.sleep(5)

        user_msg = f"""## Standup comedy transcript (part {i+1}/{len(batches)}):
{batch}
{rp_summary}

Analyze every joke and comedic moment. Return JSON with key "jokes" containing an array."""

        try:
            data = call_llm_json(
                model=JOKE_MODEL,
                system=JOKE_SYSTEM,
                user_msg=user_msg,
                max_tokens=8192,
            )
            if "jokes" not in data:
                data = {"jokes": data if isinstance(data, list) else []}
            batch_result = JokeOutput(**data)
            all_jokes.extend([j.model_dump() for j in batch_result.jokes])
        except Exception as e:
            print(f"  Joke agent error (batch {i+1}): {e}")

    return JokeOutput(jokes=[JokeBlock(**j) for j in all_jokes])
