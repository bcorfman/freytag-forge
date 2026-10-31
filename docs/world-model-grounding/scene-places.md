# Scene places

Part of [the world-model grounding guide](../world-model-grounding.md).

## Why it matters: one worked failure

Scene 1B's entry text names "an ordinary bench near the service path", but the
bench was not an entity. The reply put Kristin at `"place": "bench"`. The match
call had no bench to choose, so it picked the nearest-sounding thing it was
shown: the workstation chair, which was back in the 1A kitchen. From then on,
Kristin was tracked in the kitchen while the story was in the park. No check
failed at the time. The fix had two parts: declare the bench, and show the
match call only things in play.

## Grounding checklist, per scene

Run through this for each scene you touch. Add entities scene by scene as
problems surface, not exhaustively up front.

### Places

- **The scene's `location_id` is where the scene really happens.** If the
  entry text, Setting line and beats put the player somewhere else, such as a
  hideout, an office or a chamber, then the scene's area is wrong.
- **A named sub-place is an area with a `parent`.** The kitchen has the
  house as its parent. An office inside the facility gets the facility as its
  parent. A reply that names the sub-place then resolves, and every thing in
  it is "in" the parent too.
- **Areas that belong together share a parent.** The match call and
  `together()` both walk the tree. Two rooms with no common parent count as
  two different worlds.
- **A spot inside an area is not an area.** "The corner of the kitchen" is the
  kitchen. Detail like "near the door" stays out of the tree.
- **A scene's `situation` never says where a character is.** It is sent every turn,
  so "Kristin is at the loading docks" goes stale the moment she moves,
  and the narrator follows it over her place in THINGS. Describe the place only;
  give the starting position in `entry_text` (sent once), then let tracked facts
  carry it.

When the match call marks a new name, it also gives a kind: place, person,
group or thing. A place becomes an area under the player's current area. A
person or group is created where the player is, when that is allowed. A thing
used as a place becomes a container. A group holds nothing; a person can be a
member of a group. Members go wherever the group goes, and joining or leaving is
an ordinary move. The narrator's THINGS line for a group says which member
answers only on a turn whose command addresses the group (the match call lists
it in `refers`), or that it says nothing when it has none.
New things made while the player is in a group go to the
group's place. Things named as being in a group stay at the group's parent. If
the kind is missing or unknown,
the engine makes the safest thing-shaped fallback and records an issue. A new
thing named by the reply is a container, and new entities are created where the
player ends up after the reply. A refused move is recorded as unplaced with an
issue.

