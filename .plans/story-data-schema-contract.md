# Story data schema contract (pass 1 and pass 2)

Status (2026-11-16, branch `plan-lexicon-two-pass`): **draft contract, nothing built. Brandon answered Q1 to Q5 (section 11) on 2026-11-16: all five recommendations accepted.**
This is the Phase 1 item 2 schema for [the redesign plan](story-data-redesign-plan.md),
written for step 1 of [the dark factory plan](Continuity%20Initiative%20dark%20factory%20plan.md).
It starts from the [1A draft](story-data-1a-draft.md) and the
[2C-to-3A draft](story-data-2c-3a-draft.md) (both revision 2). Every number marked
"checked" was measured by a read-only script on the live loaded package on this
branch (section 12).

## 1. Status and scope

**What this is.** The contract a compiler, a validator and a test migration are built
against. It names every source file, every key, what each key compiles to in
today's `StoryPackage` (`storygame/story_package/models.py`), the checks, the lookup
API for tests, the story CLI surface and the parity diff. It contains no code.

**Fixed (decided by Brandon; not re-opened here).** D1 (declarative scene blocks
compile to `StoryPackage`), D2 (no stored flags store), D3 (layer 3 never blocks),
D4 (compile at load time with the fingerprint cache); fact ownership option A;
typed relations option B, shape `{item, relation: exists|held|reach, holder?, not?}`;
`examples` as a separate accept/reject fixture; a `leak_terms` or `boundaries`
override may only add; the save-identity policy (frozen IDs, warning-only
manifest, strictness at build/load, saves flexible); the coexistence manifest
(explicit mode, two owners is an error); deletion of `SL-2C-D-R1`/`-R2`; two passes,
no time box, no fallback to the nine files.

**Proposed here.** Everything else. Where a draft and the live package disagree,
the live package wins; the table below lists each place.

**Pass 1** is complete on its own: all `StoryPackage` fields for a scene and for the
catalog, matcher lists written out in full, the five structural derivations
(section 5), layers 1 and 2, record lookup, the CLI, and the parity gate. It reads
no lexicon.

**Pass 2** is optional and per scene: a name lexicon (entities, concepts, story
verb classes), a generated lock file that keeps the compiled lists unchanged, the
`add:`/`drop:` override syntax, the override-ratio report, and optional plural
twins. It starts on 1A to 2C.

**Out of scope.** Implementation, the test migration itself, story repairs (the
Reyes custody repair, deleting unplaced facts), and the deterministic runtime trace
comparison that Phase 2 also requires (it is a separate gate; section 9 points to
it).

### Where this contract departs from the drafts

| Draft said | Live package or code shows | Contract does |
| --- | --- | --- |
| 1A: `guidance.done_when` lands in "storylet completion" | No `StoryPackage` field holds it; the loader never reads `completion_or_abort` (`loader.py:1672-1683`) | Field dropped. The prose stays in `notes.completion` |
| 1A: a passage list uses "first match wins" | True for pacing realizations (`engine.py:1363`). Claim delivery variants are exactly-one-or-base: two matches give `AMBIGUOUS` (`delivery_text.py:35`). Entry and ending variants append every match (`models.py:647`, `engine.py:807`) | Three shapes with three names: `say` (first match), `text` + `text_when` (one of), `entry_additions` / `additions` (append) |
| 1A: `participants`, `items` could be derived | Not derivable (checked; section 5, rule 10) | Written explicitly |
| 1A: bridge text lands in `fallback_text` | The 1A and 2C bridge texts sit under `fallback_realization`, which no code reads (2C draft found this) | Reader-only `note` |
| 1A: shared `searches` block holds `earn_when`, `reach`, `entities` | These are scene logic, not matcher words | `earn_when`, `reach`, `entities` are reveal-level defaults in the scene file; matcher words move to the match file |
| 2C, addition 1: commit-only variant withdrawn | `SL-3C-F-R1` is a live realization with no claim (checked) | Accepted: a variant without `claim_id` compiles to a realization only |
| 2C, addition 8: delivery `scene_id` is the declaring scene, not written | 46 of 48 match; `processing_numbers_copied` and `service_level_access_known` are declared in 1C and delivered in 2A (checked) | Optional `delivery.scene`, default the declaring scene |
| 2C, addition 9: one entry claim; `k_1b_stranger_evasion` does not fit | It is a second scene-entry claim for 1B with a `characters` audience; both set `scene_1b_entry_known` | `entry_claims` is a list |
| 2C, addition 6: passage list "same shape as a beat's `say`" | Different selection rule (above) | `text_when` |
| 2C: "nothing in the format tells you" `must_convey` must change after a reword | The loader already fails a claim whose `delivery_text` or variant misses a `must_convey` group (`loader.py:726-737`) | No new check; the build error names the claim |
| 2C: not known whether the loader rejects an outcome fact the variant does not commit | It does (`loader.py:1246-1251`) | Inherited, not re-specified |
| Plan section 2: "87 of 99 claim effects identical, 12 subset" | Live: 112 sourced claims; 96 equal as sets (93 in the same order), 16 strict subsets | Same rule, new numbers |
| Plan item 10: 13 facts with no setter | They also have no reader anywhere in the package | Catalog `unplaced_facts` (question Q1) |
| Plan pass 2: `purpose`, `intent`, `says` collapse to one sentence | `intent == says` in 10 of 100 claims; `says` never equals a fact purpose (checked). It cannot reproduce the package | Not part of pass 2 (question Q2) |
| Plan item 5: Phase 2 keeps 1A legacy and runs compiled 1A beside it, and a scene marked `legacy` with compiled records fails the build | Both hold only if pilot sources live outside the shipping package root | Pilot sources live in `data/story-pilot/<story>/source/`; they move into the package root at the first flip (section 2) |

## 2. File layout

```text
data/stories/continuity-initiative/         shipping package root (nine legacy files today)
  ownership.yaml                            coexistence manifest; absent = every scene legacy
  source/
    story.yaml                              root: identity, scene order, story-wide text
    catalog.yaml                            entities, kinds, props, connections, guards, unplaced facts
    lexicon.yaml                            pass 2 only; optional
    scenes/
      1A.yaml                               scene file: prose, conditions, effects, IDs
      1A.match.yaml                         matcher words, keyed by claim ID and fact ID
      1A.match.lock.yaml                    pass 2 only; generated, never edited
      ... one pair (or triple) per scene
tests/fixtures/story_examples/continuity-initiative/1A.yaml    accept/reject commands
tests/fixtures/parity/continuity-initiative/1A.reviewed.yaml   reviewed parity differences
tests/fixtures/save_identity/continuity-initiative.yaml        frozen IDs, generated once from the snapshot
```

**Pilot location.** Until the first scene flips to `compiled` in the shipping
package, `source/` lives at `data/story-pilot/continuity-initiative/source/`. The
shipping loader never reads it, so no legacy-marked scene "has compiled records".
The parity tool compiles it. At the first flip it moves once into the package root.
The load fingerprint already hashes every file under the root (`loader.py:1728`), so
after the move every source file, match file, lock and lexicon invalidates the
cache. Examples and reviewed differences live under `tests/`, outside the root, so
they can never change the package.

**Why one match file per scene.** Prose and logic stay in the scene file; matcher
words go to a separate file keyed by claim ID. Reasons:

- 3B has 563 `action_evidence` words over 11 claims (median 55, max 93 per claim);
  3C has 502 over 17. Inline, a 3B variant would be mostly word list, and the
  passage the author edits would scroll away. Kept apart, the scene file reads as
  prose plus wiring, and the match file is a table addressed by claim ID.
- One rule for every scene. A worker never guesses where a list lives. 1A pays a
  small cost (a second file for an edit like "make `Pull the drawer out` count").
  `story show claim:<id>` merges both files, and a reworded passage that drops a
  `must_convey` phrase already fails the build.
- Every claim has an entry, because `aliases` (at least one, `models.py:186`) live
  there. So the match file's entry order is the compiled claim order (section 4.9),
  which today's package needs and the reveal order cannot give.
- Per-claim files were rejected: 122 tiny files and no per-scene review.

### Top-level keys

Every source file begins with `schema: 1` (the contract version). An unknown
top-level key is a layer 1 error.

| File | Keys, in this order |
| --- | --- |
| `ownership.yaml` | `schema`, `catalog` (`legacy`\|`compiled`), `scenes` (map scene id to `legacy`\|`compiled`; a scene not listed is `legacy`) |
| `story.yaml` | `schema`, `story`, `title`, `genre`, `protagonist`, `budget_seconds`, `scenes`, `principal_characters`, `acts`, `front_matter`, `retired_ids` |
| `catalog.yaml` | `schema`, `places`, `characters`, `groups`, `items`, `kinds`, `props`, `connections`, `protected_knowledge`, `disclosure_guards`, `unplaced_facts` |
| `scenes/<id>.yaml` | `schema`, `scene`, header keys (4.3), `brief`, `outline`, `facts`, `placements`, `beats`, `reveals`, `bridge`, `incidents`, `exit`, `ending`, `order` |
| `scenes/<id>.match.yaml` | `schema`, `scene`, `lexicon` (pass 2), `plural_twins` (pass 2), `shared`, `claims`, `deliveries` |
| `scenes/<id>.match.lock.yaml` | `schema`, `scene`, `generated_by`, `claims`, `deliveries` (generated) |
| `lexicon.yaml` | `schema`, `entities`, `concepts`, `verb_classes` |
| examples fixture | `schema`, `scene`, `claims`, `shared` |
| reviewed differences | `schema`, `scene`, `differences` |
| save identity | `schema`, `story`, `snapshot`, `ids` (map kind to list) |

YAML is read with a loader that rejects duplicate keys (layer 1). `yaml.safe_load`
overwrites them silently today.

## 3. Value shapes

