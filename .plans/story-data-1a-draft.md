# Scene 1A in the proposed authoring format (hand-written draft, no compiler)

Status (2026-11-12): **revision 2, after Brandon tried revision 1.** His copy
with his edits and hesitations is kept as
[story-data-1a-draft-edited.md](story-data-1a-draft-edited.md). What changed, and
why:

- Edit 1: one reworded sentence used to mean editing three fields and then the
  sibling variant's copy. Now the shared opening is one `parts` entry, so it is
  two places (`says` and the part).
- Edit 2: the old task read as a data edit but was a story decision. Rewritten
  as a decision with a stated choice, and corrected: the draft's description of
  when a beat fires was wrong (see the `beats` table).
- Edit 3: the schema never said how a command is checked against the word
  groups. Now it says (verified by running the real matcher), and each search
  carries `examples` with commands and whether they match.
- Edit 4: the 1B reader was missing from the file. A 1B excerpt is now in it.
  `hands_to_1B` was removed; it did nothing you could see.
- A stray block from the task sheet had also been pasted into the YAML in the
  edited copy. That is not a format problem, but the task sheet now says which
  parts are not file content.

Nothing here is read by any code. It exists so Brandon can try the four edits and
then decide D1 in [the redesign plan](story-data-redesign-plan.md). Facts,
wording and numbers are copied from the nine story files at `8670fd89`; where I
changed nothing about behavior I say so. Where the format forced a choice, it is
marked **CHOICE**.

Not in this draft (to keep it editable): the other 1A storylets (A, C, F, G, H,
I, J, K), the neighbor, the broadcast test, and the entry-claim list. The
slice covers one reveal with quiet and witnessed variants, the card-reading
claim, the patrol chain with the officer pressure, and the exit into 1B.

## How to read the format

- One file owns the scene. Everything that changes together sits together:
  situation, setup, beats in turn order, reveals, exit.
- **Prose is beside behavior.** A passage sits in the block that causes it.
- **Facts are declared once**, in the scene that owns them, with their purpose
  and any world effect (`on_assert`). Legacy: three places (`knowledge.yaml`
  facts, `storylet-routes.yaml` `new_fact_ids`, `world.yaml` fact list).
- **Claim effects default to the variant's `commits`.** A claim states
  `commits_subset:` only when it grants less. Legacy: each claim restates the
  storylet effects (87 of 99 identical).
- `used_by` and `producers` are never written. The last section shows what the
  compiler would generate, so you can follow a consequence forward and back.
- IDs in `[brackets]` are the legacy IDs, kept so saves and tests still match.

---

## Schema: which field goes where

The sample below is one instance of this. Everything an author can write is
listed here. **R** = required, **O** = optional (default shown). The last column
says where the field lands in today's `StoryPackage` (`models.py`), so the
compiler's job is checkable. A field with "new" there has no legacy field and is
this draft's invention; those are the ones to push back on.

The top level of a scene file has exactly these keys, in this order of
preference: `scene`, header fields, `facts`, `placements`, `beats`, `searches`,
`reveals`, `bridge`, `exit`. Any other key is a shape error (the legacy models
also reject unknown keys: `extra="forbid"`).

### Value shapes used everywhere

| Shape | Written as | Meaning | Legacy |
| --- | --- | --- | --- |
| id | `snake_case_word` | Stable ID, never derived from prose | same ID patterns |
| condition | `{fact: true, other_fact: false}` | All listed facts have those values. A list of bare names `[a, b]` means each is true | `FactPredicate(fact_id, equals)` list |
| effects | `{fact: true}` | Assert each fact with that value | `RouteOperation(op: assert)` list |
| passage | a string, or a list of `{when, text}` | Text the player sees. In a list, the first entry whose `when` holds is used; the last entry must have no `when` (the loader already enforces that last rule, `loader.py:918`; "first wins" is how I read it, not something I verified in the runtime) | `PacingRealization` list |
| matcher words | `[[a, b], [c, d]]` | A list of word groups. The command matches when **every group has at least one of its words or phrases in it**. See "How a command is checked" below | `action_evidence`, `must_convey` |

#### How a command is checked (`action_evidence`)

Read from `storygame/runtime/candidate_matcher.py:220-257` and confirmed by
running the real matcher on the commands in the `examples` lists below.

1. The command is lower-cased and split into whole words. A word group entry
   matches only as whole words (the entry `gap` does not match `gaping`). A
   single word of more than three letters also matches its plural or singular.
2. **Every group must be satisfied by at least one of its entries.** More groups
   means a stricter match. Think of each group as one slot of the sentence:
   (what the player does) + (where) + (what).
3. **Listing one word also admits its whole synonym class.** The engine keeps
   fixed classes (`candidate_matcher.py:48-91`). The ones that matter here:
   - look closely: search, look, check, inspect, examine, feel, rummage, go
     through, ...
   - take: take, grab, pick up, retrieve, remove, **pull**, peel off, collect
   - position: under, beneath, underneath, underside, below, bottom of, lift,
     peel, flip over, ...
   - open: open, pry open, unlatch

   So `[look, search]` already accepts `examine` and `feel`, and listing `pull`
   would also admit `take`, `grab` and `remove`. A verb in no class (`slide`,
   `run`) is accepted only if you list it.
4. A command that negates the action ("don't search under the drawer") does not
   match.
5. Words in the command that no group mentions are ignored. That is why
   "pull the drawer out and check underneath it" already matches: it contains
   `check`, a position word (`underneath`, from the position class) and
   `drawer`.

So to make a new command count, find the group it fails and add a word to that
group. Do not add a new group: that makes the match stricter, not looser. After
you change a list, check the `examples` under it still come out as written.

