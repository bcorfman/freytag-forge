# Astra review implementation plan

Sources: `.plans/astra-weak-spots-review.md` (material fixes) and `.plans/astra-arch-review.md` (turn pipeline).
Status: **Phase 4 items 1 and 2 measured (2026-10-13, branch `astra-phase4-cheap-fixes`, not merged; items 3-4 not started); Phase 4 item 1 done offline (2026-10-13, branch `astra-phase4-cheap-fixes`, not merged); Phase 3 done offline (2026-10-13, branch `astra-phase3-eval-harness`, not merged); Phase 0 done (2026-10-12); Phase 1 offline checks done (2026-10-12, on 618 staged as 787f56d1); phone-alias probe run, inconclusive (2026-10-13); 1C pointer already measured (see its section; no new run); hosted 1A-1B phone smoke not started.** Update this file after each phase (see memory: update-plan-after-each-feature).

## Findings that shape the order

- The weak-spots review's two rank-1 material fixes **already landed** in `5d45afcf` ("Scope the photograph aliases and point 1C players at the shaft's identification numbers"). `world.yaml:213` has `scoped_aliases: [photograph, photo]`; `knowledge.yaml:849` and `:882` carry the new shaft pointer. They are unmeasured, not unapplied.
- The warehouse drift (1A) has **no identified source line**. The review says no change until the saved failing sequence is read.
- The arch review keeps `worldkeeper`, the fact store and authored progression. It proposes an outcome-first turn pipeline as a **prototype to be judged by a controlled three-arm evaluation**, not a committed migration. Its own text says the benefit is unproven and that the Step 8 live recall gain was withdrawn.
- Billed runs follow the repo rules: smoke test first, one Ringer task per run unit, guard every billed endpoint, measure each fix before the next, hosted E2E only. Code changes go through Ringer.

## Phase 0: Baseline and housekeeping (no billed calls)

1. Commit the three untracked review/prompt files under `.plans/`.
2. Read the saved 1A failing sequence (warehouse introduction, the pointer turn, the next player command). Per `docs/scene-fixing-guide.md`, name the source line or declare "no source".
3. Record what the 1C and phone fixes were measured against (find the baseline in `scene-affordance-e2e.md` / `design-review-implementation.md`). If none exists, that becomes Phase 1's baseline arm.

Exit: a one-paragraph warehouse diagnosis in this file; baselines located.

### Phase 0 result (2026-10-12, no billed calls)

1. **Untracked files:** none. The review and prompt files were already committed in `26373e56`; the tree is clean.
2. **Warehouse diagnosis: no source line.** The saved failing run is `~/dev/ringer-work/playthrough-ending-x3/out/e2e-blind-player-r1.md` (canonical profile). `grep -i warehouse` over `data/stories/continuity-initiative` finds nothing. The word first appears on turn 6, command "Read Michelle's text messages.": the narrator invented a phone text ("Meet me at the old warehouse at midnight. Come alone.") with only `k_scene_1a_entry` as grounding. The player then followed that invented lead ("Visit/Search the old warehouse", then boxes, equipment, a leather-bound book), and the narrator accepted each. The drawer cue was delivered later (it is appended to the turn-10 text) but the player was already inside the invented place. So this is narrator invention on a phone-read command, not a pointer or escalation defect. It is the same class as the earlier r1 phone text and r3 "old warehouse" email in `scene-affordance-e2e.md` (L2 on aa52889). Verdict: not a diagnosed authoring defect; **Phase 2 closed**; Phase 4 item 1 (unknown identity is not authorized creation) and the Phase 3 harmless-vs-plot-bypassing invention cases cover it.
3. **Baselines:** none was recorded for the two landed fixes (`5d45afcf` added only offline tests `test_1c_reading_pointer.py`, `test_photo_scoped_alias.py` and Ringer manifests `weak-1c.json`, `weak-photo.json`). Closest 1C history: the weak-spots prompt cites 2 of 6 canonical-or-raw runs earning the chain by play; the later L2 all-nine on `99029cc6` shows 1C P7 P7 P7 (3 of 3, canonical profile). These disagree, so **Phase 1 runs its own baseline arm** (pre-`5d45afcf` material vs current) rather than trusting either. Phone: one rejection ("unavailable entity 'photo'") is the only recorded evidence; baseline arm needed there too.

## Phase 1: Verify the landed material fixes

Offline (cheap, hermetic):
- Score the review's 11 failing commands plus the 6 control commands against the real matcher (`candidate_matcher.py`). Expect the control table in the review (unique `b_r1`/`b_r2`, one tie).
- Regenerate the disclosure matrix; expect only the `photo`/`photograph` classifications to differ from before `5d45afcf`.
- Run `tests/test_scoped_aliases.py`, `test_leak_terms.py`, `test_design_review_fixtures.py`, `test_narration_corpus.py`. Add early-1A fixed-sentence checks (`photo`, `photograph`, `picture`, `Michelle's photograph`), since the corpus only covers late scenes.
- Confirm 1B resolves both scoped aliases (inspect / show / follow-up). This is the review's main named risk.

Billed (smoke test first, ringer, one task per run unit):
- Phone aliases: fixed prompt "Examine Michelle's phone.", 12 samples per arm via the local narration bench. Count alias-only rejections apart from real disclosures. Then 3 linked hosted 1A-1B smoke runs.
- 1C pointer: 12 paired raw-profile starts, baseline vs treatment, hosted L2 harness (batches of 3 replicates, 4 batches per arm). Count B reveals before turn 8, play exits, forced exits, route detours, rejections.

Decision rule (from the review): drop or revise the pointer if early B reveals and forced exits do not improve or disclosure failures appear. Revise the alias if `photo`/`photograph` still reject, the full-name guard weakens, or 1B regresses.

Exit: results table in this file; fixes kept, revised or reverted.

### Phase 1 offline result (2026-10-12, no billed calls; 618 staged as `787f56d1`)

