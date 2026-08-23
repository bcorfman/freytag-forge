# Phase 0 decision record: V2 capability targets

This decision record is the Phase 0 anchor for the
[V1 feature-porting plan](v1-porting-plan.md). Future work continuing that plan
must preserve the decisions below.

## Decision

Phase 0 records intended V2 capabilities, not historical V1 behavior. The
pinned V1 release, old tests, and retained package files are characterization
evidence only: they help recover useful product intent and identify retired or
unsafe assumptions, but they do not establish that a behavior worked or should
be reproduced.

The canonical ledger is
[`v1-parity-ledger.yaml`](v1-parity-ledger.yaml). It explicitly covers the
  opening, rich room and item presentation, progressive first-seen/revisit
  descriptions, explicit `LOOK` re-expansion, NPC presence and continuity,
  addressed dialogue, conversation-led exploration, knowledge safety, bounded
  repeated-question reactions, freeform agency, and persistence.

## Product consequences

- A new room is allowed to be richly described once. Ordinary movement back
  into it should be concise and should mention only changed or newly relevant
  details. An explicit `LOOK` requests the full description again.
- Items follow the same progressive-presentation rule: a first introduction can
  be substantial; repeat mentions should not replay the same paragraph unless
  the player asks to inspect/look at the item.
- NPCs are persistent participants, not decorative room text. Their identity,
  location, role, permitted knowledge, relationship, interaction history, and
  bounded stance changes are fact-backed. Repeated questions may make an NPC
  impatient or less helpful, but the response remains model-authored and
  policy-validated.
- Historical examples such as Daria are not V2 content or regression fixtures.
  The interaction contract they illustrate must apply to whatever NPCs each
  current story package declares, equally across mystery, fantasy, sci-fi, and
  relationship fixtures.
- Across every outline, conversation and purposeful exploration are the default
  progression modes. Objects and puzzles may support a story when authored, but
  they must not define a universal scavenger-hunt or lock-and-key loop.
- The hosted `storygame.web_demo` adapter is the sole player-facing application
  surface. The authoring CLI remains an offline compiler/review tool, not a
  second gameplay runtime.

## Non-goals for Phase 0

This record does not claim that Phase 1–5 runtime behavior is implemented. It
establishes the acceptance vocabulary so implementation can begin without
silently treating an unreliable V1 path as the specification.