Retracting a fact has no shorthand yet. Not needed in this slice; legacy uses
`{op: retract, fact_id, value}` (see `handoffs.yaml:45`).

### Scene header (top level)

| Field | R/O | Type | Meaning | Lands in |
| --- | --- | --- | --- | --- |
| `scene` | R | scene id (`1A`) | Stable ID | `SceneMetadata.scene_id`, `SceneFrame.scene_id`, every record below |
| `title` | O | text | For readers only; nothing depends on it | none (plot.md heading) |
| `location` | R | id | Where the scene is set | `location_id` |
| `objective` | R | text | What the player is trying to do | `objective` |
| `freytag_phase` | R | one of exposition, inciting_incident, rising_action, crisis, climax, falling_action, resolution | Story position | `freytag_phase` |
| `situation` | O (empty) | text | What the narrator may state as the scene's starting state | `SceneFrame.situation` |
| `pressure` | R | text | What pushes the player this scene | `SceneFrame.pressure` |
| `entry` | R | text | First text shown on entering | `entry_text` |
| `entry_variants` | O | list of `{when, text}` | Replacement entry text under conditions | `entry_variants` (`requires` = the facts in `when`) |
| `setting` | O | list of text | Ambient lines | `setting_facts` |
| `scripted_opening` | O (false) | bool | Opening is fixed text | `scripted_opening` |
| `companions` | O | list of ids | Characters travelling with the player | `companions` |
| `participants`, `items` | O | list of ids | Cast and props named for the scene. Legacy lists these by hand (`participant_ids`, `item_ids`). Left out of the sample; the compiler could derive them from placements and usage, but I have not checked that it gives the same lists | `participant_ids`, `item_ids` |

### `facts`: a map from fact id to its declaration

| Field | R/O | Type | Meaning | Lands in |
| --- | --- | --- | --- | --- |
| `purpose` | R | text | One sentence: what being true means. The only description of the fact anywhere | `FactDefinition.purpose` |
| `on_assert` | O | list of world effects | What changes in the world when the fact becomes true. A world effect has `move` + `parent` (+ optional `text`, `under`), or `reveal`, or `accompany` + `with`, or `set_axis` + `value` | `WorldSource.fact_effects[fact]` |

A fact is declared in exactly one scene file. Other scenes use it by id. The
fact list the world file keeps today (`world.yaml`) and the `new_fact_ids`
list are generated from this, not written.

### `placements`: where things start in this scene

A map from an entity id to either a text string or:

| Field | R/O | Type | Meaning | Lands in |
| --- | --- | --- | --- | --- |
| `parent` | R | id | Container the entity starts in | `parent` |
| `text` | O | text | How the narrator describes the position | `text` |
| `under` | O (false) | bool | Hidden beneath the parent | `under` |
| `part_of` | O (false) | bool | A fixed part of the parent | `part_of` |
| `while_fact_true` / `while_fact_false` | O | fact id | Placement applies only while the fact has that value | same names |

The compiler looks up whether an id is a character or an item to choose
`character_placements` or `item_placements`.

### `beats`: timed events (pacing), in turn order

| Field | R/O | Type | Meaning | Lands in |
| --- | --- | --- | --- | --- |
| `id` | R | id | Stable ID | `PacingEvent.id` |
| `at_turn` | R | int | The earliest turn the event may fire, counted from entering the scene. It fires **once**, the first time `when` holds at or after that turn (`engine.py:1349`). It does not wait for exactly that turn. Revision 1 said "the turn the event is due", which hid this | `at_turn` |
| `when` | O | condition | Extra guard besides the turn | `when` |
| `sets` | R | effects | Facts the event asserts (at least one) | `effects` |
| `trailing` | O (false) | bool | Apply after the player's action is narrated | `trailing` |
| `verbatim` | O (false) | bool | Show the text exactly as written. Applies to every `say` entry | `PacingRealization.verbatim` |
| `say` | O | passage | What the player sees | `realizations` |
| `exit` | O | exit id | The event completes this exit | `transition_id` |

### `searches`: reusable "the player did this" wording

A named block of matcher fields. A reveal or variant names it with `uses:`.
A field written on the variant itself replaces the block's field (this override
rule is new; legacy has no sharing).

| Field | R/O | Type | Meaning | Lands in |
| --- | --- | --- | --- | --- |
| `earn_when` | O | text | Plain-language description of the qualifying action. **It is read by the model, not by the word matcher**: it goes into the narrator prompt ("Earn it when the player ...", `cloudflare.py:1717`) and is used to pick prompt examples. Changing it never changes which exact commands match | `earn_when` |
| `action_evidence` | O | matcher words | The exact-match path: words in the player's command, checked as in "How a command is checked". **This is the field to change to make a new command count.** Keep it saying the same thing as `earn_when` | `action_evidence` |
| `examples` | O | list of `{command, matches}` | Commands with the expected result. The checker runs the real matcher on each and fails if it disagrees. They are the answer to "what does this list actually accept". New; there is no legacy field, and it is not copied into `StoryPackage` | none (a check) |
| `reach` | O | list of ids | Things the player must be able to reach | `reach_entity_ids` |
| `entities` | O | list of ids | Things the claim is about | `entity_ids` |
| `leak_terms` | O | list of text | Words the narrator must not use before this is earned | `leak_terms` |
| `must_convey` | O | matcher words | What the delivered text must say | `must_convey` |

### `reveals`: something the player earns

One reveal is one legacy storylet, with its claims.