- **Suites:** `test_scoped_aliases`, `test_scoped_alias_recall`, `test_leak_terms`, `test_design_review_fixtures`, `test_narration_corpus`, `test_photo_scoped_alias`, `test_1c_reading_pointer`: 35 passed.
- **Matcher scoring (real `_matches_all`, 1C with `facility_proof` true):** all 11 failing commands match no reveal, as the review said. The 6 controls match as predicted: unique `b_r1` x3, unique `b_r2` x1, none for "Inspect the uniforms.", and the one known `b_r1`+`b_r2` tie for the mixed command. No new tie.
- **Disclosure matrix:** regenerated output equals the committed matrix. Across `5d45afcf` the only classification changes are `photo` and `photograph` going from `entity_name` to `scoped_alias` (two entries each).
- **Early 1A sentences (real validator):** "photo", "photograph", "picture" and "Examine Michelle's phone." are accepted. "Michelle's photograph is on the screen." is still rejected (`narration_known_term_leak`): the full-name guard is intact, as intended.
- **1B scoped aliases:** with the photograph placed, "Inspect the photo.", "Examine the photograph." and the Examine-beneath-the-bench command match `k_sl_1b_a_r2`; "Show the photo to the man.", "Show the man the photograph.", "Ask the man about the photo." and "Show Michelle's photograph to the man." match `k_sl_1b_b_r1`. No 1B regression.
- **Early-1A test:** added as `tests/test_early_1a_photo_sentences.py` (Ringer `astra-early-1a-photo`, pass on attempt 2; 5 cases).
- **Not done:** the billed runs (phone aliases, 1C pointer) need the pre-`5d45afcf` baseline arm described in Phase 0.

### Phase 1 phone-alias probe (2026-10-13, local narration bench; Ringer `astra-phone-alias`)

Fixed prompt "Examine Michelle's phone.", scene 1A, 12 replicates per arm. Baseline arm = current package with the `michelle_photograph` block reverted to global `aliases` (variation override); current arm = shipped scoped aliases. Smoke first (2 per arm, 44 neurons), then n=12. Result: **0 rejected turns and 0 recovery requests in both arms, and no narration in either arm (0 of 24) used photo, photograph or picture.** The probe never elicited the failure, so it cannot separate the arms. The decision rule (revise if `photo` still rejects) is not triggered, but the improvement is also unmeasured. Offline checks (above) remain the evidence for this fix. A rejection needs the narrator to write the word; the one recorded case came from a longer 1A run. Next, if wanted: a probe whose prompt makes a photo likely (for example a longer 1A script), still player-guide-conformant, or fold phone-alias into the linked hosted 1A-1B smoke runs. Files: `bench/variations/astra-phone-{baseline,current}.json`, `scripts/ringer/astra/phone-alias-*`.

### Phase 1 1C pointer: already measured, no new billed run (2026-10-13)

