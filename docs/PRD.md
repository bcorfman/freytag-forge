# Freytag Forge product reference

Freytag Forge is a package-driven interactive-fiction engine for freeform
roleplay with consequences that hold. A story-agnostic runtime validates each
proposed change before committing it as a durable fact.

## Player experience

- Every ordinary in-world input goes to the narration model unchanged; only
  save/load and a typed resolution of an already-issued game-break warning are
  control actions.
- Markdown packages define scenes, entities, transitions, optional storylets,
  and Freytag pacing. They shape drama and urgency without turning into action
  menus or parser rules.
- Prompts contain the current scene, relevant public facts, and safe history for
  an unambiguous reference—never protected or speaker-private knowledge.
- A move that demonstrably removes an indispensable reachable dependency pauses
  for an explicit decision. Proceed commits the validated branch; return restores
  the exact pre-turn snapshot, including across a save/load.

## Runtime contract

The provider supplies strict JSON for narration, fact effects, optional events,
and a requested transition. Its output is untrusted: the runtime clones state,
validates operations, triggers, eligibility, transitions, and reachable
dependencies (including fallbacks), then atomically commits accepted facts.
Invalid or repaired output never mutates canonical state.

Pacing is declarative and fact-backed: accepted turns record bounded narrative
time, while package-declared deadlines may add pressure or perform an authored
transition. The runtime never infers gameplay from prose or selects an action.

## Authoring and deployment

The [Markdown story authoring](markdown-story-authoring.md) guide is the source
format contract. Loading fails closed on malformed input, unknown IDs or
predicates, invalid timing windows, ambiguous transitions, dependency cycles,
and invalid pacing events. Package inputs remain immutable at runtime.

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
