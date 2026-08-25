# Freytag Forge

> Write anything. Make it matter.

Freytag Forge turns freeform play into grounded, persistent drama.

## Why it plays differently

- **Try the move nobody listed.** Bluff, flirt, investigate, bargain, leave—or
  invent your own play.
- **Make the world answer.** Clues, promises, custody, movement, and
  relationships become lasting story truth.
- **Find a living scene.** The people, groups, evidence, and subjects in front
  of you are where the story says they are.
- **Talk like it matters.** Characters answer in their own voices, act in the
  moment, and make room for a redirect, refusal, interruption, or exit.
- **Carry the drama forward.** Earned secrets and consequences survive saves,
  replays, and every genre on one fact-backed engine.

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
