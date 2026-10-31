# Placement payloads

Part of [the world-model grounding guide](../world-model-grounding.md).

### Things the shipped narrator does with placements

- A placement's `text` is shown to the narrator word for word. It stops
  showing once the thing or its holder moves, and the parent's name is used
  instead.
- A placement with no `text` gives the narrator no line.
- A Details entry that names a declared item the narrator cannot see in this
  scene is dropped. If you declare an item that a Details line names, place it
  in that scene.
- After a package change, capture the shipped narrator's payloads with the
  network stubbed (`.plans/world-model-s1/prompt_capture.py`) and diff them.
  An unexpected change is a player-visible change.

