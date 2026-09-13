# Freytag Forge product reference

Freytag Forge is a package-driven interactive-fiction engine for freeform
roleplay. Markdown and typed knowledge compile into an immutable package.

## Player input and narration

- The player writes ordinary in-world actions. There are no menus or parser
  rules.
- The narrator receives only bounded scene material and eligible legacy
  candidates: never migrated reveals, delivery text, routes, source IDs, future
  effects, or transcript memory.
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
  parses untrusted narrator JSON, validates the prose against a cloned fact
  store, then makes one atomic commit or none.
- Validation rejects prose that names unearned knowledge, cites an ungiven fact,
  misattributes speech, or runs ahead of the plot.
- Projected authored beat prose licenses that beat's vocabulary for the turn;
  protected knowledge is never licensed this way.
- A rejected turn restores the exact pre-turn snapshot, including across save
  and load. A threatened dependency opens a typed choice: `proceed` commits the
  branch, `return` rejects it.

### Authored reveal handoff

- Opt-in: a candidate needs complete `action_evidence` and non-empty
  `delivery_text`; incomplete data follows the normal path.
- The runtime alone decides, every turn, whether the action earned a migrated
  reveal. The exact matcher requires every evidence group, rejects negations,
  and never composes two matches. Missed phrasings get author-reviewed aliases,
  never similarity scoring or model intent.
- Exactly one match inserts the delivery sentence and validates the turn
  normally; a tie or miss commits nothing.
- Grounding repair covers the whole composed turn. A multi-word term cites its
  single committed owner, falling back to the handed-off candidate only when no
  committed knowledge owns it; an ambiguous term fails validation.

## Package validation

- Loading rejects malformed source, bad references, invalid effects, ambiguous
  transitions, timing errors, dependency cycles, and stale saves.
- `_validate_narration_term_traps` rejects a scene whose own authored prose
  names a multi-word knowledge term it does not commit, so faithful repetition
  can never fail validation.

## Developer workflow

```bash
uv sync --group dev
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix .
uv run ruff format .
```
