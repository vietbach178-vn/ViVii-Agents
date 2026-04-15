"""Sub-agents grouped by series.

  - A-series: shared preprocessing (A1 splitter)
  - B-series: Rich Point Discovery (B1 scanner → B2 level1 → B3 level2)
  - C-series: Joke pipeline (C1 detector → C2 explainer → C3 comprehension MCQ + C4 transfer MCQ)
  - D-series: Culture stamps (D1 detector → D2 deep-dive)

B-series currently requires model constants in `config.py` that were trimmed
when the project pivoted to C/D series. B-series re-exports are wrapped in
try/except so importing `agents` still works while B-series is not runnable.
"""

__all__ = []

try:
    from agents.A1_splitter import split_sentences_with_llm
    __all__ += ["split_sentences_with_llm"]
except ImportError:
    pass

try:
    from agents.B1_scanner import scan_all_chunks
    from agents.B2_level1 import run_level1
    from agents.B3_level2 import run_level2
    __all__ += ["scan_all_chunks", "run_level1", "run_level2"]
except ImportError:
    pass

from agents.C1_joke_detector import run_joke_detector
from agents.C2_joke_explainer import run_joke_explainer
from agents.C3_comprehension_mcq import run_c3
from agents.C4_transfer_practice import run_c4
from agents.D1_stamp_detector import run_d1
from agents.D2_stamp_deep_dive import run_d2

__all__ += [
    "run_joke_detector",
    "run_joke_explainer",
    "run_c3",
    "run_c4",
    "run_d1",
    "run_d2",
]
