"""Pydantic models for structured output."""

from typing import Optional, List
from pydantic import BaseModel, field_validator


class _NoneCoerce(BaseModel):
    """Base model that coerces None to defaults."""

    @field_validator("*", mode="before")
    @classmethod
    def none_to_default(cls, v, info):
        if v is None:
            field = cls.model_fields[info.field_name]
            return field.default
        return v


# --- Scanner output ---

class CandidateRichPoint(_NoneCoerce):
    word: str = ""
    type: str = "word"
    pos: str = ""
    sense_tag: str = ""
    agar_score: int = 3


class ScannerOutput(BaseModel):
    candidates: List[CandidateRichPoint] = []


# --- Level 1 output ---

class Level1RichPoint(_NoneCoerce):
    word: str = ""
    type: str = "word"
    pos: str = ""
    sense_tag: str = ""
    definition: str = ""
    context_meaning: str = ""
    transcript_quote: str = ""
    timestamp_seconds: float = 0.0


class Level1Output(BaseModel):
    rich_points: List[Level1RichPoint] = []


# --- Level 2 output ---

class Level2RichPoint(_NoneCoerce):
    word: str = ""
    sense_tag: str = ""
    why_rich_point: str = ""
    misuse_consequence: str = ""
    origin_story: str = ""
    when_to_use: str = ""
    related_rich_points: List[str] = []
    outsider_rephrase: str = ""


class Level2Output(BaseModel):
    rich_points: List[Level2RichPoint] = []


# --- Joke output ---

class JokeBlock(_NoneCoerce):
    transcript_excerpt: str = ""
    timestamp: float = 0.0
    joke_type: str = ""
    explanation: str = ""
    cultural_context: str = ""

    @field_validator("transcript_excerpt", mode="before")
    @classmethod
    def coerce_excerpt(cls, v):
        if isinstance(v, list):
            return " ".join(str(x) for x in v)
        return v


class JokeOutput(BaseModel):
    jokes: List[JokeBlock] = []
