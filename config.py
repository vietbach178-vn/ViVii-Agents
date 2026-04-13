import os

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Primary model — best quality
PRIMARY_MODEL = "llama-3.3-70b-versatile"

# Fallback models — used when primary hits rate limit
FALLBACK_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "llama-3.1-8b-instant",
]

SPLITTER_MODEL = PRIMARY_MODEL
SCANNER_MODEL = PRIMARY_MODEL
LEVEL1_MODEL = PRIMARY_MODEL
LEVEL2_MODEL = PRIMARY_MODEL
JOKE_MODEL = PRIMARY_MODEL

CHUNK_SIZE = 4000  # words per chunk
CHUNK_OVERLAP = 200  # overlap words at boundaries

MAX_CONCURRENT_VIDEOS = 10
MAX_CONCURRENT_API_CALLS = 20
