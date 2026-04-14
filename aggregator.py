"""Aggregate Level 1 + Level 2 output into markdown report."""

from datetime import datetime


def merge_levels(level1_points: list[dict], level2_points: list[dict]) -> list[dict]:
    """Merge Level 1 and Level 2 outputs by (word, sense_tag)."""
    l2_map = {}
    for p in level2_points:
        key = (p["word"].lower(), p["sense_tag"])
        l2_map[key] = p

    merged = []
    for p1 in level1_points:
        key = (p1["word"].lower(), p1["sense_tag"])
        l2 = l2_map.get(key, {})
        merged.append({**p1, **l2})

    return merged


def generate_markdown(
    video_url: str,
    word_count: int,
    rich_points: list[dict],
    jokes: list[dict] = None,
    exercises: list[dict] = None,
) -> str:
    """Generate markdown report for a single video."""
    date = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"# Rich Point Discovery — {date}",
        f"",
        f"**Video:** {video_url}",
        f"**Transcript:** {word_count:,} words",
        f"**Rich points found:** {len(rich_points)}",
        f"",
        f"---",
        f"",
    ]

    for i, rp in enumerate(rich_points, 1):
        lines.append(f"## {i}. {rp.get('word', '???')}")
        lines.append(f"*{rp.get('type', '')} · {rp.get('pos', '')} · {rp.get('sense_tag', '')}*")
        lines.append("")

        # Level 1
        if rp.get("definition"):
            lines.append(f"### Definition")
            lines.append(rp["definition"])
            lines.append("")

        if rp.get("context_meaning"):
            lines.append(f"### Meaning in this video")
            lines.append(rp["context_meaning"])
            lines.append("")

        if rp.get("transcript_quote"):
            ts = rp.get("timestamp_seconds") or 0
            mins = int(ts // 60)
            secs = int(ts % 60)
            lines.append(f"### From the transcript [{mins:02d}:{secs:02d}]")
            lines.append(f"> {rp['transcript_quote']}")
            lines.append("")

        # Level 2
        if rp.get("why_rich_point"):
            lines.append(f"### Why is this a rich point?")
            lines.append(rp["why_rich_point"])
            lines.append("")

        if rp.get("misuse_consequence"):
            lines.append(f"### What if you use it wrong?")
            lines.append(rp["misuse_consequence"])
            lines.append("")

        if rp.get("origin_story"):
            lines.append(f"### Origin")
            lines.append(rp["origin_story"])
            lines.append("")

        if rp.get("when_to_use"):
            lines.append(f"### When to use / not use")
            lines.append(rp["when_to_use"])
            lines.append("")

        if rp.get("related_rich_points"):
            related = ", ".join(rp["related_rich_points"])
            lines.append(f"### Related rich points")
            lines.append(related)
            lines.append("")

        if rp.get("outsider_rephrase"):
            lines.append(f"### How to say it as an outsider")
            lines.append(rp["outsider_rephrase"])
            lines.append("")

        lines.append("---")
        lines.append("")

    # Jokes section
    if jokes:
        lines.append(f"# Jokes ({len(jokes)})")
        lines.append("")
        for i, joke in enumerate(jokes, 1):
            ts = joke.get("timestamp") or 0
            mins = int(ts // 60)
            secs = int(ts % 60)
            header_tags = joke.get("joke_type", "")
            mechanisms = joke.get("mechanisms") or []
            if mechanisms:
                header_tags += f" · {'/'.join(mechanisms)}"
                intensity = joke.get("taboo_intensity") or ""
                if intensity:
                    header_tags += f" · {intensity}"
            lines.append(f"## Joke {i} [{mins:02d}:{secs:02d}] — {header_tags}")
            lines.append("")
            if joke.get("transcript_excerpt"):
                lines.append(f"> {joke['transcript_excerpt']}")
                lines.append("")
            if joke.get("explanation"):
                lines.append(f"**Explanation:** {joke['explanation']}")
                lines.append("")
            if joke.get("cultural_context"):
                lines.append(f"**Cultural context:** {joke['cultural_context']}")
                lines.append("")
            lines.append("---")
            lines.append("")

    # Exercises section — dark humor practice MCQs
    if exercises:
        lines.append(f"# Practice exercises — dark humor mechanisms ({len(exercises)})")
        lines.append("")
        lines.append(
            "> Each exercise targets one of five core mechanisms. Pick the option you think lands; "
            "then read the explanation to learn *why*."
        )
        lines.append("")
        for i, ex in enumerate(exercises, 1):
            ts = ex.get("source_joke_timestamp") or 0
            mins = int(ts // 60)
            secs = int(ts % 60)
            lines.append(
                f"## Exercise {i} — {ex.get('mechanism', '')} (from joke @ [{mins:02d}:{secs:02d}])"
            )
            lines.append("")
            lines.append(f"**Q.** {ex.get('question', '')}")
            lines.append("")
            options = ex.get("options") or {}
            for letter in ("A", "B", "C"):
                lines.append(f"- **{letter}.** {options.get(letter, '')}")
            lines.append("")
            lines.append(f"<details><summary>Show answer + explanation</summary>")
            lines.append("")
            lines.append(f"**Correct:** {ex.get('correct', '')}")
            lines.append("")
            expl = ex.get("explanation") or {}
            if expl.get("why_c_lands"):
                lines.append(f"**Why the correct option lands:** {expl['why_c_lands']}")
                lines.append("")
            if expl.get("why_b_misses"):
                lines.append(f"**Why the near-miss option falls short:** {expl['why_b_misses']}")
                lines.append("")
            if expl.get("pattern_takeaway"):
                lines.append(f"**Takeaway pattern:** {expl['pattern_takeaway']}")
                lines.append("")
            lines.append("</details>")
            lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines)
