# ig-radar-plugin

A Claude Code plugin that finds the Instagram Reels blowing up in your niche, names
the exact psychological trigger behind why they hooked people, extracts patterns
that repeat across your competitors, and writes scripts in *your* voice — not
ChatGPT's. Built for a small team of creators, each with their own niche, own
config, own everything.

**Credit**: the outlier scoring formula, psychological trigger taxonomy, and
cross-competitor pattern-extraction method are absorbed from a teammate's
`social-media-marketing-specialist` skill. See the header comments in
`lib/outlier_scoring.py` and `lib/pattern_extraction.py` for full credit.

## Who this is for

Teammates comfortable with Claude Code, terminal, and git — but nobody should need
to write code. The setup wizard handles everything.

## Quick start

```
git clone <this repo>
cd ig-radar-plugin
claude
```

That's it — no `pip install`, no build step. The first time you open Claude Code in
this folder, it reads `SETUP.md`, notices you don't have a config yet, and walks you
through onboarding. Budget about 10 minutes, mostly tapping through choices.

## The commands

| Command | What it does |
|---|---|
| `/ig-setup` | Onboarding wizard. Runs automatically on first use; re-run manually to start over. |
| `/ig-radar` | Runs a fresh outlier sweep, extracts cross-competitor patterns, surfaces niche trends, and refills your script queue. |
| `/ig-queue` | See what's ready to script vs. already used. |
| `/ig-script [outlier_id]` | Turns a queued outlier into 3 script variations in your voice. |
| `/ig-postmortem [url]` | Analyzes one of your own posted reels against your baseline. |
| `/ig-reconfigure` | Change competitors, hashtags, banned phrases, voice fingerprint, cadence, or your Apify token — one friendly menu. |
| `/ig-voice-profile` / `/ig-voice-refresh` | Build or refresh your voice fingerprint from newer content. |

## How it's different from Virlo/Shortimize/Octupie-style tools

Those stop at "here's a video with high engagement." This plugin:
- Scores on 6 signals, not just views (comments, likes, save-intent, completion
  estimate, recency) — see `docs/understanding-outlier-scores.md`
- Names the specific psychological trigger behind every hook — see
  `docs/psychological-triggers-guide.md`
- Finds patterns that repeat across 2+ competitors (a pattern in one is noise, in
  two is signal)
- Generates scripts matched to *your* voice fingerprint, gated through an
  anti-AI-slop detector, not generic output

## What's built and live-tested (not just written)

Every piece below was run against real Apify data during this build, not just
coded and assumed correct:
- Full onboarding wizard, budget-capped Apify calls throughout
- 100-point outlier scoring — validated to stay well-bounded even against noisy
  small-account baselines (unlike a raw view-multiplier approach, which produces
  absurd artifacts on the same kind of data)
- Cross-competitor pattern extraction — two real bugs found and fixed via live
  testing (a missing-data sentinel that read as a false pattern; a group-selection
  order bug that let a lone standout block a real 5-competitor pattern)
- "This Week in Your Niche" trends pass across every reel in a sweep, not just the
  shortlist, at ~$0 marginal cost
- Voice-fingerprint-matched script generation with a real anti-slop gate (banned
  phrases, generic AI patterns, sentence-length variance, vocabulary mismatch,
  trigger mismatch) — tested against both true-negative and true-positive cases,
  not just the happy path
- The script queue: persists across sweeps, never silently deletes history

Deliberately deferred for now (flagged honestly in the wizard, not silently
half-built):
- **Real automated scheduling** — `radar_frequency` is a config label; `/ig-radar`
  is always manually triggered. The queue is designed to tolerate irregular timing.
- **Email/Slack delivery** — collected as a preference, not wired up yet. Chat +
  local files only.
- **ffmpeg deep analysis** — built and unit-tested, but this build's environment
  doesn't have ffmpeg installed, so it's never been run against a real video. Every
  caller checks `which ffmpeg` first and degrades gracefully if it's missing.

## Real costs (not the optimistic pre-tested estimate)

See `docs/how-to-get-apify-token.md` for the full breakdown — short version: the
transcript add-on runs closer to a flat ~$0.05/reel than a cheap volume-scaled rate,
which pushes weekly sweep costs to roughly $2.00–2.20 rather than the original $1.72
target. Every call still has a hard budget cap regardless — worst case is a blocked
call with a clear message, never a silent overspend.

## Repo layout

```
ig-radar-plugin/
├── SETUP.md              # First-run behavior — read this first if you're Claude
├── skills/                # 9 skills, one per command (+ 2 internal: outlier-breakdown, pattern-extraction)
├── config/                # Templates (shared) + real config (gitignored, personal)
├── lib/                   # Pure-Python logic: scoring, patterns, trends, anti-slop, Apify client
├── data/                  # All gitignored — outliers, queue, baselines, postmortems, transcripts
└── docs/                  # Setup guides, cost model, troubleshooting
```

Only `config/*.template.json`, `config/psychological_triggers.json` (shared
reference data, not personal), and everything in `docs/`/`skills/`/`lib/` are
tracked in git. Everything under `data/`, plus `config/user_config.json`,
`config/voice_fingerprint.json`, `config/banned_phrases.txt`, and `.env`, stays
local per teammate.
