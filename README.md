# Freytag Forge

> Freeform roleplay where every move changes what can happen next.

Write the move. Earn the reveal. Live with the consequence.

## Features

- **Write the move.** Freeform actions. No menus. No parser syntax.
- **Earn the truth.** Concrete actions unlock validated discoveries.
- **Feel the pressure.** Storylets and pacing make delay a choice.
- **Live with it.** Scoped knowledge and atomic turns keep consequences coherent.

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