**Correction to Phase 0 item 3.** Phase 0 said no baseline was recorded for the 1C fix. That was wrong: `.plans/playthrough-quality.md` records exactly the planned comparison (hosted L2, 12 paired raw starts of 1A-1C, 4 batches of 3, same starts both arms).
- Baseline, staging `ef75c854` (Ringer `weak1c-baseline-x12`): 1C 10 of 12 by play (2 forced); `b_r*` reveal on turn 3 (7 runs) or 4 (3 runs); 1A 12/12, 1B 12/12; 0 rejected turns.
- Treatment, staging `49d7126b` (#613/#614, which carry `5d45afcf`), two runs of the same 12 starts: 1C 11 of 12 in both; `b_r*` on turn 2-4; 1A 11 and 12 of 12; rejected turns 5 and 1, which the sibling run shows is mostly variance. Later narration-safety fix on `2e90fd97`: 1C 11 and 12 of 12, 0 and 1 rejected.
- Reading against the decision rule (drop or revise if early B reveals and forced exits do not improve, or disclosure failures appear): forced exits 2 -> 1 and 1 (not worse), B reveal about one turn earlier, and the rejections traced to five narration-safety terms (fixed), not to the pointer. The baseline arm had little headroom (at most 2 of 12 could move), so this is "no harm, small and unproven gain", the same limit that file states. **Keep the pointer.** A rerun now would spend the same budget to answer the same question at the same power; not run.
- The 1C figures quoted earlier (2 of 6 earned by play; 3 of 3 on `99029cc6`) are other draws; this paired set is the one to cite.
- Remaining Phase 1 item: 3 linked hosted 1A-1B smoke runs for the phone alias, which only matter if a probe can elicit the photo word (see the phone-alias probe above).

## Phase 2: Warehouse drift (conditional)

Only if Phase 0 found a reproducible source line or prompt conflict. Then probe it with 10-15 samples per arm, fix the material at the source (rules last, never regex), and measure before the next fix. If Phase 0 found no source, close this item as "not a diagnosed authoring defect" and let Phase 3's invention work cover it.

## Phase 3: Evaluation harness for the pipeline question

No pipeline code yet. Build what the decision needs.
1. Test set from the arch review: short references after cues, same phrase with two referents, pocketing vs withdrawing, entering vs driving, ordered compound actions, corrections, harmless vs plot-bypassing new objects, unresolved existing-NPC reference (no duplicate), refused move whose prose must show refusal, concealment then NPC encounter, save/load between cue and follow-up, reveal before/after prerequisites, player-caused dependency damage.
2. Metrics scored **separately**: correct reference, action, state, prose; false reveal; unauthorized creation; forced progress; clarification burden; latency; requests and tokens per accepted turn. No single "capture accuracy" number.
3. Fixtures on the drawer-to-truck sequence. No second story package (see Decisions).
6. Clarification test: an ambiguous command must leave the turn counter, pressure events and patrol clock unchanged.
4. Held-out commands and varied start states kept apart from the diagnostic set (10-15 samples per fixed prompt for diagnosis).
5. Player input written to `docs/player-input-guide.md` (imperative, first-person possessives).

Exit: harness runs hermetically with stubs for unit tests; a smoke run passes.

### Phase 3 result (2026-10-13, no billed calls; Ringer runs `astra-pipeline-eval` core + cases)

- **Built:** `bench/pipeline_eval/` (`model.py` cases and loader with diagnostic/held_out split; `metrics.py` eight metrics scored separately plus latency, requests, tokens, no combined key; `runner.py` `ScriptedArm`, `PipelineArm` (stub-narrator driven `RuntimeEngine`, save/load between commands), per-turn report showing successes too; `__main__.py` offline `smoke` and `report --cases`). Fixture `bench/pipeline_eval/cases.json`: 14 categories (the 13 from the arch review plus `clarification_invariance`), one diagnostic and one held-out case each, on the drawer-to-truck sequence only. Held-out commands share no string with diagnostic ones.
- **Clarification test:** `clarification_unchanged(before, after)` compares `turn_index`, fired and active events and `turn_records`. There is no separate patrol-clock field in `RuntimeSnapshot`; it is covered through events and turn index. Decision 2 (clarifications cost no turn) is what it checks.
- **Tests:** `tests/test_pipeline_eval.py` and `tests/test_pipeline_eval_cases.py`, 9 passed; smoke exits 0; ruff clean.
- **Widened (2026-10-13, Ringer `astra-pipeline-eval` widen):** 84 cases, at least 3 diagnostic and 3 held-out per category, start states varied by setup facts, scene (1A or 1B) and save/load index. Refusal checks no longer match words: a case lists `prose_must_not_assert` claims plus an unmoved-state expectation, and an injectable `claim_judge(prose, claim)` decides; with no judge the prose metric is reported unchecked. Case state keys are validated against `STATE_VOCABULARY` in `model.py` (memory_card, kristin, kristin_truck, kristin_laptop). 11 tests pass.
- **Known weak spots:** the vocabulary is small and its mapping to engine facts is unwritten (Phase 5). Every refusal case expects `kristin_truck: at_workstation`, so refusal varies the command, not the expected state. Three cases per split is breadth, not statistical power: Phase 5 still needs 10-15 samples per fixed prompt. No live claim judge exists yet (Phase 5). `PipelineArm` leaves reference/action/state/created empty because the current pipeline does not report them. Live (billed) arms are not built.
- **Process note:** the core worker also wrote an unverified copy into the main checkout against its spec. It was deleted and the verified patch applied; the cases check now fails on that.

## Phase 4: Cheap architectural fixes that are valid under either design

Each is small, tested alone and measured before the next. These do not need the full pipeline and reduce risk whichever arm wins.
1. **Unknown identity is not authorized creation.** In the item-fact application path, an unresolved name that matches an existing person or thing must not create a new entity (the recorded duplicate-man failure). Add a test layer fix too.
2. **Refused moves must reach the prose.** When capture refuses a move the narration claimed, the player-visible reply must not still assert it. Choose between repair, re-narration or engine-composed clause; measure.
3. **Recent accepted references.** Add a small structured record of the last delivered cue's referents (entity links and source spans, from committed turns and authored cues only) to the reference-matching payload. This answers "search the gap". No permanent `gap` alias. Bound it by relevance.
4. **Keep possession, knowledge and concealment distinct.** Do not reuse the discovery-hidden state for concealment of an already-found item.

Exit: each item has a bench result; regressions checked against Phase 3's set.

### Phase 4 item 1 result (2026-10-13, no billed calls; Ringer `astra-p4-1-unknown-identity`, pass on attempt 1)

- **Cause of the duplicate man:** Brandon stays unnamed until `brandon_identified`, and the engine knows him as `unnamed_label` "the man watching Kristin". A narrated "man" did not resolve to that label, the match call said "new", and `apply_item_facts` created a second man.
- **Fix:** `ItemFactsProvider._existing_unnamed_person` (`storygame/runtime/item_facts.py`). Before creating, a key whose words are a leading word-prefix of exactly one still-unnamed, in-scene, same-area character's unnamed label maps to that character, with an issue note and no creation. Deterministic, no LLM call. Ambiguous matches, longer descriptions ("man in the hoodie"), unrelated names, named Brandon and the protagonist all keep the old behaviour.
- **Tests:** `tests/test_unknown_identity_not_creation.py` (5 cases, real package, scene 1B; the knock-out is asserted on the `conscious` axis); neighbouring item-fact suites 285 passed.
- **Limit:** this covers characters that declare `unnamed_label`; any other unresolved-but-existing person is not covered. Live measurement against the old r1 failure is not run (needs a hosted run); Phase 3's unresolved-NPC case is the offline check. Items 2-4 not started.

### Phase 4 item 2 result (2026-10-13; four arms measured live on the local bench; Ringer `astra-p4-2-*`)

- **Setup:** `RuntimeEngine(refusal_mode=...)` with `off` (default, unchanged behaviour), `clause`, `repair`, `renarrate`; the bench passes `variation["refusal_mode"]`. Set: four fixed-thing commands in 1A ("Carry the workstation to the truck.", "Pick up the back door.", "Put the workstation inside the truck.", "Take the workstation outside."), 10 replicates each, judge off, scored by deterministic counts plus a hand read of every refused reply. The Phase 3 truck "refused move" cases never produce a live refusal (the truck is movable), so they are not the measurement set.
- **Fact-tracking judge dropped:** in the smoke it flagged one of four asserted moves in the `off` arm.
- **Reading rubric (strict):** clean = the reply does not claim the move and shows the attempt failing; off-topic = ignores the command; contradictory = a phrase that undercuts itself; asserts = still claims the move.

| Arm | Refused / 40 | Extra calls | Clean | Asserts the move | Authored cue kept on refused turns |
|---|---|---|---|---|---|
| off | 32 | 0 | 0 of 32 | 32 of 32 | 32 of 32 |
| clause | 29 | 0 | 0 of 29 | 29 of 29 (a "X has not moved." clause follows prose that claims it) | 29 of 29 |
| repair | 29 | 29 | about 4 of 29 | most; several self-contradict | 10 of 29 |
| renarrate (first build) | 36 | 36 | about 31 of 36 | 0 | 1 of 36 |
| renarrate + cue-restore | 33 | 33 | 23 of 33 | 1 of 33 | 33 of 33 |

- **Cue loss found and fixed:** the drawer cue is authored delivery text that `CloudflareTurnProvider._compose_staged_cue` appends inside the narrator's own proposal, so the first splice replaced it while the engine still counted it delivered. The engine now keeps any segment whose text is an authored `cue_text`, `escalation_text` or `fallback_text` (`RuntimeEngine._authored_delivery_texts`).
- **Cue-restore round (n=10):** 33 of 33 refused turns keep the cue. Of the 33: 23 clean, 6 off-topic (the narrator ignores the command, for example "gets out of her truck and walks toward the house"), 3 contradictory ("remains in the kitchen, still carried"), 1 asserts the move ("moves the workstation into the passenger seat"). The first build's 31 of 36 clean and this 23 of 33 are within the noise of n=10; `s3` ("put the workstation inside the truck") produced 3 of the 6 off-topic replies.
- **Reading:** `renarrate` with cue-restore is the only arm that removes the false claim, at one extra narrator call per refused turn (refusals only happen on commands aimed at fixed things). `clause` is cheap but leaves a contradiction on the page. `repair` fails its job; drop it.
- **Limits:** one scene, four commands, one narrator model. No hold-out commands. The `refusal kept authored text` issue string was never recorded in the bench turn records (the cue check above is the real evidence); the bench does not expose that field. Pending-resume path: a re-narration there uses the pending proposal as its own source and can replace authored segments. The first `clause` pass lost a replicate and `s4` to an SSL timeout; `s3` and `s4` were rerun in full (about 9 duplicate turns billed).
- **Default stays `off`.** Adopting `renarrate` as the web default is a cost and behaviour decision for Brandon.

### Phase 4 item 2, prevention arm: the fixed-thing marker (2026-10-13; Ringer `astra-p4-2-fixed-marker*`, `astra-p4-2-runtime-mark`, `astra-p4-2-measure-fixed`)

- **Built:** `ItemFactsProvider(mark_fixed=...)`, default off; bench option `item_facts.mark_fixed`. When on, every rendered fixed non-area thing in the narrator's THINGS block gets " It is fixed in place. It cannot be picked up or carried away. If the player tries, the attempt fails." (no "move", so opening a door is not read as moving it). `build_capture_provider(state, mark_fixed=False)` carries it on the runtime path. Production is unchanged.
- **Three invalid smokes before the real one**, each a harness-path defect, not a model result: (1) my spec gated the marker on `_referred_names`, which only the live match call fills, so it never rendered; (2) the runtime bench builds its provider with `build_capture_provider`, which dropped the option; (3) a Ringer check I wrote was too rigid. Lesson: confirm the sentence is in the recorded `prompt_user` before reading outcomes (fields `prompt_user`, 39 of 40 turns carried it; the one without was a "Pick up the back door." turn where the match call left the back door out of THINGS).
- **Result (n=10 per command, 1A, `refusal_mode=off`, count = capture refused the move the narrator claimed):**

| Command | Baseline (off) | With marker |
|---|---|---|
| Carry the workstation to the truck. | 8 / 10 | 10 / 10 |
| Pick up the back door. | 6 / 10 | 1 / 10 |
| Put the workstation inside the truck. | 8 / 10 | 8 / 10 |
| Take the workstation outside. | 10 / 10 | 0 / 10 |
| All | 32 / 40 | 19 / 40 |

- **Reading:** the marker fully fixes "take outside" and nearly "pick up" (honest replies such as "tries to lift the workstation, but it doesn't budge. It's fixed in place."). It does nothing for destination-phrased commands ("carry ... to the truck", "put ... inside the truck"): those still claim the move 18 of 20 times. Replies are near-identical across replicates, so n=10 is closer to 4 distinct samples per command than 40.
- **Controls (ordinary play, n=5 each, with and without the marker):** no over-refusal. The back door opened 5 of 5, the drawer opened 5 of 5, examining the workstation was normal, and capture refused 0 of 15 in both arms. Two side effects with the marker: the door was "stuck" before opening in 3 of 5 replies (0 of 5 without), and one examine reply said "The workstation is a fixed, stationary object".
- **Cost:** zero extra calls; one sentence per rendered fixed thing.
- **Limits:** four commands, one scene, one narrator; the destination-phrased failures suggest the wording matches verbs ("pick up", "carry away") more than intent. No wording variant was tried, and I did not tune the sentence to these four commands (that would overfit without held-out commands). The marker plus `renarrate` combination is not measured.
- **Reading across item 2:** the marker alone is not enough (19 of 40 still claim the move); `renarrate` with cue-restore handles the rest at one call each. The combination would cut `renarrate` calls by about 40 percent on these commands. Neither is the default; both are Brandon's call.

### Phase 4 item 2, marker wording variants on held-out commands: pre-registration (2026-10-13, written before any code or run)

Question: does a differently worded fixed-thing marker also stop the narrator claiming moves for destination-phrased commands, without making ordinary play refuse?

- **Variants** (`item_facts.mark_fixed`; `true` stays the first):
  - `carry_away` (current): " It is fixed in place. It cannot be picked up or carried away. If the player tries, the attempt fails."
  - `anywhere`: " It is fixed in place. It cannot be picked up, carried, pushed, or put anywhere else. If the player tries, the attempt fails."
  - `stays`: " It is fixed in place. It always stays exactly where it is. If the player tries to take it anywhere, the attempt fails."
- **Dev set (already seen, not used to choose):** Carry the workstation to the truck. / Pick up the back door. / Put the workstation inside the truck. / Take the workstation outside.
- **Held-out set H1 (chooses the variant; none of these has been run):** Lift the workstation. / Take the drawer out of the workstation. / Drag the workstation to my truck. / Set the back door on the kitchen floor. / Push the workstation against the wall. / Carry the drawer to my truck. / Bring the back door to the truck. / Remove the passenger seat from the truck.
- **Held-out set H2 (locked; run only after the choice, never used to choose):** Pick up the drawer. / Take the back door off its hinges. / Slide the workstation across the kitchen. / Put the drawer in my truck. / Haul the workstation outside. / Set the driver's seat on the kitchen floor. / Roll the workstation to the back door. / Carry the back door outside.
- **Over-refusal controls (the action should succeed):** Open the back door. / Examine the workstation. / Open the drawer. / Close the drawer. / Look at the passenger seat. / Sit in the driver's seat. / Pick up my laptop. / Carry my laptop to the workstation. (the last two are movable things next to fixed ones.)
- **Arms on H1:** baseline (no marker), `carry_away`, `anywhere`, `stays`; n=4 per command (replies barely vary across replicates, so more commands beat more replicates). Dev set: `anywhere` and `stays` at n=4 for context. Controls: all four arms at n=3.
- **Metric:** claim rate = turns where capture refused the move the narrator wrote, over turns. I read every refused-in-prose and every control reply; a control reply that says the thing is fixed, does not budge, or cannot be done counts as an over-refusal.
- **Rule, fixed now:** the winner is the variant with the lowest H1 claim rate that has zero control over-refusals. If two variants are within 5 percentage points, keep `carry_away` (shortest, already built). Then run H2 for the winner, `carry_away` and baseline at n=4. Report H1 and H2 separately; do not pool them. No wording is changed after seeing H1 results; a new wording would need a new held-out set.
- **Validity gate, learned the hard way:** before reading any outcome, check that the variant's exact sentence is in the recorded `prompt_user` of every turn that renders a fixed thing, and absent from the baseline arm.

### Phase 4 item 2, marker wording variants: result (2026-10-13; Ringer `astra-p4-2-marker-variants`, `astra-p4-2-measure-wv`; pre-registration above)

- **Validity:** every marker-arm turn carried its own sentence and no other (0 turns without it; baseline none); the movable laptop was unmarked. No failed replicates. H1 = 8 held-out commands x 4 arms x n=4 (32 turns per arm); controls = 8 commands x 4 arms x n=3 (24 turns per arm); dev set for `anywhere` and `stays` at n=4 (not analysed beyond the pattern below).
- **Scoring:** claims were counted by reading the replies, not from the capture flag (capture misses claims where no place changes, for example "Kristin lifts the workstation"). A substring screen sorted replies into refusal / not-refusal piles and I read every not-refusal reply.

| H1 (32 turns) | Baseline | carry_away | anywhere | stays |
|---|---|---|---|---|
| Reply claims the move | 32 | 14 (44%) | 15 (47%) | 19 (59%) |

- **By command shape the three wordings behave alike.** All three fix: Lift the workstation. / Take the drawer out of the workstation. / Bring the back door to the truck. (4 of 4 honest refusals each). All three fail: Drag the workstation to my truck. / Push the workstation against the wall. / Carry the drawer to my truck. (4 of 4 claims each). Mixed: Set the back door on the kitchen floor. (`carry_away` and `anywhere` refuse, `stays` claims 4 of 4) and Remove the passenger seat from the truck. (all partial). The dev-set pattern is the same: pick-up and take-out forms pass, carry-to and put-inside forms fail. A named destination or displacement beats the marker whatever the wording.
- **Over-refusal controls (the action should succeed; a reply that says the thing is fixed or does not budge counts):**

| Control (n=3 each) | carry_away | anywhere | stays |
|---|---|---|---|
| Open the drawer. | 1 over-refusal | 1 | 0 |
| Sit in the driver's seat. | 1 | 3 | 1 |
| Open the back door. (reply says "stuck" first, then opens) | 1 | 3 | 0 |
| Other 5 controls (examine, close drawer, look at seat, pick up / carry my laptop) | 0 | 0 | 0 |

  Over-refusals total: `carry_away` 2 of 24, `anywhere` 4 of 24, `stays` 1 of 24; baseline 0. The collateral is on fixed things the player is meant to use: the seats and the drawer are `fixed`, so the marker tells the narrator they cannot be handled. Baseline "Sit in the driver's seat." already has the narrator claiming a seat move in 3 of 3, so that command is also a pre-existing defect.
- **Decision under the pre-registered rule:** no variant has zero control over-refusals, so none qualifies as the winner. By claim rate alone `carry_away` (44%) and `anywhere` (47%) are within the 5-point tie band and `stays` is worse. **H2 was not run** (the rule runs it only for a winner). The marker is not adopted; `mark_fixed` stays an opt-in bench option.
- **What the evidence supports:** wording is not the lever. Two distinct limits remain: (1) commands with a destination override the marker; (2) the marker also fires on fixed things that are used rather than carried (seats, the openable drawer), causing refusals of normal play. A different design would be to mark only fixed things the player cannot use in place (exclude seats and openable containers), which is a new hypothesis needing its own held-out check (H2 is still unused and could serve, declared in advance). `renarrate` with cue-restore remains the only measured arm that handles the destination-phrased failures.
- **Limits:** one scene, one narrator, near-deterministic replies, so n=4 per command is closer to one or two distinct samples; counts above are directional.

### Phase 4 item 2, "refuse fixed move" prerequisite step: pre-registration (2026-10-13, written before any code or run; design reviewed by ChatGPT, `.plans/astra-refusal-alternatives-answer.md`)

- **Candidate:** a new prerequisite step in `WorldCapture.before_turn`, opt-in (`fixed_refusal`, default off; bench variation key `fixed_refusal`). For each fixed, visible, non-area thing in the player's area that the command names (the `take_before_put` pattern), ask the small yes/no model one new question, `relocates_thing`: does this command lift, carry, drag, push, slide, remove, or otherwise relocate that thing? Using it in place (open, close, sit in, look at, search, or putting another thing on, in, off or out of it) is not relocating it. Yes: nothing changes in the world and the narrator gets the one-turn line "Just before this: <Protagonist> tried to move <the thing>. It is fixed in place and did not move." The step runs before the standing, boarding, taking and seating steps and, when it fires, they are skipped (a refused carry must not board the truck). No answer: record an issue and add no step. No narrator call is added.
- **Arms (identical settings, interleaved):** baseline (`fixed_refusal` off, `refusal_mode` off); candidate (`fixed_refusal` on, `refusal_mode` off); `renarrate` (`refusal_mode` renarrate with cue-restore, `fixed_refusal` off).
- **Commands (16, none run before; from ChatGPT's list, one substitution: "Seat myself in the driver's seat." became "Get into the driver's seat." to keep the player-input guide's imperative voice).** Expected refusal: Raise the workstation off the floor. / Detach the driver's seat from the truck. / Extract the drawer from the workstation. / Transport the workstation into the truck. / Bring the drawer to the passenger seat. / Shove the workstation toward the back door. / Lift the drawer and the back door together. / Lift the workstation, then lower it back into place. Expected success (controls): Place my laptop on the workstation. / Set my laptop on the passenger seat. / Retrieve my laptop from the passenger seat. / Pull the drawer open. / Push the drawer shut. / Push the back door open. / Get into the driver's seat. / Move the workstation chair beside the workstation.
- **Samples:** 2 per command per arm (96 turns). Replies barely vary, so these are 16 distinct cases, not 96.
- **Bars, fixed now (screening, not a reliability rate):** at least 15 of 16 coherent honest refusals on the 8 refusal commands x 2 with zero replies that claim the prohibited relocation; destination and push commands (Transport, Bring, Shove) 6 of 6; controls 16 of 16 intended successes with no invented fixedness obstacle or seat displacement; authored cue text preserved exactly and delivery bookkeeping agreeing with the reply; no unintended prerequisite movement or progression; no narrator call added by the candidate (record classifier calls, failures and latency).
- **Reading:** every reply from a shuffled sheet with arm labels removed (mapping kept in a separate file until all are scored). A coherent refusal addresses the attempt, shows failure, and contains no contradiction or successful displacement anywhere. Prose is judged separately from facts; unchanged facts do not prove an honest reply. Report end-to-end over every scheduled case, not only turns where capture recorded a refusal. Separate target-resolution misses, classifier errors and narrator disobedience.
- **Validity gate:** before reading outcomes, the recorded `prompt_user` must contain the refusal line on candidate turns where the classifier said yes, and never on the other arms.
- **Drop rule:** drop this version if correctly classified destination or push commands still produce successful-move prose, or if controls miss the bar. If classification works but the narrator still overrides it, the next experiment is an engine-owned refusal for a wholly disallowed action (no narrator call), not more wording. Before any adoption: a fresh command set plus multi-turn checks (mixed actions, cue delivery, progression, save/load).

### Phase 4 item 2, "refuse fixed move" step: result (2026-10-13; Ringer `astra-p4-2-fixed-refusal`, `-fixed-scope`, `-fixed-article`, `astra-p4-2-measure-fr`; pre-registration above)

- **Built (opt-in, off by default, production untouched):** `storygame/runtime/fixed_refusal.py` (`refuse_fixed_move`), `relocates_thing` in `jev_questions.py`, `WorldCapture(fixed_refusal=...)`, bench key `fixed_refusal`. Two defects caught before any live run: (1) the step tested exact same-area and never fired in real play (Kristin is in "Michelle's house", the fixed things are in "kitchen" or "outside the house"); it now uses the engine's scene scope (`_name_in_scene_scope`). The first unit tests had placed the player by hand; the fix's tests start from the real scene-1A state. (2) the sentence read "tried to move driver's seat"; now "the driver's seat".
- **Validity gate passed:** the refusal line was in the recorded prompt on exactly the 16 candidate turns where the step fired (32 of 32 turns consistent), never in the other arms; no boarding, seating or taking step ran alongside a fired refusal; no failed replicates; the candidate added 0 narrator calls and asked the classifier on all 32 turns (every command names a fixed thing); no unanswered classifier questions.
- **Scoring:** 96 replies, shuffled with arm labels removed, scored by me before unblinding (C coherent refusal, X claims the relocation, O off-topic, S control success, W control oddity).

| Arm (2 samples x 16 commands) | Refusal commands (8 x 2): C / X / O | Controls (8 x 2): success | Narrator calls added |
|---|---|---|---|
| Baseline | 0 / 16 / 0 | 16 of 16 | 0 |
| Candidate (`fixed_refusal`) | 7 / 9 / 0 | 16 of 16 | 0 |
| `renarrate` with cue-restore | 8 / 6 / 2 | 14 of 16 (2 W) | 13 on 32 turns |

- **Bars (set before the run):** candidate 7 of 16 coherent refusals against a bar of 15; destination and push (Transport, Bring, Shove) 0 of 6 against a bar of 6; controls 16 of 16 (met); authored cue kept on 30 of 32 turns, as in baseline's 29 of 32 (the cue is not always due); no narrator call (met). **The candidate fails its bars.**
- **Where it works:** Raise the workstation (2 of 2), Detach the driver's seat (2 of 2), Extract the drawer (2 of 2): honest refusals, for example "tries to lift the workstation, but it doesn't budge." It causes no control over-refusal, unlike the always-on marker.
- **Where it fails, and why:** Transport (0 of 2), Bring (0 of 2), Shove (0 of 2), Lift both (1 of 2). On these the classifier was right (the step fired on 14 of the 16 refusal turns) and the narrator disobeyed: "Kristin tries to move the workstation, but it's fixed in place. She decides to transport the workstation into her truck instead. She carefully lifts the workstation and carries it out to her truck." The narrator accepts the refusal line and then does the command anyway. This is the failure ChatGPT predicted, and it matches the marker experiment.
- **Classifier errors (separate from narrator disobedience):** missed "Lift the workstation, then lower it back into place." 0 of 2 fired (a compound, lift-and-lower command); false positive on "Retrieve my laptop from the passenger seat." 2 of 2 fired (the seat is the source, not the thing relocated), though the narrator still retrieved the laptop. So 2 misses and 2 false positives in 32 asks.
- **`renarrate`:** handles the destination commands the candidate cannot (Transport 2 of 2, Bring 2 of 2, Shove 1 of 2, Extract 2 of 2) but only fires when capture notices the claim, so it missed Raise (1 of 2) and Lift-then-lower; it answered Detach driver's seat off-topic (2 of 2); and it failed the "Get into the driver's seat." control 2 of 2 ("tries to get into the driver's seat, but she's already sitting in it"), because capture already flags a seat move on that command in baseline. Capture flagged 13 of 32 baseline turns although I read 16 of 16 refusal-command replies as claiming the relocation, so capture undercounts.
- **Complement, not tested:** the candidate covers lift, detach and extract; `renarrate` covers carry, bring and shove. A combined arm is a plausible next experiment but was not pre-registered, so it needs its own declared bars and fresh commands.
- **Drop rule:** triggered ("drop this version if correctly classified destination or push commands still produce successful-move prose"). Per the pre-registration the next experiment is an engine-owned refusal for a wholly disallowed action (no narrator call), not more wording or more steering lines. Neither the candidate nor `renarrate` is adopted; both stay opt-in.
- **Limits:** one scene, one narrator, near-deterministic replies, so 16 distinct commands, not 96; my own blind scoring (one reader); the candidate bars were screening bars, not reliability rates.

### Phase 4 item 2, engine-owned refusal: result (2026-10-13; Ringer `astra-p4-2-engine-refusal`, `-bench-engine-refusal`, `astra-p4-2-measure-fe2`; frozen in `.plans/astra-engine-refusal-freeze.md`, code in 099e4e4a and 6c43c2a1)

- **Built (opt-in, off by default):** `WorldCapture(fixed_refusal=True, engine_refusal=True)`; when `relocates_thing` says yes the engine returns fixed text ("Kristin tries to move the workstation, but it is fixed in place and does not budge.") with no narrator call, restores the pre-turn snapshot and consumes no turn. An unanswered classifier narrates normally and records an issue. Bench key `engine_refusal`; refused turns record `narrator_called` false and no stale prompt or item facts. The `relocates_thing` criteria were tightened for lift-then-lower and source/surface cases. The attempt record has no "refused" outcome, so refused turns are logged as `rejected`.
- **Validity gates passed:** baseline arm had no refusal line and no classifier call; every engine-arm refusal had no narrator call, no prompt and unchanged facts; no non-refused turn carried a refusal line; classifier asked on 16 of 16, none unanswered.
- **Scoring (32 replies, shuffled, arm labels removed, one reader; the fixed sentence makes the engine arm recognisable, so blinding is partial):**

| Arm (1 reply x 16 fresh commands) | Refusal commands (9): honest refusal / claims the move | Controls (5): success | Mixed (2) | Narrator calls on refused turns |
|---|---|---|---|---|
| Baseline | 0 / 9 | 5 of 5 | 2 of 2 narrated the fixed move | n/a |
| Engine-owned refusal | 9 / 0 | 5 of 5 | 2 of 2 refused the whole command | 0 of 11 |

- **Bars (set before the run):** 9 of 9 refusals met; 5 of 5 controls met; zero prohibited-success claims, false refusals or mutations on the engine arm met; zero narrator calls on refused turns met. Destination and push commands (Carry the driver's seat into the kitchen, Move the workstation beside the truck, Slide the workstation across the kitchen, Push the passenger seat out of the truck, Carry the drawer and the passenger seat into the kitchen) all refused, which the prompt-line step could not do (0 of 6). The 2 mixed-action clarifications in ChatGPT's bar are not testable: clarification is not built.
- **Known cost:** a mixed command loses its harmless part. "Hoist the workstation, then open my laptop." and "Carry the drawer and my laptop into the truck." were refused whole, so the laptop action did not happen.
- **Limits:** one scene, 16 distinct commands, one reply each, my own single-reader scoring, no classifier false positive seen in 5 controls (the earlier "Retrieve my laptop from the passenger seat" case was not re-run). This is a screen, not a reliability rate. Not yet checked: save/load across a refused turn, cue delivery on the next accepted turn in a live run, a second story package, multi-turn sequences.
- **Decision:** the narrator was the blocker, and the engine path holds. Next is a second, separate experiment: mixed commands (refuse only the fixed part or ask which to do), cue deferral and save/load, plus a fresh command set. The path stays opt-in; `renarrate` stays off by default.

### Phase 4 item 2, honest mixed-command refusal: result (2026-10-13; Ringer `astra-p4-2-mixed-refusal`, `astra-p4-2-measure-fe3`; frozen in `.plans/astra-engine-refusal-mixed-freeze.md`, code fe0d9cee)

- **Built (opt-in):** a refused command that also asks for something else ends with "Nothing else in that command was done. Say what you want to do next." A new yes/no question `names_other_action` (asked once, only on a refused turn; yes or unanswered appends the sentence) decides it. No splitter change (judged too brittle). Unit tests cover the sentence, its absence on a simple refusal, the unanswered case, one question per turn, and save/load after a refused turn.
- **Validity:** all 12 live turns ran; refused turns had no narrator call and no prompt; no unanswered question; no refusal line on non-refused turns.

| Group (1 reply each, engine arm) | Bar | Result |
|---|---|---|
| Mixed (4) refused with the clarification | 4 of 4 | **3 of 4**: "Carry the driver's seat and my laptop into the kitchen." was refused without the sentence (`names_other_action` said no) |
| Simple refusals (4) refused without it | 4 of 4 | **3 of 4**: "Tilt the workstation onto its side." was not refused and the narrator tilted it (`relocates_thing` said no) |
| Controls (4) succeed, no refusal | 4 of 4 | 4 of 4, including "Retrieve my laptop from the passenger seat." (the earlier false positive did not recur) |
| Narrator calls on refused turns | 0 | 0 of 9 |

- **Reading:** the engine path held; both misses are classifier misses. `names_other_action` missed the shared-verb shape (one verb, two objects), the same shape that defeated the splitter. `relocates_thing` missed "Tilt ... onto its side", a repositioning verb not in its list. Bars were missed (3 of 4 twice), so this version is not adopted.
- **Per the frozen stop rule:** tune that question once on the same bars with fresh commands, not these twelve. Still needed before any default: another story package and multi-turn play.

### Phase 4 item 2, refusal tuning round: result (2026-10-13; Ringer `astra-p4-2-refusal-tuning`, `astra-p4-2-measure-fe4`; frozen in `.plans/astra-engine-refusal-tuning-freeze.md`, code c6b5f3dd)

- **Tuning (wording only, one pass):** `relocates_thing` lists the repositioning verbs (tilt, tip, rotate, turn around, roll, nudge, shift, reposition) and says a part used as designed (door swung, drawer slid, lid opened, screen tilted back) is not relocation. `names_other_action` says a second object joined by "and" counts even when one verb covers both. The check failed the task if any fresh command appeared in source or tests.
- **Result on 12 fresh commands (engine arm, 1 reply each; I read the replies and the records):** mixed 4 of 4 refused with the clarification; simple refusals 4 of 4 refused without it; controls 4 of 4 succeeded with no refusal, including three that use fixed things in place (swing the back door open, press on the drawer, slide the drawer open then closed); 0 narrator calls and no prompt on the 8 refused turns; no unanswered question. All frozen bars met.
- **Flaw seen:** "Lift the passenger seat and the back door, then open my laptop." named only the passenger seat in the refusal ("Kristin tries to move the passenger seat, ..."). The clarification sentence still said nothing else was done, so the reply is honest, but it does not mention the back door.
- **Limits:** a screen. 12 distinct commands, one reply each, one scene, one reader, and the classifier is still a small model with wording tuned to the failures found. It passed on commands it was not tuned on, but two rounds of tuning on one scene is not evidence of reliability.
- **Decision:** the engine-owned refusal with the honest clarification meets its bars and stays opt-in. Before any default: a second story package, multi-turn play (cue delivery live, refusal followed by normal turns), and a larger fresh command set. `renarrate` stays off by default.

### Phase 4 item 2, engine-owned refusal enabled in the hosted path (2026-10-13; Ringer `astra-p4-2-enable-refusal`)

- **Decision (Brandon):** turn the refusal on for the hosted path. The earlier "second story package" gate is dropped: there is one package and it must work in staging, and the mechanism reads only the story's own fixed flags. Multi-turn behaviour is covered by tests instead.
- **Change:** `engine_for` in `storygame/web_demo.py` builds `WorldCapture(..., fixed_refusal=enabled, engine_refusal=enabled)` whenever `FREYTAG_WORLD_CAPTURE=1`. `enabled` is True unless `FREYTAG_FIXED_REFUSAL` is exactly `0` (kill switch for staging rollback; set it on the service, no deploy needed). `renarrate` stays off.
- **Defect fixed on the way:** `EngineRefusalTurn` lacked `selected_knowledge_ids` and `events`, so a refused turn would have crashed `FREYTAG_EXPOSE_KNOWLEDGE_AUDIT=1` (the hosted debug/E2E mode). Both are now empty tuples; no other turn-result attribute is read on the hosted path.
- **Tests (hermetic, through the real API with sessions saved and reloaded between requests):** on by default; kill switch; refused turn with audit and prompt exposure; five-request sequence (normal, refused, normal, refused, normal) with the narrator called 3 times, turn index advancing only on normal turns, facts unchanged across refusals and a staged cue delivered once; mixed refusal then normal turn. Full local suite passed (1696 tests), ruff clean.
- **Billed calls:** each refused-or-checked turn adds classifier (Jev) calls only when the command names a fixed thing in scope: one `relocates_thing` per such thing, plus one `names_other_action` on a refusal. No narrator call on a refusal.
- **Untested until staging:** the real classifier on live traffic. Staged E2E needs the change on `main` and the SHA-bound staging deploy first (do not merge mid-run). Roll back with `FREYTAG_FIXED_REFUSAL=0` if staging shows false refusals.

### Phase 4 item 2, staging result for the engine-owned refusal (2026-10-13; PR 621, merge 1059073f)

- **Deploy:** main CI green including the scene staging evaluation and promotion gate; `GET /api/v1/version` on staging reported 1059073f, `scene-v1`, `staging`.
- **E2E (hosted, billed):** `@smoke`, `@safety` and `@npc` passed. `@spine` failed twice at journey turn 7 (the first authored 1B prompt, "At the bench her files pointed to, search underneath..."), both times with HTTP 409 `narration mentions an unavailable entity 'bench'` (`narration_known_term_leak`).
- **Live refusal probe on staging (7 commands, one session):** "Carry the workstation to the truck." and "Haul the driver's seat out of the truck." were refused with the fixed text; "Hoist the workstation, then open my laptop." was refused with the "Nothing else in that command was done" sentence; all three left `turn_index` unchanged. "Open the drawer.", "Close the back door.", "Look at the drawer." and "Put my laptop on the workstation." narrated normally. One narrator inconsistency (a drawer opened, then described as closed) is not a refusal issue.
- **The `@spine` failure is probably not caused by this change, but is not proven:** the player's own command contains "bench", the narrator repeats it, and the leak check (added 2026-09-11, no exemption for words the player typed) rejects it because the bench is not yet an available entity. The narrator prompt for that command in scene 1B is byte-identical on the previous main (fbba76f0) and on 1059073f. The merge changed none of `narration_safety.py`, the story data or the e2e prompts. No refusal text appears in the session feed, so the refusal did not fire. The last passing `@spine` artifact is dated 2026-08-30, before the leak check existed, and no later `@spine` run is recorded. It was not shown that fbba76f0 also fails: that would need the old build on staging or a live bench of the same journey.
- **Not done:** the toggle test (set `FREYTAG_FIXED_REFUSAL=0` on staging, rerun `@spine`, delete the variable) was blocked by the auto-mode classifier and did not run; staging variables were never changed (`FREYTAG_FIXED_REFUSAL` is unset, `FREYTAG_WORLD_CAPTURE=1`). The script is not committed.
- **Cause of the `@spine` stall, measured (2026-10-13, Ringer `astra-p4-1aexit`, bench runtime mode, scene 1A, the spine's four 1A prompts twice = 8 turns, 1 replicate per arm, replies near-identical so replicates would mostly repeat):** old main (fbba76f0), new main with the refusal off, and new main with it on all stayed in 1A for all 8 turns, never found the memory card, and showed the pressure line ("an officer ... lingers at the drawer") at turn 4. So the journey stalls on the pre-merge build too: the spine's fixed four-prompts-per-scene list cannot leave 1A, then types the 1B "bench" prompt in 1A, where the leak check correctly rejects it. The 2026-10-12 `@llm-canon` progress file shows the same four prompts leaving 1A unfinished after 4 turns. Replacing the second 1A prompt with "Search under the drawer in her workstation." did find the card (turns 4 and 6, new main, refusal on) but 1A still did not exit within 8 turns, so exiting 1A needs more than the card (not diagnosed; likely the recording and `michelle_lead_actionable`).
- **Open:** a spine (and canon) 1A journey that actually earns the exit, stepping adaptively until the scene changes; and a decision on whether a player's own word that names a later-scene entity should cost a turn (HTTP 409). Separate from the refusal.

## Phase 5: Three-arm comparison

Arms: (A) current pipeline with Phases 1-4 fixes; (B) same pipeline, stronger model; (C) smallest outcome-first prototype (resolve once, validate proposals, narrate from the accepted outcome, check, publish atomically), reusing existing machinery, on the drawer-to-truck sequence only. Do not rewrite all nine scenes.

Prototype scope for C: one shared grounded interpretation consumed by implicit actions, reveal selection, consequence validation and narration; bounded effect vocabulary; creation split into descriptive / interactable / route-clue-person-capability; engine-composed or authored clauses for custody, movement, discovery and transitions; in-world clarification when evidence is thin.

Drop C if gains vanish on held-out language, false reveals or story-breaking inventions rise, or it "wins" by refusing ordinary play. Keep A or B if they meet the bar more simply. Note the older finding that a separate post-narration capture call did worse, so C must earn its extra stage.

Exit: decision recorded with per-metric results.

## Phase 6: Adopt, extend or stop (gated by Phase 5)

- If C wins: migrate behind a flag, then extend timed events and openings to the same outcome validation (patrol return presupposes a visit; laptop notice presupposes the laptop's place). Narrator keeps game-break choice only for player-caused consequences.
- If A/B suffice: keep the pipeline, fold the reference record and refusal-in-prose fixes in permanently, close the arch review.
- Either way: update the README promise table qualifications ("never decides what an action does", "Canon holds"), the PRD, and the testing runbook (keep it short). Staging and production promotion follow `docs/railway-production-promotion.md`; no merge to main during staged E2E.

## Decisions

1. Stronger-model arm: affordable (Brandon, 2026-10-12).
2. Clarification questions do not consume a story turn or advance the clock (Brandon, 2026-10-12).
3. Only `continuity-initiative` exists in `data/stories/`. No second story yet (Brandon, 2026-10-12). All phases run on `continuity-initiative` only; revisit story-agnosticism later.
