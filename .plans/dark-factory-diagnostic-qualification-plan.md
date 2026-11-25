# Dark factory diagnostic and story repair qualification

**Status, 2026-11-23.** The evidence audit is complete. Autonomous repair and whole-game completion are not yet qualified. `main` is at `97fdde35`. This plan authorizes no implementation, model call, billed run or deployment; each needs the owner's word under the standing rules.

This hub is the current execution order for the dark factory. It supersedes conflicting status, next-action and completion claims in the [parent plan](Continuity%20Initiative%20dark%20factory%20plan.md). Detail lives in the linked subplans under `qualification/`. Mark a task `[x]` in its step file as soon as it lands, and update the step line here when a whole step finishes.

## What success means

- **Unseen repair.** A frozen factory gets symptoms and a pinned evidence export, investigates without private answers, chooses the cause and repair, implements it, and passes behavioral and fun checks. The sealed set is six cases with two trials each: four defects over at least three mechanisms and two scenes, plus two controls. At least one unseen structural repair must finish through the persisted workflow, and a later fresh live defect must transfer.
- **Whole game.** Every final replicate starts a fresh 1A session and carries its real facts to 3C. All eight transitions are earned, 3C reaches the authored ending, and every scene has zero confirmed stuck turns and zero unresolved cases. Continuity and fun pass. The 3C epilogue is offered after the ending, though the player need not take it.

The full definitions and the evidence behind every finding are in the [audit](qualification/audit-2026-11-23.md).

## Steps

