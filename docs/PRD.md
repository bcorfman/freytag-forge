# Freytag Forge product reference

Freytag Forge is a package-driven interactive-fiction engine for freeform
roleplay. Its story-agnostic runtime validates every proposed change before
facts become durable.

## Player experience

- Players write ordinary in-world actions. There are no menus or parser rules.
- Authored Markdown and typed knowledge define the world and its progression.
- Scene-scoped projection keeps discoveries progressive and future plot hidden.
- A threatened dependency opens a typed choice; proceed commits the branch,
  while return restores the exact pre-turn snapshot, including after save/load.

## Runtime contract

- Facts are the only durable truth. Each turn projects local knowledge, parses
  untrusted narrator JSON, validates prose and cloned facts, then commits once.
- The narrator sees bounded scene material and eligible legacy candidates. It
  never sees routes, source IDs, future effects, or transcript memory.
- Unsupported facts, leaks, ambiguity, wrong-speaker dialogue, and premature
  transitions fail closed. Pacing is declarative; prose never chooses for the player.

### Authored reveal handoff

- An authored handoff is opt-in: complete `action_evidence` plus non-empty
  `delivery_text`. After projection, exactly one match appends that text as
  ordinary narration and selects the candidate through normal validation.
  Ties and misses do nothing; legacy candidates, IDs, effects, and saves stay intact.

## Authoring and API

- The loader rejects malformed source, bad references, invalid effects,
  ambiguous transitions, timing errors, dependency cycles, and old saves.
  Package files and indexes stay immutable at runtime.
- FastAPI, React, a Cloudflare Worker, and SQLite provide hosting. The adapter
  owns transport, CORS, deployment identity, and persistence; gameplay stays
  shared. The API serves sessions, turns, game-break choices, segments, and
  compatibility `lines`.

## Developer workflow

```bash
uv sync --group dev
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix .
uv run ruff format .
```
