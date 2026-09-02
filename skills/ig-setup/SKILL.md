---
name: ig-setup
description: Runs the ~10-minute onboarding wizard that connects a brand-new teammate's Instagram (via Composio) and Apify account, then configures their niche, competitors, hashtags, voice fingerprint, and banned phrases. Auto-triggered by SETUP.md when config/user_config.json is missing; also runnable manually via /ig-setup to redo setup from scratch.
---

# ig-setup: the onboarding wizard

## Tone — read this before writing a single message

Casual and witty. A sharp friend walking them through it over coffee, not a form or
a corporate assistant. Light, dry humor is welcome. Never funny at the teammate's
expense. Never let a joke slow down clarity — if a line could be misread, cut it.

Match this:
> "Alright, that's the setup. Weekly radar's armed, voice fingerprint's saved, banned
> phrases loaded (bye forever, 'delve'). Try `/ig-radar` when you're ready — takes
> about 30 seconds to spit out a shortlist."

Not this:
> "Setup complete. Configuration has been saved successfully. Please initiate the
> /ig-radar command to begin your first sweep."

## UI pattern

Use the AskUserQuestion tool for anything with a fixed set of choices — tappable
beats typing. Use plain free-text turns only for genuinely open-ended answers (niche
description, handle lists, banned phrases). Never make a teammate type a word that
could've been a tap.

## Before you start

- **Don't test for the config file merely existing — test whether it's been filled in.**
  If `switch-page.sh` is in use, `config/user_config.json` is a symlink into the active
  profile and a freshly scaffolded page already has one, copied from the template. So
  "file exists" means nothing. A page still needs setup when
  `niche.description` is null, or every tier under `competitors` is empty:
  ```
  python3 -c "import json;c=json.load(open('config/user_config.json'));n=c.get('niche',{}).get('description');t=sum(len(v) for k,v in c.get('competitors',{}).items() if isinstance(v,list) and k!='excluded');print('needs_setup' if not n or t==0 else 'already_set_up')"
  ```
  Only when that prints `already_set_up` should you ask whether they really mean to
  start over (it overwrites). If it prints `needs_setup`, just run — this is either a
  first-time teammate or a new page they've just created, and stopping to ask "are you
  sure?" about an empty template is pure friction.
- **Which page am I setting up?** If `profiles/` exists, run `./switch-page.sh` first
  (on Windows: `python3 switch-page.py` — the `.sh` is bash-only; see
  `docs/windows-setup.md`)
  and say the active page's name out loud before doing anything. Setting up a page while
  pointed at a different one silently overwrites the wrong config, and every path in
  this skill resolves through that symlink.
- You'll be writing real files by the end of this skill: `config/user_config.json`,
  `config/voice_fingerprint.json`, `config/banned_phrases.txt`. All three are
  gitignored — that's correct, don't fight it. (`config/psychological_triggers.json`
  is different — it's shared reference data, already tracked in git, and this skill
  never modifies it.)
- Keep a scratch dict in your head (or a temp file if the conversation is long) of
  everything collected so far, since this spans ~10+ turns and you'll assemble it
  into JSON at the end.
- **Both connections come first, deliberately.** Step 2 links Composio (free) then
  Apify (paid), in that order. Composio costs nothing and immediately shows them their
  own numbers, which earns the right to ask for a paid key straight after. And Steps 4–7
  all make real Apify calls, so the token has to be live before any of them can run —
  asking mid-flow means interrupting a conversation that was going well.

---

## Step 1 — Greeting

Warm intro, ~2 sentences on what the plugin does, mention ~10 minutes, ask if ready.
(SETUP.md already sent an opening greeting if this is the very first message of the
session — don't repeat yourself, just continue naturally into connecting their
accounts.)

## Step 2 — Connect the two accounts

Both connections happen here, before anything else. **Composio first, Apify second** —
that order matters and isn't arbitrary.

