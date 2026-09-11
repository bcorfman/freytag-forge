# Freytag Forge

> Write anything. Make it matter.

Freytag Forge turns freeform roleplay into drama that remembers.

## Features

- **Freeform play.** Investigate, bluff, bargain, or run—no command menus.
- **Consequences that stick.** Validated facts make every choice count.
- **Reveals you earn.** Narration is checked before it reaches you, so the
  story keeps its secrets.
- **Pressure with purpose.** Storylets and pacing turn hesitation into stakes.

**Less prompt luck. More consequence. Drama that remembers.**

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
