# Story-gap guide

Read this when you review a scene or situation for story gaps: places where the
story does not hold together.

## What counts as a gap

A gap is a place where the prose and the engine's behavior contradict each other
or common sense. Test a candidate against common sense first; use the model only
as evidence. A thing the prose mentions that the model has no record for is not a
gap when an ordinary reader would assume it exists (a house with a back door has a
front door).

A gap must be computed from the story sources and quote them by file and line. It
is never hand-written opinion, and it disappears when the source is fixed.

## Checks every situation must run

1. **Custody.** An action that uses an item requires the actor to hold it.
2. **Co-location.** It also requires the actor to be where any device the prose
   names for it is (the laptop in the truck, or wherever she carries the laptop).
3. **No strand.** Apply 1 and 2 as a hypothetical, then confirm every response to a
   pressure still leaves an authored path to the exit. Pressure may cost the player,
   but it must never dead-end; a stranded state needs a plausible fallback.

## Tool and status

Print a situation trace, then run the three checks (plus the single-reveal strand
check) on the same anchor. Run from the repo root:

```
PYTHONPATH=.:packages/worldkeeper/src .venv/bin/python scripts/situation_trace.py <anchor>
PYTHONPATH=.:packages/worldkeeper/src .venv/bin/python scripts/gap_rules.py <anchor> [--rule NAME]
PYTHONPATH=.:packages/worldkeeper/src .venv/bin/python scripts/impact_report.py <fact|claim|event|transition|storylet>
```

The impact report lists what sets a fact, what reads it and the related claims.
The rules `no_producer` (a condition nothing can satisfy) and `unread_effect` (a
fact set and never read) use the same lookup. `unread_effect` is noisy on facts
that only record that an event happened, so read its results as information.

An anchor is a pacing event, an incident or a transition id. The trace is data
only. The rules print flags with evidence; flags are never errors and never
block a build. Custody and co-location depend on the anchor's starting state, so
the trace says when custody was not tested.

The author set the checks after the first drafts missed them, so the method is
unproven: run it blind on a second situation where the author knows the gaps
before relying on it. The old prototype `.plans/story-data-phase0/render_trace.py`
is kept as evidence only.

### Branch report

Run `scripts/branch_report.py <incident>` for an incident report. It shows what
each branch does, whether it has a way out, how its world state is handed to the
next scene, and the authored text a reader should use to judge continuity. It
reports results only and never blocks a build.