**Why Composio comes first.** It's free, it takes one browser click, and it immediately
gives you something to show them: their own handle, their own numbers, their own reels.
Nothing has been asked of them yet except permission. By the time you ask for a paid API
key in 2b, they've already seen the thing read their account back to them.

**Why Apify comes second and not later.** Steps 4 through 7 all make real Apify calls,
so the token has to be live before any of them can run. Asking mid-flow means stopping a
conversation that was going well to go and find a billing page.

### 2a — Instagram, via Composio (free)

```
python3 lib/composio_client.py check
```

Exit 0 means ready — note the `word_id` under `instagram[]`, you'll save it in Step 11.
Otherwise the `stage` field says exactly what's missing:

- `stage: "install"` → the `error` field already holds the correct install command
  **for their platform**. Show it verbatim and let them run it — macOS/Linux get
  `curl -fsSL https://composio.dev/install | sh`, Windows gets
  `winget install Composio.Composio` (or `npm install -g composio` with Node).
  **Never tell a Windows teammate to install WSL, Git Bash, or any POSIX shell.**
  The Composio CLI is native on Windows; `curl | sh` failing in PowerShell is that
  one installer being POSIX-only, not a missing shell. See `docs/windows-setup.md`
  step 4.
- `stage: "login"` → `composio login --no-wait` prints a URL. **Show them the URL and
  wait** — they have to open it themselves. Then `composio login --poll` blocks until
  they're done. Never use `composio login --agent` here; it signs in as a robot account
  with none of their data on it.
- `stage: "connect"` → link the account. **Which command depends on whether this is
  their first Instagram or an additional one**, and getting it wrong looks like
  "Instagram won't connect" rather than a missing flag:

  ```
  # first Instagram on this Composio account:
  composio link instagram --no-browser

  # second or later — --alias is REQUIRED and Composio refuses the link without it:
  composio link instagram --alias <handle> --no-browser
  ```

  Check which case you're in with `python3 lib/composio_client.py connections` — if
  `instagram` already has an entry, you need `--alias`. Use the page's handle as the
  alias so the connection is self-documenting a month from now.

  `--no-browser` prints the URL instead of trying to open one. **Show them the URL and
  wait for them to approve it** — you cannot complete an OAuth flow on their behalf.

If more than one Instagram ends up connected, ask which page this setup is for
(AskUserQuestion, one option per `word_id`). Getting this wrong fails quietly, not
loudly — every later call returns the other page's numbers with no error.

Requires a **Business or Creator** account; a personal one returns permission errors on
insights. If that's what you hit, say so plainly and carry on — the plugin still works,
it just loses saves, shares, reach and watch time.

**If they'd rather not connect at all**, that's fine and not a failure. Say once that
Step 3's niche and Step 7's voice profile will be weaker for it, then continue.

**Confirm what you found before moving on.** One line, so the free step visibly paid off:

> "Connected — @thewebplug.ai, 9 followers, 6 reels. Got your real numbers now."

### 2b — Apify token (paid, ~cents per run)

Now, and not before:

> "Next up: paste your Apify API token — that's what scrapes your competitors. Composio
> reads *your* account; Apify reads *theirs*.
> No account yet? Here's a 60-second guide:
> [docs/how-to-get-apify-token.md](../../docs/how-to-get-apify-token.md)"

Naming the split matters. Two API keys with no explanation feels like bureaucracy; "one
reads mine, one reads theirs" is a reason.

Validate immediately — this call is free, not a paid one, despite what you might assume:
```
python3 lib/apify_client.py validate-token --token <pasted_token>
```
If `"ok": false`, show the actual error message plainly and point to
`docs/troubleshooting.md`. Don't guess at the fix yourself; let the teammate paste a
corrected token and retry. Don't move on until this returns `"ok": true`.

