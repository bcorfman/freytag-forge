# Freytag Forge

> Write anything. Make it matter.

Freytag Forge turns freeform roleplay into drama that remembers.

## Features

- **Write freely.** Investigate, bluff, bargain, or run—the scene follows intent, not menus.
- **Make every move matter.** Validated facts preserve consequences, relationships, and discoveries.
- **Earn the reveal.** Audience-aware knowledge keeps mysteries local, causal, and spoiler-free.
- **Keep the tension.** Storylets, pacing, and reversible high-stakes choices turn momentum into drama.

**Less prompt luck. More consequence. More drama that remembers.**

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
