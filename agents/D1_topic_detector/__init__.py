"""D1 — Cultural Topic Detector. One LLM call over the full transcript returns
N video-level cultural topics, each grounded to a contiguous sentence range."""

from agents.D1_topic_detector.agent import run_d1

__all__ = ["run_d1"]