| Field | R/O | Type | Meaning | Lands in |
| --- | --- | --- | --- | --- |
| `id` | R | id | Stable ID. The legacy storylet id (`SL-1A-E`) goes in a comment or `legacy_id` | `StoryletRoute.id` |
| `title` | R | text | Name for readers | `title` |
| `guidance.pressure_role` | R | text | Why this reveal exists in the scene | `pressure_role` |
| `guidance.window` | R | `{earliest_turn, target_turn, latest_turn}` | When it may be offered | `earliest_turn`, `target_turn`, `latest_turn` |
| `guidance.available_while` | O | condition | Facts needed for it to be offered | `activation_conditions` |
| `guidance.done_when` / `done_when_any` | O | condition / list of facts | Finished once these hold | storylet completion |
| `guidance.boundaries` | O | list of ids | Protected knowledge it must not touch | each realization's `protected_knowledge_boundaries` |
| `uses` | O | search name | Default matcher wording for all variants | matcher fields on each claim |
| `parts` | O | map of name to text | Passage pieces shared by several variants. A variant's `text` includes one by writing `{name}`. The compiler pastes it in, so each claim's `delivery_text` is the same string as today. New: legacy repeats the sentences in each claim. **CHOICE**: this is how "reword once" works across variants; the cost is that a variant's `text` is no longer fully readable in place | none (expanded into `delivery_text`) |
| `audience` | R | `public`, or `{kind: characters, character_ids: [...], player_visible: ...}`, or `{kind: world_only}` | Who may know it. `public` is shorthand for kind public, player visible | `Audience` |
| `variants` | R | map of variant key to variant | See below | realizations and claims |

Variant fields:

| Field | R/O | Type | Meaning | Lands in |
| --- | --- | --- | --- | --- |
| `when` | O | condition | Facts that must hold for this variant. This is how two variants of one reveal are told apart | claim `requires` |
| `intent` | R | text | What the realization is trying to do dramatically. Write the purpose, not the wording: if you reword a passage, `intent` should not need to change | `dramatic_intent` |
| `commits` | R | effects | Facts asserted when the player earns it. Used for both the storylet operation and the claim's effect | `operations` and claim `establishes` |
| `commits_subset` | O | effects | Use only when the claim grants less than `commits` (12 of 99 today) | claim `establishes` |
| `says` | R | text | One sentence: what the player now knows | `KnowledgeDefinition.statement` |
| `text` | R | text | The delivered passage. May contain `{part}` references to the reveal's `parts` | `delivery_text` |
| `aliases` | R | list of text | Names the knowledge can be asked about. Legacy requires at least one; the sample left them out | `aliases` |
| `helps_exit` | O | list of exit ids | Exits this variant helps trigger. Not derivable: `SL-1A-C-R2` sets a trigger fact of `t_1a_1b` and lists none | `helps_transition_triggers` |
| `voiceable` | O (true) | bool | Whether characters may say it aloud | `voiceable` |
| `repeatable` | O (false) | bool | May be earned again | `repeatable` |
| `claim_id` | O | id | Keeps today's claim ID (`k_sl_1a_b_r0`). If absent the compiler makes one from reveal id and variant key | `KnowledgeDefinition.id` |
| matcher fields | O | as in `searches` | Override the `uses` block | same |
| `relevance`, `delivery_variants`, `speaker_text`, `action_contract` | O | as legacy | Passed through unchanged | same names |
| `source_beats`, `eligible_storylet_event_id` | O | as legacy | Passed through unchanged | same names |

### `bridge`: fallback events that keep the scene moving

| Field | R/O | Type | Meaning | Lands in |
| --- | --- | --- | --- | --- |
| `id` | R | id | Stable ID | `CanonicalRouteEvent.id` |
| `when` | R | condition (or `when_any` + `at_least`) | When it fires | `activation` |
| `commits` | R | effects | What it asserts | `operations` |
| `realized_by` | O | list of reveal ids | Reveals that normally deliver this | `realization_storylets` |
| `fallback_text` | O | text | Text if no reveal delivered it | `fallback_text` |
| `note` | O | text | For readers only | none |

### `exit`: leaving the scene

| Field | R/O | Type | Meaning | Lands in |
| --- | --- | --- | --- | --- |
| `id` | R | id | Stable ID | `Transition.id` |
| `to` | R | scene id | Target scene | `target_scene_id` |
| `priority` | R | int | Which exit wins when several are ready | `priority` |
| `when_all` | R | list of facts (each must be true) | Triggers | `triggers` |
| `needs` | O | list of item ids; or `{item, relation}` | Items that must be in a given relation. Legacy has ids only and means "exists"; `relation` (exists, held, known) is new and is what makes the Reyes finding visible | `required_dependencies` (relation is not stored today) |
| `bridge` | R | text | Text shown on leaving | `SceneMetadata.bridge_text[id]` |

There is no field for "the next scene reads these facts". Revision 1 had one
(`hands_to_<scene>`); it was removed because it did nothing you could see and the
compiler computes the list. Readers in other scenes appear in the generated block
at the end of this file.

### How to write something new

- **A new fact:** add one entry under `facts` with a `purpose`. Nothing else.
  If the world changes when it becomes true, add `on_assert`.
- **A new timed event:** add a `beats` entry with `id`, `at_turn`, `sets`, `say`.
  Add `when` if it needs a guard. End a conditional `say` list with an entry that
  has no `when`.
- **A new thing the player can earn:** add a `reveals` entry with `title`,
  `guidance`, `audience` and at least one variant (`intent`, `commits`, `says`,
  `text`, `aliases`). Give the variant its matcher wording, or name a `searches`
  block with `uses`.
- **A second version of an existing reveal:** add a variant to it, with a
  `when` that tells the versions apart.
- **A new exit:** add an `exit` entry; every fact in `when_all` must be set
  by something in this or an earlier scene (the compiler checks).

### Not covered by this draft

