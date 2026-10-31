# Prompt inputs

Part of [the world-model grounding guide](../world-model-grounding.md).

## Writing prompt lines that use the world model

These rules cover every string that reaches a model about places or things:
the narrator's THINGS and PLAYER lines, its rules and examples, the match call
and the bench judges. They add to the [narrator-writing guide](../narrator-writing-guide.md): a 12th-grade
reading level for new text, one idea per sentence, and every path that narrates.

### What a model is shown

- **Never IDs, relations or the tree.** A THINGS line is the name, then the
  place, then the condition:
  `- Michelle's memory card. Place: drawer.`
  A thing a person holds says who holds it instead of a place:
  `- Michelle's phone. Held by: Kristin. Condition: not damaged.`
- **The place is the authored `text` while it is still true, or else the
  parent's name.** Never compose English from the tree ("with Kristin in the
  kitchen of the house"). The narrator echoes what it reads, and composed
  phrases would then have to be parsed.
- **A two-pole state is shown with its other pole,** `open (or closed)`, so the
  model can report a change.
- **Give only what the command refers to,** plus the protagonist and her place
  every turn. A container brings its visible contents, open or closed, so the
  turn that opens it can show what is really inside. Hidden things are never
  given.
- **Show a model only the things in play.** The match call lists the things in
  scene scope: the scene's items and people, things at or below the scene's
  area or the protagonist's area, things she carries, and things with no place.
  An answer that names anything else is kept as new.
- **Show the match call where a new name came from.** Each new name is shown
  with the narration sentence that used it. Without it, the model guesses the
  thing that fits the command.
- **Engine steps are told, not asked.** When the engine seats the protagonist
  or hands her a thing before an action, the narrator gets a line such as
  `Just before this: Kristin sat down in the driver's seat.` Don't ask the
  narrator to perform a step the world model can perform. The engine seats the
  player only when the command names the thing that needs seated use. It uses
  only a seat in her own area.
  The engine also picks up a loose thing before a command that puts it somewhere
  when the command names it and it is in the player's own area.

