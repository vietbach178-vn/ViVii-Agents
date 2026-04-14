"""Shared rubric for 5 core dark humor mechanisms.

Source of truth for the mechanism taxonomy. Both Joke Agent (for tagging) and
Exercise Builder (for generating graduated MCQs + evaluating them) import from
this module so the two stay in sync.
"""

MECHANISM_IDS = [
    "misdirection",
    "taboo_violation",
    "benign_violation",
    "absurd_juxtaposition",
    "subverted_solemnity",
]

TABOO_INTENSITIES = ["mild", "medium", "extreme"]


MECHANISM_RUBRIC = """## 5 core dark humor mechanisms

Use these exact IDs when tagging. A joke may carry 1-3 mechanisms at once.

1. **misdirection** — The setup steers the listener's expectation one way; the punchline flips to an unexpected frame. The flip is the mechanism, regardless of how dark the topic is.

2. **taboo_violation** — The joke touches a culturally forbidden topic (death, disaster, disability, race, religion, sex, trauma). Tagging this does NOT mean the joke is offensive — it means the forbidden topic is the fuel.

3. **benign_violation** — The joke violates a norm but still feels "safe" (McGraw & Warren 2010). The listener's brain registers the norm break AND a reason not to be alarmed. Without the "benign" part, taboo lands as cruelty, not humor. Tag this when you can point to what makes the violation psychologically safe (temporal distance, fictional frame, victim-less setup, shared in-group).

4. **absurd_juxtaposition** — A grave/serious frame is crashed together with a trivial/childish/mundane frame in the same moment. Example: treating 9/11 with the attitude you'd use for a hobby project.

5. **subverted_solemnity** — The joke addresses a topic that "deserves" gravity using a flat, indifferent, or bureaucratic tone. The mismatch between topic weight and delivery tone is the payload.

## Taboo intensity scale

- **mild** — touches a taboo topic but stays within mainstream standup norms (death, minor disability, religion as abstract concept).
- **medium** — crosses into explicit territory most general-audience comedians avoid (named disasters, race stereotypes played seriously, sexual violence framed as punchline).
- **extreme** — crosses red lines (mocks specific identifiable living victims, punches down on protected groups, platforms hate framing).

## Red lines — never tag as benign_violation, always flag as extreme

- Mocks specific living named victims of real tragedies
- Punches down at protected groups using superiority mechanism
- Platforms or endorses hate framing rather than subverting it

If the joke crosses a red line, still tag the other applicable mechanisms (it is still analytically a joke) and set taboo_intensity to "extreme" so downstream consumers (e.g., Exercise Builder) can skip it."""


def mechanism_list_string() -> str:
    """Return the 5 mechanism IDs as a compact comma-separated string for prompts."""
    return ", ".join(MECHANISM_IDS)
