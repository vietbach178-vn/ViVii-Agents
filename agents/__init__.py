"""Sub-agents for the Rich Point Discovery pipeline.

Each sub-agent lives in its own subfolder with:
- prompt.py — system prompt for that agent only
- agent.py  — logic that calls the LLM with that prompt
"""

from agents.splitter import split_sentences_with_llm
from agents.scanner import scan_all_chunks
from agents.level1 import run_level1
from agents.level2 import run_level2
from agents.joke import run_joke_agent
from agents.exercise_builder import run_exercise_builder

__all__ = [
    "split_sentences_with_llm",
    "scan_all_chunks",
    "run_level1",
    "run_level2",
    "run_joke_agent",
    "run_exercise_builder",
]
