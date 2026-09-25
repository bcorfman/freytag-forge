# Freytag Forge product reference

Freytag Forge is a package-driven interactive-fiction engine for freeform
roleplay. Markdown and typed knowledge compile into an immutable story package;
gameplay code stays story-agnostic. Commands are in [README.md](../README.md).

## Hosting

- FastAPI, React, a Cloudflare Worker and SQLite. The adapter owns transport,
  CORS, deployment identity and persistence.
- The API serves sessions, turns, game-break decisions and segments, plus a
  compatibility `lines` field.

## Turn contract

- The player types in-world commands. Declarative storylets and pacing make
  delay a player choice; prose never picks a branch.
- Facts are the only durable truth. The narrator sees bounded scene-local
  material only: never protected reveals, routes, source IDs, future effects
  or transcript memory. It sees delivery text only on the turn that delivers it.
- Each turn parses the narrator's untrusted JSON and validates the prose
  against a cloned fact store. It rejects unearned knowledge, ungiven facts,
  misattributed speech and plot running ahead. A projected beat's prose
  licenses that beat's vocabulary for the turn, never protected knowledge.
- A turn commits atomically or restores the exact pre-turn snapshot, including
  across save and load. A threatened future dependency opens a game-break
  choice: `proceed` commits the branch, `return_to_scene` rejects it.

## Authored reveal handoff

- Opt-in per candidate: complete `action_evidence` and non-empty
  `delivery_text`; anything incomplete follows the normal path.
- The runtime alone decides whether an action earned a reveal. The exact
  matcher needs every evidence group, rejects negations and never composes two
  matches. Missed phrasings get author-reviewed aliases, never similarity
  scoring or model intent.
- Exactly one match inserts the delivery sentence and validates the composed
  turn. Grounding repair cites a multi-word term's single committed owner, else
  the handed-off candidate; an ambiguous term, a tie or a miss commits nothing.

## Package validation

- Loading rejects malformed source, bad references, invalid effects, ambiguous
  transitions, timing errors, dependency cycles and stale saves.
- It also rejects a scene whose own prose names a multi-word knowledge term the
  scene does not commit, so faithful repetition never fails turn validation.
