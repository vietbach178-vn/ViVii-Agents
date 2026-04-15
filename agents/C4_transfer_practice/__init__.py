"""C4 — Transfer Practice MCQ agent. Generates 3-option MCQs testing stamp recognition in a new context (stamp mode) or topic recognition when no stamps exist (topic fallback mode)."""

from agents.C4_transfer_practice.agent import run_c4, transfer_mcqs_for_block

__all__ = ["run_c4", "transfer_mcqs_for_block"]
