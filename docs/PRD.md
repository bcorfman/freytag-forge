# Freytag Forge product reference

Freytag Forge is a package-driven interactive-fiction engine for freeform
roleplay with consequences that hold. A story-agnostic runtime validates each
proposed change before committing it as a durable fact.

## Player experience

- Every ordinary in-world input goes to the narration model unchanged; only
  save/load and a typed resolution of an already-issued game-break warning are
  control actions.
- Markdown packages define scenes, entities, transitions, optional storylets,
  executable storylet routes,
  and Freytag pacing. They shape drama and urgency without turning into action
  menus or parser rules.
- Packages declare facts, safe scene frames, and audience-scoped knowledge with
  exact reveal sources. Runtime knowledge is a projection of committed facts,
  never author prose or speaker-private facts.
- A move that demonstrably removes an indispensable reachable dependency pauses
  for an explicit decision. Proceed commits the validated branch; return restores
  the exact pre-turn snapshot, including across a save/load.

## Runtime contract

The provider receives a bounded `TurnKnowledgeContext`: safe scene frame,
committed player knowledge, present-speaker sayable knowledge, and eligible
reveal candidates—never plot prose, routes, future effects, or transcript
memory. It returns strict JSON segments, route-authorized fact effects, optional
events, and a requested transition. Its output is untrusted: the runtime
validates it against cloned state and commits accepted facts atomically. Invalid
or repaired output never mutates canonical state.

Pacing is declarative and fact-backed: accepted turns record bounded narrative
time, while package-declared deadlines may add pressure or perform an authored
transition. The runtime never infers gameplay from prose or selects an action.

## Authoring and deployment

The [Markdown story authoring](markdown-story-authoring.md) guide is the source
format contract. Loading fails closed on malformed input, unknown IDs,
predicates, knowledge sources, effects, audiences, timing windows, ambiguous
transitions, and dependency cycles. Package inputs and compiled lookup indexes
remain immutable at runtime. Schema-2 knowledge packages use save version 2;
older snapshots fail closed rather than being reinterpreted under new
revelation rules.

FastAPI, React, Cloudflare Worker transport, and SQLite are the hosted stack.
`POST /api/v1/session` selects a `story_id`; `POST /api/v1/turn` returns
structured `segments`, a compatibility `lines` field, scene/phase state, and an
optional typed `game_break`; `POST /api/v1/game-break` is the only way to
resolve it. The web adapter owns transport, CORS, deployment identity, and
persistence—not gameplay policy.

## Developer workflow

```bash
uv sync --group dev
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix .
uv run ruff format .
```
