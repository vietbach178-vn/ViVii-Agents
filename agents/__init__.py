"""Sub-agents grouped by series.

  - A-series: shared preprocessing (A1 splitter)
  - B-series: Rich Point Discovery (B1 scanner → B2 level1 → B3 level2)
  - D-series: Cultural Topics (D1 topic detector → D2 topic deep-dive)

B-series and D-series both consume the A-series transcript output independently
and run in parallel.
"""

from agents.A1_splitter import split_sentences_with_llm
from agents.B1_scanner import scan_all_chunks
from agents.B2_level1 import run_level1
from agents.B3_level2 import run_level2
from agents.D1_topic_detector import run_d1
from agents.D2_topic_deep_dive import run_d2

__all__ = [
    "split_sentences_with_llm",
    "scan_all_chunks",
    "run_level1",
    "run_level2",
    "run_d1",
    "run_d2",
]
