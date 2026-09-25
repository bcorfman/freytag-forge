# World model: plan

Status (2026-09-25): decisions W1-W10 settled; S1 done, exit gaps closed. See "Resume here";
next: the S1 PR, then S2 (section 11). Written at Brandon's request
after decision 1e (containment) in
[narrated-world-continuity.md](narrated-world-continuity.md) kept turning into
separate small decisions. This plan replaces decision 1e. It also gives
decision 1a's state axes, the `fixed` refusal and the protagonist's place a
home in one model. The capture loop, cause routing and rollout stay in the
continuity plan; this plan defines the world they write into.

## Resume here (2026-09-25)

Branch `world-model-s1` holds all of S1 on top of main after PR 479:

- task 2: bd8c46b and 529b6a0;
- task 3: 515201e and cf31bd2;
- task 4: 89b1eea and 54541e9;
- the exit gaps: 2c546cb and the round 2 commit after it;
- d498b9d: ruff formatting of the `.plans/` scripts.

The full suite is green (747 tests, 92.84% coverage), and ruff is clean across
the whole repository. The shipped narrator's 1A payloads are still
byte-identical to the pre-S1 baseline. The branch has not been pushed and has
no PR. **Next:** open the S1 PR, then start S2.

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

Open question for S2, not yet raised with Brandon: `World.area()` returns
the nearest area. So once the kitchen is nested in the house, a phone in the
kitchen and Kristin in the house are not `together()`. Decide whether
`together` should compare the top-level area.

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

W10. **A self-contained library. Decided (Brandon, 2026-09-25).** The model is
a separate, reusable library named `worldkeeper`, designed to be publishable
to PyPI later: a uv workspace member, standard library only, no `storygame`
imports, state kept in the host's store through a backend interface (section
4.8). Names considered: `kindtree`, `worldkeeper`, `fictree`, `worldstate`;
Brandon chose `worldkeeper`.
