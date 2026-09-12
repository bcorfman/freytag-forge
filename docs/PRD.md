# Freytag Forge product reference

Freytag Forge is a package-driven interactive-fiction engine for freeform
roleplay. Its story-agnostic runtime validates proposed changes before facts
become durable.

## Player experience

- Players write ordinary in-world actions. There are no command menus or
  parser rules.
- Authored Markdown and typed knowledge define scenes, characters, reveals,
  transitions, storylets, and pacing.
- Facts and knowledge are scoped to the audience and current scene, so the
  narrator can build progressive reveals without exposing future plot.
- Removing an essential reachable dependency opens a typed game-break choice.
  Proceed commits the validated branch; return restores the exact pre-turn
  snapshot, including across save/load.

## Runtime contract

- The narrator receives a bounded `TurnKnowledgeContext` with the safe scene
  frame, committed sayable knowledge, and eligible candidates. It receives no
  routes, source IDs, future effects, or transcript memory.
- Narrator JSON is untrusted. The runtime resolves at most one eligible
  knowledge ID, validates narration and the cloned fact state, then commits the
  whole turn atomically. Ambiguous or partial claims, leaks, unsupported
  facts, wrong-speaker dialogue, and premature transitions fail closed.
- Accepted turns advance declarative, fact-backed pacing. The runtime never
  infers gameplay from vague prose or chooses an action for the player.

### Authored reveal handoff

- An authored handoff is opt-in per candidate: both complete `action_evidence`
  and non-empty `delivery_text` are required. The loader checks all
  `must_convey` groups and rejects package IDs or bookkeeping labels in the
  delivery. The delivery text stays out of narrator serialization.
- Candidates without this opt-in keep the narrator-proposal path. Later
  matching and delivery still use the existing validation and atomic commit
  path; no fact ID, package effect, or save payload changes, so existing saves
  remain valid.

## Authoring and API

- The loader rejects malformed Markdown, unknown references, invalid predicates
  or effects, ambiguous transitions, timing errors, dependency cycles, and old
  save formats. Package files and compiled indexes are immutable at runtime.
- FastAPI, React, a Cloudflare Worker, and SQLite provide the hosted stack.
  The web adapter owns transport, CORS, deployment identity, and persistence;
  it does not own gameplay policy.
- `POST /api/v1/session` starts a story. `POST /api/v1/turn` returns structured
  segments, compatibility `lines`, state, and an optional typed `game_break`.
  `POST /api/v1/game-break` resolves that warning.

## Developer workflow

```bash
uv sync --group dev
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix .
uv run ruff format .
```
