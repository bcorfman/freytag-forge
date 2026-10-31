# T9h drain condition and contents: separate experiment design (DRAFT 2026-10-30, nothing built, nothing billed)

Status: design only, written after the 30-call confirmation failed its frozen gate. This file follows the stop clause in `.plans/chatgpt-t9h-drain-rejection-plan.md` ("If approved source material fails to suppress those defects, stop and design a separate story-agnostic safety experiment; no proven general condition verifier is established by these artifacts, so none is smuggled in"). It authorizes nothing: every numbered step below needs its own go, the `plot.md:204` edit stays unapplied, and the hosted flag, staging and the full enforced stage are untouched. Labels use the D3 contract in `t9h-drain-full-stage-addendum.md`.

## 1. The problem, with the measured numbers

On `inspect the storm drain` the narrator invents what the world does not declare. Recorded drain prompt, 10 or 15 samples per arm, all labels by me, blind to arm, hash-frozen:

| Run | Control (current text) | Candidate (Details line adds "storm drain opening in the damaged grounds") |
| --- | --- | --- |
| 20-call screen, 19 rows | 6/10 forbidden | 0/9 |
| 30-call confirmation | 10/15 forbidden | 2/15 (rows 13 and 19, borderline) |
| Both | 16/25 (64%) | 2/24 (8%) |

Forbidden kinds: invented ajar or cover state (11 rows), definite interior contents (7 rows: "dark and musty", "leaves and twigs inside", "peering into the darkness"). Player-caused opening or entering: 0 rows in either arm. The location verifier cannot see any of this: J1c accepted the recorded "slightly ajar" reply 5/5, which is correct for location. So V0/J1c is not the tool; this needs a separate check.

Cost of a defect that is caught only by rejection: a rejected drain turn costs 9 model calls and 10 to 32 s (mean 16.6 s over 18 recorded rejections), because the narration is regenerated. At a 64% defect rate most drain turns would need a retry; at 8% few would.

## 2. What is proven and what is not

Proven: material changes this narrator's behaviour (drawer: invented contents 15/15 with none supplied, 0/15 with the real contents; drawer outcome line "Nothing else is under the drawer..." took invented objects from 2/25 to 0; 3B.2 sentence 15/15 vs 4/15); most narrator rules lose their probes (1/15 vs 4/15 and worse); an LLM check of the narrated turn, calibrated on a frozen labeled corpus, works for location (J1c: 55/60 and 60/60 positives, 0/180 negative accepts).

Not proven: that the Details line alone reaches zero (it reached 8%); that any condition or contents check works; that a typed check of the item_facts proposal is acceptable under the rule that every narrated change lands.

## 3. Candidate approaches, ranked by precedent (none is chosen here)

- **X3, a second material arm (strongest precedent).** The drawer outcome line is the closest same-scene-family fix. For the drain it would be an authored statement of what the opening shows from outside, written in ChatGPT Desktop and scored with the existing probe (`drain_details_prose_probe.py`, 10 then 15 per arm). Plot material, so it needs Brandon's approval and is not tried here.
- **X1, a typed check of the narrator's own structured reply (new, measured only offline).** Over the 49 labeled narrations: the reply carried a `condition` entry on the drain in 11 of 18 forbidden rows (10 of 11 ajar or cover, 1 of 7 contents) and in 0 of 31 clean rows. It uses a typed field, no text parsing, no extra model call. It cannot see prose-only defects (6 of 7 contents rows). It conflicts with the standing rule that every condition change item_facts reports must land, so it can only be a detector or a reject-and-retry trigger, and that is a design decision for Brandon, not something to decide here.
- **X2, an LLM check of the narrated turn (calibrated like J0/J1/J2).** A typed Jev question, same plumbing as the location verifier (`ObservationVerifier`, accept strictly above .65, reject strictly below .35, uncertain fails closed): "Does the narration state, as fact, that THING is open, ajar, lifted, covered or entered, or what is inside it, beyond this declared state?" with the world's declared state for THING as context ("declared state: none; contents: none"). Story-agnostic by construction: the declared state comes from the world, no drain text. This is the generalization of the plan's own warning that the relation verifier cannot certify conditions.
- **Ranked last, not proposed:** a narrator rule (most lost), a keyword or regex gate (excluded), an open/closed axis or a gate entity for the drain (the plan says no; the escape needs it passable).

## 4. Proposed experiment, in dependency order

**Step 0, free: freeze one labeled corpus.** Inputs already on disk: 49 labeled narrations (`t9h-drain-details/{screen,confirm}`), the 3 ON-smoke drain replies, and the recorded drain attempts from the five latency runs (42 verified attempts, unlabeled for D3). Adjudication is done by me, per the user's instruction (no ChatGPT Desktop pass): I relabel every row from the blind sheet, which shows only the narration, without opening my provisional labels, freeze that file's hash, and only then join against the provisional labels and report each disagreement. Rows 13, 19 and every "darkness" or "sealed" reading are decided before any score exists. Limit, stated plainly: this is the same reader as the provisional labels, so it checks consistency, not independence; the corpus is labeled by one reader. Result: one corpus, labels hash-frozen.

