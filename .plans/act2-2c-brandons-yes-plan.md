# Brandon’s yes in the earned 2C observation

Status: implemented on branch `act2-visible-moves` (five local commits), 2026-11-01; see "Result of running this plan".
Date: 2026-11-01. Inspected branch `act2-visible-moves`, HEAD
`5a2a47d1498ccabe2e133f84d6cde3d3542d3d99`.

## Result of running this plan (2026-11-01, branch `act2-visible-moves`)

Run by Ringer (Luna workers; manifests in `scripts/ringer/act2-2c-yes/`). Brandon told me to run the plan, so
E1 and S1 were built together. Local commits (none pushed): bedce9c5, f917b4b0, 2d550147, b0afd8b5, 48a0d869:

- `bedce9c5` **E1** `delivery_variants` (typed model, loader hygiene on every variant text, selector in
  `storygame/runtime/delivery_text.py`, projection, scripted providers, authoring doc, `tests/test_delivery_variants.py`).
  The prerequisite guard and `tests/test_reveal_prerequisites.py` are untouched.
- `f917b4b0` **E1b + S1** one `true_fact_ids` helper (the first patch computed "true" three ways); `k_sl_2c_c_r1`
  gets kept and erased variants (base unchanged); the 2C `entry_variants` are removed; four-state matrix in
  `tests/test_2c_turn_one_copy.py`; `tests/test_2c_ledger_guard.py` documents why a positive-gated sibling is still rejected.
- `2d550147` **H1** stale r2 references replaced by r1 in tests, canon prompt, spine report
  (`observation_committed`), expected-reveal JSON (regenerated: 2C r2→r1, and 2B b_r5→b_r4 because the browser walk keeps
  the name; that JSON was already stale at HEAD), runbook sentence.

