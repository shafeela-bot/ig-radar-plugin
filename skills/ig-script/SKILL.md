---
name: ig-script
description: Generates 3 voice-matched script variations (A/B/C) from a queued outlier, gated through the anti-slop detector. Marks the queue item used on success. Invoked via /ig-script [outlier_id].
---

# ig-script: turn a queued outlier into scripts that sound like you

## 1. Load context

- The outlier's breakdown from `data/outliers/<date>.json` (hook trigger, structure,
  virality scorecard, why-it-worked synthesis) — find it via the queue entry's
  `outlier_data_path`. If this specific outlier doesn't have a breakdown yet (it was
  shortlisted but not in the top 10 that got a full `ig-outlier-breakdown` pass), run
  that skill on it first rather than generating blind.
- `config/voice_fingerprint.json`
- `config/banned_phrases.txt`
- `config/user_config.json` → `niche.description`

If the voice fingerprint is missing entirely, stop and point to `/ig-voice-profile` —
don't generate "in their voice" with no voice data to work from.

**If the source outlier's hook was meme-audio-driven rather than narrated** (check
the breakdown's `hook_type` — `Audio` with `trigger: none`, or a `_method_note` from
trends flagging it), say so before generating: "heads up, this one rode a trending
sound rather than a specific hook line — the script below reinterprets the *format*
(short, sound-driven, low/no narration), not a verbal hook that didn't really exist
in the original." Don't fabricate a verbal hook line that the source never had.

## 2. Generate 3 variations (A / B / C)

Each reinterprets the outlier's **structure** — hook trigger, retention beat
mechanism, CTA shape — for this teammate's niche, in their voice. Never reuse the
original's exact wording, specific claims, or specific numbers; reference the
pattern, not the words.

- **Idea A** — same topic, different angle (e.g. a more controversial or contrarian
  take on the same underlying subject)
- **Idea B** — format variation (e.g. POV instead of tutorial, or vice versa —
  whatever the source format wasn't)
- **Idea C** — topical hook variation (tie the same underlying structure to a
  currently trending event, tool release, or meme format — check this week's
  `data/outliers/<date>.json` → `trends` for something genuinely current rather than
  inventing a fake trend)

The psychological trigger (from the breakdown's `trigger` field, one of the 7 in
`config/psychological_triggers.json`) is what the hook is actually *for* — keeping it
intact across a variation while changing its surface form is a legitimate way to
vary structure without losing why the original worked. If the source had no clear
trigger (meme/entertainment-driven), don't force one onto these variations either.

## 3. Run each variation through the anti-slop gate

```
python3 lib/script_slop_detector.py --text-file <spoken-text-only, not stage directions> \
  --banned-phrases config/banned_phrases.txt --fingerprint config/voice_fingerprint.json \
  --intended-trigger <this variation's trigger, or omit if none>
```

**Only check the actual spoken/on-screen text, not your own scene-direction
scaffolding** (timestamps, "[cut to...]" labels) — those aren't part of the script
the teammate performs, and checking them would produce false em-dash/length flags
from your own formatting, not their voice.

- Hard failures (banned phrases, generic AI-slop patterns, unexplained em-dash
  density) → regenerate that variation, up to 3 times total.
- Soft warnings (sentence-length variance, vocabulary mismatch, trigger heuristic
  mismatch) → don't block, but mention them when presenting the variation.
- **3 hard fails on the same variation** → surface to the teammate: "this outlier's
  hard to adapt to your voice — want to try a different one?" Don't silently ship a
  variation that never actually passed.

## 4. Present all 3 clean variations

For each:
- **Hook** — visual direction + exact opening line (or, for meme-format
  reinterpretations, the on-screen text + sound direction instead of a spoken line)
- **Full script** — scene-by-scene with stage directions
- **Thumbnail overlay text** (max ~6 words)
- **Caption draft**
- **Hashtag recommendations** — pull from `config/user_config.json` →
  `hashtags.tracked` plus 1-2 specific to this script's actual topic
- Close with **which of the 3 to shoot first**, one sentence why (tie it to the
  breakdown's `replicability` score and this teammate's actual constraints — e.g.
  "B's the easiest lift since it's just a screen recording, no on-camera time needed")

## 5. Mark the queue item used

Update `data/queue/current.json`: flip this outlier's entry to `status: "used"`,
set `used_at` to now. Never delete the entry — used items stay for history.
