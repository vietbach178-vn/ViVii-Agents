"""D1 — Culture Stamp Detector. Identifies culture stamps (events, institutions, traditions) in a joke's C2 output and canonicalizes them against a persisted catalog."""

from agents.D1_stamp_detector.agent import run_d1, detect_stamps_for_block

__all__ = ["run_d1", "detect_stamps_for_block"]