**Open defect found and fixed (the plan's "reachability" risk was real).** A player who stalled past the 2B window and
then erased Brandon's name got both ledger facts: the pacing event `audit_recovery_2b` (turn 8) had no check that a
choice was already made, so `bridge_2b_missed_window_recovery` asserted `brandon_name_kept` on top of
`brandon_name_erased`. The variants then overlapped, the observation was hidden, and both canon journeys failed at the
2C reply. Rejected: a worker's `retract_fact` inside the test (it hid the state). Tried and discarded: erase also
retracting kept (the bridge re-asserted it; manifest `r4-manifest.json` is that failed attempt). Fixed in `b0afd8b5`:
`audit_recovery_2b` gets the same `brandon_name_kept == false` and `brandon_name_erased == false` guards as
`audit_nudge_2b`, plus a real-engine test (`tests/test_2c_ledger_guard.py`) that fails without the guard. Audit of
2A/2C recoveries for the same flaw was left to the worker's report; not acted on.

Measured at `48a0d869` (five local commits, none pushed): full suite with coverage gate was run before the shard-manifest
commit: 3,741 passed, 3 failed, 15 skipped, 1 xfailed, coverage 92.74%. One failure was mine and is fixed
(`tests/shard_durations.json` now lists the two new test files). The other two fail identically at `5a2a47d1`, before
this work: `tests/test_affordance_map.py::test_whole_package_findings_match_recorded_gaps` (two extra 2C findings) and
`tests/test_required_storylet_closure.py::test_real_package_closes_over_the_three_act_2_incidents`. Ruff format and
check are clean. `node --test frontend/e2e/*.test.js`: 174 pass, 4 fail, all on stale Act 2 rebuild content and not
this work (`authored-spans` wants an old 2A entry variant; `knowledge-available` wants the removed `k_sl_2c_a_r1`;
`package-clock` wants a `purge_2c` pacing id, now `purge_window_2c`). Not run: live model slices, staging, hosted
E2E, the second full suite after the shard fix.

**Follow-up (same day).** Node tests fixed in `ef7d05b2` (`authored-spans`, `knowledge-available` now uses the only 2C
world_only entry `k_purge_recovery_ready`, `package-clock` uses `purge_window_2c` and the real event order; 178/178 pass,
no assertion removed). Recovery audit for the 2B flaw in the other scenes, `b6ce04b9`: 2A `inspection_recovery_2a` had the
same flaw (convincing outcome after the window got `cover_suspected` from the recovery bridge, which also put a false line in
the 2B opening) and now has the `restricted_corridor_access == false` guard; the new 2A tests fail without it. 2C has no
such flaw: exclusivity holds at every timing, so its data is unchanged. One behaviour recorded, not changed: 2C holds the
scene open until its minimum turn (8) after the neutral recovery fires at turn 6, so a commitment at turn 7 is honoured
and coexists with `purge_recovery_ready`; Brandon can decide to block it. 2A and 2B leave on the turn their recovery fires.
1C was not audited. Final full suite at `01edf723`: 3,766 passed, 2 failed (both pre-existing, listed above), coverage 92.74%.

Next, only if Brandon wants it: preregistered live kept/erased observation-to-choice slices (step 8 below), after
reading the composed delivery text, then merge and staged verification. Separate cleanup: the two stale pytest
failures and four stale node tests above.

## Resume here (original, before the run)

Decide separately whether to approve the new presentation capability in E1 and
its story-data use in S1. The strict requested result has no proved, drop-in
story-data solution that I found. My recommendation is one observation reveal
with fact-selected delivery text, retaining the prerequisite guard unchanged.
This is a **new engine capability**, based on existing conditional-text patterns;
it is not already supported and is not covered by the redesign’s “no new engine
features” decision. If that constraint remains absolute, retain the current
opening variants and neutral observation, explicitly accepting that the requested
ledger-dependent yes has not been delivered.

Only this plan is written. No runtime, tests, story data, generated files, or
runbook were changed. No tests, model calls, deployments, or paid probes were run.
The pre-existing staged prompt and attempted patch, and untracked
`scripts/ringer/phase1/act2-2c-fix-manifest.json`, are left alone. Do not execute
that manifest or apply the archived patch as the implementation of this plan.

## What the guard actually protects

Evidence references below are repository-relative file:line references at the
inspected revision, not claims that the tests passed today.

- `storygame/story_package/obligations.py:8–65` computes required **storylets**
  from canonical bridge/resolution dependencies, then closes over local producers
  of prerequisite facts. This is not a list of knowledge entries every player
  must collect. It includes alternative realizations of a required storylet.
- `storygame/story_package/loader.py:1328–1356` gathers incoming scene sources,
  unions bridge activation `all_facts_true` and asserted-true operations within
  each source, then intersects the sets across incoming source scenes.
- `loader.py:1358–1379` gathers local asserted-true producers from storylet
  realizations, pacing effects, fact deliveries and their costs, and knowledge
  effects. `loader.py:1381–1394` checks **each knowledge entry** belonging to a
  required storylet. Every positive `requires` predicate must be in those entry
  guarantees, local producers, or the scene-entry fact. False predicates are
  not checked by this guard.
- `tests/test_reveal_prerequisites.py:29–32` loads the real package.
  Lines 35–50 add `evidence_gap_development_record == true` to
  `k_sl_2c_d_r3` and require rejection. Erasing the name in 2B can produce that
  cost, but keeping the name does not. Earlier possibility is not an entry
  guarantee. That is the concrete broken-package state the test protects against.
- Runtime checking is separate: `runtime/reveal_eligibility.py:73–98` checks
  established effects, audience, spent source, prerequisites, reach and active
  source; `runtime/knowledge.py:442–459` applies it before projecting candidates.
  Loading a package must not depend on the narrator discovering an unavailable
  prerequisite during play.

The guard is a structural stranded-reveal check, not a complete proof of route
reachability. In particular its source-level bridge union is not a path-sensitive
intersection of all exits from that source; local producer existence does not
prove its own prerequisites can be met. Do not describe it as a full model checker
or broaden it casually on the assumption it already proves all reachable states.

### Why this split fails, and whether it should

`SL-2C-D` needs `rebecca_offer_heard`; `SL-2C-C` supplies it. The dependency closure
therefore makes C required. The attempted r2 has `brandon_name_erased == true`,
which 2C cannot produce and its incoming bridge facts do not guarantee. The
current algorithm correctly rejects it according to its documented contract.

The narrative intent is different from the bad single gated reveal in the
regression: the attempted r1 requires erased=false and r2 requires erased=true;
both perform the same observation and assert `rebecca_offer_heard`. Under normal
Boolean facts this pair covers both values. The pair need not strand the
observation even though one member is unavailable on each branch. A validator
that understood exhaustive alternatives could accept it safely, but this one
does not. Thus this is a limitation of the guard’s per-entry contract, not proof
that conditional narrative alternatives are inherently invalid.

The archived loader patch unions every earlier scene’s producers into the allowed
set. It would accept unrelated optional costs, including precisely the mutation
in `test_reveal_prerequisites.py:40`. Flipping that test from rejection to acceptance
removes the protection instead of proving the pair safe. Reject that patch.

Also distinguish “not erased” from “kept.” The attempted cold r1 covers a synthetic
state with neither ledger fact; plot 2C.2 specifies coldness after refusing erasure.
Do not silently declare these equivalent. Both-true states also need an explicit
policy, not whichever record happens to sort first. The recovery bridge asserts
kept (`storylet-routes.yaml:3121–3133`); the ordinary bridge’s prerequisites
(`3103–3120`) do not themselves encode an exclusive, exhaustive ledger invariant.

## Existing precedents and their limits

| Mechanism | Evidence and behavior | Guard preserved? | Meets the requested observation wording? |
| --- | --- | --- | --- |
| Current neutral r1 plus opening variants | `knowledge.yaml:1550` and `plot.md:536–540`; the opening shows avoidance or held eye contact before the observation | Yes | No. The yes itself remains neutral and even says Brandon looks at Kristin on the kept path. |
| Two reveal entries, as in 1C | `knowledge.yaml:1079–1155`: both require locally producible `facility_proof` and an open window. Different action evidence; r2 additionally establishes a possible Michelle sighting | Yes for 1C; no for the attempted positive erased gate | 1C proves sibling realizations, not earlier-ledger gating of required siblings. |
| 2A, 2B, 3A, 3B entry variants | `plot.md:358`, `441`, `645`, `734`; numbers/route, suspected cover, freed captives, erased build record | Yes | No. These append context on entry, not inside an earned delivery. |
| Conditional pacing realizations | `models.py:598–609`, `engine.py:1278–1308`; `tests/test_pacing_handoff.py:109–178` covers first matching realization/default and event predicates | Yes if no reveal prerequisite is changed | Conditional text is proved, but an event after an observation is not proved to splice a sentence into that observation. It risks wrong timing, duplicate yes, or another turn. Not a drop-in solution. |
| `handoffs.yaml` fallback/cue text | `models.py:675–686`; `handoffs.yaml:272–356`; `engine.py:1580` stages missing-fact delivery | Yes | No conditional text field exists here, and delayed fact recovery is not an earned observation. |
| Two knowledge entries with only negative ledger gates | Existing predicates can express kept=false / erased=false; loader checks only true requirements | Leaves code unchanged but evades its positive check | Not safe as proposed: neither fact gives two matches, both gives none; assumes an invariant not proved by the bridge contract. Do not use as a guard workaround. |
| Split into separately activated storylets; move gates out of knowledge | Storylet activation is fact-driven, `engine.py:1271–1275` | Leaves this function unchanged but moves the dependency outside its check | New authoring arrangement with unresolved coverage/completion risks. No proved precedent found for this use; do not disguise it as a data-only guard fix. |
| Alternative-aware prerequisite validation | Would prove at least one equivalent sibling eligible in every admitted entry state | Changes the guard’s contract | Could support the attempted split, but requires new coverage analysis and negative tests. Larger than a text-only need. Not recommended here. |
| E1 below: one reveal, conditional delivery text | Reuses the idea of fact-qualified text while adding it to knowledge delivery | Yes, unchanged | Yes, subject to new implementation and tests. |

`models.py:532–539` appends the base entry plus **every** matching variant, in
order; it does not replace the base or select one exclusive branch.
`tests/test_entry_variants.py:33–58` tests that additive behavior; its remaining
tests reject unknown/empty prerequisites, blank text and protected-term traps.
The actual current 2B has one suspected-cover variant, 3A one rescue variant and
3B one erased-name variant. The redesign describes more possibilities than are
implemented; do not infer variants from its prose.

The incident’s `observation_knowledge_ids` are validated for existence and scene
membership (`loader.py:1178–1185`). Listing two IDs does not make them exhaustive
alternatives or exempt them from prerequisites. The current 2C list contains r1
and the two D outcomes (`incidents.yaml:72`). Observation itself is not an incident
outcome; only transmit/rescue resolves the choice. Generic incident tests in
`test_incident_engine.py` cover exclusivity, no-outcome states and the min-turn
floor exception; `test_incident_pressure.py` and `test_incident_recovery.py`
cover deadline, neutral pressure and restoration.

Exact handoff requires one eligible match (`candidate_matcher.py:178–204`);
two text matches are not permission to select the first. Cloudflare appends the
selected delivery with its knowledge grounding ID (`cloudflare.py:1499–1539`).
The projector currently copies one static `delivery_text` (`knowledge.py:462–474`).
Knowledge establishment is based on effects, not the selected ID alone
(`reveal_eligibility.py:31–39`): two siblings with identical effects become
established together. A branch-specific permanent `statement` is therefore a
recall risk; use a neutral claim unless branch truth is represented separately.

## Proposed changes, separately reviewable

### E1 — New engine presentation capability; no guard change

Old contract: a knowledge definition has one optional `delivery_text` string
(`models.py:141–162`); projection copies it unchanged.

New contract text to add to the authoring documentation under authored reveal
delivery (this is a proposal, not current syntax):

> `delivery_variants` optionally supplies complete replacement delivery texts.
> Each variant has a non-empty `requires` list of fact IDs and non-blank `text`.
> All required facts must already be true when the reveal is projected. Exactly
> one matching variant replaces `delivery_text`. No match uses `delivery_text`.
> Multiple matches reject the attempted delivery before any facts are committed.
> Variants change wording only. They cannot change eligibility, effects, source,
> knowledge ID, action matching, or scene completion. Only the selected text is
> exposed on the delivery turn.

Old documentation at this location: no `delivery_variants` contract. New: insert
the paragraph above. Require a non-blank base whenever variants are supplied.
Validate registered fact IDs and every text using the existing delivery hygiene,
term and conveyance rules; do not let variants become unchecked prose. Preserve
current behavior byte-for-byte for definitions without variants.

Implementation boundary, not an implementation patch: a shared story-agnostic
text selector, typed schema, loader validation and state-aware projection. Both
exact and semantic handoffs must consume the same resolved candidate text.
Audit all raw `KnowledgeDefinition.delivery_text` readers, including refusal
composition and offline scripted providers, so none silently falls back to the
neutral base after the real selection. Keep neutral knowledge statements for
recall. Do not teach the narrator to interpret `if brandon_name_erased`.

Free checks: new hermetic schema/selector tests with a non-Continuity fixture;
`test_knowledge_projection.py`, `test_candidate_matcher.py`,
`test_cloudflare_transport.py`, `test_markdown_story_package.py`, and the unchanged
`test_reveal_prerequisites.py`. Add composition tests for exact and stubbed semantic
selection, no early/wrong-branch text in prompts, and rejection rollback. Test
save/restore recomputes the same text from facts without adding mutable state.
This code belongs with package-aware projection, not in `worldkeeper`.

### S1 — Story data using E1; independently approve the wording

Keep `k_sl_2c_c_r1` and `SL-2C-C-R1`, their neutral statement, action evidence,
`purge_window_missed == false`, and `rebecca_offer_heard` effect. No r2 is added.
Keep the observation gate on the D outcomes and current incident registration.
Do not apply the attempted patch’s duplicate storylet or prerequisite changes.

Old `k_sl_2c_c_r1.delivery_text` (YAML folding shown as prose):

> Rebecca answers Kristin without taking her eyes off Brandon. "Trust is a luxury. Decide quickly." Her tablet chimes. She reads it, and her face changes. "The purge order. It starts within hours, and my people are on the list." Brandon looks at Kristin, then says, "Yes." The guards stand down, and Rebecca goes to move against Charles. Brandon says, "There is no time to argue. The broadcast uplink is at one end of this corridor. We can send the evidence now. The transfer carts are at the other end. You can free a cart of captives before the guards react. Pick one, Kristin."

New base: **exactly the old text above**, retained for neither-fact synthetic entry.
Old `delivery_variants`: absent. New field immediately after that base:

```yaml
  delivery_variants:
  - requires: [brandon_name_kept]
    text: >-
      Rebecca answers Kristin without taking her eyes off Brandon. "Trust is a luxury. Decide quickly."
      Her tablet chimes. She reads it, and her face changes. "The purge order. It starts within hours, and my people
      are on the list." Brandon says, "Yes." He says it coldly and avoids Kristin's eyes. The guards
      stand down, and Rebecca goes to move against Charles. Brandon says, "There is no time to argue. The broadcast
      uplink is at one end of this corridor. We can send the evidence now. The transfer carts are at the other end.
      You can free a cart of captives before the guards react. Pick one, Kristin."
  - requires: [brandon_name_erased]
    text: >-
      Rebecca answers Kristin without taking her eyes off Brandon. "Trust is a luxury. Decide quickly."
      Her tablet chimes. She reads it, and her face changes. "The purge order. It starts within hours, and my people
      are on the list." Brandon says, "Yes." He glances at Kristin as he says it. The guards
      stand down, and Rebecca goes to move against Charles. Brandon says, "There is no time to argue. The broadcast
      uplink is at one end of this corridor. We can send the evidence now. The transfer carts are at the other end.
      You can free a cart of captives before the guards react. Pick one, Kristin."
```

Both-fact state: E1 rejects ambiguity; it does not pretend one ledger outcome won.
The cold text deliberately removes the old preceding look at Kristin. No new
place, character, object, world placement, narrator rule or judge prompt is added.

Remove the now-redundant opening foreshadowing from `plot.md`. Exact old block:

```yaml
entry_variants:
- requires: [brandon_name_kept]
  text: "Brandon did not look at Kristin."
- requires: [brandon_name_erased]
  text: "Brandon's eyes found Kristin's and stayed there a moment too long."
```

New: empty (delete this block only). Keep entry_text and the canonical 2C.2
paragraph unchanged. This makes the observation carry the requested consequence.

Free checks: package load and authored-text hygiene; kept/erased/neither/both
state matrix through real projection and stubbed composition; compare exact
rendered delivery, not just selected IDs. Verify `Tell Rebecca my answer to her
offer.` earns r1, unlocks D but grants neither commitment nor cost. Verify
`Head to the broadcast uplink and transmit the copied JANUS files.` cannot earn
D before the observation. Then test both transmit and rescue after it.

### H1 — Repair current harness assumptions for one observation ID

These changes are required for either the current single-r1 package or E1/S1.
They are not evidence that E1 works. Keep existing coverage and update its meaning.
Exact replacements below are scoped to these current harnesses, never repository-
wide replacement in historical fixtures or experiment manifests.

| File / current text | Proposed new text or exact removal | Free check |
| --- | --- | --- |
| `frontend/e2e/canon-journey.js`, first 2C command: `Ask Brandon why Rebecca turned against Charles.` | `Tell Rebecca my answer to her offer.` | Offline spine simulation and JS unit tests; preserve all 2B prompts |
| `tests/test_canon_journey.py:61`: `("k_sl_2c_c_r2", "2C"),` | `("k_sl_2c_c_r1", "2C"),` | Both canonical journeys; retain its erased-name 2B path |
| `tests/test_2c_spine_prompts.py:50`, `tests/test_2c_assess_verbs.py:30`: `{"k_sl_2c_c_r1", "k_sl_2c_c_r2"}` | `{"k_sl_2c_c_r1"}` | Both matcher test files |
| `tests/test_2c_assess_verbs.py:54`: `assert len(knowledge["k_sl_2c_c_r2"]["action_evidence"]) == 2` | Delete only that assertion; retain r1 and D evidence checks | Same |
| `tests/test_2c_paths_repro.py:109–110`: r1 and r2 tuples with `("purge_window_missed", "brandon_name_erased")` | One r1 entry: `"k_sl_2c_c_r1": (("purge_window_missed",), ("rebecca_offer_heard",)),` | Paths repro tests |
| `tests/test_markdown_story_package.py:689`, reviewed set member `"k_sl_2c_c_r2",` | Delete only that member | Package tests; add variant-text validation coverage |
| `tests/test_2c_turn_one_copy.py:45`: `assert matched.candidate.id == "k_sl_2c_c_r2"` | `assert matched.candidate.id == "k_sl_2c_c_r1"` plus assert the erased delivery equals S1’s complete erased text | Expand this test to the four-state matrix; do not merely rename the ID |
| `tests/test_spine_expected_reveals.py:36`: `assert "k_sl_2c_c_r2" in expected["2C"]` | `assert "k_sl_2c_c_r1" in expected["2C"]` | Expectation tests; remove r2 from its current-knowledge set at line 53 |
| `scripts/generate_spine_expected_reveals.py:98`: same r2 assertion | Same r1 assertion | Run simulation, then regenerate JSON |
| Generator’s scripted provider: `text = item.delivery_text or item.statement` | Contract: use the selected `handoff.delivery_text`, not the definition’s unresolved base | Exact-text assertion on kept and erased simulations |
| `frontend/e2e/spine-record.js:105`: `c_r2_committed: (committedByScene.get("2C") || new Set()).has("k_sl_2c_c_r2"),` | `observation_committed: (committedByScene.get("2C") || new Set()).has("k_sl_2c_c_r1"),` | JS tests, including rejected and missing bundles |
| `frontend/e2e/scene-runtime.spec.js:216`: `expect(chains.c_r2_committed, "2C must commit k_sl_2c_c_r2").toBe(true);` | `expect(chains.observation_committed, "2C must commit k_sl_2c_c_r1").toBe(true);` | JS unit checks now; staged browser run later |
| `frontend/e2e/spine-record.test.js`: literal `k_sl_2c_c_r2` and property `c_r2_committed` | `k_sl_2c_c_r1` and `observation_committed`, respectively, throughout this file | `node --test frontend/e2e/*.test.js` |
| `scripts/ringer/spine/check_spine_expected.sh:35`: `assert "k_sl_2c_c_r2" in sim["2C"], "2C must expect k_sl_2c_c_r2"` | `assert "k_sl_2c_c_r1" in sim["2C"], "2C must expect k_sl_2c_c_r1"` | Offline expectation check; inspect shell wrapper before invoking |

Generated `frontend/e2e/spine-expected-reveals.json`: old 2C observation member
`"k_sl_2c_c_r2"`; expected new member `"k_sl_2c_c_r1"`. Regenerate from runtime,
never hand-edit or remove unexpected misses to get a green result. Preserve the
other committed 2C outcome ID that the actual walk earns.

Runbook correction, after H1 implementation: in
`docs/testing-runbook/local-checks.md`, replace exactly
`It retains 2C C-R2 and writes sorted per-scene reveal sets.` with
`It retains the earned 2C observation C-R1 and writes sorted per-scene reveal sets.`
Free check: compare that description to the generator assertion and a successful
simulation; no dated test-result entry in the runbook.

Legacy tooling needs semantic review, not a rename:
`scripts/ringer/astra/check_transmit_guard.py:14,27–38` treats r2 as evidence-ready
knowledge and also names removed D-R1/D-R2. New r1 is Rebecca’s observation, not
that historical evidence step. Leave this historical probe unexecuted; retire or
redesign it in a separately scoped task if it is still an active gate.
`scripts/ringer/astra/check_step_b.sh:20` also pins legacy r2. Historical fixture
`tests/fixtures/continuity_initiative_pre_3c_adoption/knowledge.yaml:1700` must keep
its own r2. Old JSON experiment manifests are historical instructions, not current
contracts. Changing a name alone could make their checks falsely pass.

The `observation_committed` report field rename is an interface change: search
report consumers before implementation. If a live consumer needs compatibility,
review a migration explicitly; do not keep a field named r2 that falsely claims
r2 committed. Browser prompt path keeps the name; the Python canon path erases
it. Cover both deliberately instead of changing 2B merely to satisfy an r2 check.

## Tests and order of work

1. Review E1 and S1 separately. Do not relax the guard. If E1 is declined, the
   exact requested delivery remains open; H1 can still reconcile the baseline.
2. Record baseline failures with the focused free commands below. Preserve the
   prerequisite rejection test unchanged. Add a test reproducing rejection of
   the attempted positive-gated r2 on a temporary package, so its limitation is
   explicit. No need to apply the whole archived patch.
3. Implement E1 against a small non-Continuity package first. Test no variants,
   one matching variant, no match, overlapping matches, unknown facts, blank
   text, protected terms and unmet must-convey groups. Test that presentation
   requirements do not become gameplay prerequisites or mutable truth.
4. Apply S1 and H1. Extend real 2C tests with the full ledger matrix, repeat
   observation attempts, pre-observation D rejection, and both D outcomes.
   Through actual 2B routes, cover kept, erased and missed-window recovery into
   2C; do not assume isolated fact injection proves those paths.
5. Verify missed window before observation, observation followed by delay,
   deadline-edge observation, neutral recovery and save/restore. Keep
   `purge_window_2c` at turn 5 and neutral recovery behavior. A required storylet
   surviving its nominal latest turn (`engine.py:1261`) must still respect its
   missed-window fact gate. Confirm no commitment/cost on neutral exit.
6. Regenerate spine expectations after fixing the scripted provider and command.
   Run canon journeys, package/projection/leakage/transport checks and JS unit
   tests. Inspect actual delivered text plus lead-up, not IDs alone. The current
   2C min-turn setting is 8, but resolved incidents can bypass that floor; do not
   lengthen the negotiation by adding filler commands or changing unrelated clocks.
7. Use the quick suite, Ruff and final full deterministic suite per the runbook.
   Update the existing runbook sentence and this plan with actual results.
8. Only under later authorization: preregister live kept/erased observation→choice
   slices plus missed-window/recovery cases; follow the scene-fixing workflow,
   read full prompts and composed delivery, and run its three replicates. Merge
   implementation, wait for the exact main SHA’s staging deployment, then run
   hosted spine/canon verification. No production promotion is part of this plan.

Focused free commands, from repository root, per `docs/testing-runbook/local-checks.md`:

```bash
TMPDIR=/tmp uv run pytest -q tests/test_reveal_prerequisites.py tests/test_entry_variants.py tests/test_2c_turn_one_copy.py tests/test_2c_paths_repro.py tests/test_2c_spine_prompts.py tests/test_2c_assess_verbs.py
TMPDIR=/tmp uv run pytest -q tests/test_markdown_story_package.py tests/test_knowledge_projection.py tests/test_candidate_matcher.py tests/test_cloudflare_transport.py tests/test_act2_knowledge_sources.py
TMPDIR=/tmp uv run pytest -q tests/test_incident_engine.py tests/test_incident_loader.py tests/test_incident_pressure.py tests/test_incident_recovery.py tests/test_pacing_handoff.py tests/test_scene_relative_pacing.py tests/test_canon_journey.py tests/test_spine_expected_reveals.py tests/test_knowledge_leakage_matrix.py
uv run python -m scripts.generate_spine_expected_reveals
node --test frontend/e2e/*.test.js
```

The generator writes its generated JSON; run it only during approved
implementation, after correcting its assertion. New E1 tests join the relevant
existing files or a focused presentation test file, not billed bench scripts.
These are future checks, not results from this investigation.

## What could break and what remains unverified

- Conditional text can bypass validation if only the base is checked. Check every
  variant at load time and the selected composed turn at runtime. Keep protected
  terms, grounding, narrator lead-up exclusion and atomic rollback intact.
- Raw delivery readers can diverge from projection. The offline generator already
  reads the definition directly; an ID-only test would miss wrong ledger prose.
- Shared-effect sibling statements can both appear established. Retaining one
  neutral statement avoids introducing contradictory cold/warm recall claims.
- The current test tree is inconsistent with the current package: stale r2
  expectations remain in Python, generated JSON and hosted spine. This is source
  evidence, not an executed failure count or a claim about deployed staging.
- Erase followed by recovery may expose both ledger facts. Recovery asserts kept;
  I did not run a reachability check to establish whether that combination can
  occur in real play. Test it before shipping the fail-closed overlap policy;
  if reachable, diagnose the ledger lifecycle separately rather than invent a
  precedence rule in the text selector.
- No proof was obtained that all valid arrivals have exactly one ledger fact.
  The base handles neither; both is explicit ambiguity. No guarantee of general
  alternative coverage or guard soundness is claimed.
- Package fingerprint/save compatibility must follow the repository’s existing
  rejection policy; no migration or historical-save rewriting is proposed.
- I did not inspect live recorded prompts or run narrator samples. The smoke log
  records earlier versions: row 25’s one-turn choice does not validate the current
  observation-first scene. New wording’s live quality and semantic matches remain
  unmeasured. No rate can be inferred from those single rows.
- I read the PRD, contributor boundary guides, agent workflow, grounding guide,
  player-input and narrator guides, scene-fixing guide, testing runbook and local
  checks, promotion guide, world-model checklist and relevant historical decision
  excerpts, Act 2 redesign, whole-story pacing, Round 2 smoke log, and the archived
  attempt. Existing placement remains authoritative; this proposal adds none.
- Investigation used the available codebase-memory graph and targeted source
  reads. Serena was not available in the tool catalog; no symbol edits were made.
  No external model documentation or web research is needed for these local-code
  conclusions.
