# Runtime and authoring boundaries

Part of [the contributor guide](../contributor-guide.md).

## Runtime and authoring boundaries

- Build one story-agnostic engine for every Markdown package. Story, character,
  premise, and genre behavior belongs only in validated package data.
- Facts are the sole canonical mutable runtime state. Packages, prose, saves,
  artifacts, traces, and transcripts are immutable inputs or integrity-checked
  projections; never treat them as competing mutation authorities.
- Put opening setup, public presentation, protected knowledge, relationships,
  location, custody, pacing, and scene purpose in validated package declarations.
  Correct authoring sources, never generated projections.
- Edit story source (`data/stories/<story>/source/*.yaml`) only with the story
  CLI (`python -m storygame.story_cli new|set|rename|fmt`). Committed source
  must be exactly what the CLI writes: CI runs `story_cli fmt --check`, and the
  factory's station 5 applies the format in a repair's tree. When the CLI
  cannot make an edit, add the missing command rather than editing by hand.
- After a source change, regenerate the scene-entry snapshots with
  `python -m storygame.runtime.entry_snapshots write`; they record a
  fingerprint of the source. Station 5 does this for factory repairs.
- Do not add story- or genre-specific runtime branches, fixed action tables,
  hand-edit generated artifacts, accept unvalidated provider output, leak
  protected knowledge, or change facts after rendering.
- World-model logic lives in `packages/worldkeeper`, not in `storygame`. A
  rule that reads or changes only world state (parents, containment, kinds,
  reach, visibility, seats, companions, axes) is a `World` method with its
  tests in `packages/worldkeeper/tests/`. `storygame/runtime/world_model.py`
  only adapts the story package and facts to `worldkeeper`; other modules
  call `World` methods and never walk the tree themselves. Code that needs the
  story package, prose, or a model call stays in `storygame`.
- Keep the hosted adapter as a thin boundary when it is rebuilt. Share code
  only below that boundary and preserve fail-closed behavior.
