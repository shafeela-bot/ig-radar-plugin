# Getting your Apify token (60 seconds)

1. Go to [apify.com](https://apify.com) and sign up (free, no credit card needed to start).
2. Once you're in, go to **Settings → Integrations**.
3. Copy the token labeled **Personal API token**.
4. Paste it into `/ig-setup` when asked, or `/ig-reconfigure` → "Update Apify token" later.

That's it. The setup wizard validates it immediately with a free call — no cost to check it works.

## What this actually costs — the honest numbers

The PRD's original cost model assumed numbers before anything had actually been run
against Apify's live pricing. This plugin's build process included real live
testing, and the corrected numbers are meaningfully different in a couple of places
— worth knowing before you commit to the 7-day proof plan below.

### One-time setup cost

| Item | PRD estimate | Real observed range |
|---|---|---|
| Competitor finder (if used) | $0.29 | ~$0.10–0.35 |
| Tier stratification | $0.03 | ~$0.06–0.10 |
| Voice fingerprint (30 reels + transcripts) | $0.23 | **~$1.50–1.60** |
| Pilot sweep | $0.05 | ~$0.05–0.15 |
| **Setup total** | **~$0.60** | **~$1.75–2.20** |

The voice fingerprint line is the big gap. Apify's transcript add-on behaves closer
to a flat **~$0.05/reel** than a cheap volume-scaled rate at the batch sizes this
plugin actually uses (confirmed live: a 5-reel transcript pull cost $0.25, a 10-reel
pull cost $0.46) — so 30 reels with transcripts runs closer to $1.50 than the
originally-estimated $0.23.

### Weekly recurring cost

| Item | PRD estimate | Real observed |
|---|---|---|
| Radar sweep (competitor + hashtag + 15 transcripts) | $1.72 | **~$1.95–2.10** |
| 7 script generations (from queue) | $0.00 | $0.00 (confirmed — pure generation, no Apify calls) |
| 7 postmortems | $0.07 | ~$0.35–1.00 (same transcript-cost effect if you pull transcripts) |
| **Weekly total** | **~$1.79** | **~$2.30–3.10** |

### What this means for the 7-day proof plan

The free plan's $5 credit still covers a real week-1 proof — it's just a tighter
fit than the PRD's original $2.39-for-week-1 estimate suggested. Budget closer to
**$3.50–4.50 for week 1** (setup + one radar sweep + a handful of scripts/postmortems)
against the $5 credit. You'll likely want to decide on Starter ($29/mo) by the end
of week 1 rather than stretching into week 3, unless you're using this lightly.

None of this changes the plugin's behavior — every Apify call still goes through a
hard budget cap (`config/user_config.json` → `apify.budget_caps_usd`) that refuses
to spend past what you've set, regardless of estimate accuracy. Worst case, a call
gets blocked and tells you plainly rather than silently overspending.
