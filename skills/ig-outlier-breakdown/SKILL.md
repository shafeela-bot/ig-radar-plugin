---
name: ig-outlier-breakdown
description: Produces a structured decode of a single shortlisted outlier — hook deconstruction with psychological trigger, content structure, the one-sentence outlier factor, a 1-5 virality scorecard, and synthesis. Called by ig-radar on the top 10 of each sweep, and its output feeds ig-pattern-extraction directly, so the classified fields matter as much as the prose.
---

# ig-outlier-breakdown: decode a winner

This is the thing every competing tool skips — they stop at "this got a lot of
views." Your job is to explain *why*, specifically enough that the pattern is
reusable, not just observed.

**Important**: this skill's output isn't just for the teammate to read — `/ig-radar`
step 8 feeds it into `ig-pattern-extraction`, which does exact-match grouping on the
classified fields below (`hook_format`, `format`, `length_bracket`, `trigger`,
`cta_present`, `posted_day_of_week`). Use the *exact* vocabulary from each fixed list
— inventing a synonym ("tutorial-style" instead of "Tutorial") silently breaks the
cross-competitor grouping downstream.

## Input

One reel's data: caption, transcript (if pulled), engagement metrics, and — if
`lib/ffmpeg_analysis.py` ran on it — cut timestamps and loudness data. Missing
ffmpeg data isn't a blocker; estimate pacing/audio qualitatively from the transcript
and caption instead, and say so rather than presenting a guess as measured fact.

## Produce this structure

### Hook deconstruction

- **Hook type**: `Text` / `Visual` / `Audio` / `Combo`
- **Hook format**: `Question` / `Bold claim` / `Controversy` / `Pattern interrupt` /
  `Shock` / `Relatability` / `Pain` / `Curiosity gap` / `Hot take`
- **First line or visual**: what does the viewer see/hear in seconds 0–3? The actual
  first line if you have a transcript, otherwise your best inference from caption/context.
- **Psychological trigger**: exactly one of the 7 from `config/psychological_triggers.json`
  (`curiosity_gap` / `fear_fomo` / `identity_signal` / `pain_point` /
  `transformation_promise` / `social_proof` / `controversy_hot_take`). If genuinely
  none fit, say so explicitly rather than forcing a bad match — some winners work on
  pure entertainment with no psychological lever at all. Use the file's `id` values
  (snake_case), not the display names, when recording this field for downstream use.

### Content structure

- **Format**: `talking_head` / `tutorial` / `pov` / `text_on_screen` / `broll_voiceover`
  / `trend_audio` / `duet` / `stitch`
- **Length bracket**: `short` (<15s) / `medium` (15–30s) / `long` (30–60s) /
  `extended` (60s+)
- **Pacing**: `fast_cuts` / `slow_storytelling` / `mixed`
- **On-screen text density**: `heavy` / `minimal` / `none`
- **CTA present**: `comment` / `save` / `follow` / `share` / `soft` / `none`

### Outlier factor (one sentence)

What ONE thing made this reel different from the competitor's average content? Pick
the closest fit: `timing` / `format_shift` / `unexpected_topic` / `raw_emotion` /
`extreme_relatability` / `controversy` / `trend_jacking` /
`exceptional_educational_density` / `pure_entertainment` / `unique_pov` /
`vulnerable_personal_story`.

### Virality mechanics scorecard (1–5 each)

- **Hook strength**: does it demand attention in 3 seconds?
- **Emotional pull**: does it make you feel something?
- **Shareability**: would someone send this to a friend?
- **Save-worthiness**: does it contain info worth revisiting?
- **Replicability**: how easy for *this teammate* to adapt in their niche? (This
  number feeds the queue's `replicability` field — be honest, not generous. A 5 here
  should mean genuinely easy, not "technically possible.")

### Synthesis

- **Why it likely worked** — one paragraph. Tie the components together into a
  specific causal story, not a list recap. "The hook fires curiosity_gap, the
  mid-video pays it off with a numbered reveal, and the save-CTA converts that
  curiosity into save-intent — that combination is why this scored 87" is the bar.
  "Good hook and pacing" is not.
- **How to reinterpret this in the teammate's voice** — one paragraph pointing to
  specific `config/voice_fingerprint.json` hooks (their actual hook style, energy,
  preferred triggers if known) — concrete, not "this could work for you too."

## Also record (for pattern extraction and the queue)

- `competitor`: the handle this reel belongs to
- `score`: the 100-point score from `lib/outlier_scoring.py`
- `topic`: a short keyword/phrase for what this reel is actually about (feeds
  `ig-pattern-extraction`'s underserved-angle check)
- `posted_day_of_week`: derived from the reel's timestamp, if available

## Output

Present conversationally in chat, and save the full structured version (both the
classified fields and the prose) to `data/outliers/<date>.json` under a `breakdown`
key for that reel, so `/ig-script` and `ig-pattern-extraction` can both load it later
without re-deriving anything.
