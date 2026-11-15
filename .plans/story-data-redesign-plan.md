# Story authoring, test contracts, and compiled runtime data

Status (2026-11-15): **Phase 0 measured; review-tooling slices 1, 2, 4 and 5
built (slice 3 dropped); D1 decided 2026-11-12; Phase 1 (schema and compiler
contract) is under way: items 1, 3, 4 and 5 done or accepted, item 10 decided and its 2C-to-3A draft written (waiting for Brandon's
two edits).** Track A is finished except the deferred blind run. The review-tooling
walkthrough of 2026-11-15 changed story data (3A and 3B entry variants, one plot
sentence) and code (rule dropped, rename, faster load); all of it is in PR #767
(branch `story-gap-cleanup`, open, not merged). This plan is separate from ongoing story
edits and does not supersede their plans.

Companion documents (evidence lives there, not here):

- [story-data-phase0.md](story-data-phase0.md): baselines, measured edits,
  duplication counts, ownership map, 2C slice.
- [story-data-comparison.md](story-data-comparison.md): four models on one real
  slice, edit walkthroughs, ranking, the Reyes/card analysis.
- [story-data-design-reference.md](story-data-design-reference.md): the reasoning
  behind the rules below (comparison framework, full requirement 5 text,
  reading-view requirement, the conditional sketch, test design table).
- [docs/story-gap-guide.md](../docs/story-gap-guide.md): what counts as a gap and
  the three checks.

## Resume here

Two tracks. Track A does not wait for Track B.

**Track A, review tooling on today's story package: finished except item 5.**
Slices 1, 2, 4 and 5 are built and merged (PR #761); slice 3 is dropped. Items
1 to 4 below were settled on 2026-11-15; item 5 needs Brandon's answer key.

1. **`unread_effect`: dropped (Brandon, 2026-11-14).** It gave 68 results over 20
   facts; about 10 were pressure markers, 7 minor facts, and only 3 were declared
   costs or advantages nothing reads (`supervisor_convinced`,
   `detention_sectors_sealed`, `evidence_not_transmitted`), which the branch
   report already prints. Checked first: the code paths that read all asserted
   facts only match them against declared conditions (not checked: `capture.py`,
   `knowledge_audit.py`). Rule, its helper and tests removed through Ringer
   (`scripts/ringer/drop-unread-effect/`); `no_producer` now has a test that it
   gives zero results on every anchor of the real package. The snapshot
   `.plans/unread-effect-report.md` was deleted with it.
2. **Branch report on the other incidents: run 2026-11-14, results below, for
   Brandon to judge** (none is a tool defect; each is a story question).
   - `i_1c_freight_transfer` (to 2A): coherent. Every branch reaches `t_1c_2a`
     through `facility_infiltration_needed`; the two real routes show up in 2A's
     entry variants. The missed-window branch leaves no trace, but its own text
     points the player back to the service entrance. `trust_brandon` and
     `terminal_sweep_closing` are set and never read.
   - `i_2a_real_leak` (to 2B): **resolved 2026-11-15, no story change (Brandon).**
     `supervisor_convinced` is the only fact that tells the cost-free convinced
     outcome apart from the others: the loader requires that the recovery
     storylet cannot award more than one outcome (`loader.py:1204-1215`), and a
     test run showed that declaring `restricted_corridor_access` instead breaks
     the load. Nothing needs to read it; the convinced branch's consequence is 2B's
     default entry (the plot gives only the vague-answer path a consequence). The
     supervisor in the archive is intended: `plot.md` 2B places him leading the
     audit, and 2B.4 makes him one of Michelle's recruited workers who lets them
     go (carried by beat prose, not YAML). Recorded in `docs/story-gap-guide.md`.
   - `i_2b_audit` (to 2C): coherent. Name kept/erased reach 2C's claim wording and
     the ending; `evidence_gap_development_record` reaches 3C. The report's
     "no next-scene transition can fire" lines are because `michelle_reply_received`
     comes from another route, as designed.
   - `i_3c_evacuation`: last scene, so handoff analysis is skipped. All its facts
     read "nothing after this scene" even where the ending in 3C reads them; the
     report does not separate "read by the ending" from "unread".
   Raw reports are not committed (they go stale); rerun `scripts/branch_report.py
   <incident>`.
3. **2C story fix: done 2026-11-15 (Brandon chose option 1; committed on `story-gap-cleanup`).**
   3A now has a second entry variant, `requires: [detention_sectors_sealed]`: "The
   upload was still running. The other detention sectors had sealed the moment it
   started, and this was the one sector still open." The base entry line stays: it
   is true in both branches (3A.1 says one sector is partly unsecured). Brandon
   confirmed the evidence takes time and is not instant, so the 3A.1 plot sentence
   "the outside world already has it" became "the upload is still running". The
   loader rejects protected terms in entry text, so the line cannot say "Michelle's
   route" or "maintenance route". The branch report now shows
   `detention_sectors_sealed` read by 3A. `evidence_not_transmitted` (rescue
   branch) is now read by a 3B entry variant, added 2026-11-15 by the same pattern
   and not separately reviewed by Brandon: "The evidence had never been sent. It
   was still with Kristin, and the broadcast was the first chance to get it out." (The
   loader rejects "copied files" in entry text.) Four
   `test_branch_report.py` tests pinned the old 2C state and were updated (none
   weakened); the helper `_remove_rescue_variant` was renamed
   `_remove_entry_variants` because it drops every 3A variant. Full suite run after the rename: 4433
   passed, 33 skipped.
4. **Rename "flag" to "rule result": done 2026-11-15 (through Ringer,
   `scripts/ringer/rename-flag-to-rule-result/`).** `Flag` is now `RuleResult`,
   `render_flags` is `render_rule_results`, the report title is "Gap rule results",
   and the word is gone from `gap_rules.py`, `scripts/gap_rules.py`,
   `tests/test_gap_rules.py` and the guide (same 22 tests, same 38 assertions).
   This plan, the frozen Ringer manifests and old plans keep "flag" in their
   history on purpose.
5. **The deferred blind run** on 1B.4 (or 2A.4), with Brandon writing the answer
   key.

**Track B, the migration: unblocked by D1** (decided 2026-11-12, section 4). Next:
Brandon tries the two edits on the 2C-to-3A draft
([story-data-2c-3a-draft.md](story-data-2c-3a-draft.md), revision 1, written
2026-11-14); its 13 proposed schema additions and its questions (commit-only
variants, `internal_claims`, the dead bridge text) feed the Phase 1 schema, item 2.
Phase 1 items 3 (ID policy for saves) and 5 (coexistence) were accepted on
2026-11-15, so the schema (item 2) is the next piece, after his two edits; then
item 6 (fixtures and tests first). The 1A draft
([story-data-1a-draft.md](story-data-1a-draft.md), revision 2) and the 2C-to-3A
draft are the starting point for the schema, not a finished one. What they leave
out is listed in Phase 1 item 10 and in the
[design reference, section 4](story-data-design-reference.md).

Housekeeping:

