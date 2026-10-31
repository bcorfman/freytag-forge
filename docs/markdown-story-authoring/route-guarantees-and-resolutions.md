# Route guarantees and resolutions

Part of [the Markdown story authoring guide](../markdown-story-authoring.md).

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
