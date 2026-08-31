# The reel formula

One structure for every video on this page: **copied hook → crazy useful body → ebook
CTA.** Restructured 2026-08-27 around a single end goal.

**End goal: platform signups.** The reel earns a comment, the comment earns the ebook
link, the ebook earns the signup. Views are not the goal and never were — the page's
1,539-view reel produced zero comments and moved nobody onto the platform. Every rule
below is judged on whether it feeds that chain.

Two disciplines carry over from the previous version of this doc, because they are what
make a script debuggable when it flops: **every creative choice names the measurement
behind it**, and **anything unmeasured gets labelled a guess.**

---

## Part 1 — HOOK: copied, never written

The strictest rule in the document. A hook is not composed, it is **lifted verbatim from
a reel that already proved it works.**

If you cannot name the source reel, you do not have a hook. Record all four:

| Required | Why |
|---|---|
| Source URL | So the claim is checkable |
| Views + multiple vs *that account's own* median | 500k on a 500k-median account proves nothing |
| Post date | Must be ≤45 days old |
| Audience the source reel was aimed at | The filter below |

### Preferred shape: belief reversal

State what everyone already believes, then flip it. "Everyone's using X. X is the reason
you're stuck." The hook's job is to make continuing feel involuntary.

### The audience filter — the one that has already burned this page

**A hook copied correctly can still fail, because it brings the wrong crowd.**

The measured framings from the last sweep:

| Framing | vs own median |
|---|---|
| "websites that feel illegal to know" | 94.3x |
| "stay away from these websites" | 9.6x |
| "3 websites to ..." | 2.8x |
| "websites you should know" | 2.8x |

This page copied the 94.3x framing on 2026-08-24 — "Illegal websites you're not supposed
to know part 4". Result: **165 views, 0 saves.** The framing was reproduced faithfully
and still failed, because "illegal websites" recruits curiosity-scrollers, and
curiosity-scrollers will not trade a comment for a founder ebook. The 9.6x "stay away
from these" framing has the same problem pointed at the same crowd.

So a hook must clear **both** bars: proven on a real outlier, *and* aimed at people who
would want the ebook. A hook that only clears the first is how you get comments from
people who want a free anything.

Contrast: the page's only genuine hit (1,539 views, 46 saves, 11.1x median) was tagged
`#startuptips`/`#startup` and carried a founder payload. Competitor data tells you what
works on *their* audience; your own postmortems tell you who yours is. When the two
disagree, your own data wins.

### Where the account signature goes now

`config/voice_fingerprint.json` records "Did you know if you go to this website," in 5 of
5 videos and calls it the hardest signature in the set — never to be paraphrased. That
collides with the copied-hook rule, since both want the opening seconds.

**Resolution: the copied hook takes 0-2s, and the signature line moves to the first body
beat.** The signature survives intact, the hook slot stays proven, and neither rule
bends. Do not run both in the first two seconds — that is three seconds of preamble
before any value, and it is how retention dies.

---

## Part 2 — BODY: one crazy thing, then relentless usefulness

The body does two jobs at once: keep them watching, and leave them able to act. Miss the
second and the video reads as an ad for the ebook, which collapses saves.

### The crazy beat

Exactly one, and it is the single most surprising **verifiable** fact you have. Place it
**past the halfway mark**, not at the start — the page's winning reel had a `builds_up`
loudness curve, its worst had `winds_down`.

