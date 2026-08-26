# Markdown story authoring

A story package is an immutable source directory containing `plot.md`,
`world.yaml`, `pacing.yaml`, and `storylets.md`. The loader rejects unknown
references, malformed Markdown/YAML, invalid timing, ambiguous transitions,
and cyclic scene dependencies before a package can reach runtime.

`plot.md` retains the human-readable plot. Every playable `## Scene 1A` heading
is immediately followed by YAML frontmatter with its stable scene ID, location,
Freytag phase, objective, participant/item IDs, entry text, and transition IDs.
Prose is never inferred as runtime truth.

`world.yaml` declares stable IDs for locations, NPCs, items, facts, protected
knowledge, and explicit fallbacks. `pacing.yaml` supplies one ordered window
per scene plus typed fact predicates and a distinct priority for each outgoing
transition. `storylets.md` keeps the labelled companion format: each `SL-*`
entry links to `plot.md`, names its allowed scene, retains all required dramatic
sections, and declares `Pacing window` (`earliest`, `target`, `latest`) plus a
`Pacing impact` of `none`, `brief_delay`, `pressure_increase`, or
`advance_readiness`.

Load a package with `storygame.story_package.load_story_package(path)`. It is a
validated immutable authoring input; it does not interpret player text or add a
story-specific runtime branch.
