# Finding competitors when you don't have a list ready

If you picked "Help me find some" (or "Mix of both") during `/ig-setup`, here's what
actually happens behind the scenes — useful to know so the process doesn't feel like
a black box.

## The process

1. You give 3 hashtags you'd use for your own content.
2. The wizard pulls the top ~50 recent posts per hashtag via Apify (small, budget-capped —
   see `docs/how-to-get-apify-token.md` for real cost numbers).
3. Results get grouped by creator, ranked by median views across whatever showed up
   in the pull.
4. You get the top 20 as a tappable list — you pick 10-15 that actually feel like
   your peers.

**You confirm every pick.** Nothing gets added to your real competitor list
automatically — the wizard surfaces candidates, you decide.

## Picking good hashtags to seed this with

The 3 hashtags matter more than they might seem — they determine the whole candidate
pool. Good ones are:
- **Specific to your actual content**, not generic (`#vibecoding` beats `#tech`)
- **Active but not oversaturated** — a hashtag with millions of posts will surface
  mostly noise; one with a few thousand active posts surfaces real peers
- **Ones you'd genuinely use**, not aspirational ones for an audience you don't
  actually make content for

## What to do if the results look off

- **Mostly irrelevant creators**: your seed hashtags were probably too broad or too
  generic. Redo the "Help me find some" step with more specific tags.
- **Too few results**: your hashtags might be too niche/small. Try one or two
  broader (but still relevant) tags mixed in.
- **A few good creators, mostly noise**: totally normal — just pick the good ones
  from the top 20 and don't worry about filling all 15 slots if 8-10 genuinely
  fit better.

## Later, via /ig-reconfigure

You're not locked into your initial picks. `/ig-reconfigure` → "Add or remove
competitors" lets you adjust any time — add someone new (their tier gets computed
automatically), drop someone who turned out not to be a good comp, or move someone
between tiers if their follower count changed a lot.
