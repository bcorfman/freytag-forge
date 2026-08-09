# External story-data migration inventory

This is the Phase 0 inventory for the [external story-data migration plan](../.plans/external-story-data-migration.md).
The static audit in `storygame.story_data_audit` scans `storygame/engine`,
`storygame/llm`, and `storygame/cli.py`. It reports current matches; it does
not authorize new embedded story data. New matches fail the audit until they
are classified here and assigned an owner phase.

| Surface | Current classification | Owner | Replacement schema | Removal |
| --- | --- | --- | --- | --- |
| `engine/world.py` | generic package-to-facts realization | complete (Phase 2) | package map, item, character, and opening sections | n/a |
| `engine/world_builder.py` | package loader/compatibility expansion | Phase 1 | `data/story_packages.yaml` validated package sections and references | Phase 6 |
| `engine/mystery.py` | temporary compatibility document/reveal helpers | Phase 4 | package-declared document and reveal contracts | Phase 6 |
| `engine/freeform.py` | generic fact-backed intent routing | complete (Phase 4) | readable-item contracts and exit affordance facts | n/a |
| `llm/opening_coherence.py` | authoring data | Phase 5 | fact-backed exposure and staging policy | Phase 6 |
| `llm/story_agents/prompts.py` | generic fact-aware presentation policy | complete (Phase 3) | observer-scoped opening and roleplay constraints | n/a |
| `cli.py` | generic fact-aware presentation policy | complete (Phase 3) | package room copy and canonical presentation facts | n/a |

The genre comparison and story identifiers in this report are intentionally
inventory markers. They must move into validated package data before the
corresponding owner phase is complete. Generic policies remain permitted only
when they validate categories such as custody, exposure, availability, or
knowledge without naming a story entity.
