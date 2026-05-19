"""Fetch YouTube transcript via youtube-transcript-api.

Returns a dict matching the transcript format used by the joke pipeline:
  { video_id, url, title, word_count, sentence_count, sentences: [{text, start, end}, ...] }
"""

import re
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:embed/)([A-Za-z0-9_-]{11})",
        r"(?:shorts/)([A-Za-z0-9_-]{11})",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    cleaned = url.strip()
    if re.match(r"^[A-Za-z0-9_-]{11}$", cleaned):
        return cleaned
    raise ValueError(f"Cannot extract video ID from: {url}")


def fetch_transcript(url: str) -> dict:
    """Fetch transcript for a YouTube URL.

    Returns dict with keys: video_id, url, sentences, word_count, sentence_count.
    Each sentence has: text, start, end.
    """
    video_id = extract_video_id(url)
    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id)
    # Convert to list of dicts with text, start, duration.
    # YouTube captions often contain newlines within a segment — flatten them.
    segments = [
        {"text": " ".join(s.text.split()), "start": s.start, "duration": s.duration}
        for s in fetched
    ]

    sentences = _segments_to_sentences(segments)
    full_text = " ".join(s["text"] for s in sentences)
    word_count = len(full_text.split())

    return {
        "video_id": video_id,
        "url": url,
        "title": "",
        "word_count": word_count,
        "sentence_count": len(sentences),
        "sentences": sentences,
    }


def _segments_to_sentences(segments: list) -> list:
    """Merge small YouTube caption segments into sentence-level items.

    Heuristic: split on time gaps > 1s, sentence-ending punctuation,
    bracketed markers, or when accumulated text exceeds 80 words.
    """
    if not segments:
        return []

    sentences = []
    buf_texts = []
    buf_start = segments[0].get("start", 0.0)
    buf_end = segments[0].get("start", 0.0)

    for i, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        if not text:
            continue

        start = seg.get("start", 0.0)
        duration = seg.get("duration", 0.0)
        end = start + duration

        # Bracketed marker → standalone sentence
        if text.startswith("[") and text.endswith("]"):
            if buf_texts:
                sentences.append({
                    "text": " ".join(buf_texts),
                    "start": buf_start,
                    "end": buf_end,
                })
                buf_texts = []
            sentences.append({"text": text, "start": start, "end": end})
            if i + 1 < len(segments):
                buf_start = segments[i + 1].get("start", end)
            continue

        # Time gap > 1s → flush
        if buf_texts and (start - buf_end) > 1.0:
            sentences.append({
                "text": " ".join(buf_texts),
                "start": buf_start,
                "end": buf_end,
            })
            buf_texts = []
            buf_start = start

        buf_texts.append(text)
        buf_end = end

        # Sentence-ending punctuation
        if text and text[-1] in ".?!":
            sentences.append({
                "text": " ".join(buf_texts),
                "start": buf_start,
                "end": buf_end,
            })
            buf_texts = []
            if i + 1 < len(segments):
                buf_start = segments[i + 1].get("start", end)

        # Max 80 words → force split
        elif len(" ".join(buf_texts).split()) >= 80:
            sentences.append({
                "text": " ".join(buf_texts),
                "start": buf_start,
                "end": buf_end,
            })
            buf_texts = []
            if i + 1 < len(segments):
                buf_start = segments[i + 1].get("start", end)

    if buf_texts:
        sentences.append({
            "text": " ".join(buf_texts),
            "start": buf_start,
            "end": buf_end,
        })

    return sentences
