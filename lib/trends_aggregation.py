#!/usr/bin/env python3
"""
Niche-wide pattern aggregation across ALL reels pulled in one /ig-radar run — the
"This Week in Your Niche" section that opens the weekly report, ahead of individual
outliers and cross-competitor patterns. Distinct from lib/outlier_scoring.py (is
THIS reel a breakout for its creator) and lib/pattern_extraction.py (what repeats
across 2+ competitors' winners) — this asks "what's everyone in the niche doing
right now," across the whole pool, not just the shortlist.

Trigger classification here is a caption+metadata heuristic against the 7-trigger
taxonomy (config/psychological_triggers.json — absorbed from the
social-media-marketing-specialist skill, credited there), not a verified read of the
actual video. /ig-radar only transcribes the shortlist (by design, for cost), so
there's no transcript for most of the pool this pass runs over — and the PRD calls
for ~$0 marginal spend here, so no new Apify calls either. The heuristic is cheap
enough to run over every reel in the pool, which is what makes a real
full-population baseline possible (needed to flag a format/trigger as
"overperforming" its normal share). Treat formats/triggers output as directional
signal, not ground truth — say so wherever this feeds a teammate-facing report.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict

try:
    from outlier_scoring import is_reel, _views_of
except ImportError:
    from lib.outlier_scoring import is_reel, _views_of

MIN_AUDIO_CREATOR_COUNT = 3
MIN_HASHTAG_DELTA = 1.5
MIN_HASHTAG_DISTINCT_CREATORS = 2  # one viral outlier's tag choices shouldn't read as a niche trend
MIN_FORMAT_HOOK_DELTA = 1.3
MIN_BASELINE_SHARE_TO_FLAG = 0.02  # below this, a "delta" is mostly small-sample noise, not signal
TOP_N_TOPICS = 5
TOP_N_HASHTAGS = 5

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for", "is",
    "it", "this", "that", "with", "as", "at", "by", "from", "i", "you", "your",
    "my", "me", "we", "our", "so", "just", "if", "be", "are", "was", "were",
    "how", "what", "when", "why", "not", "no", "do", "did", "does", "up", "out",
    "all", "can", "get", "got", "here", "here's", "im", "its", "it's", "one",
    "comment", "link", "below", "watch", "check", "video", "like", "follow",
}

# Caption/hashtag/duration heuristics for CONTENT FORMAT (not psychological trigger).
FORMAT_RULES = [
    ("pov", re.compile(r"\bpov\b", re.I)),
    ("skit", re.compile(r"\bskit\b|\"[^\"]{5,}\".*\"[^\"]{5,}\"", re.I)),
    ("demo", re.compile(r"\bbuilt\b|\bhere'?s how\b|\btutorial\b|\bstep\b|\bin \d+\s*(minutes?|hours?|days?|weeks?)\b", re.I)),
    ("meme", re.compile(r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]{2,}|\brage\b|\bbait", re.I)),
]
DEFAULT_FORMAT = "talking_head"

# Caption heuristics mapped to the 7-trigger taxonomy in config/psychological_triggers.json.
# Deliberately simple keyword rules, not a classifier — cheap, deterministic, and
# honest about being a proxy for the real (unwatched, untranscribed) video.
TRIGGER_RULES = [
    ("controversy_hot_take", re.compile(r"unpopular opinion|hot take|controversial", re.I)),
    ("fear_fomo", re.compile(r"\bstop doing\b|\bmistake\b|\bwarning\b|before it'?s too late", re.I)),
    ("transformation_promise", re.compile(r"how i went from|\bbefore\b.{0,20}\bafter\b|\bin \d+\s*(days?|weeks?|months?)\b", re.I)),
    ("social_proof", re.compile(r"\bmillion\b|\beveryone(?:'s| is)\b|\bviral\b|\d+[kmb]\+?\s*(people|views|watched)", re.I)),
    ("pain_point", re.compile(r"tired of|struggling with|sick of|why (can'?t|won'?t) (you|i)", re.I)),
    ("identity_signal", re.compile(r"if you'?re a\b|you know you'?re a\b|every .{0,20} knows", re.I)),
    ("curiosity_gap", re.compile(r"you won'?t believe|wait (for it|until)|watch (till|until) the end|\?\s*$", re.I)),
]
UNCLEAR_TRIGGER = "unclear"  # honest fallback rather than forcing a bad match


def classify_format_heuristic(reel: dict) -> str:
    caption = reel.get("caption") or ""
    for label, pattern in FORMAT_RULES:
        if pattern.search(caption):
            return label
    duration = reel.get("videoDuration") or reel.get("duration") or 0
    if duration and duration < 10:
        return "meme"
    return DEFAULT_FORMAT


def classify_trigger_heuristic(reel: dict) -> str:
    caption = reel.get("caption") or ""
    for label, pattern in TRIGGER_RULES:
        if pattern.search(caption):
            return label
    return UNCLEAR_TRIGGER


GENERIC_AUDIO_NAMES = {"original audio", "original sound"}


def audio_identity(reel: dict) -> str | None:
    """
    Prefers a named track (musicInfo) when present. "Original audio" / "Original
    sound" are Instagram's generic placeholder names for any creator's own
    self-recorded audio — the large majority of reels carry one of these, and
    treating that string as a shared identity would merge hundreds of unrelated
    creators' own narration into one fake "trend" (confirmed by hitting exactly
    this bug on real data: 511/654 reels shared the placeholder name, which a
    naive version of this function grouped into one 90-creator false trend).
    Only a real named track counts as an identity here.
    """
    music = reel.get("musicInfo")
    if isinstance(music, dict):
        name = music.get("song_name") or music.get("title") or music.get("artist_name")
        if name and name.strip().lower() not in GENERIC_AUDIO_NAMES:
            return f"track:{name}"
    return None


def top_quartile_by_views(reels: list[dict]) -> list[dict]:
    reel_only = [r for r in reels if is_reel(r)]
    with_views = [(r, v) for r in reel_only if (v := _views_of(r)) is not None]
    if not with_views:
        return []
    with_views.sort(key=lambda x: x[1], reverse=True)
    cutoff = max(1, len(with_views) // 4)
    return [r for r, _ in with_views[:cutoff]]


def audio_trends(top_quartile_reels: list[dict], min_creator_count: int = MIN_AUDIO_CREATOR_COUNT) -> list[dict]:
    by_track: dict[str, set[str]] = defaultdict(set)
    display_name: dict[str, str] = {}
    for r in top_quartile_reels:
        identity = audio_identity(r)
        if not identity:
            continue
        owner = r.get("ownerUsername") or "unknown"
        by_track[identity].add(owner)
        if identity not in display_name:
            music = r.get("musicInfo")
            display_name[identity] = music.get("song_name") if isinstance(music, dict) and music.get("song_name") else "trending/shared audio"

    results = [
        {"track": display_name[identity], "creator_count": len(owners)}
        for identity, owners in by_track.items() if len(owners) >= min_creator_count
    ]
    results.sort(key=lambda x: x["creator_count"], reverse=True)
    return results


def _tokenize(caption: str) -> list[str]:
    words = re.findall(r"[a-zA-Z']+", caption.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def keyword_topics(top_quartile_reels: list[dict], top_n: int = TOP_N_TOPICS) -> list[dict]:
    """
    Frequency-based keyword grouping, not semantic clustering — deliberately
    simple (stdlib Counter only). Each "topic" is a frequent keyword plus a
    couple of example captions that used it, so a teammate can sanity-check the
    grouping themselves rather than trusting an opaque cluster label.
    """
    term_captions: dict[str, list[str]] = defaultdict(list)
    counts = Counter()
    for r in top_quartile_reels:
        caption = (r.get("caption") or "").strip()
        if not caption:
            continue
        seen_terms = set(_tokenize(caption))
        for term in seen_terms:
            counts[term] += 1
            if len(term_captions[term]) < 3:
                term_captions[term].append(caption[:120])

    topics = []
    for term, count in counts.most_common(top_n):
        if count < 2:
            continue
        topics.append({"cluster": term, "reel_count": count, "example_captions": term_captions[term]})
    return topics


def hashtag_heat(top_quartile_reels: list[dict], all_reels: list[dict],
                  min_delta: float = MIN_HASHTAG_DELTA, top_n: int = TOP_N_HASHTAGS,
                  min_distinct_creators: int = MIN_HASHTAG_DISTINCT_CREATORS) -> list[dict]:
    def tally(reels):
        c = Counter()
        creators = defaultdict(set)
        for r in reels:
            owner = r.get("ownerUsername")
            for h in (r.get("hashtags") or []):
                tag = h.lower()
                c[tag] += 1
                if owner:
                    creators[tag].add(owner)
        return c, creators

    winner_counts, winner_creators = tally(top_quartile_reels)
    baseline_counts, _ = tally(all_reels)
    n_winners = max(1, len(top_quartile_reels))
    n_all = max(1, len(all_reels))

    rising = []
    for tag, w_count in winner_counts.items():
        if len(winner_creators.get(tag, set())) < min_distinct_creators:
            continue  # A single creator's tag choices on one viral post isn't a trend — just their post.
        winner_share = w_count / n_winners
        baseline_share = baseline_counts.get(tag, 0) / n_all
        if baseline_share <= 0:
            continue
        delta = winner_share / baseline_share
        if delta >= min_delta:
            rising.append({"tag": f"#{tag}", "delta_vs_baseline": f"+{delta:.1f}x",
                           "distinct_creators": len(winner_creators[tag])})

    rising.sort(key=lambda x: float(x["delta_vs_baseline"].strip("+x")), reverse=True)
    return rising[:top_n]


def _distribution(labels: list[str]) -> dict[str, float]:
    if not labels:
        return {}
    counts = Counter(labels)
    total = len(labels)
    return {label: round(count / total, 3) for label, count in counts.items()}


def format_distribution(reels: list[dict]) -> dict[str, float]:
    return _distribution([classify_format_heuristic(r) for r in reels])


def trigger_distribution(reels: list[dict]) -> dict[str, float]:
    return _distribution([classify_trigger_heuristic(r) for r in reels])


def flag_overperforming(top_quartile_dist: dict[str, float], baseline_dist: dict[str, float],
                         min_delta: float = MIN_FORMAT_HOOK_DELTA) -> list[str]:
    flagged = []
    for label, winner_share in top_quartile_dist.items():
        baseline_share = baseline_dist.get(label, 0)
        if baseline_share >= MIN_BASELINE_SHARE_TO_FLAG and (winner_share / baseline_share) >= min_delta:
            flagged.append(label)
    return flagged


def build_trends_report(all_reels: list[dict]) -> dict:
    top_quartile = top_quartile_by_views(all_reels)
    reel_only_all = [r for r in all_reels if is_reel(r)]

    format_top = format_distribution(top_quartile)
    format_baseline = format_distribution(reel_only_all)
    trigger_top = trigger_distribution(top_quartile)
    trigger_baseline = trigger_distribution(reel_only_all)

    return {
        "trends": {
            "_method_note": (
                "formats/triggers are caption+metadata heuristics (no transcript for "
                "most of the pool by design) — directional signal, not a verified "
                "read of the actual video."
            ),
            "audio": audio_trends(top_quartile),
            "topics": keyword_topics(top_quartile),
            "formats": format_top,
            "formats_overperforming": flag_overperforming(format_top, format_baseline),
            "triggers": trigger_top,
            "triggers_overperforming": flag_overperforming(trigger_top, trigger_baseline),
            "hashtags_rising": hashtag_heat(top_quartile, reel_only_all),
        }
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reels-json", required=True, help="Path to a JSON file: a list of reel dicts (the full pool, not just the shortlist)")
    args = parser.parse_args()

    with open(args.reels_json) as f:
        reels = json.load(f)

    print(json.dumps(build_trends_report(reels), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
