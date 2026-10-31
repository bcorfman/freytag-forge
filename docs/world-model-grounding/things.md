# Things

Part of [the world-model grounding guide](../world-model-grounding.md).

- To name a thing with common words in one scene without guarding those words in every other scene, give it a unique name and put the common words in `scoped_aliases`.
- **Declare every physical thing the story text names that a player could act
  on, or that a reply could use as a place.** Look in the entry text, bridge
  text, Details lines, beats, delivery text and cue text. The test is simple:
  could a reply say `"place": "<this noun>"`? If yes, it must resolve.
- **Place every item in the scene where it appears.** Put an `item_placements`
  entry in new form (`{parent: ...}`) in each scene where the item appears. An
  item listed in `item_ids` with no placement has no place in that scene.
- **Things stay where they were left.** When the story moves something
  between scenes (Kristin drives the truck to the park), place it again in the
  new scene. Things the protagonist carries move with her, and nothing else
  does.
- **Pick the kind that fits.** Use `container`, `supporter`, `vehicle`,
  `seat`, `opening` or a story sub-kind. The kind decides the relation (in or
  on), so the reply never has to say it. Only `under` needs a flag. Use
  `opening` for a fixed door, gate, hatch or drain with no declared open or
  closed state and no contents. Narration may not invent one.
- **Mark `fixed: true` on anything that cannot move**, unless its kind already
  defaults to fixed, such as `opening`. The engine refuses a narrated move for
  a fixed thing.
- **Seats.** A seat with `seat_for` needs `enter_text` and `leave_text`. A
  seat without `seat_for` (a park bench) must have neither. A vehicle's visible
  seat with `seat_for` makes the engine seat the character when a command
  boards the vehicle, when exactly one such vehicle is in the protagonist's
  area, or when item facts place the protagonist at that vehicle; an item's
  `notice_text` is added as a step only for each visible item in the vehicle
  that the protagonist does not hold.
- **Contents.** A container's contents are declared on it with `contents:`,
  never as a setting-fact sentence. The sentence goes stale the moment a thing
  leaves.
- **Hidden things get a real place.** Declare the place plus `hidden: true`.
  The only way to reveal one is a story fact's `on_assert`:
  `{move: ..., parent: ...}` plus `{reveal: ...}`. A hidden thing is never
  shown to the narrator, so its declared place cannot leak.
- **Story facts that restate a physical relation declare the effect once.**
  Use `on_assert` with `move`, `reveal`, `accompany` or `set_axis`. The
  binding is one-way: narrated moves never change story facts.
- **A thing needed later may name its unusable pole with `unavailable:`.** For
  example, the transit token can use `destroyed`. When a reply puts it on that
  pole, the game stops and asks the player to go on or go back.