Verify it live before filming. A previous session nearly scripted BuiltWith before a
check showed its lookup had moved behind a signup — the shoot would have hit a wall
mid-film. Where a real number exists, use the real number ("151,259 apps ranked by
2,029,353 users"), never a vague intensifier.

### Ultra-useful test

**The viewer must be able to act on the video without the ebook.** The ebook is the
upgrade, not the payload. If the only value sits behind the comment gate, you are asking
strangers to pay before being given anything.

Payload class matters more than production. From this page's own six-reel comparison,
where all six were production-identical:

- **Searchable databases, directories, calculators** → 46 saves, 21 shares
- **One-look toys and novelties** → 0 saves, 0 shares

### Pacing — measured against the niche, 2026-08-31

Every winning reel in this niche cuts **faster than this page does.** Real ffmpeg
measurements from the 2026-08-31 sweep:

| Account | Result | Duration | Cuts | Mean shot |
|---|---|---|---|---|
| setupsai | 1,179,290 views | 13.0s | 9 | **1.30s** |
| ryxai_ | 5.6x own median | 13.8s | 9 | **1.38s** |
| beasttechx | 2.8x own median | 8.7s | 6 | **1.24s** |
| gnutechai | 117.6x own median | 23.6s | 12 | 1.81s |
| promptingbad | 12.0x own median | 32.0s | 13 | 2.29s |
| maxtalkstech_ | 202 comments | 46.8s | 19 | 2.34s |
| **this page, best reel** | 1,539 views | 13.9s | **5** | **2.31s** |

**At ~13 seconds the benchmark is 9 cuts, not 5.** This page's best-ever reel runs at
roughly half the cut rate of every short-form winner in the set. The old "≤2.5s mean
shot" rule was set from this page's own history and is far too lax — 2.31s is a *long
form* cadence here, appropriate at 30-45s, not at 13s.

Use this instead:

- **Under 15s → mean shot ~1.3s** (9-10 cuts in 13s)
- **25-35s → mean shot ~2.3s** (13 cuts in 32s, promptingbad's proven shape)
- **45s+ → mean shot ~2.3s** (19 cuts, maxtalkstech_'s shape)

Loudness is **not** a differentiator and needs no work: all six winners sit at -14.1 to
-14.5 LUFS, and this page already runs -14.48.

Length follows payload, not instinct. The page's 16.6s flop lost on cut rate and heavy
silence, not duration.

---

## Part 3 — CTA: the ebook, once, at the end

The conversion step, and the reason the page exists.

- **One ask.** Comment a keyword, get the ebook link. Nothing else — no save prompt, no
  link-in-bio, no follow ask. Stacked asks split intent.
- **Placement: the last 1.5-2s, after the value has fully landed.** Never before the
  crazy beat.
- **Keyword: short, lowercase, typo-proof.** It has to survive being typed by someone
  half-watching.
- **Caption carries the same single ask**, matching the on-screen keyword exactly.

### Choosing which ebook — verified 2026-08-31

`greta.sh/ebooks` holds **130 free guides**, and the page states they are free and *"do
not sit behind a form."* Two consequences:

1. **The comment is not a gate, it is distribution.** You are genuinely just sending
   someone a link they could have found. That keeps the ask honest — and the comment is
   still a real ranking input, which is the point.
2. **Pick the ebook whose promise continues the reel's hook**, and pick it *before*
   writing the hook, because the hook's outcome slot has to match it. maxtalkstech_'s
   202-comment reel used the keyword "Diet" on a fitness reel — topic-matched, which is
   why it converted.

Prefer a guide where **greta.sh is the substance, not a banner.** Compare:

- `/ebooks/lean-startup-stack` — greta.sh is the centerpiece ("builds your app —
  frontend, backend, logins, domain, Stripe payments, and deploy, all from plain English
  prompts"), "around $38 a month", "built for total beginners". Converts.
- `/ebooks/30-websites-you-need` — better name-match for this page, but greta.sh appears
  only as a closing CTA. Weaker for signups.

The reel's job is to earn the comment. The **ebook's** job is to sell the platform. Do
not make the video do both.

### The trade being made here, stated plainly

The previous strategy said conversion asks go in the caption and **never** on screen,
because retention is the ranking input. Its evidence: the one reel with an on-screen ask
("Comment 'games' for the link") landed at 134 views.

That evidence is weak — n=1, and it was posted `is_shared_to_feed=false`, so it was never
a clean test. It also cuts the other way: this page earns ~0 comments, which is 20 points
of the 100-point score it can never reach, and comments are a real ranking input. A
comment CTA attacks that directly.

So the ask moves on screen deliberately, with two costs accepted:

1. **10 scoring points forfeited.** `scoring.save_signal_keywords` only fires on a save
   prompt in the caption, and the caption now carries the comment ask instead.
2. **Retention risk**, which is why the CTA is capped at the last ~2 seconds.

`config/voice_fingerprint.json` still records the old no-in-video-CTA rule and the
caption save-prompt rule. Both are **superseded by this doc** and need updating.

### Greta placement is now solved by the ebook

The old rule had greta.sh as "the substrate, never the subject," needing a ~2s in-video
reveal at 10.5s. **Drop it.** The ebook is the bridge now, and a better one — it takes
the conversion job out of the video entirely, which protects the retention the reveal
always risked costing.

---

## Judge every post on this, before you post it

Set the bar in advance or you are guessing again next time.

| Metric | Bar | Why |
|---|---|---|
| **Comments** | the new primary | It is the conversion step |
| Retention | ≥50% | The winner hit 52.4% against a 38-43% baseline |
| Saves | ≥4% of reach | The winner hit 4.06%; median was ~1.3% |

Watch for the specific failure mode: **comments up, retention down.** That means the CTA
is too early or too long — shorten it or push it later. If saves collapse below ~2.5%
while comments rise, the body stopped being useful on its own.

Views follow these. Tracking views alone tells you a post did well without telling you
why, which means the next one is guesswork.

## The evidence split

Attach two separate lists to every script:

- **Traced to data** — one line per choice, naming the measurement and the reel it came
  from.
- **Guesses** — usually the subject, the search terms, which beat is "the crazy one", and
  most copy lines. On an early script these are the majority, and that is fine *as long
  as they are labelled.*

Never state a hunch in a measurement's voice. Say the sample size out loud: "one win, a
five-video voice profile, one competitor sweep" is a hint, not proof.

## Where the numbers come from

| What you need | Source | Cost |
|---|---|---|
| Own views, reach, saves, shares, retention | Instagram Graph API (Composio) | free |
| Competitor reels, captions, view counts | `apify/instagram-reel-scraper` | ~$2.80/1k |
| **Verbatim hook text (voiceover)** | same actor, `includeTranscript` | ~$0.05/reel |
| **Verbatim hook text (on-screen, silent reels)** | frames via ffmpeg | free — **ffmpeg not installed** |
| Cuts, shot length, loudness, silence | `lib/ffmpeg_analysis.py` | free — **needs ffmpeg** |
| Site claims | live check of the site | free |

Two gaps worth knowing about, because they block Part 1:

- **No verbatim hook text has ever been stored.** `data/outliers/*.json` keeps
  classifications (`hook_format: "Bold claim"`) and captions, not opening lines. The
  transcript spend from the 2026-08-13 sweep survives as a line item; the transcripts
  themselves were never saved. Fix: write transcript text into the outlier record.
- **ffmpeg is not installed**, so burned-in on-screen text cannot be read. Much of this
  niche is text-on-screen, so transcripts alone will come back empty for some reels.

Saves, shares, reach and average watch time are **only** available first-party via the
Graph API. Pull your own numbers there; use Apify only for competitors.

## Related

- `docs/understanding-outlier-scores.md` — the 100-point formula
- `docs/psychological-triggers-guide.md` — the 7-trigger taxonomy (belief reversal is
  closest to "Controversy / Hot take"; it is not yet its own entry)
- `skills/ig-script/SKILL.md` — the skill this formula feeds
- `skills/ig-postmortem/SKILL.md` — where the next data point comes from
