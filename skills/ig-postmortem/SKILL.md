---
name: ig-postmortem
description: Analyzes one of the teammate's own posted reels against their own rolling baseline, using the same 100-point score and breakdown structure as competitor outliers. Conversational, not a report dump — the teammate can ask follow-ups. Invoked via /ig-postmortem [url].
---

# ig-postmortem: how did that one actually do?

## 1. Get the reel — Composio first, it's free and tells you more

This is their own post, so use the Graph API rather than paying to scrape a page they
own:

```
python3 lib/composio_client.py reels --limit 25 --account <accounts.composio_account>
```

Match the reel by its `permalink` against the URL they gave you. This returns what
Apify structurally cannot see, and these are usually the metrics that explain the
result:

| Field | Why it matters |
|---|---|
| `_saves` | The strongest ranking input on Reels. Views alone routinely understate an outlier |
| `_shares` | Distinguishes "watched" from "worth passing on" |
| `_reach` | Views ÷ reach tells you rewatches; reach vs followers tells you how much was cold traffic |
| `_avg_watch_ms` | Retention, once you know the duration — the single best predictor here |

**Two gaps to handle rather than ignore:**

- **No duration**, so `completion_bonus` (10 points) cannot fire and the score reads up
  to 10 low. Fill it by downloading `_media_url` and calling
  `lib/ffmpeg_analysis.get_duration()`, then pass it via `to_apify_shape(..., duration_sec=)`.
  Free and exact. If you skip it, call the score a floor, not a result.
- **No speech transcript.** For text-on-screen creators, read the burned-in text off
  frames with ffmpeg — that *is* the script. Only fall back to the Apify path for a
  genuine voiceover, and say why you're spending.

**Apify fallback** (no Composio connection, or a reel that isn't theirs), budget-capped
at `apify.budget_caps_usd.postmortem`, default $0.15:
```
python3 lib/apify_client.py run-actor \
  --actor apify/instagram-reel-scraper \
  --input '{"username": ["<url>"], "includeTranscript": true}' \
  --budget-cap 0.15 --expected-results 1 --with-transcript
```
The actor takes URLs through the same `username` field it takes handles through —
there's no separate `directUrls` field.

## 2. Compute their own baseline

Check `data/baselines/<their-handle>.json` (use `config/user_config.json` →
`accounts.primary_handle`, or `additional_handles` if they specify a different one of
their own accounts). If missing or stale (`is_baseline_stale()`, >30 days), rebuild it
from the same free Composio pull as step 1 — `compute_baseline()` reads the shape
`composio_client.to_apify_shape()` returns, so no conversion is needed:

```
python3 lib/composio_client.py reels --limit 30 --account <accounts.composio_account>
```
Then `compute_baseline()` + `save_baseline()` from `lib/outlier_scoring.py`.

Note the trim: `BASELINE_EXCLUDE_TOP_PCT` drops the top 10% by views, so a baseline
built while their outlier is recent excludes that outlier. That's intended — a baseline
shouldn't contain the hit it's being used to measure — but say so when you quote it,
otherwise the median looks wrong to them.

**Watch `MIN_VIEWS_FLOOR`.** It defaults to 20,000 in `lib/outlier_scoring.py`, tuned for
six-figure competitor accounts. On a small account every post scores 0 with reason
`below_min_views_floor` and the postmortem silently says nothing. Always pass
`scoring.min_views_floor` from their config, and if it's still the 20,000 default while
their median is in the hundreds, flag that the number needs recalibrating rather than
reporting a 0.

**Apify fallback** for the baseline, same cap:
```
python3 lib/apify_client.py run-actor \
  --actor apify/instagram-reel-scraper \
  --input '{"username": ["their-handle"], "resultsLimit": 30}' \
  --budget-cap 0.15 --expected-results 30
```

## 3. Score against their own baseline

Score this reel with `score_reel()` — same 100-point formula, same math as every
competitor outlier, just against the teammate's own median/avg-comments/avg-likes
instead of a competitor's.

## 4. Breakdown

Run the same structure `ig-outlier-breakdown` uses (hook deconstruction with
psychological trigger, content structure, outlier factor, virality scorecard) on
this reel. It's their own content, so lean into specificity rather than hedging.

## 5. Compare to their own top-quartile pattern

Run the same analysis `/ig-script` uses to find her proven patterns (do this *before*
step 6 saves the current reel, so it doesn't skew its own comparison):
```
python3 lib/own_pattern_analysis.py --postmortems-dir data/postmortems \
  --min-win-score <config/user_config.json → scoring.viral_threshold>
```
If it returns patterns, compare this reel's classified fields against them:
- **What worked**: fields on this reel that match a returned pattern's value
- **What underperformed**: patterns present in her history but *absent* on this reel —
  this is usually the more useful half
- **Specific next-time recommendations** — concrete, tied to her actual voice
  fingerprint and niche, not generic advice

If it returns an empty pattern list (fewer than 2 of her own postmortems have hit the
viral threshold yet), say so — there's no reliable historical pattern to compare
against yet, and that's fine, not a gap to apologize for. Just deliver the standalone
breakdown and score.

## 6. Save

Write to `data/postmortems/<YYYY-MM-DD>_<reel_id>.json` with the classified fields at
the top level, in the same names `ig-outlier-breakdown` uses. `/ig-script` reads this
same directory (via `lib/own_pattern_analysis.py`) to find what's proven to work for
her — keeping this shape consistent is what makes that loop actually function, not
just a nice-to-have:
```json
{
  "date": "YYYY-MM-DD",
  "url": "...",
  "reel_id": "...",
  "score": 0,
  "hook_format": "...",
  "format": "...",
  "length_bracket": "...",
  "trigger": "...",
  "cta_present": "...",
  "topic": "...",
  "outlier_factor": "...",
  "breakdown_prose": "the full hook deconstruction / structure / virality scorecard write-up",
  "comparison_prose": "the what-worked / what-underperformed / recommendations write-up from step 5, or null if this was her first postmortem"
}
```

## 7. Deliver conversationally

Not a report dump. Open with the score and the one-sentence takeaway, then let the
teammate ask follow-ups rather than front-loading everything:

> "That one scored 62/100 — solidly above-average, not quite a breakout. The hook
> leaned on curiosity_gap and it clearly worked (comment_score maxed out), but there
> was no clear CTA, and your last few wins all had one. Want the full breakdown, or
> just the one thing I'd change next time?"
