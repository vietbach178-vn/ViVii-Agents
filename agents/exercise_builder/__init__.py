"""Exercise Builder — graduated MCQ workflow for dark humor practice.

NOTE: this is a Workflow (code-driven control flow with Prompt Chain +
Evaluator-Optimizer patterns), not an Agent. See groovy-wiggling-tower plan.
"""

from agents.exercise_builder.workflow import run_exercise_builder

__all__ = ["run_exercise_builder"]
