# Markdown story authoring

A story package is an immutable source directory containing `plot.md`,
`world.yaml`, `pacing.yaml`, `storylets.md`, `storylet-routes.yaml`, and
`knowledge.yaml`. The loader rejects unknown
references, malformed Markdown/YAML, invalid timing, ambiguous transitions,
and cyclic scene dependencies before a package can reach runtime.

`plot.md` retains the human-readable narrative canon. Every playable `## Scene 1A` heading
is immediately followed by YAML frontmatter with its stable scene ID, location,
Freytag phase, objective, participant/item IDs, entry text, and transition IDs.
Its metadata is descriptive; prose is scene-local model guidance, never runtime
truth.

`world.yaml` declares stable IDs for locations, NPCs, items, facts, protected
knowledge, and explicit fallbacks. `knowledge.yaml` supplies typed fact
purposes, one safe frame per scene, and audience-scoped claims with aliases,
prerequisites, exact effects, and a single route source. Its fact catalog must
match `world.yaml`; every route effect must match its named realization.
`pacing.yaml` supplies one ordered window
per scene plus typed fact predicates and a distinct priority for each outgoing
transition. `storylets.md` keeps the labelled companion format: each `SL-*`
entry links to `plot.md`, names its allowed scene, retains all required dramatic
sections, and declares `Pacing window` (`earliest`, `target`, `latest`) plus a
`Pacing impact` of `none`, `brief_delay`, `pressure_increase`, or
`advance_readiness`.

`storylet-routes.yaml` is the executable companion to `storylets.md`. It
declares scene-local activation predicates, exact fact operations for each
realization, protected boundaries, canonical bridge events, and canonical
resolution events. The runtime accepts a durable canonical fact from an LLM
only through an eligible storylet realization with those exact operations.
Pacing events remain authored in `pacing.yaml`; their job is observable pressure,
not unearned knowledge or arbitrary scene transitions.

Load a package with `storygame.story_package.load_story_package(path)`. It is a
validated immutable authoring input; it does not interpret player text or add a
story-specific runtime branch.
