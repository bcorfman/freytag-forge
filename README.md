# Freytag Forge

> Write anything. Make it matter.

Freytag Forge turns freeform roleplay into drama that remembers.

## Features

- **Write freely.** Investigate, bluff, bargain, or run—no command menus.
- **Make it stick.** Validated facts preserve consequences, discoveries, and relationships.
- **Earn every reveal.** Audience-aware knowledge keeps mysteries causal and spoiler-free.
- **Hold the tension.** Storylets, pacing, and reversible high-stakes choices keep drama moving.

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
