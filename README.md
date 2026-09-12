# Freytag Forge

> Freeform roleplay with consequences that stick.

Write the move. Change the story.

## Features

- **Write any move.** Freeform in-world actions, with no menus or parser syntax.
- **Change the story.** Validated discoveries and choices stick.
- **Uncover what you earn.** Future plot stays hidden until your actions reveal it.
- **Feel the pressure.** Storylets and pacing make every delay count.
- **Keep your footing.** Scoped knowledge and atomic turns protect continuity.

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
