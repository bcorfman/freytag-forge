# Freytag Forge

> Freeform roleplay where every move changes what can happen next.

Write the move. Earn the reveal. Live with the consequence.

## Features

- **Play your way.** Write any in-world move. No menus. No parser syntax.
- **Earn the truth.** Your actions unlock validated discoveries that stay with you.
- **Make pressure count.** Storylets and pacing turn every delay into a choice.
- **Keep the thread.** Scoped knowledge and atomic turns protect continuity.

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
