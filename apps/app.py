"""Flask web UI for the Rich Point + Cultural Topic pipeline.

Endpoints:
  POST /api/analyze   — start a background job for a YouTube URL
  GET  /api/status/<id> — poll job status + results
  GET  /api/history    — list completed jobs (most recent first)
  GET  /               — serve the SPA
"""

import json
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from transcript import fetch_transcript
from chunker import sentences_to_chunks

from agents.A1_splitter import split_sentences_with_llm
from agents.B1_scanner import scan_all_chunks
from agents.B2_level1 import run_level1
from agents.B3_level2 import run_level2
from agents.D1_topic_detector import run_d1
from agents.D2_topic_deep_dive import run_d2


app = Flask(__name__, static_folder="static", template_folder="templates")

# In-memory job store
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()

OUTPUT_DIR = Path("output")


# ---------------------------------------------------------------------------
# Pipeline runner (background thread)
# ---------------------------------------------------------------------------

def _run_pipeline(job_id: str, url: str):
    """Run the full pipeline for one YouTube URL. Updates job dict in place.

    B-series and D-series both consume A-series output. They are independent
    and run sequentially in this thread; if you want parallelism, fan them
    out into two threads here.
    """

    def _update(status: str, message: str, **extra):
        with jobs_lock:
            jobs[job_id].update({"status": status, "message": message, **extra})

    try:
        # --- A-series: Transcript processing ---
        _update("fetching", "Fetching transcript...")
        transcript = fetch_transcript(url)
        sentences = transcript["sentences"]
        full_text = " ".join(s["text"] for s in sentences)
        word_count = transcript["word_count"]

        _update("fetching", f"Transcript: {len(sentences)} sentences, {word_count} words")

        _update("splitting", "A1: Splitting sentences with LLM...")
        split_sents = split_sentences_with_llm(sentences)
        # Keep the shape D1 expects (with start/duration).
        transcript_for_d1 = {**transcript, "sentences": split_sents}

        # --- B-series: Rich Point Discovery ---
        rich_points_merged = []
        try:
            _update("scanning", "B1: Chunking + scanning for rich points...")
            chunks = sentences_to_chunks(split_sents)
            candidates = scan_all_chunks(chunks, full_text)

            if candidates:
                _update("level1", f"B2: analyzing {len(candidates)} candidates...")
                l1 = run_level1(candidates, full_text, split_sents)
                l1_dicts = [rp.model_dump() for rp in l1.rich_points]

                _update("level2", f"B3: deep analysis of {len(l1_dicts)} rich points...")
                l2 = run_level2(l1_dicts)
                l2_map = {rp.word.lower(): rp.model_dump() for rp in l2.rich_points}

                for rp in l1_dicts:
                    merged = {**rp}
                    deep = l2_map.get(rp["word"].lower(), {})
                    merged.update({k: v for k, v in deep.items() if v})
                    rich_points_merged.append(merged)
            else:
                _update("level2", "No rich point candidates found.")
        except Exception as e:
            print(f"B-series error: {e}")
            _update("scanning", f"Rich points skipped: {e}")

        # --- D-series: Cultural Topics ---
        _update("topics", "D1: Detecting cultural topics...")
        d1_output = run_d1(transcript_for_d1)

        _update("topics", f"D2: Writing deep-dive articles for {len(d1_output.get('topics', []))} topics...")
        cache_dir = OUTPUT_DIR / "d2_articles"
        d2_output = run_d2(d1_output, cache_dir)

        # --- Done ---
        _update(
            "done",
            "Analysis complete!",
            results=rich_points_merged,
            transcript=sentences,
            word_count=word_count,
            url=url,
            d1=d1_output,
            d2=d2_output,
        )

        # Save to disk for persistence
        _save_job(job_id)

    except Exception as e:
        _update("error", str(e))


def _save_job(job_id: str):
    """Persist completed job to disk."""
    out = OUTPUT_DIR / job_id
    out.mkdir(parents=True, exist_ok=True)
    with jobs_lock:
        job = dict(jobs[job_id])
    job.pop("thread", None)
    (out / "job.json").write_text(json.dumps(job, indent=2, ensure_ascii=False, default=str))


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True)
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    job_id = str(uuid.uuid4())[:8]
    with jobs_lock:
        jobs[job_id] = {
            "job_id": job_id,
            "url": url,
            "status": "queued",
            "message": "Queued...",
            "created_at": time.time(),
        }

    t = threading.Thread(target=_run_pipeline, args=(job_id, url), daemon=True)
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        path = OUTPUT_DIR / job_id / "job.json"
        if path.exists():
            job = json.loads(path.read_text())
            with jobs_lock:
                jobs[job_id] = job
        else:
            return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/history")
def history():
    items = []
    with jobs_lock:
        for jid, job in jobs.items():
            if job.get("status") == "done":
                items.append({
                    "job_id": jid,
                    "url": job.get("url", ""),
                    "rich_points_count": len(job.get("results", [])),
                    "topics_count": len(job.get("d1", {}).get("topics", [])),
                    "created_at": job.get("created_at"),
                })

    if OUTPUT_DIR.exists():
        for d in OUTPUT_DIR.iterdir():
            if d.is_dir() and (d / "job.json").exists():
                jid = d.name
                if any(i["job_id"] == jid for i in items):
                    continue
                try:
                    job = json.loads((d / "job.json").read_text())
                    if job.get("status") == "done":
                        items.append({
                            "job_id": jid,
                            "url": job.get("url", ""),
                            "rich_points_count": len(job.get("results", [])),
                            "topics_count": len(job.get("d1", {}).get("topics", [])),
                            "created_at": job.get("created_at"),
                        })
                except Exception:
                    pass

    items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return jsonify(items)


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)
    app.run(host="0.0.0.0", port=5001, debug=True)
