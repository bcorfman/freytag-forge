# Freytag Forge

> Write anything. Make it matter.

Freytag Forge turns any freeform move into grounded, persistent drama.

## Features

- **Write freely.** Bluff, bargain, investigate, flee—your intent drives the drama.
- **Make it matter.** Validated facts carry consequences, clues, and relationships across every scene.
- **Feel the arc.** Markdown scenes, optional storylets, and Freytag pacing create pressure without menus or rails.
- **Trust the reveal.** Scene-local memory keeps context sharp and protected knowledge private.
- **Own the risk.** A story-breaking move gives you a real choice: proceed or return to the exact moment before.

**Less prompt luck. More character, consequence, and drama that remembers.**

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
