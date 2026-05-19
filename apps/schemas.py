"""Pydantic models for the rich point + topic pipeline.

Tolerant: coerce null → defaults so LLM output with missing fields doesn't crash.
"""

from typing import List
from pydantic import BaseModel, Field


# --- B-series schemas ---


class ScannerCandidate(BaseModel):
    word: str = ""
    type: str = ""
    pos: str = ""
    sense_tag: str = ""
    agar_score: int = 0


class ScannerOutput(BaseModel):
    candidates: List[ScannerCandidate] = Field(default_factory=list)


class Level1RichPoint(BaseModel):
    word: str = ""
    type: str = ""
    pos: str = ""
    sense_tag: str = ""
    definition: str = ""
    context_meaning: str = ""
    transcript_quote: str = ""
    timestamp_seconds: float = 0.0


class Level1Output(BaseModel):
    rich_points: List[Level1RichPoint] = Field(default_factory=list)


class Level2RichPoint(BaseModel):
    word: str = ""
    sense_tag: str = ""
    why_rich_point: str = ""
    misuse_consequence: str = ""
    origin_story: str = ""
    when_to_use: str = ""
    related_rich_points: List[str] = Field(default_factory=list)
    outsider_rephrase: str = ""


class Level2Output(BaseModel):
    rich_points: List[Level2RichPoint] = Field(default_factory=list)


# --- D-series schemas ---


class CulturalTopic(BaseModel):
    title: str = ""
    short: str = ""
    sentence_range: List[int] = Field(default_factory=lambda: [0, 0])
    time_range: List[int] = Field(default_factory=lambda: [0, 0])
    confidence: float = 0.0
    evidence_quotes: List[str] = Field(default_factory=list)


class TopicDetectorOutput(BaseModel):
    topics: List[CulturalTopic] = Field(default_factory=list)


class TopicArticleSections(BaseModel):
    historical_context: str = ""
    cultural_significance: str = ""
    common_misunderstandings: str = ""
    related_references: str = ""


class TopicArticle(BaseModel):
    topic_title: str = ""
    tl_dr: str = ""
    sections: TopicArticleSections = Field(default_factory=TopicArticleSections)
    word_count: int = 0
