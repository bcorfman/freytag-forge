# Freytag Forge Multi-Agent Rewrite Plan (Revised with Recommendations 1-7)

## Summary
Adopt the moviemaking-role multi-agent architecture, but harden it for determinism and coherence control.
This revision applies recommendations **1-7**, with recommendation 2 changed to: **multiple critique agents + one final judge** (single judge retained for now).

## Key Changes
- [x] **Canonical state split (structured truth + narrative view)**
- [x] Add `StoryState.json` as a persisted turn artifact for state serialization.
- [x] Keep `STORY.md` generated as an agent-readable narrative workspace.
- [x] Orchestrator is the only writer to both artifacts.
- [x] `StoryState.json` and `STORY.md` are treated as authoritative canonical truth with schema-versioned diff trace.
- [x] `STORY.md` is regenerated from `StoryState.json` only; external mutations are rejected and logged.
- [x] Canonical state round-trip is deterministic across process boundaries.
- [x] Every `StoryState.json` diff is traced to a prior command and accepted `JudgeDecision`.
- [x] **Quality exit criteria for Key Change 1: validated against implementation**
- [x] Every persisted turn has exactly one valid `StoryState.json` schema instance and one `STORY.md` snapshot hash.
- [x] `STORY.md` is regenerated from `StoryState.json` only; mutation outside orchestrator is rejected and logged.
- [x] Canonical state round-trip is deterministic within a single process and across processes.
- [x] Each `StoryState.json` turn diff maps to one prior command and one accepted `JudgeDecision`.

- [x] **Coherence gate: multi-agent critique, single final judge**
- [x] Add multiple critique agents that return rubric-scored feedback.
- [x] Keep one `Director/Judge` as final arbiter for aggregate pass/fail decisions.
- [x] Keep weighted rubric + threshold `>=80/100` with critical-dimension floors and max `10` rounds.
- [x] All critique agents return all required rubric dimensions each round.
- [x] Judge aggregation is deterministic and documented.
- [x] A turn is accepted only if total score `>=80` and every critical floor is met.
- [x] Judge outputs include referenced critic IDs and rubric component scores.
- [x] **Quality exit criteria for Coherence gate met**
- [x] Rubric pass/fail thresholds are enforced and reproducible under fixed seeds.

- [ ] **Deterministic validators before judge loop**
- [x] Add pre-judge validators for:
- [x] entity existence/reachability
- [x] inventory/location consistency
- [x] contradiction checks against prior committed state
- [x] beat-transition legality from Story Supervisor
- [x] Reject invalid candidate before critique rounds and force revision.
- [x] Each validator returns explicit pass/fail and machine-readable reason codes.
- [x] Invalid candidates never reach judge scoring.
- [x] Deterministic invalid-turn fixtures have 100% recall.
- [x] **Quality exit criteria for deterministic validators met**
- [x] Golden corpus yields zero false positives for valid turns and deterministic reject path coverage.

- [ ] **Turn budgets and fail-fast controls**
- [ ] Define hard limits per turn: max critique rounds (10), per-role token budget, wall-clock timeout.
- [ ] Invoke hard-fail when any hard limit is exhausted with no earlier acceptance.
- [ ] Enforce no budget overruns.
- [ ] Emit per-turn telemetry for rounds, token spend, elapsed time, and hard-fail reason.
- [ ] **Quality exit criteria for turn budgets met**
- [ ] Failure/retry behavior under identical seeds is reproducible and bounded.

- [ ] **Hard-fail recovery with constrained reversal**
- [ ] Implement reversal seeding by Story Supervisor.
- [ ] Preserve committed facts/player agency and emit changed-vs-preserved delta.
- [ ] Replan from reversal state through normal critique pipeline.
- [ ] Include `preserved`, `modified`, and `discarded` categories in reversal output.
- [ ] Reversed candidates are revalidated end-to-end.
- [ ] Successful deterministic retry path exists under max-round failure.
- [ ] **Quality exit criteria for hard-fail recovery met**
- [ ] Reversal branch satisfies revalidation and traceability requirements.

- [ ] **Strict typed contracts for agent I/O**
- [ ] Define schemas for:
- [ ] `AgentProposal`
- [ ] `StoryPatch`
- [ ] `CritiqueReport`
- [ ] `JudgeDecision`
- [ ] `RevisionDirective`
- [ ] Enforce structured outputs with bounded natural-language rationale.
- [ ] Missing/invalid fields are rejected with deterministic error typing and no state mutation.
- [ ] Boundary validation is explicit in parser/adapter layer.
- [ ] **Quality exit criteria for typed contracts met**
- [ ] Parser/adapters reject malformed contracts and prevent silent fallthrough.

- [ ] **Evaluation harness aligned to classic IF output contract**
- [ ] Add golden-turn checks for diegetic output, debug internals, room-first structure, clarity prompts, and transcript-only echo.
- [ ] Add coherence regression tests on fixed seeds/commands.
- [ ] Golden tests are deterministic and byte-stable in non-debug sections.
- [ ] Debug mode can emit parseable internal trace.
- [ ] Non-debug mode never exposes engine labels or rubric internals.
- [ ] Coherence regression reports no narrative/state deltas on replay.
- [ ] **Quality exit criteria for evaluation harness met**
- [ ] Full output-contract matrix is green with fixed fixtures.

## Test Plan
- [ ] Determinism: same seed + command stream => identical `StoryState.json` history and accepted turn outputs.
- [ ] Validation gates: malformed/contradictory proposals fail pre-judge.
- [ ] Critique loop: pass path and budget-exhaustion path both deterministic.
- [ ] Single judge integration: judge decision must reference critic reports and rubric components.
- [ ] Reversal path: triggered only on threshold failure after max rounds; produces valid replan candidate.
- [ ] Output contract: non-debug contains no engine labels/scores; debug exposes internals.

## Assumptions and Defaults
- [ ] Big-bang rewrite remains the migration strategy.
- [ ] Single final judge retained for v1; critique support comes from additional specialist agents.
- [ ] Threshold defaults: total `>=80/100`, critical floors enabled, max `10` rounds.
- [ ] Orchestrator single-writer lock is mandatory; agents never directly mutate canonical files.
