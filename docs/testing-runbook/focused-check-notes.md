# Focused check notes

Part of [local checks](local-checks.md#2-focused-checks-by-boundary): how to
regenerate fixtures for some focused tests, and what those tests do not show.

## Narration corpus

Regenerate the verdicts:

```bash
TMPDIR=/tmp uv run python scripts/regenerate_narration_corpus_verdicts.py
```

Add runs:

```bash
uv run python scripts/extract_narration_corpus.py RUN_DIR
```

## Spine expectation

Regenerate the JSON:

```bash
uv run python -m scripts.generate_spine_expected_reveals
```

The generator replays the real runtime with a network-free scripted provider
that assembles prompts and selects eligible exact handoffs. It retains the
earned 2C observation C-R1 and writes sorted per-scene reveal sets. Inspect turn
records separately to verify reveal order, spacing and deadline use; this replay
does not measure live narration or semantic fallback behavior.

## Guard earning and card

Each package leak term is tested independently at scene start and after its
owning knowledge effects. The synthetic held-transit-card test records that
narration guards both bare/article forms before recovery, while reference
resolution can still resolve bare `card` to the transit card.

## Recovery, pressure and drawer

These tests are deterministic and need no live worker. The drawer tests call the
matcher directly. They verify current behavior, not live narration.
