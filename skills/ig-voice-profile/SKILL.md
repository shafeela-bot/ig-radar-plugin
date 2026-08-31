---
name: ig-voice-profile
description: Builds or refreshes config/voice_fingerprint.json from a teammate's own reels (or, for brand-new creators, from a short interview). Called internally by ig-setup during onboarding, and directly via /ig-voice-profile or /ig-voice-refresh (also accessible via the reconfigure menu) any time after that to rebuild from newer content.
---

# ig-voice-profile: build/refresh the voice fingerprint

This is the anti-slop foundation. `/ig-script` leans on this file to keep generated
scripts sounding like the teammate, not like a helpful assistant. Don't rush it, and
don't fabricate specificity you don't have — a thinner, honest fingerprint beats a
detailed-looking fake one.

## Tone

Same as everywhere else in this plugin: casual, warm, a little wry. This step in
particular can feel exposing ("here's what an AI thinks your voice sounds like") —
keep it collaborative, not clinical. Always let the teammate correct what you noticed.

## Determine mode

- **initial_setup** — invoked by `ig-setup` step 7. No existing fingerprint.
- **refresh** — invoked directly via `/ig-voice-profile` / `/ig-voice-refresh`, or
  from `/ig-reconfigure`. `config/voice_fingerprint.json` already exists; load it
  first, you'll merge into it.

## Step A — path fork (skip if refreshing; refresh always uses the upload path)

AskUserQuestion:
> "To make your scripts sound like *you* and not like a helpful AI assistant, I need
> to study your existing content. Two options:"
- Upload 10–30 of my recent reels (best)
- I'm new, just describe my voice in words

### Upload path

**Try Composio before spending anything.** If their Instagram is connected (it will be
when `ig-setup` Step 3 ran), their own reels come back free — and richer, since the
Graph API returns saves, shares, reach and average watch time that Apify cannot see:

```
python3 lib/composio_client.py check
python3 lib/composio_client.py reels --limit 30 --account <accounts.composio_account>
```

If `ig-setup` Step 3 already pulled this data in the same session, reuse it rather than
calling again — say so ("reusing what I pulled earlier").

What this gets you and what it doesn't:

- **Verbal patterns** — the Graph API returns captions, not speech. For text-on-screen
  creators the burned-in caption *is* the script, and you can read it off frames for
  free: download `_media_url` and extract frames with ffmpeg. Record which source you
  used in `built_from`, because burned-in text and spoken audio can differ, and a
  fingerprint that claims to know their spoken voice when it only saw captions is the
  kind of quiet wrongness that's hard to catch later.
- **Pacing and audio** — `_media_url` gives you the actual file, so `lib/ffmpeg_analysis.py`
  works on it directly. Free, and better than any estimate.
- **What it can't give you** — real speech transcripts. If the account is a talking-head
  and you need the spoken words, fall back to the Apify path below and say why you're
  spending.

**Sample size honesty.** `n_videos_analyzed` is the number of videos you actually
studied, not the number requested. If the account only has 6 reels, that's the ceiling —
keep `low_confidence: true` and say plainly that it's thin, rather than presenting a
five-video fingerprint as settled.

### Apify path (talking-head accounts, or no Composio connection)

1. Ask for their Instagram handle (skip if refreshing — reuse `built_from.source_handle`
   unless they say they want a different account analyzed).
2. Pull their reels + transcripts, budget-capped at
   `apify.budget_caps_usd.voice_fingerprint_build` (or `.voice_fingerprint_refresh` if
   refreshing — default $2.00 either way; the transcript add-on runs closer to a flat
   ~$0.05/reel than a volume-discounted rate, so 30 reels is a real ~$1.50, not a
   rounding error):
   ```
   python3 lib/apify_client.py run-actor \
     --actor apify/instagram-reel-scraper \
     --input '{"username": ["handle"], "resultsLimit": 30, "includeTranscript": true}' \
     --budget-cap 2.00 --expected-results 30 --with-transcript
   ```
   If refreshing, prefer reels newer than `built_from.date_built` — filter
   client-side after the pull if the actor doesn't take a date filter directly.
