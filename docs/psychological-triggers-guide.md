# The 7 psychological triggers

*This taxonomy is absorbed from a teammate's `social-media-marketing-specialist`
skill. Reference data lives in `config/psychological_triggers.json` — shared, not
gitignored, since it's not personal config.*

Every hook that works is pulling on *something*. Naming which of these 7 it is turns
"that hook felt good" into a reusable pattern instead of a vibe.

## The 7 triggers

### Curiosity gap
**Signature**: Sets up a question the viewer must resolve.
**Example**: *"You won't believe what happens when..."*
**Use when**: The payoff is genuinely surprising or counter-expectation. Don't force
this if the answer is predictable — the gap collapses and the hook falls flat.

### Fear / FOMO
**Signature**: Urgency plus loss aversion.
**Example**: *"Stop doing this — it's killing your reach"*
**Use when**: There's a real, specific cost to inaction. Vague fear reads as
manipulative; a named, concrete stake doesn't.

### Identity signal
**Signature**: Belonging to a tribe.
**Example**: *"If you're a [X], you already know..."*
**Use when**: The audience has a real shared identity — a niche, a role, a shared
struggle. Falls flat addressed to a generic audience.

### Pain point
**Signature**: Meets the viewer in their frustration.
**Example**: *"Tired of posting and getting zero views?"*
**Use when**: The frustration is specific and the viewer would nod immediately.
Generic pain points ("life is hard") don't land.

### Transformation promise
**Signature**: Before/after arc.
**Example**: *"How I went from 0 to 100K in 60 days"*
**Use when**: There's a real, specific before/after with numbers or a concrete
comparison. Vague improvement claims read as generic-AI-slop territory — this is
one of the easiest triggers to accidentally fake, so anchor it in something real.

### Social proof
**Signature**: Bandwagon signal.
**Example**: *"1M people already watched this — here's why"*
**Use when**: The proof point is real and verifiable. A fabricated-sounding number
undermines trust instantly, and once a viewer doesn't believe the number, they
usually don't believe anything after it either.

### Controversy / Hot take
**Signature**: Provokes debate.
**Example**: *"Unpopular opinion: [X] is actually wrong"*
**Use when**: You actually hold the position and can defend it in comments. A hot
take with no real conviction behind it reads as bait, not perspective — and
audiences are good at telling the difference.

## How this plugin uses the taxonomy

- **`/ig-outlier-breakdown`** tags every winner with exactly one of these 7 (or
  explicitly "none" if the winner rode pure entertainment/trending-audio rather than
  a psychological lever — this happens more than you'd expect, see the note below).
- **`/ig-voice-profile`** records which triggers *your own* content naturally leans
  on, in `hook_style.preferred_triggers`.
- **`/ig-script`** treats the trigger as a structural axis it can preserve or
  deliberately swap when generating variations.
- **`lib/trends_aggregation.py`** runs a lightweight caption-keyword heuristic
  against this same taxonomy across the *whole* weekly pool (not just breakdown
  winners) to surface which triggers are trending niche-wide — this is a much
  rougher, approximate read than a full breakdown, and is labeled as such wherever
  it shows up in a report.

## An honest caveat, found via real testing

Not every viral winner has a clean psychological trigger. Live-testing this plugin
against real data found that a majority of one week's top-10 outliers were actually
riding **trending audio** rather than a specific verbal hook — the "hook" was a meme
sound, not a curiosity gap or pain point. Forcing a trigger tag onto those would be
dishonest. If a winner's real mechanism is "I found a trending sound and paired it
with a relatable moment," that's what the breakdown should say — `trigger: none`,
`outlier_factor: trend_jacking` or `pure_entertainment` — not a manufactured trigger
label just to fill the field.
