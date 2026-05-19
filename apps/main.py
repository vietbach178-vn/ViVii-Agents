"""CLI runner for the Rich Point + Cultural Topic pipeline.

Pipeline:
    A-series (transcript) → B-series (rich points) and D-series (topics)
    B and D consume A's output independently — order is sequential here for
    simplicity; both branches always run.

Usage:
    cd apps
    PYTHONPATH=..:. python main.py <YouTube URL> [output_dir]

Writes (to output_dir, default `./output/<job_id>/`):
    job.json           — full result: rich_points, d1 (topics), d2 (articles)
    d2_articles/<slug>.json   — per-topic deep-dive, cached cross-video
"""

import json
import sys
import uuid
from pathlib import Path

from transcript import fetch_transcript
from chunker import sentences_to_chunks

from agents.A1_splitter import split_sentences_with_llm
from agents.B1_scanner import scan_all_chunks
from agents.B2_level1 import run_level1
from agents.B3_level2 import run_level2
from agents.D1_topic_detector import run_d1
from agents.D2_topic_deep_dive import run_d2


def run(url: str, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[A] Fetching transcript: {url}")
    transcript = fetch_transcript(url)
    sentences = transcript["sentences"]
    full_text = " ".join(s["text"] for s in sentences)
    print(f"[A] {len(sentences)} sentences, {transcript['word_count']} words")

    print(f"[A1] Splitting sentences with LLM...")
    split_sents = split_sentences_with_llm(sentences)
    transcript_for_d1 = {**transcript, "sentences": split_sents}

    print(f"[B1] Scanning for rich point candidates...")
    chunks = sentences_to_chunks(split_sents)
    candidates = scan_all_chunks(chunks, full_text)
    print(f"[B1] {len(candidates)} candidates")

    rich_points_merged = []
    if candidates:
        print(f"[B2] Level 1 analysis...")
        l1 = run_level1(candidates, full_text, split_sents)
        l1_dicts = [rp.model_dump() for rp in l1.rich_points]

        print(f"[B3] Level 2 deep analysis...")
        l2 = run_level2(l1_dicts)
        l2_map = {rp.word.lower(): rp.model_dump() for rp in l2.rich_points}

        for rp in l1_dicts:
            merged = {**rp}
            deep = l2_map.get(rp["word"].lower(), {})
            merged.update({k: v for k, v in deep.items() if v})
            rich_points_merged.append(merged)
        print(f"[B] {len(rich_points_merged)} rich points")

    print(f"[D1] Detecting cultural topics...")
    d1_output = run_d1(transcript_for_d1)
    print(f"[D1] {len(d1_output.get('topics', []))} topics")

    print(f"[D2] Writing topic deep-dive articles (cached cross-video)...")
    d2_output = run_d2(d1_output, output_dir / "d2_articles")
    print(f"[D2] {len(d2_output.get('articles', []))} articles")

    result = {
        "url": url,
        "rich_points": rich_points_merged,
        "d1": d1_output,
        "d2": d2_output,
        "transcript": sentences,
        "word_count": transcript["word_count"],
    }
    (output_dir / "job.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str)
    )
    print(f"\nDone. Output -> {output_dir}/")
    return result


def main():
    if len(sys.argv) < 2:
        print("usage: python main.py <YouTube URL> [output_dir]")
        sys.exit(1)

    url = sys.argv[1]
    if len(sys.argv) >= 3:
        output_dir = Path(sys.argv[2])
    else:
        job_id = str(uuid.uuid4())[:8]
        output_dir = Path("output") / job_id

    run(url, output_dir)


if __name__ == "__main__":
    main()
