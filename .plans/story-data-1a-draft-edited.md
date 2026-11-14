# Scene 1A in the proposed authoring format (hand-written draft, no compiler)

Status (2026-11-11): **draft for D1; schema section added after Brandon asked where the field rules were.** Nothing here is read by any code. It
exists so Brandon can try four edits on it and then decide D1 in
[the redesign plan](story-data-redesign-plan.md). Facts, wording and numbers
are copied from the nine story files at `8670fd89`; where I changed nothing
about behavior I say so. Where the format forced a choice, it is marked
**CHOICE**.

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
| matcher words | `[[a, b], [c, d]]` | A list of word groups; one word from each group must appear | `action_evidence`, `must_convey` |

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
| `at_turn` | R | int | Turn the event is due | `at_turn` |
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
| `earn_when` | O | text | Plain-language description of the qualifying action | `earn_when` |
| `action_evidence` | O | matcher words | Words in the player's command | `action_evidence` |
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
| `audience` | R | `public`, or `{kind: characters, character_ids: [...], player_visible: ...}`, or `{kind: world_only}` | Who may know it. `public` is shorthand for kind public, player visible | `Audience` |
| `variants` | R | map of variant key to variant | See below | realizations and claims |

Variant fields:

| Field | R/O | Type | Meaning | Lands in |
| --- | --- | --- | --- | --- |
| `when` | O | condition | Facts that must hold for this variant. This is how two variants of one reveal are told apart | claim `requires` |
| `intent` | R | text | What the realization is trying to do dramatically | `dramatic_intent` |
| `commits` | R | effects | Facts asserted when the player earns it. Used for both the storylet operation and the claim's effect | `operations` and claim `establishes` |
| `commits_subset` | O | effects | Use only when the claim grants less than `commits` (12 of 99 today) | claim `establishes` |
| `says` | R | text | One sentence: what the player now knows | `KnowledgeDefinition.statement` |
| `text` | R | text | The delivered passage | `delivery_text` |
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
| `hands_to_<scene>` | O | list of facts | A declaration that the next scene reads these. New. The compiler can compute the list itself, so this may be unnecessary | none |

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
**Change:** a player typing "pull the drawer out" should count as searching the
drawer. Add the words you think are needed.

**Done when:** you have changed the matcher and can say which variants it now
applies to.

searches:                          # shared wording that decides "the player did this"
  drawer_search:
    earn_when: searches the drawer, the gap in the drawer, or the space beneath it, or pulls the drawer out
    action_evidence:
      - [look, search, inspect, check]
      - [under, beneath, underside, gap, lower edge, bottom edge]
      - [drawer, KMS, workstation, "drawer's"]
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

    variants:
      quiet:                       # [claim k_sl_1a_b_r0, realization SL-1A-E-R1]
        claim_id: k_sl_1a_b_r0
        when: {patrol_in_house: false}
        aliases: [memory card recovered]
        helps_exit: [t_1a_1b]
        intent: Kristin searches beneath the KMS drawer, finds Michelle's hidden memory card, and keeps it with her.
        commits: {memory_card_recovered: true}
        says: Kristin finds Michelle's memory card taped beneath the drawer and tucks it in her jacket.
        voiceable: false
        text: >-
          Kristin's fingers find something taped beneath the drawer. She peels
          it loose. It is Michelle's memory card, and she tucks it in her jacket. 
          Her laptop is still out in her truck.

      witnessed:                   # [claim k_sl_1a_b_r0w, realization SL-1A-E-R2]
        claim_id: k_sl_1a_b_r0w
        when: {patrol_in_house: true}
        aliases: [memory card recovered in sight of the patrol]
        helps_exit: [t_1a_1b]
        intent: Kristin finds the hidden card while a patrol officer is in the house, and the officer challenges her.
        commits: {officer_demanded_card: true, memory_card_recovered: true, card_challenged: true, kristin_marked_by_patrol: true}
        says: An officer saw Kristin take Michelle's memory card and asked what it is.
        text: >-
          Kristin's fingers find something taped beneath the drawer. She peels
          it loose. It is Michelle's memory card, and she pockets it. The
          officer turns at the sound. "What have you got there?" His hand is
          already out.

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
        earn_when: reads the files on Michelle's recovered memory card
        action_evidence:
          - [read, inspect, open, check, review, plug, insert, connect]
          - [memory card, card]
          - [file, files, saved file, saved files, card file, card files, laptop]
        reach: [memory_card, kristin_laptop]
        entities: [kristin, michelle, memory_card, kristin_laptop, park_bench]
        must_convey:
          - [memory card, card]
          - [Michelle, "Michelle's", Dr. McGehee, Michelle McGehee, Shelly]
          - [damaged recording, voice recording, recording]
          - [emergency broadcasts, broadcast]
          - [dead drop, exchange point]
          - [bench in the park, park bench]
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
    hands_to_1B:                   # optional, new; the compiler can compute this itself
      - kristin_marked_by_patrol   # read by 1B pursuit_1b
