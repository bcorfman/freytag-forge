# Freytag Forge

> Freeform roleplay where every move changes what can happen next.

Write the move. Earn the reveal. Live with the consequence.

## Features

- **Just type.** Tell your character what to do. No menus, no parser syntax.
- **Earn every reveal.** Secrets land only when your action earns them, in the author's own words.
- **Canon holds.** No invented facts, wrong speakers, or plot jumping ahead. A bad turn is thrown out whole.
- **Delay costs you.** The clock keeps running, so every detour is a real choice.
- **Break the story on purpose.** Moves that would wreck what comes next warn you first. Push on or take it back.
- **Any story, one engine.** Authors write Markdown; the engine plays it.

## For contributors

Python 3.12+ and [uv](https://docs.astral.sh/uv/) run the compiler and tests. Hosted play needs only a browser.

| Command | Description |
| --- | --- |
| `uv sync` | Install dependencies. |
| `TMPDIR=/tmp uv run pytest -q` | Run the full suite. |
| `uv run ruff check --fix . && uv run ruff format .` | Lint and format. |

Product and runtime reference: [docs/PRD.md](docs/PRD.md).
