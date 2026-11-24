# Step 2: repair measurement before optimizing against it

Part of the [qualification plan](../dark-factory-diagnostic-qualification-plan.md). The goal, check, estimate and owner's-word text below is the binding audit text, moved verbatim on 2026-11-23; the task list under it tracks progress. Work spec: `qual-20261122/qualification/step2-spec.md`; contract and frozen examples: `factory/outcome_contract.py`, `tests/fixtures/outcome_contract/`.

**Read this when:** you change how a turn is classified as stuck, progress, explored or pressure, touch telemetry capture, or wire the outcome contract into a path.

## Goal, check, estimate and owner's word

**Goal.** Give hosted play, replay, qualification and final delivery the same honest outcome contract, while retaining their distinct experiment purposes.

**Check.** Through Ringer, add hermetic cases for successful world actions without reveals, legitimate exploration, repeated futile named-object commands, unrelated timed reveals, prior delivered knowledge, provenance faults with healthy progression, healthy empty-failure input, missing telemetry, missing/duplicate replicates, skipped scenes and a real terminal ending. Check requested counts against the manifest, not just present rows. Keep raw flags and adjudicated outcomes side by side; never silently revise old reports. Demonstrate old false positives/negatives and the terminal gate failure first. Reconcile the foundation's remaining gaps, including crash-safe cumulative spend reservations for every provider/retry; a projected cap and a post-run excess flag are not a hard in-flight cap.

**Estimate.** 1–2 working days, approximately 200k–500k Ringer tokens and 35k–65k review tokens; deterministic execution $0. A model-based measurement calibration needs its own estimate after the examples are selected.

**Owner's word.** Station/harness changes and frozen gate/config revisions require approval under existing rules. Keep the zero-stuck requirement and 90% coverage rule. Any new fun-judging logic or wording must be designed and checked by Opus; do not write it in an orchestration prompt as a shortcut.

## Decided

- **Null grounding (owner, 2026-11-23): pacing-only replay.** Deterministic, no narration call; clock-opened storylets never count as null grounding. Reasoning, engine facts and fixture effects: [null-grounding-decision.md](null-grounding-decision.md). The wording is applied to `step2-spec.md` item 2.

**Priority raised (2026-11-23, gate ladder R1a).** The live gate's current stuck input wrongly blocks 12 of 15 good runs on the frozen examples ([R1 results](gate-r1-results.md)). Until 2.2b and 2.2 to 2.4 replace it with the outcome contract, no live-gate result is evidence about story quality, so these tasks come before more story or repair work.

## Tasks

- [x] **Frozen examples**: 27 cases (19 core, 8 extension) plus contract README.
- [x] **2.1 Contract module** `factory/outcome_contract.py` with tests; all 27 examples pass (PR #824, `fe2bcc14`).
- [x] **2.7 Pacing numbers and character-knowledge flag** (same PR). Numbers are reported, never gated, until F2 fixes the bounds.
- [x] **Null-grounding design** decided and written into the spec (2026-11-23).
- [x] **Strengthen the M4 fixture** (round 28a, 2026-11-24, first attempt, 40k Codex tokens; repo and workspace copies synced; 29 cases; uncommitted): replace the "Wait by the door." inputs with a futile command; add a counterexample where pressure fires while the command earns a different reveal, and one where a pacing event fires only because of the command's own fact.
- [x] **2.2b free checks** (2026-11-24; [results](null-grounding-decision.md#free-check-results-2026-11-24)): pacing items link to events through facts; replay needs a deep copy and still needs its unit test; 12 of 123 saved turns show a new grounding that is not the matched candidate (9 re-grounded, 3 pacing or bridge); matcher source is not recoverable from saved reports.
- [ ] **2.2b typed link** from each pacing event to the knowledge it makes deliverable, in the story schema and compiler, with a validator that rejects an unlinked pacing-linked item.
- [ ] **2.2b pacing-only replay**, test first. If it reads or changes only world state, it is a `World` method in `packages/worldkeeper`.
- [ ] **2.2b telemetry capture**: per turn `committed_facts`, `null_grounding_ids`, `pressure_event` (from the `fired_pacing_event_ids` diff), `npc_move`, `ending_latched`, `recovery`, `grounding_source`; keep `state` in saved reports. Test: a recorded run round-trips through `classify_run` with no `unknown_telemetry`.
- [~] **Fill `scene.delivered_before` from earlier scenes**: `factory/contract_scene.py::build_contract_scene(package, scene_id)` done (round 28a, first attempt, 53k tokens; uncommitted; also fills `pacing_window`, `terminal`, `ending_requires`; the other fields stay empty). Still to do: call it from each adapter (2.2 to 2.4), which do not exist yet. Original wording: so re-grounded knowledge (r4-2C turn 2, `k_sl_2b_b_r4`) is not read as new.
- [ ] **2.2 Hosted path** (`frontend/e2e/blind-player.js`). Owner's word to push.
- [ ] **2.3 Probe path** with a cross-path parity test on one fixture file. Owner's word to push.
- [ ] **2.4 Qualification path** (`run_case.py`, live playtest packets and gate, healthy/no-change diagnosis result). Owner's word to push.
- [ ] **2.5 Crash-safe cumulative spend reservation** for every provider and retry. Owner's word to push.
- [ ] **2.6 Delivery report validator** `factory/checks/final_report.py`.
- [ ] **Decision needed: exploration that reveals nothing.** The engine grounds only knowledge IDs, so a real "look around and the world answers" turn reads `no_effect` and counts toward stalls. This pushes repairs toward a reveal on every action. Needs a design (Opus, as fun-related logic) before the contract certifies anything.
