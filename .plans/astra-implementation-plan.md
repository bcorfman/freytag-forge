# Astra review implementation plan

Sources: `.plans/astra-weak-spots-review.md` (material fixes) and `.plans/astra-arch-review.md` (turn pipeline).
Status: **Phase 0 done (2026-10-12); Phase 1 not started.** Update this file after each phase (see memory: update-plan-after-each-feature).

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

## Phase 4: Cheap architectural fixes that are valid under either design

Each is small, tested alone and measured before the next. These do not need the full pipeline and reduce risk whichever arm wins.
1. **Unknown identity is not authorized creation.** In the item-fact application path, an unresolved name that matches an existing person or thing must not create a new entity (the recorded duplicate-man failure). Add a test layer fix too.
2. **Refused moves must reach the prose.** When capture refuses a move the narration claimed, the player-visible reply must not still assert it. Choose between repair, re-narration or engine-composed clause; measure.
3. **Recent accepted references.** Add a small structured record of the last delivered cue's referents (entity links and source spans, from committed turns and authored cues only) to the reference-matching payload. This answers "search the gap". No permanent `gap` alias. Bound it by relevance.
4. **Keep possession, knowledge and concealment distinct.** Do not reuse the discovery-hidden state for concealment of an already-found item.

Exit: each item has a bench result; regressions checked against Phase 3's set.

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
