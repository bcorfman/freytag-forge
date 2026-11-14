# Story authoring, test contracts, and compiled runtime data

Status (2026-11-13): **Phase 0 measured; review-tooling slices 1, 2, 4 and 5
built (slice 3 dropped); D1 decided 2026-11-12, so Phase 1 (schema and compiler
contract) is next.** No story data, test
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
Slices 1, 2, 4 and 5 are built; slice 3 is dropped. Slices 4 and 5 are in PR #761
(branch `story-data-gap-rules`, not merged when this was written). Open items, in
the order to take them:

1. **`unread_effect` is noisy** (68 results over 20 facts on the real package).
   Brandon has not chosen. Recommended narrowing: report first the facts that an
   incident outcome lists under `costs` or `advantages`, because the scene view
   of 2C showed those are the useful results and the pressure-state facts are
   noise. The alternatives are to keep it as information or to drop it. Not
   checked yet: whether the narrator reads the whole fact store (several engine
   modules read `facts.asserted` broadly). The full list of results is pinned in
   `test_real_dependency_results_match_the_audit_inventory`
   (`tests/test_gap_rules.py`); a per-fact snapshot was made on 2026-11-10 but
   not committed because it goes stale.
2. **Run the branch report on the other incidents** (`scripts/branch_report.py
   <incident>`; incidents are in `incidents.yaml`). It has only been run on 2C. Read each
   report against Brandon's rule: if the next scene's state does not follow from
   where the branch leaves off, something is broken.
3. **2C is a story fix, not a tool fix** (Brandon's call): the transmit branch
   leaves no trace in 3A, and both declared costs (`detention_sectors_sealed`,
   `evidence_not_transmitted`) are set and never read. 3A's default entry says "a
   partly unsecured detention sector" after the transmit branch seals them.
4. **Rename "flag" to "rule result"** in the plan, the guide, `gap_rules.py` and
   its output (the branch report already says "result").
5. **The deferred blind run** on 1B.4 (or 2A.4), with Brandon writing the answer
   key.

**Track B, the migration: unblocked by D1** (decided 2026-11-12, section 4). Next:
Phase 1 (schema and compiler contract). The 1A draft ([story-data-1a-draft.md](story-data-1a-draft.md),
revision 2) is the starting point for the schema, not a finished one. What it
leaves out is listed in Phase 1 item 10 and in the
[design reference, section 4](story-data-design-reference.md).

Housekeeping:

1. PRs #759 and #760 (slice 1 and this plan) are merged. Slice 2 (`f403c4ae`),
   slice 4 and slice 5 are in PR #761. The 1A departure hold and the phone
   wording are committed separately on branch `1a-departure-hold` (commits
   `a5515298`, `0a350fe8`, not pushed when this was written); they belong to
   [the 1A plan](1a-password-and-officer-plan.md). The working tree also holds one
   unrelated line in `docs/testing-runbook/local-checks.md`.
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
   **Snapshot candidate, 2026-11-13: the tip of branch `scripted-opening-1a`** (a commit cannot name its own hash; record the merged hash here after merge)
   (not pushed or merged when this was written). It commits the in-flight 1A work
   that had blocked the snapshot: a `scripted_opening` scene field (`plot.md`
   scene 1A, `models.py`, `engine.py`) and 12 test files, 126 tests passing.
   Confirm the snapshot after the branch merges (merge commits keep this hash
   reachable).
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
      is left to the draft. **Not yet written.** Original wording: typed
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
- 2026-11-10. Slice 5 built (section 6): the branch report, after Brandon asked
  for branch analysis and his rule that a next scene's state must follow from
  where the branch leaves off. Slices 4 and 5 are in PR #761. Next steps are in
  "Resume here".
- 2026-11-11. PRs #761 and #762 merged. 1A editing draft written in `.plans/story-data-1a-draft.md` (hand-written, no compiler, nothing reads it). Next step is Brandon's four edits, then D1.
- 2026-11-12. Brandon tried the four edits on revision 1 of the 1A draft (copy and hesitation table in `story-data-1a-draft-edited.md`). Revision 2 of the draft fixes what he hit (shared passage parts, matcher rules and examples, edit 2 rewritten as a story decision, 1B excerpt added, `hands_to_1B` removed). He then said "go ahead with D1": recommendation adopted, Track B unblocked. Not done: he has not re-run the edits on revision 2; the design reference still holds the conditional sketch.
- 2026-11-13. Coverage check of the chosen format against the design reference. The draft covers passage ownership, field separation, fact purpose, claim effect defaults and stable IDs; it only partly covers typed relations and relationship context; it does not cover a root catalog (and differs from the sketch on shared facts), entities, incidents, handoffs and other undrafted parts, or walks 3–6. Compiler, runtime and test redesign are not the format's job and were already in Phase 1 items 6–7 and Phases 2–3. Two risks recorded in the design reference section 4: `examples` written beside the matcher, and search-block overrides that can shrink `leak_terms`. Added Phase 1 item 10 and two Phase 2 items.
- 2026-11-13. Item 10 decisions made by Brandon: matcher examples become accept/reject lists in a separate fixture; a variant override may only add `leak_terms`/`boundaries` entries. Item 10 is fully decided as of this entry: shared facts live where first set (A), typed relations use one shared shape (B), a second slice 2C to 3A is drafted by hand (B, not yet written), and no new authored field for requirement 5 (A, plus exit trigger purposes in the view). The probe behind the accept/reject design ran the draft's word groups through `_matches_all`, not the legacy story file.
- 2026-11-13. Resumed Phase 1. Item 4 (layer 1 audit) written from reading `models.py` and `loader.py`; item 1 (snapshot) found blocked by uncommitted `scripted_opening` work on `main`. No code or story data changed.
