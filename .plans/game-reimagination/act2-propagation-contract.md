# Act 2 redesign ID contract

Scope: `data/stories/continuity-initiative`. `NEW` means the identifier does not
currently exist. Booleans below are story facts with initial value `false` unless
stated otherwise. The incident shape is the exact shape used by
`i_1c_freight_transfer`; loader rules require outcome advantages to be asserted by
their realization, disjoint advantages, a scene-local missed-window event and
transition, and a distinct recovery storylet.

## 1. Incidents.yaml entries

Lane 1 owns these entries and the referenced pacing events. Lane 2 must create the
new recovery routes and the realization IDs named here. The recovery storylet IDs
`SL-2A-RECOVERY`, `SL-2B-RECOVERY`, and `SL-2C-RECOVERY` are NEW; they are not
citations of existing storylets.

```yaml
incidents:
- id: i_2a_real_leak
  scene_id: 2A
  outcomes:
  - id: inspection_convincing
    storylet_id: SL-2A-C
    realization_id: SL-2A-C-R5
    advantages: [restricted_corridor_access]
    costs: []
  - id: inspection_doubted
    storylet_id: SL-2A-C
    realization_id: SL-2A-C-R6
    advantages: [restricted_corridor_access]
    costs: [cover_suspected]
  recovery_storylet_id: SL-2A-RECOVERY
  missed_window_event_id: inspection_window_2a
  successor_transition_id: t_2a_2b
  observation_knowledge_ids: [k_sl_2a_c_r5, k_sl_2a_c_r6]
  completes_scene: true
- id: i_2b_audit
  scene_id: 2B
  outcomes:
  - id: brandon_name_kept
    storylet_id: SL-2B-B
    realization_id: SL-2B-B-R4
    advantages: [brandon_name_kept]
    costs: []
  - id: brandon_name_erased
    storylet_id: SL-2B-B
    realization_id: SL-2B-B-R5
    advantages: [brandon_name_erased]
    costs: [evidence_gap_development_record]
  recovery_storylet_id: SL-2B-RECOVERY
  missed_window_event_id: audit_window_2b
  successor_transition_id: t_2b_2c
  observation_knowledge_ids: [k_sl_2b_b_r4, k_sl_2b_b_r5, k_sl_2b_c_r3]
  completes_scene: true
- id: i_2c_rebecca_corridor
  scene_id: 2C
  outcomes:
  - id: committed_to_transmit
    storylet_id: SL-2C-D
    realization_id: SL-2C-D-R3
    advantages: [committed_to_transmit]
    costs: [detention_sectors_sealed]
  - id: committed_to_rescue
    storylet_id: SL-2C-D
    realization_id: SL-2C-D-R4
    advantages: [committed_to_rescue]
    costs: [evidence_not_transmitted]
  recovery_storylet_id: SL-2C-RECOVERY
  missed_window_event_id: purge_window_2c
  successor_transition_id: t_2c_3a
  observation_knowledge_ids: [k_sl_2c_d_r3, k_sl_2c_d_r4]
  completes_scene: true
```

`inspection_window_2a`, `audit_window_2b`, `purge_window_2c`, the six knowledge
IDs, `SL-2A-RECOVERY`, `SL-2B-RECOVERY`, `SL-2C-RECOVERY`, and all R5/R6/R3/R4
realization IDs above are NEW. The recovery routes must require the corresponding missed fact, default
2A to the doubted/under-watch path, default 2B to `brandon_name_kept`, and let
2C proceed neutrally through Michelle’s route without asserting either commitment.

## 2. Existing storylets and new route operations

Lane 2 owns this entire section, including route YAML and prose. Existing IDs are
kept where named; old realization IDs may be retired or rewritten only as stated.

### 2A

- `SL-2A-A` — CUT. Hideout exposition is bridge text; no scene beat. Retire
  `SL-2A-A-R1/R2` and its `brandon_prepared_before_event` operations.
- `SL-2A-B` — CUT. Cover construction is bridge text; no separate preparation
  storylet. Retire `SL-2A-B-R1/R2` and `false_identities_ready` operations here.