1. PRs #759 to #763 are merged (slice 1, this plan, slices 2/4/5, the 1A
   departure hold and phone wording, the `scripted_opening` field). Local branch
   `story-gap-cleanup` holds the commits from 2026-11-15 (unread_effect dropped,
   3A/3B entry variants, rename, plan items 3 and 5, faster load, this refresh)
   and is PR #767 (open, not merged; Brandon merges per PR). Each Ringer task's
   manifest and check are committed with its change.
2. Known limits of slice 2: custody and co-location results depend on the
   anchor's baseline state, so a transition anchor cannot run the hypothetical
   holder (the trace says "not tested here"). Custody tests that pin today's
   behavior
   (`test_transition_rejects_lead_and_patrol_without_card_custody`,
   `test_officer_demand_does_not_change_card_custody_or_transition_trigger`)
   will flip when the Reyes custody repair lands; that repair is a separate story
   change.

Code changes go through Ringer. Update this plan after each slice or phase item.

## 1. Requirements

1. **Local changes.** An ordinary story change is one cohesive authoring operation,
   with no manual synchronizing of several representations. Locality does not
   require one file per scene.
2. **One owner.** Every fact definition, authored passage and executable effect has
   one canonical owner. Tests stop copying passages and patching source strings,
   without weakening independent behavioral expectations.
3. **Measured efficiency.** Build, load, memory and per-turn budgets are measured,
   not assumed.
4. **Readable and editable by the author.** Narrative order, prose beside
   behavior, and forward/backward dependency navigation. Raw nodes, tables or IDs
   are not an authoring interface.
5. **Gap finding and repair.** The representation helps the author and a competent
   LLM find missing causal links, credible responses and consequences, in plain
   language with traceable evidence, keeping canon apart from inference, questions
   and proposals.

## 2. What the evidence says

Measured in Phase 0 on `2bb01bbc` unless noted. These facts shape the order of work.

- **Speed is not the case for change.** Uncached load 0.36 s (YAML parsing is about
  0.05 s of it; the rest is validation), cached 0.68 ms, per-turn projection
  3–6 ms, package 2.6 MiB. The case is ownership and coupling.
- **Facts have three owners.** 121 facts are defined in both routes and knowledge,
  all 176 are listed again in the world file, and 24 of the 121 have already
  drifted.
- **Most claim effects restate route effects.** 87 of 99 are identical, 12 are a
  strict subset. So the rule is "derive by default, allow a declared subset", not
  "always equal". Incidents restate costs their variant already asserts.
- **Tests are coupled to wording and layout.** 67 authored sentences are copied
  into 36 test files; 43 test files use `.replace(` on source; 72 name story files.
  A prose-only edit fails a test; a rename fails four.
- **The loader misses a dead consumer.** Removing the effect that marks Kr leaves
  the marked pursuit passage with no producer, and the package still loads.
- **Raw-file readers exist outside the loader.** Three browser E2E helpers, one
  script (`generate_spine_expected_reveals.py`; Phase 0 counted two, but
  `disclosure_matrix.py` uses the loader) and 72 tests parse the source files
  directly. An adapter to
  `StoryPackage` alone does not carry them.
- **A reading view organized by reveal failed the author; one organized by
  situation passed.** The situation trace is accepted as a reading view. No
  *editing* format has been put in front of the author yet.
- **Relation kinds were conflated.** After the card is handed to Reyes, the
  card-reading claim and the `t_1a_1b` dependency check are unchanged, because
  `required_dependencies` means "not destroyed or incapacitated", not "held".
- **The gap method is proven on one case only.** The three checks were set by the
  author after early drafts missed them; a blind run on a second case is deferred.

## 3. Direction

**Decided (D1, Brandon, 2026-11-12):** the author edits readable declarative
scene/reveal blocks; their meaning is a typed graph (facts, claims, passages,
effects, typed relations); a compiler derives the repeated wiring and builds the
existing immutable `StoryPackage`. Reading views and impact reports are generated.
No graph library, database or custom graph engine is selected, and physical
storage is not part of D1. It is examined in Phase 4 only if profiling shows a
bottleneck.

Strongest rejected alternative: plain scene aggregates with shared references
(lower overhead, close to the recommendation if the compiler's derivations stay
small).

What would reverse it: the 1A pilot (Phase 2) still fans out on ordinary edits, or
Brandon finds the draft format harder to edit than today's files. The fallback is
to keep the nine files and add only the derivations and checks (single fact owner,
derived claim effects, derived incident costs, producer/consumer rule), which
deliver most of requirement 2 without a new authoring surface.

## 4. Decisions

Made (Brandon, 2026-11-09 unless noted):

| Decision | Result |
| --- | --- |
| Pilot scene | 1A, starting once its in-flight story edits are committed |
| Budgets | Cold load ≤ 0.5 s, cached ≤ 2 ms, per-turn projection ≤ 10 ms, package ≤ 5 MiB, nothing slower than today. Regression guards, not targets |
| Reading view | Situation-centered trace accepted for the pilot. A generated view, not an authoring format |
| Requirement 5 cases | Reyes/card (known); held-out 1B.4 park ambush (fallback 2A.4); control `i_2a_real_leak` |
| Blind reviewers | Fresh-context Claude subagent and ChatGPT Desktop on the same packets |
| Build go-ahead | "I like the gaps that it finds now. I'll amend it later if I find more weaknesses. Proceed past this point to build the features into the project." Drafter's reading: Reyes findings are enough for requirement 5 for now; the blind run is deferred, not cancelled |
| Fixtures | From the continuity-initiative story only for now; schema and compiler stay story-agnostic |
| Validation | Layered, "like RelaxNG against XML" (section 5) |
| D2, review overlay scope (amended 2026-11-10) | **No stored accepted-flags store.** Rule results are computed on every run and never saved, so they cannot go stale or drift from the code. LLM findings and proposals stay generated reports, never stored records. If a rule ever needs silencing, the exemption is declared on the authored record it concerns, with a reason, and the rule reads it from there (a small schema addition made when the first case arrives; custody is the likely first). Reason: Brandon dislikes flags that sit one step removed from the code and go stale. The first D2 (a store keyed by evidence digest) narrowed staleness but did not remove it, and the earlier hand-written overlay was already removed as "not helpful; it held opinion, not evidence" |
| **D1, model and authoring format** (2026-11-12) | **Recommendation adopted:** readable declarative scene/reveal blocks, a typed graph as their meaning, a compiler that derives the repeated wiring and builds the existing `StoryPackage`. Decided on revision 1 of the 1A draft plus the fixes in revision 2; Brandon has not re-run the four edits on revision 2. Revision 1 evidence (his table): one reworded fact meant three fields plus a sibling copy; the matcher lists could not be edited from the schema alone; the edit-2 task hid a story decision; `hands_to_1B` showed no effect. Revision 2 changes address each. **Strongest rejected alternative:** plain scene aggregates with shared references. **Reversal evidence, still live:** the Phase 2 pilot still fans out on ordinary edits, or Brandon finds the format harder to edit than today's files; fallback is the nine files plus only the derivations and checks (section 3). `parts` and `examples` in the draft are proposals for the Phase 1 schema, not adopted by D1 |
| D3, CI gating | Layer 3 rule results never block a build |
| D4, when compilation runs | Load time, with the existing fingerprint cache, unless the measured cold load misses 0.5 s |
| Editing draft before D1 | Approved: 1A is drafted by hand in the proposed format and Brandon tries four edits before deciding the model |

