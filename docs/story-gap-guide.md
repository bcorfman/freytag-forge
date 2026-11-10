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

The prototype is `.plans/story-data-phase0/render_trace.py`. It builds a situation
trace from the story files and prints the computed gaps. Run it from the repo root:

```
PYTHONPATH=.:packages/worldkeeper/src .venv/bin/python \
  .plans/story-data-phase0/render_trace.py . > .plans/story-data-phase0/situation-trace-reyes-card.md
```

Its probes cover only the Reyes/card situation. The author set the three checks
after the first drafts missed them, so the method is unproven: run it blind on a
second situation where the author knows the gaps before relying on it.
