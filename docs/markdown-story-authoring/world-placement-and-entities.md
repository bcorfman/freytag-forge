# World placement and entities

Part of [the Markdown story authoring guide](../markdown-story-authoring.md).

The optional `item_placements` mapping gives the narrator a positive placement
sentence for authored items whose location matters in a scene. String values and
the old `{placement: ...}` form still load. The new form also changes the world:
`{parent: item_or_location_id, text: ..., under: true, part_of: true}`. `under`
and `part_of` are mutually exclusive; use `part_of` when an item is a component
of its parent. `text` is optional; without it, the bench uses the parent's name.
When an item authored under a place is no longer there, the engine tells the
narrator nothing more is under it. No extra declaration is needed.
A hidden item may have a declared place because it never
reaches the narrator, but it must not carry `text`.

The optional `character_placements` mapping places a participant at scene
start. Each value has a required `parent` ID and optional non-empty `text`.
The parent must be a known area or an enterable container or supporter. The
protagonist may be listed; this replaces where the protagonist starts. The
scene's `location_id` does not change.

The optional `groups` list in `world.yaml` declares crowds with the same `id`,
`name`, and `aliases` fields as NPCs. A group or item may also declare
`scoped_aliases`, plain words that name it only while it is placed and in
scene scope; they are not world aliases. A `character_placements` key may name
a declared group; group keys need not be participants. A character placement
may use that group ID as its `parent`.

```yaml
groups:
  - {id: prisoners, name: Prisoners, aliases: [prisoners]}
character_placements:
  prisoners: {parent: yard}
michelle: {parent: prisoners}
```

The optional `companions` list names NPC participants who start with the
protagonist. A companion cannot be the protagonist. Each scene resets the
companions from its own declaration. A companion without its own character
placement starts where the protagonist starts.

```yaml
participant_ids: [ada, tom]
companions: [tom]
character_placements:
  tom: {parent: shore, text: mending nets on the shore}
```

The loader checks all IDs and placements. A companion follows only while it is
in the same place as the protagonist. A narrated split leaves the companion
behind. A narrated rejoin makes the companion follow again.

Locations may declare a `parent` location ID. `world.yaml` may declare story
sub-kinds with `kinds: [{id: desk, is: [furniture, supporter]}]`. A kind may
set `fixed: true` or `fixed: false` to control whether its entities can move.
It may also set `enterable: true` when it descends from `container` or `supporter`. Items
may set `kind`, `openable`, `hidden`, `contents`, `owner`, and `enterable`.
An item may also set `enter_pole` to an axis pole that is selected when a
character enters it, `seat_for` to the furniture it seats, and `axes` for a
two-pole state axis. For example:

```yaml
kinds:
- {id: seat, is: [supporter], enterable: true}
items:
- id: workstation_chair
  name: workstation chair
  kind: seat
  axes: [{overturned: [], upright: [standing]}]
  enter_pole: upright
  seat_for: michelle_workstation
```

An item with `use_seated: true` needs the engine to seat the protagonist before
it is used. A seat may provide `right_text` for making its `enter_pole` state
ready, `enter_text` for entering it, and `leave_text` for leaving it. An item
may provide `take_text`; the engine says it just before the player uses a
seated-use thing that is not already in the protagonist's hands, unless the thing
rests on the supporter that the chosen seat serves. These
must be short past-tense statements of what happened. The engine shows these
lines to the narrator as `Just before this` when the player command uses a
visible nearby seated-use item or leaves a seat.

`enterable: false` on an item overrides an enterable kind. The two poles and
all aliases in one axis must not overlap, ignoring case. Furniture descendants
are fixed unless the nearest kind or the item explicitly sets `fixed: false`.

Set `contents_complete: true` when the world model lists everything that can be in or on this place.
If a player looks at or searches it while it is empty, the engine tells the narrator that nothing is left, so the narrator does not invent an object.
Leave it off (the default) for any place where the story may add things; it applies to the exact place, not to what is inside it.

World facts may already declare `on_assert` effects. These effects run when the
fact becomes true. Supported effects include `move`, `reveal`, `accompany`, and
`set_axis`. A `move` effect may include optional `text`, which becomes the
narrator's place text after the move. It lasts until the thing or its holder
moves again.

The optional `setting_facts` list contains true, visible-state sentences. Each
sentence is rendered verbatim as its own narrator rule after the placement
rules. Use short sentences. Write new ones at a 12th-grade reading level;
existing 8th-grade sentences stay as they are.

```yaml
item_ids: [memory_card, michelle_phone]
item_placements:
  michelle_phone: on the kitchen floor
```
