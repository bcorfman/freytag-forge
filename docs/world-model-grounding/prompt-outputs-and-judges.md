# Prompt outputs and judges

Part of [the world-model grounding guide](../world-model-grounding.md).

### What a model is asked to return

- **A place is a name, never a phrase.** Ask for `{"place": "driver's
  seat"}`, not "the passenger seat of the truck". The engine resolves names;
  it never parses phrases.
- **A held thing names its holder in `held_by`, not in `place`.** Ask for
  `{"held_by": "Kristin"}`, not `{"place": "Kristin"}`. When "place" could
  name a person, the narrator also wrote "Kristin" for a drawer she only
  opened. When a reply gives both, `held_by` wins if `place` is missing,
  unresolved, the holder, the holder's area, or where the holder is in the
  same reply; otherwise `place` wins. A leading "in", "on" or "at" is dropped
  before the place is resolved. The other extra field is `"under": true`.
- **Replace an example; do not add one.** The place rule has one example. If
  it teaches the wrong shape, change it rather than adding a second rule
  beside it.
- **Hand the model material before rules.** A declared entity with a name,
  or a THINGS line, prevents more mistakes than a rule telling the model what
  not to do.
- **Show state guidance only for named things.** THINGS shows a state as
  `State: open. It can be: closed.` For a thing named by the player's command,
  it says `State: open. If it changes, give "state": "closed".` On every line,
  this made the reply change states the story never touched.
- **Capture stays in the one narration reply.** Never add a second call to
  collect world changes.
- **Never repair places by scanning prose.** Regex or keyword matching of
  narration is brittle by definition. Resolution belongs to the engine's name
  resolver and the match call.

### Judges

- **Ask about state, not events.** Ask whether a thing ends the turn somewhere
  other than where it started, not whether it "moved" or "left". A round trip
  and a pocket-to-hand shift are events that change nothing.
- **Give the judge the containment it cannot infer.** Pass the things inside
  a place (`place_contents`), each thing's other names (`also_called`), the
  typed command separate from the engine's steps, and the narrator's own
  text separate from the story's own sentences.
- **Fix known judge faults before any comparison relies on the judge.**

