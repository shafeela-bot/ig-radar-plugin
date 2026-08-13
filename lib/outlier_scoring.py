#!/usr/bin/env python3
"""
100-point weighted outlier scoring.

CREDIT: this scoring formula (the 40/20/15/10/10/5-point weighted breakdown, the
🔴/🟡/⚪ tagging thresholds, and the per-competitor top-5 shortlist rule) is absorbed
from a teammate's `social-media-marketing-specialist` skill. This file implements
that formula against real Apify field names; the `min_views_floor` hard filter
below is this plugin's own addition on top of the original design, not part of the
absorbed formula — called out explicitly so credit stays precise.

Pure functions, no network calls, no dependencies beyond the standard library —
this module just turns raw Apify reel data into scores.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from datetime import datetime, timezone

MIN_VIEWS_FLOOR = 20_000  # this plugin's own addition, not part of the absorbed formula
VIEW_SCORE_WEIGHT = 40
COMMENT_SCORE_WEIGHT = 20
LIKE_SCORE_WEIGHT = 15
SAVE_SIGNAL_POINTS = 10
SAVE_SIGNAL_KEYWORDS = ["save", "bookmark", "screenshot this", "save for later", "download this"]
COMPLETION_BONUS_POINTS = 10
COMPLETION_MAX_DURATION_SEC = 20
COMPLETION_MIN_VIEW_MULTIPLE = 2
RECENCY_BONUS_POINTS = 5
RECENCY_MAX_DAYS = 7
RECENCY_MIN_VIEW_MULTIPLE = 1.5

VIRAL_THRESHOLD = 70
ABOVE_AVERAGE_THRESHOLD = 40

BASELINE_WINDOW_DAYS = 30
BASELINE_EXCLUDE_TOP_PCT = 10
BASELINE_STALE_DAYS = 30
TOP_N_PER_COMPETITOR = 5
TOTAL_SHORTLIST_CAP = 30

BASELINES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "baselines")


def _views_of(reel: dict) -> int | None:
    # Field names confirmed via live testing against real Apify responses — these
    # actors are inconsistent about which one shows up (videoPlayCount from the
    # reel scraper, igPlayCount from the hashtag scraper for the same underlying
    # metric).
    for key in ("videoPlayCount", "igPlayCount", "videoViewCount", "viewCount", "views", "playsCount", "plays"):
        v = reel.get(key)
        if isinstance(v, (int, float)):
            return int(v)
    return None


def _comments_of(reel: dict) -> int:
    v = reel.get("commentsCount")
    return int(v) if isinstance(v, (int, float)) else 0


def _likes_of(reel: dict) -> int:
    v = reel.get("likesCount")
    return int(v) if isinstance(v, (int, float)) else 0


def _duration_of(reel: dict) -> float | None:
    v = reel.get("videoDuration") or reel.get("duration")
    return float(v) if isinstance(v, (int, float)) else None


def _posted_days_ago(reel: dict) -> float | None:
    ts = reel.get("timestamp")
    if not ts:
        return None
    try:
        # Apify timestamps show up as either ISO strings or "YYYY-MM-DD - HH:MM"
        # depending on the actor — handle both rather than assuming one format.
        cleaned = ts.replace(" - ", "T") if " - " in ts else ts
        posted = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - posted).total_seconds() / 86400
    except (ValueError, AttributeError):
        return None


def is_reel(item: dict) -> bool:
    """
    Defensive filter so a hashtag or profile pull that accidentally includes
    static posts/carousels never pollutes a baseline or shortlist. Apify's
    Instagram actors vary in field naming across versions, so we check several
    common signals rather than trusting one field name.
    """
    product_type = str(item.get("productType", "")).lower()
    type_field = str(item.get("type", "")).lower()
    if product_type == "clips" or "reel" in type_field:
        return True
    if type_field in ("sidecar", "carousel", "image", "photo"):
        return False
    if item.get("isVideo") is False:
        return False
    return bool(item.get("videoDuration") or item.get("duration"))


def compute_baseline(handle: str, reels: list[dict], window_days: int = BASELINE_WINDOW_DAYS,
                      exclude_top_pct: int = BASELINE_EXCLUDE_TOP_PCT) -> dict:
    """
    Median views (primary benchmark — a few mega-viral reels would skew a mean
    unfairly) plus mean comments/likes, from a creator's reels within the last
    window_days. Drops the top exclude_top_pct% by views first so a single recent
    viral hit doesn't drag the whole baseline up. Reel-only, never carousels/photos.
    """
    reel_only = [r for r in reels if is_reel(r)]

    dated = []
    for r in reel_only:
        age = _posted_days_ago(r)
        if age is None or age <= window_days:
            dated.append(r)

    views = sorted((v for r in dated if (v := _views_of(r)) is not None), reverse=True)
    n_drop = round(len(views) * (exclude_top_pct / 100.0))
    trimmed_views = views[n_drop:] if n_drop < len(views) else views

    comments = [c for r in dated if (c := _comments_of(r)) > 0]
    likes = [l for r in dated if (l := _likes_of(r)) > 0]

    if not trimmed_views:
        return {
            "handle": handle, "median_views": None, "avg_comments": None, "avg_likes": None,
            "n_reels_used": 0, "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "handle": handle,
        "median_views": statistics.median(trimmed_views),
        "avg_comments": statistics.mean(comments) if comments else None,
        "avg_likes": statistics.mean(likes) if likes else None,
        "n_reels_used": len(trimmed_views),
        "n_reels_seen": len(views),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def save_baseline(baseline: dict) -> str:
    os.makedirs(BASELINES_DIR, exist_ok=True)
    path = os.path.join(BASELINES_DIR, f"{baseline['handle']}.json")
    with open(path, "w") as f:
        json.dump(baseline, f, indent=2)
    return path


def load_baseline(handle: str) -> dict | None:
    path = os.path.join(BASELINES_DIR, f"{handle}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def is_baseline_stale(baseline: dict, max_age_days: int = BASELINE_STALE_DAYS) -> bool:
    if not baseline or not baseline.get("computed_at"):
        return True
    computed = datetime.fromisoformat(baseline["computed_at"])
    age_days = (datetime.now(timezone.utc) - computed).days
    return age_days >= max_age_days


def _has_save_signal(caption: str) -> bool:
    caption_lower = caption.lower()
    return any(kw in caption_lower for kw in SAVE_SIGNAL_KEYWORDS)


def score_reel(reel: dict, baseline: dict, min_views_floor: int = MIN_VIEWS_FLOOR) -> dict:
    """
    The absorbed 100-point formula. `baseline` is compute_baseline()'s output
    (needs median_views, avg_comments, avg_likes). Returns a full breakdown, not
    just the total — callers can see exactly which components fired.
    """
    views = _views_of(reel)
    result = {
        "views": views, "score": 0, "tag": None,
        "view_score": 0, "comment_score": 0, "like_score": 0,
        "save_signal": False, "completion_bonus": False, "recency_bonus": False,
        "reason": None,
    }

    if views is None:
        result["reason"] = "no_view_count_in_source_data"
        return result

    if views < min_views_floor:
        result["reason"] = f"below_min_views_floor ({views} < {min_views_floor}) — this plugin's addition, not part of the absorbed formula"
        result["tag"] = "⚪"
        return result

    median_views = baseline.get("median_views")
    avg_comments = baseline.get("avg_comments")
    avg_likes = baseline.get("avg_likes")

    if median_views:
        result["view_score"] = round(min((views / median_views) * VIEW_SCORE_WEIGHT, VIEW_SCORE_WEIGHT), 2)
    if avg_comments:
        result["comment_score"] = round(min((_comments_of(reel) / avg_comments) * COMMENT_SCORE_WEIGHT, COMMENT_SCORE_WEIGHT), 2)
    if avg_likes:
        result["like_score"] = round(min((_likes_of(reel) / avg_likes) * LIKE_SCORE_WEIGHT, LIKE_SCORE_WEIGHT), 2)

    caption = reel.get("caption") or ""
    if _has_save_signal(caption):
        result["save_signal"] = True

    duration = _duration_of(reel)
    if median_views and duration is not None and duration <= COMPLETION_MAX_DURATION_SEC and views > COMPLETION_MIN_VIEW_MULTIPLE * median_views:
        result["completion_bonus"] = True

    age_days = _posted_days_ago(reel)
    if median_views and age_days is not None and age_days <= RECENCY_MAX_DAYS and views > RECENCY_MIN_VIEW_MULTIPLE * median_views:
        result["recency_bonus"] = True

    total = (
        result["view_score"] + result["comment_score"] + result["like_score"]
        + (SAVE_SIGNAL_POINTS if result["save_signal"] else 0)
        + (COMPLETION_BONUS_POINTS if result["completion_bonus"] else 0)
        + (RECENCY_BONUS_POINTS if result["recency_bonus"] else 0)
    )
    result["score"] = round(min(total, 100), 2)

    if result["score"] >= VIRAL_THRESHOLD:
        result["tag"] = "🔴"
    elif result["score"] >= ABOVE_AVERAGE_THRESHOLD:
        result["tag"] = "🟡"
    else:
        result["tag"] = "⚪"

    result["reason"] = f"score {result['score']}/100 -> {result['tag']}"
    return result


def score_batch(reels: list[dict], baseline: dict, min_views_floor: int = MIN_VIEWS_FLOOR) -> list[dict]:
    return [{**reel, "score": score_reel(reel, baseline, min_views_floor)} for reel in reels]


def shortlist(scored_by_competitor: dict[str, list[dict]], top_n_per_competitor: int = TOP_N_PER_COMPETITOR,
              total_cap: int = TOTAL_SHORTLIST_CAP) -> list[dict]:
    """
    Top N red-tagged per competitor, filling with yellow if fewer than N red exist,
    capped at total_cap across the whole sweep — matches the absorbed formula's
    "5 per competitor, ~30 total" rule.
    """
    picked = []
    for handle, reels in scored_by_competitor.items():
        red = [r for r in reels if r["score"]["tag"] == "🔴"]
        yellow = [r for r in reels if r["score"]["tag"] == "🟡"]
        red.sort(key=lambda r: r["score"]["score"], reverse=True)
        yellow.sort(key=lambda r: r["score"]["score"], reverse=True)
        picked.extend(red[:top_n_per_competitor])
        if len(red) < top_n_per_competitor:
            picked.extend(yellow[:top_n_per_competitor - len(red)])

    picked.sort(key=lambda r: r["score"]["score"], reverse=True)
    return picked[:total_cap]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_baseline = sub.add_parser("compute-baseline", help="Compute + cache a creator's rolling baseline")
    p_baseline.add_argument("--handle", required=True)
    p_baseline.add_argument("--reels-json", required=True, help="Path to a JSON file: a list of reel dicts")

    p_score = sub.add_parser("score", help="Score a batch of reels against a cached (or given) baseline")
    p_score.add_argument("--reels-json", required=True)
    p_score.add_argument("--handle", help="Load this handle's cached baseline")

    args = parser.parse_args()

    if args.command == "compute-baseline":
        with open(args.reels_json) as f:
            reels = json.load(f)
        baseline = compute_baseline(args.handle, reels)
        path = save_baseline(baseline)
        print(json.dumps({"saved_to": path, **baseline}))
        return 0

    if args.command == "score":
        with open(args.reels_json) as f:
            reels = json.load(f)
        baseline = load_baseline(args.handle) if args.handle else {}
        scored = score_batch(reels, baseline or {})
        print(json.dumps(scored, indent=2))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
