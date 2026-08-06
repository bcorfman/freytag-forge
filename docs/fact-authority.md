# Fact authority

Canonical runtime state lives in `GameState.world_facts`. Location, custody,
goals, flags, scene state, roles, and other asserted world state are changed
through `ValidatedFactCommitter`, which validates invariants before refreshing
compatibility projections.

`GameState.player`, room collections, and `active_goal` are read-after-commit
projections. `world_package` is authoring/session input, not a second runtime
authority. The parser adapter has a narrow compatibility bridge for legacy room
setup; semantic turn execution reads canonical facts only.

Persistence may import values missing from old object-view saves through the
explicit `persistence_projection_migration` source. Canonical facts win when
both representations contain a value. `StoryState.json` and `STORY.md` render
runtime location, inventory, flags, room contents, and active goal from facts;
their existing integrity hash chain remains enforced.

Proposal state deltas pass through the Phase 2 predicate-policy registry before
they reach the committer. Each declarative predicate identifies its family,
legal commit sources, normalization mode, invariants, and derived-update owner.
Unknown or proposal-forbidden predicates are rejected without changing the
fact store. Intent families similarly map to bounded effects; they do not grant
the model permission to invent arbitrary predicates.

## Observer and evidence boundaries

`storygame.engine.perception.ObservationResolver` derives an observer's
existence, location, accessibility, perceptibility, observation, recognition,
and interpretation status from facts. `observer_context_slice` and
`speaker_context_slice` are the only supported projections for model context:
protected case truth is included only when the observer knows its key, while
scene facts are included only when the observer can perceive their entities.

Concealment, exposure, lighting, weather, sensory blocking, portals, traces,
discovery, evidence state, and contamination are declared in the core policy
pack. Evidence placement continues to use the existing custody/room
cardinality rules, and evidence state is single-valued so transformations do
not leave contradictory canonical states.

## Consequences and affordances

`storygame.engine.consequences.apply_consequences` runs validated declarative
rules after a direct semantic effect and before turn triggers. Rule conditions
bind only against canonical facts; effects are normalized through the
predicate-policy registry and committed through `ValidatedFactCommitter`.
Each rule binding fires at most once per pass in stable rule order. Narration-
only turns do not run the pass, so prose cannot create downstream truth.

Universal rules live in `data/rules/core_rules.yaml`; genre extensions live in
`data/rules/genres/`. `build_affordance_context` derives legal exits, locks,
visible items, addressable NPCs, and inventory from facts for model context.
It is advisory context, not a mutation authority.
