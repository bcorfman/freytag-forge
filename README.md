# Freytag Forge

> Freeform roleplay where every move changes what can happen next.

Write the move. Earn the reveal. Live with the consequence.

## Features

- **Just type.** Say what your character does. No menus, no parser syntax.
- **Earn every reveal.** Discoveries land only when your action earns them, in the author's own words.
- **A world that stays honest.** No unearned secrets, invented facts, wrong-speaker lines, or plot jumping ahead.
- **Delay is a choice.** Storylets and live pacing pressure make every detour cost something.
- **Nothing breaks.** A bad turn changes nothing, and broken stories or stale saves are caught before play.

## For contributors

Python 3.12+ and [uv](https://docs.astral.sh/uv/) are required for the offline
compiler and test suite. Hosted play needs only a browser.

| Command | Description |
| --- | --- |
| `uv sync` | Install dependencies. |
| `TMPDIR=/tmp uv run pytest -q` | Run the full suite. |
| `uv run ruff check .` | Check the code. |
| `uv run ruff format .` | Format the code. |