Open, for Brandon: nothing from this section. D1 was decided 2026-11-12 (table
above).

## 5. Rules that hold throughout

Ownership and safety:

- Facts remain the sole mutable truth. Authored relationships are immutable and
  are not a second live world store. Nothing grants player knowledge because it is
  reachable in the authoring graph.
- Stable IDs are independent of headings, wording and file paths. Existing IDs are
  preserved where possible.
- Safe framing, protected claims, delivery text and dramatic guidance stay
  distinct fields. Deduplication never broadens narrator access.
- Review material (rule results, LLM reports) never reaches
  `StoryPackage`, narrator inputs or runtime facts.
- A requirement states which relation it asserts: **hold, know, reach or exist**.
- World-state-only logic is a `World` method in `packages/worldkeeper`;
  `storygame` adapts and calls it. Schema, compiler and checks carry no story names.
- Generated views are disposable and never edited. Every view names the one
  editable source.
- The migration preserves behavior. Story repairs (including what happens when Kr
  surrenders the card to Reyes) are separate reviewed changes.
- Frozen evidence (`bench/frozen/`, test fixture snapshots, Ringer history) is not
  rewritten.

Tests (full table in the design reference, section 3):

- Never derive an expected effect from the declaration under test.
- Behavior tests address records by stable ID and field; they do not copy prose or
  patch source strings. Exact-passage tests resolve the canonical passage by
  identity. Wording is asserted only where the wording itself is the requirement.
- Player actions are not generated from the matcher vocabulary they test.
- Do not delete tests to reduce counts, and add only complete, useful ones.
  Coordinate with the [test consolidation plan](test-suite-consolidation-plan.md).

Validation layers. Every check has one layer, a stable name, and a diagnostic
giving source file, record and field:

| Layer | Question | Analogy | Severity |
| --- | --- | --- | --- |
| 1. Shape | Right fields, types, enums, required values? | RelaxNG / XSD types | Error: build fails |
| 2. Integrity | Unique IDs, no dangling references, no cycles, one owner per fact and passage, claims authorized by their source effects, no duplicate YAML keys | XSD key/keyref | Error: build fails |
| 3. Story rules | Custody, co-location, no strand, a condition with no producer, an effect read by nothing | Schematron | Flag: reported, never blocks |
| 4. Narrative judgment | Is a response plausible, a consequence missing, a repair sound? | None | Advisory: LLM review, author decides |

Layers 1 and 2 are pure functions of the authored data. Layer 3 may run the real
engine but stays deterministic, quotes its evidence by file and line, and each rule
has one seeded-defect test that trips it and one clean-story test that does not.
Layer 4 never produces pass/fail.

## 6. Work

### Track A: review tooling on today's package (unblocked)

These read the current `StoryPackage`, so they need no model decision and keep
working after the migration.

- [x] **Slice 1, situation trace.** Commit `74ad8245`.
  `storygame/story_package/situation_trace.py`, `scripts/situation_trace.py <anchor>`,
  `tests/test_situation_trace.py`. Anchors: pacing event, incident, transition.
  Data-driven sections only (situation and prose, where it leads, what the exit
  needs with producers, story-says versus engine-checks); no responses or gaps, so
  its output is safe as a blind packet. Reyes output equals the prototype's
  sections 1–3. Ringer reported FAIL only because the manifest's scope filter
  misspelled an unrelated file; the corrected check passed by hand.
- [x] **Slice 2, gap rules (layer 3).** Built 2026-11-10 through Ringer.
  `storygame/story_package/gap_rules.py` (registry `RULES`: `custody`,
  `co_location`, `no_strand`, `single_reveal_strand`; `custody_checks()`),
  `scripts/gap_rules.py <anchor> [--rule NAME]`, `tests/test_gap_rules.py`.
  The module carries no story names (a test and the Ringer check enforce it).
  World-only logic is in worldkeeper: `World.holds`, `World.characters_together`,
  `World.apart`. Every cited `file:line` is a defining line of the named record
  or is omitted. On `officer_presses_1a` it flags custody (two claims),
  co-location (the laptop) and no-strand (two claims), the three Reyes findings.
  Slice 1 thin spots fixed: all anchor kinds show the authored scene situation and
  pressure; the engine-checks table reports a computed custody result
  (`checked`, `unchecked` or `untested`) instead of a fixed sentence. Test
  cleanup: the hand-rolled `test_no_single_reveal_can_strand_a_scene_exit` and
  its helper in `tests/test_canon_journey.py` were replaced by the
  `single_reveal_strand` rule after the old test body and the rule flagged the
  same realization on a seeded defect. Reviewed, not asserted by the workers:
  two defects found and fixed after the first pass (citations to non-defining
  lines; a trace that said "no held item" when custody was untested). Not done:
  other older tests that may overlap (1A tests, `*_repro.py`) have not been
  opened; sweep after slice 4 using the consolidation plan's mutation evidence.
- [x] **Slice 4, impact report and producer/consumer rules.** Built 2026-11-10
  through Ringer; in PR #761. `storygame/story_package/dependencies.py`
  (shared `producers()` and `consumers()`, used by the trace, the report and the
  rules), `storygame/story_package/impact_report.py`,
  `scripts/impact_report.py <fact|claim|event|transition|storylet>`,
  `tests/test_impact_report.py`; rules `no_producer` and `unread_effect` added
  to `gap_rules.py`. The measured case holds: removing every effect that sets
  the mark still loads, and `no_producer` reports it on `pursuit_1b`. Two review
  rounds were needed. The first pass gave about 10 `no_producer` and 40
  `unread_effect` false results because (a) a condition that needs a fact to be
  false was treated as unproduced and (b) the consumer lookup missed storylet
  completion/abort, route-event activation and ending conditions. Both are
  fixed, and a completeness test walks the model fields so a new reading site
  cannot be silently missed. Impact report test matches are textual (the id as
  a token in `tests/*.py`), not proof of coverage.
  **Open question for Brandon:** on the real package `no_producer` gives no
  results, but `unread_effect` gives 68 results over 20 facts, mostly
  pressure-state facts set by pacing events (for example `pursuit_closing_in`)
  that only record that the event happened. The worker called them true gaps;
  that is not established. Whether a recorded-but-unread fact is a gap is an
  authoring decision, and I did not check whether the narrator reads them from
  the fact store. Until decided the rule is noisy on this story.