Scene-entry claims (`k_scene_1a_entry`), the fact delivery for
`continuity_initiative_known` in `handoffs.yaml`, incidents and their outcomes
(1A has none; 2C does), connections between places, the world file's entities
(locations, characters, items), disclosure guards, the ending, and the prose
that `plot.md` and `storylets.md` hold. They keep their legacy files in the
migration until a draft covers them.

---

## The file: `scenes/1A.yaml` (proposed)

```yaml
scene: 1A                          # stable ID. The file name and title are not the ID.
title: Michelle's Disappearance
location: mcgehee_home
objective: Find evidence of Michelle's disappearance
freytag_phase: exposition

situation: >-
  Michelle's home is otherwise untouched, but the back door has been forced.
  The deadbolt is still thrown. Michelle is missing, and her tablet and work
  bag are gone. Kristin knows Michelle would not leave her kitchen like this.
  A drawer on Michelle's workstation has Kristin's initials, KMS, newly carved
  into it. Kristin did not carve them.
pressure: Find evidence of Michelle's disappearance

entry: |
  Michelle's text came in a little after 4:00am, lost among the emergency
  alerts while Kristin finished a late-night shift. She missed it by minutes.
  When she read it, her stomach dropped. Every call back failed. Kristin ran
  for her truck and drove as hard as the streets allowed, past sirens,
  ambulances, police cars, and intersections blocked for no reason anyone would
  explain. Was she hurt? Taken? Gone? Not knowing was the worst of it. She
  found the back door forced and let herself into the kitchen.

  The kitchen was wrong at a glance. Michelle's chair lay tipped over at her
  workstation across the room, and her tablet and work bag were nowhere in
  sight. A mug sat on the workstation beside a stack of manuscript pages. The
  calendar and the lake photograph hung by the refrigerator, where they always
  had. Kristin was too frantic to read any of it yet. She called Michelle's
  name.

setting:
  - Sirens carry from the next street.
  - A dog barks behind the empty house next door.
  - The rest of the house is quiet. Michelle is not in it.

# ---------------------------------------------------------------- facts
# Declared once. Purpose is the only description. Effects on the world model
# live here too, so "what happens when this becomes true" is in one place.
facts:
  memory_card_recovered:
    purpose: Kristin has recovered Michelle's memory card.
    on_assert:
      - {move: memory_card, parent: kristin, text: with Kristin}
      - {reveal: memory_card}
  card_challenged:
    purpose: A patrol officer saw Kristin take Michelle's memory card and challenged her.
  officer_demanded_card:
    purpose: The officer has demanded the card from Kristin.
  kristin_marked_by_patrol:
    purpose: The patrol has Kristin marked as someone to watch.
  patrol_on_scene:
    purpose: A federal emergency patrol has arrived at Michelle's house.
  patrol_in_house:
    purpose: A patrol officer is inside Michelle's house.
    on_assert:
      - {move: patrol_officer, parent: kitchen, text: at Michelle's workstation}
  patrol_departed:
    purpose: The federal emergency patrol has left Michelle's house.
    on_assert:
      - {move: patrol_officer, parent: patrol_staging}
  patrol_return_pressure:
    purpose: Observable signs indicate the federal patrol is likely to return or intensify scrutiny at Michelle's house.
  drawer_gap_pointed_out:
    purpose: Kristin has been pointed toward the thin gap beneath Michelle's workstation drawer.
  michelle_lead_actionable:
    purpose: Kristin has a concrete, credible lead from Michelle's research that can be followed away from the house.
  # Facts this scene only uses, not owns (owned elsewhere, referenced by ID):
  #   michelle_abduction_suspicion, continuity_initiative_known, michelle_warning_known

# ---------------------------------------------------------------- setup
placements:
  kristin: {parent: kitchen}
  walt_pruitt: {parent: outside_house, text: "the elderly neighbor from next door, at the fence between the yards"}
  memory_card: {parent: michelle_drawer, under: true}
  michelle_drawer: {parent: michelle_workstation, part_of: true, text: in Michelle's workstation}
  michelle_phone: {parent: kitchen, text: on the kitchen floor}
  kristin_laptop: {parent: truck_passenger_seat, text: on the passenger seat of Kristin's truck}
  # ... the other 14 placements are unchanged, omitted here.

# ---------------------------------------------------------------- beats
# Pacing events in turn order. "trailing" applies the event after the player's
# action is narrated. Text marked verbatim is delivered as written.
beats:

  - id: kristin_steadies_1a
    at_turn: 3
    trailing: true
    when: {michelle_abduction_suspicion: false}
    sets: {michelle_abduction_suspicion: true}
    verbatim: true
    say: >-
      Kristin makes herself stop and look properly. Michelle's phone is still
      here - damaged a bit but still working. Then she sees the back door. The
      splinters around the frame point outward, away from the house. A door
      forced from outside would splinter inward. Someone broke this one from
      inside to make it look like a break-in. It looks staged.

  - id: patrol_arrives_1a
    at_turn: 6
    trailing: true
    sets: {patrol_on_scene: true}
    verbatim: true
    say: >-
      A federal emergency patrol pulls up outside Michelle's house. Two
      officers get out. One walks to the front door. The other looks over the
      street.

  - id: patrol_enters_1a
    at_turn: 7
    trailing: true
    when: {patrol_on_scene: true}
    sets: {patrol_in_house: true}
    verbatim: true
    say: >-
      The front door opens. An officer walks in and heads straight for
      Michelle's workstation.

  # --- officer pressure ------------------------------------------------
  - id: officer_presses_1a
    at_turn: 7
    when: {card_challenged: true, patrol_in_house: true}
    sets: {officer_demanded_card: true}
    verbatim: true
    say: |
      The officer plants himself between her and the front door and holds out a gloved hand. "Whatever you just took from that desk. Let's see it, ma'am. Right now."

  - id: reyes_rams_drawer_1a
    at_turn: 8
    trailing: true
    when: {patrol_in_house: true, drawer_gap_pointed_out: false, memory_card_recovered: false}
    sets: {drawer_gap_pointed_out: true}
    verbatim: true
    say: >-
      Reyes tugs at the workstation drawer. It sticks. Frustrated, he rams it
      back into place with the heel of his hand, and it sits high in its frame.
      A thin gap shows beneath its lower edge, wide enough for Kristin's
      fingers. Reyes never looks down. Only Kristin sees it.

  - id: patrol_leaves_1a
    at_turn: 10
    trailing: true
    when: {patrol_on_scene: true}
    sets: {patrol_departed: true, patrol_on_scene: false, patrol_in_house: false}
    verbatim: true
    say:
      - when: {officer_demanded_card: true}
        text: >-
          The officer's radio crackles with a description that is hers. He backs
          out through the front door, eyes on her the whole way, and the patrol
          pulls away from the curb.
      - text: The patrol pulls away from the curb.

  - id: patrol_returns_1a
    at_turn: 13
    sets: {patrol_return_pressure: true}
    say:
      - when: {patrol_departed: true}
        text: The patrol is coming back to the house.
      - text: A federal emergency patrol turns onto Michelle's street.
    verbatim: true

# ---------------------------------------------------------------- reveals
# A reveal is something the player earns by playing. Variants differ in what
# the world looks like when it happens. Each variant is one claim.

searches:                          # shared wording that decides "the player did this"
  drawer_search:
    earn_when: searches the drawer, the gap in the drawer, or the space beneath it
    action_evidence:
      - [look, search, inspect, check]
      - [under, beneath, underside, gap, lower edge, bottom edge]
      - [drawer, KMS, workstation, "drawer's"]
    examples:                      # run through the real matcher on 2026-11-12; the checker would re-run them
      - {command: Search under the KMS drawer, matches: true}
      - {command: Check the gap in the drawer, matches: true}
      - {command: Feel under the drawer, matches: true}          # "feel" is in the look-closely class
      - {command: Check underneath the drawer, matches: true}    # "underneath" is in the position class
      - {command: Search the drawer, matches: false}             # no position word. earn_when says "searches the drawer"; the matcher does not accept it
      - {command: Pull the drawer out, matches: false}
      - {command: Open the drawer, matches: false}
      - {command: Don't search under the drawer, matches: false}  # negated
    reach: [michelle_drawer]
    entities: [kristin, michelle, memory_card, michelle_drawer]
    leak_terms:
      - memory card
      - hidden memory card
      - hidden card
      - "Michelle's card"
      - the card
      - taped beneath the drawer
      - taped under the drawer
      - taped to the drawer
      - memory card recovered
    must_convey:
      - [memory card, card, "Michelle's card", the card, hidden card, hidden memory card]
      - [taped]
      - [beneath the KMS drawer, under the KMS drawer, beneath the drawer]
      - [Michelle, "Michelle's", Dr. McGehee, Michelle McGehee, Shelly]

  card_read_files:                 # revision 2: read_files now uses a search block like find_card, so both reveals look the same
    earn_when: reads the files on Michelle's recovered memory card
    action_evidence:
      - [read, inspect, open, check, review, plug, insert, connect]
      - [memory card, card]
      - [file, files, saved file, saved files, card file, card files, laptop]
    examples:
      - {command: Read the files on the memory card, matches: true}
      - {command: Plug the memory card into my laptop, matches: true}
      - {command: Open the files on the card, matches: true}
      - {command: Read the memory card, matches: false}           # no file word
      - {command: Play the recording on the memory card, matches: false}
    reach: [memory_card, kristin_laptop]
    entities: [kristin, michelle, memory_card, kristin_laptop, park_bench]
    must_convey:
      - [memory card, card]
      - [Michelle, "Michelle's", Dr. McGehee, Michelle McGehee, Shelly]
      - [damaged recording, voice recording, recording]
      - [emergency broadcasts, broadcast]
      - [dead drop, exchange point]
      - [bench in the park, park bench]

reveals:

  - id: find_card                  # [SL-1A-E]
    title: The KMS Mark
    guidance:
      pressure_role: Let the KMS mark reward a careful search of Michelle's workstation before the patrol closes in.
      window: {earliest_turn: 1, target_turn: 3, latest_turn: 12}
      boundaries: [janus_selection_system, brandon_history, janus_phase_two]
      available_while: {memory_card_recovered: false}
      done_when: {memory_card_recovered: true}
    uses: drawer_search
    audience: public               # player-visible

    parts:                         # new: wording both variants share. Legacy repeats it in each claim.
      find_lead: >-
        Kristin's fingers find something taped beneath the drawer. She peels
        it loose. It is Michelle's memory card, and she pockets it.

    variants:
      quiet:                       # [claim k_sl_1a_b_r0, realization SL-1A-E-R1]
        claim_id: k_sl_1a_b_r0
        when: {patrol_in_house: false}
        aliases: [memory card recovered]
        helps_exit: [t_1a_1b]
        intent: Kristin searches beneath the KMS drawer, finds Michelle's hidden memory card, and keeps it with her.
        commits: {memory_card_recovered: true}
        says: Kristin finds Michelle's memory card taped beneath the drawer and pockets it.
        voiceable: false
        text: "{find_lead} Her laptop is still out in her truck."

      witnessed:                   # [claim k_sl_1a_b_r0w, realization SL-1A-E-R2]
        claim_id: k_sl_1a_b_r0w
        when: {patrol_in_house: true}
        aliases: [memory card recovered in sight of the patrol]
        helps_exit: [t_1a_1b]
        intent: Kristin finds the hidden card while a patrol officer is in the house, and the officer challenges her.
        commits: {memory_card_recovered: true, card_challenged: true, kristin_marked_by_patrol: true}
        says: An officer saw Kristin take Michelle's memory card and asked what it is.
        text: >-
          {find_lead} The officer turns at the sound. "What have you got
          there?" His hand is already out.

  - id: read_card                  # [SL-1A-B]
    title: Michelle Hid Something for Kristin
    guidance:
      pressure_role: Once Kristin has the card, let its files or recording reveal Michelle's lead without requiring one fixed command.
      window: {earliest_turn: 2, target_turn: 5, latest_turn: 6}
      boundaries: [janus_selection_system, brandon_history, janus_phase_two]
      available_while: {memory_card_recovered: true, continuity_initiative_known: false}
      done_when_any: [continuity_initiative_known, michelle_warning_known]
    audience: public

    variants:
      read_files:                  # [claim k_sl_1a_b_r1, realization SL-1A-B-R1]
        claim_id: k_sl_1a_b_r1
        when: {memory_card_recovered: true}
        aliases: [continuity initiative known, michelle warning known, michelle abduction suspicion, michelle lead actionable]
        helps_exit: [t_1a_1b]
        intent: Kristin reads the recovered card's files and damaged recording. They point to a dead drop at a bench in the park.
        commits:
          michelle_warning_known: true
          continuity_initiative_known: true
          michelle_abduction_suspicion: true
          michelle_lead_actionable: true
        says: >-
          Kristin reads Michelle's memory card. Its damaged recording warns her
          not to trust emergency broadcasts, and the Continuity Initiative
          files point to a dead drop at a bench in the park.
        uses: card_read_files      # this reveal has no default search; each variant names one
        text: >-
          The card holds Michelle's saved files and a damaged recording. The
          recording warns, "Do not trust the emergency broadcasts." The files
          name the Continuity Initiative and point to a dead drop at a bench in
          the park.

      play_recording:              # [claim k_sl_1a_b_r2, realization SL-1A-B-R2]
        claim_id: k_sl_1a_b_r2
        when: {memory_card_recovered: true}
        aliases: [michelle warning known, michelle abduction suspicion]
        helps_exit: []
        intent: Kristin plays the recovered card's damaged warning before reading the remaining files.
        commits: {michelle_warning_known: true, michelle_abduction_suspicion: true}
        says: Kristin plays the damaged recording on Michelle's memory card. It warns her not to trust emergency broadcasts.
        earn_when: plays Michelle's damaged recording
        text: >-
          The card holds a damaged recording. Michelle's voice warns, "Do not
          trust the emergency broadcasts."
        # (action_evidence and must_convey omitted here for length)

# Fallback event (legacy canonical bridge): if the Initiative is known by any
# route, make the lead actionable.
bridge:
  - id: bridge_1a_actionable_lead
    when: {continuity_initiative_known: true}
    commits: {michelle_lead_actionable: true}
    realized_by: [read_card]       # legacy also lists SL-1A-D, not drafted here
    note: The warning alone is not sufficient. Only the files give the park/dead-drop lead.

# ---------------------------------------------------------------- exit
exit:
  - id: t_1a_1b                    # [t_1a_1b]
    to: 1B
    priority: 10
    when_all:
      - michelle_lead_actionable
      - patrol_return_pressure
      - memory_card_recovered
    needs:                         # CHOICE: the relation is named. Legacy "required_dependencies" meant exists, not held.
      - {item: memory_card, relation: exists}
    bridge: >-
      Kristin starts the truck and heads for the park, avoiding checkpoints and
      emergency patrols.
```