| Shape | Written as | Compiles to | Rule |
| --- | --- | --- | --- |
| id | `snake_case` (`^[a-z][a-z0-9_]*$`) | same | Never derived from a heading, prose, file name or order. The compiler generates no ID except the entry fact `scene_<id>_entry_known`, which the engine already fixes (`state.py:276`) |
| scene id | `1A` (`^[1-9][A-Z]$`) | same | |
| storylet id | `SL-1A-E` | `StoryletRoute.id`, `Storylet.id` | Pattern from `models.py:757`. Free per the save policy, but written explicitly |
| realization id | `SL-1A-E-R1` | `RouteRealization.id` | Free; written explicitly |
| outline beat id | `1A.1` | `SceneBeat.id` | Pattern `models.py:660` |
| anchor | `scene-1a1--michelle-is-gone` | `SceneBeat.anchor` | Written explicitly, not derived from the title. A new beat's anchor is written by `story` when the beat is created, as `scene-<id without dot>` |
| condition | `{fact: true, other: false}` or `[fact, other]` (each true) | tuple of `FactPredicate`, in written order | Values `true`/`false` only. Fields marked "all true" (entry additions, `text_when`, ending additions, exit `when_all`) reject `false` (layer 1) |
| activation | `when`, `when_any`, `at_least` | `ActivationRule(all_facts_true, any_of, at_least)` | Bridge entries only |
| effects | `{fact: true}`, `{fact: false}`, `{fact: retract}` | Route operations: `true` gives `assert` value `True`; `false` gives `assert` value `False`; `retract` gives `op: retract, value: True` (`handoffs.yaml` shape). Pacing `sets`: `FactPredicate(equals)`; `retract` is a layer 1 error there | Map order is the operation order |
| world effect | `{move, parent, text?, under?}`, `{reveal}`, `{accompany, with}`, `{set_axis, value}` | `WorldEffect` | Exactly one shape (`models.py:439`) |
| passage | a YAML string | `str`, byte for byte | The scalar's value is the compiled string. The converter picks a style that reproduces the legacy bytes (the live 1A `entry_text` ends in `"\n\n"`). `story fmt` never changes a scalar's value |
| part reference | `{find_lead}` inside a passage | the part's text pasted in | Only in variant `text`, `text_when[].text`, and `speaker_text`. `{{` and `}}` write a literal brace. No live passage contains a brace (checked). An unknown name is a layer 2 error |
| typed relation | `{item, relation: exists\|held\|reach, holder?, not?}` | exit: `required_dependencies` gets `item` when `relation` is `exists` or `held` and `not` is absent; anything else compiles to nothing and feeds the checker | Decided shape. `item` may name any entity, a character included (the 2C draft noted the oddity; kept as decided). `holder` defaults to the protagonist and is valid only with `held` |
| matcher words | list of groups: `[[a, b], [c]]` | `tuple[tuple[str, ...], ...]` | `action_evidence`, `must_convey`. Pass 1: plain lists only |
| term list | `[a, b]` | `tuple[str, ...]` | `aliases`, `leak_terms` |
| `leak_terms` absent vs empty | key absent, or `leak_terms: []` | `None`, or `()` | Not the same. With `None` the loader treats every alias and every multi-word `must_convey` phrase as a leak term; with `()` there are none (`loader.py:385-397`). Live: 98 claims `None`, 13 empty, 11 with a list (checked) |

## 4. Per-record schemas for pass 1

Columns: **R** required, **O** optional (default in brackets). "Lands in" names the
`StoryPackage` field. "reader" means the value reaches no runtime field.

### 4.1 `story.yaml`

| Key | R/O | Lands in |
| --- | --- | --- |
| `story` | R | `StoryPackage.story_id`, `WorldSource.story_id`, `StoryletRoutesSource.story_id` |
| `title` | O | reader |
| `genre` | O [""] | `StoryPackage.genre` |
| `protagonist` | R | `protagonist_id` (both) |
| `budget_seconds` | R | `PacingSource.budget_seconds` |
| `scenes` | R | `canonical_scene_chain`; the last entry is `sole_ending_scene_id`; order of `StoryPackage.scenes` |
| `principal_characters` | O [] | order of `StoryPackage.characters`; each id must be a catalog character with `narrator_bio` or `bio` |
| `acts` | O | reader: `{title, intro, scenes}` keeps the act headings and intros now inside `plot.md` |
| `front_matter` | O | reader: premise, overall setting, the pacing contract (today `plot.md` lines 1-72) |
| `retired_ids` | O | none: `{kind: {id: reason}}`; silences the save-identity warning for that ID |

```yaml
schema: 1
story: continuity_initiative
title: Story 1373
genre: Adventure / Conspiracy Thriller
protagonist: kristin
budget_seconds: 7200
scenes: [1A, 1B, 1C, 2A, 2B, 2C, 3A, 3B, 3C]
principal_characters: [kristin, michelle, brandon, charles, rebecca, senior_official, patrol_officer]
acts:
  - title: Scene 2 — The Infiltration
    scenes: [2A, 2B, 2C]
    intro: |
      ...
retired_ids: {}
```

### 4.2 `catalog.yaml`

Entity entries are the model records with the id as the map key. Every field of
`Location` (`models.py:326`), `Npc` (`:416`), `Group` (`:322`) and `Item` (`:346`) is
accepted with the same name and default; nothing is renamed. Map order is list
order in `WorldSource`.

| Key | Shape | Lands in |
| --- | --- | --- |
| `places` | map id to `Location` fields | `WorldSource.locations` |
| `characters` | map id to `Npc` fields, plus `bio` (O, reader: the `plot.md` paragraph) | `WorldSource.npcs`; `Character(id, name, bio=narrator_bio or bio)` for each id in `principal_characters` |
| `groups` | map id to `Group` fields | `WorldSource.groups` |
| `items` | map id to `Item` fields | `WorldSource.items` |
| `kinds` | map id to `{is, enterable, fixed}` | `WorldSource.kinds` |
| `props` | map id to `PropDeclaration` fields | `WorldSource.props` (none live) |
| `connections` | map id to `{from, to, via?, access_fact?, consequences?, arrival}` | `Connection(from_place_id, to_place_id, via_id, access_fact_id, consequences, arrival_text)` |
| `protected_knowledge` | list of names | `WorldSource.protected_knowledge` |
| `disclosure_guards` | map id to `{terms, unlock_fact? \| unlock_claim?}` | `DisclosureGuard`; `unlock_claim` is `unlock_knowledge_id` |
| `unplaced_facts` | map id to a fact declaration (4.5) | facts that nothing sets and nothing reads (13 live). A fact with a setter or a reader here is a layer 2 error |

```yaml
characters:
  brandon:
    name: Brandon Corfman
    aliases: [Brandon, Brandon Corfman]
    unnamed_label: the man watching Kristin
    named_by: brandon_identified
    narrator_bio: A 54-year-old former software developer ...
    bio: ...                        # reader only: the plot.md paragraph
    axes: [{conscious: [awake], unconscious: [knocked out]}]
    unavailable: unconscious
items:
  memory_card: {name: "Michelle's memory card", aliases: [memory card], fallback_ids: [michelle_phone], hidden: true}
disclosure_guards:
  memory_card_word_guard: {terms: [card], unlock_fact: memory_card_recovered}
```

### 4.3 Scene header

| Key | R/O | Lands in |
| --- | --- | --- |
| `scene` | R | `SceneMetadata.scene_id`, `SceneFrame.scene_id`, `ScenePacing.scene_id`, and the `scene_id` of every record in the file |
| `title` | O | reader (the `## Scene` heading) |
| `location` | R | `location_id` |
| `objective` | R | `objective` |
| `freytag_phase` | R | `freytag_phase` (enum, `models.py:622`) |
| `situation` | O [""] | `SceneFrame.situation` |
| `pressure` | R | `SceneFrame.pressure` |
| `turns` | R | `ScenePacing{min_turns, nudge_after_turns, handoff_after_turns}` from `{min, nudge, handoff}` |
| `scripted_opening` | O [false] | `scripted_opening` |
| `companions` | O [] | `companions` |
| `participants` | O [] | `participant_ids` (explicit; not derivable) |
| `items` | O [] | `item_ids` (explicit; order is not placement order in 4 scenes) |
| `setting` | O [] | `setting_facts` |
| `prop_pool` | O [] | `prop_pool` |
| `entry` | R | `entry_text` |
| `entry_additions` | O [] | `entry_variants`: `{when (all true), text}` to `EntryTextVariant(requires, text)`. Every addition whose facts hold is appended after `entry`, in order. Renamed from `entry_variants` because authors read "variant" as "replaces" (2C draft) |
| `entry_claims` | O [] | 4.12 |

Generated from the header and the file: `SceneMetadata.transition_ids` and
`bridge_text` (from `exit`), `Scene.prose` (4.4), the scene's `Storylet` records.

### 4.4 `brief` and `outline` (today's `plot.md` scene body)

| Key | R/O | Lands in |
| --- | --- | --- |
| `brief` | O [""] | reader: the markdown before the first beat (Setting, Characters, Plot, Hidden canon, Established timeline) |
| `outline` | R, at least one entry, one with id `<scene>.1` | `Scene.beats` (keyed by anchor) and `Scene.opening_beat` (the `.1` beat) |
| `outline[].id` | R | `SceneBeat.id` |
| `outline[].anchor` | R | `SceneBeat.anchor`; the key of `Scene.beats` |
| `outline[].title` | R | `SceneBeat.title` |
| `outline[].details` | R, 3 to 7 | `SceneBeat.details` |
| `outline[].prose` | R | `SceneBeat.prose` (markdown, the beat body without the Details line) |