**Step 1, free: offline X1 measurement and held-out cases.** Count how often a typed `condition` or contents proposal on a thing with no declared axis appears across the whole frozen corpus (a counting script, no model). Build a held-out set that is not the drain: recorded drawer, glove box, door and truck replies that opened or described something in prose (the plan records at least the `inspect the drawer` first attempt that "opens the drawer in prose"), plus authored negatives, so the check is shown to generalize across things and stories (`audits-must-generalize-across-stories`).

**Step 2, billed, small: X2 calibration.** Frozen cases and labels, three question variants (bare; with declared-state context; with context plus a one-line statement that undeclared means not authorized), 5 samples each over the corpus plus held-out. Estimate: 140 cases (100 drain plus 40 held-out) x 3 variants x 5 samples = 2100 calls at the Jev cost seen so far (60 calls ceiling $0.0012), so about $0.04, proposed cap $0.06 and a 2100-call limit, both stated in the preregistration (the earlier 735 calls and $0.015 covered only the 49-row probe set). Hash-locked cases, `--confirm`, no rerun, partial run = inconclusive.

**Step 2 gate, numbers chosen by Brandon 2026-10-30 (denominators restated on the full corpus; still needs his go to build and run Step 2).** Each case's 5 samples combine into one score, the per-case median. Rejected means median strictly below .35; accepted means median strictly above .65. On the 100-row drain corpus (54 forbidden, 46 clean): at least 49 of 54 forbidden rejected, and at least 42 of 46 clean accepted (41 of 46 is 89.1% and fails). On the 40 labelable held-out rows (10 forbidden, 30 clean): at least 9 of 10 forbidden rejected and at least 27 of 30 clean accepted. Each of the four conditions must hold, for the question variant that is declared the candidate before scoring (a variant that wins one corpus but not the other does not pass). No separate authored-negatives clause (decided 2026-10-30). No threshold, label or denominator moves after seeing scores.

**Step 3, free then billed: integration.** Only if Step 2 passes. Free: wiring, payload and rollback tests; a rejected turn still leaves equal state digests and at most two logical attempts. Billed: the OFF/ON engine smoke (3 replicates, caps as before) with the new check on versus off, hedges and batching identical, counting first-attempt acceptance and latency. A check that passes but turns most drain turns into two-attempt turns fails on cost, so Step 3 is also where the cost question is answered (with and without any approved material change).

## 5. What this cannot establish

A calibrated check shows detection on these cases, not that every inspection of every opening is safe, and not that the prose is good. One labeler's blind reading is adjudicated in Step 0 but is still small-sample (49 rows, 18 forbidden). The smoke OFF arm never completed a clean 3-replicate run (two Worker timeouts), so ON-versus-OFF latency is not yet comparable.

## 6. Decisions needed from Brandon

1. Approve Step 0 and Step 1 (free). Recommended.
2. Approve the Step 2 gate numbers, call limit and cap, or change them.
3. Whether X1 may ever be a runtime reject-and-retry trigger given "every change the reply reports must land", or only an offline detector.
4. Whether to also try X3, a drawer-style outcome line for the drain, in ChatGPT Desktop. The plan says plot changes need his approval.
5. Whether the `plot.md:204` Details line (8% residual) is wanted as a layer under the check, once Step 3 can measure the cost.

## 7. Results of Steps 0 and 1 (2026-10-30, free, no model call; artifacts under `bench/results/environment-narration/t9h-drain-condition/`)

**Step 0, drain corpus (`corpus/corpus-adjudicated.json`, 100 rows).** I relabeled every row from the blind sheet (narration only) without opening my provisional labels, froze the hash (`corpus-sheet/labels.freeze.json`), then joined. On the 49 provisional rows the forbidden/clean call agreed on all 49; the only differences were 4 informational `speculative_only` flags and one `asserts_definite_contents` flag on a row that was already forbidden for being ajar. Same reader as the provisional labels, so this is a consistency check, not independence (single labeler). Forbidden rates:

| Rows | Forbidden |
| --- | --- |
| Probe control arm (screen + confirmation) | 16 of 25 |
| Probe Details-line candidate arm | 2 of 24 |
| Latency-run attempts (hedge-short, all-on, on-2, off-2) | 30 of 36 |
| Hidden-clue smoke attempts | 3 of 6 |
| Earlier drain smoke (OFF 6, ON 3) | 3 of 9 |
| All | 54 of 100 (35 ajar or cover, 22 contents, 2 opening; rows can carry more than one) |

The real game path (latency attempts) is at least as bad as the probe's control arm. The three followup-smoke ON narrations (`t9h-drain-followup`) are not in this corpus.

**Step 1, typed-field count (`x1/x1_count.json`).** Reproduced the hand measurement: 18 forbidden and 31 clean rows among the 49 probe rows; a `condition` entry on the drain in 11 forbidden and 0 clean rows; the undeclared counts equal the raw counts because the drain declares no state. X1 can only be measured on rows with an attributable raw reply, which is why the 51 engine-run rows are excluded.

