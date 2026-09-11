# Freytag Forge product reference

Freytag Forge is a package-driven interactive-fiction engine for freeform
roleplay with consequences that hold. A story-agnostic runtime validates each
proposed change before committing it as a durable fact.

## Player experience

- Every ordinary in-world input goes to the narration model unchanged; only
  save/load and a typed resolution of an already-issued game-break warning are
  control actions.
- Markdown plus typed knowledge declarations define scenes, entities,
  transitions, optional storylets, executable storylet routes, and Freytag
  pacing, shaping drama and urgency without turning into action menus or parser
  rules. The knowledge declaration supplies the audience- and scene-scoped
  facts that support progressive revelation and narration safety.
- A move that demonstrably removes an indispensable reachable dependency pauses
  for an explicit decision. Proceed commits the validated branch and its
  narration; return restores the exact pre-turn snapshot—facts, knowledge,
  continuity, and transcript position—including across a save/load. No pending
  candidate's prose is ever shown before that decision is made.

## Runtime and deployment contract

The provider receives a bounded `TurnKnowledgeContext`: the safe scene frame,
committed sayable knowledge, and eligible reveal candidates. It never receives
plot prose, routes, source IDs, future effects, or transcript memory. Its strict
JSON is untrusted. The runtime resolves one eligible knowledge ID to its
package-owned route, applies the proposal to a cloned fact store, and runs
`NarrationSafetyValidator` against that clone. Leaks, unsupported claims,
wrong-speaker dialogue, and premature transitions fail closed with no partial
state change. Only validated facts and narration commit.

Pacing is declarative and fact-backed: accepted turns advance bounded narrative
time, while package deadlines may add pressure or perform an authored
transition. The runtime never infers gameplay from prose or selects an action.

Stories use [Markdown authoring](markdown-story-authoring.md) plus typed
`knowledge.yaml` declarations. The loader fails closed on malformed input,
unknown references, invalid predicates/effects, ambiguous transitions, timing
errors, and dependency cycles. Package files and compiled indexes are immutable
at runtime; schema-2 packages use save version 2 and older snapshots are
rejected.

FastAPI, React, a Cloudflare Worker, and SQLite form the hosted stack. The web
adapter owns transport, CORS, deployment identity, and persistence—not gameplay
policy. `POST /api/v1/session` starts a story and returns its authored opening;
`POST /api/v1/turn` returns structured segments, compatibility `lines`, state,
and an optional typed `game_break`; `POST /api/v1/game-break` is the only
resolution endpoint.

## Developer workflow

```bash
uv sync --group dev
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix .
uv run ruff format .
```
