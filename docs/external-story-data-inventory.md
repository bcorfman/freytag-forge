# External story-data migration inventory

Phase 6 completed the [external story-data migration plan](../.plans/external-story-data-migration.md).
The static audit in `storygame.story_data_audit` scans `storygame/engine`,
`storygame/llm`, and `storygame/cli.py`. It has no compatibility allowlist:
any named story entity, authored genre branch, or story-specific prompt match
fails CI. Story-specific names, prose, aliases, maps, openings, and objectives
belong only in validated package data.

| Runtime surface | Phase 6 boundary |
| --- | --- |
| package loader and builder | reads validated package templates; no named room, item, or objective fallback data |
| world realization | commits package declarations into canonical facts |
| presentation helpers | derive inventory, status, and affordances from facts without genre knowledge |
| opening coherence and prompts | validate generic exposure, custody, role, and knowledge policies |

Generic policies may validate categories such as custody, exposure,
availability, and knowledge, but may not name a story entity or author a genre
presentation branch.
