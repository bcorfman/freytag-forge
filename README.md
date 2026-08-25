# Freytag Forge

> Write anything. Make it matter.

Freytag Forge turns freeform play into grounded, persistent drama.

## Why it plays differently

- **Try the unlisted move.** Investigate, flirt, bluff, bargain, flee—or make
  your own play.
- **Change a real world.** Clues, custody, promises, movement, and
  relationships persist as story truth.
- **Meet the scene in front of you.** Named people, groups, evidence, and
  inspectable subjects are present where the story places them.
- **Hear the drama land.** Distinct characters speak in attributed voices and
  act in the scene; you can redirect, refuse, interrupt, or walk away.
- **Keep the continuity.** Secrets stay earned, and saves, replays, mystery,
  fantasy, sci-fi, and relationship drama all share one fact-backed engine.

**Less prompt luck. More character, consequence, and playable drama.**

## Play online

[Open the live story](https://bcorfman.github.io/freytag-forge/) and write what
your character tries.

## For contributors

Python 3.12+ and [uv](https://docs.astral.sh/uv/) are required for the offline
compiler and test suite. Hosted play needs only a browser.

| Command | Description |
| --- | --- |
| `uv sync` | Install dependencies. |
| `TMPDIR=/tmp uv run pytest -q` | Run the full suite. |
| `uv run ruff check .` | Check the code. |
| `uv run ruff format .` | Format the code. |
