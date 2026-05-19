"""Config for the pipeline: A-series (transcript) + B-series (rich points) + D-series (topics).

Uses Groq with Llama models. Override via env vars.
"""

import os

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# --- A-series: shared preprocessing ---
SPLITTER_MODEL = os.environ.get(
    "SPLITTER_MODEL", "llama-3.3-70b-versatile"
)

# --- B-series: Rich Point Discovery ---
SCANNER_MODEL = os.environ.get(
    "SCANNER_MODEL", "llama-3.3-70b-versatile"
)
LEVEL1_MODEL = os.environ.get(
    "LEVEL1_MODEL", "llama-3.3-70b-versatile"
)
LEVEL2_MODEL = os.environ.get(
    "LEVEL2_MODEL", "llama-3.3-70b-versatile"
)

# --- D-series: Cultural Topics ---
TOPIC_DETECTOR_MODEL = os.environ.get(
    "TOPIC_DETECTOR_MODEL", "openai/gpt-oss-120b"
)
TOPIC_DEEP_DIVE_MODEL = os.environ.get(
    "TOPIC_DEEP_DIVE_MODEL", "llama-3.3-70b-versatile"
)

FALLBACK_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "llama-3.1-8b-instant",
]

# --- Chunking ---
CHUNK_MAX_WORDS = int(os.environ.get("CHUNK_MAX_WORDS", "4000"))
