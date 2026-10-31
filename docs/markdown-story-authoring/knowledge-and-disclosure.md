# Knowledge and disclosure

Part of [the Markdown story authoring guide](../markdown-story-authoring.md).

An entity without `disclosure` uses the legacy policy. `public` makes its name and
aliases ordinary words. A secret should use a `disclosure_guards` entry with its
terms and an unlock fact or knowledge ID. Choose the policy deliberately for each
new declaration.

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

An optional `reach_entity_ids` list makes a reveal require the protagonist to
be together with each named world item, character, or group. Use it when the
reveal is about something the protagonist must be physically near; omit it
when the reveal has no reach restriction. The loader validates every ID, and
the runtime checks reach after prerequisites and before source activation.

Locations may also declare an optional `description` used when the protagonist
is outside the scene's location; it must be a non-blank string and should
describe only what is visible from that place.

An optional `leak_terms` list names vocabulary that narration must guard before
the knowledge is earned. Every multi-word phrase in the list is blocked;
single-word entries are not enforced. If the field is absent, the old behavior
remains: aliases and multi-word `must_convey` phrases are guarded. An empty list
means the item has no guarded vocabulary.

A knowledge statement may set `voiceable: false` when it records what the player character did, so a present non-player character does not repeat it as speech.
The default is true.

Each `FactDelivery` may also have an optional `cue_text`. A cue is one or two
short sentences about a concrete thing the player can already see or has
already been told in that scene. It points toward the missing fact without
stating that fact. Write new cues at a 12th-grade reading level; existing
8th-grade cues stay as they are. The runtime shows at
most one cue after the scene's nudge turn, and records each cue once per scene
visit. If the cue goes unanswered, the runtime may show one stronger pointer
later in the same visit, from the optional `escalation_text` (the `cue_text`
is reused when there is none). Write it at a 12th-grade reading level. A fact
asserted by a pacing event needs no `cue_text`; its Deadline delivery remains
the path that makes the fact true.

```yaml
  cue_text: The marked gate stands beside the service path. Fresh tire tracks cross the mud.
```