- [x] **Slice 5, branch report (built 2026-11-10, in PR #761; added after
  Brandon's review of `unread_effect`).** The slice 2 and 4 rules look at one fact at a time. They
  cannot say what a scene's branches do to the story. Brandon's requirement: for
  the branches of a scene (an incident's outcomes, its recovery and its
  missed-window path), analyze (1) the branch within its scene: what it does,
  whether it leaves an authored way out, whether what it sets and what it costs
  make sense, and (2) how it influences the next scene (when there is one):
  which next-scene entry variants, claims, gates and transitions react to it,
  what carries on only in some branches, and which declared costs or advantages
  nothing enforces. Layer 3 part (computed, cites file and line): the branch
  table above. Layer 4 part (judgment, never pass/fail): the report quotes the
  branch's text beside the next scene's entry text so a reader can check common
  sense, for example a branch that seals a place followed by an entry that calls
  it open. Module `storygame/story_package/branch_report.py`, script
  `scripts/branch_report.py <incident>`, tests `tests/test_branch_report.py`.
  **Brandon's rule (2026-11-10): if the state of the next scene does not follow
  from where the branch leaves off, something is broken.** So the core check is
  handoff continuity, computed with the real engine: take the world after the
  branch, apply the next scene's entry placements (`apply_scene_placements`),
  and list everything the entry moves (protagonist, characters, items,
  companions) and every fact the branch set that the next scene never reflects.
  An unexplained move is a result.
  Built through Ringer in one pass (`branch_report.py`, `scripts/branch_report.py
  <incident>`, `tests/test_branch_report.py`, `Consumer.scene_id`, a guide
  section). On 2C it finds the two unread declared costs and that the transmit
  branch leaves no trace in 3A, and no unexplained world move. Two follow-up
  Ringer tasks fixed the first output: the bridge text now prints once per
  handoff, scene setup is listed apart from carried-over state, and reads by the
  incident scene's own exit transition count as "read" but not as a trace in a
  later scene. Limits: run on one incident (2C) only; the check that the next
  scene's text agrees with the branch's text is left to the reader (the report
  quotes both side by side). The rescue branch reaches 3A through one entry
  variant; the other three paths leave 3A identical.
- [x] **Slice 3, accepted flags: dropped (2026-11-10, amended D2).** No separate
  store is built. If a rule needs silencing, add a reasoned exemption field on the
  authored record and have the rule read it; do that only when a real case
  arrives. Until then nothing is stored and nothing can go stale.
- [ ] **Deferred blind run (quality check on the method).** Brandon writes the
  1B.4 answer key and keeps it out of the packets and out of the drafter's context
  ("no known gap" switches the held-out case to 2A.4). Packets are slice 1 output
  for the three anchors; both reviewers run on the same packets; Brandon scores
  supported findings, misses, false alarms and clarity. Until it runs, the rule set
  is shaped by the Reyes case alone: a recorded risk.

### Track B: migration

#### Phase 0: decide (one item left)

Done: comparison on a real reveal and cross-scene dependency; 2C incident slice;
baselines and budgets; three measured edits; ownership map; pilot scene; reading
view accepted; requirement 5 shown on Reyes (non-blind) and accepted for now.

- [x] **Editing draft and D1.** Done 2026-11-12 (D1 row in section 4). Still to do: replace the conditional sketch in the design reference with the chosen format. Draft written 2026-11-11: [story-data-1a-draft.md](story-data-1a-draft.md) (tried by Brandon 2026-11-12, copy with his edits and hesitation table in [story-data-1a-draft-edited.md](story-data-1a-draft-edited.md); findings: one fact reworded in three fields of one variant, matcher word lists not editable from the schema alone, the edit-2 task wording was unclear, `hands_to_1B` shows no visible effect; revision 2 of the draft (`story-data-1a-draft.md`) fixes those four and awaits another try; a field-by-field schema section was added after he said the sample alone does not tell him what can go where). Original step: write 1A by hand in the proposed format, in
  `.plans/`, with no compiler: scene entry and beats, one reveal with quiet and
  witnessed variants, its claims and delivery text, a pacing event, the officer
  pressure, the exit and its cross-scene dependency. Brandon tries four edits on
  it: reword a passage; change what a variant commits; change a shared search
  description; follow one consequence into 1B and back. The full task sheet (what
  to change, what to watch for, legacy counts, answers to check afterwards) is the
  "Four edits to try" section of the draft. Record where he hesitated.
  He then decides D1, and the conditional sketch in the design reference is
  replaced by the chosen format.

Why this was added: the earlier "readable authoring prototype" item was closed on
a reading view. Requirement 4 also asks that the author can *edit* it, and that
has not been tested.

Exit: D1 recorded with the strongest rejected alternative and its reversal
evidence.

#### Phase 1: schema and compiler contract

Starts after D1. Order matters: contract, then tests, then code.

1. **Snapshot.** Name the commit that migration mappings are written against,
   after the in-flight 1A edits are committed (`2bb01bbc` is already behind).
   **Snapshot, settled 2026-11-13: `20892032`** (merge of PR #763 into `main`;
   the feature commit is `8f2ad1e3`). It commits the in-flight 1A work that had
   blocked the snapshot: a `scripted_opening` scene field (`plot.md` scene 1A,
   `models.py`, `engine.py`) and 12 test files, 126 tests passing, CI green. Later
   `main` commits (`a627db84`, PR #764) change only `.plans/`; a diff of `data/`,
   `storygame/`, `tests/`, `packages/` and `scripts/` from `20892032` to that
   commit was empty when checked.
2. **Schema.** Typed records, stable IDs, reference resolution, source maps,
   disclosure boundaries, versioning. Typed relation kinds (hold, know, reach,
   exist, and their negations). Commit-only variants (the 2C finding). Derivation
   rules, each explicit: one fact owner; claim effects default to the source's
   effects with a declared subset allowed; incident costs and advantages derived
   from the named variant.
3. **ID policy for saves.** **Accepted by Brandon 2026-11-15** (proposal read from
   `persistence.py` and `state.py`; revised the same day around his rule below). The save-compatibility decision
   itself stays in Phase 3.
   - *What a save holds:* the session state without the package, as JSON, keyed by
     `story_id` and a store schema version (5). On load the only checks are story
     id, schema version, payload hash, and that the saved scene exists with a
     matching phase. **Every other ID in a save is accepted unchecked**, so a
     renamed fact or event would be silently orphaned, not rejected. This is true
     today, before any migration.
   - *Frozen IDs (a save stores them; migration must keep them):* scene ids (9),
     fact ids (177; they are the `predicate` of every saved fact), entity ids
     (items, places, characters and groups; they appear as fact subjects and
     objects), knowledge claim ids (122; saved as `reveal_ids` and
     `revealed_knowledge_ids`), pacing event ids (31; `active_event_ids`,
     `fired_event_ids`, turn records), transition ids (8), delivery fact ids (48;
     the cue ledger and staged handoffs), and the story id.
   - *Free IDs (a save does not store them; the migration may change them):*
     passage and variant ids, storylet and realization ids (68 storylets),
     incident and outcome ids (derived from facts), matcher groups, source file
     names, headings and block order. One exception to note: the saved
     `last_turn_delivery.beats_projected` holds beat anchors, which today are
     derived from beat headings (for example `scene-3a4--the-uprising-begins`);
     it is read once, for the last turn only, so it is not frozen, but the new
     format should not derive any ID from a heading.
   - *When the checks run (rule from Brandon, 2026-11-15):* **schema strictness
     belongs to package build and load; saves stay flexible, tag and value, so
     in-progress work can always be saved and reloaded.** Today this already
     holds: `load_story_package` runs shape and integrity checks once, at app
     startup (`web_demo.py:208`), in tests and in CI, cached by a hash of the
     source files, and a bad package stops the server. A save load checks only
     story id, store version, hash, the state's own shape, that the saved scene
     exists and the phase matches; saved facts are checked only for predicate
     name pattern and length. The compiler keeps the same moment (D4). **A
     load-time check of saved IDs against the package is rejected.**
   - *Enforcement is a developer warning, not a build error (Brandon,
     2026-11-15):* the compiler writes a save-identity manifest (the frozen IDs
     by kind) from the snapshot package. A test compares the current package
     with it and emits a `UserWarning` naming every missing frozen ID; it does
     not fail the suite, it never runs at load or play time, and a player never
     sees it. This is a layer 3 result in the sense of D3 (reported, never
     blocks). An intended removal is listed in a retirement file with a reason,
     which silences the warning for that ID (the exemption lives on the authored
     record, as D2 requires). Checked: `pyproject.toml` ignores only
     `DeprecationWarning`, so a `UserWarning` shows in pytest's summary; no test
     uses `warnings.warn` yet, and a summary line is easy to scroll past, so the
     same check should also be runnable as a script. Limits: it protects ID
     names, not their meaning, so an ID reused with a different meaning would
     pass; and an old save loaded against a package that dropped an ID loads
     fine and the orphaned facts simply do nothing. Not built or tested.
4. **Layer 1 audit.** List what `storygame/story_package/models.py` already
   enforces and what the schema adds; record it here.
   **Audit, 2026-11-13 (read from code, not run):**
   - *Shape (layer 1)* is in `models.py`: every model is `_Model` with
     `extra="forbid", frozen=True`; typed fields, ID patterns, `min_length`, and
     about 30 field/model validators (axes, placements, effects, delivery text,
     guards, pacing, storylet routes).
   - *Integrity (layer 2)* is not in `models.py`. It is about 200
     `StoryPackageError` raises in `loader.py`: unique IDs, unknown scene, fact,
     entity, transition, realization, knowledge and incident references, one
     delivery per fact, knowledge effects equal to their realization, canonical
     event or entry fact, ownership ambiguity, prerequisite/reveal cycle, scene
     transition cycle, ambiguous transition priority. All run on the built
     `StoryPackage` (`_load_story_package_uncached`, about lines 1693–1704), so a
     compiler that builds the same `StoryPackage` gets them without rewriting.
   - *Source-format checks* (markdown headings, frontmatter, beat Details lines,
     SL-* sections, YAML shape: about lines 74–345 and 1297–1630) are specific to
     today's nine files. The new schema has to supply its own equivalents.
   - *Not enforced today*, which the schema must add: duplicate YAML keys
     (`yaml.safe_load` overwrites silently); one owner per fact across files (121
     facts are defined twice and nothing objects); claim effects authorized by or
     derived from the source effects (only equality with the realization is
     checked); a variant's `leak_terms`/`boundaries` override may only add
     entries (item 10). Dead consumers are layer 3, already covered by
     `no_producer`.
5. **Coexistence.** **Accepted by Brandon 2026-11-15 (option 1, as written); not built.**
   - *Explicit mode, no precedence.* An ownership manifest in the package root
     lists, for each scene and for the root catalog, `legacy` or `compiled`; a
     missing manifest means all `legacy`, which is today's behavior. No
     environment switch. The loader builds legacy scenes from the nine files and
     compiled scenes from compiled records, and merges them into one
     `StoryPackage`.
   - *Two owners are an error.* A record id defined on both sides, a scene marked
     `compiled` that the legacy files still define, or a scene marked `legacy`
     that has compiled records fails the build (layer 2) and names both sources.
   - *Raw-file readers (section 2).* They parse the legacy files directly, so a
     scene marked `compiled` would vanish from them. Sequencing rule: a scene is
     marked `compiled` in the shipping package only after the readers that touch
     it read through a generated export of the package
     (`scripts/export_story_package.py`, to be written) instead of the source
     files. Until then, Phase 2 keeps 1A legacy in the shipping package and runs
     the compiled 1A beside it in the parity test, not in a mixed package. Mixed
     ownership starts in Phase 3, per scene, after that scene's readers have
     moved (the Phase 3 reader list). Checked 2026-11-15: the raw readers
     scan whole files, not scenes. `frontend/e2e/authored-spans.js` reads
     `plot.md`, `knowledge.yaml`, `handoffs.yaml`, `pacing.yaml` and
     `storylet-routes.yaml`; `knowledge-available.js` reads `knowledge.yaml` and
     `storylet-routes.yaml`; `roleplay-judge.test.js` reads `knowledge.yaml`;
     `scripts/generate_spine_expected_reveals.py` reads `knowledge.yaml`.
     `scripts/disclosure_matrix.py` uses the loader and is not a raw reader. So
     the export and the four reader changes are one prerequisite before the
     first scene flips, not a per-scene task. The 72 raw-reading tests are the
     Phase 0 count at `2bb01bbc` and were not recounted.
6. **Fixtures and tests first.** Small typed fixtures and patch helpers that
   address records by ID and field, drawn from continuity-initiative and together
   covering claims, protected material and audience scoping, pacing, an incident
   with outcomes, and a cross-scene dependency. Schema and validator tests before
   the implementation.
7. **Compiler and adapter** to `StoryPackage`. Layer 2 checks. Deterministic
   output with schema/compiler version and source digest; cache invalidation over
   all compiler inputs; fail closed on mismatch at load. Compilation runs at load
   time (D4); record the measured cold load that confirms or reverses it.
8. **Safety tests.** Deduplication does not broaden narrator access; review
   material cannot reach the package or narrator inputs (a test that fails if it
   does).
9. **Generated story view** from compiled records: narrative order, continuation
   requirements shown as promise versus check, and each exit trigger fact's
   `purpose` beside the exit (the motivation evidence; decided under item 10).
10. **Close the D1 coverage gaps** (found 2026-11-13 by reading the 1A draft
    against the design reference; full table in
    [design reference, section 4](story-data-design-reference.md)). Decide or
    build each before the exit below:
    - *Shared facts:* **decided 2026-11-13 (Brandon): option A.** A fact is
      declared in the scene that first sets it in story order; a fact nothing sets
      lives in the first scene that reads it; other scenes use it by ID. Measured
      on the current package (177 facts, scene-tagged records only): 144 set and
      read in one scene, 17 set in one and read in another, 3 set in two scenes,
      13 with no setter found (not examined; a story question). Checks that make
      a reveal move safe: (1) layer 2, error: a fact's declaring scene must equal
      its first setting scene, and the error prints the block to move; (2) layer 3,
      result: a fact read in a scene earlier than any scene that sets it; (3)
      layer 2: scene-scoped references (turn window inside the new scene's pacing
      window, `helps_exit` naming an exit of the reveal's own scene, reach items
      present in the new scene; the last two not yet verified against the
      loader). No `home:` exemption until a real case needs one. Design only, not
      prototyped.
    - *Typed relations:* **decided 2026-11-13 (Brandon): option B.** One shared
      shape `{item, relation: exists|held|reach, holder?, not?}` used in an exit's
      `needs` and in a new reveal-level `needs`. The existing `reach` list keeps
      its name (the name already says the relation). Know stays as fact
      conditions and audience; no new syntax. A `held` need is a promise to the
      checker, not a runtime gate (the engine only enforces "not unavailable"
      today, `validation.py:438-456`). Migration is mechanical: the four exits
      with `required_dependencies` today (`memory_card`; `transit_card` and
      `brandon`; `brandon`; `brandon`) become `exists`. Changing the 1A exit to
      `held` is a story change for the Reyes repair, separate from migration. The
      custody rule keeps inferring; a difference between a stated need and the
      inference becomes a result. Not built or tested.
    - *Drafts beyond 1A:* **decided 2026-11-13 (Brandon): option B.** A second
      hand-written slice, 2C to 3A, covering the incident (commit-only variants
      for the two outcomes with no claim; costs and advantages derived from the
      named variant), the handoffs into 3A, and 3A's entry claims. Short sketches,
      not full conversions, for the root catalog: entities (25 places, 9 NPCs, 2
      groups, 72 items; no setter, so they do not follow the facts rule), the 2
      connections, the 1 disclosure guard and 3 protected-knowledge entries, and
      the ending. Handoffs (48) go on the fact's declaration as an optional
      `delivery`; incidents (5) and entry claims (10) go in their scene file.
      Brandon then tries two edits on the slice, as he did for 1A. The draft must
      not repair the 2C finding (transmit branch leaves no trace in 3A; both
      declared costs unread): migration preserves behavior, so the draft shows
      the gap in the generated view and the fix stays a separate story change.
      Counts are from the loaded package. The ending's home (root or last scene)
      is left to the draft. **Written 2026-11-14:**
      [story-data-2c-3a-draft.md](story-data-2c-3a-draft.md), revision 1. A
      scratch script compared 180 of its values with the loaded package, all
      matching; Brandon has not tried its two edits. Corrections it found: the
      two variants with no claim are `SL-2C-D-R1` and `-R2`, not the incident
      outcomes (those have claims); the 2C bridge text sits under a legacy key
      (`fallback_realization`) that the loader never reads, in all 11 bridge
      events. The ending's home is still open (the draft puts it in a root
      `catalog` and marks it). **Decision 2026-11-14 (Brandon): delete `SL-2C-D-R1` and `-R2`**
      (their claims were removed on purpose in `16d6094c`; they do nothing R3, R4
      and the recovery storylet do not). The draft omits them and the commit-only
      variant is withdrawn; the live package still has them until a separate
      story change removes them. Original wording: typed
      relations beyond the exit's `needs`
      (hold, know, reach, exist, negations); drafts for what 1A did not cover
      (entities, connections, entry claims, handoffs, incidents, disclosure
      guards, ending).
    - *Layer 2 checks the format must make possible:* dangling references, cycles,
      one owner per fact and passage, claims authorized by their source.
      **Decided 2026-11-13 (Brandon):** a variant's override of `leak_terms` or
      `boundaries` can only add entries, never remove or replace them. This is a
      layer 2 check (build fails). Example: a variant of `drawer_search` that
      replaces its nine leak terms with two is rejected.
    - *`examples`:* **decided 2026-11-13 (Brandon): accept and reject lists in a
      separate fixture, addressed by record ID, not in the authoring file.** The
      authoring file keeps the word groups (`action_evidence`). The fixture holds,
      per search, the commands that must match and the commands that must not:
      `drawer_search: {accept: [Search under the KMS drawer, Look under a drawer],
      reject: [Look at the drawer, Look under the desk]}`. The checker runs the
      real matcher on every line. For a failing accept line it names the failing
      group and the smallest word to add, and lists what that edit would newly
      accept. If the edit would flip a reject line, it says so. This replaces the
      draft's `examples` field, so the expected result is never written beside
      the declaration it checks. The checker is advisory help for the author; a
      failing accept or reject line is a test failure. Limits: the "newly
      accepts" list covers only commands the checker generates (verbs of the
      class crossed with the group's words), not all free text. One related
      matcher change is deferred: a marker such as `=search` meaning "this word
      only, no synonym class", needed to accept "search the drawer" without
      "look at the drawer". It is a generic engine change with its own tests,
      outside Phase 1. The model path's `ActionContract` already has `positive`
      and `near_miss` command lists; whether the fixture lists should feed it
      too is not checked (no story YAML sets it today, as far as I found).
    - *Requirement 5:* **decided 2026-11-13 (Brandon): option A.** No authored
      field beyond `situation`, `pressure` and the typed exit `needs`. Possession
      is covered by the typed `held` need, retained knowledge by the producers of
      facts already set, physical ability partly by the co-location and no-strand
      rules. Motivation is not derivable; the evidence for it is each exit
      trigger fact's authored `purpose`, shown beside the exit (the current
      situation trace already does this, `situation_trace.py:72`; item 9 must
      keep it). Not decided: whether purposes are enough for a reviewer to catch
      a motivation gap. That is the open risk. Test it in the deferred blind run
      by comparing reviewers with and without a sentence such as `why_go`; an
      optional field can be added later without breaking anything. Exit 5 below
      is the other test.

