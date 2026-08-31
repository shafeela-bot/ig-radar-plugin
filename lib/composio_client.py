#!/usr/bin/env python3
"""
Thin, dependency-free wrapper around the Composio CLI for Instagram Graph API access.

Why this exists alongside apify_client.py: Apify scrapes what's *publicly* visible.
The Graph API returns first-party metrics for an account you own — saves, shares,
reach, and average watch time — which no scraper can see, and which are usually the
metrics that actually explain why a reel outperformed. Views alone routinely
understate an outlier.

Design goals mirror apify_client.py:
- Stdlib only (subprocess, json, argparse). Composio ships as a standalone binary, so
  there's nothing to pip install.
- Every call is free. The Graph API costs nothing, so unlike apify_client there are no
  budget caps here — but calls DO consume the account's Graph API rate limit, so
  batch where possible (see get_reels_with_insights).

Field-name and CLI gotchas confirmed by live testing on 2026-08-24 (and 2026-08-27):
- **Big responses come back as a stub, not as data** (found 2026-08-27). Above roughly
  10,000 tokens of output the CLI writes the payload to a temp file and returns
  `{"successful": true, "error": null, "storedInFile": true, "tokenCount": N,
  "outputFilePath": "..."}` with NO `data` key. `successful` is true and `error` is
  null, so it reads as a clean success. `_load_spilled()` now reads the file back, so
  callers never see this — but if you write a new Composio wrapper anywhere else, this
  is the failure that will bite you, and it bites SILENTLY. It cost `reels --limit 25`
  its entire result set on a 9-reel account. Note it depends on total output size, not
  on item count: more *fields* tips a call over as readily as more items.
- `composio connections list` — the subcommand is REQUIRED. Bare `composio connections`
  prints help and exits non-zero.
- `composio tools list <toolkit>` takes the toolkit POSITIONALLY. `--toolkit` is
  rejected as an unknown argument.
- INSTAGRAM_GET_IG_USER_MEDIA needs `ig_user_id`; pass the literal string "me" for the
  authenticated account rather than hunting for the numeric ID.
- The media list does NOT reliably return view/like counts even when you ask for them
  in `fields` — the documented field names come back absent. Counts have to come from
  INSTAGRAM_GET_IG_MEDIA_INSIGHTS per media item. This is the single biggest gotcha:
  code that trusts the media list's metrics silently sees zeros.
- Insights metric names that work: views, reach, likes, comments, shares, saved,
  total_interactions, ig_reels_avg_watch_time, ig_reels_video_view_total_time.
  'impressions', 'plays', 'video_views' are deprecated and silently filtered out;
  'engagement' and 'clicks' are rejected outright.
- There is NO endpoint for who an account follows. The Graph API has never exposed it,
  so a following list needs Apify (see docs/how-to-connect-instagram.md). Searching
  Composio for it returns INSTAGRAM_GET_USER_INFO as a false positive because its
  description mentions follows_count — a COUNT, not a list.
- `--account <word_id>` selects which connected Instagram account to use. This matters
  once more than one page is connected: without it Composio picks for you, and a sweep
  can silently return the wrong page's numbers. Store the word_id per page in
  user_config.json -> accounts.composio_account.

CLI usage (what skills shell out to):
    python3 lib/composio_client.py check
    python3 lib/composio_client.py connections
    python3 lib/composio_client.py user-info [--account <word_id>]
    python3 lib/composio_client.py reels [--account <word_id>] [--limit 25]
    python3 lib/composio_client.py insights --media-id <id> [--account <word_id>]

Exit codes: 0 = success, 2 = Composio/API error, 3 = bad input, 4 = not logged in or
no Instagram connected (the caller should walk the teammate through connecting).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys

CLI_TIMEOUT_SECS = 180

# Metrics worth pulling for a reel. Ordered roughly by how much they explain.
REEL_METRICS = [
    "views", "reach", "likes", "comments", "shares", "saved", "total_interactions",
    "ig_reels_avg_watch_time", "ig_reels_video_view_total_time",
]

MEDIA_FIELDS = "id,caption,media_type,media_product_type,media_url,permalink,thumbnail_url,timestamp,username"


class ComposioError(Exception):
    pass


class ComposioSpillError(ComposioError):
    """
    Composio wrote a large response to disk and we could not read it back.

    Its own subclass because this failure means "the data exists but we lost it," which
    callers must never quietly turn into "there was no data" — that confusion is the
    exact bug this class exists to prevent. See _load_spilled().
    """


class NotConnectedError(Exception):
    """Composio isn't installed, isn't logged in, or has no Instagram account linked."""


def _cli() -> str:
    exe = shutil.which("composio")
    if exe:
        return exe
    # The installer drops it here and appends to the shell profile, which a
    # non-interactive subprocess won't have sourced yet — so check the path directly
    # rather than trusting PATH.
    fallback = os.path.expanduser("~/.local/bin/composio")
    if os.path.exists(fallback):
        return fallback
    raise NotConnectedError(
        "composio CLI not found. Install it with:\n"
        "  curl -fsSL https://composio.dev/install | sh\n"
        "then open a new terminal and run: composio login"
    )


def _run(args: list[str], timeout: int = CLI_TIMEOUT_SECS) -> str:
    try:
        result = subprocess.run(
            [_cli()] + args, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise ComposioError(f"composio {' '.join(args)} timed out after {timeout}s") from e
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise ComposioError(f"composio {' '.join(args)} failed: {detail[:400]}")
    return result.stdout


def _load_spilled(slug: str, envelope: dict) -> dict:
    """
    Recover a response Composio wrote to disk instead of returning inline.

    Above roughly 10,000 tokens of output the CLI stops inlining the payload. Instead it
    writes the whole envelope to a temp file and hands back a stub that carries
    `storedInFile`, `tokenCount` and `outputFilePath` — and **no `data` key at all**:

        {"successful": true, "error": null, "logId": "log_...",
         "storedInFile": true, "tokenCount": 10328,
         "outputFilePath": "/var/folders/.../INSTAGRAM_GET_IG_USER_MEDIA_OUTPUT_x.json"}

    `successful` is still true and `error` is still null, so nothing looks wrong. Read
    the spill file and the real payload is all there, `data` included.

    This is the single nastiest failure mode in this wrapper, because the stub is a
    *success*. Before this function existed, `_execute` did `payload.get("data") or {}`,
    so every spilled response became an empty dict and every caller silently saw
    nothing: `reels --limit 25` returned `{"n": 0, "reels": []}` on an account with 9
    reels, and a postmortem built on it reported no data rather than an error.

    Whether a call spills depends on total output size, not on the limit you asked for,
    so it is not reproducible by item count alone — asking for more *fields* tips a call
    over just as easily as asking for more items. Confirmed live 2026-08-27 on a 9-reel
    account: MEDIA_FIELDS (which includes both media_url and thumbnail_url, ~2KB/item)
    spilled at limit>=9 while the same limit with a light field set stayed inline.
    """
    path = envelope.get("outputFilePath")
    if not envelope.get("storedInFile") or not path:
        raise ComposioSpillError(
            f"{slug} reported success but returned no 'data' key, and no spill file to "
            f"read it from. Envelope: {json.dumps(envelope)[:300]}"
        )
    try:
        with open(path, encoding="utf-8") as fh:
            spilled = json.load(fh)
    except FileNotFoundError as e:
        raise ComposioSpillError(
            f"{slug} spilled its {envelope.get('tokenCount')}-token response to {path}, "
            f"but that file is missing. It lives in the OS temp dir, so it can be swept "
            f"between the call and this read. Re-run the call; if it keeps happening, "
            f"request fewer fields or a smaller limit so the response stays inline."
        ) from e
    except (OSError, json.JSONDecodeError) as e:
        raise ComposioSpillError(f"{slug} spill file {path} is unreadable: {e}") from e

    # The spilled copy carries its own envelope, and it is the authoritative one.
    if not spilled.get("successful", True):
        raise ComposioError(f"{slug} failed inside its spill file: {spilled.get('error')}")
    if "data" not in spilled:
        raise ComposioSpillError(
            f"{slug} spill file {path} has no 'data' key either. Keys present: "
            f"{sorted(spilled)}"
        )
    return spilled


def _execute(slug: str, data: dict, account: str | None = None) -> dict:
    """
    Run one Composio tool. Composio wraps every response as
    {"successful": bool, "data": ..., "error": ...} — unwrap it here so callers never
    have to know that, and raise on the failure case rather than returning a dict that
    looks almost right.

    Large responses are the exception: they come back as a stub pointing at a temp file
    with no `data` key, which _load_spilled() reads back. Everything above this line
    behaves identically whether or not a given call happened to spill.
    """
    args = ["execute", slug, "-d", json.dumps(data)]
    if account:
        args += ["--account", account]
    raw = _run(args)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ComposioError(f"{slug} returned non-JSON: {raw[:200]}") from e
    if not payload.get("successful"):
        raise ComposioError(f"{slug} failed: {payload.get('error') or payload}")
    if "data" not in payload:
        payload = _load_spilled(slug, payload)
    return payload.get("data") or {}


def check() -> dict:
    """Is the CLI present, logged in, and is an Instagram account connected?"""
    try:
        cli = _cli()
    except NotConnectedError as e:
        return {"ok": False, "stage": "install", "error": str(e)}

    try:
        who = _run(["whoami"]).strip()
    except ComposioError as e:
        return {"ok": False, "stage": "login", "error": str(e)}
    if not who:
        return {
            "ok": False, "stage": "login",
            "error": "Not logged in. Run `composio login --no-wait` to get a URL, "
                     "open it, then run `composio login --poll`.",
        }
    try:
        account = json.loads(who)
    except json.JSONDecodeError:
        account = {"raw": who}

    conns = connections()
    ig = conns.get("instagram") or []
    active = [c for c in ig if c.get("status") == "ACTIVE"]
    if not active:
        return {
            "ok": False, "stage": "connect", "cli": cli, "account": account,
            "error": "No active Instagram connection. Run `composio link instagram`.",
        }
    return {"ok": True, "cli": cli, "account": account, "instagram": active}


def connections() -> dict:
    """Connected accounts per toolkit. Note the required `list` subcommand."""
    raw = _run(["connections", "list"])
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def get_user_info(account: str | None = None) -> dict:
    """Handle, follower count, media count, account type for the connected page."""
    return _execute("INSTAGRAM_GET_USER_INFO", {}, account)


def get_media(limit: int = 25, account: str | None = None) -> list[dict]:
    """
    Recent media. Remember: the metrics fields come back absent here — this is the
    list of WHAT was posted, not how it did. Pair with get_insights().
    """
    data = _execute(
        "INSTAGRAM_GET_IG_USER_MEDIA",
        {"ig_user_id": "me", "limit": limit, "fields": MEDIA_FIELDS},
        account,
    )
    return data.get("data") or []


def get_insights(media_id: str, metrics: list[str] | None = None,
                 account: str | None = None) -> dict:
    """
    Lifetime insights for one media item, flattened to {metric_name: value}.
    Returns {} rather than raising when a media item has no insights at all — a
    non-reel or a very fresh post legitimately has none, and that shouldn't abort
    a whole batch.

    A ComposioSpillError is deliberately NOT swallowed: "we lost the response" is not
    the same as "this post has no insights," and collapsing the two would put zeros
    into a baseline.
    """
    try:
        data = _execute(
            "INSTAGRAM_GET_IG_MEDIA_INSIGHTS",
            {"ig_media_id": media_id, "metric": metrics or REEL_METRICS},
            account,
        )
    except ComposioSpillError:
        raise
    except ComposioError:
        return {}
    out = {}
    for item in data.get("data") or []:
        values = item.get("values") or [{}]
        out[item.get("name")] = values[0].get("value")
    return out


def to_apify_shape(media: dict, insights: dict, duration_sec: float | None = None) -> dict:
    """
    Re-key a Graph API reel into the field names lib/outlier_scoring.py expects.

    This is the whole reason the rest of the plugin needs no changes to consume
    first-party data: compute_baseline() and score_reel() read videoPlayCount /
    likesCount / commentsCount / timestamp / productType, so we hand them exactly
    that. The first-party-only metrics are carried alongside under underscore-prefixed
    keys, where the scoring code ignores them but callers can still use them — those
    are the ones that actually explain an outlier.

    DURATION GAP — read this before trusting a score. The Graph API has no duration
    field on media (it isn't in the documented `fields` list at all), so unless a
    caller passes duration_sec, `videoDuration` is absent and score_reel()'s
    completion_bonus (10 points) can NEVER fire. That makes every Composio-sourced
    score up to 10 points lower than the same reel scored from Apify data, which is
    exactly the kind of quiet discrepancy that makes two runs disagree for no visible
    reason. Two ways to fill it:
      - download `_media_url` and call lib/ffmpeg_analysis.get_duration() (free, exact)
      - carry a known duration through from an earlier ffmpeg pass
    When you can't, say the score is a floor rather than presenting it as final.
    """
    product = (media.get("media_product_type") or "").lower()
    return {
        # Omitted entirely rather than set to None: _duration_of() checks isinstance,
        # so a None would read the same as absent but hides the intent.
        **({"videoDuration": duration_sec} if isinstance(duration_sec, (int, float)) else {}),
        "id": media.get("id"),
        "url": media.get("permalink"),
        "caption": media.get("caption"),
        "timestamp": media.get("timestamp"),
        # 'clips' is what is_reel() checks for; Graph returns REELS for reels.
        "productType": "clips" if product == "reels" else product,
        "type": "Video" if (media.get("media_type") or "").upper() == "VIDEO" else media.get("media_type"),
        "videoPlayCount": insights.get("views"),
        "likesCount": insights.get("likes") or 0,
        "commentsCount": insights.get("comments") or 0,
        # First-party only — invisible to every Apify actor.
        "_reach": insights.get("reach"),
        "_saves": insights.get("saved"),
        "_shares": insights.get("shares"),
        "_interactions": insights.get("total_interactions"),
        "_avg_watch_ms": insights.get("ig_reels_avg_watch_time"),
        "_total_watch_ms": insights.get("ig_reels_video_view_total_time"),
        "_media_url": media.get("media_url"),
        "_thumbnail_url": media.get("thumbnail_url"),
    }


def get_reels_with_insights(limit: int = 25, account: str | None = None,
                            durations: dict | None = None) -> list[dict]:
    """
    The function most callers want: recent reels with their real numbers attached,
    already in the shape outlier_scoring.py reads.

    Costs one API call for the list plus one per reel. Free in money, but it does
    spend rate limit, so ask for the smallest limit that answers your question.

    durations: optional {media_id: seconds} to close the duration gap described in
    to_apify_shape(). Without it, completion_bonus can't fire and scores read low.
    """
    durations = durations or {}
    reels = []
    for m in get_media(limit=limit, account=account):
        if (m.get("media_type") or "").upper() != "VIDEO":
            continue
        reels.append(to_apify_shape(
            m, get_insights(m["id"], account=account), durations.get(m["id"])))
    return reels


def summarize(reels: list[dict]) -> dict:
    """Quick descriptive stats for the analyze-then-confirm step in ig-setup."""
    def vals(key):
        return [r[key] for r in reels if isinstance(r.get(key), (int, float))]
    views, saves, reach = vals("videoPlayCount"), vals("_saves"), vals("_reach")
    return {
        "n_reels": len(reels),
        "median_views": statistics.median(views) if views else None,
        "total_saves": sum(saves) if saves else 0,
        "median_reach": statistics.median(reach) if reach else None,
        "best": max(reels, key=lambda r: r.get("videoPlayCount") or 0) if views else None,
        "captions": [r.get("caption") for r in reels if r.get("caption")],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="CLI installed, logged in, Instagram connected?")
    sub.add_parser("connections", help="list connected accounts as JSON")

    for name, helptext in (("user-info", "handle, followers, media count"),
                           ("reels", "recent reels with first-party insights")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--account", default=None,
                       help="connected account word_id/alias (required once 2+ pages are linked)")
        if name == "reels":
            p.add_argument("--limit", type=int, default=25)

    p_ins = sub.add_parser("insights", help="lifetime insights for one media id")
    p_ins.add_argument("--media-id", required=True)
    p_ins.add_argument("--account", default=None)

    args = parser.parse_args()

    try:
        if args.command == "check":
            result = check()
            print(json.dumps(result, indent=1))
            return 0 if result.get("ok") else 4
        if args.command == "connections":
            print(json.dumps(connections(), indent=1))
        elif args.command == "user-info":
            print(json.dumps(get_user_info(args.account), indent=1))
        elif args.command == "reels":
            reels = get_reels_with_insights(args.limit, args.account)
            print(json.dumps({"n": len(reels), "reels": reels}, indent=1))
        elif args.command == "insights":
            print(json.dumps(get_insights(args.media_id, account=args.account), indent=1))
    except NotConnectedError as e:
        print(json.dumps({"ok": False, "error": str(e)}, indent=1), file=sys.stderr)
        return 4
    except ComposioError as e:
        print(json.dumps({"ok": False, "error": str(e)}, indent=1), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
