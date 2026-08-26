# Freytag Forge

> Write anything. Make it matter.

Freytag Forge turns any freeform move into grounded, persistent drama.

## Features

- **Write anything.** Bluff, bargain, investigate, flee—your freeform intent drives the drama.
- **Make it count.** Validated facts carry consequences, clues, and relationships from scene to scene.
- **Feel the pressure.** Markdown scenes, optional storylets, and Freytag pacing build urgency without menus or rails.
- **Keep the mystery.** Scene-local memory brings forward what matters without spilling protected knowledge.
- **Choose the risk.** When a move could break the story, you can commit to it or return to the exact moment before.

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
