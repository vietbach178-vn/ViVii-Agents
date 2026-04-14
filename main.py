"""Main entry point — orchestrate the full rich point discovery pipeline."""

import sys
import os
from pathlib import Path

# Add project dir to path
sys.path.insert(0, str(Path(__file__).parent))

from transcript import fetch_transcript
from chunker import sentences_to_chunks
from agents import (
    scan_all_chunks,
    run_level1,
    run_level2,
    run_joke_agent,
    run_exercise_builder,
)
from aggregator import merge_levels, generate_markdown


def process_video(url: str) -> str:
    """Run the full pipeline for a single video. Returns markdown report."""

    # Stage 1: Fetch transcript
    print(f"\n{'='*60}")
    print(f"Processing: {url}")
    print(f"{'='*60}")

    print("\n[1/6] Fetching transcript...")
    data = fetch_transcript(url)
    print(f"  Transcript: {data['word_count']:,} words")

    # Stage 2: Chunk + scan
    print("\n[2/6] Scanning for rich point candidates...")
    print(f"  Merged into {len(data['sentences'])} sentence(s)")
    chunks = sentences_to_chunks(data["sentences"])
    print(f"  Split into {len(chunks)} chunk(s)")

    candidates = scan_all_chunks(chunks, data["full_text"])
    print(f"  Found {len(candidates)} candidate(s)")

    if not candidates:
        print("  No rich points found.")
        return f"# No rich points found\n\nVideo: {url}\nTranscript: {data['word_count']:,} words\n"

    for c in candidates:
        print(f"    - {c['word']} ({c['sense_tag']}, agar: {c['agar_score']})")

    # Stage 3: Level 1 — understand the word (batch to avoid rate limits)
    print("\n[3/6] Level 1: Generating definitions & context...")
    import time
    BATCH_SIZE = 3
    all_l1_points = []
    for i in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[i:i + BATCH_SIZE]
        batch_names = [c["word"] for c in batch]
        print(f"  Batch {i // BATCH_SIZE + 1}: {', '.join(batch_names)}")
        if i > 0:
            time.sleep(10)  # wait for Groq rate limit reset
        l1_result = run_level1(batch, data["full_text"], data["sentences"])
        all_l1_points.extend([p.model_dump() for p in l1_result.rich_points])
    l1_points = all_l1_points
    print(f"  Level 1 validated: {len(l1_points)} rich point(s)")

    # Stage 4: Level 2 + Joke Agent (sequential due to rate limits)
    print("\n[4/6] Level 2: Deep cultural analysis...")
    all_l2_points = []
    for i in range(0, len(l1_points), BATCH_SIZE):
        batch = l1_points[i:i + BATCH_SIZE]
        batch_names = [p["word"] for p in batch]
        print(f"  Batch {i // BATCH_SIZE + 1}: {', '.join(batch_names)}")
        if i > 0:
            time.sleep(10)
        l2_result = run_level2(batch)
        all_l2_points.extend([p.model_dump() for p in l2_result.rich_points])
    l2_points = all_l2_points

    print("\n[5/6] Joke Agent: Explaining jokes...")
    joke_result = run_joke_agent(data["sentences"], l1_points)
    jokes = [j.model_dump() for j in joke_result.jokes]
    print(f"  Found {len(jokes)} joke(s)")

    # Stage 6: Exercise Builder — graduated MCQs for jokes tagged with dark humor mechanisms
    print("\n[6/6] Exercise Builder: Generating dark humor practice exercises...")
    exercise_set = run_exercise_builder(joke_result)
    exercises = [e.model_dump() for e in exercise_set.exercises]

    # Merge and generate output
    merged = merge_levels(l1_points, l2_points)
    markdown = generate_markdown(url, data["word_count"], merged, jokes, exercises)

    return markdown


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <youtube-url> [output-file]")
        print("  youtube-url  — YouTube video URL")
        print("  output-file  — Optional output path (default: result.md)")
        sys.exit(1)

    url = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "result.md"

    if not os.environ.get("GROQ_API_KEY"):
        print("Error: GROQ_API_KEY environment variable not set.")
        sys.exit(1)

    report = process_video(url)

    # Save to file
    output_file = Path(__file__).parent / output_path
    output_file.write_text(report, encoding="utf-8")
    print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    main()
