# External story-data migration inventory

This is the Phase 0 inventory for the [external story-data migration plan](../.plans/external-story-data-migration.md).
The static audit in `storygame.story_data_audit` scans `storygame/engine`,
`storygame/llm`, and `storygame/cli.py`. It reports current matches; it does
not authorize new embedded story data. New matches fail the audit until they
are classified here and assigned an owner phase.

| Surface | Current classification | Owner | Replacement schema | Removal |
| --- | --- | --- | --- | --- |
| `engine/world.py` | authoring data and mystery compatibility setup | Phase 2 | package map, item, character, and opening sections | Phase 6 |
| `engine/world_builder.py` | authoring data | Phase 1 | validated package sections and references | Phase 6 |
| `engine/mystery.py` | temporary compatibility document/reveal helpers | Phase 4 | package-declared document and reveal contracts | Phase 6 |
| `engine/freeform.py` | authoring data | Phase 4 | declared item aliases and typed read/reveal contracts | Phase 6 |
| `llm/opening_coherence.py` | authoring data | Phase 5 | fact-backed exposure and staging policy | Phase 6 |
| `llm/story_agents/agents.py` | authoring data | Phase 5 | package-declared placement and custody constraints | Phase 6 |
| `llm/story_agents/prompts.py` | authoring data | Phase 3 | package-provided opening and role constraints | Phase 6 |
| `cli.py` | temporary compatibility presentation seam | Phase 3 | generic fact-aware room presentation | Phase 6 |

The genre comparison and story identifiers in this report are intentionally
inventory markers. They must move into validated package data before the
corresponding owner phase is complete. Generic policies remain permitted only
when they validate categories such as custody, exposure, availability, or
knowledge without naming a story entity.