`Scene.prose` has no runtime reader (checked by grep: only `beat.prose` and
`opening_beat` are read). The compiler renders it as `brief`, then each beat as
`### Scene <id> — <title>`, `**Details:** <details joined by "; ">`, `<prose>`,
joined by blank lines. It is compared as reader-only text (section 9). Today the
1C and 2C `Scene.prose` also carry the next act's heading and intro, because the
parser reads to the next `## Scene` (checked); those move to `story.yaml acts`.

```yaml
outline:
  - id: 1A.1
    anchor: scene-1a1--michelle-is-gone
    title: Michelle Is Gone
    details: [missing tablet and work bag, splintered back door frame and thrown deadbolt, lukewarm mug of tea,
              folded reading glasses on manuscript pages, wall calendar and lake photograph, KMS initials carved in drawer]
    prose: |
      Kristin reaches Michelle's neighborhood after navigating traffic jams, ...
```

### 4.5 `facts`

A map from fact id to its declaration. A fact is declared once, in the scene that
first sets it in story order; a fact nothing sets lives in the first scene that
reads it; a fact nothing sets or reads lives in `catalog.unplaced_facts`.

| Key | R/O | Lands in |
| --- | --- | --- |
| `purpose` | R | `FactDefinition.purpose` |
| `on_assert` | O | `WorldSource.fact_effects[fact]` |
| `delivery` | O | `FactDelivery` (fact id from the key) |
| `delivery.scene` | O [declaring scene] | `FactDelivery.scene_id` |
| `delivery.source_kind` | R | `source_kind` (enum) |
| `delivery.source_entity` | O | `source_entity_id` |
| `delivery.fallback_text` | R | `fallback_text` |
| `delivery.cue_text` | O | `cue_text` |
| `delivery.escalation_text` | O | `escalation_text` (none live) |
| `delivery.costs` | O {} | `costs` (effects; `retract` allowed) |
| (`must_convey`) | in the match file | `FactDelivery.must_convey`, at least 2 groups |

Generated: `KnowledgeCatalog.facts` and `WorldSource.facts` (both: every declared
fact plus each scene's entry fact, in story order: scene order, then file order,
entry fact first, catalog `unplaced_facts` last). `storylet-routes.yaml new_fact_ids`
is not in `StoryPackage` and is not compiled.

```yaml
facts:
  memory_card_recovered:
    purpose: Kristin has recovered Michelle's memory card.
    on_assert:
      - {move: memory_card, parent: kristin, text: with Kristin}
      - {reveal: memory_card}
  continuity_initiative_known:
    purpose: Kristin knows Dr. McGehee was researching a suspicious emergency program called the Continuity Initiative.
    delivery:
      source_kind: message
      source_entity: michelle
      fallback_text: >-
        Kristin recovers Michelle's memory card from beneath the drawer and reads the files on it. The card
        identifies the federal emergency program as the Continuity Initiative, which was preparing to choose
        who remains.
      cue_text: "Kristin's initials, KMS, are carved into a drawer of Michelle's workstation."
      costs: {memory_card_recovered: true}
```

### 4.6 `placements`

A map from entity id to a string, `{parent, text?, under?, part_of?}`, or the old
form `{placement, while_fact_true? | while_fact_false?}` (model-supported, unused
live). The compiler routes characters and groups to `character_placements` and
items to `item_placements` (checked: that is how every live scene splits them).
Relative order within each kind is kept. Characters accept only `parent` and
`text` (`CharacterPlacement`).

### 4.7 `beats` (pacing events)

| Key | R/O | Lands in |
| --- | --- | --- |
| `id` | R | `PacingEvent.id` (frozen) |
| `at_turn` | R | `at_turn`: the earliest turn; fires once, the first time `when` holds at or after it |
| `when` | O [] | `when` |
| `sets` | R | `effects` (`FactPredicate`) |
| `trailing` | O [false] | `trailing` |
| `verbatim` | O [false] | default for every `say` entry |
| `say` | O | `realizations`: a string, or a list of `{when?, text, verbatim?}`. **First entry whose `when` holds is used**; the last entry has no `when` |
| `exit` | O | `transition_id` (none live) |
| `note` | O | none; reader-only review reason (today `pacing_event_review.reason`) |

Event order in the file is event order within the scene. The converter keeps the
legacy relative order; it decides same-turn ties (four live cases, checked).

### 4.8 `reveals`, variants and claims

One reveal is one storylet: one `StoryletRoute` plus one `Storylet` record.

**Reveal keys**

| Key | R/O | Lands in |
| --- | --- | --- |
| `id` | R | none: the authoring handle; unique story-wide |
| `storylet_id` | R | `StoryletRoute.id`, `Storylet.id` |
| `title` | R | `StoryletRoute.title`, `Storylet.title` |
| `guidance.pressure_role` | R | `pressure_role` |
| `guidance.window` | R | `{earliest_turn, target_turn, latest_turn}` on the route and on `Storylet` |
| `guidance.available_while` | O [] | `activation_conditions` |
| `guidance.boundaries` | O [] | `protected_knowledge_boundaries` of every realization. Reveal-level only (uniform in 68 of 68 storylets, checked) |
| `from_outline` | R, at least one | `Storylet.source_links` (beat ids to anchors) |
| `commits_common` | O {} | merged into every variant's `commits` |
| `parts` | O {} | none: text pasted into passages |
| `notes` | O {} | `Storylet.sections` (below) |
| `needs` | O [] | none: typed relations for the checker (option B) |
| defaults | O | `audience`, `helps_exit`, `entities`, `reach`, `relevance`, `voiceable`, `repeatable`, `earn_when`: a value here is the default for every variant; a variant's own value replaces it |
| `variants` | R | map from variant key (a handle) to variant |

**Variant keys**

| Key | R/O | Lands in |
| --- | --- | --- |
| `realization_id` | R | `RouteRealization.id` |
| `intent` | R | `dramatic_intent` |
| `commits` | R | `operations` = `commits_common` then `commits` (a variant key wins on conflict) |
| `from_outline` | O [] | `source_beats` (no default from the reveal: 36 live realizations have none while their storylet has links) |
| `helps_exit` | O [reveal default, else []] | `helps_transition_triggers` |
| `outcome` | O | 4.11 |
| `claim_id` | O | `KnowledgeDefinition.id` (frozen). Present = the variant has a claim. Absent = realization only (`SL-3C-F-R1`); then no claim key below is allowed |
| `says` | R with claim | `statement` |
| `when` | O [] | `requires` |
| `text` | O | `delivery_text` |
| `text_when` | O [] | `delivery_variants`: `{when (all true), text}`. **At most one may hold**; if two hold the engine returns `AMBIGUOUS` (`delivery_text.py:35`) |
| `speaker_text` | O {} | `speaker_text` |
| `earn_when` | O [default] | `earn_when` (read by the model, not the matcher) |
| `entities` | O [default] | `entity_ids` |
| `reach` | O [default] | `reach_entity_ids` |
| `relevance` | O [default, else `{entity_ids: [], priority: 0}`] | `relevance` (no default from `entities`: equal in only 61 of 122, 2C draft) |
| `audience` | R with claim (often from the default) | `audience`; `public` means `{kind: public, player_visible: true}` |
| `voiceable` | O [default, else true] | `voiceable` |
| `repeatable` | O [default, else false] | `repeatable` |
| `commits_subset` | O | `establishes`; must be a subset of the compiled `commits`. Absent: `establishes` = compiled `commits` |
| `action_contract` | O | `action_contract` (none live) |
| `extra_claims` | O [] | further claims from the same realization, each with its own `claim_id`, `says`, `audience` and the claim keys above. Renamed from the draft's `internal_claims`: one live extra claim is public (`k_supervisor_escorting`) |

Generated for every claim: `available_in_scenes = (scene,)`, `source =
{storylet_realization, storylet_id, realization_id}`. Matcher fields come from the
match file.

**`notes` and `Storylet.sections`.** The `Storylet` record has no runtime reader
beyond `id`, `scene_id` and `source_links` (checked by grep in `storygame/` and
`scripts/`). The compiler renders three sections from fields and takes the rest
from `notes`:

| Section | Source |
| --- | --- |
| `Source beats:` | rendered from `from_outline` as `[<id> — <title>](plot.md#<anchor>)`, comma-joined (reproduces 68 of 68, checked) |
| `Allowed scene:` | rendered as `` `<scene>` ``, unless `notes.allowed_scene` is set (3 live storylets add a parenthetical) |
| `Pacing window` | rendered from `guidance.window` |
| `Available when`, `Participants / items`, `Dramatic purpose`, `Possible realizations`, `Effects`, `Completion`, `Abort`, `Protected boundary`, `Non-coercion note:` | `notes.available_when`, `.participants`, `.dramatic_purpose`, `.possible_realizations`, `.effects`, `.completion`, `.abort`, `.protected_boundary`, `.non_coercion_note`, verbatim. Not derivable: `Dramatic purpose` equals `pressure_role` in 23 of 68, `Possible realizations` equals the intents in 11 of 68 (checked) |

Worked example (live 1A values; match entries in 4.9):

