# Understanding the 100-point outlier score

*The scoring formula on this page is absorbed from a teammate's
`social-media-marketing-specialist` skill. Full credit in `lib/outlier_scoring.py`'s header.*

## The short version

Every reel gets scored 0-100 based on how it performed *relative to that creator's
own normal numbers* — not some universal bar. A tiny account with 500 followers and
a small account with 50,000 followers can both score 90/100, because the question
being asked is "how unusual is this for *them*," not "is this a big number."

- **70-100** → 🔴 viral outlier, worth a full breakdown
- **40-69** → 🟡 above average, worth noting the pattern
- **0-39** → ⚪ nothing special, skip it

## The six components

```
view_score      up to 40 pts   — this reel's views ÷ the creator's median views
comment_score   up to 20 pts   — this reel's comments ÷ the creator's average comments
like_score      up to 15 pts   — this reel's likes ÷ the creator's average likes
save_signal     +10 pts        — caption mentions "save this," "bookmark," etc.
completion_est  +10 pts        — short (≤20s) AND way above median views
                                  (short + very-watched = the algorithm is pushing it)
recency_bonus   +5 pts         — posted in the last 7 days AND already above median
                                  (still actively gaining, not just a past hit)
```

Each component is **capped individually** — a reel that's 500x a creator's median
views still only contributes 40 points from view_score, not an unbounded number.
This matters more than it sounds: a tiny account's baseline is naturally noisy (a
handful of reels averaging a few hundred views each), and without a cap, one
slightly-above-average reel for a tiny account could produce an absurd multiplier
that looks like a massive breakout but is really just statistical noise. Capping
keeps the score honest at every account size.

## A real worked example

From this plugin's own live testing: `@dimarussu_`, an account with roughly 386
followers, posted a reel that scored **90/100** — a viral outlier.

- Their median views (from their last ~20 reels) was low, as expected for a small
  account.
- This specific reel's views were high enough relative to that median to max out
  `view_score` at 40.
- Comments and likes were also proportionally high relative to their averages,
  contributing most of `comment_score` and `like_score`.
- The reel was short (8 seconds) and well above 2x their median views →
  `completion_est` fired, +10.
- Total: 90/100, tagged 🔴.

Compare that to a mega-account with 500,000 followers whose median reel already gets
50,000 views — for *them* to hit the same 90/100, a reel would need to be
proportionally just as unusual *for their own normal*, not for dimarussu_'s. That's
the whole point: the score travels across account sizes, it's not an absolute bar.

## Why "views ÷ median," not "views ÷ average"

A creator's average (mean) views can get dragged way up by one or two past viral
hits. Median is more robust — a few flukes don't move it much. That's also why the
baseline calculation drops the top 10% of a creator's reels before computing the
median (the "recency safeguard") — otherwise last month's viral hit would make this
week's genuinely good reel look unremarkable by comparison.

## The one thing this score doesn't tell you

A high score means "this was unusual for this creator" — it doesn't by itself tell
you *why*. That's what `/ig-outlier-breakdown` is for: naming the actual
psychological trigger, hook structure, and format that likely drove the number.
Score first, understand second.
