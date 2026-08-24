# How a script gets built

`/ig-script` can hand you a script that reads well and is still unfalsifiable — if it
doesn't say which video it came from, you can't tell what to change when the post
underperforms. This doc is the method for building a script that carries its own
evidence, worked out during a real session on 2026-08-24.

Two things it insists on: **every creative choice names the measurement behind it**, and
**anything that isn't measured gets labelled a guess.** A thinner script with honest
provenance beats a confident one you can't debug.

## The steps

### 1. Score competitors against their own median, never against each other

An account with a 54,727-view median and one with an 8,047-view median are not
comparable in absolute views. Use `compute_baseline()` per channel, then `score_reel()`
against that channel's own baseline. A 59,828-view reel on a 21,487-median channel
(2.8x) is a stronger signal than a 500,000-view reel on a channel that always does
500,000.

Watch the floor. `MIN_VIEWS_FLOOR` defaults to 20,000 in `lib/outlier_scoring.py`, which
is calibrated for six-figure accounts — for a small account every reel scores 0 and the
whole exercise silently returns nothing. Pass `scoring.min_views_floor` from
`config/user_config.json` and set it to roughly 3-4x your own median.

### 2. Throw out anything older than about 45 days

This is the step that changes results most, and it did not exist before.

A real example: `techh_hq` had reels at 5.8M, 4.4M and 3.9M views — all posted 196-236
days earlier. Everything that channel posted in the following month sat at 17k-85k, with
the same template. Copying those three would have meant copying an era that had already
closed. Filter by age *before* ranking, or the dead giants dominate every list.

### 3. Rank by spread and recency, not by the biggest multiple

Two traps:

- **Low medians inflate multiples.** A 94x on an 8,047-median channel and a 2.8x on a
  21,487-median channel are closer than they look. Sanity-check against absolute views.
- **One account tagging heavily looks like a trend.** In one 42-reel pull, a 26-tag
  gaming-rig cluster accounted for 56 hits — all from a single account. Counting reels
  would have made it the top signal. Counting *distinct accounts* correctly demoted it,
  and promoted `#website`, used by four separate competitors.

For a format, prefer one that **repeats**. A three-site list format that ran three times
in two weeks (156,713 / 154,968 / 49,611 views) is worth more than a single spike,
because you can tell it wasn't luck.

### 4. Reject sources whose topic your own account has already failed on

The highest multiple in a sweep is worth nothing if it points at the wrong crowd. In
that session the top recent outlier by views was a movie/watch-party site. The account
being written for had already posted a movie site (157 views, 3 saves) and a Minecraft
site (136 views, 1 save). Its one success was founder-tagged.

Competitor data tells you what works *on their audience*. Your own postmortems tell you
who yours is. When they disagree, your own data wins.

### 5. Verify the site is genuinely usable before writing a single line

Do this every time, and do it before scripting, not after.

