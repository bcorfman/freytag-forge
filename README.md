# Freytag Forge

> Write anything. Make it matter.

Freytag Forge turns any freeform move into grounded, persistent drama.

## Features

- **Write the unexpected.** Bluff, bargain, investigate, flee—the story follows freeform intent.
- **Make it stick.** Facts preserve people, clues, custody, and relationships across turns and saves.
- **Play drama, not menus.** Markdown scenes, optional storylets, and Freytag pacing keep the plot responsive.
- **Trust every turn.** Validated model proposals, durable snapshots, and explicit game-break choices protect the world.
- **Bring any world.** One story-agnostic engine powers every genre without runtime genre rules.

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