- `SL-2A-E` — CUT. Travel/reaching the facility is the new entry frame. Retire
  `SL-2A-E-R1` and its `facility_perimeter_reached` operation.
- `SL-2A-C` — KEEP and merge the real supervisor confrontation. Add NEW
  `SL-2A-C-R5`: convincing diagnosis; assert
  `restricted_corridor_access`, `rebecca_observing_infiltrators`, and
  `inspection_console_used`. Add NEW `SL-2A-C-R6`: vague/overlong diagnosis;
  assert `restricted_corridor_access`, `rebecca_observing_infiltrators`,
  `inspection_console_used`, and `cover_suspected`. Both are incident outcomes;
  R6 is the harsher 2B entry. `inspection_console_used` is NEW. Keep the
  console-limits sentence because 3B relies on it.

### 2B

- `SL-2B-A` — MERGE into `SL-2B-B`. The single first pull of Kristin’s file must
  establish `janus_known`, `janus_evidence`, `kristin_was_bait`, and
  `michelle_selected_for_resistance_influence` as the authored discovery permits;
  retire old A realizations and their separate search pacing.
- `SL-2B-B` — KEEP and merge the discovery plus whispered confrontation. Add NEW
  `SL-2B-B-R4`: keep Brandon’s name; assert `brandon_name_kept`,
  `brandon_janus_role_known`, `brandon_claimed_reform_motive`, `janus_evidence`,
  and `archive_crisis_understood`. Add NEW `SL-2B-B-R5`: erase his name; assert
  `brandon_name_erased`, `brandon_janus_role_known`,
  `brandon_claimed_reform_motive`, `janus_evidence`, and
  `archive_crisis_understood`; both outcomes assert/move/reveal the existing
  `copied_janus_files` item with Kristin. The erased record also asserts
  `evidence_gap_development_record`.
- `SL-2B-C` — KEEP as the Shelly reply, replacing corrupted-file reading. Add
  NEW `SL-2B-C-R3`: medical-terminal maintenance line, one reply, Michelle alive
  and active; assert `michelle_resistance_known`, `michelle_reply_received`,
  and `archive_crisis_understood`. `michelle_reply_received` is NEW. Do not
  reveal the uprising or broadcast solution here.

### 2C

- `SL-2C-A` — MERGE into `SL-2C-D`. Rebecca’s offer is the opening of the live
  negotiation; retain `rebecca_offer_active` and `antagonist_split_known` as
  operations in the merged route, not as a separate encounter.
- `SL-2C-B` — CUT. The tablet purge-order moment is the incident pressure event;
  retire its standalone `purge_clock_started` realization route.
- `SL-2C-C` — CUT. Do not restore an open-ended evidence/rescue debate; the
  commitment is made physically as the incident outcome. Retire both old C
  realizations.
- `SL-2C-D` — KEEP and merge Rebecca’s offer, purge tablet, Brandon’s apparent
  yes, physical commitment, and Michelle’s later route. Add NEW R3: assert
  `committed_to_transmit`, `detention_sectors_sealed`,
  `purge_clock_started`, `evidence_ready_to_transmit`,
  `combined_broadcast_rescue_plan_known`, and
  `rebecca_office_required_for_broadcast`. Add NEW R4: assert
  `committed_to_rescue`, `evidence_not_transmitted`, `purge_clock_started`,
  `evidence_ready_to_transmit`, `combined_broadcast_rescue_plan_known`, and
  `rebecca_office_required_for_broadcast`. R3/R4 preserve the commitment cost;
  Michelle expands options without erasing it. `SL-2C-D-R1/R2` may be rewritten
  to the merged route but are no longer incident outcomes.

## 3. World facts and pacing

Lane 1 owns all declarations and events in this section.

### New world facts

Declare each as boolean, initial `false`:

- `cover_suspected` — 2A’s doubtful inspection cover; selects the early/closer
  2B audit variant, not a durable ledger fact.
- `inspection_console_used` — Kristin has used the limited inspection console.
- `brandon_name_kept`, `brandon_name_erased` — mutually exclusive 2B ledger facts.
- `michelle_reply_received` — Michelle answered Kristin once through the medical
  terminal.
