"""Fetch YouTube transcript with timestamps."""

from __future__ import annotations

import re
from typing import Optional, List, Dict
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:youtube\.com/watch\?v=)([^&\s]+)',
        r'(?:youtu\.be/)([^?\s]+)',
        r'(?:youtube\.com/embed/)([^?\s]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_transcript(url: str) -> Dict:
    """Fetch transcript for a YouTube video.

    Returns dict with:
        - segments: list of {text, start, duration}
        - full_text: concatenated transcript
        - word_count: total words
    """
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from: {url}")

    api = YouTubeTranscriptApi()
    result = api.fetch(video_id)

    # Convert snippets to simple dicts
    segments = [
        {"text": s.text, "start": s.start, "duration": s.duration}
        for s in result.snippets
    ]

    full_text = " ".join(seg["text"] for seg in segments)
    word_count = len(full_text.split())

    # Build sentences from segments (heuristic merge + LLM split)
    from chunker import segments_to_sentences
    from agents.splitter import split_sentences_with_llm
    raw_sentences = segments_to_sentences(segments)
    print(f"  Raw sentences: {len(raw_sentences)}")
    sentences = split_sentences_with_llm(raw_sentences)
    print(f"  After LLM split: {len(sentences)}")

    return {
        "video_id": video_id,
        "url": url,
        "segments": segments,
        "sentences": sentences,
        "full_text": full_text,
        "word_count": word_count,
    }
