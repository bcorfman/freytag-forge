# Freytag Forge

> Freeform roleplay where every move changes what can happen next.

Write the move. Earn the reveal. Live with the consequence.

## Features

- **Play in plain text.** Type the action your character takes. No menus or parser syntax.
- **Earn every reveal.** Discoveries land only when your action and the narration support them.
- **Hear the authored line.** When a discovery has its proof and delivery text, the engine decides when you earned it and delivers the intended sentence.
- **Keep the world honest.** The engine blocks unearned knowledge, unsupported facts, wrong-speaker dialogue, and plot that jumps ahead.
- **Make choices matter.** Storylets and declarative pacing turn delay into a real choice.
- **Trust each turn.** A rejected turn changes nothing, even after saving and loading.
- **Load with confidence.** Broken references, invalid effects, ambiguous paths, dependency cycles, and stale saves are rejected before play.

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
