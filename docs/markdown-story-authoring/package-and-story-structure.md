# Package and story structure

Part of [the Markdown story authoring guide](../markdown-story-authoring.md).

`plot.md` retains the human-readable narrative canon. Every playable `## Scene 1A` heading
is immediately followed by YAML frontmatter with its stable scene ID, location,
Freytag phase, objective, participant/item IDs, entry text, and transition IDs.
Its metadata is descriptive; prose is scene-local model guidance, never runtime
truth.

`world.yaml` declares stable IDs for locations, NPCs, items, facts, protected
knowledge, and explicit fallbacks. `knowledge.yaml` is currently schema `2.0`:
it supplies typed fact purposes, one safe frame per scene, and audience-scoped
claims with aliases, prerequisites, exact effects, and one typed source
(storylet realization, canonical route event, or scene entry). Its fact catalog
must match `world.yaml`; each claim's effects must be authorized by its named
source. Schema-2 saves use persistence version 2 and intentionally reject
older snapshots rather than silently reinterpreting prose-era state.

`pacing.yaml` supplies one ordered window
per scene plus typed fact predicates and a distinct priority for each outgoing
transition. `storylets.md` keeps the labelled companion format: each `SL-*`
entry links to `plot.md`, names its allowed scene, retains all required dramatic
sections, and declares `Pacing window` (`earliest`, `target`, `latest`).

`storylet-routes.yaml` is the executable companion to `storylets.md`. It
declares scene-local activation predicates, exact fact operations for each
realization, protected boundaries, canonical bridge events, and canonical
resolution events. The runtime accepts a durable canonical fact from an LLM
only through an eligible storylet realization with those exact operations.
Pacing events remain authored in `pacing.yaml`; their job is observable pressure,
not unearned knowledge or arbitrary scene transitions.

Each realization may declare `source_beats`, the `plot.md` beat anchors whose
knowledge it reveals. It is required for every realization of a storylet with
more than one source beat; a single-beat storylet may omit it. If omitted, the
runtime uses the storylet's source beat links.

```yaml
  - id: SL-1C-C-R1
    dramatic_intent: Read the logistics categories.
    source_beats: [scene-1c3--the-nationwide-network]
    operations:
    - {op: assert, fact_id: national_detention_network_known, value: true}
```
