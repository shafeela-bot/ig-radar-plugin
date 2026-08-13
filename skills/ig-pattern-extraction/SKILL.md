---
name: ig-pattern-extraction
description: Finds patterns appearing across 2+ competitors' outlier breakdowns — a pattern in one competitor is noise, in two is signal. Called by ig-radar after ig-outlier-breakdown produces classified fields for the sweep's top 10-15 items. Absorbed from the social-media-marketing-specialist skill; see lib/pattern_extraction.py header for full credit.
---

# ig-pattern-extraction: what repeats isn't an accident

`lib/pattern_extraction.py` does the counting — grouping this sweep's classified
breakdowns by `hook_format`, `format`, `length_bracket`, `trigger`, `cta_present`,
and `posted_day_of_week`, and returning which values repeat across 2+ competitors.
Your job is turning that structured output into something the teammate can act on.

## Input

The list of classified breakdowns from this sweep's `ig-outlier-breakdown` runs
(top 10 deep-broken-down, plus any of the extra 5 transcribed-but-not-deep-broken
items you also classified). Optionally, the teammate's own past topics (from prior
`data/outliers/*.json` breakdowns or `data/postmortems/*.json`) for the
underserved-angle check — if this is a first sweep with no history, that check will
come back empty, which is expected, not broken.

## Run the extraction

```
python3 lib/pattern_extraction.py --breakdowns-json <path> [--teammate-topics-json <path>]
```
Or import `extract_all_patterns()` directly.

## For each pattern returned, write the full card

```
🔍 PATTERN #N: [Pattern name — human-readable, not the raw category id]
FOUND IN: [@competitor1, @competitor2, ...]
WHAT IT IS: [2-sentence description of the actual pattern, grounded in the data]
WHY IT WORKS: [The psychology behind it — connect back to the trigger taxonomy in
  config/psychological_triggers.json where relevant]
YOUR OPPORTUNITY: [A specific angle to apply this in *this teammate's* niche —
  concrete, referencing their actual content style from config/user_config.json,
  not generic advice]
CONFIDENCE: HIGH (3+ competitors) / MEDIUM (2 competitors) / SIGNAL (1 competitor,
  strong data — only the underserved-angle category can hit SIGNAL; everything else
  requires the 2+ bar to appear at all)
```

**Minimum 5 patterns per weekly report.** If the extraction genuinely returns fewer
(small sweep, thin data), say so honestly rather than padding with a weak repeat of
an existing pattern reworded — "only 3 real patterns emerged this week, here's why"
is a better report than 5 patterns where 2 are filler.

The **underserved angle** pattern is the one worth calling out distinctly when it
appears — it's explicitly the "gold" category per the PRD's own framing (a topic
competitors are winning with that this teammate hasn't touched yet). Don't bury it
in the middle of the list.

## Output

Present all patterns in chat as part of `/ig-radar`'s delivery (after trends, before
the individual outlier list — see `ig-radar` step 13). Save the full structured list
alongside the sweep's other data in `data/outliers/<date>.json` under a `patterns`
key.
