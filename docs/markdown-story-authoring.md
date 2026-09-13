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

The optional `item_placements` mapping gives the narrator a positive placement
sentence for authored items whose location matters in a scene. Author it per
scene as needed; it is not required to cover every item.

Do not use `item_placements` for a hidden item's location. Put that location in
the reveal's `delivery_text`, and repeat it in any `Deadline` fallback that can
deliver the same fact. Do not put the location in beat text. For human readers,
audits, and the bench judge, record it in a scene-level `**Hidden canon:**` line
after `**Plot:**` and before the first beat. This line is never sent to the
narrator. Keep it before the first beat; after the last beat it becomes part of
that beat.

The optional `setting_facts` list contains true, visible-state sentences. Each
sentence is rendered verbatim as its own narrator rule after the placement
rules. Use short sentences written at an 8th-grade reading level.

```yaml
item_ids: [memory_card, michelle_phone]
item_placements:
  michelle_phone: on the kitchen floor
```

`world.yaml` declares stable IDs for locations, NPCs, items, facts, protected
knowledge, and explicit fallbacks. `knowledge.yaml` is currently schema `2.0`:
it supplies typed fact purposes, one safe frame per scene, and audience-scoped
claims with aliases, prerequisites, exact effects, and one typed source
(storylet realization, canonical route event, or scene entry). Its fact catalog
must match `world.yaml`; each claim's effects must be authorized by its named
source. Schema-2 saves use persistence version 2 and intentionally reject
older snapshots rather than silently reinterpreting prose-era state.

A selectable knowledge claim may also declare `earn_when`: one short,
player-safe sentence fragment describing the in-world action that earns the
claim. It is shown only with an already eligible candidate. It guides the
narrator's proposal; it never commits a fact or replaces selection, grounding,
must-convey, effect, or narration-safety validation.

`action_evidence` is separate, typed authoring data for an exact action matcher.
Each inner list contains conservative equivalent phrases; every non-empty list
must match the player's action. Pair it with `delivery_text` only when the
candidate is ready for authored handoff. The delivery must state every
`must_convey` group and must not contain package IDs or bookkeeping labels. It
is never sent to the narrator or exposed in the narrator's serialized context.

```yaml
  action_evidence:
  - [recover, retrieve]
  - [damaged recording, interrupted message]
  - [listen, play]
  delivery_text: >-
    Michelle's memory card contains a damaged recording. It warns against
    emergency broadcasts.
```

Keep aliases narrow and author-reviewed. A candidate without `delivery_text`
keeps the legacy narrator-proposal path.

Each `FactDelivery` may also have an optional `cue_text`. A cue is one or two
short sentences about a concrete thing the player can already see or has
already been told in that scene. It points toward the missing fact without
stating that fact. Keep it at an 8th-grade reading level. The runtime shows at
most one cue after the scene's nudge turn, and records each cue once per scene
visit. A fact asserted by a pacing event needs no `cue_text`; its Deadline
delivery remains the path that makes the fact true.

```yaml
  cue_text: The marked gate stands beside the service path. Fresh tire tracks cross the mud.
```

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

Required storylet reveals must not depend on a true fact that is unavailable at scene entry and cannot be made true in that scene.
The loader checks incoming bridge guarantees, scene storylet and pacing effects, `FactDelivery` entries and costs, scene knowledge, and the scene entry fact.
Add a delivery or another scene-local producer when a required reveal needs an earlier fact.

Canonical route events may list `realization_storylets`, a tuple of storylet IDs
that must have been shown before the event can commit. This gating applies to
resolution events; bridge events still commit as soon as their activation holds.
The loader rejects an unknown storylet ID. A storylet named by a bridge or
resolution event is required, so it stays available past its optional expiry.

Every resolution event must also have a short, player-facing `fallback_text`.
Keep `fallback_realization` as an author note; it is not player prose. When a
resolution scene reaches its `handoff_after_turns` Deadline on an accepted turn,
the runtime commits each remaining activation-ready resolution event in
declaration order, shows its `fallback_text`, and marks its realization
storylets as shown. These fallback segments are returned with that turn.

Each fact in a resolution activation must be guaranteed at scene entry or by an
earlier resolution event in the same scene. Entry guarantees come from the
incoming scene's bridge event: use its `all_facts_true` facts or facts asserted
by its operations. The loader rejects a resolution chain that has no such
guarantee, naming the scene, event, and missing fact.

Load a package with `storygame.story_package.load_story_package(path)`. It is a
validated immutable authoring input; it does not interpret player text or add a
story-specific runtime branch.
