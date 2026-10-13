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