Run Steps 1 to 5 in order before claiming autonomous repair. Step 6 can be prepared alongside. Steps 7 and 8 depend on both. Step estimates are planning ranges of active time and token allowances, not promises; see [how to read them](qualification/audit-2026-11-23.md#how-to-read-the-step-estimates).

- [ ] [Step 1: make the evidence set trustworthy](qualification/step-1-evidence.md) — 4 of 9 tasks done (1.1 to 1.3 and 1.7)
- [ ] [Step 2: repair measurement before optimizing against it](qualification/step-2-measurement.md) — contract, examples, pacing numbers, the null-grounding design, `build_contract_scene`, the typed pacing-event link (`delivers`, validator, 12 declared links), the pacing-only replay (`replay_pacing`) and the engine-side telemetry builder (`build_turn_telemetry`) are done and committed on `qualification-step2-contract-scene`; the adapters that call them (2.2 to 2.4), the spend reservation (2.5) and the delivery validator (2.6) remain
- [ ] [Gate-proving ladder](qualification/gate-proving-ladder.md) — approved 2026-11-23; R0 inventory done ([gate-inventory.md](qualification/gate-inventory.md)); R1 3 of 6 sub-rounds done (R1a stuck measures, R1b runtime rejections, R1c test pinning; [results](qualification/gate-r1-results.md)); proves the gate stack on test sets labelled by how they are built (good, seeded faults, meaning-preserving rewrites, per-scene subtracted twins), rung by rung from one gate to the whole game; Steps 4, 5, 7 and 8 wait on its rungs
- [ ] [Step 3: investigate causes before selecting a repair](qualification/step-3-investigation.md)
- [ ] [Step 4: complete repairs the current menu cannot express](qualification/step-4-structural-repair.md) — first real use is N-3
- [ ] [Step 5: qualify independent diagnosis and completed repair](qualification/step-5-qualify.md)
- [ ] [Step 6: scope of the whole-game structural check](qualification/step-6-structural-check.md) — unreachable-content ratchet and reachability check merged; the check is wired into station 5 as the `journey_reachability` free gate (round 32a, local, uncommitted)
- [ ] [Step 7: run the factory through actual scene repairs](qualification/step-7-scene-repairs.md)
- [ ] [Step 8: certify continuous 1A–3C completion and deliver](qualification/step-8-delivery.md)
- [ ] [Fun requirements and the N-3 decision](qualification/fun-requirements.md) — these extend Steps 2, 4, 6 and 8; items 1 and 2 of 7 done

## Decisions in force

- **N-3 must be reachable** (owner, 2026-11-23), and the factory must do it through Step 4. Phase Two is offered, not required.
- **Opus is the sole judge of the whole-game fun gate** (owner, 2026-11-23; a recorded exception to the different-families rule). Opus designs and checks all fun-judge logic, bounds and wording.
- **Null grounding is a pacing-only replay** (owner, 2026-11-23; [decision](qualification/null-grounding-decision.md)). No billed call. Clock-opened storylets never count as null grounding.
- **3B stays `wording_or_matching`.** All held-out candidates stay candidates until Step 1 passes. The structural slot needs a new unexamined case or a labelled synthetic one.
- **Strict adherence to this plan** (owner, 2026-11-22). The proposed pivot to real tickets was not adopted.

## Waiting on the owner

- Figures for the 1.4 sign-offs and the 1.5 canary, and for each Opus design session (fun items 3 to 7, the exploration-without-grounding design in Step 2, and the ladder's R1d fun-review calibration).
- The word to push the station and harness work in tasks 2.2 to 2.6.
- The `coverage nightly` gate: 88.4% against 90%. Either a test-hardening round on the story tooling or a lower gate.
- Whether the untracked round-18/19 manifests in `scripts/ringer/1a-stuck/` get committed as records.

## Standing rules

- Every code change goes through Ringer, test first. Check every Ringer check's shell fragments by hand before a round.
- `factory/config/**` stays frozen. Evaluator sessions run through `qual-20261122/tools/run_evaluator.py`.
- Never `rm` with globs. Never merge to `main` during staged runs.
- Write an estimate before every billed or subscription run and the actual after, in the parent plan's calibration table.
- World-state-only logic is a `World` method in `packages/worldkeeper`.
- Execution rules and the verification protocol are in the [original phase specification](qualification/original-phase-spec.md#execution-rules-for-sonnet-or-opus).

Workspace root: `/home/bcorfman/dev/ringer-work/qual-20261122/`.

## Resume here (2026-11-24, late: 2.2b engine side done, test consolidation done)

- Earlier findings (gate-proving ladder R0 to R1e-2, the story CLI as the only edit path, the 2.2b free checks, round 28a) are in [gate-r1-results.md](qualification/gate-r1-results.md), [null-grounding-decision.md](qualification/null-grounding-decision.md) and git history.
- **2.2b engine side done (rounds 29a to 29d, all free, Codex only):** the owner chose to declare the typed link in story source. A pacing beat may list `delivers` (knowledge ids); `pacing_link_problems(package)` checks the declarations against the facts and the real story is clean with 12 declared links (11 items). `story set` can now create a missing optional field (round 29b1); unknown keys still roll back. `replay_pacing(engine)` reports what a do-nothing turn would fire without touching the engine. `build_turn_telemetry` builds the contract's turn record from engine observations; a run built from real engine turns round-trips through `classify_run` with no `unknown_telemetry`. `npc_move` is always false and `recovery` is omitted because the engine records no signal for either (open question).
- **Test consolidation done (round 30a, owner's request):** one table-driven test (`tests/test_scene_commands_reach_reveals.py`, 18 cases in `tests/fixtures/scene_commands.json`) replaces five copied per-scene tests, `tests/scene_harness.py` replaces the copied engine helpers in those five files, and 12 structurally identical tests in five files are parametrized. Still to do if the owner wants it: 28 more test files copy `_engine` and `_handoff` helpers, and the 3A "wrist tags, radios, reader read after arriving" trio is a parametrize candidate.
- **Owner's word still needed:** wiring the pieces into the hosted path (`frontend/e2e/blind-player.js`, `storygame/web_demo.py`), the probe and qualification paths (2.2 to 2.4); `state` must stay in saved reports and the adapter must call `replay_pacing` before each turn. Also 2.5 and 2.6.
- **Round 32a done (free, Codex, 78k tokens, first attempt):** `journey_reachability` gate added to the station-5 free gates, then limited by 32b to story-data tickets (override key, 240 s timeout; 57k more tokens); 124 station/check tests pass; changes uncommitted in the working tree. Station code, so pushing waits for the owner's word.
- **Free, not started:** R1b-2 (adjudicating term-leak rejections; needs a method design first).
- Ringer actuals this session (Codex, subscription, no billed call): 29a 81k, 29b1 50k, 29b 51k after two failed attempts that were my own check bugs (the story CLI could not create a field; a superseded old test was off the ownership list; 229k tokens wasted), 29c 108k, 29d 54k, 30a 82k and 48k.

## Subplan index

| File | Read this when |
| --- | --- |
| [audit-2026-11-23.md](qualification/audit-2026-11-23.md) | You need the evidence for a finding, the full success definition, or the audit's scope and limits |
| [step-1-evidence.md](qualification/step-1-evidence.md) … [step-8-delivery.md](qualification/step-8-delivery.md) | You work on that step |
| [fun-requirements.md](qualification/fun-requirements.md) | You touch fun judging, pacing bounds, anti-flattening guards, story contracts or the 3C epilogue |
| [gate-inventory.md](qualification/gate-inventory.md) | You need to know which gates exist, which blocked a change, or which overlap |
| [gate-proving-ladder.md](qualification/gate-proving-ladder.md) | You add, change or remove a gate, send real story work through the full line, or see good content blocked |
| [null-grounding-decision.md](qualification/null-grounding-decision.md) | You build 2.2b or change how timed reveals are classified |
| [original-phase-spec.md](qualification/original-phase-spec.md) | A step points you to the original Phase 1 to 7 wording, execution rules or verification protocol |
| [resume-log.md](qualification/resume-log.md) | You need what a past round did, its cost, commit or PR, or why a decision was taken |
