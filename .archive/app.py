"""Web UI for Rich Point Discovery."""

import sys
import os
import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, render_template, request, jsonify

from transcript import fetch_transcript
from chunker import sentences_to_chunks
from agents import (
    scan_all_chunks,
    run_level1,
    run_level2,
    run_joke_agent,
    run_exercise_builder,
)
from aggregator import merge_levels

app = Flask(__name__, template_folder="templates", static_folder="static")

# Job store — persisted to disk
JOBS_FILE = Path(__file__).parent / "jobs.json"
jobs = {}


def _load_jobs():
    """Load jobs from disk on startup."""
    global jobs
    if JOBS_FILE.exists():
        try:
            jobs = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
            print(f"Loaded {len(jobs)} job(s) from {JOBS_FILE}")
        except Exception as e:
            print(f"Warning: could not load jobs: {e}")
            jobs = {}


def _save_jobs():
    """Save jobs to disk."""
    try:
        JOBS_FILE.write_text(json.dumps(jobs, ensure_ascii=False, default=str), encoding="utf-8")
    except Exception as e:
        print(f"Warning: could not save jobs: {e}")


def process_video_job(job_id, url):
    """Run the full pipeline in a background thread, updating job status."""
    job = jobs[job_id]

    try:
        # Stage 1
        job["status"] = "fetching"
        job["message"] = "Fetching transcript..."
        data = fetch_transcript(url)
        job["word_count"] = data["word_count"]
        job["message"] = f"Transcript: {data['word_count']:,} words"

        # Store sentences for UI
        job["transcript"] = data["sentences"]

        # Stage 2
        job["status"] = "scanning"
        job["message"] = "Scanning for rich point candidates..."
        chunks = sentences_to_chunks(data["sentences"])
        candidates = scan_all_chunks(chunks, data["full_text"])
        job["candidates_count"] = len(candidates)
        job["message"] = f"Found {len(candidates)} candidate(s)"

        if not candidates:
            job["status"] = "done"
            job["message"] = "No rich points found."
            job["results"] = []
            return

        # Stage 3 — Level 1 (batched)
        job["status"] = "level1"
        BATCH_SIZE = 3
        all_l1 = []
        for i in range(0, len(candidates), BATCH_SIZE):
            batch = candidates[i:i + BATCH_SIZE]
            names = [c["word"] for c in batch]
            job["message"] = f"Level 1: analyzing {', '.join(names)}..."
            if i > 0:
                time.sleep(10)
            l1_result = run_level1(batch, data["full_text"], data["sentences"])
            all_l1.extend([p.model_dump() for p in l1_result.rich_points])

        job["message"] = f"Level 1: {len(all_l1)} rich point(s) validated"

        # Stage 4 — Level 2 (batched)
        job["status"] = "level2"
        all_l2 = []
        for i in range(0, len(all_l1), BATCH_SIZE):
            batch = all_l1[i:i + BATCH_SIZE]
            names = [p["word"] for p in batch]
            job["message"] = f"Level 2: deep analysis for {', '.join(names)}..."
            if i > 0:
                time.sleep(10)
            l2_result = run_level2(batch)
            all_l2.extend([p.model_dump() for p in l2_result.rich_points])

        # Stage 5 — Joke Agent
        job["status"] = "jokes"
        job["message"] = "Analyzing jokes..."
        joke_result = run_joke_agent(data["sentences"], all_l1)
        jokes = [j.model_dump() for j in joke_result.jokes]

        # Stage 6 — Exercise Builder (dark humor practice MCQs)
        job["status"] = "exercises"
        job["message"] = "Generating practice exercises..."
        exercise_set = run_exercise_builder(joke_result)
        exercises = [e.model_dump() for e in exercise_set.exercises]

        # Merge
        merged = merge_levels(all_l1, all_l2)
        job["status"] = "done"
        job["message"] = (
            f"Done! Found {len(merged)} rich point(s), {len(jokes)} joke(s), "
            f"{len(exercises)} exercise(s)"
        )
        job["results"] = merged
        job["jokes"] = jokes
        job["exercises"] = exercises
        _save_jobs()

    except Exception as e:
        job["status"] = "error"
        job["message"] = f"Error: {str(e)}"
        _save_jobs()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "queued",
        "message": "Starting...",
        "url": url,
        "results": None,
        "jokes": None,
        "word_count": 0,
        "candidates_count": 0,
        "created_at": datetime.now().isoformat(),
    }

    thread = threading.Thread(target=process_video_job, args=(job_id, url))
    thread.daemon = True
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/history")
def history():
    """Return list of completed jobs for the sidebar."""
    completed = []
    for job_id, job in jobs.items():
        if job.get("status") == "done":
            results = job.get("results") or []
            jokes = job.get("jokes") or []
            completed.append({
                "job_id": job_id,
                "url": job.get("url", ""),
                "status": "done",
                "word_count": job.get("word_count", 0),
                "rich_points_count": len(results),
                "jokes_count": len(jokes),
                "created_at": job.get("created_at", ""),
            })
    completed.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify(completed)


if __name__ == "__main__":
    if not os.environ.get("GROQ_API_KEY"):
        print("Error: GROQ_API_KEY environment variable not set.")
        sys.exit(1)
    _load_jobs()
    print("Starting Rich Point Discovery web UI...")
    print("Open http://localhost:5001 in your browser")
    app.run(debug=False, port=5001)
