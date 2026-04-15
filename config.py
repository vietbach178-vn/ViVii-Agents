"""Config for the A1 + A2 joke pipeline.

Standalone from the archived rich-point discovery project. Uses Groq (already installed
in .venv) with Llama models. Override via env vars.
"""

import os

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# A1 needs structural segmentation — a fast mid-size model is enough.
# A2 applies multi-theory analysis — use the strongest available model.
JOKE_DETECTOR_MODEL = os.environ.get(
    "JOKE_DETECTOR_MODEL", "llama-3.3-70b-versatile"
)
JOKE_EXPLAINER_MODEL = os.environ.get(
    "JOKE_EXPLAINER_MODEL", "llama-3.3-70b-versatile"
)

FALLBACK_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "llama-3.1-8b-instant",
]