Exit (all required):

1. A small story built from the fixtures compiles to a `StoryPackage`; safety
   tests pass.
2. Layers 1 and 2 fail the build on seeded defects; layer 3 flags and does not
   block.
3. Migration mappings from the named snapshot are written and reviewed.
4. Compile and load numbers are measured against the budgets; a miss is recorded
   and explained.
5. Brandon traces the Reyes gap in the generated view unaided.

#### Phase 2: 1A pilot

- [ ] Convert 1A mechanically. **Parity gate:** the compiled 1A portion of the
  package equals the legacy-loaded one, shown as a semantic diff of IDs,
  predicates, effects, passages, placements and disclosure scopes; deterministic
  runtime traces match the baseline. Only reviewed representation differences are
  allowed. Because parity is at the `StoryPackage` boundary, tests that go through
  the loader keep protecting behavior unchanged.
- [ ] Replace copied prose and source patching in the 1A pilot tests (section 5
  test rules).
- [ ] Repeat the three Phase 0 edits and compare:

  | Edit | Phase 0 | Target |
  | --- | --- | --- |
  | A. Reword a passage | 1 source line, 1 test fails on a copied string | 1 edit, no test fails |
  | B. Change a variant's effect | 2 files plus stale prose; 1 behavioral test fails | 1 declaration; only the behavioral guard fails; the dead consumer is flagged |
  | C. Rename a shared fact | 5 story files, 3 test files, 4 failures | 1 declaration plus real consumers, each listed by the compiler |

