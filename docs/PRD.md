# Freytag Forge product reference

Freytag Forge is a package-driven interactive-fiction engine for freeform
roleplay. Markdown and typed knowledge compile into an immutable package.

## Player input and narration

- The player writes ordinary in-world actions. There are no menus or parser
  rules.
- The narrator receives only bounded scene material and eligible legacy
  candidates. It never receives migrated reveal candidates, their delivery
  text, routes, source IDs, future effects, or transcript memory.
- Declarative storylets and pacing make delay a player choice. Prose cannot
  choose a branch for the player.

## Hosting and API

- FastAPI, React, a Cloudflare Worker, and SQLite provide hosting. The adapter
  owns transport, CORS, deployment identity, and persistence; gameplay stays
  shared and story-agnostic.
- The API serves sessions, turns, game-break choices, segments, and a
  compatibility `lines` field.

## Runtime contract

- Facts are the only durable truth. Each turn projects scene-local knowledge,
  parses untrusted narrator JSON, validates the prose and a cloned fact store,
  then makes one atomic commit or none.
- Narration safety checks reject prose that names unearned knowledge, cites a fact it was
  not given, puts words in the wrong character's mouth, or runs ahead of the
  plot.
- Authored beat prose licenses the vocabulary of that beat for the turn when it is
  projected to the narrator. Protected knowledge is never licensed this way.
- Any rejected turn restores the exact pre-turn snapshot, including across
  save and load. A threatened dependency opens a typed choice: `proceed`
  commits the branch, while `return` rejects it.

### Authored reveal handoff

- Handoff is opt-in. It requires complete `action_evidence` and non-empty
  `delivery_text`.
- The exact matcher requires every authored evidence group, rejects negations,
  and composes nothing from two matches; unmatched phrasing is fixed with
  author-reviewed aliases, never similarity scoring or model intent.
- The runtime owns migrated reveals on every turn: it alone decides whether the
  action earned one, and the candidate is never offered to or selectable by the
  narrator.
  When exactly one candidate matches, it inserts the authored delivery
  sentence and validates the result normally.
- A tie or a miss commits nothing. Incomplete handoff data follows the normal
  path.

## Package validation

- Loading rejects malformed source, bad references, invalid effects, ambiguous
  transitions, timing errors, dependency cycles, and stale saves.
- `_validate_narration_term_traps` rejects a package when a scene's own
  authored prose names a multi-word knowledge term whose owning knowledge is
  not committed in that scene. This prevents the narrator from failing on
  prose that faithfully repeats material it received.

## Developer workflow

```bash
uv sync --group dev
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix .
uv run ruff format .
```
