# Freytag Forge
Freeform roleplay where every move changes what can happen next.

## Features

- **Type anything.** No verb list, no "I don't understand that." A live narrator answers whatever you try.
- **It doesn't forget.** Where every person and object is lives in the engine, not in the model's memory.
- **A plot, not drift.** An authored story with a real arc. Your choices bend it, but it still goes somewhere.
- **Earn every reveal.** Secrets land only when your action earns them, in the author's own words.
- **Canon holds.** No invented facts, wrong speakers, or plot jumping ahead. 
- **Delay costs you.** The clock keeps running, so every detour is a real choice.
- **Break the story on purpose.** Moves that would wreck what comes next warn you first. Push on or take it back.
- **Any story, one engine.** Authors write Markdown; the engine plays it.

## Not your parser's world model

Inform and its kin model the world as nouns *and* verbs. Every action needs a rule, from the standard library or written by the author, and the parser turns down everything else. Your imagination ends where the author's verb list does.

Freytag Forge keeps the nouns and drops the verb list. The world model tracks what exists, where it is, and what state it's in, but it never decides what an action does. The narrator writes the outcome of whatever you try. The world model is the referee:

- **It holds the line.** A bolted-down desk won't be carried off. A hidden key won't be grabbed before anyone finds it.
- **It grows.** Something new the story names becomes a real object, with a place you can return to.
- **It keeps the cast together.** Companions walk with you, groups move as one, and what you carry goes where you go.

Authors declare what's in the world. They never have to guess what players will try.

## For contributors

Python 3.12+ and [uv](https://docs.astral.sh/uv/) run the compiler and tests. Hosted play needs only a browser.

| Command | Description |
| --- | --- |
| `uv sync` | Install dependencies. |
| `TMPDIR=/tmp uv run pytest -q` | Run the full suite. |
| `TMPDIR=/tmp uv run pytest -q --cov` | Run the full suite with the 90% coverage gate (CI runs this). |
| `uv run ruff check --fix . && uv run ruff format .` | Lint and format. |

Product and runtime reference: [docs/PRD.md](docs/PRD.md).
