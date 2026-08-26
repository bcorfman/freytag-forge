# Freytag Forge product reference

Freytag Forge is a package-driven interactive-fiction engine for consequences
that hold. Players roleplay in freeform; a story-agnostic runtime validates
proposed changes before committing them as durable facts.

## Player experience

- Every ordinary in-world input goes to the narration model unchanged; only
  save/load and a typed resolution of an already-issued game-break warning are
  control actions.
- Markdown packages define scenes, entities, transitions, optional storylets,
  and Freytag pacing. They shape drama and urgency without turning into action
  menus or parser rules.
- Context is limited to the current scene, relevant public facts, and safe
  history for an unambiguous reference. Protected and speaker-private knowledge
  never enters a player prompt.
- A move that demonstrably removes an indispensable reachable dependency pauses
  for an explicit decision. Proceed commits the validated branch; return restores
  the exact pre-turn snapshot, including across a save/load.

## Runtime contract

The provider supplies strict JSON: narration, fact effects, optional storylet or
pacing events, and a requested transition. Provider output is untrusted. The
runtime clones state, validates operations, trigger predicates, event eligibility,
transitions, and remaining reachable dependencies (including declared fallbacks),
then atomically commits accepted facts. Invalid or repaired output never mutates
canonical state.

Pacing is declarative and fact-backed: each accepted turn records bounded
narrative time, and package-declared deadlines may add pressure or perform an
authored transition. The runtime never infers gameplay from prose or selects a
player action.

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
