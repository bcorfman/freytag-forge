# Freytag Forge

> Interactive fiction with freedom, memory, and consequences.

Freytag Forge lets you write what your character tries—not choose from a tiny
verb menu—and turns every attempt into a grounded, persistent story beat.

## The hook

- **Write anything.** Investigate, flirt, bluff, flee, bargain, or try the move
  nobody put on a menu.
- **Meet characters who remember.** NPCs speak from their role, relationships,
  scene, and earned knowledge—not a generic chat window.
- **Make trouble that matters.** Clues, pressure, relationships, timed events,
  and failure-forward turns keep every choice alive.
- **Find the drama, keep the freedom.** Fresh story moments deliver twists,
  trade-offs, and alternate routes without prescribing your next command.
- **Keep your story yours.** Spoilers stay protected; every accepted consequence
  persists across saves, reloads, and replays.
- **Play any kind of tale.** One engine powers mystery, fantasy, sci-fi, and
  relationship drama with fact-backed continuity.

**Less prompt luck. More playable story.**

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