- [ ] Re-measure load, memory and per-turn numbers against the budgets.
- [ ] Run the design reference's decision-exercise walks 3–6 on the pilot, which
  the hand draft could not show: move a reveal between scenes with its
  cross-scene dependencies; assemble only the current audience's eligible
  material; reject dangling references, incompatible effects and cycles; update a
  behavior test without copying prose.
- [ ] Re-run the four edits from the 1A draft's task sheet on the compiled format
  (Brandon has only tried revision 1 by hand).
- [ ] Brandon makes one real 1A edit in the new format and reports on it.

Exit, and the go/no-go for Phase 3: targets met, no safety regression, no
unexplained performance regression, and Brandon prefers editing the new format. If
edits still fan out, revise the schema once and re-run; if they still do, take the
fallback in section 3.

#### Phase 3: full story and consumers

- [ ] Convert remaining scenes and shared definitions incrementally, parity gate
  per scene.
- [ ] Migrate the raw-file readers: `frontend/e2e/authored-spans.js`,
  `knowledge-available.js`, `roleplay-judge.test.js`,
  `scripts/generate_spine_expected_reveals.py`, and the tests that name story
  files. (`scripts/disclosure_matrix.py` was listed here until 2026-11-15; it
  already uses the loader.) Per the coexistence proposal in Phase 1 item 5, the
  four readers move before the first scene flips.
