# Freytag Forge

> Write anything. Make it matter.

Freytag Forge turns any freeform move into grounded, persistent drama.

## Features

- **Write the unexpected.** Bluff, bargain, investigate, flee—the story meets freeform intent.
- **Make consequences stick.** Facts keep people, clues, custody, and relationships grounded across play and saves.
- **Play scenes, not menus.** Markdown-authored scenes, optional storylets, and Freytag pacing turn a plot into responsive drama.
- **Keep every world distinct.** One story-agnostic engine powers any genre without genre rules in the runtime.
- **Trust the boundary.** Model proposals are validated before a fact changes; authored packages are checked before play.

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