- `committed_to_transmit`, `committed_to_rescue` — mutually exclusive 2C ledger
  facts.
- `detention_sectors_sealed` and `evidence_not_transmitted` — the two explicit
  2C outcome costs.
- `inspection_window_missed`, `audit_window_missed`, `purge_window_missed` —
  missed-window state facts.
- `supervisor_escorting`, `audit_reaches_stacks`, `purge_alarm_active` — NEW
  pressure-state facts asserted only by the corresponding nudges/recovery paths.

Also preserve the already-declared world item `copied_janus_files`: type `item`,
initial value `not carried by Kristin` (no fact asserted at package load). The 2B
outcomes must move/reveal it with Kristin, and it remains carried into 2C. It is
not a new YAML fact, but is a required contract dependency.

Declare NPC `shift_supervisor` under `npcs`: type `npc`, name `Shift supervisor`, aliases
`[shift supervisor, supervisor]`, and a restrained narrator bio: a facility shift
supervisor responsible for cooling/infrastructure operations and staff oversight.
Do not state his sympathy for Michelle in the bio. Place him physically at
`facility_perimeter` in 2A and `janus_archive` in 2B with placement text; he is a
valid speaker only in those scenes. The audit placement is also the grounding for
the missed-window “sees them and does not raise the alarm” recovery. This follows
the grounding rule that physical NPCs need `character_placements`; a heard-only
speaker is not placed.

### New pacing events

Use the 1C timing pattern as an ASSUMPTION where the redesign gives no number:

- `inspection_window_2a` NEW: scene `2A`, `at_turn: 5`, effect assert
  `inspection_window_missed: true`; default text says the supervisor’s patience
  ends and he escorts them in to watch.
- `inspection_nudge_2a` NEW: scene `2A`, `at_turn: 6`, when missed and no outcome,
  effect `supervisor_escorting: true` (NEW); nudge toward proving the fault.
- `audit_window_2b` NEW: scene `2B`, `at_turn: 5`, effect
  `audit_window_missed: true`; default text says the audit reaches the stacks.
- `audit_nudge_2b` NEW: scene `2B`, `at_turn: 6`, when missed and no outcome,
  effect `audit_reaches_stacks: true` (NEW); nudge toward the whisper choice.
- `purge_window_2c` NEW: scene `2C`, `at_turn: 5`, effect
  `purge_window_missed: true`; default text says the purge alarm forces them
  out and Michelle’s route arrives, with no commitment fact.
- `purge_nudge_2c` NEW: scene `2C`, `at_turn: 6`, when missed and no outcome,
  effect `purge_alarm_active: true` (NEW); nudge toward the route and neutral 3A.

The turns and nudge IDs are ASSUMPTIONS copied from 1C’s 5/6 pattern because the
redesign leaves them open. Keep `scrutiny_2a` changed into/remapped to the
inspection-window pressure (no duplicate old scrutiny), remove `cover_review_2a`
because the doubt outcome owns that pressure, keep `archive_sweep_2b` but change
its text/activation to the supervisor’s live sweep (or fold it into
`audit_window_2b`, not both), remove `purge_2c` because the tablet is now the
2C incident set piece, and remove `transfers_2c` because physical commitment
owns the transfer/rescue consequence.

## 4. Transition triggers

Lane 2 owns the transition-trigger declarations and route-side bridge wiring;
Lane 1 merely references these existing transition IDs in the incident entries.
Keep the transition IDs and triggers:

- `t_2a_2b`: `restricted_corridor_access` — unchanged.
- `t_2b_2c`: `archive_crisis_understood` — unchanged, but the kept/new B/C
  realizations must assert it after the single discovery and Shelly reply.
- `t_2c_3a`: `combined_broadcast_rescue_plan_known` — unchanged. Both commitment
  outcomes retain their cost/advantage, then Michelle’s route asserts this trigger.

## 5. Entry variants

Lane 2 owns `plot.md` entry variants and their route-facing facts. Existing syntax
is an ordered list under a scene, for example:

```yaml
entry_variants:
- requires: [processing_numbers_copied]
  text: "Kristin still has the copied prisoner numbers."
- requires: [service_level_access_known]
  text: "Brandon knows the service approach."
```