- [ ] Migrate active tests, E2E setup, probes and Ringer manifests to stable
  record operations.
- [ ] Another genre as a portability gate.
- [ ] Save compatibility decided explicitly: preserve identity only where semantic
  equivalence is established; otherwise version, reject or provide a tested
  migration. Never silently reinterpret a saved session.
- [ ] Retire the legacy sources and the dual-loader path at cutover; keep exports
  only as generated views. Update the authoring documentation and PRD.

#### Phase 4: measured optimization and release

- [ ] Profile the migrated implementation; add indexes only for demonstrated
  costs. Examine physical storage only if evidence shows a bottleneck.
- [ ] Verification per the [testing runbook](../docs/testing-runbook.md); staging
  and SHA-bound hosted E2E per the
  [promotion guide](../docs/railway-production-promotion.md).

Independent of all phases: **done 2026-11-15 (through Ringer,
`scripts/ringer/compile-delivery-token-pattern/`).** `_delivery_internal_token`
ran 100 times and each call rebuilt the id set and ran about 630 `re.search`
calls (about 63,000 in all, 0.21 s unprofiled). It now uses one compiled pattern
per package. Measured uncached load, best of 5, same machine: about 0.40 s
before, about 0.16 s after (budget 0.5 s). The check compared the new matcher
with a copy of the old logic on thousands of texts. The only visible difference:
an error message shows a matched token in lower case. **Phase 4 candidate, not
done:** the profile also shows `world_for` rebuilding the world schema about 100
times inside `_validate_narration_term_traps` (about 0.18 s profiled); it is also
called on the per-turn path, so it is not an isolated fix and the budget is
already met.

## 7. Acceptance and scope limits

Success: one authored definition per fact and reusable passage; fewer files
changed per ordinary edit (the Phase 2 table); stable IDs through prose renames;
deterministic compilation; actionable reference errors; independent regression
assertions; measured runtime within budget; unchanged safety. The author can
follow and edit the narrative, trace a gap such as the Reyes demand through the
generated view unaided, understand an evidence-linked finding, and judge a
proposed repair. Passing schema and runtime tests alone does not meet this.

Out of scope: removing tests to reduce counts; choosing libraries or storage
before D1 and profiling; a visual editor; narrative changes during parity work; a
fixed menu of player actions or a branch per possible action.

## 8. Record

- 2026-11-09. Phase 0 measured on a detached worktree at `2bb01bbc`
  ([evidence](story-data-phase0.md)). Comparison ran 75 focused tests, all passing.
- 2026-11-09. Slice 1 committed as `74ad8245`; `tests/test_situation_trace.py`
  passes (re-run during this revision).
- 2026-11-09. Plan restructured: two tracks, decisions table, design discussion
  moved to the reference file. Substantive changes from the previous version:
  D1 now needs an editing draft; physical storage removed from the blocker; slice 3
  narrowed pending D2; producer rule added to layer 3; raw-file readers named in
  Phases 1 and 3; Phase 2 given measured targets and a go/no-go with a fallback.
  Not verified: nothing in Phases 1–4 has been built or measured.
- 2026-11-09. Brandon accepted all four recommendations: D2, D3, D4 and the
  editing-draft step. D1 stays open until he has tried the 1A draft.
- 2026-11-10. Slice 2 built (section 6). Story-gap guide now points at
  `scripts/gap_rules.py`. The blind run is still deferred, so the rules remain
  shaped by the Reyes case alone.
- 2026-11-10. Brandon amended D2: slice 3 (accepted-flags store) is dropped in
  favor of exemptions declared on the authored record, built only when a rule
  needs one. Open, not yet done: rename "flag" to "rule result" in the plan, the
  guide, the module and the output (a follow-up pass, not part of slice 4).
- 2026-11-10. Slice 4 built (section 6). `unread_effect` is noisy on the real
  package (68 results); decision pending.
- 2026-11-10. Slice 5 built (section 6): the branch report, after Brandon asked
  for branch analysis and his rule that a next scene's state must follow from
  where the branch leaves off. Slices 4 and 5 are in PR #761. Next steps are in
  "Resume here".
