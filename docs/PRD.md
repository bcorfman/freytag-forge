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

- The narrator receives only a bounded `TurnKnowledgeContext`: the safe scene
  frame, committed sayable knowledge, and eligible reveal candidates. It does
  not receive routes, source IDs, future effects, or transcript memory.
- Narrator JSON is untrusted. The runtime resolves at most one eligible
  knowledge ID to its package-owned route, validates the cloned fact state and
  narration, then commits the whole turn atomically. If the narrator leaves the
  ID empty but its text fully proves exactly one offered candidate, the
  transport may fill that ID before the same checks run. Ambiguous or partial
  text stays unselected. Leaks, unsupported claims, wrong-speaker dialogue,
  and premature transitions fail closed.
- Accepted turns advance declarative, fact-backed pacing. The runtime never
  infers gameplay from vague prose or chooses an action for the player.

### Authored reveal handoff

- A candidate may bypass narrator selection only when its package explicitly
  opts in with complete `action_evidence` and non-empty `delivery_text`.
  The runtime may then match the player's action and deliver that authored
  text, but it still sends the composed turn through the existing validation
  and atomic commit path.
- `delivery_text` is optional for the package as a whole. It is required only
  for candidates that opt into authored handoff. Candidates without this
  opt-in keep the current LLM-proposal path.
- This handoff changes delivery, not a fact ID, package effect, or save payload.
  Existing saves containing those facts remain valid under the normal story,
  schema, and integrity checks.

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
