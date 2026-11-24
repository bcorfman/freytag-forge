# Dark factory diagnostic and story repair qualification

**Status, 2026-11-23.** The evidence audit is complete. Autonomous repair and whole-game completion are not yet qualified. `main` is at `97fdde35`. This plan authorizes no implementation, model call, billed run or deployment; each needs the owner's word under the standing rules.

This hub is the current execution order for the dark factory. It supersedes conflicting status, next-action and completion claims in the [parent plan](Continuity%20Initiative%20dark%20factory%20plan.md). Detail lives in the linked subplans under `qualification/`. Mark a task `[x]` in its step file as soon as it lands, and update the step line here when a whole step finishes.

## What success means

- **Unseen repair.** A frozen factory gets symptoms and a pinned evidence export, investigates without private answers, chooses the cause and repair, implements it, and passes behavioral and fun checks. The sealed set is six cases with two trials each: four defects over at least three mechanisms and two scenes, plus two controls. At least one unseen structural repair must finish through the persisted workflow, and a later fresh live defect must transfer.
- **Whole game.** Every final replicate starts a fresh 1A session and carries its real facts to 3C. All eight transitions are earned, 3C reaches the authored ending, and every scene has zero confirmed stuck turns and zero unresolved cases. Continuity and fun pass. The 3C epilogue is offered after the ending, though the player need not take it.

The full definitions and the evidence behind every finding are in the [audit](qualification/audit-2026-11-23.md).

## Steps

Run Steps 1 to 5 in order before claiming autonomous repair. Step 6 can be prepared alongside. Steps 7 and 8 depend on both. Step estimates are planning ranges of active time and token allowances, not promises; see [how to read them](qualification/audit-2026-11-23.md#how-to-read-the-step-estimates).

- [ ] [Step 1: make the evidence set trustworthy](qualification/step-1-evidence.md) — 3 of 9 tasks done (1.1 to 1.3)
- [ ] [Step 2: repair measurement before optimizing against it](qualification/step-2-measurement.md) — contract, examples, pacing numbers, the null-grounding design and its four free checks done; M4 fixture strengthened and `build_contract_scene` (fills `delivered_before`) built, both uncommitted (round 28a); the typed link, replay and telemetry capture (2.2b) are next, then wiring `build_contract_scene` into the adapters (2.2 to 2.4)
- [ ] [Gate-proving ladder](qualification/gate-proving-ladder.md) — approved 2026-11-23; R0 inventory done ([gate-inventory.md](qualification/gate-inventory.md)); R1 3 of 6 sub-rounds done (R1a stuck measures, R1b runtime rejections, R1c test pinning; [results](qualification/gate-r1-results.md)); proves the gate stack on test sets labelled by how they are built (good, seeded faults, meaning-preserving rewrites, per-scene subtracted twins), rung by rung from one gate to the whole game; Steps 4, 5, 7 and 8 wait on its rungs
- [ ] [Step 3: investigate causes before selecting a repair](qualification/step-3-investigation.md)
- [ ] [Step 4: complete repairs the current menu cannot express](qualification/step-4-structural-repair.md) — first real use is N-3
- [ ] [Step 5: qualify independent diagnosis and completed repair](qualification/step-5-qualify.md)
- [ ] [Step 6: scope of the whole-game structural check](qualification/step-6-structural-check.md) — unreachable-content ratchet and reachability check merged, not yet wired into station 5
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

## Resume here (2026-11-24, 2.2b free checks and round 28a done)

- The owner approved the [gate-proving ladder](qualification/gate-proving-ladder.md). R0 is done: [gate-inventory.md](qualification/gate-inventory.md) lists 22 content gates (about 360 rules) and 8 process gates, flags six signals measured by more than one gate, and ranks five R1 priorities (the live gate's all-or-nothing rule, the hosted stuck heuristic, runtime rejections, the full suite as a story gate, the eight fun checks). Copied prose in tests is down to 3 files and 4 sentences; 279 of 400 test files name real-story IDs.
- **R1a done** ([results](qualification/gate-r1-results.md)): the live gate's stuck input (gate 18) and the probe's (gate 20) each wrongly block 12 of 15 good runs on the frozen examples, because any turn that reveals nothing new counts as stuck and one such turn fails a scene. Gate 18 also passes 2 of 6 stuck runs. This is a measurement defect, so Step 2's outcome-contract wiring (2.2b, then 2.2 to 2.4) is now the highest-value work for getting story through the gates.
- **R1b and R1c done** ([results](qualification/gate-r1-results.md)). Runtime rejections: only the term-leak guard shows in saved retry telemetry (16% of bench turns retried, 4.4% visibly rejected; hosted 0.6%), and 3 of 4 sampled rejections repeat the player's own words, a possible false-rejection pattern. Test pinning: 268 of 400 test files assert on real-story IDs. That is an upper bound on structure pinning, not prose blocking.
- **R1e done** ([results](qualification/gate-r1-results.md#r1e-deterministic-gates-on-good-seeded-fault-and-variant-stories-2026-11-24)): no false block on the good story across gates 1 to 10; gates 3 and 4 act as one gate. The full suite fails every meaning-preserving variant, mostly (34 tests) because the factory never regenerates entry snapshots after a source edit (`write_entry_snapshots`); true wording and order pins are about 5 and 6 tests.
- **R1e-2 done** ([results](qualification/gate-r1-results.md#r1e-2-station-5-regenerates-entry-snapshots-variants-remeasured-2026-11-24)): station 5 regenerates entry snapshots in the ticket tree (owner's decision; patch in the working tree, uncommitted). The remeasured variants fail 0, 0, 5 and 6 tests: text-freeze tests and one possessive-rule order surface.
- **Story CLI is the only edit path** (same results section): station 5 formats and regenerates snapshots in the repair tree, `new beat --at-turn`, a wiring hand-edit log, and CI steps; merged as PR #826 (`2f9a2653`).
- **2.2b free checks done (2026-11-24)** ([results](qualification/null-grounding-decision.md#free-check-results-2026-11-24)): re-grounded earlier knowledge is the biggest false-progress source (9 of 123 turns), so `scene.delivered_before` moves ahead of the typed link; the link can be derived from event `sets` facts and item `commits` facts.
- **Round 28a done (2026-11-24, free, both tasks first attempt):** the M4 fixture now uses a futile command and has two new cases (29 in all); `factory/contract_scene.py` builds the contract's scene dict with `delivered_before` from earlier scenes and entry items, so the saved 2C, 2A and 1B re-groundings read as no progress. Changes are in the working tree, uncommitted.
- **Next, free:** the typed pacing-event link and validator, then the pacing-only replay (test first). R1b-2 (adjudicating term-leak rejections) needs a method design first.

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