### Excerpt: `scenes/1B.yaml` (so the reader of the 1A fact is in front of you)

Only the one beat. Copied from `pacing.yaml:106-117` at `8670fd89`. Nothing else
from 1B is drafted.

```yaml
scene: 1B
beats:
  - id: pursuit_1b
    at_turn: 4
    sets: {pursuit_closing_in: true}
    say:
      - when: {kristin_marked_by_patrol: true}      # fact owned by 1A, used here by id
        text: The pursuers already have a description of Kristin. They are closing in through the park.
      - text: The pursuers are closing in through the park. The pursuit is not over.
```

---

## What the compiler would generate (never edited)

Shown so you can follow a change forward and backward. This is the "forward
and backward dependency navigation" requirement; the author does not write it.

**How this block was made:** by hand, from `grep` over the nine legacy files and
`tests/` on 2026-11-12, not by a tool. Each "read by" line was checked against
the legacy file it comes from (`pacing.yaml:48,86,114`, `storylet-routes.yaml`,
`knowledge.yaml`). A real compiler would produce it, and the Phase 2 parity gate
would compare it with the legacy graph. Until then, treat it as my claim and
check a line against the file when it matters.

```text
kristin_marked_by_patrol
  set by:   reveals.find_card.witnessed (1A)
  read by:  1B beat pursuit_1b  (picks "already have a description of Kristin")
  tests:    5 test files mention the id today (textual match only, not a check of behavior)

card_challenged
  set by:   reveals.find_card.witnessed
  read by:  1A beat officer_presses_1a (when)
  note:     was listed with used_by_storylets: [SL-1A-E] and
            used_by_transitions: [] in three places before; now one

memory_card_recovered
  set by:   reveals.find_card.quiet, reveals.find_card.witnessed
  read by:  read_card.available_while, read_card variants (when),
            reyes_rams_drawer_1a (when), exit.t_1a_1b (trigger, and needs memory_card)
  effect:   world: memory_card moves to kristin and is revealed

officer_demanded_card
  set by:   beats.officer_presses_1a
  read by:  beats.patrol_leaves_1a (picks the "description that is hers" text)
```

