# Markdown story authoring

A story package is an immutable source directory containing `plot.md`,
`world.yaml`, `pacing.yaml`, `storylets.md`, `storylet-routes.yaml`, and
`knowledge.yaml`.

The loader rejects unknown references, malformed Markdown/YAML, invalid timing, ambiguous transitions, and cyclic scene dependencies before a package can reach runtime.

## Detail files

- [Package and story structure](markdown-story-authoring/package-and-story-structure.md): read this when authoring `plot.md`, understanding package files, or configuring storylets and route realizations.
- [World placement and entities](markdown-story-authoring/world-placement-and-entities.md): read this when defining locations, items, NPCs, groups, placements, companions, seats, contents, or world facts.
- [Knowledge and disclosure](markdown-story-authoring/knowledge-and-disclosure.md): read this when defining knowledge claims, evidence, delivery text, reach, guarded vocabulary, cues, or voiceability.
- [Pacing and incidents](markdown-story-authoring/pacing-and-incidents.md): read this when authoring pacing windows, pressure realizations, or optional incident decision windows.
- [Route guarantees and resolutions](markdown-story-authoring/route-guarantees-and-resolutions.md): read this when validating required reveals, bridge guarantees, resolution events, or fallback text.
- [Loading and scene movement](markdown-story-authoring/loading-and-scene-movement.md): read this when checking package loading behavior or protagonist placement and carried items across scene changes.
