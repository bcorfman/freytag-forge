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