The compiler would also write the claim records back into the nine-file
`StoryPackage` shape, for example claim `k_sl_1a_b_r0w` with `establishes`
equal to the variant's `commits` and `source` pointing at
`find_card` / `witnessed`. That is the parity-gate comparison in Phase 2.

---

## Four edits to try (task sheet)

Rules for all four: use only this file (schema section plus sample plus the
generated block). Do not open the nine legacy files until you have finished the
edit. Say aloud or write down: where you looked first, what you typed, and the
moment you were unsure. Fill in the table at the end. If you cannot tell what to
do from the schema, that is the finding; write it down instead of guessing.

The "Legacy" lines are my counts from the nine files at `8670fd89`. They are
counts of places, not timings. The "Check yourself" lines come last on purpose:
read them after you have tried the edit.

### Edit 1. Reword a passage

**Change:** in the quiet find (`find_card` / `quiet`), Kristin does not pocket
the card. She tucks it into her jacket.

**Done when:** every line in the file that describes how Kristin handles the
card, in either variant, says so.

**Watch for:** which fields say how she handles the card; what the witnessed
variant does; the `must_convey` words.

**Legacy:** `delivery_text` of `k_sl_1a_b_r0` and `k_sl_1a_b_r0w`, and the
`statement` of `k_sl_1a_b_r0` (all in `knowledge.yaml`). Three test files contain
the sentence "and she pockets it" (`test_pipeline_eval.py`, `test_judge_input.py`,
`test_1a_back_door_gap.py`); I did not run which of them fail.

