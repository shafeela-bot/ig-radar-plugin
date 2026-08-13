#!/usr/bin/env python3
"""
Cross-competitor pattern extraction.

CREDIT: the core method here — "a pattern in one competitor is noise, in two is
signal," the 8 pattern categories (dominant hook format, top topic cluster, winning
format, length sweet spot, emotion signature, underserved angle, CTA pattern, timing
pattern), and the HIGH/MEDIUM/SIGNAL confidence tiers — is absorbed from a
teammate's `social-media-marketing-specialist` skill.

Like lib/trends_aggregation.py, this module only does counting/grouping — it takes
breakdowns that ig-outlier-breakdown has already classified (hook_format, format,
length_bracket, trigger, cta_present, posted day/hour) and finds which
classifications repeat across 2+ competitors. The actual "WHAT IT IS" / "WHY IT
WORKS" / "YOUR OPPORTUNITY" prose is Claude's synthesis at the skill layer, informed
by this module's structured output plus the teammate's own niche context — that part
requires judgment this module deliberately doesn't attempt.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from statistics import mean

MIN_COMPETITORS_FOR_SIGNAL = 2


def _confidence(n_competitors: int) -> str:
    if n_competitors >= 3:
        return "HIGH"
    if n_competitors == 2:
        return "MEDIUM"
    return "SIGNAL"


# Sentinels meaning "we don't have this data" — must NOT be grouped as if they were
# a real category. Distinct from a legitimate substantive value like "none" (e.g.
# emotion_signature: none, cta_pattern: none), which reflects real data saying the
# thing is genuinely absent, not that it's unknown. Confirmed live: without this
# exclusion, 8 breakdowns all carrying posted_day_of_week="unknown" (missing
# timestamp data) produced a fake "timing_pattern: unknown, HIGH confidence" —
# a data gap masquerading as a finding.
MISSING_DATA_SENTINELS = {"unknown", "n/a", "unclear", ""}


def _group_by_field(breakdowns: list[dict], field: str) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for b in breakdowns:
        value = b.get(field)
        if value and str(value).strip().lower() not in MISSING_DATA_SENTINELS:
            grouped[value].append(b)
    return grouped


def _competitors_in(items: list[dict]) -> list[str]:
    seen = []
    for item in items:
        c = item.get("competitor")
        if c and c not in seen:
            seen.append(c)
    return seen


def dominant_hook_format(breakdowns: list[dict]) -> dict | None:
    grouped = _group_by_field(breakdowns, "hook_format")
    if not grouped:
        return None
    top_format, items = max(grouped.items(), key=lambda kv: len(_competitors_in(kv[1])))
    competitors = _competitors_in(items)
    if len(competitors) < MIN_COMPETITORS_FOR_SIGNAL:
        return None
    return {
        "category": "dominant_hook_format",
        "value": top_format,
        "found_in": competitors,
        "confidence": _confidence(len(competitors)),
        "supporting_scores": [b.get("score") for b in items if b.get("score") is not None],
    }


def _best_scoring_qualifying_group(grouped: dict[str, list[dict]]) -> tuple[str, float, list[str]] | None:
    """
    Shared by winning_format/length_sweet_spot: picks the highest-average-score
    group, but only among groups that already clear the 2+ distinct-competitor bar.
    Confirmed live why this order matters: a single standout in its own unique
    category (one competitor, one very high score) can have a higher raw average
    than any real multi-competitor pattern — picking by score first and checking the
    competitor count after means that lone standout silently blocks the real pattern
    from ever being reported, even though it has 5x the supporting evidence.
    """
    qualifying = {
        key: (mean(b.get("score", 0) for b in items), _competitors_in(items))
        for key, items in grouped.items()
        if len(_competitors_in(items)) >= MIN_COMPETITORS_FOR_SIGNAL
    }
    if not qualifying:
        return None
    top_key, (avg_score, competitors) = max(qualifying.items(), key=lambda kv: kv[1][0])
    return top_key, avg_score, competitors


def winning_format(breakdowns: list[dict]) -> dict | None:
    grouped = _group_by_field(breakdowns, "format")
    best = _best_scoring_qualifying_group(grouped)
    if best is None:
        return None
    top_format, avg_score, competitors = best
    return {
        "category": "winning_format",
        "value": top_format,
        "avg_score": round(avg_score, 1),
        "found_in": competitors,
        "confidence": _confidence(len(competitors)),
    }


def length_sweet_spot(breakdowns: list[dict]) -> dict | None:
    grouped = _group_by_field(breakdowns, "length_bracket")
    best = _best_scoring_qualifying_group(grouped)
    if best is None:
        return None
    top_bracket, avg_score, competitors = best
    return {
        "category": "length_sweet_spot",
        "value": top_bracket,
        "avg_score": round(avg_score, 1),
        "found_in": competitors,
        "confidence": _confidence(len(competitors)),
    }


def emotion_signature(breakdowns: list[dict]) -> dict | None:
    grouped = _group_by_field(breakdowns, "trigger")
    if not grouped:
        return None
    top_trigger, items = max(grouped.items(), key=lambda kv: len(_competitors_in(kv[1])))
    competitors = _competitors_in(items)
    if len(competitors) < MIN_COMPETITORS_FOR_SIGNAL:
        return None
    return {
        "category": "emotion_signature",
        "value": top_trigger,
        "found_in": competitors,
        "confidence": _confidence(len(competitors)),
    }


def cta_pattern(breakdowns: list[dict]) -> dict | None:
    grouped = _group_by_field(breakdowns, "cta_present")
    if not grouped:
        return None
    top_cta, items = max(grouped.items(), key=lambda kv: len(_competitors_in(kv[1])))
    competitors = _competitors_in(items)
    if len(competitors) < MIN_COMPETITORS_FOR_SIGNAL:
        return None
    return {
        "category": "cta_pattern",
        "value": top_cta,
        "found_in": competitors,
        "confidence": _confidence(len(competitors)),
    }


def timing_pattern(breakdowns: list[dict]) -> dict | None:
    """
    Groups by (day_of_week, hour_bucket) if breakdowns carry that data — most
    Apify actors return a timestamp, but not always a reliable local-time hour, so
    this returns None gracefully rather than fabricating a pattern from thin data.
    """
    grouped = _group_by_field(breakdowns, "posted_day_of_week")
    if not grouped:
        return None
    top_day, items = max(grouped.items(), key=lambda kv: len(_competitors_in(kv[1])))
    competitors = _competitors_in(items)
    if len(competitors) < MIN_COMPETITORS_FOR_SIGNAL:
        return None
    return {
        "category": "timing_pattern",
        "value": top_day,
        "found_in": competitors,
        "confidence": _confidence(len(competitors)),
    }


def underserved_angle(breakdowns: list[dict], teammate_topics: list[str] | None = None) -> dict | None:
    """
    Topics appearing in competitor breakdowns that the teammate's own topic history
    doesn't cover. Needs teammate_topics (e.g. from their own past outlier/postmortem
    topic clusters) — returns None rather than guessing if that history isn't
    available yet (a brand-new teammate has no history to compare against).
    """
    if not teammate_topics:
        return None
    grouped = _group_by_field(breakdowns, "topic")
    teammate_topics_lower = {t.lower() for t in teammate_topics}
    for topic, items in grouped.items():
        if topic.lower() not in teammate_topics_lower:
            competitors = _competitors_in(items)
            if len(competitors) >= 1:  # this one, being an opportunity signal, doesn't need the 2+ bar
                return {
                    "category": "underserved_angle",
                    "value": topic,
                    "found_in": competitors,
                    "confidence": _confidence(len(competitors)),
                }
    return None


def extract_all_patterns(breakdowns: list[dict], teammate_topics: list[str] | None = None) -> list[dict]:
    extractors = [
        dominant_hook_format, winning_format, length_sweet_spot,
        emotion_signature, cta_pattern, timing_pattern,
    ]
    patterns = [p for fn in extractors if (p := fn(breakdowns))]
    angle = underserved_angle(breakdowns, teammate_topics)
    if angle:
        patterns.append(angle)
    return patterns


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--breakdowns-json", required=True, help="Path to a JSON file: a list of classified breakdown dicts")
    parser.add_argument("--teammate-topics-json", required=False, help="Optional path to a JSON list of the teammate's own past topics")
    args = parser.parse_args()

    with open(args.breakdowns_json) as f:
        breakdowns = json.load(f)

    teammate_topics = None
    if args.teammate_topics_json:
        with open(args.teammate_topics_json) as f:
            teammate_topics = json.load(f)

    patterns = extract_all_patterns(breakdowns, teammate_topics)
    print(json.dumps(patterns, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
