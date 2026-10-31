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
