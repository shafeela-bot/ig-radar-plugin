#!/usr/bin/env python3
"""
Own-history pattern analysis — the postmortem-to-script feedback loop.

Unlike lib/pattern_extraction.py (which finds patterns repeating across 2+
*competitors*), this finds patterns repeating across the teammate's OWN past
postmortems — i.e., what her own high-scoring videos have in common, so
/ig-script can lean into what's actually proven to work for her specifically,
not just what worked for a competitor.

"Win" = a postmortem scoring >= min_win_score (the caller should pass
config/user_config.json's scoring.viral_threshold). Confidence scales with how
many of her own postmortems exist, not competitor count — a teammate with
fewer than 2 wins on record has no reliable signal yet, and this returns an
empty pattern list rather than fabricating one from thin history.

Standalone by design (no import of lib/pattern_extraction.py) — every lib/
script here is self-contained and runnable on its own via `python3 lib/<x>.py`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CLASSIFIED_FIELDS = ["hook_format", "format", "length_bracket", "trigger", "cta_present"]

# Same rationale as pattern_extraction.py's MISSING_DATA_SENTINELS: these mean
# "we don't have this data," not a legitimate value like cta_present: none.
MISSING_DATA_SENTINELS = {"unknown", "n/a", "unclear", ""}


def _own_history_confidence(n_wins: int) -> str:
    if n_wins >= 5:
        return "HIGH"
    if n_wins >= 3:
        return "MEDIUM"
    return "SIGNAL"


def _group_by_field(records: list[dict], field: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for r in records:
        value = r.get(field)
        if value and str(value).strip().lower() not in MISSING_DATA_SENTINELS:
            grouped.setdefault(value, []).append(r)
    return grouped


def field_pattern(postmortems: list[dict], field: str, min_win_score: float) -> dict | None:
    """
    For one classified field (e.g. cta_present), finds the value most common
    among her wins and contrasts it against how often that same value shows up
    in her non-wins — a within-account signal, not a cross-competitor one.
    """
    wins = [p for p in postmortems if p.get("score") is not None and p["score"] >= min_win_score]
    if len(wins) < 2:
        return None
    grouped = _group_by_field(wins, field)
    if not grouped:
        return None
    top_value, items = max(grouped.items(), key=lambda kv: len(kv[1]))
    losses = [p for p in postmortems if p.get("score") is not None and p["score"] < min_win_score]
    losses_with_value = [
        p for p in losses
        if str(p.get(field, "")).strip().lower() == str(top_value).strip().lower()
    ]
    return {
        "field": field,
        "value": top_value,
        "present_in_wins": len(items),
        "total_wins_analyzed": len(wins),
        "present_in_non_wins": len(losses_with_value),
        "total_non_wins_analyzed": len(losses),
        "confidence": _own_history_confidence(len(wins)),
    }


def own_winning_patterns(postmortems: list[dict], min_win_score: float) -> list[dict]:
    """
    Only surfaces a pattern as actionable if it shows up in a clear majority of
    her wins — otherwise it's just "one thing one winning video happened to
    have," not something to bake into every future script.
    """
    candidates = [p for f in CLASSIFIED_FIELDS if (p := field_pattern(postmortems, f, min_win_score))]
    return [p for p in candidates if p["present_in_wins"] / p["total_wins_analyzed"] >= 0.5]


def load_postmortems(postmortems_dir: str) -> list[dict]:
    dir_path = Path(postmortems_dir)
    if not dir_path.is_dir():
        return []
    records = []
    for f in sorted(dir_path.glob("*.json")):
        with open(f) as fh:
            records.append(json.load(fh))
    return records


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postmortems-dir", required=True, help="Path to data/postmortems/")
    parser.add_argument(
        "--min-win-score", type=float, required=True,
        help="Score threshold counting as a 'win' — pass user_config.json's scoring.viral_threshold",
    )
    args = parser.parse_args()

    postmortems = load_postmortems(args.postmortems_dir)
    patterns = own_winning_patterns(postmortems, args.min_win_score)
    print(json.dumps({"n_postmortems_analyzed": len(postmortems), "patterns": patterns}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
