# Freytag Forge

> Interactive fiction with freedom, memory, and consequences.

Freytag Forge lets you write what your character tries—not choose from a tiny
verb menu—and turns every attempt into a grounded, persistent story beat.

## Why it plays differently

- **Say it your way.** Investigate, flirt, bluff, flee, bargain—or try the move
  nobody thought to put on a menu.
- **A world that remembers.** Accepted clues, promises, possessions, and
  relationships become durable story truth—not convenient prose.
- **Characters who know their limits.** NPCs speak in a distinct voice, from the
  current scene, with only the knowledge they have earned.
- **Conversations with dramatic traction.** Encounters can begin, continue,
  redirect, refuse, interrupt, fail forward, or land cleanly—without stealing
  your agency.
- **Scenes with a pulse.** People, evidence, movement, and pressure remain
  grounded in the playable world, so every lead has a real path.
- **Secrets worth earning.** Protected revelations stay protected until your
  choices unlock them.
- **Continuity you can trust.** Save, reload, and replay without the world
  quietly changing behind your back.
- **One engine, every genre.** Mystery, fantasy, sci-fi, and relationship drama
  share the same fact-backed foundation—no one-story tricks.

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