- 2026-11-11. PRs #761 and #762 merged. 1A editing draft written in `.plans/story-data-1a-draft.md` (hand-written, no compiler, nothing reads it). Next step is Brandon's four edits, then D1.
- 2026-11-12. Brandon tried the four edits on revision 1 of the 1A draft (copy and hesitation table in `story-data-1a-draft-edited.md`). Revision 2 of the draft fixes what he hit (shared passage parts, matcher rules and examples, edit 2 rewritten as a story decision, 1B excerpt added, `hands_to_1B` removed). He then said "go ahead with D1": recommendation adopted, Track B unblocked. Not done: he has not re-run the edits on revision 2; the design reference still holds the conditional sketch.
- 2026-11-13. Coverage check of the chosen format against the design reference. The draft covers passage ownership, field separation, fact purpose, claim effect defaults and stable IDs; it only partly covers typed relations and relationship context; it does not cover a root catalog (and differs from the sketch on shared facts), entities, incidents, handoffs and other undrafted parts, or walks 3–6. Compiler, runtime and test redesign are not the format's job and were already in Phase 1 items 6–7 and Phases 2–3. Two risks recorded in the design reference section 4: `examples` written beside the matcher, and search-block overrides that can shrink `leak_terms`. Added Phase 1 item 10 and two Phase 2 items.
- 2026-11-13. Item 10 decisions made by Brandon: matcher examples become accept/reject lists in a separate fixture; a variant override may only add `leak_terms`/`boundaries` entries. Item 10 is fully decided as of this entry: shared facts live where first set (A), typed relations use one shared shape (B), a second slice 2C to 3A is drafted by hand (B, not yet written), and no new authored field for requirement 5 (A, plus exit trigger purposes in the view). The probe behind the accept/reject design ran the draft's word groups through `_matches_all`, not the legacy story file.
- 2026-11-13. Resumed Phase 1. Item 4 (layer 1 audit) written from reading `models.py` and `loader.py`; item 1 (snapshot) found blocked by uncommitted `scripted_opening` work on `main`. No code or story data changed.
- 2026-11-14. Wrote the 2C-to-3A hand draft (Phase 1 item 10, option B): `story-data-2c-3a-draft.md`. It lists 13 schema additions the slice needed, with a status each; shows the 2C gap in the generated view without repairing it; sketches the root catalog; and has a two-edit task sheet. Checked by script against the loaded package (180 values, all matching (R1 and R2 dropped from the draft by decision), after two mistakes of mine were fixed). Not checked: passage-list first-match semantics in the runtime, operation order, the shape of `internal_claims`. Open questions for Brandon are in the draft's "Things I noticed": the commit-only variants `negotiated` and `split_exposed` that nothing tells apart, the 11 dead bridge texts, `item` as the key for a character in an exit's `needs`. No code or story data changed. Not committed.
- 2026-11-14. Deleted `SL-2C-D-R1` and `-R2` from the live package through Ringer (`scripts/ringer/delete-2c-d-r1-r2/`): routes file minus those two options, two test-set entries removed; 206 focused tests passed, ruff clean. The first run failed only on a bug in my check (git add with an ignored `.venv`), not on the worker output; the check was fixed and rerun on the kept worktree, then the patch was applied. Frozen copies, old plans and the generated disclosure matrix still mention them. Not committed.
- 2026-11-14 (later). Resumed. Repo state: `main` at `eac9d666`, clean; PR #766 (the R1/R2 deletion and the 2C-to-3A draft) is merged, so the two "Not committed" notes above are out of date. Ran the branch report on the four incidents not yet covered (1C, 2A, 2B, 3C); findings are in "Resume here" Track A item 2. One new story question: 2A's convinced branch sets an advantage nothing reads. Nothing else changed. Still waiting on Brandon: his two edits on the 2C-to-3A draft (gates Phase 1 item 2), the `unread_effect` choice, and the 2A/2C story calls.
- 2026-11-15. Walked Brandon through the "waiting on me" items. Item 1 decided: drop `unread_effect` (see Resume here, Track A item 1); done through Ringer. First Ringer run passed but its check did not export a patch, so Ringer deleted the worktree and the change was lost; the check was fixed and the run repeated. Items 2 (2C/3A) and 3 (2A supervisor) are still open: for 2C the options put to Brandon were a 3A entry variant for the transmit branch (recommended), a neutral default plus two variants, real mechanical teeth, or dropping the two costs. Slice 4's description above still lists `unread_effect` as built; it is historical.
- 2026-11-15 (later). 2C/3A decided: option 1, plus fixing the plot sentence (see Resume here item 3). Correction to my earlier step-2 reading: entry variants are appended to the base entry text, not substituted (`scene_entry_texts`, `models.py:647`), and the base line "a partly unsecured detention sector" is not a contradiction. Step 3 (the 2A supervisor) is next.
- 2026-11-15 (end of walkthrough). Step 3 decided: leave 2A alone and document why. My first recommendation (declare `restricted_corridor_access` as the convinced outcome's advantage) failed: it breaks the loader's recovery rule, so it was reverted before commit. All three "waiting on Brandon" items are now closed; open work is `evidence_not_transmitted` (unread, likely a 3B reader, unchecked), the "flag" to "rule result" rename, the deferred blind run, and Phase 1 item 2 once he tries the two 2C-to-3A edits. Uncommitted in the working tree: the `unread_effect` removal, the 3A variant and plot sentence, four updated branch-report tests, guide and plan. The full suite has not been run.
- 2026-11-15 (after the walkthrough). Added the 3B entry variant for `evidence_not_transmitted` (both 2C costs are now read); updated `test_real_incident_renders_expected_costs_and_variant` to match. Committed everything so far on local branch `story-gap-cleanup` (not pushed) so the next Ringer task, the "flag" to "rule result" rename, starts from current files.
- 2026-11-15 (Phase 1). Wrote proposals for item 3 (ID policy for saves) and item 5 (coexistence) from reading `persistence.py`, `state.py` and the loaded package. Finding: a save's IDs are not checked at load beyond scene and phase, so an ID change fails silently today. Both items wait for Brandon to accept or change them. Nothing built.
- 2026-11-15 (rename). Rename applied from the Ringer patch (first run passed; this time the check exported the patch). Full suite run once after it: 4433 passed, 33 skipped (4 min 31 s). Repo-wide `ruff check .` reports 229 lint errors, all in older `.plans/` scratch scripts and `scripts/ringer/story-data` generators that this work did not touch (CI's rule set `E9,F63,F7,F82` is clean); `ruff format --check .` flagged 3 `.plans/` scripts, now formatted.
- 2026-11-15 (load time). Compiled the delivery token pattern once per package (Ringer, check compared old and new logic): uncached load about 0.40 s to about 0.16 s. D4's budget check (cold load at most 0.5 s) now has more room for a compiler. Remaining validation hotspot recorded as a Phase 4 candidate.
- 2026-11-15 (final run). Full suite on the committed branch: 4435 passed, 1 failed, 33 skipped. The failure was `test_real_manifest_covers_test_files`: the new `tests/test_delivery_token_matcher.py` was missing from `tests/shard_durations.json`; added with `scripts/regen_shard_durations.py --missing-only` and the test passes. The suite was not rerun in full after that one-line manifest change.
- 2026-11-15 (wording approved). Brandon approved the 3A and 3B entry lines (walkthrough item 1 of 5). He asked for the last sentence of the 3B line to be reworded: now "The evidence had never been sent. It was still with Kristin, and the broadcast was the first chance to get it out." Focused story tests pass (142); the full suite was not rerun for this one-sentence text change.
- 2026-11-15 (rule on checks). Brandon: schema checks belong to package build/load; saves and loads stay flexible tag/value so in-process work can be saved. Phase 1 item 3 rewritten around it; the load-time saved-ID check I had raised as an option is withdrawn. Verified in code first: package validation runs at package load (startup, tests, CI), save load checks structure only.
- 2026-11-15 (item 3 accepted). Brandon accepted Phase 1 item 3, the ID policy for saves, as revised.
- 2026-11-15 (item 3 amended). Brandon: the frozen-ID check should be a warning, not an error, and run as a test, not at runtime, so only the developer sees it. Item 3 changed from a layer 2 build failure to a test-time layer 3 warning with a retirement file.
- 2026-11-15 (item 5 accepted). Brandon accepted Phase 1 item 5, coexistence, as written (explicit ownership manifest, two owners an error, the four raw-file readers move to a generated export before the first scene flips, 1A stays legacy in the shipping package during Phase 2). Walkthrough item 3 of 5 is closed.