**Step 1, held-out set (`heldout/heldout-labeled.json`, `heldout-sheet/labels.freeze.json`).** 49 narrations about the drawer, truck, passenger seat and laptop (40 real, 9 authored). Two Ringer fixes were needed before labeling was meaningful: each row now carries its declared state, the player's command and whether the engine opened the thing that turn (read from recorded fields), and the sheet shows them with a clean `[thing]` mask. 40 rows are labelable; 9 are excluded because their source files do not record that metadata (3 defect-probe drawer rows, 4 seat rows, 2 authored). Contract used: forbidden means the narration states the thing is open, ajar, lifted or entered, or shows its contents, when the engine did not open it that turn. The recorded `open_state_after` cannot count as authorization, because it also reflects the narration's own claim landing. Result: 10 forbidden (drawer 5, truck 4 of which 3 are authored, laptop 1), 30 clean.

**Caveats found.** (1) Only 10 forbidden held-out cases, so a "90% of held-out forbidden" gate means 9 of 10 and cannot be read as a rate. (2) The authored "negative" original for the truck opens the door and peers inside, which the contract calls forbidden, so it is labeled forbidden against its authored note. (3) The held-out narrations are 70B probe or smoke outputs, not a different model. (4) One reader, no second labeler. (5) "Intact", "old and rusty" and exterior debris are clean; "darkness inside", "too dark to see", "empty except water" are contents, applied the same way in both passes except one flag that did not change a verdict.

**Effect on Step 2 (decisions for Brandon).** The proposed gate (17 of 18 drain forbidden rejected, 90% of clean accepted, 90% of held-out forbidden rejected) stands but should be read as: drain forbidden 17 of 18 (94%) scales to 51 of 54 on the full corpus, and a 90% floor is 49 of 54; held-out forbidden 9 of 10 is a smoke-level check. Decided 2026-10-30: samples combine by per-case median, and the separate authored-negatives clause is dropped, so the gate has no undefined terms left; the remaining open choice is the gate numbers and denominators above. Say whether to keep these numbers, enlarge the held-out set first, or restate the gate on the full 100-row drain corpus plus the 40 held-out rows. Step 2 stays unapproved and unbilled.

## 8. Step 2 first run: stopped by an upstream rate limit (2026-10-30; `bench/results/environment-narration/t9h-drain-condition/step2/`)

The 2100-call calibration (preregistration `t9h-drain-condition-judge-prereg.md`, frozen before any score) stopped at call 246 on an upstream HTTP 429, not the local budget guard: Workers AI returned "Unified billing rate limit exceeded for this gateway. Please reduce request rate or use BYOK." The probe sent about 5 requests a second with no pacing. Spent $0.0069 of the $0.06 cap. By the preregistration the run is **INCONCLUSIVE (partial)**; the gate report prints no pass and no medians, because the calls run sample-major and only sample 0 of the first 82 drain cases (all three variants) was reached. The rows are kept untouched and the preregistration's no-rerun rule is not overridden by me.

Information only, single sample per case, 82 of the 100 drain cases, no held-out cases, so **not a gate result**:

| Variant | Forbidden (43 cases): rejected below .35 | Clean (39 cases): accepted above .65 |
| --- | --- | --- |
| A bare | 41 | 17 (20 uncertain, 2 rejected) |
| B declared state (the candidate) | 42 (1 accepted) | 39 |
| C declared state plus support rule | 40 (1 accepted, 1 uncertain) | 37 (2 uncertain) |

Two facts for planning a complete run: (1) the observed cost is about $0.0000282 per call, so 2100 calls cost about $0.059, not the $0.04 I estimated, and the $0.06 cap would be hit near the end; (2) the probe needs request pacing (for example a minimum interval between calls) to stay under the gateway limit. A complete run would be a new run in a fresh directory with the same frozen cases, variants, gate and Variant B as the candidate; only pacing and the cap change, and the addendum would say so. It needs the user's explicit go because it spends again and overrides the no-rerun rule.

## 9. Step 2 complete run: Variant B FAILS the frozen gate (2026-10-30; `step2-complete/`, 2100 of 2100 rows, no stop reason, $0.0587 spent, paced at 0.5 s)

Same frozen cases, variants and gate as the first run; only pacing and the cap changed (preregistration addendum). Per-case median of 5 samples; accepted above .65, rejected below .35.

| Variant | Drain forbidden rejected (gate 49 of 54) | Drain clean accepted (gate 42 of 46) | Held-out forbidden rejected (gate 9 of 10) | Held-out clean accepted (gate 27 of 30) |
| --- | --- | --- | --- | --- |
| A, bare | 50, pass | 24, FAIL | 10, pass | 10, FAIL |
| **B, declared state (the candidate)** | **52, pass** | **46, pass** | **10, pass** | **19, FAIL** |
| C, declared state plus support rule | 51, pass | 46, pass | 10, pass | 17, FAIL |

**Verdict: FAIL.** Variant B passes three of the four conditions and misses the held-out clean one (19 of 30; the gate needs 27). No variant passes. On the drain itself, which is the target, B rejected 52 of 54 forbidden narrations (1 accepted, 1 uncertain) and accepted 46 of 46 clean ones. The declared-state context is what matters: the bare Variant A accepted only 24 of 46 clean drain narrations.

