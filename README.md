# Freytag Forge

> Interactive fiction with freedom, memory, and consequences.

Freytag Forge lets you write what your character tries—not choose from a tiny
verb menu—and turns every attempt into a grounded, persistent story beat.

## Why it plays differently

- **Write the move nobody put on a menu.** Investigate, flirt, bluff, flee,
  bargain—or try something stranger.
- **Make it count.** Clues, promises, possessions, relationships, and movement
  become durable story truth—not convenient prose.
- **Meet a living scene.** Named people, groups, evidence, and inspectable
  subjects are where the story says they are.
- **Talk to characters, not chatbots.** Distinct voices answer from the current
  scene and earned knowledge; conversations can begin, redirect, refuse,
  interrupt, or fail forward without taking your agency.
- **Earn every reveal.** Secrets stay protected until your choices unlock them.
- **Trust the continuity.** Save, reload, and replay without the world quietly
  changing behind your back—across mystery, fantasy, sci-fi, and relationship
  drama.

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