```yaml
reveals:
  - id: find_card
    storylet_id: SL-1A-E
    title: The KMS Mark
    from_outline: [1A.1]
    guidance:
      pressure_role: Let the KMS mark reward a careful search of Michelle's workstation before the patrol closes in.
      window: {earliest_turn: 1, target_turn: 3, latest_turn: 12}
      available_while: {memory_card_recovered: false}
      boundaries: [janus_selection_system, brandon_history, janus_phase_two]
    audience: public
    helps_exit: [t_1a_1b]
    earn_when: searches the drawer, the gap in the drawer, or the space beneath it
    entities: [kristin, michelle, memory_card, michelle_drawer]
    reach: [michelle_drawer]
    relevance: {entity_ids: [memory_card, michelle_drawer], priority: 10}
    parts:
      find_lead: >-
        Kristin's fingers find something taped beneath the drawer. She peels it loose. It is Michelle's memory
        card, and she pockets it.
    notes:
      available_when: "- Kristin does not yet have Michelle's memory card."
      completion: "- Kristin has Michelle's memory card."
      # ... the other free sections, verbatim
    variants:
      quiet:
        realization_id: SL-1A-E-R1
        intent: Kristin searches beneath the KMS drawer, finds Michelle's hidden memory card, and keeps it with her.
        from_outline: [1A.1]
        commits: {memory_card_recovered: true}
        claim_id: k_sl_1a_b_r0
        when: {patrol_in_house: false}
        says: Kristin finds Michelle's memory card taped beneath the drawer and pockets it.
        voiceable: false
        text: "{find_lead} Her laptop is still out in her truck."
      witnessed:
        realization_id: SL-1A-E-R2
        intent: Kristin finds the hidden card while a patrol officer is in the house, and the officer challenges her.
        from_outline: [1A.1]
        commits: {memory_card_recovered: true, card_challenged: true, kristin_marked_by_patrol: true}
        claim_id: k_sl_1a_b_r0w
        when: {patrol_in_house: true}
        says: An officer saw Kristin take Michelle's memory card and asked what it is.
        text: >-
          {find_lead} The officer turns at the sound. "What have you got there?" His hand is already out.
```

A one-of text (2C, `k_sl_2c_d_r3`):

```yaml
        text: "{sending} A maintenance ticket scrolls up the uplink's status panel. {route_close}"
        text_when:
          - when: [ticket_header_matched]
            text: >-
              {sending} A maintenance ticket scrolls up the uplink's status panel with the archive header and the
              code sensor fault. {route_close}
```

### 4.9 Match file

```yaml
schema: 1
scene: 1A
shared:
  drawer_search:
    action_evidence:
      - [look, search, inspect, check]
      - [under, beneath, underside, gap, lower edge, bottom edge]
      - [drawer, KMS, workstation, "drawer's"]
    must_convey:
      - [memory card, card, "Michelle's card", the card, hidden card, hidden memory card]
      - [taped]
      - [beneath the KMS drawer, under the KMS drawer, beneath the drawer]
      - [Michelle, "Michelle's", Dr. McGehee, Michelle McGehee, Shelly]
    leak_terms: [memory card, hidden memory card, hidden card, "Michelle's card", the card,
                 taped beneath the drawer, taped under the drawer, taped to the drawer, memory card recovered]
claims:                                   # entry order = compiled claim order in this scene
  k_sl_1a_b_r0:
    use: drawer_search
    aliases: [memory card recovered]
  k_sl_1a_b_r0w:
    use: drawer_search
    aliases: [memory card recovered in sight of the patrol]
deliveries:
  continuity_initiative_known:
    must_convey:
      - ["Michelle's memory card", "Michelle's files", "Michelle's notes", "Michelle's card", memory card, research files]
      - [Continuity Initiative, federal emergency program, Continuity program, federal Continuity program,
         Continuity project, population-selection program]
```

| Key | R/O | Lands in |
| --- | --- | --- |
| `claims` | R | one entry per claim of the scene (variant claims, extra claims, bridge claims, entry claims), keyed by claim id. Missing or extra entry: layer 2 |
| `claims.<id>.use` | O | name of a `shared` block; its fields are the defaults |
| `claims.<id>.aliases` | R (here or via `use`) | `aliases`, at least one |
| `claims.<id>.action_evidence` | O [()] | `action_evidence`; replaces the shared value |
| `claims.<id>.must_convey` | O [()] | `must_convey`; replaces the shared value |
| `claims.<id>.leak_terms` | O [absent] | `leak_terms`. Over a shared value only `{add: [...]}` is allowed (layer 2). Absent and not shared: `None` |
| `deliveries.<fact>.must_convey` | R for each declared `delivery` | `FactDelivery.must_convey` |
| `shared.<name>` | O | `action_evidence`, `must_convey`, `leak_terms`, `aliases` |

**Order.** Within a scene, compiled `KnowledgeCatalog.knowledge` follows the order
of `claims` here. Today's within-scene claim order differs from reveal order in
every scene (checked), and the runtime iterates claims in package order
(`knowledge.py:130` and later), so this order is kept, not derived.

**Long lists (3A to 3C).** `story fmt` writes each group as a flow list wrapped at
100 columns, one group per item, with an optional trailing comment as the group's
label. Entries keep their written order (`must_convey` group[0] is shown to the
model, `cloudflare.py:1731`). A 3B entry:

```yaml
  k_sl_3b_a_r1:
    aliases: [...]
    action_evidence:
      - [trigger, set off, sound, raise, create, plant, feed, send, report, fake, stage, simulate, cause, start,   # what she does
         trip, activate, use, reset, flood, overwhelm, trace, follow, exploit, overload, manipulate, spoof, ...]
      - [false alarm, false alarms, fake alarm, fake alarms, water-pressure alarm, water-pressure alarms, ...]       # what it is done to
```

Edits go by ID, not by copying: `story set claim:k_sl_3b_a_r1.action_evidence[1] --add "smoke alarm"`.

### 4.10 `bridge` (canonical bridge and resolution events)

| Key | R/O | Lands in |
| --- | --- | --- |
| `id` | R | `CanonicalRouteEvent.id` |
| `kind` | O [`bridge`] | `bridge` goes to `bridge_events`, `resolution` to `resolution_events` |
| `when` | O [] | `activation.all_facts_true` |
| `when_any`, `at_least` | O [[], 0] | `activation.any_of`, `at_least` |
| `commits` | R | `operations` |
| `realized_by` | O [] | `realization_storylets` (reveal handles to storylet ids) |
| `fallback_text` | O; R for `resolution` | `fallback_text` |
| `delivery_text` | O | `delivery_text` |
| `note` | O | none: reader-only (the 11 legacy `fallback_realization` texts; question Q4) |
| `claim` | O | a claim with `source = {canonical_route_event, canonical_event_id}`; claim keys as in 4.8; `commits_subset` against `commits` (7 of 12 live event claims are subsets) |

```yaml
bridge:
  - id: bridge_2c_missed_window_recovery
    when: [purge_window_missed, purge_recovery_ready]
    commits: {purge_window_missed: true, rebecca_offer_active: true, ...}
    realized_by: [michelles_route_arrives]
    note: The purge forces the group onto a neutral maintenance route toward Rebecca's office.
    claim:
      claim_id: k_purge_window_missed
      says: The purge window closed before Kristin resolved the command-corridor incident.
      audience: public
      commits_subset: {purge_window_missed: true}
```

### 4.11 `incidents` (at most one per scene; `loader.py:1121`)

| Key | R/O | Lands in |
| --- | --- | --- |
| `id` | R | `Incident.id` |
| `reveal` | R | the reveal whose variants are the outcomes; gives `IncidentOutcome.storylet_id` |
| `outcomes` | R, at least 2 | variant keys of `reveal`, in order; each variant must carry `outcome` |
| `recovery` | R | reveal handle, to `recovery_storylet_id` |
| `missed_window` | R | beat id, to `missed_window_event_id` |
| `successor` | O | exit id, to `successor_transition_id` (absent only in the ending scene) |
| `observed_by` | R | claim ids, the full list, in order, to `observation_knowledge_ids` |
| `completes_scene` | O [true] | `completes_scene` |

Variant `outcome: {id, advantages, costs?}` gives `IncidentOutcome(id, storylet_id,
realization_id, advantages, costs)`. The outcome `id` is written (6 of 10 differ from
the first advantage, checked).

```yaml
incidents:
  - id: i_2c_rebecca_corridor
    reveal: michelle_changes_the_choice
    outcomes: [transmit, rescue]
    recovery: michelles_route_arrives
    missed_window: purge_window_2c
    successor: t_2c_3a
    observed_by: [k_sl_2c_c_r1, k_sl_2c_d_r3, k_sl_2c_d_r4]
# on the variant:
#   outcome: {id: committed_to_transmit, advantages: [committed_to_transmit], costs: [detention_sectors_sealed]}
```

### 4.12 `entry_claims`

A list. Each entry is a claim (keys as in 4.8, without `when`, `text`,
`commits_subset`) with `source = {scene_entry}` and `establishes =
{scene_<id>_entry_known: true}`. The compiler declares that fact with the purpose
"The safe opening frame for scene <ID> has been established." (all nine live
entry facts use this text, checked). Matcher fields come from the match file
(`k_scene_3c_entry` has `leak_terms: []`; the others are absent).

```yaml
entry_claims:
  - claim_id: k_scene_1b_entry
    says: The park is an immediate place of pursuit and uncertainty.
    entities: [kristin, los_angeles_park]
    audience: public
  - claim_id: k_1b_stranger_evasion
    says: "I won't tell you that. Keep your voice down; patrols are nearby."
    audience: {kind: characters, character_ids: [brandon]}
```

### 4.13 `exit`

| Key | R/O | Lands in |
| --- | --- | --- |
| `id` | R | `Transition.id`; listed in `SceneMetadata.transition_ids` |
| `to` | R | `target_scene_id` |
| `priority` | R | `priority` |
| `when_all` | R | `triggers` (each `equals: true`) |
| `needs` | O [] | `required_dependencies` (3); the four live dependencies migrate as `exists` |
| `bridge` | R | `SceneMetadata.bridge_text[id]` |

### 4.14 `ending` (only in the file of the last scene in `story.scenes`)

`{when, text, additions: [{when (all true), text}], marker}` to `StoryEnding(scene_id
= this scene, when, text, variants, marker)`. Every addition whose facts hold is
appended (`engine.py:807`). The ending sits in 3C's file, not the root: its scene is
fixed, and prose stays beside the scene that delivers it (the 2C draft left this
open).

### 4.15 The 13 proposed additions of the 2C-to-3A draft

