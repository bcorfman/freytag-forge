# Freytag Forge

> Freeform roleplay where every move changes what can happen next.

Write the move. Earn the reveal. Live with the consequence.

## Features

- **Play freeform.** Write any in-world move. No menus. No parser syntax.
- **Make it stick.** Validated discoveries and choices become lasting facts.
- **Earn the reveal.** Progressive plot stays hidden until your actions uncover it.
- **Feel the pressure.** Storylets and pacing make every delay count.
- **Trust the thread.** Scoped knowledge and atomic turns keep continuity intact.

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
