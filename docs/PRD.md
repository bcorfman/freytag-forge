# Freytag Forge product reference

Freytag Forge is a package-driven interactive-fiction engine for freeform
roleplay. Its story-agnostic runtime validates every proposed change before
facts become durable.

## Player experience

- Players write ordinary in-world actions. There are no command menus or
  parser rules.
- Authored Markdown and typed knowledge define the world, reveals, storylets,
  transitions, and pacing.
- Knowledge is scoped to the audience and current scene, so reveals stay
  progressive and future plot stays hidden.
- Removing an essential reachable dependency opens a typed game-break choice.
  Proceed commits the validated branch; return restores the exact pre-turn
  snapshot, including across save/load.

## Runtime contract

- The narrator receives bounded `TurnKnowledgeContext` scene material,
  committed knowledge, and current candidates. It receives no routes, source
  IDs, future effects, or transcript memory.
- Narrator JSON is untrusted. The runtime resolves at most one eligible fact,
  validates the composed narration and cloned fact state, then commits the
  whole turn atomically. Leaks, unsupported facts, wrong-speaker dialogue,
  ambiguity, and premature transitions fail closed.
- Accepted turns advance declarative, fact-backed pacing. The runtime never
  infers gameplay from vague prose or chooses an action for the player.

### Authored reveal handoff

- An authored handoff is opt-in per candidate: complete `action_evidence` and
  non-empty `delivery_text` are required. After projection, one exact match
  adds that authored text as ordinary narration and selects the same candidate
  through the normal resolver. Ties and misses produce no handoff. The result
  stays out of narrator and API serialization; legacy candidates keep the
  narrator path. Existing fact IDs, effects, and saves remain unchanged.

## Authoring and API

- The loader rejects malformed Markdown, unknown references, invalid predicates
  or effects, ambiguous transitions, timing errors, dependency cycles, and old
  save formats. Package files and compiled indexes are immutable at runtime.
- FastAPI, React, a Cloudflare Worker, and SQLite provide the hosted stack.
  The web adapter owns transport, CORS, deployment identity, and persistence;
  it does not own gameplay policy. The API exposes session, turn, and typed
  game-break endpoints with structured segments and compatibility `lines`.

## Developer workflow

```bash
uv sync --group dev
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix .
uv run ruff format .
```