| # | Addition | Result | Reason |
| --- | --- | --- | --- |
| 1 | Commit-only variant (withdrawn) | **Accept** | `SL-3C-F-R1` is a live realization with no claim. A variant without `claim_id` |
| 2 | `commits_common` | **Accept** | Merges into every variant. Operation order differs from legacy; allowed as `op_order` (no two facts in any operation list share an on-assert entity, checked) |
| 3 | `outcome` on a variant | **Accept** | Advantages and costs are not derivable from commits (1C `secure_route` commits `trust_brandon`, which is neither); the loader already rejects an outcome fact the variant does not commit |
| 4 | `incidents` block | **Change** | `observed_by` lists claim ids in full and in order. The draft's "reveal ids plus outcome claims added by the compiler" cannot reproduce the order (2B and 3C interleave) |
| 5 | `internal_claims` | **Change** | Renamed `extra_claims`; four live realizations need it (`SL-2A-D-R1` with three claims, `SL-2B-D-R1`, `SL-2C-E-R1`, `SL-3C-H-R1`), and one extra claim is public. Whether such records should be claims at all is a story change outside parity |
| 6 | Passage list in `text` | **Change** | `text` plus `text_when`: claim variants select one-of, not first match |
| 7 | `helps_exit` at reveal level | **Accept** | As one of the reveal defaults; uniform in 64 of 68 storylets |
| 8 | `delivery` on a fact | **Change** | Add optional `scene` (2 of 48 differ); `must_convey` moves to the match file |
| 9 | `entry_claim`, generated entry fact | **Change** | `entry_claims` list; `k_1b_stranger_evasion` fits |
| 10 | `claim` on a bridge entry | **Accept** | |
| 11 | `turns: {min, nudge, handoff}` | **Accept** | |
| 12 | `note` on a beat | **Accept** | Reader-only; never reaches `StoryPackage` (fixture F26) |
| 13 | Root `catalog` (ending, connections, guards, protected knowledge, entities) | **Change** | Split into `story.yaml` (identity, order, story text) and `catalog.yaml` (world records, unplaced facts). The ending goes to 3C's scene file |

### 4.16 `order`

The optional `order` mapping is the last top-level key in a scene file. It may
contain `storylets`, `deliveries`, `knowledge`, and `pacing_events`, each a list
of IDs belonging to that scene's records of the named kind (storylet IDs,
delivery fact IDs, claim IDs, or pacing event IDs). The compiler first builds
each collection in its natural order, then places the listed records first in
the scene's existing block; unlisted records retain their natural relative
order after them. The scene block keeps its position among the other scenes'
blocks. Layer 2 reports `L2.order_id` for an ID that is not a record of that
kind in the scene or for a duplicate ID.

## 5. Derivation rules

Each rule names what was run against the loaded package. "Unchecked" means no
script compared it.

| # | Rule | Reproduces legacy? |
| --- | --- | --- |
| 1 | Claim `establishes` defaults to the source's compiled commits; `commits_subset` declares less | **Checked.** 112 sourced claims: 96 equal as sets (93 in the same order; `k_sl_1a_b_r1`, `k_sl_2b_b_r4`, `k_sl_2b_b_r5` reordered), 16 strict subsets (9 realization, 7 bridge). The 3 reorders are `op_order` differences |
| 2 | `commits_common` merged into each variant's commits | **Checked** in the 2C draft (sets equal); order differs (`op_order`). Checked here: in every operation list and claim, no two facts have on-assert effects on the same entity (0 collisions) |
| 3 | Incident outcomes from the named variant | **Checked** 10 of 10: `storylet_id` and `realization_id` follow from the variant; advantages and costs are a written subset of its commits; `id` is written |
| 4 | `observation_knowledge_ids` | **Checked:** every incident's list contains its outcome claims (5 of 5); order not derivable, so written |
| 5 | `KnowledgeCatalog.facts` and `WorldSource.facts` generated | **Checked:** 177 distinct facts in both. Legacy `world.facts` has 178 entries (`processing_numbers_copied` twice) and a different order. Order matters for `pending_world_effects` (`world_model.py:82`) among on-assert facts that touch one entity: 8 such pairs live; 7 keep their order under story order, one (`relay_open` 3B before `brandon_identified` 1B) inverts (review entry) |
| 6 | Fact declaring scene = first setting scene in story order | **Checked:** 164 facts have a setter (route operations, bridge commits, pacing effects, delivery costs, entry facts); `trust_brandon` is set in 1B and 1C and goes to 1B; no fact is read before its first setter; 13 have neither setter nor reader (catalog `unplaced_facts`) |
| 7 | `FactDelivery.scene_id` defaults to the declaring scene | **Checked:** 46 of 48; 2 written explicitly |
| 8 | `WorldSource.fact_effects` from `on_assert` | Unchecked (a copy; 34 facts) |
| 9 | Entry fact and its purpose | **Checked:** 9 of 9 use the same sentence |
| 10 | Scene `participants` and `items` | **Not derivable (checked).** Placements plus companions plus claim entities plus protagonist miss 1 id in 5 scenes and add 1 in 4; item order differs from placement order in 4. Written explicitly |
| 11 | `Storylet` record from the reveal | **Checked.** `Source beats` renders 68 of 68; `Allowed scene` 65 of 68 (3 use `notes.allowed_scene`); `Pacing window` 65 of 68 (the other 3 contain the next heading, a parser leak); title 65 of 68 (3 drifted from routes); window 67 of 68 (`SL-3C-E` drifted: 0/14/14 vs 0/8/13; the runtime uses the route window, `engine.py:1325`) |
| 12 | Reveal-level defaults | **Checked** on the 30 storylets with more than one claim: `audience` uniform in 26, `entities` 24, `reach` 28, `relevance` 27, `voiceable` 27, `repeatable` 29, `earn_when` 6; `helps_exit` 64 of 68; `boundaries` 68 of 68 |
| 13 | Placement routing by entity kind | **Checked:** 9 of 9 scenes |
| 14 | Transitions, `transition_ids`, `bridge_text` from `exit`; `SceneFrame` and `ScenePacing` from the header | Unchecked here (the 2C draft compared 2C and 3A) |
| 15 | `Character` records | **Checked:** all 9 NPCs have `narrator_bio`, so `Character.bio = narrator_bio`; the order list is unchecked |

Rejected as derivations (each would change the package): `relevance` from
`entities` (61 of 122 equal); claim `when` from `available_while` (73 of 100);
`intent` from `says` (10 of 100); `Dramatic purpose` from `pressure_role` (23 of
68); participants from placements (rule 10).

## 6. Pass 2: the lexicon

Optional. A scene uses it only when its match file says `lexicon: true`.

### 6.1 `lexicon.yaml`

```yaml
schema: 1
entities:                          # key must be a catalog entity id
  memory_card:
    names: [memory card, card, "Michelle's card", the card]
    hidden_names: [hidden card, hidden memory card]
  michelle_drawer:
    names: [drawer, KMS, workstation, "drawer's"]
concepts:                          # named phrases that are not world things
  dead_drop:
    names: [dead drop, exchange point]
verb_classes:                      # story classes; compile-time lists only
  connect:
    words: [plug, insert, connect]
```

- **Lexicon names are matcher-only.** They never change catalog `name`, `aliases`
  or `scoped_aliases`, which the runtime reads for reference resolution.
- **Engine classes** have reserved ids: `look_closely`, `read`, `take`, `position`,
  `open`, `talk` (the six sets in `candidate_matcher.py:48-92`). `$look_closely`
  expands to that set, sorted. They cannot be redefined.
- **A story verb class adds no runtime synonym behavior.** It is a named list
  expanded at compile time.
- Ids are one namespace across `entities`, `concepts` and `verb_classes`.
  No entry refers to another entry, so there are no cycles.

### 6.2 What a lexicon may replace

Only these, and only in a lexicon-on match file: each group of
`claims.<id>.action_evidence` and `.must_convey`, `claims.<id>.leak_terms`,
`claims.<id>.aliases`, each group of `deliveries.<fact>.must_convey`, and the same
fields in `shared`. Nothing in a scene file, the catalog or `story.yaml` (passages,
`says`, `earn_when`, entity names, guard terms, protected names) accepts a
reference.

A derived value is a map; a plain list is explicit and stays as in pass 1:

```yaml
schema: 1
scene: 1A
lexicon: true
claims:
  k_sl_1a_b_r1:
    aliases: [continuity initiative known, michelle warning known, michelle abduction suspicion, michelle lead actionable]
    action_evidence:
      - {from: [$read, $connect], add: [inspect, open, check]}
      - {from: [$memory_card], drop: ["Michelle's card", the card]}
      - [file, files, saved file, saved files, card file, card files, laptop]      # explicit group
    must_convey:
      - {from: [$memory_card], drop: ["Michelle's card", the card]}
      - {from: [$dead_drop]}
    leak_terms: {from: [$memory_card.all], add: [memory card recovered]}
```

**Expansion of one derived value:** `$id` gives the entity or concept `names` or the
class `words`; `$id.hidden` gives `hidden_names`; `$id.all` gives both. Take the
optional `first` entry, then the `from` references in order, then `add`; remove
every entry equal (casefold) to a `drop` entry; remove later casefold duplicates. A
`drop` entry that removes nothing is a layer 2 error. `first` exists for
`must_convey`, whose group[0] is shown to the model: `{first: "memory card", from:
[$memory_card]}`. It counts as an added entry only if no reference produces it.

(The example above is illustrative. It was not run through the equivalence check.)

The plan's slot sketch (`earned_by`, `conveys`, `{under: drawer}`) is not adopted:
references inside the existing list shapes keep pass 1 and pass 2 the same shape,
so a worker converts one group at a time, and positional templates cannot
reproduce phrases like `beneath the KMS drawer` without an `add` per case.

### 6.3 Expand-back and the lock file