3. **Read the transcripts and captions yourself.** This is qualitative synthesis, not
   a script — no lib/ module does this for you. Look for:
   - `verbal_patterns.common_vocabulary` / `signature_phrases` / `allowed_fillers` /
     `banned_fillers` — words/phrases that show up often and feel characteristic,
     not generic; near-verbatim lines they reuse; whether "um"/"like" reads as
     authentic or gets edited out entirely.
   - `sentence_structure` — rough average sentence length, rhetorical-question
     frequency, contraction habits, any punctuation tic (trailing "...", em-dashes).
   - `hook_style.opening_type_distribution` — tally how their videos open across
     the sample. `avg_hook_duration_sec` — estimate from transcript timestamps if
     available; leave null if you can't estimate it honestly.
   - `hook_style.preferred_triggers` — using the 7-trigger taxonomy in
     `config/psychological_triggers.json`, which triggers does *this teammate's own
     content* actually lean on? This is different from any single outlier's
     trigger — it's their own pattern across their own sample. Leave empty if the
     sample's too thin or mixed to call a real preference.
4. **Pacing and audio** need actual video frame/waveform analysis, not just
   transcripts. Check `which ffmpeg`. If present and the actor response included
   downloadable video URLs, run `lib/ffmpeg_analysis.py` on a handful of the pulled
   videos and fold the results in; set `built_from.ffmpeg_analysis_included = true`.
   If ffmpeg isn't installed, leave those sections null, set the flag `false`, and
   mention pacing/audio analysis is available once ffmpeg's installed — don't
   pretend you analyzed something you didn't.
5. Draft the fingerprint. Present it conversationally, not as raw JSON:
   > "Here's what I noticed about your voice: you open with a direct question about
   > 60% of the time — usually a curiosity-gap or pain-point angle — average
   > sentence length runs short and punchy, you say 'honestly' a lot, and you never
   > use exclamation points even when the energy's high. Does this feel right?"
6. Free text: let them correct anything. Apply corrections directly — don't just
   note them and move on.
7. Set `built_from = {n_videos_analyzed, date_built: today, source_handle, method:
   "video_analysis", ffmpeg_analysis_included}`, `low_confidence: false`.

### New-creator path

Interactive elicitation via AskUserQuestion where the answer is a fixed set (hook
style, energy level), free text where it's genuinely open (vocabulary, specific
phrases they know they use or want to avoid):
- Hook style: question / bold claim / jump straight into action / direct-to-camera address
- Sentence rhythm: short and punchy / long and flowing / mixed
- Energy: high energy throughout / calm and steady / builds up over the video
- Free text: "Any words or phrases that are just *you*? Anything you know you overuse
  or want to avoid?"
- Filler tolerance: keep it raw (ums and likes are fine) / clean it up

Build a thinner fingerprint from these answers only — don't invent specifics you
weren't told (no fabricated `avg_length_words` number, for instance; leave numeric
fields null when they only came from a verbal description). Leave
`hook_style.preferred_triggers` empty — a self-description doesn't give you enough
to call a real trigger preference honestly.

Set `built_from = {n_videos_analyzed: 0, date_built: today, source_handle: null,
method: "self_description", ffmpeg_analysis_included: false}`, `low_confidence: true`.

## Refresh merge logic

When refreshing an existing (non-low-confidence) fingerprint with new video data:
- **Vocabulary/phrases**: union the old and new sets, but if something from the old
  list is completely absent from the new sample, ask before dropping it rather than
  silently deleting it.
- **Numeric fields**: recompute fresh from the new sample rather than averaging with
  stale numbers — recent content is the better signal for "how do you talk now."
- **preferred_triggers**: recompute from the new sample; if it's shifted from the old
  list, mention that explicitly ("you used to lean on pain_point a lot, this batch
  is mostly curiosity_gap — evolving on purpose, or worth knowing either way?").
- **low_confidence**: if the old fingerprint was `true` and this refresh used real
  video data, flip it to `false` and say so — that's a genuine upgrade worth
  mentioning.

## Finish

Write `config/voice_fingerprint.json` (following the shape in
`config/voice_fingerprint.template.json`). If this was called from `ig-setup`, return
control there. If called directly, give a short cheerful confirmation and mention
`/ig-script` is what actually uses this.