```

---

## What the compiler would generate (never edited)

Shown so you can follow a change forward and backward. This is the "forward
and backward dependency navigation" requirement; the author does not write it.

```text
kristin_marked_by_patrol
  set by:   reveals.find_card.witnessed (1A)
  read by:  1B beat pursuit_1b  (picks "already have a description of Kristin")
  also:     1A exit.hands_to_1B
  tests:    <id matches in tests/*.py, textual only>

card_challenged
  set by:   reveals.find_card.witnessed
  read by:  1A beat officer_presses_1a (when)
  note:     was listed with used_by_storylets: [SL-1A-E] and
            used_by_transitions: [] in three places before; now one

memory_card_recovered
  set by:   reveals.find_card.quiet, reveals.find_card.witnessed
  read by:  read_card.available_while, read_card.*.needs,
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

**Done when:** the quiet passage says so, and you are satisfied that nothing the
file says about this event now contradicts it.

**Watch for:** which other fields in the same variant describe the same moment;
the witnessed variant; the `must_convey` words.

**Legacy:** `delivery_text` of `k_sl_1a_b_r0` (`knowledge.yaml`) and its
`statement`. Three test files contain the sentence "and she pockets it"
(`test_pipeline_eval.py`, `test_judge_input.py`, `test_1a_back_door_gap.py`);
I did not run which of them fail.

**Check yourself:** `says` also says "pockets it", so there are two lines to
change in this variant. The witnessed variant's `text` also begins with the same
three sentences and ends the sentence the same way, so Kristin would tuck it in
one version and pocket it in the other unless you change both. The `must_convey`
groups still hold ("memory card", "taped", "beneath the drawer", "Michelle's").
The format did not make the wording single-owner; that is the honest result to
record if you find it.

### Edit 2. Change what a variant commits

**Change:** make the witnessed find also commit `officer_demanded_card`, so the
officer's demand is a consequence of being seen.

**Done when:** the witnessed variant commits it, and you have decided what
happens to the `officer_presses_1a` beat.

**Watch for:** what the beat does besides setting the fact; what reads
`officer_demanded_card`; what the player now sees and when.

**Legacy:** two places to change: the `operations` of `SL-1A-E-R2`
(`storylet-routes.yaml`) and `establishes` of `k_sl_1a_b_r0w`
(`knowledge.yaml`). The fact catalogs already list `SL-1A-E` as a user of the
fact, so they do not change. (My earlier draft said they would; that was wrong.)

**Check yourself:** the beat cannot simply be deleted. Its `say` is the officer's
spoken demand ("Whatever you just took from that desk..."), and
`patrol_leaves_1a` picks its text from the fact. Committing the fact at find time
would skip the demand passage. So this edit is partly a story decision, not only
a data edit: does the demand still happen at turn 7, and if so what does the
commit add? A good outcome is that you notice this from the file alone.

### Edit 3. Change a shared search description

**Change:** a player typing "pull the drawer out" should count as searching the
drawer. Add the words you think are needed.

**Done when:** you have changed the matcher and can say which variants it now
applies to.

**Watch for:** whether one change reaches both variants; whether the new words
also admit commands you did not intend, such as "open the drawer".

**Legacy:** `action_evidence` and `earn_when` are copied in both `k_sl_1a_b_r0`
and `k_sl_1a_b_r0w`. Both copies are identical today, and another copy sits in a
frozen test fixture (`tests/fixtures/continuity_initiative_pre_3c_adoption/`) that
must not change.

**Check yourself:** one change in `searches.drawer_search` reaches both variants.
The first word group needs a verb such as "pull" or "slide", and the second needs
something like "out", since "pull the drawer out" has none of the current
position words. Notice that `read_files` in the sample does not use the
`searches` block and carries its own copy of its matcher. That inconsistency is
mine; tell me if it confused you.

### Edit 4. Follow one consequence into 1B and back

**Change:** none. Start at the fact `kristin_marked_by_patrol` and answer, using
only this file: where is it set; what reacts to it in 1B; what text does the
player see because of it; and what goes stale in 1B if the witnessed find stops
committing it.

**Done when:** you have written the four answers.

**Legacy:** the fact appears in `world.yaml`, `pacing.yaml`,
`storylet-routes.yaml` (two places), `knowledge.yaml` (two places) and
`storylets.md`, plus tests. The only reader is the first realization of
`pursuit_1b` in `pacing.yaml`.

**Check yourself:** set by `find_card` / `witnessed`; read by the 1B pacing event
`pursuit_1b`; it picks "The pursuers already have a description of Kristin..."
over the default; if the commit is removed that sentence has no producer, which
the loader accepts today (Phase 0 edit B). Note that this draft contains no 1B
text at all. The 1B reader is shown only in the generated block, which I wrote by
hand. If you could not trust that block, that is the finding. A related thing to
notice: `officer_demanded_card` also makes the patrol "have a description that is
hers" (`patrol_leaves_1a`). Two facts say nearly the same thing.

### Optional harder edits (from the earlier comparison and Phase 0)

The comparison document ran different edits, and Phase 0 measured three more.
They are not part of the four above, so do them only if you want more evidence:

- **Move card recovery from 1A to 1B** (comparison). The hardest one. It is not
  just changing a scene id: the 1A exit needs the card, and the alternate handoff
  can produce it in 1A too. A good format reports those instead of letting you
  proceed silently. This draft cannot show that, because it has no impact
  checker and only one scene.
- **Rename `kristin_marked_by_patrol`** (Phase 0 edit C). In the draft: one fact
  key, one commit, one `hands_to_1B` line, and the 1B reader, which is not in the
  file. Legacy: 5 story files, 3 test files, 4 failing tests.
- **Remove the commit that marks her** (Phase 0 edit B). Same as the last
  question in edit 4.

## Things I noticed while writing this (for you, not decisions)

- Two things were wrong in the first version of this draft and are fixed: it had no schema (now the section above), and its sample used fields it never defined, left out `aliases` (legacy requires at least one) and `helps_transition_triggers`, and wrote `text: verbatim` where legacy has a per-passage `verbatim` flag. The sample's top-level keys, beat keys and variant keys were checked mechanically against the schema section; the *meaning* column is my reading of `models.py` and the data, not a test.
- Claim `k_sl_1a_b_r0` (the quiet find) has its `source` set to storylet
  `SL-1A-E`, but its ID says `b`. In the draft the ID is kept, and the reveal is
  `find_card`. Prose-derived letters in IDs mislead; this is why the plan says
  IDs must be independent of headings.
- The exit's `needs: memory_card, relation: exists` is the Reyes finding made
  visible: the exit does not check that Kristin still holds the card. I did not
  repair it. The format just makes the relation name something you have to
  write.
- `trailing: true` is the legacy field `PacingEvent.trailing` (`models.py:741`): "apply the event after the player's action is narrated." The draft's comment on it ("fires even if the player left") was wrong and is fixed below. The key is copied as is.
- Size, measured: the two reveals (storylets E and B, claims `b_r0`, `b_r0w`, `b_r1`, `b_r2`) are 319 legacy lines in `knowledge.yaml` and `storylet-routes.yaml`. The draft's `reveals:` block is 97 lines, with the `play_recording` search wording left out (about 15 more lines). The saving comes from the search wording appearing once and claim effects not being restated. It is a line count, not a measure of ease of editing; that is what the four edits test.

## Where you hesitated (fill in)

| Edit | Looked first | Edited | Hesitated at |
| --- | --- | --- | --- |
| 1 | variants: quiet | says:, then intent:, then text:| wondering why I'm still editing three spots when they are mostly copies of each other. |
| 2 | variants: witnessed |adds officer_demanded_card: true to commits: | I could not understand what you were asking for |
| 3 | searches: drawer_search: earn_when | earn_when | action_evidence: - didn't make any sense how to edit the lists to achieve "pull the drawer out"  |
| 4 | find_card: variants: witnessed; t_1a_1b; Kristin's fingers find something taped beneath the drawer. She peels it loose. It is Michelle's memory card, and she pockets it. The officer turns at the sound. "What have you got there?" His hand is already out.; The exit goes stale. | find_card: variants: witnessed | hands_to_1B because it's not clear what that does from there, even though you said it's all in one file. | 

