"""D2 — Stamp Deep-Dive agent. Writes a long-form article (with mandatory TL;DR) for each culture stamp detected by D1."""

from agents.D2_stamp_deep_dive.agent import run_d2, deep_dive_for_stamp

__all__ = ["run_d2", "deep_dive_for_stamp"]
