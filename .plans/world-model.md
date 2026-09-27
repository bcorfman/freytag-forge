# World model: plan

Status (2026-09-26, end of session): decisions W1-W13 settled; S1 merged
(PR 480). S2 tasks A and C merged (PR 481). Tasks B and D-I are on
branch `world-model-s2b`, which is not pushed and has no PR. Next: the v36
comparison, then the PR. See "Resume here".
The task split is in section 11. Written at Brandon's request
after decision 1e (containment) in
[narrated-world-continuity.md](narrated-world-continuity.md) kept turning into
separate small decisions. This plan replaces decision 1e. It also gives
decision 1a's state axes, the `fixed` refusal and the protagonist's place a
home in one model. The capture loop, cause routing and rollout stay in the
continuity plan; this plan defines the world they write into.

## Resume here (2026-09-26, end of session)

Start from branch `world-model-s2b` (in the main repository; check it out
in a fresh worktree). It holds everything since PR 481, oldest first:

- 17437be: task B, the reply names the parent.
- 77c0240: task D, seats (W11). c06ee38, 7989583, c7705b8: fixes from
  the first seat smokes.
- ea59876: task E, seating before use (W12). 795580d: Jev answers a
  probability; a yes is `noul > 0.5`.
- d08defa: bench `item_facts.drop_rules`. 09e1d98: the two upright
  narrator rules and the 1A setting fact "The workstation chair is
  overturned." removed.
- b2a827f: task F. The new "use" question, standing up before leaving a
  seat (W13), a kind may declare `fixed`, and `seat` is movable
  furniture.
- 9210622: task G. The engine's steps reach the narrator as "Just before
  this: ..."; the stay-seated rule; a seat placed at its own furniture
  does not move; "overturned workstation chair" out of the 1A Details
  line.
- c29c2f7: task H. Kristin and Michelle are friends; the house is
  "Michelle's house"; a fixed back door in the kitchen. 35d490f: the
  entry text says "late-night shift", and Kristin "arrives at" the house.
- 7ea8c2b: Brandon is placed in the 1B park; script turn 10 fixed.
  79eeaa9: learned names (`add_alias`). 82b9c22 and d22a221: task I, the
  driver's seat and the pick-up step.

The full suite passes and ruff is clean at d22a221. The shipped
narrator's 1A baseline (`.plans/world-model-s1/narrator-1a-baseline.json`)
matches the code. The results of every smoke are recorded under tasks E,
F and G in section 11.

The Ringer manifests, checks and smoke variations lived in a session
scratchpad and are gone. To rebuild the W13 stand smoke: take
`item-facts-world-two-scene`'s item_facts and overrides, place the laptop
`{parent: michelle_workstation, text: on Michelle's workstation}`, set
`fixed_turns: 6`, turn both judges off, and use two 1A scripts:

- `stand-overturned`: "Read the files on my laptop.", "Open the
  drawer.", "Go out to the truck.", "Go back into the kitchen.", "Read
  the files on my laptop.", "Pick up Michelle's phone from the kitchen
  floor."
- `stand-upright`: "Set the workstation chair upright.", "Type a note on
  my laptop.", "Close my laptop.", "Walk to the back door.", "Search my
  laptop for Michelle's notes.", "Pick up the workstation chair and carry
  it out to the truck."

### Task H done: friends, not roommates (c29c2f7)

Brandon decided on 2026-09-26 to simplify the fiction so that place names
resolve. Kristin and Michelle are longtime friends, and Kristin does not
live in the house. The stand smoke's replies had named the house
"Michelle's home" or "inside the house". None of those names resolved, so
Kristin ended up outside every area.

- The story lines came from ChatGPT Desktop and were applied verbatim.
  Brandon then kept ChatGPT's "late-night shift" in the entry text and had
  the 1A plot line say that Kristin "arrives at" Michelle's house.
- The saved prompt missed four lines, which were found by a sweep and
  included: `storylet-routes.yaml` 73, 147 and 495, and `plot.md` 223
  ("tracked from her house").
- `mcgehee_home` is now named `Michelle's house`, with the aliases
  `Michelle's home` and `the house`.
- The back door is a fixed item in the kitchen, placed in 1A with no text.
  A reply that puts Kristin at the back door leaves her in the kitchen.
- The shipped 1A baseline changed only in the scene line, the two bios and
  the entry text's drive clause.
- Ringer passed on the first attempt on Luna. The full suite passes, and
  ruff is clean.

### Next 1: the two-scene smoke replicate

One replicate of `bench/variations/item-facts-world-two-scene.json` with
the fact and continuity judges, for a few cents. It answers W5's two
questions at the 92% bar (Brandon, 2026-09-26):

- at least 92% of turns where a thing's place is Kristin are judged
  consistent;
- at least 92% of reported places resolve (`item_facts_unplaced`).

