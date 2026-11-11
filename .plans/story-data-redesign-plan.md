# Story authoring, test contracts, and compiled runtime data

Status (2026-11-10): **Phase 0 measured; review-tooling slices 1 and 2 built;
the model decision is the one open blocker for the migration.** No story data, test
or deployment has changed. This plan is separate from ongoing story edits and does
not supersede their plans.

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

**Track A, review tooling on today's story package: unblocked.**
Slices 1, 2 and 4 are built; slice 3 is dropped. Next: decide what to do about the
noisy `unread_effect` rule (section 6, slice 4), then the deferred blind run.

**Track B, the migration: blocked on decision D1** (section 4). The unblocking
step is not more analysis. It is a hand-written draft of scene 1A in the proposed
format that Brandon tries four edits on (Phase 0, last open item).

Housekeeping, in order:

1. Branch `story-data-situation-trace` carries slice 1 (`74ad8245`) and this plan,
   with a PR open against `main`. The working tree also holds unrelated,
   uncommitted 1A story edits (arrival glance, departure hold) that belong to
   [the 1A plan](1a-password-and-officer-plan.md); keep them out of this branch's
   commits.
2. Slice 2 is committed on this branch (see section 6). Known limits: custody and
   co-location flags depend on the anchor's baseline state, so a transition
   anchor cannot run the hypothetical holder (the trace says "not tested here").
   Custody tests that pin today's behavior
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
- **Raw-file readers exist outside the loader.** Three browser E2E helpers, two
  scripts and 72 tests parse the source files directly. An adapter to
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

Recommended, **not yet decided** (D1): the author edits readable declarative
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
| D3, CI gating | Layer 3 rule results never block a build |
| D4, when compilation runs | Load time, with the existing fingerprint cache, unless the measured cold load misses 0.5 s |
| Editing draft before D1 | Approved: 1A is drafted by hand in the proposed format and Brandon tries four edits before deciding the model |

Open, for Brandon:

- **D1 (blocks Track B). Model and authoring format.** Decided on a concrete draft,
  not on the abstract comparison: scene 1A written by hand in the proposed format,
  no compiler (Phase 0, last item; Brandon approved this step 2026-11-09).
  Recommendation above.

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
  through Ringer; not yet committed. `storygame/story_package/dependencies.py`
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
  results, but `unread_effect` gives 68 results over about 28 facts, mostly
  pressure-state facts set by pacing events (for example `pursuit_closing_in`)
  that only record that the event happened. The worker called them true gaps;
  that is not established. Whether a recorded-but-unread fact is a gap is an
  authoring decision, and I did not check whether the narrator reads them from
  the fact store. Until decided the rule is noisy on this story.
- [x] **Slice 5, branch report (built 2026-11-10, not committed; added 2026-11-10 after Brandon's review of
  `unread_effect`).** The slice 2 and 4 rules look at one fact at a time. They
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
  branch leaves no trace in 3A, and no unexplained world move. Known defects in
  the first output, to fix next: the same bridge text repeats on every line;
  scene setup (things that appear with no earlier place) is listed as moves
  beside real carried-over moves; and "later scenes read it through nothing"
  ignores reads by the exit transition. First case: 2C, where the rescue branch reaches 3A and the
  transmit branch's declared cost reaches nothing.
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

- [ ] **Editing draft and D1.** Write 1A by hand in the proposed format, in
  `.plans/`, with no compiler: scene entry and beats, one reveal with quiet and
  witnessed variants, its claims and delivery text, a pacing event, the officer
  pressure, the exit and its cross-scene dependency. Brandon tries four edits on
  it: reword a passage; change what a variant commits; change a shared search
  description; follow one consequence into 1B and back. Record where he hesitated.
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
2. **Schema.** Typed records, stable IDs, reference resolution, source maps,
   disclosure boundaries, versioning. Typed relation kinds (hold, know, reach,
   exist, and their negations). Commit-only variants (the 2C finding). Derivation
   rules, each explicit: one fact owner; claim effects default to the source's
   effects with a declared subset allowed; incident costs and advantages derived
   from the named variant.
3. **ID policy for saves.** Which IDs are preserved and which may change. (The
   save-compatibility decision itself is Phase 3.)
4. **Layer 1 audit.** List what `storygame/story_package/models.py` already
   enforces and what the schema adds; record it here.
5. **Coexistence.** Legacy nine-file loading and compiled loading as explicit
   package modes with a per-scene ownership manifest that rejects two owners, and
   no silent precedence. State how the raw-file readers (section 2) keep working
   while both exist.
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
   requirements shown as promise versus check.

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
  `scripts/disclosure_matrix.py`, `scripts/generate_spine_expected_reveals.py`,
  and the tests that name story files.
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

Independent of all phases: validation is about 0.34 s of the 0.36 s load, mostly
recompiled patterns in `_delivery_internal_token`. Compiling them once is a small
fix that can ship on its own at any time.

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