One near-miss: BuiltWith looked like an ideal subject until a live check showed its
homepage now hides the lookup behind a signup — the shoot would have hit a wall
mid-film. Four other sites checked out and their real numbers ("151,259 apps ranked by
2,029,353 users") went straight into the script as facts rather than vague claims.

Check: is it free, does it need an account, does the specific feature you're about to
film actually exist. If you can't confirm, say so in the script rather than letting them
find out with a camera running.

### 6. Apply the voice fingerprint literally

`config/voice_fingerprint.json` is only useful if it's obeyed exactly. From a real
five-video sample:

- A signature opener appearing in 5 of 5 videos is a hard constraint, not a suggestion.
  Never paraphrase it.
- Punctuation tics are real style. Lines ending in commas rather than periods, and zero
  exclamation points across the sample, are both reproducible instructions.
- Build the fingerprint from on-screen text if there's no transcript — frames read with
  `ffmpeg` are free, where the Apify transcript add-on runs about $0.05/reel. Record
  which source you used, because burned-in captions and spoken audio can differ.

### 7. Take length and cut rate from recent winners, not from instinct

Length and pacing are separate variables and conflating them produces bad advice.

The mistake worth avoiding: concluding "shorter is better" because a 13.9s reel beat a
16.6s one. The 16.6s reel lost because it had **2 cuts, a 5.5s mean shot and heavy
silence** — not because of its length. Recent winners in the same niche ran 23-39
seconds. A 24s video cutting every 2.5s is 9 cuts and still feels fast.

So: hold the cut rate near the winner's mean shot length, and let duration extend only
when there's more payload to fill it. Put the biggest visual moment past the halfway
mark — the winning reel's loudness curve was `builds_up`, the flop's was `winds_down`.

### 8. Pick the framing from measured framings

Wording of the title card moved results more than anything else in that sweep:

| Framing | vs own median |
|---|---|
| "websites that feel illegal to know" | 94.3x |
| "stay away from these websites" | 9.6x |
| "3 websites to ..." | 2.8x |
| "websites you should know" | 2.8x |

Copy the framing *and* check it suits your audience. "Stay away from" suits addictive or
novelty sites; pointed at a founder audience it's a 9.6x framing aimed at the wrong
people, which is still a flop.

### 9. Conversion asks go in the caption, never on screen

Retention is the ranking input, so in-video asks cost you the thing that decides
distribution. The one reel in that sample with an on-screen ask ("Comment 'games' for
the link") was its second-worst.

Put the save prompt in the caption instead. It satisfies
`scoring.save_signal_keywords` — worth 10 points the account's best reel forfeited by
omitting it — and pushes saves, which is what drove the outlier in the first place. One
ask per post; stacking save, comment and link asks splits intent.

### 10. Don't force proven tags onto an off-topic video

Tempting and wrong. If `#startuptips` carries your only hit, it does not follow that it
belongs on a video about free Photoshop alternatives — it just sends a
software-savings video to founders who didn't ask for one. Either match the tags to the
topic, or change the framing so the proven tags fit honestly.

### 11. Attach the evidence split

Two lists, kept separate:

- **Traced to data** — one line per choice naming the measurement and the reel it came
  from.
- **Guesses** — the subject itself, specific search terms, which beat is "the impressive
  one", copy lines. These are usually the majority on an early script, and that's fine
  as long as they're labelled.

Never present a hunch in the same voice as a measurement. State the sample size plainly:
"one win, a five-video voice profile, one week of competitor posts" is a hint, not proof.

### 12. Judge the result on saves and retention, not views

Set the bar before posting. For the account in that session: **saves above 4% of reach**
and **retention above 50%** — the only two metrics its 1,535-view outlier actually beat
the field on (46 saves against a median of 1; 52.4% against 38-43%).

Views follow those two. Watching views alone tells you a post did well without telling
you why, which means the next one is guesswork again.

## Where the numbers come from

| What you need | Source | Cost |
|---|---|---|
| Own views, reach, saves, shares, retention | Instagram Graph API (Composio) | free |
| Competitor reels, captions, view counts | `apify/instagram-reel-scraper` | ~$2.80/1k results |
| Follower counts for tiering | `apify/instagram-followers-count-scraper` | ~$2.80/1k |
| Cuts, shot length, loudness, silence | `lib/ffmpeg_analysis.py` | free |
| On-screen script text | frames via ffmpeg, read directly | free |
| Site claims | live check of the site | free |

Saves, shares, reach and average watch time are **only** available first-party through
the Graph API — the Apify actors can't see them, and they're the metrics that explain
outliers. Pull your own numbers from the API and use Apify only for competitors.

## Related

- `docs/understanding-outlier-scores.md` — the 100-point formula
- `docs/psychological-triggers-guide.md` — the 7-trigger taxonomy
- `skills/ig-script/SKILL.md` — the skill this method is meant to inform
- `skills/ig-postmortem/SKILL.md` — where the second data point comes from;
  `lib/own_pattern_analysis.py` needs two wins before it returns a pattern
