# Freytag Forge

> Write anything. Make it matter.

Freytag Forge turns freeform roleplay into drama that remembers.

## Features

- **Write anything.** Bluff, bargain, investigate, flee—your intent drives the scene.
- **Leave a mark.** Validated facts preserve consequences, clues, and relationships.
- **Ride the arc.** Markdown scenes, storylets, and Freytag pacing bring pressure without menus.
- **Keep the mystery.** Scene-local context protects revelations and private knowledge.
- **Choose the risk.** A story-breaking move lets you proceed or return to the exact moment before.

**Less prompt luck. More consequence. More drama that remembers.**

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