**Check yourself:** two lines change: `says` of the quiet variant, and
`parts.find_lead`. The witnessed passage picks the new wording up through
`{find_lead}`, so the two variants cannot disagree. `intent` says "keeps it with
her", which is still true, so it does not change; that is what "purpose, not
wording" means. The `must_convey` words still hold. Two costs remain, and they are
the honest result to record: `says` and the passage are still two copies of one
fact, because `says` is a separate statement of what the player now knows; and
the witnessed `text` is no longer readable in place, since part of it lives in
`parts`. In revision 1 this edit touched three fields plus the other variant.

### Edit 2. Decide who owns the officer's demand

This one is a story decision. Choose first, then edit. Say which you chose.

**Today:** when Kristin is seen taking the card, the witnessed passage ends with
the officer asking "What have you got there?" The officer's spoken demand
("Whatever you just took from that desk...") comes later, from the beat
`officer_presses_1a`. That beat fires once, the first time `card_challenged` and
`patrol_in_house` are both true at or after turn 7, and it sets
`officer_demanded_card`. The beat `patrol_leaves_1a` reads that fact to pick its
text.

**Choice A: leave the demand where it is.** Then write down what, if anything,
committing `officer_demanded_card` at find time would add. (Hint: look at what
`officer_presses_1a` checks before it fires.)

**Choice B: make the demand part of the find.** Do all three:
1. Make the witnessed variant commit `officer_demanded_card`.
2. Put the officer's demand into the witnessed passage.
3. Remove the beat `officer_presses_1a`.

If you have no strong view, do B; it touches more of the file.

**Done when (B):** the witnessed variant commits the fact, its passage contains
the demand, the beat is gone, and you can say what the player now sees and when,
compared with before.

**Watch for:** the beat's passage is flagged `verbatim`; a reveal's `text` has no
such flag in this format, and I have not checked whether a reveal's text is
delivered exactly as written. Also: what reads `officer_demanded_card` once the
beat is gone, and whether the demand now arrives earlier than before.

**Legacy:** for B, `operations` of `SL-1A-E-R2` (`storylet-routes.yaml`),
`establishes` and `delivery_text` of `k_sl_1a_b_r0w` (`knowledge.yaml`), and the
event in `pacing.yaml`. Five test files name `officer_presses_1a`
(`test_trailing_pacing_events.py`, `test_gap_rules.py`, `test_situation_trace.py`,
`test_1a_officer_press.py`, `test_impact_report.py`); I did not run which break.
The fact catalogs already list `SL-1A-E` as a user of the fact, so they do not
change.

**Check yourself:** for A: the beat's guard is `card_challenged` and
`patrol_in_house`. It does not read `officer_demanded_card`, so it still fires and
sets the fact again. The extra commit changes nothing the player can see; it is
redundant. Saying so is a valid result. For B: nothing in the file reads
`officer_demanded_card` except `patrol_leaves_1a`, so deleting the beat is safe
for the data, but the demand text must move or it is lost. The player now hears
the demand in the same turn as the find, not a turn or more later. Whether that is
better is your call, not the format's.

### Edit 3. Change a shared search description

**Change:** a player typing "Pull the drawer out" should count as searching the
drawer. Change the lists so it does.

**Done when:**
1. `Pull the drawer out` in `drawer_search.examples` is changed to
   `matches: true`, and every other example keeps its result.
2. You can say which variants the change reaches.
3. You have added one example for a command you did *not* mean to admit.

**Where to read first:** "How a command is checked", under the value shapes in the
schema section. It says what each list does and which words come for free.

**Watch for:** which of the three groups "Pull the drawer out" fails; whether the
new words also admit commands you did not intend (rule 3 in that section);
whether editing `earn_when` is enough (it is not; see its row in the `searches`
table).

**Legacy:** `action_evidence` and `earn_when` are copied in both `k_sl_1a_b_r0`
and `k_sl_1a_b_r0w`. Both copies are identical today, and another copy sits in a
frozen test fixture (`tests/fixtures/continuity_initiative_pre_3c_adoption/`) that
must not change.

