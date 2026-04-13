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


def generate_markdown(video_url: str, word_count: int, rich_points: list[dict], jokes: list[dict] = None) -> str:
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
            lines.append(f"## Joke {i} [{mins:02d}:{secs:02d}] — {joke.get('joke_type', '')}")
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

    return "\n".join(lines)
