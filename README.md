# Freytag Forge

> Freeform roleplay where every move changes what can happen next.

Write the move. Earn the reveal. Live with the consequence.

## Features

- **Just type.** Tell your character what to do. No menus, no parser syntax.
- **Earn every reveal.** Secrets land only when your action earns them, in the author's own words.
- **Canon holds.** No invented facts, wrong-speaker lines, or plot jumping ahead.
- **Delay costs you.** Live pacing pressure makes every detour a real choice.
- **Bad turns never stick.** A rejected turn changes nothing, and moves that would break the story warn you first.

## For contributors

Python 3.12+ and [uv](https://docs.astral.sh/uv/) run the compiler and tests. Hosted play needs only a browser.

| Command | Description |
| --- | --- |
| `uv sync` | Install dependencies. |
| `TMPDIR=/tmp uv run pytest -q` | Run the full suite. |
| `uv run ruff check --fix . && uv run ruff format .` | Lint and format. |

Product and runtime reference: [docs/PRD.md](docs/PRD.md).