The compiled package never takes a derived list directly. It takes the **lock**:

- `scenes/<id>.match.lock.yaml` holds, for every derived value in the scene, the
  list the package receives. It is generated by `story lock <scene>` and never
  edited.
- On build, for each derived value the compiler computes the expansion `E` and
  reads the lock entry `L`. If `E` is equivalent to `L` (below), it emits `L`. If
  not, or if `L` is missing, the build fails with `L2.lock_stale`, naming the claim
  and field.
- `story lock <scene> --adopt` creates the first lock from the pass-1 lists. It
  refuses unless every `E` is equivalent to the pass-1 list it replaces, and prints
  each mismatch as the `add:`/`drop:` needed.
- After a lexicon edit, `story lock <scene>` rewrites only the entries that are no
  longer equivalent, with `E` itself. That lock diff is the reviewed change. Since
  one lexicon edit can touch many scenes, `story lock --all` reports every scene it
  would change.

**Equivalence per field** (from how the engine reads each field):

| Field | Equivalent when | Basis |
| --- | --- | --- |
| `action_evidence` group | Same closure: the casefolded, word-normalized entries plus every engine class any entry belongs to (plus the look operations for `look_closely`). Same number of groups, compared as a multiset | `_matches_one_group` builds exactly this set; `_matches_all` ignores group order; the group count breaks ties (`candidate_matcher.py:207-237`) |
| `must_convey` group | Same group order, same group[0] byte for byte, the rest equal as casefolded sets | group[0] goes into the prompt (`cloudflare.py:1731`) and into miss reports; matching casefolds (`validation.py:84-120`) |
| `leak_terms` | Equal casefolded sets, and `None`/`()`/list kind unchanged | read only through the casefolded index (`loader.py:395`) |
| `aliases` | Equal, in order | consumers not fully traced; kept strict |

**Omitting the layer changes nothing.** Three properties, each a fixture (F17 to
F19): a lexicon-off scene compiles without opening `lexicon.yaml`, even a malformed
one; `story expand <scene>` writes plain lists equal to the lock and sets
`lexicon: false`, and compiling that result with `lexicon.yaml` deleted gives the
same canonical package; adoption changes no package byte, because the first lock
is the pass-1 list.

### 6.4 Override ratio (the one-third rule)

For each scene and field kind (`action_evidence`, `must_convey`, `leak_terms`,
`aliases`): `ratio = (added + dropped) / expanded entries`, summed over that
scene's derived values of that kind. Plain lists do not count. Output, as a table
and as JSON:

```text
scene field           derived  expanded  added  dropped  ratio  status
1A    action_evidence 12       140       9      4        0.09   ok
1A    must_convey     9        96        31     6        0.39   over
```

`over` (ratio above 1/3) fails the pass-2 gate for that scene. The fix is to write
that field kind as plain lists in that scene. The report always runs; it does not
fail a normal build.

### 6.5 Plural twins (optional)

`plural_twins: true` in a match file lets an entry in `add` or in a lexicon name end
in `(s)` or `(es)` on its last word: `saved file(s)` expands to `saved file`,
`saved files`, singular first. With the option off, `(` in an entry is a layer 1
error (no live entry contains `(s)`, checked). Live counts: 283 twin entries in
`action_evidence` (13%; 3B 24%, 3C 18%, 1A 4%); 254 are multi-word, which the
matcher does not fold; 29 are single words over three letters, which the matcher
already folds (`candidate_matcher.py:251`), so they are redundant in matching but
kept by the lock. Plural twins are the only pass-2 tool proposed for 3A to 3C, and
they go through the same lock and parity check.

## 7. Layer 1, 2 and 3 checks

Every check has a stable name and a diagnostic with source file, record address
(section 8) and field. Layers 1 and 2 fail the build; layer 3 reports only (D3).
All loader checks that run on the built `StoryPackage` today (`loader.py:1713-1724`,
about 200) run unchanged after compilation and are not repeated here.

| Name | Layer | What |
| --- | --- | --- |
| `L1.duplicate_key` | 1 | a repeated key in any mapping of any source file |
| `L1.unknown_key`, `L1.missing_key`, `L1.type`, `L1.enum`, `L1.id_pattern` | 1 | shape, per the tables in section 4 |
| `L1.condition_value` | 1 | `false` in an all-true field; `retract` in pacing `sets` |
| `L1.passage_list` | 1 | a `say` list whose last entry has a `when`, or a guarded entry after an unguarded one |
| `L1.claim_keys_without_claim` | 1 | claim keys on a variant with no `claim_id` |
| `L1.lexicon_off` | 1 | a `{from:}` value or `$` reference in a match file without `lexicon: true` |
| `L1.plural_off` | 1 | `(s)`/`(es)` without `plural_twins: true` |
| `L1.match_scene` | 1 | a match file's `scene` differs from its scene file |
| `L2.duplicate_id` | 2 | an id defined twice within a kind, story-wide (fact, claim, beat, exit, entity, storylet, realization, reveal handle, incident, bridge, outline anchor) |
| `L2.dangling_ref` | 2 | any id, part name, `use` block, outline id or lexicon reference that does not resolve |
| `L2.fact_one_owner` | 2 | a fact declared in two places (scene files and catalog) |
| `L2.fact_declaring_scene` | 2 | a fact's declaring scene is not its first setting scene (or, with no setter, its first reading scene). The message prints the declaration block and the scene file to move it to |
| `L2.unplaced_fact` | 2 | a fact in `unplaced_facts` that something sets or reads |
| `L2.undeclared_fact` | 2 | a fact used but declared nowhere |
| `L2.claim_authorized` | 2 | `commits_subset` not a subset of its source's compiled commits |
| `L2.override_add_only` | 2 | a claim's `leak_terms` over a `shared` value written as anything but `{add: [...]}`; a variant `boundaries` key (reveal-level only) |
| `L2.match_coverage` | 2 | a claim with no match entry, a match entry with no claim, a `delivery` with no `deliveries` entry |
| `L2.incident_observes_outcomes` | 2 | `observed_by` lacks an outcome variant's claim |
| `L2.scene_scope` | 2 | `helps_exit` or `successor` naming another scene's exit; `reach` or `needs` items absent from the scene's `items`/`participants` (not yet verified against the loader) |
| `L2.ending_scene` | 2 | `ending` outside the last scene of `story.scenes` |
| `L2.ownership` | 2 | the manifest marks a scene `compiled` and a legacy file still defines it; a record id defined on both sides (names both sources) |
| `L2.lock_stale` | 2 | pass 2: a derived value not equivalent to its lock entry, or no lock entry |
| `L2.drop_unused` | 2 | pass 2: a `drop` entry that removes nothing |
| `L2.cycles` | 2 | transitions and prerequisite/reveal cycles are inherited from the loader; `use` never chains (a shared block cannot `use`), so it cannot cycle |
| `L3.no_producer` | 3 | existing rule |
| `L3.read_before_set` | 3 | a fact read in a scene earlier than any scene that sets it |
| `L3.unplaced_fact` | 3 | one result per entry of `unplaced_facts` |
| `L3.need_vs_custody` | 3 | a stated `held` need that the custody inference does not support, or the reverse |
| `L3.overlapping_text_when` | 3 | two `text_when` entries of one claim can hold together (the engine returns `AMBIGUOUS`) |
| `L3.unused_part`, `L3.unused_shared`, `L3.unused_lexicon_entry` | 3 | defined, never used |
| `L3.save_identity` | 3 | a frozen id from the save-identity manifest missing from the package and not in `retired_ids` (a `UserWarning` in a test and a script, never at load or play) |
| `override_ratio` | report | 6.4; fails only the pass-2 gate |

## 8. Test lookup contract and story CLI

### 8.1 Addresses

```text
address := kind ":" id [ "." field { "." field | "[" index "]" } ]
```

| Kind | Id | Resolves against |
| --- | --- | --- |
| `scene` | `1A` | header, `entry`, `entry_additions[i].text`, `situation`, `pressure` |
| `fact` | fact id | `purpose` |
| `delivery` | fact id | `fallback_text`, `cue_text`, `escalation_text`, `must_convey` |
| `claim` | claim id | `says`, `text`, `text_when[i].text`, `speaker_text.<speaker>`, `aliases`, `action_evidence`, `must_convey`, `leak_terms`, `earn_when` |
| `beat` | pacing event id | `say[i].text` (`[-1]` is the unguarded default), `note` |
| `exit` | transition id | `bridge` |
| `bridge` | event id | `fallback_text`, `delivery_text`, `note` |
| `outline` | `1A.1` | `title`, `prose`, `details[i]` |
| `ending` | `story` | `text`, `additions[i].text`, `marker` |
| `entity` | entity id | catalog fields |
| `reveal` | handle | `title`, `guidance.pressure_role`, `notes.<section>` |
| `variant` | `<reveal>/<key>` | `intent`, `text` |
| `part` | `<reveal>/<name>` | the part text |
| `outcome` | `<incident>/<outcome id>` | `advantages`, `costs` |

Kinds are needed because ids collide across kinds (four outcome ids equal fact
ids, checked).

### 8.2 Python lookup

```python
story_text(address: str, *, package: StoryPackage | None = None, source: bool = False) -> str
story_value(address: str, *, package: StoryPackage | None = None) -> object
```

- `story_text` returns the string the engine receives: the compiled `StoryPackage`
  value, with `{parts}` already pasted in. `claim:k_sl_1a_b_r0.text` returns the
  full `delivery_text`; `claim:k_sl_2c_d_r3.text_when[0].text` returns
  `delivery_variants[0].text`.
- `source=True` returns the authored template (`"{find_lead} Her laptop is still out
  in her truck."`). `part:find_card/find_lead` returns the part alone, for a test
  that asserts a sentence appears.
