# Freytag Forge product reference

Freytag Forge is a package-driven interactive-fiction engine for freeform
roleplay. Its story-agnostic runtime validates every proposed change before
facts become durable.

## Player experience

- Players write ordinary in-world actions. There are no command menus or
  parser rules.
- Authored Markdown and typed knowledge define the world, reveals, storylets,
  transitions, and pacing.
- Scene-scoped knowledge keeps reveals progressive and future plot hidden.
- Removing an essential reachable dependency opens a typed game-break choice.
  Proceed commits the validated branch; return restores the exact pre-turn
  snapshot, including across save/load.

## Runtime contract

- Facts are the only durable truth. A turn projects scene-local knowledge,
  parses untrusted narrator JSON, validates narration and cloned facts, then
  commits the whole turn atomically.
- The narrator sees bounded scene material, committed knowledge, and eligible
  legacy candidates. It sees no routes, source IDs, future effects, or transcript
  memory. Unsupported facts, leaks, ambiguity, wrong-speaker dialogue, and
  premature transitions fail closed.
- Pacing is declarative and fact-backed. The runtime never infers gameplay from
  vague prose or chooses an action for the player.

### Authored reveal handoff

- An authored handoff is opt-in per candidate: complete `action_evidence` and
  non-empty `delivery_text` are required. After projection, exactly one match
  adds the authored text as ordinary narration and selects the candidate through
  the normal validation path. The narrator gets only surrounding scene
  material. Ties and misses do nothing. Legacy candidates, fact IDs, effects,
  and saves remain unchanged.

## Authoring and API

- The loader rejects malformed source, unknown references, invalid predicates or
  effects, ambiguous transitions, timing errors, dependency cycles, and old
  save formats. Package files and indexes are immutable at runtime.
- FastAPI, React, a Cloudflare Worker, and SQLite provide hosting. The web
  adapter owns transport, CORS, deployment identity, and persistence; gameplay
  stays in the shared runtime. The API exposes session, turn, and typed
  game-break endpoints with structured segments and compatibility `lines`.

## Developer workflow

```bash
uv sync --group dev
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix .
uv run ruff format .
```
