# Pacing and incidents

Part of [the Markdown story authoring guide](../markdown-story-authoring.md).

A pacing event may have `realizations`, an ordered list of short, observable
pressure texts. The first entry whose `when` predicates match the current facts
wins. The last entry must have no `when`; it is the default. A realization text
creates pressure that is true and visible now. It must never carry unearned
knowledge or name a hidden location. A bridge may narrate only pressure facts
that its activation requires. Set `verbatim: true` when the authored text must
be emitted directly to the player rather than reproduced by the narrator.

An optional `incidents.yaml` file declares scene-local decision windows.
Each incident has an `id`, `scene_id`, two or more `outcomes`, a missed-window event, and a successor transition.
Each outcome names an `id`, one storylet realization, at least one advantage fact, and optional cost facts.
Observation knowledge IDs may name free knowledge available in that scene.
The loader requires exclusive realizations, known facts, scene-local events and transitions, and asserted outcome facts.
Advantages must be disjoint, and an outcome cannot list the same fact as both an advantage and a cost.
The missed-window event cannot grant an outcome fact or force the successor transition.
Fact delivery costs in the incident scene cannot duplicate outcome costs.
Phase 1 step 2 adds declarations and validation only; the engine does not act on incidents yet.

## Optional ambient reveals

Story-critical reveals use priority 0 or higher. Optional ambient reveals use -1 so they never push a story-critical reveal out of the four offered candidates. A reveal whose action evidence matches the player's command is offered first, so an ambient reveal still surfaces when the player asks for it. Give a reveal exactly the evidence groups its plain command needs.
When several reveals match a command, deliver the one with the most evidence groups; equal matches deliver none.
