# Freytag Forge

> Write anything. Make it matter.

Freytag Forge turns freeform play into grounded, persistent drama.

## Features

- **Write the move nobody listed.** Bluff, flirt, investigate, bargain, leave—
  the story accepts freeform intent.
- **Meet a world that remembers.** People, clues, custody, movement, and
  relationships stay grounded in the scene and persist across saves.
- **Have conversations with consequence.** Distinct characters can initiate,
  respond, redirect, refuse, and act—without forcing a script.
- **Play every genre on one engine.** Mystery, fantasy, sci-fi, and relationship
  drama share fact-backed continuity instead of genre-specific rules.

**Less prompt luck. More character, consequence, and playable drama.**

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
