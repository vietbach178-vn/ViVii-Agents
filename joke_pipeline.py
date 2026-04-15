"""CLI runner for the C+D joke pipeline.

Pipeline:
    C1 (detector) → C2 (explainer, 2-tier) ┬→ C3 (comprehension MCQ per bit)
                                            └→ D1 (stamp detector, canonicalized)
                                                  ├→ D2 (stamp deep-dive, cached)
                                                  └→ C4 (transfer MCQ, stamp or topic mode)

Usage:
    python joke_pipeline.py <transcript.json> <output_dir>

Writes:
    <output_dir>/c1_output.json
    <output_dir>/c2_output.json
    <output_dir>/c3_output.json
    <output_dir>/c4_output.json
    <output_dir>/d1_output.json
    <output_dir>/d2_output.json
    <output_dir>/d2_articles/<slug>.json   (cache, shared across runs)
"""

import json
import sys
from pathlib import Path

from agents.C1_joke_detector import run_joke_detector
from agents.C2_joke_explainer.agent import explain_all_blocks
from agents.C3_comprehension_mcq import run_c3
from agents.C4_transfer_practice import run_c4
from agents.D1_stamp_detector import run_d1
from agents.D2_stamp_deep_dive import run_d2


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    if len(sys.argv) != 3:
        print("usage: python joke_pipeline.py <transcript.json> <output_dir>")
        sys.exit(1)

    transcript_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)

    transcript = json.loads(transcript_path.read_text())

    print(f"[C1] Detecting topic blocks in {transcript_path.name}...")
    c1_output = run_joke_detector(transcript)
    _write_json(output_dir / "c1_output.json", c1_output)
    print(f"[C1] {len(c1_output['topic_blocks'])} blocks")

    print(f"[C2] Explaining each block (2-tier output)...")
    c2_output = explain_all_blocks(transcript, c1_output)
    _write_json(output_dir / "c2_output.json", c2_output)
    print(f"[C2] {len(c2_output['explanations'])} explanations")

    print(f"[C3] Generating comprehension MCQs (1 per bit)...")
    c3_output = run_c3(c2_output)
    _write_json(output_dir / "c3_output.json", c3_output)
    total_c3 = sum(len(b.get("mcqs", [])) for b in c3_output.get("mcqs_per_block", []))
    print(f"[C3] {total_c3} MCQs across {len(c3_output['mcqs_per_block'])} blocks")

    print(f"[D1] Detecting culture stamps + canonicalizing...")
    d1_output = run_d1(c2_output)
    _write_json(output_dir / "d1_output.json", d1_output)
    total_stamps = sum(len(b.get("stamps", [])) for b in d1_output.get("stamps_per_block", []))
    print(f"[D1] {total_stamps} stamps across {len(d1_output['stamps_per_block'])} blocks")

    print(f"[D2] Writing stamp deep-dive articles (with cache)...")
    d2_cache_dir = output_dir / "d2_articles"
    d2_output = run_d2(d1_output, d2_cache_dir)
    _write_json(output_dir / "d2_output.json", d2_output)
    print(f"[D2] {len(d2_output['articles'])} unique articles -> {d2_cache_dir}")

    print(f"[C4] Generating transfer practice MCQs...")
    c4_output = run_c4(c2_output, d1_output)
    _write_json(output_dir / "c4_output.json", c4_output)
    total_c4 = sum(len(b.get("mcqs", [])) for b in c4_output.get("mcqs_per_block", []))
    print(f"[C4] {total_c4} transfer MCQs across {len(c4_output['mcqs_per_block'])} blocks")

    print(f"\nDone. Output -> {output_dir}")


if __name__ == "__main__":
    main()