- `story_value` returns tuples and models as the package holds them.
- An unknown address raises `KeyError` naming the address. A field that is unset
  raises `KeyError`, not `None`.
- Package-level kinds (`scene`, `fact`, `delivery`, `claim`, `beat`, `exit`,
  `bridge`, `outline` by beat id, `ending`, `entity`) resolve against a legacy
  package too, so tests can migrate before a scene flips. `reveal`, `variant`,
  `part` and `outcome` need compiled sources.
- Without `package`, the default story package is loaded once through the normal
  loader (cached). No network, no model call.

### 8.3 `story` CLI

All commands take `--story <id>` (default `continuity-initiative`) and `--json`.

| Command | Reads | Writes | Contract |
| --- | --- | --- | --- |
| `story show <address>` | source files, compiled package | nothing | Prints the record as authored (owning file, YAML path), its match entry, generated producers and consumers, and test files that mention its id. Exit 2 on an unknown address |
| `story set <address> <yaml>`, `--add <v>`, `--drop <v>` | owning source file | exactly one field in one file | Round-trip edit keeping comments and order. Refuses generated values (lock entries, entry facts, generated sections) and frozen-id fields. Compiles the affected scene and runs layers 1 and 2; on failure restores the file and prints the diagnostics. Prints the file diff |
| `story rename <kind>:<old> <new>` | all source files | every reference in source files | Free id: rewrites all references. Frozen id: refuses unless `--retire "<reason>"`, which also adds the old id to `retired_ids`. Lists tests and non-source readers that mention the old id; never edits tests or frozen evidence |
| `story impact <address>` | compiled package | nothing | The existing impact report, addressed the same way |
| `story new <kind> ...` | scene file | one new record | Writes the record with every id it needs (`claim_id`, `realization_id`, `anchor`) so the compiler never generates one |
| `story fmt [<scene>]` | source files | formatting only | Never changes a scalar's value |
| `story lock`, `story expand` | match files, lexicon | lock, match file | 6.3 |
| `story parity <scene>` | legacy package, sources | diff output | Section 9 |

## 9. Parity diff spec

**Inputs.** `L` = the package from the legacy loader at the named snapshot (or the
current legacy files during migration). `C` = the package with the scene compiled
from sources. For pass 2, `L` is the pass-1 compiled package of that scene.

**Canonical form.** `model_dump(mode="json", by_alias=True)` of both packages.
`knowledge_indexes` is compared whole: a difference there with no upstream
difference is a compiler bug, never reviewable.

**Scope of one scene.** Its `Scene` (metadata, beats, opening beat, prose), its
`SceneFrame`, `ScenePacing`, outgoing transitions, pacing events, `Storylet` and
`StoryletRoute` records, bridge and resolution events, claims (`available_in_scenes`
equals the scene), deliveries (`scene_id` equals the scene), incident, the facts it
declares (definitions and `fact_effects`), and the ending if it is the ending scene.
The catalog scope: world entities, kinds, props, connections, protected knowledge,
disclosure guards, characters, genre, ids, budget, scene chain.

**What is compared.** Every field in scope. That covers IDs, predicates (`requires`,
`when`, `triggers`, `activation_conditions`, activation rules), effects
(`operations`, `establishes`, `effects`, `costs`, `consequences`), passages (every
text field, byte for byte), placements, disclosure scopes (`audience`,
`protected_knowledge_boundaries`, `leak_terms`, `voiceable`, `speaker_text`, guards)
and matcher lists (`action_evidence`, `must_convey`, `aliases`).

**Keying.** Collections compare by id, not index: `knowledge[k_sl_1a_b_r0]`,
`storylet_routes.storylets[SL-1A-E].realizations[SL-1A-E-R1]`,
`pacing.events[patrol_leaves_1a]`, `deliveries[continuity_initiative_known]`,
`world.facts[memory_card_recovered]`. Position is compared separately (classes
below).

**Difference classes.**

| Class | Applies when | Needs a review entry? |
| --- | --- | --- |
| `op_order` | Two operation lists hold the same set, all facts distinct, and no two facts have on-assert effects on one entity | No (proved by the tool) |
| `condition_order` | Two predicate tuples hold the same set | No (evaluated with `all()`) |
| `collection_order` | Applies only when a keyed record moves ONLY ACROSS SCENES; its relative order among same-scene records is unchanged. Moving a record from one scene's block to another's position is still allowed; reordering records of the same scene is not. For `world.facts`, every order-sensitive pair (5, rule 5) keeps its order | No |
| `reader_only` | The field has no runtime reader: `Scene.prose`, `Storylet.title`, `Storylet` window, `Storylet.sections` (fixed list in the tool) | Yes |
| `dedupe` | A duplicate entry removed (`world.facts`) | Yes |
| `whitespace` | Texts equal after collapsing whitespace runs and trimming | Yes |
| `data_bug` | Legacy owners disagreed; the compiled value keeps one owner's value | Yes |
| `representation` | Any other reviewed change, with a reason | Yes |

Anything not in a class is unreviewable and fails.

**Known review entries for the first full conversion** (from section 5): the
`world.facts` duplicate; the `relay_open`/`brandon_identified` order pair; the three
`Storylet` titles (`SL-1A-F`, `SL-3A-D`, `SL-3C-C`); the `SL-3C-E` window; the three
`Pacing window` parser leaks (`SL-1A-K`, `SL-1C-G`, `SL-3A-I`); every scene's
`Scene.prose` rendering, with the act intros leaving 1C and 2C.

**Review file.**

```yaml
schema: 1
scene: 1A
differences:
  - path: storylets[SL-1A-F].title
    class: reader_only
    legacy: 3f2a9c01d4e7      # first 12 hex of sha256 of the canonical JSON value
    compiled: 8b41e0c2a9f3
    reason: storylets.md title drifted from storylet-routes.yaml; the route title is kept.
```

An entry matches only when path, class and both digests match. A later change at
the same path makes it unreviewed again.

**Output.** One JSON object per difference, then a summary:

```json
{"scene": "1A", "path": "knowledge[k_sl_1a_b_r1].establishes", "class": "op_order", "reviewed": true, "legacy": "…", "compiled": "…"}
{"scene": "1A", "summary": {"records": 61, "differences": 5, "auto": 3, "reviewed": 2, "unreviewed": 0, "pass": true}}
```

`story parity <scene>` exits 0 when `unreviewed` is 0 and the knowledge indexes are
equal; 1 otherwise; 2 on a compile error. The Phase 2 gate also requires the
deterministic runtime traces to match the baseline; that is a separate check that
runs on the compiled package.

## 10. Fixtures plan (Phase 1 item 6)

Fixtures live in `tests/fixtures/story_source/`. Each is a small source tree cut
from continuity-initiative records (the fixtures decision), changed only where a
two-scene story needs it (for example the exit target). F01 is the base; the others
are F01 plus one change. Tests for each can be written before the compiler.

| # | Fixture | Property it exercises | Expected |
| --- | --- | --- | --- |
| F01 | `mini_ok` | 1A slice (`find_card` with both variants, the patrol beats, `t_1a_1b`, the card delivery) plus a second scene with the 2C incident, two entry claims and the ending. Covers claims, protected material and audience scoping, pacing, an incident with outcomes, a cross-scene dependency | Compiles; every inherited loader check passes; safety tests pass |
| F02 | `dup_key` | a repeated key in a variant | `L1.duplicate_key` |
| F03 | `unknown_key` | `done_when` on a reveal | `L1.unknown_key` |
| F04 | `fact_two_owners` | one fact in two scene files | `L2.fact_one_owner` |
| F05 | `fact_wrong_scene` | a fact declared in scene 2 but first set in 1A | `L2.fact_declaring_scene`, message names the block and target file |
| F06 | `claim_unauthorized` | `commits_subset` with a fact the variant does not commit | `L2.claim_authorized` |
| F07 | `leak_narrowed` | a claim replacing its shared `leak_terms` with a shorter list; and a variant `boundaries` key | `L2.override_add_only` twice |
| F08 | `dangling` | `{missing}` part, `use: nope`, unknown fact in `when`, exit to an unknown scene | four `L2.dangling_ref` |
| F09 | `cycles` | a two-scene transition cycle; a claim requiring its own fact | inherited loader errors |
| F10 | `outcome_not_committed` | an advantage the variant does not commit | inherited loader error |
| F11 | `observes_missing` | `observed_by` without an outcome claim | `L2.incident_observes_outcomes` |
| F12 | `passage_rules` | `say` with two matching entries; `text_when` with two holding; two entry additions | first `say` wins; `AMBIGUOUS`; both additions appended |
| F13 | `leak_null_vs_empty` | one claim without `leak_terms`, one with `[]` | `None` vs `()`; the leak index differs exactly by the alias forms |
| F14 | `two_owners_manifest` | scene marked `compiled` while legacy files define it | `L2.ownership` naming both sources |
| F15 | `manifest_absent` | sources present, no manifest | package equals the legacy one |
| F16 | `claim_order` | match file order differs from reveal order | claim order follows the match file |
| F17 | `lexicon_off_ignored` | malformed `lexicon.yaml`, every scene `lexicon: false` | compiles |
| F18 | `lexicon_ref_when_off` | a `$memory_card` reference without `lexicon: true` | `L1.lexicon_off` |
| F19 | `lexicon_roundtrip` | derived lists equivalent to the lock | package equals F01; `story expand` then compile with no lexicon gives the same canonical JSON |
| F20 | `lexicon_stale` | a lexicon name added, lock not regenerated | `L2.lock_stale` naming claim and field |
| F21 | `override_ratio` | a field with 2 of 5 entries added | ratio 0.4, status `over`, pass-2 gate fails, build passes |
| F22 | `plural_twins` | `saved file(s)` with the option on and off | two entries; `L1.plural_off` |
| F23 | `parity_classes` | legacy/compiled package pairs seeded with one difference of each class | each classified correctly; unreviewed ones fail |
| F24 | `review_digest` | a review entry whose compiled digest no longer matches | unreviewed, fail |
| F25 | `save_identity` | a frozen claim id removed; then listed in `retired_ids` | `UserWarning` naming the id; then silent |
| F26 | `review_isolation` | a beat `note` and a bridge `note` with unique marker text | the marker appears nowhere in the package dump or narrator inputs |
| F27 | `examples` | accept/reject lines for `k_sl_1a_b_r0`, one failing accept | the checker runs the real matcher, names the failing group and the smallest word to add |
| F28 | `lookup` | one address of every kind | each resolves; parts pasted in; `source=True` returns the template; unknown address raises `KeyError` |
| F29 | `typed_needs` | `exists`, `held`, `reach` and `not` needs on an exit | only `exists` and `held` reach `required_dependencies` |
| F30 | `claimless_variant` | a variant with no `claim_id` | a realization with no claim |
| F31 | `deterministic` | compile twice, in two processes | identical canonical JSON; the digest covers schema version, compiler version and every source file |