Add/retain exactly four conditional entry cases, with base entry text first:

- 2B, audit near: `requires: [cover_suspected]`; supervisor/staff sweep begins
  closer and faster.
- 2B, clean: use the no-cover base entry text; do not invent negative-fact
  syntax. The conditional 2B variant is `requires: [cover_suspected]` and is the
  earlier/closer audit. (ASSUMPTION: “2B twice” means clean base plus this one
  conditional variant; `inspection_convincing` is an outcome id, not a fact.)
- 3A: `requires: [committed_to_rescue]`; a freed cart joins the uprising.
- 3B: `requires: [brandon_name_erased]`; Brandon’s confession is the only proof.
  Add the complementary `brandon_name_kept` wording only if the existing 3B
  entry already has a two-case declaration; do not invent another fact.

## 6. Knowledge and handoffs

Lane 3 owns every change here.

Knowledge: add `k_sl_2a_c_r5/r6`, `k_sl_2b_b_r4/r5`, `k_sl_2b_c_r3`, and
`k_sl_2c_d_r3/r4` with the facts/operations named in sections 1–2; make them
scene-local and observation/action-earned. Rewrite the old 2A hideout/cover/facility
knowledge to bridge-only or retire it. Rewrite 2B A/B knowledge so the one-file
discovery yields `janus_known`, `kristin_was_bait`, and the Brandon record together;
retire old separate search-only records. Rewrite old C knowledge from corrupted
files to the single medical-terminal Shelly reply. Retire old 2C A/B/C/D records
that encode the separate argument/clock; preserve only knowledge needed by the
merged Rebecca negotiation, physical commitment, and Michelle route. Keep the
protected boundaries `janus_selection_system`, `brandon_history`, and
`janus_phase_two`.

Handoffs: rewrite the 2A supervisor delivery to use `shift_supervisor` and the
real cooling fault; add deliveries for `cover_suspected`, the two Brandon-name
facts, `michelle_reply_received`, the two commitment facts and their costs, and
the new missed-window facts. Retire old handoffs whose fallback prose promises a
terminal search, separate archive sweep, open-ended evidence/rescue argument, or
Michelle’s broadcast solution before the incident. Keep existing 1C handoffs and
3A/3B protected-delivery boundaries.

## LANE 1

Own only `world.yaml`, `incidents.yaml`, and `pacing.yaml`: supervisor declaration
and placements; all new boolean facts; the three exact incident entries; incident
event IDs, timing assumptions, nudge effects; and old pacing-event status. Do not
edit storylets, routes, knowledge, handoffs, tests, or plot prose.

## LANE 2

Own only `storylets.md` and `storylet-routes.yaml`: cut/merge/keep decisions,
new recovery storylets, all new realization IDs and operations, route completion
and transition wiring, and the four entry variants in the existing route/scene
syntax if that syntax is represented in these files. Coordinate the plot entry
text through the owning workflow; do not edit Lane 1 or Lane 3 files.

## LANE 3

Own only `knowledge.yaml` and `handoffs.yaml`: all new/revised/retired knowledge
IDs, delivery operations and fallback text, supervisor speaker deliveries,
Shelly reply, ledger facts, costs, and entry/exit handoff wording. Do not edit
world, incidents, pacing, storylets, routes, or tests.

## 7. Existing tests requiring updates

The following existing tests were found by grepping the requested old IDs/terms.
Each must be updated to assert the new contract rather than old mandatory beats:

