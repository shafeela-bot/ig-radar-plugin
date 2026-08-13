# Troubleshooting

## Apify token issues

**"No Apify token found"** — `.env` is missing or `APIFY_API_TOKEN` isn't set in it.
Run `/ig-reconfigure` → "Update Apify token" to fix, or check that `.env` exists in
the repo root with a line like `APIFY_API_TOKEN=apify_api_...`.

**Token validation fails** — the error message from `validate-token` is the real
Apify API error, not a guess. Common causes: token was copied with extra
whitespace/newline, token was regenerated on Apify's side (old one revoked), or the
Apify account itself has an issue (check apify.com directly). Paste a fresh token
and try again rather than assuming the plugin is broken.

## Budget-exceeded errors

`"reason": "budget_exceeded"` means a call was estimated to cost more than its
configured cap — and **nothing was spent**, the call never ran. This is the safety
mechanism working, not a bug. Fix by either:
- Lowering `--expected-results` / the actor's `resultsLimit` for that call
- Raising the relevant cap in `config/user_config.json` → `apify.budget_caps_usd`

If this happens on a call that used to work fine, Apify's pricing may have changed —
worth checking `docs/how-to-get-apify-token.md`'s real-cost table against what
you're actually seeing.

## Empty or near-empty results

- **A competitor pull came back empty**: the account may be private, deleted, or
  the actor hit a rate limit. `/ig-radar` logs this to `logs/` and skips the
  competitor rather than crashing the whole sweep — check the log for specifics.
- **Hashtag pull came back thin**: the hashtag may be too small/niche, or too
  broad and mostly returning old/irrelevant content. `/ig-reconfigure` → "Change
  hashtags" to swap it out.
- **A single reel scrape (postmortem) fails**: double-check the URL is a public
  reel, not a private account or a deleted post.

## Field-name mismatches (if you're editing lib/ code yourself)

Two real gotchas confirmed by hitting the actual API errors during this plugin's
build, worth knowing if you extend `lib/apify_client.py` calls yourself:
- `apify/instagram-reel-scraper` takes **`username`** (singular) for both handles
  *and* direct post/reel URLs — there's no separate `directUrls` field.
- `apify/instagram-followers-count-scraper` takes **`usernames`** (plural) — a
  genuinely different convention from the reel scraper. Easy to mix up.

## Anti-slop detector failures

`/ig-script` shows you exactly which check failed — banned phrase, generic AI-slop
pattern, em-dash density, sentence-length variance, vocabulary mismatch, or trigger
mismatch. The first three are hard failures (block + regenerate); the last three are
soft warnings (shown, don't block). After 3 hard-failed regeneration attempts on the
same outlier, the skill will offer to try a different one rather than looping
forever — that's expected behavior, not a crash. Some outliers (especially
meme-audio-driven ones with almost no real spoken hook) are genuinely harder to
adapt into a teammate's voice than others.

## The queue looks wrong

- **Queue file missing entries you expect**: `/ig-radar` only *appends* — it never
  deletes. If something's missing, check whether that sweep actually ran
  successfully (check `logs/`) rather than assuming the queue is broken.
- **Everything shows as "used" already**: check `data/queue/current.json` directly —
  if you've been running `/ig-script` a lot, that's expected. Run `/ig-radar` again
  to refill it.

## "Weekly" cadence isn't actually running weekly

Correct — by design, in this build. `cadence.radar_frequency` is a label, not real
automated scheduling. `/ig-radar` only runs when you (or a cron job you set up
yourself outside this plugin) trigger it. The queue architecture is built to
tolerate irregular timing gracefully, so this isn't a bug to fix, just a scope
boundary worth knowing about.

## Something else entirely

Check `logs/` first — every skill that touches Apify logs failures there rather
than swallowing them silently. If a log entry doesn't make sense, that's worth
flagging as a real bug, not just a "seems off."