### 10.1 API names the fixtures settled (2026-11-16)

Fixtures round 2 had to assume these; the five `tests/story_source/ambiguities_*.md`
files list each case. Settled here so the validator and compiler are written to them.
All live in `storygame.story_source` unless noted.

| Name | Contract |
| --- | --- |
| `Diagnostic.address`, `.field` | `address` is a section 8.1 address string; `field` is the field key. Tests assert both are non-empty and that the message names the id; they never assert exact message wording. Order of several diagnostics is not fixed; tests compare as multisets |
| Loader errors after compile | A cycle in transitions or prerequisites is `L2.cycles`; any other check inherited from `loader.py` is wrapped as one diagnostic named `LOADER` carrying the loader message. `compile_source_tree` raises `SourceError` for both; only the name `L2.cycles` is asserted |
| `check_parity(legacy, compiled, *, reviews=None)` | Returns a report with `differences` (a list of the section 9 JSON objects) and `summary` (`records`, `differences`, `auto`, `reviewed`, `unreviewed`, `pass`). A stale compiled digest in a review entry counts as `unreviewed` |
| `check_save_identity(package, manifest, *, retired_ids=None)` | Emits one `UserWarning` per frozen id missing from the package and not retired; silent otherwise. Never raises |
| `override_ratio(root)`, `pass2_gate(root)` | `override_ratio` returns one row per claim field with `added`, `dropped`, `expanded`, `ratio`, `status` (`ok` or `over`); `pass2_gate` returns `False` when any row is `over`. `check_source_tree` does not depend on either |
| `check_examples(root, examples_path)` | Returns a list of failures, empty when every line behaves. A failure has `claim_id`, `kind` (`accept` or `reject`), `line`, `group` (the matcher group index that failed) and `missing` (the smallest word to add to pass it). It runs the real matcher |
| Examples file location | `tests/fixtures/story_examples/<story>/<scene>.yaml` (section 2 layout), never inside the source tree. Keys `schema`, `scene`, `claims`, `shared`; each claim has `accept` and `reject` lists of player lines |
| `storygame.story_cli.main(argv) -> int` | The `story` CLI entry point; returns the exit code. The source root is the current directory when it holds `story.yaml`, else `data/stories/<story>/source` |
| `source_digest(root) -> str` | sha256 over the schema version, `COMPILER_VERSION` and every source file's relative path and bytes in sorted path order. Canonical package JSON is `model_dump(mode="json", by_alias=True)` with sorted keys |
| Claimless variant | The realization compiles with no claim; no knowledge entry names it |
| Required dependencies | Compiled order and duplicates are not fixed; tests compare as sets |

## 11. Questions for Brandon (answered)

**Decided 2026-11-16 (Brandon): all five recommendations accepted as written.** Each
was checked against the code before he answered; the checks changed two wordings, noted
under Q3 and Q5.

- **Q1. The 13 facts nothing sets or reads** (for example `false_identities_ready`,
  `purge_transfers_underway`; `facility_perimeter_reached` even has an on-assert
  effect). Keep them, or delete them? *Recommendation:* keep them in
  `catalog.unplaced_facts` for parity (fact ids are frozen), with a layer 3 result
  each; delete any as a separate story change. **Decided: keep.** Check: 12 appear
  nowhere outside their declarations; the 13th, `facility_perimeter_reached`, has an
  on-assert effect but no setter. `tests/test_markdown_story_package.py` already lists
  all 13 as "retained world declarations from the retired Act 2 preparation/search
  beats", so deleting any also means editing that test.
- **Q2. The plan's pass-2 rule that `purpose`, `intent` and `says` collapse into one
  sentence.** It cannot reproduce the package (`intent == says` in 10 of 100
  claims). *Recommendation:* remove it from pass 2. If wanted, do it later as a
  reviewed prose edit per scene. **Decided: removed.** The dark factory plan's pass 2
  no longer lists it.
- **Q3. The `storylets.md` sections** (Dramatic purpose, Possible realizations,
  Effects and the rest). No code reads them. Keep them verbatim as reveal `notes`,
  or drop them? *Recommendation:* keep them in pass 1, so parity is exact and no
  author text is lost; decide later which ones only restate fields. **Decided: keep
  as `notes` in pass 1.** Wording correction: the loader does read this file's
  headings (they must match the route file's storylet list, `loader.py:964`) and its
  "Source beats" links (checked against `plot.md`). Only the text under the other
  sections is unread.
- **Q4. The 11 bridge texts under `fallback_realization`** that no code reads (the
  2C draft's question). *Recommendation:* keep them as reader-only `note`; making any
  a real `fallback_text` is a story change. **Decided: keep as `note`.** Checked: the
  11 bridge events carry only `fallback_realization`; the 5 resolution events carry
  both it and a read `fallback_text`. No Python reads the field.
- **Q5. `SL-3C-F-R1` has no claim** (Open the Surface Gates; commits
  `los_angeles_facility_lost`). Intended? *Recommendation:* the schema supports it,
  so leave it; review it with 3C's story work. **Decided: leave.** The resolution
  event for 3C already produces the same fact and carries the player-facing text, so
  the split looks deliberate; whether the storylet should show the player anything is
  a 3C story question. Correction: the package test names four "unmapped"
  realizations (`SL-2A-D-R1`, `SL-2B-D-R1`, `SL-2C-E-R1`, `SL-3C-F-R1`), but the first
  three have claims in `knowledge.yaml`. Only `SL-3C-F-R1` has none, so the test's
  list is stale.

## 12. What I checked by running code, and what I did not

Run with read-only scratch scripts (`TMPDIR=/tmp uv run python`, not committed) on
the package loaded from `data/stories/continuity-initiative` on this branch:

- Claim effects against their sources: 122 claims, 112 sourced, 96 equal sets (93
  ordered), 16 subsets, 10 entry; the 3 reordered claims by id.
- Realizations: 96; one with no claim (`SL-3C-F-R1`); four with several claims; all
  have operations; every operation is `assert` with value `True`; no duplicate fact
  in a list; no on-assert entity collision in any operation list or claim.
- Fact lists: 177 distinct; `world.facts` 178 entries with one duplicate; orders
  differ. First setting scene for every fact; 13 with no setter and no reader; one
  set in two scenes; none read before set. 8 order-sensitive on-assert pairs, one
  cross-scene inversion.
- Deliveries: 46 of 48 in the declaring scene.
- Incidents: outcome fields, outcome id versus first advantage, observation lists
  contain outcome claims, order not derivable.
- Entry claims: 10, the shared purpose sentence, `k_1b_stranger_evasion`'s audience,
  `k_scene_3c_entry`'s empty leak terms.
- Participants and items derivation (fails); placement routing by kind (holds).
- `Storylet` rendering: sections, titles, windows (numbers in section 5, rule 11).
- Reveal-level default uniformity (section 5, rule 12).
- Record order: within-scene claim order differs from reveal order in every scene;
  storylet routes and bridge events are scene-contiguous; events, claims and facts
  are not; four same-turn event ties.
- `Scene.prose` of 1C and 2C carries the next act's heading; no code reads whole
  `Scene.prose`; `package.storylets` is read only for `id`, `scene_id`,
  `source_links` (grep).
- `intent` versus `says` (10 of 100 equal); `says` never equals a fact purpose.
- ID collisions across kinds (four outcome ids equal fact ids).
- `leak_terms` kinds (98 `None`, 13 empty, 11 lists); no matcher entry starts with
  `$` or contains `(s)`; no passage contains a brace.
- `.plans/story-data-phase0/lexicon_plural_twins.py` (13% overall), and a split of
  twins into 254 multi-word and 29 single-word.

Read in code but not run: the three passage selection rules (`engine.py:1363`,
`delivery_text.py:35`, `engine.py:807`, `models.py:647`); the matcher closure and
group-count tie-break; `must_convey` group[0] in the prompt; the `leak_terms` index;
`pending_world_effects` order; the loader's existing outcome and `must_convey`
checks.

Not checked by anyone:

- That the runtime filters claims and pacing events by the current scene in every
  path, which `collection_order` relies on for cross-scene moves.
- Whether any consumer depends on `aliases` order or on fact-store insertion order.
- Whether today's duplicate `processing_numbers_copied` in `world.facts` applies
  its on-assert effects twice.
- `L2.scene_scope` against the loader (reach items and `helps_exit`, as plan item 10
  already notes).
- The `principal_characters` order against `plot.md` heading order; fact effects,
  transitions, frames and pacing windows for scenes other than 2C and 3A.
- Any parity diff at all: no compiler exists, so the "known review entries" list
  is a forecast from the measurements above, not a diff result.
- The 1A and 2C drafts' YAML against this contract's key names (they use
  `entry_variants`, `internal_claims`, `uses`, `done_when`; a converter renames).
