# Freytag Forge

> Write anything. Make it matter.

Freytag Forge turns freeform roleplay into drama that remembers.

## Features

- **Freeform actions.** Type what your character does. No command menus.
- **Consequences that stick.** Validated facts make every discovery count.
- **Secrets you earn.** Your actions unlock reveals while future plot stays hidden.
- **Pressure with purpose.** Storylets and pacing turn delay into stakes.

**Write the move. Change the story.**

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