One replicate near the bar means another replicate, not a decision.
Seating stays on: opening the laptop is not use, so turn 6 ("Open my
laptop.") adds nothing, and turn 13 happens at the truck, where there is
no seat.

Also watch the empty condition. After "Set the workstation chair
upright.", the reply gave the chair an empty condition in 2 of 3 runs of
the task G stand smoke (0 of 3 before it), so the chair stayed
overturned. Turn 7 ("Stand the overturned chair back up.") and the
drawer turns test it. If it recurs, the fix is a rule that replaces the
existing condition sentence rather than adding one: `For "condition",
give the new state in one or two words, like "open" or "upright".`

Accepted, not fixed (Brandon, 2026-09-26): the narrator may stand
Kristin up for "Open the drawer." despite the stay-seated rule (3 of 3).
The reply now records it, so the world and the story agree.

Result, first replicate (2026-09-26, at 35d490f): the run completed with
19 accepted turns and no failed replicate.

- **Places resolve: 41 of 43 (95%), which meets the bar.** Both misses
  are from turn 16 of 1B, "Walk over to the man watching me and hand him
  Michelle's phone.". The reply put Kristin and the phone at "stranger",
  and the match call mapped "stranger" to "man". Brandon has no name
  Kristin could know him by yet, so neither name resolved.
- **Held things: 11 or 12 of 15 turns (73-80%), below the bar.** Every
  place probe the fact judge ran on a held thing agreed with the tracked
  place, 14 of 14. The failures come from two causes that are not the
  label:
  - Turn 10 of the script, "Take Michelle's phone out and throw it hard
    against the kitchen wall.", runs after turn 9 has sent Kristin out to
    the truck. The narration threw the phone from outside. The reply kept
    the phone with Kristin, and turns 10 and 11 conflict.
  - Turn 18 follows on from the turn 16 miss. The handed-over phone was
    left unplaced, and turn 17's reply put it back with Kristin.
  A per-turn "all facts right" measure scored 6 of 15. It counts faults
  in other things, so it does not measure this question.
- **Empty condition: no repeat.** Turn 7's chair reply was `["upright"]`.
- Seen, but not measured: at turn 13 the narrator drove Kristin "back to
  her house, where her laptop is", which is the old shared-home idea.

Fixes after replicate 1 (7ea8c2b), both approved by Brandon: script turn
10 now reads "Go back into the kitchen and throw Michelle's phone hard
against the wall.". Scene 1B places Brandon "across the park from
Kristin", and the bench match call shows a placed character's place. No
alias was added, because narration safety scans aliases, so a "stranger"
alias would reject narration in scenes where Brandon is not allowed. A
"known as" label was considered and dropped, because the 1B narrator
prompt already names Brandon.

Result, second replicate (2026-09-26, at 7ea8c2b): the run completed with
19 accepted turns.

- **Places resolve: 50 of 52 (96%).** The two misses: at turn 7 Kristin
  was placed "at Michelle's workstation", which copies the chair's
  authored text and is a phrase, not a name. At turn 13 the truck was
  placed at "driveway", which is not in the world.
- **Held things: 15 of 15 place probes agree.** Every per-thing place
  probe on a held thing agreed with the tracked place (lowest 0.53). The
  handoff now lands: at turn 16 the match call mapped "stranger in the
  park" to Brandon, the phone was tracked with Brandon through turn 17,
  and it came back to Kristin at turn 18. The one held-thing conflict, at
  turn 18, is the judge reading the place "Brandon" against narration
  that calls him "the stranger". The judge does not know they are the
  same person.
- **The per-turn "all facts right" measure: 11 of 19.** This is the
  capture accuracy that the v36 comparison measures, not W5.
- **Empty condition: no repeat** (the turn 7 chair reply was `["upright"]`).
- Seen in both replicates: at turn 13 ("Read the files on Michelle's
  memory card with my laptop.") the narrator drives Kristin "back to her
  house". At turn 17 the reply listed 1B Details nouns as things, which
  created "stranger in the park" as a second entity alongside Brandon.

Verdict on W5: both questions pass. The bare parent name reads as held,
and replies use names, not phrases. No `Held by:` fallback is needed.

Follow-ups on the two issues above (Brandon, 2026-09-26):

- **Duplicate entity: fixed (79eeaa9).** The engine did not remember a
  name the match call had resolved. worldkeeper's `add_alias` now stores a
  learned name as a `wk_alias` fact, and the bench learns every name the
  match call maps to a thing or character. It never learns a name mapped
  to an area, so "floor" does not become a name for the kitchen. Replaying
  live turns 16 and 17 now resolves "stranger in the park" to Brandon.
- **Turn 13's drive: probed live, 10 calls per version, on the
  replicate 2 prompt.**

  | Version | Drives off | "Her house" | Reads at once |
  |---|---|---|---|
  | A: as recorded | 10 | 10 | 0 |
  | B: without "Write only what leads up to it." | 10 | 10 | 0 |
  | C: B, also without the reveal line | 10 | 3 | 0 |
  | D: engine step, seated in the driver's seat | 1 | 1 | about 3 |
  | E: D without the reveal line | 2 | 0 | about 1 |
  | F: D, and the engine hands her the laptop | 0 | 0 | 10 |

  The two prompt lines are not the cause. The narrator ignores where
  Kristin already is and invents a trip home. In D, 6 of 10 narrations had
  Kristin walk round to fetch the laptop before reading. Engine steps fix
  the turn, in line with the rule that the engine performs a command's
  prerequisite steps. The build is task I.
- **Task I (Brandon approved, 2026-09-26):**
  - The truck gets a fixed `driver's seat`.
  - Items may declare an authored `take_text`, and the laptop's is
    "Kristin picked up her laptop."
  - The seating step treats "already seated" as having a seat as parent,
    not merely an enterable parent, so being inside the truck no longer
    counts.
  - It prefers the seat next to the thing being used.
  - It hands the protagonist the thing, saying its `take_text`, unless she
    already holds it or it rests on a supporter.
  - The task also fixes `add_alias`, which called the host's resolver
    callback when checking for a conflicting name.

Task I was built as 82b9c22. The third replicate found a hole: the
narrator had left the laptop on the driver's seat, and a seat is a
supporter, so the engine skipped the pick-up. d22a221 fixes it. A thing
is now used in place only when it rests on the furniture its seat serves
(`seat_for`).

Results of replicates 3 and 4 (2026-09-26), each with 19 accepted turns:

- **Places resolve: 40 of 40, then 41 of 41.**
- **Turn 13, in replicate 4:** the engine seated Kristin and handed her
  the laptop. The narration reads the card at once, with no drive and no
  "her house".
- **The phone handoff:** "stranger" resolves to Brandon, and the phone
  stays tracked with him through turn 18.
- **Fact judge, per turn, all facts right:** 10, 11, 13 and then 14 of 19
  over replicates 1 to 4.
- **Continuity judge, replicate 4:** 0 contradictions and 0 scene
  restarts.
- **Judge noise left over:**
  - At turn 13 the judge counts the engine's seating move as a start
    conflict, because the narration does not show her sitting down.
  - At turn 18 it scores "Brandon" against narration that says "the
    stranger".

The v36 comparison, first pass (2026-09-26):

- **Before comparing, the bench's measurement was fixed (f0f58a4).**
  - The before-state is now read after the engine's seating steps and
    before the turn. It used to be read after the turn, so a
    scene-leaving turn was scored with Kristin already in 1B.
  - Both judges now receive `also_called`, each thing's other names.
  - `rejudge.py` re-scores any saved results folder.
- **v36's 2 saved replicates, re-scored with the current judges:** almost
  unchanged, 28 of 38 turns with every fact right.
- **Current branch at f0f58a4:** 4 single-replicate Ringer tasks.
- **Script turn 10 is left out of both arms,** because the script changed
  there.

| Measure (per-thing judge answers) | v36 (n=2) | Branch (n=4) |
|---|---|---|
| Place changes captured | 18/25 (72%) | 42/48 (88%) |
| Condition changes captured | 6/10 (60%) | 16/31 (52%) |
| Turns with every fact right | 26/36 (72%) | 43/69 (62%) |

- **Turns 4, 6, 12 and 13 fail in all 4 replicates.**
  - **Turns 4 and 12 are real capture misses.** The narrator unlocks the
    truck or starts its engine on its own, and the reply does not
    report it.
  - **Turn 6 is a measurement artifact.** The card's place label changes
    from the authored "with Kristin" to the bare "Kristin" when Kristin
    moves, and the judge scores that as an invented change. v36's store
    never changed labels, so this hurts only the branch arm. It cost 3
    turns.
  - **Turn 13:** the narrator reopens a laptop that is already open.

Why condition changes are missed (2026-09-27, the 4 comparison
replicates): 16 of 31 condition changes the judge saw were captured. The
engine lost no condition that a reply reported; every miss is a reply
that never reported the change.

- **8 misses: the truck.** The narrator itself unlocked the truck (turn
  4) or started its engine (turn 12). The truck has no declared state, so
  nothing in THINGS asks for it.
- **4 misses: turn 13.** The narrator re-opens a laptop that is already
  open. The hypothesis is that `open (or closed)` reads as "either" to the
  8b model; a probe is running.
- **3 misses: other small cases.**
- **An engine gap, found in replicate 3.** When the narrator had already
  seated Kristin, the seating step returned early and skipped the laptop
  pick-up. The fix is running as a Ringer task.

**Bookmarked (Brandon, 2026-09-27, "for now").** Capture is scored only
on places and declared state axes. Changes to undeclared conditions that
the narrator makes on its own, such as the truck unlocked or its engine
running, do not count as misses. Brandon is not convinced this will stay
unimportant, so revisit it before S4 (runtime capture). The alternative
is declaring more axes so that THINGS gives the narrator something to
report against.

### Next 2: the v36 comparison, then the PR for `world-model-s2b`

### S1 record

Branch `world-model-s1` held all of S1 on top of main after PR 479:

- task 2: bd8c46b and 529b6a0;
- task 3: 515201e and cf31bd2;
- task 4: 89b1eea and 54541e9;
- the exit gaps: 2c546cb and the round 2 commit after it;
- d498b9d: ruff formatting of the `.plans/` scripts.

The full suite is green (747 tests, 92.84% coverage), and ruff is clean across
the whole repository. The shipped narrator's 1A payloads are still
byte-identical to the pre-S1 baseline. S1 merged as PR 480.

The S1 exit is met:

- `tests/test_world_second_package.py` runs the section 10 storygame checks
  over continuity-initiative and a synthetic second package,
  `tests/fixtures/stories/lighthouse-keeper/`. The second package loaded
  zero-shot apart from one general loader fix: a delivery's own fact now
  counts as set in its scene, as the engine sets it.
- The whole tree survives SQLite save and load, snapshot and restore, and a
  `FactStore` clone. A created thing keeps its minted ID and is still found by
  name.
- `MemoryBackend` and `FactStore` give the same world.
- The protagonist starts each scene in the scene's `location_id`, and a scene
  change carries what she holds. A refusal is logged like any other
  placement.

Left for S2: W8's `companions` and `character_placements` front-matter
fields. S1's task list never scheduled them. Also left for S2 is the
`together()` question below.

What S1 left in place, for S2 to build on:

- **Package fields.** `world.yaml` declares `kinds` (typed `KindDeclaration`), a
  location `parent`, and item `kind`, `openable`, `open`, `hidden`,
  `contents` and `owner`. `Item.fixed` is `None` unless declared, and
  `WorldSchema.is_fixed` and `WorldSchema.kind_is` decide it.
- **Placements.** Scene 1A uses only the `{parent, text?, under?,
  part_of?}` form. The other scenes still use strings. `apply_scene_placements`
  runs at bootstrap and on a scene change. The loader simulates every scene's
  new-form placements and rejects bad ones.
- **The found card.** `memory_card_in_kristins_custody` is now
  `memory_card_recovered` everywhere outside `.plans/`. Its `on_assert` is
  `{move: memory_card, parent: kristin, text: with Kristin}` plus
  `{reveal: memory_card}`. The card starts hidden `under` the drawer.
- **Text on a move effect.** A move effect may carry `text`, which becomes the
  thing's authored place text until it or its holder moves
  (`World.place_text`). This was added in task 4 so the narrator still says
  "Michelle's memory card is with Kristin." once the card is found.
- **The shipped narrator reads a world view.**
  `CloudflareTurnProvider._placement_world()` clones `_placement_facts()`,
  applies world effects and wraps the result in a world. It is built once
  per rule call. The narrator leaves out things the world says are hidden.
  A new-form placement's line comes from `place_text`. Owner and placement
  rules cover only things with narrator text, so the truck and the
  workstation get no line.
- **The workstation's name.** The item is named `workstation` with `owner:
  michelle`, in the same way as the `drawer`. As `Michelle's workstation` it
  made the audit flag the beat detail "overturned workstation chair"
  (`test_real_package_has_no_ambiguous_owned_item`).
- **Bench and judge.** The bench seed skips hidden things and seeds the card
  (`with Kristin`) once the world reveals it. The judge treats a thing that a
  handoff's fact reveals through `on_assert` as revealed.

Materials in [world-model-s1/](world-model-s1/):

- `prompt_capture.py` records the shipped narrator's 1A payloads with the
  network stubbed: the opening plus the turn "Search the kitchen for signs of
  a struggle.", each with and without the found fact. It applies world effects
  after setting the fact, as every commit point does. Its default fact is
  `memory_card_recovered`. Run it from the repository root: `uv run python
  .plans/world-model-s1/prompt_capture.py OUT.json`.
- `narrator-1a-baseline.json` is its output from before S1, and the capture
  still matches it after task 4. S2 changes the narrator on the bench only,
  so the shipped narrator must keep matching it until S4.
- `s1t3_acceptance_draft.py` is task 3's acceptance test, which built the 1A
  conversion in a temp copy.
- `s1t2_check_example.sh` is the task 2 check. Reuse its structure:
  ownership, library boundary, acceptance, full suite, mutation checks,
  ruff, patch export. Grep only `*.py` files (`--include="*.py"`), because a
  bare `grep -r` matches `__pycache__`. Run acceptance tests with
  `PYTHONPATH=packages/worldkeeper/src:.` plus the acceptance directory, or
  `bench` does not import.

Lessons from task 2, for writing the next checks:

- Enforce the required tests in the check. Round 1 skipped them because only
  the spec asked for them. Mutation checks work.
- Scope a layering rule to the new code. A blanket rule ("story_package
  never imports runtime") pushed the worker to rewrite
  `_validate_narration_term_traps`, and that rewrite was dropped at
  integration.
- `uv sync` makes `packages/worldkeeper/src/worldkeeper.egg-info/`, which is
  now ignored. Run `uv lock` and `uv sync` yourself after a pyproject change;
  workers have no network.

`together()` (decided by Brandon, 2026-09-25): `World.area()` returns the
nearest area, so a phone in the kitchen and Kristin in the house were not
`together()`. Two entities are now together when one's area is the other's
area or contains it: Kristin in the house is together with the phone in the
kitchen, but two sibling rooms of the house are not together. Rejected:
comparing the top-level area, which would make every room of the house one
place. This library change rides with S2 task C.

This plan is self-contained so it can be picked up in a new chat with no
other context. The continuity plan's principles (its section 2) and working
rules (its section 3) apply here unchanged: every code change is a Ringer task
on GPT-5.6 Luna, and narrator strings are written at an 8th-grade reading level.

## Contents

1. Why a separate plan
2. What we take from world-model practice
3. Scope: the questions the model answers
4. The model
5. Operations and rules
6. What the narrator reads
7. Capture: from the narrator's reply to operations
8. Authoring
9. How the existing mechanisms map onto the model
10. Checks
11. Phases
12. Decisions for Brandon

---

## 1. Why a separate plan

The engine has a representation of the world but almost no model of how it
changes. On the bench (`bench/item_facts.py`) a tracked thing is a `place`
phrase of up to 80 characters plus up to two `condition` phrases. The narrator
effectively decides what every action does, and the engine works backwards
from the reply's phrases.

Each defect since round 3 has added one mechanism to that representation:

- binary state axes with aliases (decision 1a, round 4);
- the `fixed` flag on furniture, which refuses a place change;
- seeding the protagonist as a tracked thing in the scene's location
  (`_seed_protagonist`), and giving her line every turn (v30);
- the start-place rule and the "bigger place" rule for the protagonist's
  moves (v31, v33);
- the name-match call, which today runs only for names not already tracked;
- lifting reply entries the narrator put outside `item_facts`.

Each one is sound on its own terms. Together they are a world model built one
defect at a time, with no statement of what the world is. The symptom that
triggered this plan: the laptop was recorded "in her hand" with no record of
whether Kristin was at the truck or in the house. Container-shaped replies
such as `{"kitchen counter": {"contents": ["Michelle's phone"]}}` are still
dropped, because nothing in the representation can hold them.

There is also a structural conflict with the PRD. The PRD says facts are the
only durable truth, and the runtime's `FactStore` holds
`(predicate, subject, object, value)` facts. The bench's `item_facts` dict is
a second, separate store of truth. The runtime build must not copy it.

## 2. What we take from world-model practice

Source: Nate B. Jones, "Inside NVIDIA: What a world model actually is"
(an interview with Ming-Yu Liu of NVIDIA's Cosmos Lab, September 2026).
The article is about learned neural world models for robots and video. We
take its architecture, not its technique. Nothing here is learned or neural.

1. **Keep the world model separate from what acts on it.** The article traces
   this to Ha and Schmidhuber (2018): one part represents the environment and
   predicts how actions change it; a separate part chooses what to do.
   Producing a convincing outcome is not the same as modelling one. For us the
   narrator is the generator. The engine's model owns what an action does to
   the world. The narrator proposes; the model's rules decide what is legal and
   what follows from it. This is the PRD's "LLM-proposal-first" rule, applied to
   things and places.
2. **Scope the model to the job.** A model needs a useful representation of
   the part of the world the task depends on, not all of it. Section 3 writes
   our scope down, and anything outside it is out of the model.
3. **An observation can show a change without the action that caused it.**
   The narrator's reply reports end states ("the phone is on the counter"), not
   actions. Capture therefore turns an observed end state into an operation,
   and the model must derive the effects the reply did not state, such as
   everything Kristin carries moving with her.
4. **A symbolic simulator and a learned generator do different jobs.** The
   article describes a physics engine used alongside a learned model. Ours is
   a deterministic symbolic world with the LLM on top.
5. **A check proves only what it covers.** The article's example is a garment
   folded into the right shape but put in the wrong drawer. A place phrase can
   read correctly while the tree behind it is wrong, so checks in section 10
   test the tree, not the phrase.

The shape of the model borrows from interactive fiction's standard world model
(Inform 7): an object tree with typed relations, kinds that carry properties,
and rules that check and carry out actions. That model has been proven over
decades of parser games. Our difference is only where changes come from:
narrated prose rather than a parser.

## 3. Scope: the questions the model answers

The model must answer these, for any story package, every turn:

1. **Where is X?** Its immediate parent, and the chain up to a top-level area.
2. **Who has X?** Whether a character carries it, directly or inside
   something she carries.
3. **Are X and Y together?** Whether they share an area.
4. **What state is X in?** Its value on each declared axis, plus free
   condition phrases.
5. **Can X change like that?** Whether it can move, open or be carried.
6. **Can the player see X?** Whether X is hidden, for example inside a closed
   container or not yet revealed.
7. **Does the story still work?** Whether a thing a future transition needs is
   still available. The existing dependency analysis answers this; the model
   only has to feed it.
8. **Whose is X?** Its owner, which is not where it is. Kristin can hold
   Michelle's phone. The owner is how the narrator names a thing at first
   mention, and how "my laptop" or "her phone" resolves.
9. **Who goes where Kristin goes?** Which characters travel with the player
   character, so that moving her moves them.

Out of scope: force, weight, size, exact position within a parent ("near the
door"), time, and routes between areas. Detail like "face down" or "near the
door" may be kept as a condition phrase, but nothing reasons over it.

Also out of scope, because other parts of the package already model them:

- **Who knows what.** `knowledge.yaml` entries carry an `audience` (public,
  world-only, or named characters) and `entity_ids`. The world model does not
  duplicate this.
- **What a thing tells you.** The memory card's files, the photograph showing
  Michelle with Brandon, and the transit token's number sequence are
  knowledge attached to things through `entity_ids` and deliveries, not
  physical relations.
- **Access between areas.** Sealed exits, sealed detention sectors, a locked
  office and a maintenance route are story facts moved by storylets and
  pacing (`relay_open`, `evacuation_route_open`, `restricted_corridor_access`).
  A map with blocked connections would duplicate them.

These scope choices come from reading every file in
`data/stories/continuity-initiative/`. Section 4.6 lists what that reading
found.

## 4. The model

### 4.1 Entities and kinds

Every tracked entity has a stable ID, a display name, aliases and one kind.
Kinds form a hierarchy, as in Inform 7: a kind inherits every property, part
and rule of the kinds above it (decided by Brandon, 2026-09-25).

```text
entity
├── area                  part: floor; can hold characters and things
├── character             part: hands; carries things; captive|free
└── thing                 portable unless fixed
    ├── container         takes things "in"; may be openable (open|closed)
    │   └── vehicle       a container characters can be in; portable
    ├── supporter         takes things "on"
    └── furniture         fixed
```

- **The engine defines only these base kinds**, so it stays story-agnostic.
  A story declares each of its entities as an instance of a kind, and may add
  its own sub-kinds (a `desk` that is both furniture and a supporter) in the
  package. Runtime code never names a story's kinds or things.
- **A kind decides the relation.** A thing whose parent is a container is
  `in` it; a supporter, `on` it; a character, `carried_by`; an area, `in`. The
  narrator's preposition is never read (section 7).
- **A kind limits parents.** A phone cannot be carried by a truck, because a
  truck is not a character. These checks are invariants (section 4.4).
- **Inherited parts** absorb common phrases. Every area has a floor, so a thing
  on the kitchen floor is `on` the kitchen. Every character has hands, so a
  thing in Kristin's hand is `carried_by` Kristin.
- **Properties inherit and can be set per instance**: `fixed`, `openable`,
  `hidden`, declared axes. The drawer is an openable container that is fixed;
  the truck is a vehicle, not fixed, because it can drive away.

### 4.2 The tree

Every entity except a top-level area has exactly one parent and one relation
to it:

| Relation | Parent | Example |
|---|---|---|
| `in` | area, or a container | the phone in the kitchen; the card in the laptop |
| `on` | a supporter, or an area's floor | the phone on the kitchen counter |
| `under` | a thing | the memory card taped beneath the drawer |
| `carried_by` | a character | the phone carried by Kristin |
| `part_of` | a thing | the drawer part of Michelle's workstation |

`under` must be its own relation. The story's first key item depends on it:
the card is taped beneath the drawer, not in it. The narrator finding the card
in the drawer was a round 7 canon leak, so "under" and "in" must not collapse
into one relation.

A carried thing can be inside another carried thing: the card in a bag, the
bag carried by Kristin. "With Rebecca in her hands" and "with Kristin" in the
authored placements are both `carried_by`.

Two relations sit outside the tree, because they do not decide where
something is:

| Relation | Example | Effect |
|---|---|---|
| `owned_by` | Michelle's phone owned by Michelle | naming only; never moves anything |
| `accompanies` | Brandon accompanies Kristin from 1B | when Kristin moves, Brandon moves to the same parent |

A thing's owner is part of its display name today ("Michelle's phone"). The
model keeps it as a relation too, so "her phone" and "my laptop" resolve, and
so a thing narrated as new with an owner can be matched to the owned thing.

A worked example, scene 1A after Kristin takes the phone to the truck:

```text
outside the house            (area)
└── Kristin's truck          in
    ├── Kristin              in
    │   └── Michelle's phone carried_by
    └── Kristin's laptop     in   (narrated "on the seat"; detail not kept)
Kristin and Michelle's house (area)
└── kitchen                  in
    └── Michelle's workstation  in, fixed
        └── drawer           part_of, fixed
```

Everything else is derived by walking the tree: the phone is in the truck, the
truck is outside the house, so the phone is outside the house.

### 4.3 State

- **Axes.** Exactly two opposite poles with aliases, as decided in 1a. Setting
  one pole removes the other.
- **Conditions.** Up to two free phrases not on any axis, as today.
- **Availability.** The existing `destroyed` and `incapacitated` predicates.
- **Hidden or found.** An axis on a concealed thing. The memory card starts
  `hidden` and becomes `found` only by the story's own route. A hidden thing is
  never in THINGS and cannot be moved by a reply, which makes the round 7 leak
  structurally impossible rather than something a rule asks the narrator to
  avoid. Hidden is separate from "inside a closed container": the card is under
  the drawer, and opening the drawer does not reveal it.
- **Missing.** A thing the story says is gone has no parent, and it has a
  `missing` status. Michelle's tablet and work bag are "missing and not in
  their normal spots". They are tracked so that the narrator cannot find them
  in the house. "Where is X?" answers "unknown", never a guessed place.
- **Captive or free.** An axis on characters. Captives, Michelle in her
  holding block and Rebecca once captured all need it. A captive character's
  parent is an area like any other character's.

### 4.6 What the story package already says

A reading of all seven files in `data/stories/continuity-initiative/` found
these relationships. Each is either in the model above or deliberately left
out in section 3.

| Found in the story | Where | In the model |
|---|---|---|
| card taped beneath the drawer, hidden until found | `plot.md` 1A hidden canon | `under`, `hidden` axis |
| drawer in Michelle's workstation; KMS carved in it | 1A placements, cue text | `part_of`, fixed |
| drawer "holds pens, binder clips, a stapler, and spare batteries" | 1A setting facts | declared `contents`, expanded to entities (W9) |
| tablet and work bag missing | 1A beats, storylets | `missing` status |
| laptop in Kristin's truck outside the house | 1A placements | `in` truck, truck `in` outside the house |
| card "with Kristin"; archive "with Rebecca in her hands" | 1A and 3C placements | `carried_by` |
| Kristin opens the card on her laptop | 1A beat | card `in` laptop |
| phone owned by Michelle, laptop owned by Kristin | item names | `owned_by` |
| Brandon travels with Kristin from 1B | 1B beats onward | `accompanies` |
| captives, holding block, Rebecca captured | 2C-3C | `captive|free` axis |
| locked office, sealed exits, relay connected to JANUS | 3A-3C | story facts (out of scope) |
| photograph of Michelle with Brandon; files on the card | 1B, 1A | knowledge (out of scope) |
| who knows a fact; Brandon-only knowledge | `knowledge.yaml` `audience` | knowledge (out of scope) |
| `memory_card` falls back to `michelle_phone` | `world.yaml` `fallback_ids` | existing dependency analysis |

### 4.7 Story facts that restate a physical relation

The package already has story facts that say where a thing is.
`memory_card_in_kristins_custody` is asserted by the 1A delivery's `costs`
and by storylets, and the placement `memory_card: with Kristin` is shown only
`while_fact_true` of it. `portable_archive_secured` hides the placement "with
Rebecca in her hands". `rebecca_captured` and `michelle_reached` are similar.

If the tree also records the card as carried by Kristin, there are two truths
that can disagree. Decision W7 (decided) makes the binding one-way: setting
such a fact applies a declared world effect, and narrated moves never change
story facts. In this package the facts record events, not current places.

### 4.4 Invariants

The engine refuses any operation that breaks one of these, and records why:

1. One parent per entity; no cycles.
2. A top-level entity is an area.
3. `carried_by` points only at a character.
4. `in` points only at an area or a container; `on` only at a supporter or an
   area.
5. A `fixed` thing never changes parent.
6. A character's parent is an area or a container (a truck, a closet), never
   a character or a supporter.

### 4.5 Storage

At runtime the tree and state are facts in `FactStore`, keyed by entity ID:
`Fact(predicate="in", subject="michelle_phone", object="kristin_truck")`,
`Fact(predicate="state", subject="michelle_drawer", value="open")`. They are
saved, cloned for candidate turns and restored exactly like every other fact.
No second store of truth.

The model lives in the `worldkeeper` library (section 4.8), which never owns
state. It reads and writes facts through a small backend interface that
`FactStore` already satisfies, so `FactStore` stays the only truth.

The bench keeps its own harness, but it uses the same library with the same
operations, so the bench measures the thing the runtime will run.

### 4.8 The `worldkeeper` library

Decided by Brandon, 2026-09-25 (W10): the model is its own self-contained,
reusable library named `worldkeeper`, designed so it could be published to
PyPI later even if it never is. Existing libraries were considered first and
rejected: Microsoft's TextWorld (`textworld.logic`) is closest, with a type
hierarchy, typed facts and rules, but its rules model player commands rather
than narrated end states, its `State` would be a second store of truth, it has
no parent chain, hidden things, owners or companions, and it pulls in a native
Z-machine emulator (`jericho`) and a pinned `tatsu`. Evennia is a whole MUD
server; Tale, IntFicPy, textadv and adventurelib are unmaintained or too
small. TextWorld's kind declarations remain a useful reference for the
`world.yaml` schema.

**Storage through a backend interface.** The library never imports
`FactStore` and never keeps its own state:

```python
class FactBackend(Protocol):
    def matching(self, predicate: str, subject: str | None = None) -> tuple[FactLike, ...]: ...
    def assert_fact(self, fact: FactLike) -> None: ...
    def retract_fact(self, fact: FactLike) -> None: ...
```

`FactStore` already has these three methods, so freytag-forge passes its store
in directly; another user could pass a dict-backed store. Cloning, rollback and
saves are unchanged.

**What goes where:**

| In `worldkeeper` (story-agnostic, no LLM) | Stays in freytag-forge |
|---|---|
| Base kinds, inheritance, story sub-kinds | Reading YAML and `plot.md`; the library takes plain data |
| Entities, the tree, the invariants | The narrator's reply format and prompt text |
| Operations and derived effects (W3, W8 rules) | The match call; the library accepts an optional resolver callback for names it cannot find |
| Minting IDs; name and alias lookup | Deciding when a story fact's world effects apply (W7); the library applies an effect list |
| Visibility (hidden, closed containers); what is given with an open container (W9) | Formatting THINGS lines |
| The place label: authored text while still true, else the parent's name (W4) | The bench, judges and saves |

**Structure and rules:**

- A uv workspace member in this repository (`packages/worldkeeper/`) with its
  own `pyproject.toml`; storygame depends on it as it would on a published
  package. Publishing later is only a release step.
- Standard library only: no pydantic or other runtime dependency.
- It never imports `storygame`. A test enforces this, and another enforces
  the standard-library-only rule.
- Its own tests use synthetic worlds only; continuity-initiative tests stay in
  storygame. Principle 8 (any story package) is then part of how the library
  is built, not a check afterwards.
- `worldkeeper` was free on PyPI on 2026-09-25 (the JSON API returned 404).
  PyPI can still refuse a name too close to an existing one; only registering
  proves it. Reserving it early is a public action and needs Brandon's go.

## 5. Operations and rules

Capture produces operations; only operations change the model.

| Operation | Does | Refused when |
|---|---|---|
| `move(x, relation, parent)` | sets x's parent | an invariant would break; x is fixed |
| `set_axis(x, pole)` | sets one pole, clears its opposite | x has no such axis |
| `set_conditions(x, phrases)` | replaces free phrases (max two) | more than two, or too long |
| `create(x, kind, relation, parent)` | adds a narrated new thing (decision 1c) with a minted ID | the name resolves to an existing entity |
| `make_unavailable(x, predicate)` | `destroyed` or `incapacitated` | never refused; the story check decides what follows |

**A created thing is a full entity (decided by Brandon, 2026-09-25).** If the
narration creates a thing, it must exist in the world facts and be
referenceable, not only in narration. So `create`:

- mints a stable, deterministic ID in the engine, never from the model:
  `n_` plus a slug of the name plus a counter (`n_usb_drive_1`), unique and
  stable across save and load;
- records the thing as facts exactly like an authored entity: name, kind
  (default `thing`), parent, and owner when the reply gives one (owner capture
  already exists in `_resolve_new_items`);
- after that the thing is ordinary: the name resolver finds it from player
  input and later replies, THINGS gives it under the 1c reference rule, and it
  is saved and restored.

The narrator is already asked for new things ("Every time your story moves
or changes a thing, or puts a new thing in a place, add that thing to
item_facts."), so only the ID and facts were missing. Today the bench stores a
narrated thing under its name string only.

Derived effects the model applies with no reply saying so:

- Moving anything moves everything under it. Kristin walking to the truck
  moves the phone she carries. Nothing else is written.
- A thing inside a closed container is hidden from the player's view until
  the container is opened. (Protected knowledge still follows the existing
  reveal rules; this only covers what can be seen.)

The closed-container rule is decided (W3). A reply may move a thing to an
area its holder is not in (the phone tossed out of the truck window): the
engine has no map to tell a real move from a mistaken one (routes are out of
scope, section 3), and refusing would drop a narrated change. If the bench
shows the narrator teleporting things by mistake, find its cause then.

Every refused operation refuses only itself, never the turn, and is recorded
in the turn's issues. A refusal is still a story failure under the rule that
every reply change must land, so the continuity plan's regeneration path
(cause routing) is where a refused change goes next.

## 6. What the narrator reads

The narrator never sees relations, IDs or the tree. The engine never composes
English from the tree either (W4, decided): generating sentences from kinds
and relations needs templates for articles, plurals and chain depth, and loses
authored detail. The THINGS line's `Place` is one of two things:

1. **The authored `text`**, verbatim, while it is still true: neither the
   thing nor anything above it has moved since the scene began. The check is
   structural and never reads the words.
2. **Otherwise, the parent's name only**, as a label. It is the same form the
   narrator's reply uses (section 7), so what it reads is what it writes.

```text
THINGS:
- Kristin. Place: Kristin's truck.
- Michelle's phone. Place: Kristin. Condition: not damaged.
- Kristin's laptop. Place: in Kristin's truck outside the house.
```

(The laptop still shows its authored text because neither it nor the truck
has moved. If the truck drives away, the laptop's line becomes
`Place: Kristin's truck.`)

- Because the line comes from the tree every turn, it cannot go stale.
- Which things are given stays as decided: the ones the command refers to and
  those a current beat or progression involves (1c), plus the protagonist
  every turn.
- When an open container is given, its visible direct contents are given
  with it (W9). Otherwise "Open the drawer." hands the narrator the drawer
  but not what is in it, and it invents contents. Hidden things are never
  given.
- How a bare parent name reads to the narrator is decision W5.

Because the line is built from the model, the "bigger place" and start-place
rules may no longer be needed. Remove them only after a bench run shows the
narrator still reports Kristin's moves without them (principle 5: remove a
mechanism before adding a rule, but verify the removal).

## 7. Capture: from the narrator's reply to operations

Capture stays in the one narration call. Its single job is to translate each
reply entry into operations the model then validates. No place phrase is ever
parsed (decision W1, Brandon, 2026-09-25).

**The reply names the parent.** `place` changes from a phrase to the name of
a thing, character or area:

```json
{"item_facts": {
  "Michelle's phone": {"place": "Kristin", "condition": ["not damaged"]},
  "Kristin": {"place": "Kristin's truck"},
  "memory card": {"place": "drawer", "under": true}
}}
```

1. **Key to entity.** Resolve the reply's key to a tracked entity by exact
   name or alias. If that fails, use the existing match call (as today, only
   for unresolved names). If that fails, the key is a new thing: `create`.
2. **`place` to parent.** Resolve the `place` name with the same resolver:
   exact name or alias, then the match call. This is name resolution, which
   the engine already does, not phrase parsing.
3. **Relation from the parent's kind** (section 4.1). `"under": true` is the
   one relation a kind cannot imply, so it is an optional flag.
4. **An unresolved name still lands.** If no parent is found, record the name
   as the thing's place with an unknown parent. Never drop it and never guess
   the scene's location (place-is-the-most-local-container). The next THINGS
   line shows it, and the offline report counts these.
5. **Container-shaped replies.** `{"kitchen counter": {"contents": [...]}}`
   becomes one `move` into the kitchen counter per listed thing, with the
   relation from its kind.
6. **Condition phrases** go through the existing axis matching, then
   `set_axis` or `set_conditions`.

The cost is a changed reply format, so capture is re-measured against the 92%
bar. The risk is whether the 8b model writes `"Kristin"` where it now writes
`"in her hand"`. One smoke replicate answers that before any full run. The
narrator rule and example that ask for this must be rewritten at the
8th-grade level, replacing the current place example rather than adding one.

## 8. Authoring

Following principle 9, `plot.md` settles the world first; the other package
files follow it.

- **Areas** are declared with a parent, for example `kitchen` in `the house`.
  Scene `location_id`s become top-level or nested areas.
- **Kinds and properties** (`container`, `supporter`, `openable`, `fixed`) are
  declared per item in `world.yaml`, alongside the existing `fixed` field.
- **Placements** (W4, decided) name the parent by ID, with an optional
  authored `text` for the narrator. Loading checks the ID like any other
  reference and never reads `text`:

  ```yaml
  item_placements:
    michelle_phone: {parent: kitchen, text: on the kitchen floor}
    kristin_laptop: {parent: kristin_truck, text: in Kristin's truck outside the house}
    memory_card: {parent: michelle_drawer, under: true}
  ```

  Whether `text` agrees with `parent` is the author's job; no check reads it.
- **Hidden things get declared places.** The authoring rule that keeps a
  hidden item out of `item_placements` exists because placements were sent to
  the narrator as sentences. A `hidden` thing is never in THINGS, so its place
  can be declared. Delivery text and the `**Hidden canon:**` line stay.
  `docs/markdown-story-authoring.md` changes with this.
- **Declared contents** (W9, decided) are one line on the container; the
  loader expands each into an entity with an ID, parented to the container:

  ```yaml
  - {id: michelle_drawer, name: drawer, kind: container, openable: true, fixed: true,
     contents: [pens, binder clips, stapler, spare batteries]}
  ```

  The setting fact "The drawer holds pens, binder clips, a stapler, and spare
  batteries." is removed: the tree says it, and the sentence would go stale
  once a thing leaves the drawer.
- **Hidden things and bindings** (W7) are declared with the item: the memory
  card starts `hidden`, and `memory_card_recovered` (renamed, W7) moves and reveals it.
- **Add them scene by scene as problems surface**, not exhaustively (standing
  preference). Scene 1A needs: the house, the kitchen, outside the house,
  Kristin's truck, Michelle's workstation.
- Story text changes go to ChatGPT Desktop with a self-contained prompt.

## 9. How the existing mechanisms map onto the model

| Today (bench) | In the model |
|---|---|
| `place` phrase | `place` names the parent; relation from its kind; unresolved names kept |
| state axes (1a) | axes, unchanged |
| `fixed` refusal | invariant 5 |
| protagonist seeded "in {location}" | the protagonist's parent is the scene's area |
| protagonist line every turn | unchanged |
| start-place and bigger-place rules | candidates for removal once the THINGS line carries the area (section 6) |
| name-match call | step 1 of capture, unchanged |
| dropped `contents` replies | `move` per listed thing |
| `destroyed` / `incapacitated` | `make_unavailable`, feeding the existing dependency analysis |

## 10. Checks

Two gates, as elsewhere in this project.

**Deterministic (authoritative).** Unit tests of the model module with no
live worker and no story names in the module:

- each invariant refuses its violation and records why;
- moving a container moves its contents, to any depth;
- the THINGS line for each entity matches the tree after every operation;
- a saved and loaded game gives the same tree;
- package loading rejects a placement with an undeclared parent;
- declared `contents` expand to entities with IDs, parented to the container;
- a created thing gets a minted ID, is found by the name resolver afterwards,
  and survives save and load;
- an open container's visible contents are given with it; hidden things never
  are;
- every case runs against a second, synthetic package as well as
  continuity-initiative (principle 8);
- `worldkeeper` never imports `storygame` and has no runtime dependency
  outside the standard library;
- `FactStore` satisfies the `FactBackend` interface, and a dict-backed
  backend passes the same library tests.

**Live (integration and quality).** The bench scores capture per operation
type (`move`, `set_axis`, `set_conditions`, `create`) against the 92% bar,
grading the whole world state every turn. The fact judge reads the rendered
tree so that it grades location, not wording. The hosted E2E `@world-state`
test asserts the phone's parent is Kristin, not merely that a scene exists.

## 11. Phases

Each phase is Ringer tasks on Luna; Claude writes the spec and check, and
reviews the patch. Phases are numbered S0-S4 so they are not confused with
decisions W1-W10. Scope decided by Brandon, 2026-09-25 (W6).

**S0 - Decisions.** Brandon settles section 12. Nothing is built before.

**S1 - The model and the package schema.** No billed runs.

- Task 1: the `worldkeeper` library (section 4.8) in
  `packages/worldkeeper/`: kinds and inheritance, the tree, axes, invariants,
  operations, ID minting, the W3 closed-container rule, the W8 companion rule,
  W9 contents, and the W4 place label, all through the `FactBackend`
  interface. Synthetic-world tests only, plus the no-`storygame`-import and
  standard-library-only tests.
- Task 2: wire it into storygame: `FactStore` passed as the backend, the
  package data handed to it as plain data, W7 effects applied when a story
  fact is set. This task and the ones below depend on task 1.
  Task 1 is done (PR 479). Task 2 is done (branch `world-model-s1`,
  commits bd8c46b and 529b6a0). worldkeeper is a uv workspace dependency.
  `storygame/runtime/world_model.py` is the adapter. `world.yaml` facts may
  declare `on_assert` effects, which apply once per fact through a sweep
  after every commit point, leaving a `world_effects_applied` marker.
  Bootstrap seeds the world, and the provider cannot write `wk_` facts. The
  two library fixes from task 1's review landed with it: story-effect moves
  carry companions, and `create()` lost `parent_id`. So did a third: a
  companion with no place never follows. The schema data is built in
  `storygame/story_package/world_schema.py`, and the next task extends it.
- Package schema and loader: `kind` on items, `parent` on locations, an
  optional `kinds` list, placements as `{parent, text, under}`. Loading
  rejects unknown IDs and parents a kind does not allow. String placements
  still load, so nothing breaks before it is converted.
  Done as task 3 (commits 515201e and cf31bd2), together with the narrator,
  bench and docs bullets below.
- The shipped narrator: `_placement_rules`
  (`storygame/runtime/cloudflare.py`) reads `text` and says exactly what it
  says today. This is the only change to shipped behaviour, and it must change
  nothing the player sees. The loader (`storygame/story_package/loader.py`)
  and the bench readers (`bench/item_facts.py`, `bench/judge_input.py`) are the
  other placement readers.
- Convert continuity-initiative scene 1A only: the kitchen and
  outside-the-house areas, the truck, the workstation, the card's hidden place.
  Structured YAML edits in a Ringer task; no story prose. Keep the setting
  fact "The drawer holds pens, binder clips, a stapler, and spare
  batteries." through S1, because the shipped narrator does not read the
  tree yet. Removing it now would change what the player sees. It goes when
  THINGS gives an open container's contents (S2 on the bench, S4 at runtime).
  The shipped narrator's 1A payloads must stay byte-identical to the
  baseline captured before S1 (opening and one turn, with and without the
  card custody fact).
- Update `docs/markdown-story-authoring.md` for hidden places and the new
  placement form.
- The 1A conversion and the W7 rename are done as task 4 (commits 89b1eea
  and 54541e9). See "Resume here" for the move-effect `text`, the narrator's
  world view and the workstation's name.
- Exit: the section 10 unit tests pass on continuity-initiative and a
  synthetic second package; full suite green.

**S2 - The bench uses the model.** Billed.

S2 is split into Ringer tasks on branch `world-model-s2` (S1 merged as PR
480):

- **Task A: the bench store is the world.** `ItemFactsProvider` keeps no dict
  of places. Every tracked place, axis pole and condition is a `wk_*` fact in
  `state.facts`, and `item_facts` becomes a read-only view rendered from the
  world. The reply format and prompt wording do not change. A phrase that
  names no entity lands as an unplaced name, and each turn records these as
  `item_facts_unplaced`. Characters are shown by their short name
  (`Kristin`). Variation state axes become world axes; the drawer's axis must
  use the world's `open`/`closed` poles. Done as 7e32ab1 (five Ringer
  rounds squashed). Review found what the checks missed: a move out of a
  closed container was refused, match calls ran once per name, and view
  reads re-seeded the store. The last was a worldkeeper bug: `seed()`
  re-hid revealed things. Lesson for B's check: guard the patterns a
  review found, and read the whole diff, since one round added a
  `seed_defaults()` alias only to pass a grep.
- **Task B: the reply names the parent.** THINGS and PLAYER lines follow
  W4 and W5. The place rule and the output example are replaced: the lantern
  becomes `{"place": "Kristin"}`, with an optional `"under": true`. The
  bigger-place rule ("name both, like the passenger seat of the truck") goes
  in this task, not S3, because it asks for a phrase and W1 asks for a name.
  Container-shaped replies land. Unresolved place names join the existing
  match call's NEW NAMES. A given open container brings its visible contents
  (W9). A new variation drops the drawer-contents setting fact. Two
  corrections to task C's section of `docs/markdown-story-authoring.md` ride
  along: the protagonist's own placement replaces where she starts, not the
  scene's `location_id`; and the companion and protagonist roles are
  written without gendered pronouns, like the rest of the guide.
  Done as 17437be on branch `world-model-s2b` (two Ringer rounds
  squashed). Choices the plan left open: a character named at furniture
  (Kristin "at the workstation") lands in the furniture's area, since a
  character cannot be on a supporter; the match call lists nearby areas
  and placed characters only when it carries a place name, and
  `_MATCH_SYSTEM` gained one sentence mapping a spot in a room to the
  room. Review found what the check missed: the echo test guessed the
  relation from the parent's kind, which refused an echo of the fixed
  drawer (`part_of`); three owner tests had been weakened to expect match
  calls; and required repository tests were missing because the check
  grepped for words, not test names. Lesson for later checks: require
  named tests and run them.
- **Task C: W8's front matter.** `companions` and `character_placements`,
  in the loader and in `apply_scene_placements`, plus the decided
  `together()` rule in `worldkeeper`. It is independent of A and B. Done as
  1ab6d22.
- **Task D: seats (W11).** `enterable` and `enter_pole` in `worldkeeper`,
  item axes and `seat_for` in `world.yaml` and the loader, the workstation
  chair declared as a seat, and THINGS giving a furniture's seat with it.
  The shipped narrator's 1A payloads must stay byte-identical. Then a
  small smoke with "Sit in the workstation chair." on an overturned chair,
  separate from the v36 script.
  Done as 77c0240 (two Ringer rounds). Round 2 removed two library
  changes nobody asked for and added the seat tests round 1 skipped. The
  smoke runs led to three follow-ups: c06ee38, 7989583 and c7705b8 (see
  "Resume here"). W12 replaces seat smoke 3 as the next step.
- **Task E: seating before use (W12).** `use_seated` on items and
  `right_text`/`enter_text` on seats in `world.yaml` and the loader, with the
  loader rejecting a seat that lacks either line. A Python Jev client and
  the yes/no question. The two checks and the added sentences on the bench
  turn path. The shipped narrator's 1A payloads must stay byte-identical.
  Unit tests stub Jev and cover: overturned and unseated (both lines),
  upright and unseated (enter line only), already seated (nothing), in the
  truck (nothing), no seat nearby (nothing), and a "no" answer (nothing).
  The seating logic is `storygame/runtime/seating.py`, story-agnostic and
  handed the question as a callable, so S4 can reuse it with the Worker
  route. The bench turn record's `player_input` is the command the narrator
  received, including the added steps, so the judges do not count the
  sitting as beyond the command. The typed input is kept as
  `typed_input`, and the added steps as `seating_steps`.
  Done as the commit after ac07f03 (two Ringer rounds; round 1 skipped the
  named tests). Known gap for S4: the bench applies the seating before the
  turn, so a rejected turn keeps Kristin seated with no narration. The
  runtime version should run inside the turn's snapshot so a rejection
  undoes it.
  Jev answers a probability (`{"type": "noul", "noul": 0.78}`), not a
  boolean, so the first smoke asked but never seated anyone; 795580d reads
  `noul > 0.5`, as `bench/jev-judge.mjs` does.
  W12 seat smoke (2026-09-26, 3 replicates each of `laptop-overturned` and
  `laptop-upright`, variation in the session scratchpad): Jev answered all
  questions correctly (yes for reading files; no for setting upright,
  knocking over, standing up and carrying the laptop). The engine added the
  right steps every time it was asked, and the narration never seated
  Kristin before righting the chair. Both steps narrated in order 4 of 5
  times (one reply dropped the sit sentence); the sit step alone narrated 2
  of 3 times (one reply righted the already upright chair instead). The
  remaining faults are capture, not W12: a narrated stand-up not captured,
  so Kristin stayed "in" the chair and no question was asked; "Set the
  workstation chair upright." captured as Kristin sitting in it (2 of 3);
  and one reply putting the chair's place as Kristin, after which seating
  was refused as a cycle.
  Without the two-line upright rule (d08defa added `item_facts.drop_rules`;
  same scripts and replicates, every prompt confirmed without the lines):
  the added steps were narrated in order 12 of 12 times (both steps 7 of 7,
  sit alone 5 of 5), against 6 of 8 with the rule; no turn seated Kristin
  before righting the chair; Jev answered every question correctly. The
  "set upright" command was no longer captured as Kristin sitting. Both arms
  still have the narrator call the chair "overturned" after it was righted,
  which looks like the authored setting fact "The workstation chair is
  overturned." still reaching the prompt (W9's stale-sentence problem), and
  one reply captured that description as the chair's state. Brandon
  (2026-09-26): remove both. The two lines are gone from
  `_SINGLE_CALL_RULES`, and "The workstation chair is overturned." is gone
  from the 1A setting facts; the chair's axis already starts it overturned.
  The shipped narrator's 1A baseline was regenerated, and it differs only
  by that sentence.
  Then a seat smoke with "Read the files on my laptop." in the kitchen, on
  an overturned chair and again on an upright one, and a run without the
  two-line upright rule to decide whether it goes.
- **Task F: the "use" question, standing up, movable seats (W12, W13).**
  The Jev "use" question is rewritten so opening, closing and turning the
  laptop on or off are not use. A second Jev question and `leave_text`
  stand a seated Kristin up before a command that needs it. `worldkeeper`
  kinds may declare `fixed`, and `seat` becomes `[furniture, supporter]`
  with `fixed: false`. The check calls Jev live on eight "use" cases and six
  "stand" cases; the old question is asked the same "use" cases for the
  record. The shipped narrator's 1A payloads stay byte-identical.
  Done as b2a827f (two Ringer rounds; round 1 skipped the named tests, as
  in task E). Live Jev: the old "use" question answered "Open my laptop."
  as use; the new one answered all 8 "use" cases and all 6 "stand" cases
  right. Next: a seat smoke with a stand-up case.
  W13 stand smoke (2026-09-26, `stand-overturned` and `stand-upright`, 3
  replicates each, variation in the session scratchpad, laptop on the
  workstation): Jev answered every seating and standing question right,
  and every added step was narrated, in order (8 stand steps, 9 sit
  steps). The movable chair was carried to the truck 2 of 3 times, and
  held by Kristin once. Faults found, none in the engine's steps:
  1. With two added steps (right the chair, sit), the narration stopped
     after them and never read the files, and the reply omitted
     item_facts (3 of 3). With one step it finished the command.
  2. "Open the drawer." while seated: Jev said stay seated, but the
     narration stood her up 3 of 3, and the reply kept her in the chair.
  3. A reply giving the chair's place as the workstation put the chair on
     the desk (3 of 3 in `stand-upright`), since the chair is no longer
     fixed.
  4. The narration called the righted chair "overturned" twice. The 1A
     Details line "overturned workstation chair" still reaches the prompt.
  Brandon (2026-09-26): fix 1, 3 and 4, and add a rule for 2. Task G:
  1. The engine's steps reach the narrator as a separate PLAYER line,
     "Just before this: ...", not as commands in front of the player's
     command. The seat's authored lines become past-tense statements
     ("Kristin set the workstation chair upright."). The turn record and
     the judges still get the steps with the command.
  2. While Kristin is seated when the prompt is built, the bench narrator
     gets one rule: "Kristin stays sitting in the workstation chair."
     She is only seated then when Jev said she need not stand.
  3. A reply giving a seat's place as the furniture it is `seat_for` is a
     quiet no-op, like a thing named as its own place.
  4. "overturned workstation chair" leaves the 1A Details line. The
     bullet "The chair at Shelly's workstation has been overturned." stays:
     it never reaches the narrator, and knowledge and storylets cite the
     overturned chair as evidence.
  Done as 9210622 (one Ringer round). Stand smoke rerun on it (same
  scripts, `item-facts-w13g-stand-smoke-*`): Jev and the engine's steps
  were right on every turn.
  1. Fixed: with two added steps, the command was carried out 5 of 5
     times (was 0 of 3). The narration now shows the command, not the
     steps.
  2. Not fixed by the rule: the rule was in every prompt, and "Open the
     drawer." still stood her up 3 of 3. "Close my laptop." kept her
     seated 3 of 3. The replies now record her standing, so world and
     story agree.
  3. Fixed: the chair stayed off the desk 3 of 3.
  4. Fixed: no narration called the chair overturned.
  Capture faults left, for the two-scene run to measure: "Set the
  workstation chair upright." captured with an empty condition, so the
  chair stayed overturned (2 of 3); and places the engine did not resolve
  ("Michelle's home", "inside the house") left Kristin outside every area,
  so no seating question was asked on the next laptop command.
- Then the smoke replicate and the v36 comparison below.

- Capture produces operations; THINGS follows W4 and W5; the reply names the
  parent; the system prompt's place example is replaced.
- One smoke replicate first, answering W5's two questions. Then compare
  against v36 on the same script.
- Exit: no capture category worse than v36, and container-shaped replies
  land.
- The continuity plan's Phase 0 bar (92% per change type) restarts on the new
  reply format from here, with v36 as the baseline.

**S3 - Remove what the model makes redundant.** One run per removal: the
start-place rule, the bigger-place rule. Keep a removal only if the numbers
hold.

**S4 - Runtime.** Capture during play, the tree in saves (schema bump), cause
routing: hand over to the continuity plan's Phases 4-6, which build on this
model instead of a `place`/`condition` dict.

## 12. Decisions for Brandon

W1. **How a reply's place becomes a relation and parent. Decided (Brandon,
2026-09-25).** Brandon rejected parsing the place phrase (finding names in it
and reading the relation from its first word) as brittle, and asked for an
inheritance-like model instead. Decision: kinds form a hierarchy (section
4.1); the reply's `place` names the parent; the engine resolves that name
with its existing resolver; the relation comes from the parent's kind, with an
optional `under` flag (section 7). Rejected: phrase parsing; a match call for
every changed place.

W2. **Relation set. Decided with W1.** `in`, `on`, `under`, `carried_by`,
`part_of` in the tree, and `owned_by` and `accompanies` outside it. Every
relation but `under` follows from the parent's kind. "Behind" and "beside" are
not relations; the narrator names the nearest parent, and detail can be kept
as a condition phrase.

W3. **Closed containers. Decided (Brandon, 2026-09-25).** When a reply puts
a thing into, or takes it from, a closed container, the move is accepted and
the container is set `open` as a derived effect, because the narration showed
it happen and narrator initiative is not a failure. The engine applies a
reply's moves first and its states second, so a reply that also says the
container is closed wins. Opening makes contents visible but never reveals a
`hidden` thing. The rule belongs to the container kind, so every openable
container inherits it. `locked` is left out until a story needs it. Rejected:
refusing the move (drops a narrated change); accepting it with the container
still closed (an impossible state).

W4. **Where kinds, areas and starting places are declared. Decided (Brandon,
2026-09-25).** Base kinds live in the engine. What an entity is (its kind,
properties, and an area's parent) goes in `world.yaml`, next to the existing
`fixed` field, with optional story sub-kinds in a `kinds` list. Where an
entity starts goes in each scene's `plot.md` `item_placements`, as a parent
ID plus optional authored `text` (section 8). Hidden things get declared
places. Brandon rejected rendering the narrator's placement sentences from the
tree as brittle; the authored text is shown while it is still true, and a bare
parent name after that (section 6).

W5. **How a bare parent name reads. Decided (Brandon, 2026-09-25).** After a
thing moves, THINGS shows only its parent's name (`Place: Kristin.`), the same
form the reply writes. The system prompt's place example is replaced, not
added to: a picked-up lantern becomes `{"place": "Kristin"}`. The S2 smoke
replicate must answer two questions before a full run: does narration show a
thing whose place is a character as held by that character (fact judge), and
do replies use bare parent names rather than slipping back to phrases (the
harness counts unresolved names)? If either fails, the fallback is a separate
`Held by:` label for things whose parent is a character. Rejected: a relation
word before the name ("with Kristin"), because it composes English and the
narrator would echo it back, forcing phrase parsing.

W6. **Scope of the first build. Decided (Brandon, 2026-09-25).** Three steps
before the runtime turn (section 11, S1-S3). "Bench first" cannot mean bench
only: the shipped loader and narrator both read item placements, so S1 changes
the shared schema and loader, with the shipped narrator's output kept
identical.

W7. **Story facts that restate a relation. Decided (Brandon, 2026-09-25):
one-way.** A story fact may declare world effects in `world.yaml`; setting the
fact from any source (storylet operation, route event, delivery `costs`)
applies them. Narrated moves never change story facts.

```yaml
facts:
- id: memory_card_recovered
  on_assert:
  - {move: memory_card, parent: kristin}
  - {reveal: memory_card}
```

The story fact records that an event happened and stays true; the tree
records where things are now. This is the only way a hidden thing becomes
found. Only facts with a clear world effect declare one: `rebecca_captured`
sets Rebecca `captive`; `portable_archive_secured` declares none, because the
archive has no single new holder.

Rejected: a two-way binding. Tracing the package showed it causes a replay
bug: `SL-1A-E` ("The KMS Mark", finding the card beneath the drawer) activates
while the custody fact is false, so a narrated drop that retracted the fact
would offer the find again with the card on the truck seat. Also rejected: no
binding, which leaves the card hidden under the drawer after the story says
Kristin found it.

Consequences, all in S1 as a Ringer task (structured data, not prose; Brandon
confirmed a label rename is not a prose rewrite):

- Rename `memory_card_in_kristins_custody` to `memory_card_recovered` everywhere
  it is referenced (`world.yaml`, `knowledge.yaml`,
  `storylet-routes.yaml`, `pacing.yaml`, `handoffs.yaml`, plus the two
  mentions in `storylets.md` and the placement guard in `plot.md`).
- Drop "and is carrying it" from its purpose, which now states the event.
- Remove the card's `while_fact_true` placement guard; the tree records the
  move.
- The pacing line "searching the house for something Kristin now carries" is
  left as is: it can be slightly wrong if she has put the card down, which
  does not break the story.

W8. **Companions. Decided (Brandon, 2026-09-25).** Who travels with Kristin
is plot, so only the story sets it, never a reply: a scene's front matter may
list `companions: [brandon]` from the scene's start, and a fact's `on_assert`
(W7) may add `{accompany: brandon, with: kristin}` partway through (in 1B,
`brandon_identified`). The move rule carries one condition: a companion moves
with Kristin only if he is in the same place as her when she moves. So a
narrated split ("Brandon stays in the truck") lands and he stays behind, and a
narrated rejoin makes him travel with her again, with no flag to set or clear.
Each new scene resets companions and positions from its own declarations.
Rejected: companions reported by the narrator; clearing the companion flag on
a split, which cannot resume after a narrated rejoin.

Scene `participant_ids` cannot stand in for presence: Michelle is listed in
1A-2C while she is missing or captive. So characters get starting places in a
new `character_placements` front-matter field with the same `{parent, text}`
shape as `item_placements`, added scene by scene. The protagonist defaults to
the scene's area.

W9. **Contents of a container. Decided (Brandon, 2026-09-25): each
declared content is an entity.** Brandon's criterion: anything the narration
creates must exist in the world facts and be referenceable. Authored contents
known only from a setting-fact sentence fail it (the player can type "Take the
stapler." and the world has no stapler), and the sentence goes stale. So a
container declares `contents` in one line, the loader expands them into
entities with IDs, the setting fact is removed, and an open container's
visible contents are given with it (sections 6 and 8). New things narrated
inside a container are created under 1c with minted IDs (section 5).

Rejected: a closed list that refuses unlisted things. Its motivating case,
the round 7 USB drive in the drawer, was already removed in round 8 by fix A
(the owner rule no longer names hidden items: 4/4 to 0/4), and the remaining
hidden-card leak is closed by the `hidden` axis. The list would also need
text matching of narrated names against authored ones, which W1 rejected,
and it overrides 1c. Also rejected: contents left as setting text only.

W11. **Seats. Decided (Brandon, 2026-09-25).** When the narration has
Kristin sit down, the reply names the chair, and the world must hold her
there. Following Inform 7, a container or supporter may be `enterable`, and
a character's parent is an area or an enterable container or supporter
(invariant 6). `vehicle` is enterable by kind; a story kind or an item may
declare `enterable: true`. An enterable thing may declare an `enter_pole`:
a character entering it sets that pole, as taking a thing from a closed
container opens it (W3). So the workstation chair is an enterable
supporter with an `overturned|upright` axis declared in `world.yaml` and
`enter_pole: upright`: Kristin can never sit in an overturned chair. A
seat may declare `seat_for` a piece of furniture; when that furniture is
given in THINGS, its seat is given with it, so the narrator has the chair's
name and state when it seats her by its own initiative. A reply that puts
Kristin "at" furniture that is not enterable still lands her in its area:
that reply does not say she sat, and seating her anyway would narrate a
change the prose never showed. Whether the narration shows her righting
the chair before sitting is measured in its own smoke run first; a short
prompt rule follows only if it fails most of the time (the narration fix
ranking).

W12. **Seating before using a thing. Decided (Brandon, 2026-09-26).** Seat
smokes 1 and 2 showed the narrator seating Kristin before it righted the
overturned chair (0 of 6, then 2 of 5 turns in the right order). A prompt
rule asks the narrator to get the order right. Instead, the engine does the
steps itself, before narration, as Inform 7 does with implicit actions
("(first taking the lamp)"). Brandon limited it to the one case that
matters: sitting is needed only to use a computer. No other command seats
her.

- **Data, not branches.** An item may declare `use_seated: true` in
  `world.yaml`; in continuity-initiative, only `kristin_laptop` does. A seat
  declares its two authored lines, `right_text` ("Set the workstation chair
  upright.") and `enter_text` ("Sit in the workstation chair."). The engine
  never builds these sentences itself (W4). Runtime code names no story
  thing.
- **The trigger.** One short yes/no question goes to Jev (`typesafe/jev` on
  Cloudflare, chosen by Brandon as cheap and fast): does this command use
  that thing? "Read the files on my laptop." is yes; "Take my laptop to the
  truck." is no. Jev reads only the player's input and the thing's name,
  never narration.
- **What "use" means (Brandon, 2026-09-26).** Using the laptop means
  working on it: reading, typing, or searching its files. Opening or
  closing it, turning it on or off, moving it, carrying it, picking it up
  and putting it down are not using it. The first question named only the
  moving verbs as "no", so "Open my laptop." (turn 6 of the two-scene
  script) would probably have seated Kristin. Task F rewrites the question
  and checks it live.
- **When the question is asked (task E, 2026-09-26).** Only on a turn where
  the steps could apply: a `use_seated` thing is `together()` with Kristin
  (held by her, or in her area), a seat is `together()` with her, and her
  parent is not already enterable. The world decides this, with no reading
  of the input. The earlier wording, "a turn whose input names the thing",
  would have needed name matching over the player's words, and the bench's
  only reference detection is an 8b match call. "Near" is `together()`,
  not the same area: Kristin starts 1A in the house, and the chair is in
  the kitchen.
- **Bench first, Worker later.** On the bench (task E), a Python client
  calls Jev on the Cloudflare API directly with the local
  `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_AI_TOKEN`, as
  `bench/jev-judge.mjs` already does. The bench runs only on a developer's
  machine and exposes no endpoint. The Worker route below is for the
  runtime turn, in S4.
- **Auth guard (Brandon, 2026-09-26).** No one outside the game may call
  Jev, for their own use or to run up the Cloudflare bill. The question
  goes through the existing narration Worker as a new route, never straight
  from Railway to the Cloudflare API, so the Cloudflare credentials stay in
  the Worker only. The Worker sends a fixed yes/no question and takes only
  the player's input and the thing's name; it never forwards a
  caller-supplied prompt or model. The Worker's shared bearer token
  becomes required: today `.plans/cloudflare.js` checks it only when
  `DEMO_SHARED_TOKEN` is set, so the Worker fails open. With no token set,
  both routes must refuse every request. This covers the narration route
  too. Rate limits and the $5 daily model budget, which the Jev route
  shares, are in [rate-limits.md](rate-limits.md).
- **The two checks, on a yes.** The seat to use is the first seat, by ID,
  that is `together()` with Kristin. On a no, or with no answer, nothing is
  added, and no answer is recorded as an issue. Otherwise:
  1. if the seat is not at its `enter_pole` (the chair is overturned), set
     that pole and add the seat's `right_text`;
  2. if Kristin's parent is not the seat, move her into it and add the
     seat's `enter_text`.
  An upright chair gets only step 2; a seated Kristin gets neither.
- **The narrator is told.** The added lines go before the player's command
  as separate sentences, in the same way the command splitter
  (`storygame/runtime/command_split.py`) hands the narrator a compound
  command. The world changes are committed before narration, so no fact
  changes after rendering. The narrator narrates the steps as material,
  not as a rule to obey.
- **What it does not cover.** The narrator seating her on its own
  initiative, when the command never asked, is left to `enter_pole` for
  state. The two-line upright rule (c7705b8) is a candidate for removal once
  W12 lands; remove it only if a seat smoke shows the order still holds
  without it (principle 5).

Rejected: seating her before any command that names the workstation
("Search under the workstation." does not need a seat); a list of "use"
verbs (a fixed action table, forbidden by AGENTS.md); asking before any
command that names the laptop with no judgement ("Take my laptop to the
truck." would seat her first).

W13. **Standing up before leaving a seat. Decided (Brandon, 2026-09-26).**
The counterpart of W12. The engine tracks whether a character is seated or
standing, and a seated character can move only once she stands. The seat
smokes found the gap: the narration showed Kristin standing up, the reply
left the change out, and the world kept her in the chair.

- **Posture is the tree.** Kristin is seated when her parent is a seat, a
  thing with `seat_for`. Otherwise she is standing. A vehicle is not a seat:
  sitting in the truck is not covered.
- **Data, not branches.** A seat declares a third authored line,
  `leave_text` ("Stand up from the workstation chair."), next to
  `right_text` and `enter_text`. A seat without it fails to load.
- **The trigger.** Only while Kristin is seated, one Jev question: does
  she need to get up to carry out this command? The state holds the
  command, the seat's name, and the names of the things within reach of the
  seat. Within reach means the seat, the furniture it is `seat_for`,
  everything inside or on that furniture, and everything Kristin holds. It
  is yes when the command sends her somewhere else, or acts on a thing that
  is not within reach. While she is standing, the question is not asked.
- **The step, on a yes.** The engine moves her from the seat to the seat's
  area and adds the seat's `leave_text` before the command, as W12 does. On
  a no, or with no answer, nothing is added, and no answer is recorded as
  an issue. A turn that stands her up does not also ask the W12 question.
- **A reply that moves a seated Kristin elsewhere** without the step is
  accepted as standing up and then moving. Refusing it would drop a
  narrated change, which is a severe failure. The step before the turn
  should make this rare.

**Seats are furniture, but the chair can move (Brandon, 2026-09-26).** The
`seat` kind becomes `[furniture, supporter]`. Furniture is fixed by default,
so a kind may now declare `fixed`, and `seat` declares `fixed: false`. A
chair is light enough to carry to another room, and `fixed` would refuse
every move of it. The desk kind stays fixed. A reply that records the
chair's place as Kristin is a capture error, and W5's held-by question
measures it.

W10. **A self-contained library. Decided (Brandon, 2026-09-25).** The model is
a separate, reusable library named `worldkeeper`, designed to be publishable
to PyPI later: a uv workspace member, standard library only, no `storygame`
imports, state kept in the host's store through a backend interface (section
4.8). Names considered: `kindtree`, `worldkeeper`, `fictree`, `worldstate`;
Brandon chose `worldkeeper`.
