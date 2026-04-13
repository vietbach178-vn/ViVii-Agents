"""Level 2 agent — 'Deep analysis' (why rich point, misuse, origin, usage, related, rephrase)."""

import json

from config import LEVEL2_MODEL
from schemas import Level2Output
from llm_utils import call_llm_json
from agents.level2.prompt import LEVEL2_SYSTEM


def run_level2(level1_rich_points: list) -> Level2Output:
    """Run Level 2 deep analysis on validated rich points from Level 1."""

    user_msg = f"""## Rich points from Level 1 (with definitions and context):
{json.dumps(level1_rich_points, indent=2)}

Provide deep cultural analysis for each rich point above.
Return JSON with key "rich_points" containing an array of objects."""

    data = call_llm_json(
        model=LEVEL2_MODEL,
        system=LEVEL2_SYSTEM,
        user_msg=user_msg,
        max_tokens=8192,
    )
    if "rich_points" not in data:
        data = {"rich_points": data if isinstance(data, list) else []}
    return Level2Output(**data)
