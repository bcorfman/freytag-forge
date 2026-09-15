# Freytag Forge product reference

Freytag Forge is a package-driven interactive-fiction engine for freeform
roleplay. Markdown and typed knowledge compile into an immutable story package;
gameplay code stays story-agnostic. Commands are in [README.md](../README.md).

## Hosting

- FastAPI, React, a Cloudflare Worker and SQLite. The adapter owns transport,
  CORS, deployment identity and persistence.
- The API serves sessions, turns, game-break decisions, segments and a
  compatibility `lines` field.

## Turn contract

- The player types ordinary in-world commands. Declarative storylets and pacing
  make delay a player choice; prose never picks a branch for the player.
- Facts are the only durable truth. Each turn projects bounded scene-local
  material to the narrator (never protected reveals, delivery text, routes,
  source IDs, future effects or transcript memory), parses its untrusted JSON,
  validates the prose against a cloned fact store, then commits atomically or
  not at all.
- Validation rejects prose that names unearned knowledge, cites an ungiven fact,
  misattributes speech or runs ahead of the plot. A projected beat's own prose
  licenses that beat's vocabulary for the turn, never protected knowledge.
- A rejected turn restores the exact pre-turn snapshot, including across save
  and load. A threatened future dependency opens a game-break choice:
  `proceed` commits the branch, `return_to_scene` rejects it.

## Authored reveal handoff

- Opt-in per candidate: complete `action_evidence` and non-empty
  `delivery_text`; anything incomplete follows the normal path.
- The runtime alone decides each turn whether the action earned a reveal. The
  exact matcher needs every evidence group, rejects negations and never composes
  two matches; missed phrasings get author-reviewed aliases, never similarity
  scoring or model intent.
- Exactly one match inserts the delivery sentence and validates the whole
  composed turn, including grounding repair: a multi-word term cites its single
  committed owner, else the handed-off candidate; an ambiguous term fails. A tie
  or miss commits nothing.

## Package validation

- Loading rejects malformed source, bad references, invalid effects, ambiguous
  transitions, timing errors, dependency cycles and stale saves.
- A scene whose own authored prose names a multi-word knowledge term it does not
  commit is rejected, so faithful repetition can never fail turn validation.