**Check yourself:** "Pull the drawer out" fails two groups: group 1 has no verb
for "pull", and group 2 has no word for "out" (there is no position word in the
command). Add `pull` to group 1 and `out` to group 2. I ran exactly this change
through the real matcher. It reaches both variants, because both use
`drawer_search`. Side effects I measured: `pull` is in the engine's "take" class,
so "Take the drawer out" and "Grab the drawer out" now match too. "Slide the
drawer out" still does not (`slide` is in no class), and "Remove the drawer" still
does not (no position word). `earn_when` is read by the model, so editing it alone
changes nothing about which exact commands match; revision 1's copy of this edit
changed only `earn_when`. One more thing the examples show: "Search the drawer"
does not match, though `earn_when` says "searches the drawer". That mismatch is in
the legacy data too; I copied it as it was.

### Edit 4. Follow one consequence into 1B and back

**Change:** none. Start at the fact `kristin_marked_by_patrol` and answer, using
only this file: where is it set; what reacts to it in 1B; what text does the
player see because of it; and what goes stale in 1B if the witnessed find stops
committing it.

**Done when:** you have written the four answers.

**Where to look:** the 1B excerpt after the 1A file, and the generated block at
the end. The generated block was made by hand (its header says how), so check at
least one of its lines against the excerpt.

**Legacy:** the fact appears in `world.yaml`, `pacing.yaml`,
`storylet-routes.yaml` (two places), `knowledge.yaml` (two places) and
`storylets.md`, plus five test files. The only reader is the first realization of
`pursuit_1b` in `pacing.yaml`.

**Check yourself:** set by `find_card` / `witnessed`; read by the 1B beat
`pursuit_1b` (the first `say` entry); the player sees "The pursuers already have a
description of Kristin. They are closing in through the park." instead of "The
pursuers are closing in through the park. The pursuit is not over."; if the commit
is removed that first entry can never be chosen, and nothing in the file says so
(the legacy loader accepts it too; Phase 0 edit B). A related thing to notice:
`officer_demanded_card` also makes the patrol "have a description that is hers"
(`patrol_leaves_1a`). Two facts say nearly the same thing. Revision 1 had a
`hands_to_1B` line here that did nothing you could see; it was removed.

### Optional harder edits (from the earlier comparison and Phase 0)

The comparison document ran different edits, and Phase 0 measured three more.
They are not part of the four above, so do them only if you want more evidence:

- **Move card recovery from 1A to 1B** (comparison). The hardest one. It is not
  just changing a scene id: the 1A exit needs the card, and the alternate handoff
  can produce it in 1A too. A good format reports those instead of letting you
  proceed silently. This draft cannot show that, because it has no impact
  checker and only one scene.
- **Rename `kristin_marked_by_patrol`** (Phase 0 edit C). In the draft: one fact
  key, one commit, and the `when` in the 1B excerpt. Legacy: 5 story files and
  5 test files mention it today; Phase 0 measured 4 failing tests for the rename.
- **Remove the commit that marks her** (Phase 0 edit B). Same as the last
  question in edit 4.

## Things I noticed while writing this (for you, not decisions)

- Revision 1 was wrong in several ways, all now fixed: no schema section; fields
  used but not defined; `aliases` and `helps_transition_triggers` left out;
  `text: verbatim` where legacy has a per-passage flag; a wrong description of
  when beats fire; no 1B text for edit 4; a task-2 wording that hid a story
  decision. The sample's keys were checked mechanically against the schema section
  in revision 1; I did not re-run that check after the revision-2 edits, and the
  *meaning* columns are my reading of `models.py`, the engine and the data, not a
  test.
- What revision 2 relies on that I **did** check by running code: the sample's
  YAML parses and its top-level keys are the ones the schema lists; the match
  result of every `examples` entry (real matcher, `candidate_matcher.py`); the
  side effects listed in edit 3; and that expanding `{find_lead}` gives the quiet
  and witnessed `delivery_text` of `knowledge.yaml` exactly, after whitespace is
  collapsed. What I did **not** check: that any checker would accept `examples`
  (no checker exists); how `verbatim` interacts with a reveal's text; the
  per-field meanings in the schema tables beyond what is cited.
- `parts` and `examples` are both new inventions and the ones most worth
  pushing back on. `parts` makes one reword work across variants but a variant's
  text is no longer fully readable in place. `examples` makes the matcher lists
  understandable but adds about 15 lines per search block.
- Claim `k_sl_1a_b_r0` (the quiet find) has its `source` set to storylet
  `SL-1A-E`, but its ID says `b`. In the draft the ID is kept, and the reveal is
  `find_card`. Prose-derived letters in IDs mislead; this is why the plan says
  IDs must be independent of headings.
- The exit's `needs: memory_card, relation: exists` is the Reyes finding made
  visible: the exit does not check that Kristin still holds the card. I did not
  repair it. The format just makes the relation name something you have to
  write.
- `trailing: true` is the legacy field `PacingEvent.trailing` (`models.py:741`):
  "apply the event after the player's action is narrated." The key is copied as is.
- Size, measured: the two reveals (storylets E and B, claims `b_r0`, `b_r0w`,
  `b_r1`, `b_r2`) are 319 legacy lines in `knowledge.yaml` and
  `storylet-routes.yaml`. The draft's `searches:` and `reveals:` blocks are now
  145 lines (56 + 89), including the new `parts` and `examples` and the
  `play_recording` matcher still left out (about 15 more lines). Revision 1 was 97
  lines; the growth is mostly `examples`. It is a line count, not a measure of ease
  of editing; that is what the four edits test.

## Where you hesitated (fill in)

Keep your task notes in this table, not in the YAML above. In revision 1's copy,
the edit 3 task text ended up pasted into the middle of the sample file; the task
sheet is not part of the file you are editing.

| Edit | Looked first | Edited | Hesitated at |
| --- | --- | --- | --- |
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
