# Connecting your Instagram

The plugin can read your own account directly through Instagram's Graph API, using
[Composio](https://composio.dev) to handle the connection. This is separate from Apify:
Apify scrapes what's publicly visible on *other people's* pages, Composio reads *your*
page with your permission.

It's optional. Everything still works without it — you just pay Apify for data you
could have had free, and you lose the metrics that matter most.

## Why bother

Four numbers exist only here. No scraper can see them, at any price:

| Metric | Why it matters |
|---|---|
| **Saves** | The heaviest ranking input on Reels. A post can look flat on views and be your best performer on saves |
| **Shares** | Separates "watched it" from "sent it to someone" |
| **Reach** | Views ÷ reach shows rewatches; reach vs your follower count shows how much was cold traffic |
| **Average watch time** | Retention — usually the single best predictor of whether a post gets pushed |

A real example from setting this up: a reel showed 1,535 views against a 138 median.
Notable. The Graph API added **46 saves against a median of 1** and **52% retention
against 38-43%** — which is what actually explained it, and neither number was
available from scraping.

It also means your own baseline and voice profile cost nothing instead of a few dollars
of Apify credit, and your handle gets verified rather than typed.

## Setup

**1. Install the CLI**

```bash
curl -fsSL https://composio.dev/install | sh
```

Lands at `~/.local/bin/composio` and adds itself to your shell profile. Open a new
terminal afterwards, or the `composio` command won't be found.

**2. Log in**

```bash
composio login --no-wait      # prints a URL
# open the URL, approve, then:
composio login --poll         # waits until you're done
```

Don't use `composio login --agent`. It signs in as a robot account with none of your
data on it, which looks like it worked and then returns nothing.

**3. Connect Instagram**

```bash
composio link instagram
```

Needs a **Business or Creator** account. Personal accounts return permission errors on
insights — Instagram doesn't expose them, and there's no workaround.

**4. Check it**

```bash
python3 lib/composio_client.py check
```

Exit 0 means ready. Otherwise `stage` tells you which step above to revisit.

## Two pages? Read this

Each connected account gets a `word_id` like `instagram_levite-actu`:

```bash
python3 lib/composio_client.py connections
```

Put that in the page's config at `accounts.composio_account`. It's passed as
`--account` on every call.

**This is not optional once you have two pages connected.** Without it Composio picks
an account for you, and a call returns the wrong page's numbers **with no error** — you
get a clean-looking postmortem built entirely on the other page's data. If you're using
`./switch-page.sh` (or `switch-page.py` on Windows), each profile under `profiles/` carries its own value, so switching
pages switches the connection too.

## What it can't do

- **Who you follow.** The Graph API has never exposed a following list, and it isn't
  coming. Use Apify for that. Searching Composio returns `INSTAGRAM_GET_USER_INFO` as a
  false positive because its description mentions `follows_count` — that's a count, not
  a list.
- **Video duration.** Not a Graph API field. This matters because
  `score_reel()`'s completion bonus is worth 10 points and can't fire without it, so a
  Composio-only score reads up to 10 points low. Fill the gap by downloading
  `_media_url` and calling `lib/ffmpeg_analysis.get_duration()`.
- **Speech transcripts.** Captions yes, spoken words no. For text-on-screen videos the
  burned-in caption is the script and can be read off frames with ffmpeg for free. For
  talking-head videos you need Apify's transcript add-on (~$0.05/reel).
- **Other people's numbers.** Only accounts you've connected. Competitors are Apify's
  job.

## Commands

```bash
python3 lib/composio_client.py check                          # installed, logged in, connected?
python3 lib/composio_client.py connections                    # word_ids for every linked account
python3 lib/composio_client.py user-info   --account <word_id>
python3 lib/composio_client.py reels       --account <word_id> --limit 12
python3 lib/composio_client.py insights    --media-id <id> --account <word_id>
```

`reels` returns them already shaped for `lib/outlier_scoring.py`, so
`compute_baseline()` and `score_reel()` accept the output directly with no conversion.
First-party-only metrics ride along under underscore-prefixed keys (`_saves`,
`_shares`, `_reach`, `_avg_watch_ms`) which the scoring code ignores and you can use.

## Cost

Nothing. The Graph API is free for accounts you own. Calls do consume rate limit, so
pull the smallest number of reels that answers your question rather than 30 out of
habit.

## Related

- `docs/how-to-get-apify-token.md` — the other data source, for competitors
- `docs/script-framework.md` — which decisions each metric should drive
- `lib/composio_client.py` — the module, with the CLI and field-name gotchas documented
  at the top
