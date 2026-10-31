# T9h route E: enforced drain run with J1c on and off (preregistration, DRAFT, nothing built, nothing billed)

Status: APPROVED by Brandon 2026-10-30 (route, 20 replicates per arm, gates D1 18/20 and D2 16/20, $0.20 cap); free harness build started; billed stage awaits his go. Originally DRAFT 2026-10-30; step 4 of `t9h-j1c-wiring-plan.md`. The product change (step 3) is built and merged nowhere yet: it is on branch `t9h-stage-s-result`, flag `FREYTAG_OBSERVATION_SCENE_STATE`, default off. This run decides whether the flag fixes the drain miss in the real engine.

**Question.** With the enforcing verifier on and the J1c scene state on, does the engine commit `inspect the storm drain` in scene 1B, and does it still refuse to commit a narration that opens, moves or fills the drain?

**Why the run is narrow, not the whole of route E.** The earlier route E smoke (`t9h/smoke/e`) had 5 unsuccessful turns of 11. Only one was the drain (`ProposalValidationError` after two `uncertain` verdicts, 0.58 and 0.57). The other four were `search the park bench` and `check the park bench` turns rolled back by the unrelated-move guard (the narrator picked up the bench's hidden items) and one call-budget turn. J1c does not touch that cause, so a full route E run would fail G1 for a reason this change cannot fix and would tell us nothing about the drain. The bench problem stays open (see `.plans/chatgpt-t9h-route-e-hidden-clues-plan.md`).

**Arms.** Both arms run the real engine, product wiring, enforcing verifier, local Worker, 70B JSON off, 20 s timeout and no retry on a timeout, as T9d and T9e (`enforce_t9h.sh`).
- `OFF`: enforcing verifier as today (no scene state).
- `ON`: the same, with the scene state on (`scene_state=True`).
Each replicate restores the 1B entry checkpoint (index 9, as the route E harness does) and plays ONE command: `inspect the storm drain` (a new bench route `observe_storm_drain_1b`, one turn). Arms are run as separate invocations with a fixed order (OFF replicates first, then ON), each with its own call cap; same model and settings; the Jev model/version is recorded.

**Counts and cost.** Smoke: 3 replicates per arm, `--max-calls 40` per arm, `--max-usd 0.04`. Full: 20 replicates per arm, `--max-calls 220` per arm, `--max-usd 0.20`. The earlier route E averaged about 8 calls per turn and about $0.003 per turn (39,073 micro-USD over 12 turns), so expect about $0.12 for the full stage (an estimate). No reruns; stop on any quota code, 429, 5xx or cap. The smoke is not gated; it checks the plumbing and the `scene_state` record. The full stage is gated.

**Labels (frozen before any verdict is opened).** Procedure as T9d: blind sheets, I read every committed narration and every rejected first attempt, freeze the labels hash, then join. Per narration: `opens_drain` (the drain is opened, lifted or entered), `moves_drain`, `gives_contents` (the narration says what is inside, or puts a new object in or at it), `really_deficient` for a rejected attempt (the drain is missing, remembered, elsewhere or denied in the prose). Invented vegetation or debris is not a tag (the project counts it only if story-breaking).

**Gate (set now; applies to the ON arm; the OFF arm is printed beside it).**
- D1 commits: at least 18 of the 20 ON turns end with a committed narration. Wilson interval printed.
- D2 first attempt: at least 16 of the 20 ON turns are accepted on the first attempt (no rejected attempt before the commit).
- D3 control (G9 of the confirmation preregistration): zero committed ON narrations labelled `opens_drain`, `moves_drain` or `gives_contents`.
- D4 state sent: every ON verifier request on this turn has `scene_state` true and no OFF request has it. Zero violations. (The drain is scene-level in the compiled package, checked by a test.)
- D5 rollback and budget (T9h G4, G5): every unsuccessful ON turn leaves `places_after == places_before`, a typed error and no narration; no turn uses more than 2 narration attempts or 2 verifier requests. Zero violations.
- D6 false rejects: at most 1 rejected ON first attempt is labelled not `really_deficient`.
Printed, not gated: OFF commit and first-attempt rates, verdict scores per arm with ranges, the `call timing` block per arm, attempts per turn.

**Reading the outcomes.** All pass and the OFF arm shows the miss (its first-attempt rate well below ON's): the drain fix is confirmed in the engine; next, a short addendum proposing a staging run (Stage H style) and the hosted flag, needing Brandon's explicit instruction. OFF also commits at the ON rate: the drain miss does not reproduce in the engine; record it, and J1c stays off. D1 or D2 fails: read the rejected ON attempts; if they are real misses, the design changes. D3 fails: stop; J1c's state is letting a bad narration through. D4 fails: a wiring defect; fix before any further billed run.

**Limits.** One command in one scene, 20 replicates per arm: the effective n is 20 per arm, and the recorded drain replies came from earlier prompts. Arms run one after the other, not interleaved, so a drift in the Worker between them would show as an arm difference. The run does not measure the bench problem, other scene-level things, or latency gates. It does not qualify enforcement for the game.

**Free build (Ringer, tests first, before any billed stage).** (1) `scripts/ringer/transcript_1a/live_baseline.py`: route `observe_storm_drain_1b` (one command, start scene 1B), registered in `NEW_ROUTES` and `ROUTE_START_SCENES`, and a `--scene-state` flag that builds the enforcing verifier with `scene_state=True` and records `scene_state` in the per-turn rows. (2) `enforce_t9h_drain.sh smoke|full`: local Worker, OFF then ON, caps as above, no rerun. (3) A small report (`enforce_drain_report.py`) with the D1 to D6 arithmetic over the joined labels. Existing live_baseline and enforce tests stay green.

**Decisions for Brandon.** Approve or change: the one-command route and 20 replicates per arm; the gate numbers (D1 18 of 20, D2 16 of 20); the cost cap ($0.20); and whether to run the full route E later, after the bench problem is fixed.
