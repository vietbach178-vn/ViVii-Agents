"""Chunk sentences into ~4K-word groups for the Scanner agent.

Never cuts mid-sentence.
"""

from config import CHUNK_MAX_WORDS


def sentences_to_chunks(sentences: list, max_words: int = None) -> list:
    """Group sentences into chunks of approximately max_words words.

    Returns list of dicts: { text, start_idx, end_idx, word_count }.
    """
    if max_words is None:
        max_words = CHUNK_MAX_WORDS

    chunks = []
    buf_sentences = []
    buf_words = 0
    start_idx = 0

    for i, sent in enumerate(sentences):
        wc = len(sent["text"].split())

        if buf_words + wc > max_words and buf_sentences:
            chunks.append({
                "text": " ".join(s["text"] for s in buf_sentences),
                "start_idx": start_idx,
                "end_idx": i - 1,
                "word_count": buf_words,
            })
            buf_sentences = []
            buf_words = 0
            start_idx = i

        buf_sentences.append(sent)
        buf_words += wc

    if buf_sentences:
        chunks.append({
            "text": " ".join(s["text"] for s in buf_sentences),
            "start_idx": start_idx,
            "end_idx": len(sentences) - 1,
            "word_count": buf_words,
        })

    return chunks
