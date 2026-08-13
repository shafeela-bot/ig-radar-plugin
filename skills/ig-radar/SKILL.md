---
name: ig-radar
description: Runs an outlier sweep across the teammate's tracked competitors and hashtags, scores everything with the 100-point formula, extracts cross-competitor patterns, surfaces niche-wide trends, and refills the script queue. Manually triggered (labeled "weekly" in config, but no real automation) via /ig-radar, or offered automatically at the end of /ig-setup.
---

# ig-radar: the outlier sweep

Budget ceiling for a full run: `apify.budget_caps_usd.weekly_radar_sweep` (default
$4.00 — a hard stop, not a target). Be upfront in the delivered summary about real
costs here: a prior build's live testing found the transcript add-on runs closer to
a flat ~$0.05/reel than a cheap per-1000 rate, and this sweep transcribes 15 reels
(not 5), so realistic total cost is closer to **$1.95–2.10**, not the PRD's original
$1.72 estimate. Say the real number, not the aspirational one.

Never let one bad API call kill the whole sweep. Wrap every Apify call, catch
errors, log the failure to `logs/ig-radar-<date>.log`, skip that item, and keep
going. A partial shortlist beats a crashed run.

## 1. Load config

Read `config/user_config.json`. If it doesn't exist, stop and say so — point them at
`/ig-setup`, don't try to proceed with defaults. Pull:
- `competitors.{north_stars,peers,wild_cards}` → flatten to one list of handles for
  the sweep, but keep tier info around for the summary.
- `hashtags.tracked`
- `scoring.*` (the 100-point formula's weights/thresholds — fall back to the
  defaults in `lib/outlier_scoring.py` if a key is missing)

## 2. Competitor sweep

For each competitor handle, pull their latest 20 reels:
```
python3 lib/apify_client.py run-actor \
  --actor apify/instagram-reel-scraper \
  --input '{"username": ["handle"], "resultsLimit": 20}' \
  --budget-cap <remaining budget> --expected-results 20
```
Batch all usernames into one call rather than one per competitor — cheaper on
overhead, easier to budget-check as a single estimate.

Filter to reels posted within the last 30 days for scoring purposes (older reels in
the pull are fine to ignore rather than erroring on).

For each competitor, check `data/baselines/<handle>.json`:
- Missing or stale (`is_baseline_stale()`, >30 days) → recompute via
  `compute_baseline()` + `save_baseline()` from the reels you just pulled. 20 reels
  is a smaller window than the ideal 30-day pool, but it's what's affordable
  per-run — this isn't a precision instrument, it's a triage signal.
- Fresh → use the cached baseline, don't recompute.

## 3. Hashtag sweep

For each tracked hashtag, pull the top 30 recent reels:
```
python3 lib/apify_client.py run-actor \
  --actor apify/instagram-hashtag-scraper \
  --input '{"hashtags": ["tag1","tag2",...], "resultsType": "reels", "resultsLimit": 30}' \
  --budget-cap <remaining budget> --expected-results 300
```
One batched call across all tracked hashtags, same reasoning as above.

Hashtag-sweep reels won't always belong to a tracked competitor. For those, use
whatever baseline you can — a known competitor's cached baseline if the creator
happens to match one, otherwise skip baseline-relative scoring and rely on the
absolute components of the 100-point formula (save signal, completion, recency) that
don't need a per-creator median.

## 4. Score everything

Use `lib/outlier_scoring.py`'s `score_reel`/`score_batch` — the 100-point formula
(view/comment/like score + save signal + completion bonus + recency bonus, capped at
100, tagged 🔴/🟡/⚪). Apply `is_reel()` filtering first — hashtag-scraper output can
include non-reels if `resultsType` didn't fully filter upstream.

## 5. Shortlist

Use `shortlist()` from `lib/outlier_scoring.py`: top 5 🔴 per competitor, filling with
🟡 if fewer than 5 🔴 exist for that competitor, capped at 30 total across the sweep.

## 6. Transcribe shortlist (top 15 by score)