**Diagnosis of B's 11 held-out clean cases that were not accepted (informational, after the fact; nothing here changes the verdict).** 5 rejected, 6 uncertain. They cluster:
1. Engine-opened drawers described open with their contents (3 cases, medians .46 to .57): the declared sentence says the engine opened it, but the judge stays uncertain.
2. The designed find: "something taped to the underside of the drawer" is the memory card (hidden under the drawer), and the declared sentence does not say where hidden items are, only a count (3 cases).
3. Truck and passenger-seat cases that mention the laptop on the seat (4 cases): the declared sentence gives a count of declared items ("2 declared items"), not their names, so the judge cannot tell the laptop is declared.
4. One case with unrelated off-topic prose ("starts the truck and heads for the park").
So most misses look like an input limit of my declared sentence (counts, not names, no hidden-item location), not a failure to detect forbidden states. That is a hypothesis, not a measured result.

**What this does not allow.** The 40 held-out cases are now spent as development data: any change made after seeing these misses, then re-scored on the same 40, would be tuning on the test. A v2 (declared sentence that names the declared items and says where hidden items are) would need a new preregistration and a NEW held-out set of drawer, truck, seat and laptop narrations that nobody has seen, with fresh blind labels. The drain set does not need that, because the drain declares nothing.

**What the experiment settles for the drain.** A calibrated typed Jev question with the declared state as context separates the drain's forbidden and clean narrations at 52 of 54 and 46 of 46 on a 100-row corpus. It has not been shown to generalize to other things. Nothing is wired into the engine; Step 3 (integration) is not approved and is not justified by a failed gate on its own.

## 10. Draft v2: scope the check by declared properties (2026-10-30; DRAFT, not preregistered, nothing built or billed)

Prompted by the user's point that the drain is a different kind of thing from objects that contain or have an "under" property, and by the diagnosis in section 9. The step 2 gate mixed two jobs: flagging any open, ajar or "inside" claim on a thing that declares nothing (the drain), and matching a narration against a thing's declared contents (the drawer, the truck). Variant B did the first well (drain: 52 of 54 forbidden rejected, 46 of 46 clean accepted; held-out things that declare nothing: 3 of 3 clean accepted) and the second badly, because my declared sentence reduced a drawer's named contents to a count and the truck's two seats to "2 declared items".

**Property vocabulary, taken from existing sources rather than invented.** `.plans/chatgpt-t9h-drain-rejection-plan.md` separates, for the drain, four things: no open/closed axis, no declared contents, no completeness promise (`contents_complete`, which the passenger seat in `world.yaml` declares), and `fixed` (which "prevents relocation; it does not mean sealed, closed, empty, or impossible to enter"). It also separates four behaviours (actual opening, invented initial condition, asserted contents, tentative speculation) and three relation classes in the location verifier (scene-level, specific-place, held). `docs/world-model-grounding.md` gives the declaration fields: `kind` (container, supporter, vehicle, seat), `fixed`, `contents`, `hidden`, `axes` (two-pole states), `unavailable`, and says a container brings its visible contents "so the turn that opens it can show what is really inside", i.e. the engine already owns what a container shows. The plan has no object-class taxonomy for the check and does not propose scoping it; this section does.

**Superseded scope (2026-10-30):** the class is now "things of declared kind `opening`" (section 11), and the experiment below is preregistered with that class in `t9h-opening-condition-v2-prereg.md`. The absence predicate that follows is kept only as history.

**Proposed class, a predicate over those world fields, with no object names:** a thing is in scope when it is `fixed: true` and declares no `kind`, no `openable`, no `contents`, no `contents_complete`, no `axes` and no `hidden` parts. In `continuity-initiative` that is `storm_drain`, `back_door`, `house_gate`, `facility_gate` and `service_gate`. The park bench and the passenger seat declare a seat kind and are out; the drawer, truck and laptop declare kinds, contents or axes and are out. Containers keep the engine-open and material mechanisms already in place.

**Policy this check encodes (a decision, not a measurement):** for a thing in that class, a narration that states it open, ajar, lifted, covered or entered, or states what is inside it, is unauthorized, because the world declares nothing that would support it. The world model itself leaves undeclared conditions unscored and the plan says not to add an open/closed axis to the drain just to get a boolean; this policy sits on top of that and is the author's call.

