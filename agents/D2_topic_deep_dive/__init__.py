"""D2 — Cultural Topic Deep-Dive agent. Writes a long-form article (with mandatory TL;DR) for each topic detected by D1, cached by slug(title) cross-video."""

from agents.D2_topic_deep_dive.agent import run_d2, deep_dive_for_topic

__all__ = ["run_d2", "deep_dive_for_topic"]
