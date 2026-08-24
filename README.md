# Freytag Forge

> Interactive fiction with freedom, memory, and consequences.

Freytag Forge lets you write what your character tries—not choose from a tiny
verb menu—and turns every attempt into a grounded, persistent story beat.

## The hook

- **Freeform play.** Investigate, bargain, lie, help, run, refuse—or invent the
  move no menu anticipated.
- **Living characters.** NPCs respond from their role, relationships, scene, and
  earned knowledge.
- **Consequences with teeth.** Goals, clues, pressure, timed events, and
  failure-forward choices keep the story moving.
- **A world you can touch.** Inspect items, follow routes, uncover documents,
  and change what becomes possible.
- **No silent guesses.** Ambiguity gets clarified; unsafe proposals fail closed.
- **Persistent story memory.** Restart, reload, and replay without losing the
  facts that made your story yours.
- **One engine, every genre.** Mystery, fantasy, sci-fi, and relationship drama
  share the same spoiler-safe, fact-backed rules.
- **Drama with momentum.** Reusable dramatic situations create twists,
  trade-offs, alternate paths, and failures that open the next door—never a
  command menu.
- **Stories built to play.** Every adventure balances a sturdy dramatic spine
  with surprising, replayable moments that react to the facts you earn.

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