Never transcribe the full pull — only the top 15 by score from the shortlist. The
actor takes post URLs through the same `username` field it takes handles through —
there's no separate `directUrls` field:
```
python3 lib/apify_client.py run-actor \
  --actor apify/instagram-reel-scraper \
  --input '{"username": ["url1","url2",...], "includeTranscript": true}' \
  --budget-cap <remaining budget> --expected-results 15 --with-transcript
```
This is the single biggest cost line in the sweep at real observed pricing — budget
for it explicitly rather than treating it as an afterthought.

## 7. Deep breakdown on top 10

Invoke the **ig-outlier-breakdown** skill once per reel for the top 10 by score (not
all 15 transcribed — the extra 5 transcripts exist so the *pattern extraction* step
below has more classified data to work with, even for items that don't get a full
individual breakdown). Each breakdown must produce classified fields
(`hook_format`, `format`, `length_bracket`, `trigger`, `cta_present`,
`posted_day_of_week`) — not just prose — since `ig-pattern-extraction` needs those
fields verbatim to do its counting.

## 8. Cross-competitor pattern extraction

Invoke **ig-pattern-extraction** with all classified breakdowns from step 7 (plus any
additional classified items from the extra 5 transcribed-but-not-deep-broken-down
reels, if you classified those too — more data points strengthens the "2+
competitors" signal). Minimum 5 patterns in the delivered report; if fewer emerge
naturally, say so rather than padding with weak ones.

## 9. Trends aggregation — "This Week in Your Niche"

Across *every* reel pulled this run (competitor sweep + hashtag sweep combined), not
just the shortlist. Marginal cost ~$0 — pure computation over data already pulled:
```
python3 lib/trends_aggregation.py --reels-json <path to combined reel pool>
```
Or import `build_trends_report()` directly. Returns audio trends (≥3 distinct
creators — can legitimately come back empty, that's a real result not a failure),
keyword topic clusters, format/trigger distributions with `_overperforming` lists,
and hashtags rising vs. baseline (≥2 distinct creators required — a single viral
post's tag choices aren't a trend).

**Formats and triggers here are caption+metadata heuristics, not a verified video
read** — most of the pool never gets transcribed. Say so explicitly when delivering
this section.

## 10. Queue update

Read `data/queue/current.json` (create it with an empty `queue: []` if missing —
never overwrite existing entries). Append every shortlisted item as a new queue
entry with `status: "ready"`:
```json
{"id": "OUT-<date>-<NN>", "outlier_data_path": "data/outliers/<date>.json",
 "competitor": "@handle", "score": <0-100>, "trigger": "<one of 7>",
 "replicability": <1-5, from the breakdown's virality scorecard if available>,
 "status": "ready", "added": "<ISO timestamp>", "used_at": null}
```
Preserve every existing entry regardless of status — `used` items stay for history,
never auto-deleted. If the ready count (across old + new) is below 3 even after this
sweep, say so in the delivery.

## 11. Optional ffmpeg pass on top 3 (phase 2)

Check `which ffmpeg`. If available, download video files for the top 3 by score and
run `lib/ffmpeg_analysis.py` for real cut counts, shot lengths, and loudness curves.
If not installed, skip silently — the breakdown skill already handles missing
ffmpeg data gracefully. Don't block the sweep on this optional dependency.

## 12. Save

Write the full run — shortlist + breakdowns + patterns + trends + metadata (date,
total spend, competitor/hashtag counts, any errors logged) — to
`data/outliers/<YYYY-MM-DD>.json`.

## 13. Deliver

`delivery.mode` is `claude_chat` right now (email/Slack aren't built yet) — present
in chat, in this order: **trends first, then outliers, then patterns, then a
suggested next action.**

> "Here's what's moving in your niche this week: [trends summary, with the
> caption-heuristic caveat]. Formats/triggers are estimates, not a verified read.
>
> Now the individual wins — N outliers worth your time, cost about $X.XX. Top pick:
> @handle's reel scored 87/100, trigger: curiosity_gap. [one-line hook description]
>
> Cross-competitor patterns: [list, each with confidence tier]
>
> Try `/ig-script OUT-<date>-01` next, or `/ig-queue` to see everything that's ready."

If ready-queue count is below 3, mention it plainly rather than burying it.