**Proposed experiment:** keep the Step 2 judge (Variant B, wording unchanged, declared sentence for this class only: the thing has no open or closed value, no declared contents and is fixed in place). New unseen held-out set: real narrator narrations for `inspect the back door`, the house gate, the facility gate and the service gate, about 10 each (40 narrations, about $0.05 at the screen's $0.0012 a call), labeled blind with the D3 contract, then judged 5 samples each (200 calls, under $0.01). Proposed gate: at least 90% of forbidden narrations rejected and at least 90% of clean narrations accepted by per-case median, with at least 10 of each, else INCONCLUSIVE. The drain result from the complete run stands as the in-class evidence already collected. Needs the user's approval of the gate terms and the cost before a preregistration is written.

## 11. Decision (2026-10-30): give the fixed openings a kind and scope the check by kind (nothing built, edited or billed; supersedes the class definition in section 10)

**Why section 10's class is replaced.** Section 10 defined the class by absence: `fixed: true` and no `kind`, `openable`, `contents`, `contents_complete`, `axes` or `hidden` parts. That is brittle. Adding a declaration to the drain would silently drop it from the check, a forgotten declaration would silently add a thing, the class was read off one story, and the five members share no declared fact.

**The cause is a missing declaration, found in `data/stories/continuity-initiative/world.yaml`.** `back_door`, `house_gate`, `facility_gate`, `service_gate` and `storm_drain` carry only `fixed: true` and no `kind`, although the story already declares sub-kinds (`desk`, `seat` under `kinds:`) and `docs/world-model-grounding.md` says "Pick the kind that fits ... or a story sub-kind". The same guide says to mark doors `fixed: true`, which is how doors were declared kindless. History: the drain and maintenance gate were declared in 89c9f164 (2026-10-05), the back door in c29c2f7b (2026-09-26), both before this experiment. The engine base kinds (`worldkeeper.BASE_KINDS`) are entity, area, character, group, thing, container, supporter, furniture, vehicle; there is no door or opening kind.

**Decision to record (direction only; the user has not yet said go to the edit):**
1. Add a story sub-kind to `world.yaml` `kinds:`, working name `opening`, `is: [thing]`, `fixed: true`, with no open/closed axis and no contents. Set `kind: opening` on `back_door`, `house_gate`, `facility_gate`, `service_gate` and `storm_drain`. Change only those entries and the `kinds:` block, because `world.yaml` already holds the user's unrelated uncommitted edits (hidden: true on the bench clues, `bench_clues_recovered`).
2. Redefine the v2 scope as "things of kind `opening`" instead of the absence predicate. The policy in section 10 (an open, ajar, lifted, covered or entered claim, or a claim about what is inside, is unauthorized for these things) is unchanged and remains the author's call. Section 10's proposed experiment (40 fresh narrations, blind labels, 200 Variant B judge calls, 90% / 90% gate with at least 10 of each) is unchanged, except that the class is read from the declared kind.
3. Do not add an open/closed axis to the drain to get a boolean (the ChatGPT drain plan warns it conflicts with the later earned escape).

**Checks owed before the edit (free):**
- Does worldkeeper accept a story sub-kind of `thing` that has no relation (no "in" or "on")? Is the `fixed` default inherited from the kind, or must each entity still declare `fixed: true`?
- Does adding the kind change any recorded narrator prompt or fixture (the recorded prompts and `tests/fixtures/place_feed/baseline_prompts.json` are dirty and used by benches), the loader checks at `storygame/story_package/loader.py:1471`, or the typed `condition` counts? A before-and-after prompt comparison for the drain, a gate and the opening scene settles it.
- The edit goes through Ringer (standing rule) and the focused tests; the full suite stays for the end.

**Idea from Inform 7, flagged as not project-proven** (recalled, not re-read this session): kinds carry explicit default properties (a door usually closed and openable, a container usually open and unopenable, scenery fixed in place), and check, carry-out and report rules are separate so report text never changes state. This supports giving the openings an explicit kind. It is a technique new to this project (per `recommend-only-proven-techniques`), and it does not remove the need for the narration check, because the narrator invents prose Inform never generates.

**Still not approved, so not started:** the `world.yaml` kind edit, the v2 preregistration, the 40-narration generation (about $0.05), the judge run (under $0.01), Step 3 integration, the hosted flag, staging, the full enforced stage, and the `plot.md:204` Details edit.

**To resume:** (a) run the two free checks above; (b) if both pass and the user says go, make the five-entry edit through Ringer; (c) rewrite section 10's scope text and write the v2 preregistration with the kind-based class and the unchanged gate; (d) get the user's approval of gate and cost; (e) generate the narrations, then label blind (Claude labels, per `claude-adjudicates-drain-labels-not-chatgpt`).

**Resume step (a) done (2026-10-30, free, no model call).** Trial edit applied to `world.yaml` (a `kinds:` entry `opening`, `is: [thing]`, `fixed: true`, and `kind: opening` on the five entries), the focused tests run, then `world.yaml` restored byte for byte (sha256 checked). Results:
- Worldkeeper and the loader accept a relation-less `thing` sub-kind. `fixed` is inherited from the kind (`worldkeeper/model.py:207-223`), so the five entries could drop their own `fixed: true`; the trial kept them.
- No prompt drift: across 19 focused files (prompt goldens in `test_place_scoped_feed.py`, `test_package_view_scope.py`, `test_narration_json.py`, `test_narration_corpus.py`, `test_environment_baseline.py`, `test_defect_probe.py`, plus the drain payload fixtures) the only new failures were 5 in `tests/test_world_placements.py`, all from its `placement_package` helper replacing `world["kinds"]` wholesale with `desk` and `seat` ("item 'back_door' has unknown kind 'opening'"). The real edit must change that helper to keep the story's kinds (one-line test change). The 6 failures already known on the dirty tree were unchanged.
- The typed `condition` counts read recorded rows, not the package, so they are unaffected.
Next: step (b), the five-entry edit plus the helper fix through Ringer, waits on the user's go.

**Correction and step (b) done (2026-10-30).** My step (a) note above miscounted: the trial's new failures were 4 in `test_world_placements.py` (the helper) plus 1 schema golden, `tests/test_package_view_scope.py::test_unmodified_package_schema_is_byte_identical`, whose hash covers the world schema. No narrator prompt golden changed. Step (b): Ringer run `t9h-opening-condition-v2` round 1 (`run-t9h-opening-kind.json`, Luna high) made the `world.yaml` edit (the `opening` kind plus five `kind: opening` lines, nothing else; verified against the backup in `bench/results/environment-narration/t9h-opening-v2/world.before.yaml`) and the helper fix; its check failed only on that golden. The schema diff before and after is exactly the new kind and the five entities' `kind` field, so I updated `EXPECTED_SCHEMA_HASH` to `b7763234...0ecfb` by hand (one line), and the check (`check_t9h_opening_kind.sh`) then passed: 324 passed, the 6 known failures deselected. Step (c): preregistration `t9h-opening-condition-v2-prereg.md`, approved by the user ("Go ahead with all").

## 12. v2 result: the opening-kind check PASSES (2026-10-30)

Steps (b) to (e) done under the user's "Go ahead with all". Generation `generate-2` 40/40, no failed calls, $0.0423 (plus $0.0022 for the partial `generate`); blind labels by Claude frozen (sha256 `248f923e...4258`): 19 forbidden, 21 clean; cases locked (`ccec34d0...e2b3`, 40 cases); judge 200/200 rows, no stop reason, $0.0059. **Verdict PASS: forbidden rejected 19/19, clean accepted 21/21, no uncertain case.** Per thing: back door 9 clean accepted (including every "forced open" reveal narration) and 1 forbidden rejected; facility gate 9 and 1; house gate 3 and 7; service gate 0 clean, 10 forbidden rejected. Total billed for v2 $0.0504. Full record, amendments and limits: `t9h-opening-condition-v2-prereg.md`. Two more golden updates came from the kind edit: `tests/test_world_model.py` lists the story's entity kinds (`opening` added) and the schema hash in `tests/test_package_view_scope.py`; both checked against the schema diff, which is only the new kind. Quick suite after all changes: 3251 passed, 7 failed, all seven recorded before this work (fixed_refusal 2, observation_open_step 2, search_opens_drawer 2, hidden_bench_1b2_capture 1). Not started and still needing the user's go: Step 3 integration (scope the Variant B check by kind `opening`), the hosted flag, staging, the full enforced stage and the `plot.md:204` Details edit.

## 13. Step 3: the opening check is wired behind a flag; the live smoke shows the narrator still invents (2026-10-30)

Approved by the user ("Go ahead"). Built through Ringer (`t9h-opening-check-wiring`):
- `opening` is now an engine base kind in worldkeeper (`BASE_KINDS`, fixed by default), so the shared runtime does not depend on this story's vocabulary; the story's `kinds:` entry was removed and the five things keep `kind: opening`; the grounding guide names the kind.
- `storygame/runtime/opening_check.py` holds the measured Variant B question (byte-identical, tested against the probe) and state. With `FREYTAG_OPENING_CHECK=1` (off by default), `ObservationVerifier` asks one Jev request per opening the command refers to (at most 2 per attempt, concurrent with the relation request); a non-accept verdict fails the attempt through the existing retry/reject path; verdicts are recorded in preview and shadow rows. `live_baseline.py --opening-check` and routes `observe_service_gate_1b` and `observe_back_door_1a` were added.
- Full suite in the CI simulation: 3831 passed.

**Live smoke** (`enforce_t9h_opening_check.sh smoke`, enforcing verifier, scene state and opening check on, 3 replicates per route, $0.0233; `bench/results/environment-narration/t9h-opening-check/smoke`): storm drain 1 of 3 turns committed, service gate 0 of 3, back door 3 of 3. The check judged every attempt as a reader would: all "slightly ajar" or "pushes it open" attempts rejected (scores 0.04 to 0.09), clean attempts accepted (0.74 to 0.91), one back-door attempt uncertain (0.57) then accepted on retry. The failure is upstream: the narrator invents "ajar" on nearly every gate and drain inspection and the generic retry repeats it, so enforcing the check alone turns those inspections into failed turns. Not shippable on until the narrator stops inventing the state. Options are in the plan's next-step line.

## 14. Side by side: retry fact vs THINGS material (2026-10-30; $0.0727 billed for both arms)

The user chose to compare both fixes. Each sits behind its own flag, off by default: `FREYTAG_OPENING_RETRY_FACT` (after a rejected opening verdict the retry feedback states "The <thing> has no open or closed state and nothing inside it." and names no word from the rejected reply) and `FREYTAG_OPENING_THINGS_FACT` (a command-referred opening's THINGS line gets " It has no open or closed state and nothing inside."). Live enforced smoke, opening check on, 5 replicates per route (baseline 3), `bench/results/environment-narration/t9h-opening-check/{smoke,retry,things}`:

| Arm | Drain committed (first try) | Service gate | Back door | Median turn | Over 10 s |
| --- | --- | --- | --- | --- | --- |
| baseline (check only) | 1/3 (1/3) | 0/3 (0/3) | 3/3 (2/3) | 7.8 s | 3/9 |
| retry fact | 5/5 (0/5) | 5/5 (0/5) | 5/5 (4/5) | 9.4 s | 6/15 |
| THINGS material | 5/5 (2/5) | 5/5 (4/5) | 5/5 (1/5) | 7.5 s | 2/15 |

Reading: both arms commit every turn. The retry fact never changes the first attempt (the narrator still invents "ajar" first on every gate and drain turn), so every such turn pays a second narration. THINGS material stops most inventions on the first attempt and is the faster arm. Its four back-door retries were all `uncertain` (0.53 to 0.61) on the "forced open" reveal wording, the known gray zone where the judge does not see the story's reveal; the retry then accepted. Accepted narrations read clean by eye in both arms. Small samples (5 per route); this is a smoke, not a gate. Recommendation: combine the two (material first, retry fact as the fallback), and look at the back-door uncertainty (for example give the judge the authored reveal as part of the declared sentence), then run one combined smoke.

## 15. Combined smoke: THINGS material and retry fact together (2026-10-31; $0.0348 billed)

The user said "turn on both, run combined smoke". Stage `combined` of `enforce_t9h_opening_check.sh` (both flags, port 8816, 5 replicates per route), Ringer run `run-t9h-opening-combined.json`, `bench/results/environment-narration/t9h-opening-check/combined`. No stop reason; integrity check PASS. The back-door reveal was not added to the judge's declared sentence (not asked for).

| Arm | Drain committed (first try) | Service gate | Back door | Median turn | Over 10 s |
| --- | --- | --- | --- | --- | --- |
| THINGS material (section 14) | 5/5 (2/5) | 5/5 (4/5) | 5/5 (1/5) | 7.5 s | 2/15 |
| combined | 4/5 (1/5) | 5/5 (5/5) | 5/5 (3/5) | 7.3 s | 3/15 |

Reading: gates are solved (5/5 first try). The drain is now the weak route, and its failure has changed: no attempt says "ajar" any more; the rejected attempts have Kr "peer into" the drain and see it "dark and quiet" or "too dark to see anything inside" (scores 0.10 to 0.25, one uncertain 0.50). The judge treats looking inside as describing an interior, consistent with the D3 contract, and the THINGS sentence "nothing inside" does not stop the narrator looking in. One drain turn failed both attempts (both "peers into"), so the turn was rejected. Accepted drain retries all have Kr stand beside it and look down at an ordinary drain. Back door: two retries, one uncertain (0.59) and one rejected (0.27, "noticing it has been forced open"), both on the reveal wording; both accepted on retry. Small samples; the drain difference from the THINGS-only arm (2/5 vs 1/5 first try) is within noise. Open question for the user: whether "peers in and sees only darkness" is a defect at all (the check says yes, a reader might say no). If yes, the drain needs material that removes the invitation to look inside; if no, the declared sentence or the question needs to allow seeing darkness.

## 16. Policy change: looking into a dark opening is allowed (2026-10-31; registered before any billed call)

The user's decision: "I'd let the check allow looking into the drain's dark opening, while still rejecting invented states like ajar, a lid or a grate opened." Reason: in the story the drain is the passage Kr and Br escape through in 1B.4 (`plot.md:241-243`, `knowledge.yaml:923-927`), so seeing darkness in it invents nothing.

**Label rule (D3 amended).** `asserts_definite_contents` no longer covers perceiving only darkness or nothing inside: "too dark to see anything inside", "peers into the darkness", "nothing visible", silence. It still covers anything specific perceived inside: a smell ("musty", "decay"), water or its sound, debris, leaves, objects, "empty", "hasn't been used". `opens_or_enters` and `invents_open_state` are unchanged (ajar, lid or grate off or opened, pushed open, entering). Silence ("dark and quiet") is counted as perceiving nothing; flagged for the user.

**Relabel (by Claude, applying the rule above to the narration text only).** Of the 140 Step 2 cases, 22 mention darkness; 11 were forbidden only for darkness (their adjudicated `final_label` has only `asserts_definite_contents`) and become clean: drain-row-030, 038, 051, 054, 056, 061, 070, 080, 081, 089, 090. The other 11 stay forbidden for smell, interior state, sound of water, debris or ajar. The two v2 opening cases that mention darkness stay forbidden (ajar and pushed open). No other label changes.

**Wording.** New Variant D = Variant B with "darkness" removed from the forbidden examples and "looking into it and seeing only darkness or nothing" added to the consistent list. The runtime check switches from B to D; B stays in the probe as the historical variant.

**Gate (same thresholds as v2).** Cases: the 100 drain cases relabeled plus the 40 v2 opening cases (`cases-v3.jsonl`, locked). Five samples per case, median score. PASS when at least 90% of forbidden cases are rejected and at least 90% of clean cases are accepted, on the drain and opening sets together, and the 11 flipped cases are reported on their own line. The 40 Step 2 held-out cases (other kinds, out of the runtime's scope) are judged and reported only. Partial run: INCONCLUSIVE. Cap $0.05. On PASS, one combined live smoke (same as section 15) with D.

**Result (2026-10-31): Variant D PASSES, narrowly; $0.0273 judge + $0.0352 smoke.** Judge 900/900 rows, no stop reason (`bench/results/environment-narration/t9h-opening-v3/report.md`). Gate: forbidden rejected 56/62 (minimum 56), clean accepted 75/78. **The 11 relabelled darkness cases: 11/11 accepted.** No false accepts in the gated sets. All six forbidden misses are `uncertain`, not accepted: four are the same "dark and musty ... hasn't been used" narration (medians 0.48 to 0.64), plus "hasn't been sealed off" (0.64) and "leaves and twigs clogging the grate" (0.45). So the darkness allowance softened the judge on a smell sitting next to darkness. Clean misses (also uncertain): one back-door reveal (0.64) and two house-gate "checks the latch and finds it securely locked" (0.60, 0.65). Held-out set (other kinds, out of the runtime's scope, not gated): forbidden 10/10, clean 18/30 accepted, 6 false rejects on drawers, truck and seat. The runtime fails an attempt on any verdict other than accept, so in play an uncertain forbidden attempt is still retried: on the gated sets D let no forbidden narration through, and costs a retry on 3 of 78 clean ones.

**Combined smoke rerun with D** (`combined-d`, same as section 15): drain 5/5 committed (first try 1/5), service gate 5/5 (5/5), back door 5/5 (2/5); median 8.3 s, 4/15 over 10 s. Every rejected drain attempt claims something specific inside ("empty", "musty", "smell of decay", "faint smell of damp earth"), which the amended rule still forbids; no attempt in the run showed only darkness, so the smoke does not exercise the new allowance (the judge run does). Back-door retries are again on the reveal wording (0.20 to 0.56).

## 17. Policy change 2: describing the inside of an opening is allowed (2026-10-31; registered before any billed call)

The user's decision: "the smells and empty interior are fine for the drain". **Label rule (D3 amended again).** `asserts_definite_contents` now covers only a distinct object or person placed inside as fact (a note, a bag, a phone, a tool, a body, a clue), because those would become story items the plot does not have. Describing what it is like inside (darkness, smells, sounds, water, dirt, leaves, debris, "empty", "hasn't been used") is clean. `opens_or_enters` and `invents_open_state` are unchanged. The rule is worded for every thing of kind `opening` (the runtime stays story-agnostic); for a gate or door the inside is only visible once it is open, which stays forbidden.

**Relabel (Claude).** 8 more drain cases were forbidden only for contents and none places a distinct item inside: drain-row-002, 008, 034, 036, 044, 055, 077, 083 become clean. No v2 opening case was forbidden only for contents (4 have contents, all also open or ajar). Cases `cases-v4.jsonl` (drain 65 clean / 35 forbidden, opening 21 / 19, held-out unchanged), lock `lock-v4.json`; all 19 relabelled ids in `relabelled-v4.json`.

**Wording.** Variant E, pinned in `drain_condition_judge/variant-e-question.json`: forbids only the open states and a distinct object or person inside; names inside description as consistent. The runtime switches from D to E.

**Gate.** Same as section 16 (drain plus opening, 90% / 90%, complete run), relabelled cases on their own line, held-out reported only. Cap $0.05. Then the combined live smoke again (`combined-e`).

**Addition before any run (2026-10-31):** the user: "i think 'forced open' is fine for the back door as well." The back-door inspect turn delivers authored text that says "the back door was forced". So the check now receives the turn's authored delivery text when there is one: the declared sentence becomes `the <thing> has no open or closed value, no declared contents, and is fixed in place. The story states: <delivery text>`, and Variant E adds "Anything the declared sentence says the story states, such as damage to the thing, is supported." This stays story-agnostic and supports only what the story itself says (an invented forced gate is still unsupported). In `cases-v4.jsonl` the 10 back-door cases carry the 1A delivery text in their declared sentence (re-locked); no label changes (the v2 label rule already counted "forced" as clean; the one forbidden back-door case is ajar and pushed open).

**Result (2026-10-31): Variant E PASSES clearly; $0.0296 judge + $0.0321 smoke (plus $0.0328 for a broken smoke).** Judge 900/900 rows, no stop reason (`bench/results/environment-narration/t9h-opening-v4/report.md`). Gate: forbidden rejected 52/54, clean accepted 85/86. All 19 relabelled drain cases accepted; opening set 19/19 and 21/21 (every back-door "forced" narration accepted with the story text in the declared sentence). The two false accepts are both labelled only `invents_ajar_or_cover_state` on weak readings: drain-row-032 "it looks like it hasn't been sealed off" (0.66) and drain-row-086 "leaves and twigs clogging the grate" (0.89); not relabelled after the fact. Held-out (out of scope): forbidden 9/10, clean 16/30 accepted.

**Smoke.** The first run (`combined-e`) is void for the back door: the bench wrapper `counted_verify` in `live_baseline.py` did not accept the new `story_text` keyword, so all five back-door turns failed with "The observation check could not complete" before any judge call (drain 5/5 first try, service gate 5/5 with one real "slightly ajar" retry in that run). Fixed by passing `story_text` through; rerun `combined-e2`, all three routes, no stop reason:

| Run | Drain committed (first try) | Service gate | Back door | Median turn | Over 10 s |
| --- | --- | --- | --- | --- | --- |
| combined, Variant B (section 15) | 4/5 (1/5) | 5/5 (5/5) | 5/5 (3/5) | 7.3 s | 3/15 |
| combined, Variant D | 5/5 (1/5) | 5/5 (5/5) | 5/5 (2/5) | 8.3 s | 4/15 |
| **combined, Variant E (`combined-e2`)** | **5/5 (4/5)** | **5/5 (5/5)** | **5/5 (4/5)** | **4.9 s** | **0/15** |

Both retries were fair: the drain attempt said it "seems to be slightly ajar" (0.10); one back-door attempt scored uncertain (0.40) on "noticing that it has been forced open", accepted on retry. Small samples; a smoke, not a gate.