Store the token in `.env` as `APIFY_API_TOKEN=...` (create the file if missing — it's
gitignored). Do **not** put the raw token inside `config/user_config.json`; that file
should only ever reference `apify.token_env_var`.

If they don't have Apify set up yet and want to pause here, that's fine — make it easy
to resume: nothing before this point needs to be re-asked next time they run
`/ig-setup`. Their Instagram connection from 2a persists.

## Step 3 — Niche, read off the account

Don't ask them to describe their niche. Their last 12 reels describe it better than a
sentence they write about it, and you already have access.

**Why this isn't just a nicety.** Asking produces a self-description, and a
self-description is what fills `voice_fingerprint.built_from.n_videos_analyzed` with 0
and `low_confidence` with true. That fingerprint then can't do its job.

**Skip to the free-text fallback** ("Describe your niche in one sentence — what kind of
videos do you make?") only if they declined to connect in 2a.

### Read the account

```
python3 lib/composio_client.py user-info --account <word_id>
python3 lib/composio_client.py reels --limit 12 --account <word_id>
```

`user-info` gives you the **exact** handle. Use that string, never what they typed —
Apify calls key off it, and a wrong handle returns an empty result set rather than an
error, so a typo yields confident analysis of nothing.

`reels` returns their last 12 with the real numbers attached: views, reach, saves,
shares, average watch time. Read the captions and the numbers together.

Mind the duration gap documented in `to_apify_shape` in `lib/composio_client.py` — the
Graph API has no duration field, so any score computed here is a floor, up to 10 points
below the true value. Don't present a score as final at this step.

### Analyse, then confirm

Say what you worked out, in their words, and let them correct it:

> "Had a look at your last 12. Reads like short screen-recorded website tours, no face
> on camera, mostly aimed at founders — and the one that took off was the startup-tools
> one: 11x your usual, 46 saves against a normal of 1. Sound right?"

Cover what kind of videos, who they're for, and which post did best and by how much.
Free text, so they can correct any part. Apply corrections directly rather than noting
them and moving on.

Save the agreed version as `niche.description` and `niche.one_line_pitch`.

**Keep two things from this step** — both save real money later:

- **The reel data.** Step 7's voice profile can be built from it for free instead of
  paying Apify's transcript add-on (~$0.05/reel).
- **Their own baseline.** `compute_baseline()` from `lib/outlier_scoring.py` runs on this
  data as-is, so write `data/baselines/<handle>.json` now rather than paying Apify to
  scrape a page they own. `/ig-postmortem` needs it and would otherwise pull it itself.

## Step 4 — Competitors

AskUserQuestion, single-select:
> "Do you already have competitors in mind?"
- Yes, I have handles ready
- Help me find some
- Mix of both

**Yes path** — free text, one handle per line. Accept 5–20; if fewer than 5, gently
push for a few more ("give me at least 5 so the tiers below actually mean something").
If more than 20, ask them to trim to their favorite 20.

**Help path (Level 1 discovery — human confirms every pick, nothing gets added to
your real competitor list without you tapping it)**:
1. Free text: "Give me 3 hashtags you'd use most often for your own content."
2. Run, budget-capped at `apify.budget_caps_usd.competitor_finder_pilot` (default $0.35):
   ```
   python3 lib/apify_client.py run-actor \
     --actor apify/instagram-hashtag-scraper \
     --input '{"hashtags": ["tag1","tag2","tag3"], "resultsType": "reels", "resultsLimit": 50}' \
     --budget-cap 0.35 --expected-results 150
   ```
3. If it returns `"reason": "budget_exceeded"`, tell the teammate plainly and offer to
   lower resultsLimit or raise the cap in their config (don't silently retry with
   different numbers without telling them).
4. Cluster the returned items by `ownerUsername` (field names vary slightly by actor
   version — check what's actually in the JSON if this doesn't match). For each
   creator, compute median views across their items in the pull.
5. Rank creators by that median, descending. Take the top 20.
6. AskUserQuestion, multi-select (this one legitimately needs more than 4 options —
   if AskUserQuestion can't render that many, fall back to a numbered list in chat
   and ask them to reply with numbers):
   > "Which of these feel like your peers? Pick 10–15."
   List each as `@handle — median Xk views/reel`.

**Mix path**: collect their existing handles (free text, as in Yes path), then run
the Help path flow but only far enough to round the total up to ~20.

Store the final list temporarily — tiers get assigned in Step 5.

## Step 5 — Tier stratification

Budget-capped at `apify.budget_caps_usd.tier_stratification` (default $0.10):
```
python3 lib/apify_client.py run-actor \
  --actor apify/instagram-followers-count-scraper \
  --input '{"usernames": ["handle1","handle2", ...]}' \
  --budget-cap 0.10 --expected-results 20
```
Note the field name here is `usernames` (plural) — genuinely different from the reel
scraper's `username` (singular), confirmed by hitting the actual API error once.
Don't "fix" this to match the other actor's convention.

Split by follower count:
- **North Stars**: > `competitors.north_star_threshold_followers` (default 500,000)
- **Peers**: 20,000 – threshold
- **Wild Cards**: < 20,000

Show the split as a simple list grouped by tier. AskUserQuestion:
> "Does this split look right?"
- Looks right
- Let me move a few around

If "move a few around", free-text: ask which handle(s) go to which tier, apply, and
show the corrected split before moving on.

**Younger/smaller niches will often produce zero North Stars** at the 500k bar —
that's expected, not a bug. Offer to lower the threshold for this teammate
specifically (e.g. 200k) and say so plainly, then save the actual threshold used to
`competitors.north_star_threshold_followers` so it's visible later rather than a
silent one-off judgment call.

Save into `competitors.north_stars` / `.peers` / `.wild_cards` with `{handle,
followers, added_at}` per the config schema.

## Step 6 — Radar hashtags

You need a sample of what these competitors' captions actually use. If Step 4 already
ran a hashtag-scraper or reel pull that returned caption/hashtag data, reuse it —
don't spend budget twice. Otherwise, pull a light sample now, budget-capped at
`apify.budget_caps_usd.hashtag_suggestion_pull` (default $0.15):
```
python3 lib/apify_client.py run-actor \
  --actor apify/instagram-reel-scraper \
  --input '{"username": ["handle1", "handle2", ...], "resultsLimit": 5}' \
  --budget-cap 0.15 --expected-results 100
```
Extract hashtags from each item's `hashtags` field (or parse them out of the caption
if the actor doesn't split them out), tally frequency across all competitors, and
surface the top 15–20 candidates. If some look like sponsor/brand-partnership tags
rather than topical ones (e.g. a recurring `#[brand]partner`), flag that when you
list them rather than presenting them as equally generic.

AskUserQuestion, multi-select:
> "Here's what your competitors are tagging with most. Pick about 10 to track."

Save to `hashtags.tracked`. Cache whatever reel data you pulled here in memory — it
can seed Step 10's pilot sweep so that step doesn't need a fresh pull either.

## Step 7 — Voice fingerprint

This is the step that keeps scripts from sounding like generic AI output, so don't
rush it. Hand off to the **ig-voice-profile** skill entirely — invoke it now with
mode=`initial_setup`. That skill handles both the upload path and the new-creator
path, and returns a completed `config/voice_fingerprint.json` (including
`hook_style.preferred_triggers` if built from real footage). Come back here once
it's done.

(Don't duplicate its logic here — if you're editing fingerprint-building behavior,
that file is the source of truth, not this one.)

## Step 8 — Banned phrases

No Apify calls in this step — pure conversation. Free text:
> "What words or phrases do you never want in your scripts? One per line — go wild."

Then:
> "Want me to also pre-load a starter list of AI-slop phrases? Things like 'delve',
> 'unlock the power of', 'in today's fast-paced world' — the stuff that makes a
> script scream ChatGPT."
- Yes, load the starter list
- No, just my list

Merge (teammate's list first, then starter list if accepted, deduped case-insensitively)
into `config/banned_phrases.txt`, following the format in
`config/banned_phrases.template.txt` (one phrase per line, `#`-prefixed comments
allowed, case-insensitive substring match).

## Step 9 — Cadence and delivery

Be upfront that "weekly" is a label, not automation, and that email/Slack aren't
built yet — don't offer toggles that silently do nothing when picked.

> "How often do you want the radar labeled as running? Doesn't actually auto-schedule
> yet — you (or a cron job you set up yourself) still trigger `/ig-radar` — but the
> queue is built to tolerate running late gracefully, so weekly is a fine default even
> without real automation behind it."
- Weekly (default)
- Daily
- On-demand only

> "Heads up: reports land right here in Claude chat for now — no email/Slack
> integration built yet. Easy to bolt on later if you end up wanting it, just flag it."

Set `cadence.radar_frequency` to their pick and `delivery.mode = "claude_chat"`. No
question needed for delivery — there's nothing to actually choose yet.

## Step 10 — Pilot sweep

> "Before we lock this in, let me run a tiny pilot — 5 competitors × 4 reels each,
> about $0.05 — so you can see the kind of shortlist your setup would produce.
> Sound good?"

If you already have fresh reel data cached from Step 6 covering at least 5 of the
seeded competitors, reuse it instead of re-pulling (say so — "I've already got some
of this from earlier, reusing it to save you the spend"). Otherwise, budget-capped at
`apify.budget_caps_usd.onboarding_pilot_sweep` (default $0.15):
```
python3 lib/apify_client.py run-actor \
  --actor apify/instagram-reel-scraper \
  --input '{"username": ["h1","h2","h3","h4","h5"], "resultsLimit": 4}' \
  --budget-cap 0.15 --expected-results 20
```

Score with `lib/outlier_scoring.py`'s 100-point formula (compute a quick per-creator
baseline from whatever reels you have — even a 4-5 reel sample, though note in your
own head that this is a rough baseline, not a precision instrument this early). Show
the top 3–5 by score, **with their psychological trigger tagged** — this is a good
early preview of what `/ig-outlier-breakdown` will surface for real later, so tag it
properly even at pilot scale rather than skipping it as "too early for that."

AskUserQuestion:
> "Do these feel like the kind of videos you want inspiration from?"
- These look great
- Meh, let me tweak the seeds
- Terrible, redo

- **These look great** → proceed to Step 11.
- **Meh, tweak the seeds** → go back to Step 4, keep everything else already
  collected (niche, token, hashtags-so-far, banned phrases) so they're not re-asked.
- **Terrible, redo** → go back to Step 3. Confirm first: "Want me to wipe the niche
  and start clean, or just redo the competitors?" — don't nuke the token/banned
  phrases unless they actually say so.

## Step 11 — Handoff

Assemble everything collected into `config/user_config.json` using
`config/user_config.template.json` as the shape (fill in `created_at`/`updated_at`
with the current timestamp). Write it.

Cheerful summary, then offer to run the first real sweep:

> "Alright, that's the setup. Voice fingerprint's saved, banned phrases loaded (bye
> forever, 'delve'). Here's what you've got:
> - `/ig-radar` — outlier sweep, refills your script queue
> - `/ig-queue` — see what's ready to script vs already used
> - `/ig-script [outlier_id]` — turn a queued outlier into 3 scripts in your voice
> - `/ig-postmortem [url]` — see how one of your own reels stacked up
> - `/ig-reconfigure` — change anything, any time
> - `/ig-voice-refresh` — rebuild your voice fingerprint from newer content later
>
> Want me to kick off your first real `/ig-radar` sweep right now?"

If yes, invoke the **ig-radar** skill directly.
