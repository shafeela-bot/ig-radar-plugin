---
name: ig-reconfigure
description: Friendly menu for changing any single piece of an existing setup (competitors, hashtags, banned phrases, voice fingerprint, cadence, Apify token) without redoing the whole wizard. Invoked via /ig-reconfigure.
---

# ig-reconfigure: change one thing without redoing everything

## Tone

Same casual, witty voice as the rest of the plugin. This is a quick in-and-out tool,
not a form — get them to the thing they want to change fast.

## Preconditions

If `config/user_config.json` doesn't exist yet, there's nothing to reconfigure — say
so and point to `/ig-setup` instead.

## The menu

Always show this menu first, every time this skill runs — don't try to guess what
they want from context:

AskUserQuestion, single-select:
> "What do you want to change?"
- Add or remove competitors
- Change hashtags
- Update banned phrases
- Refresh voice fingerprint
- Change cadence
- Update Apify token

(6 options exceeds AskUserQuestion's typical 4-option render — if the tool can't show
all 6 as taps, fall back to a numbered list in chat and let them reply with a number.)

## [1] Add or remove competitors

Show the current tiers (`competitors.north_stars/peers/wild_cards`) as a simple list.
Ask: add, remove, or move between tiers? Free text for handles either way. For new
additions, run the same tier-stratification call as `ig-setup` Step 5
(`apify/instagram-followers-count-scraper`, budget-capped at
`apify.budget_caps_usd.tier_stratification`) to place them correctly rather than
asking the teammate to guess their own tier. Save back to
`config/user_config.json`, bump `updated_at`.

## [2] Change hashtags

Show current `hashtags.tracked`. Free text: add/remove. If they want fresh
suggestions instead of picking blind, offer to re-run the Step 6 hashtag-suggestion
pull from `ig-setup` (same budget cap) against their current competitor list.

## [3] Update banned phrases

Show the current custom entries in `config/banned_phrases.txt` (skip the starter-list
entries in the display — just show what looks teammate-added — or just show the
whole file if separating them cleanly isn't practical). Free text: add or remove
lines. Rewrite the file, preserving the format in
`config/banned_phrases.template.txt`.

## [4] Refresh voice fingerprint

Invoke the **ig-voice-profile** skill directly in `refresh` mode. Don't reimplement
any of its logic here.

## [5] Change cadence

Be honest, same as in `ig-setup` Step 9: `radar_frequency` is a label, not real
automation — `/ig-radar` is always manually triggered regardless of what's picked
here. Update the label if they want, but say plainly that changing it doesn't change
what actually happens.

## [6] Update Apify token

Same flow as `ig-setup` Step 3: prompt for the new token, validate with
`python3 lib/apify_client.py validate-token --token <token>` before saving, show the
real error and point to `docs/troubleshooting.md` if it fails. Update `.env`, not
`config/user_config.json`.

## After any change

Confirm what changed in one cheerful line, then ask if they want to change anything
else (loop back to the menu) or if they're done.
