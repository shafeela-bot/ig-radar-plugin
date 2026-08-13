---
name: ig-queue
description: Shows the current script queue — what's ready to turn into scripts vs already used. State lives in data/queue/current.json, written by ig-radar and updated by ig-script. This skill only reads and displays it; it doesn't generate anything.
---

# ig-queue: what's ready right now

No Apify calls, no generation — this just reads `data/queue/current.json` and
presents it clearly. If that file doesn't exist yet, say so and point to `/ig-radar`
("run your first sweep to fill the queue") rather than erroring.

## Display

Sort `ready` items by `score × replicability` descending (both come straight from
the queue entry — no need to recompute anything). Show:

```
READY (N)
1. OUT-2026-08-12-01 — @handle — score 87, curiosity_gap, replicability 5/5
2. OUT-2026-08-12-04 — @handle — score 74, transformation_promise, replicability 4/5
...

USED (M) — for reference, not actionable
OUT-2026-08-05-02 — @handle — used 2026-08-09
...
```

If `ready` count is below 3, say so plainly: "Only 2 ready right now — worth running
`/ig-radar` again soon." Don't just silently show a short list.

## Offer next action

> "Want me to turn one of these into scripts? Just say `/ig-script OUT-2026-08-12-01`
> (or whichever ID) and I'll take it from there."

## Behind the scenes (for other skills, not shown to the teammate)

- `/ig-radar` appends new entries with `status: "ready"` — never overwrites or
  removes existing entries, `used` items stay forever for history.
- `/ig-script` flips an entry to `status: "used"` with a `used_at` timestamp once it
  successfully generates scripts for that ID — this skill never writes to the file
  itself, only reads it.
- If the queue file is malformed or missing the `queue` key entirely, don't crash —
  treat it as an empty queue and mention the file looked off, in case the teammate
  edited it by hand.
