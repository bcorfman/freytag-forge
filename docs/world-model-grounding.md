# Grounding a story in the world model

Read this before you add or place anything in a story package, or before you
write any prompt line that tells a model about places or things. Field syntax
lives in [markdown-story-authoring.md](markdown-story-authoring.md). The design
and its decisions (W1-W13) live in `.plans/world-model.md`.

The world model (`packages/worldkeeper`, adapted by
`storygame/runtime/world_model.py`) is a tree of typed entities held as facts.
Every thing, character and area has one parent. The engine owns that tree. The
narrator proposes changes by naming parents, and the engine resolves the names.
A name that resolves to nothing, or to the wrong entity, breaks the story
silently. So grounding means one thing: **every name a model may use for a
place, thing or person resolves to exactly the right entity, in the scene
where it is used.**

A group's scoped aliases name it only while the group is placed and in scene
scope. Plain words therefore stay free to name different people in other
scenes.

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

### Things

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
  `seat` or a story sub-kind. The kind decides the relation (in or on), so the
  reply never has to say it. Only `under` needs a flag.
- **Mark `fixed: true` on anything that cannot move**, such as doors,
  desks, bolted benches and built-in seats. The engine refuses a narrated move
  for a fixed thing.
- **Seats.** A seat with `seat_for` needs `enter_text` and `leave_text`. A
  seat without `seat_for` (a park bench) must have neither.
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

### Characters (NPCs)

- A person needed later may declare a state, such as Brandon's `conscious`/`unconscious`, and name the unusable one with `unavailable:`. If the narrator knocks him out, the game stops and asks the player to go on or go back.

Scene 1B's Brandon is the working example:

```yaml
character_placements:
  brandon: {parent: los_angeles_park, text: across the park from Kristin}
```

- **`participant_ids` is not presence.** Michelle is a participant in scenes
  where she is missing or held captive. Give every NPC who is physically in
  the scene a `character_placements` entry. Its `parent` is the area, or a
  thing inside it, and its optional `text` says where the character is from
  the protagonist's point of view.
- **An NPC who is only heard from is not placed.** That covers recordings,
  a remote connection or a video conference.
- **Who travels with the protagonist is plot, set only by the story.** Use a
  scene's `companions: [...]` from the start of the scene, or an
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
- **Learned names persist.** When the match call maps a new name to an
  entity, the bench stores it as a `wk_alias` fact. A wrong mapping therefore
  repeats in every later turn. That is one more reason to declare the right
  entity.

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

## Writing prompt lines that use the world model

These rules cover every string that reaches a model about places or things:
the narrator's THINGS and PLAYER lines, its rules and examples, the match call
and the bench judges. They add to the narrator rules in `AGENTS.md`: an 8th-grade
reading level, one idea per sentence, and every path that narrates.

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
  narration is brittle by definition. Resolution belongs to the engine's
  name resolver and the match call.

### Judges

- **Ask about state, not events.** Ask whether a thing ends the turn somewhere
  other than where it started, not whether it "moved" or "left". A round trip
  and a pocket-to-hand shift are events that change nothing.
- **Give the judge the containment it cannot infer.** Pass the things inside
  a place (`place_contents`), each thing's other names (`also_called`), the
  typed command separate from the engine's steps, and the narrator's own
  text separate from the story's own sentences.
- **Fix known judge faults before any comparison relies on the judge.**

## Verifying

- **Tree properties are deterministic.** Test them with the real package and
  a synthetic second package, with no network. Every audit must work on a
  package it has never seen.
- **A prompt rule is only observable live.** A test that greps the prompt
  proves the prompt says it, not that the model obeys. Run a single-scene
  smoke first, and read its `item_facts_unplaced` and match-call resolutions.
