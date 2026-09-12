# Freytag Forge

> Freeform roleplay with consequences that stick.

Write the move. Change the story.

## Features

- **Play freely.** Describe any in-world action. No menus or parser syntax.
- **Make it matter.** Validated facts make discoveries and choices stick.
- **Earn the secrets.** Unlock reveals through action while future plot stays hidden.
- **Keep the pressure on.** Storylets and pacing turn every delay into stakes.
- **Stay in the story.** Scoped knowledge and atomic turns protect continuity.

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
