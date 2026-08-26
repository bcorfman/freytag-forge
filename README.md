# Freytag Forge

> Write anything. Make it matter.

Freytag Forge turns any freeform move into grounded, persistent drama.

## Features

- **Write anything.** Bluff, bargain, investigate, flee—freeform intent drives the drama.
- **Leave a mark.** Durable facts carry clues, custody, relationships, and consequences forward.
- **Stay in the moment.** Markdown scenes, storylets, and Freytag pacing shape tension without menus.
- **Keep secrets safe.** Scene-local memory recalls the right names and history without spilling future knowledge.
- **Trust the turn.** Every model change is validated; snapshots make consequential choices explicit and reversible.

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
