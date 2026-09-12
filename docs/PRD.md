# Freytag Forge product reference

Freytag Forge is a package-driven interactive-fiction engine for freeform
roleplay. Markdown and typed knowledge compile into an immutable package.

## Player input and narration

- The player writes ordinary in-world actions. There are no menus or parser
  rules.
- The narrator receives only bounded scene material and eligible legacy
  candidates. It does not receive routes, source IDs, future effects, or
  transcript memory.
- Declarative storylets and pacing make delay a player choice. Prose cannot
  choose a branch for the player.

## Runtime contract

- Facts are the only durable truth. Each turn projects scene-local knowledge,
  parses untrusted narrator JSON, validates the prose and a cloned fact store,
  then commits exactly once or not at all.
- Narration safety checks reject prose that names unearned knowledge, cites a fact it was
  not given, puts words in the wrong character's mouth, or runs ahead of the
  plot.
- A rejected turn restores the exact pre-turn snapshot, including across save
  and load.

### Authored reveal handoff

- Handoff is opt-in. It requires complete `action_evidence` and non-empty
  `delivery_text`.
- The runtime decides whether the action earned the reveal. When exactly one
  candidate matches, it inserts the authored delivery sentence and validates
  the result normally.
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
