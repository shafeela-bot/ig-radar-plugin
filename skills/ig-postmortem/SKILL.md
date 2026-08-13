---
name: ig-postmortem
description: Analyzes one of the teammate's own posted reels against their own rolling baseline, using the same 100-point score and breakdown structure as competitor outliers. Conversational, not a report dump — the teammate can ask follow-ups. Invoked via /ig-postmortem [url].
---

# ig-postmortem: how did that one actually do?

## 1. Scrape the reel

Budget-capped at `apify.budget_caps_usd.postmortem` (default $0.15) — a single reel
with transcript is real money but small:
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
their own accounts). If missing or stale (`is_baseline_stale()`, >30 days), pull
their last 20-30 reels and compute it:
```
python3 lib/apify_client.py run-actor \
  --actor apify/instagram-reel-scraper \
  --input '{"username": ["their-handle"], "resultsLimit": 30}' \
  --budget-cap 0.15 --expected-results 30
```
Then `compute_baseline()` + `save_baseline()` from `lib/outlier_scoring.py`.

## 3. Score against their own baseline

Score this reel with `score_reel()` — same 100-point formula, same math as every
competitor outlier, just against the teammate's own median/avg-comments/avg-likes
instead of a competitor's.

## 4. Breakdown

Run the same structure `ig-outlier-breakdown` uses (hook deconstruction with
psychological trigger, content structure, outlier factor, virality scorecard) on
this reel. It's their own content, so lean into specificity rather than hedging.

## 5. Compare to their own top-quartile pattern

If they have enough history (multiple past postmortems or breakdowns of their own
content — check `data/postmortems/*.json`), compare this reel's classified fields
against what's repeated in their own past winners:
- **What worked**: patterns present here that also show up in their historical wins
- **What underperformed**: patterns present in their historical wins but *absent*
  here — this is usually the more useful half
- **Specific next-time recommendations** — concrete, tied to their actual voice
  fingerprint and niche, not generic advice

If this is their first postmortem, say so — there's no historical pattern to compare
against yet, and that's fine, not a gap to apologize for. Just deliver the standalone
breakdown and score.

## 6. Save

Write to `data/postmortems/<YYYY-MM-DD>_<reel_id>.json` — the score, breakdown, and
comparison (if any). This is what future postmortems compare against, so keep the
classified fields in the same vocabulary `ig-outlier-breakdown` uses.

## 7. Deliver conversationally

Not a report dump. Open with the score and the one-sentence takeaway, then let the
teammate ask follow-ups rather than front-loading everything:

> "That one scored 62/100 — solidly above-average, not quite a breakout. The hook
> leaned on curiosity_gap and it clearly worked (comment_score maxed out), but there
> was no clear CTA, and your last few wins all had one. Want the full breakdown, or
> just the one thing I'd change next time?"
