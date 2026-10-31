# Characters and names

Part of [the world-model grounding guide](../world-model-grounding.md).

### Characters (NPCs)

- A person needed later may declare a state, such as Brandon's `conscious`/`unconscious`, and name the unusable one with `unavailable:`. If the narrator knocks him out, the game stops and asks the player to go on or go back.

Scene 1B's Brandon is the working example:

```yaml
character_placements:
  brandon: {parent: los_angeles_park, text: across the park from Kristin}
```

- **`participant_ids` is not presence.** Michelle is a participant in scenes
  where she is missing or held captive. Give every NPC who is physically in the
  scene a `character_placements` entry. Its `parent` is the area, or a thing
  inside it, and its optional `text` says where the character is from the
  protagonist's point of view.
- **An NPC who is only heard from is not placed.** That covers recordings,
  a remote connection or a video conference.
- **Who travels with the protagonist is plot, set only by the story.** Use
  a scene's `companions: [...]` from the start of the scene, or an
  `on_assert` `{accompany: ..., with: ...}` partway through. A companion
  moves with the protagonist only while it is in the same place as her, so a
  narrated split lands without any flag.
- **Captive or free is a state, not a place.** Use `set_axis` in an
  `on_assert` when a story fact captures or frees someone.
- **The protagonist defaults to the scene's `location_id`.** Give her a
  `character_placements` entry only when she starts somewhere more specific.

### Names

- **The tracked name is what models see.** Characters are shown by their first alias ("Kristin"). Things are shown by `name`. A new alias is a new
  way to be matched, so add one only for a word the story really uses.
- **Aliases are scanned for safety and leaks.** Never add an alias such as
  "stranger" that would match text in scenes where the character is not
  allowed. If two things share a noun and trip an ambiguity check, rename one
  of them in the fiction instead of loosening the check.
- **Public items may use scoped aliases.** Place the item in the scene where it
  appears so those aliases resolve only while the item is in play.
- **Review knowledge leak terms separately.** An item's optional `leak_terms`
  list names vocabulary that narration must guard before the item is earned.
  Every multi-word phrase in the list is blocked, even when it is not an alias
  or a `must_convey` phrase; single-word entries are not enforced. If the field
  is absent, the item's aliases and multi-word `must_convey` phrases are guarded
  as before. An empty list means it has no guarded phrases. The package loader
  also rejects scene prose that contains a guarded phrase its scene has not
  earned.
- **Learned names persist.** When the match call maps a new name to an
  entity, the bench stores it as a `wk_alias` fact. A wrong mapping therefore
  repeats in every later turn. That is one more reason to declare the right
  entity.

