# Freytag Forge

> Write anything. Make it matter.

Freytag Forge turns freeform roleplay into drama that remembers.

## Features

- **Write anything.** Investigate, bluff, bargain, or run—no command menus.
- **Make it matter.** Validated facts preserve consequences, discoveries, and relationships.
- **Earn every reveal.** Audience-safe, fact-backed context keeps spoilers out and causality in.
- **Keep the pressure on.** Declarative storylets and pacing turn choices into momentum.

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