- `test_markdown_story_package.py::test_scene_2a_arrival_moves_kristin_and_brandon_to_the_perimeter` — retain the same perimeter placement after the new at-gate opening; do not expect hideout storylet travel.
- `test_markdown_story_package.py::test_group_member_package_declares_group_and_places_member` — retain group declaration/placement invariants; update any 2C placement expectation to Rebecca’s live corridor and the committed route.
- `test_scene_2a_corridors.py::test_scene_2a_scrutiny_waits_for_false_identities` — scrutiny comes from the supervisor incident, with `cover_suspected` only on the doubtful outcome.
- `test_scene_2a_grounding.py` tests for hideout/facility placement — expect direct gate opening and supervisor placement, while preserving grounded corridor/console placement.
- `test_scene_2a_advantages.py` all six advantage/variant tests — replace 1C-carried-advantage confrontation assertions with `inspection_convincing`/`inspection_doubted`, `restricted_corridor_access`, and the 2B `cover_suspected` variant.
- `test_scene_2a_advantages.py::test_2a_completes_without_either_carried_advantage` — expect incident missed-window recovery/under-watch, not the old free bridge.
- `test_pacing_handoff.py::test_scene_2a_handoff_asserts_hidden_bridge_fact_without_projecting_it` and `test_exit_backstop_invariant.py::test_continuity_package_accepts_2a_world_only_bridge_fact_without_delivery` — assert the incident recovery and no unearned outcome advantage.
- `test_canon_journey.py` — replace old A/B/E and separate 2B/2C realization sequence with one incident outcome per scene plus Shelly reply and the Michelle route.
- `test_spine_expected_reveals.py`, `test_2a_spine_prompts.py`, `test_2b_spine_prompts.py`, and `test_2c_spine_prompts.py` — expect the consolidated realization/knowledge IDs and four new entry cases.
- `test_phase1_slice_playthroughs.py` — update copied/route/missed-window slices to the three incident windows and recovery routes.
- `test_scene_2a_grounding.py::test_warning_the_supervisor_earns_corridor_access_by_handoff` — expect the declared shift supervisor and `restricted_corridor_access` from the incident.
- `test_2c_turn_one_copy.py`, `test_2c_assess_verbs.py`, and `test_candidate_matcher.py` 2C cases — replace terminal/file debate matching with Rebecca negotiation, physical transmit/rescue commitment, and Michelle route.
- `test_copied_files_pilot.py`, `test_leak_terms.py`, `test_narration_safety.py`, `test_narration_place_names.py`, and `test_medical_records_alias.py` — preserve copied-file/medical-terminal grounding but update timing and earned-knowledge gates.
- `test_knowledge_projection.py`, `test_revealed_knowledge_ids.py`, `test_evidence_penalty.py`, `test_cue_spent_reveal.py`, and `test_reference_evidence_append.py` — expect rewritten 2A–2C knowledge and the new name/commitment ledger facts.
- `test_scene_roleplay_contract.py`, `test_required_storylet_closure.py`, `test_affordance_map.py`, `test_incident_characterization.py`, and `test_incident_handoff_guard.py` — expect one incident per Act 2 scene, distinct recovery storylets, unchanged scene chain, and no old mandatory storylet closure.
- Any test match for `scrutiny_2a`, `cover_review_2a`, `archive_sweep_2b`, `purge_2c`, or `transfers_2c` — expect the new inspection/audit/purge incident events and their missed-window facts; old event IDs must be absent where this contract says removed.

## Orchestrator corrections (2026-11-01, after review)

1. **Entry variants are not a Ringer lane.** They live in each scene's `plot.md` frontmatter
   (`entry_variants:` with `requires: [fact]` and `text:`; 2A already has two) and are story
   text. Section 5 above wrongly gave them to Lane 2. They go to one ChatGPT Desktop prompt (a
   short pointer to this contract section 5 and `act2-redesign.md`). The facts they require
   (`cover_suspected`, `committed_to_rescue`, `brandon_name_erased`) are declared by Lane 1.
2. **Lanes cannot pass the package loader alone.** Each lane runs in its own worktree and sees
   only its own files, so cross-file validation fails in every lane. Lane checks are structural
   only (YAML parses, contract ids present, no foreign files touched). A serial **integration
   task** then merges the three patches, runs the package loader and the focused tests, and fixes
   cross-file mismatches. Test updates (section 7) belong to that task.
3. **Assumptions to confirm at review:** the 5/6 turn pattern copied from 1C; `evidence_gap_development_record`
   as the cost of erasing Brandon's name (reuses an existing fact); recovery storylet ids
   `SL-2A/2B/2C-RECOVERY` (new); "2B twice" read as clean base plus the `cover_suspected` variant.
