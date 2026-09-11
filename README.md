# Freytag Forge

> Write anything. Make it matter.

Freytag Forge turns freeform roleplay into drama that remembers.

## Features

- **Write anything.** Investigate, bluff, bargain, or run—no command menus, ever.
- **Make it matter.** Validated facts make consequences stick.
- **Earn every reveal.** Every line of narration is checked before you see it—no spoilers, no plot holes, no cheating the story.
- **Keep the pressure on.** Declarative storylets and pacing turn hesitation into stakes.

**Less prompt luck. More consequence. Drama that remembers.**

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
