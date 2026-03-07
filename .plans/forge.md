# Freytag Forge Multi-Agent Rewrite Plan (Revised with Recommendations 1-7)

## Summary
Adopt the moviemaking-role multi-agent architecture, but harden it for determinism and coherence control.
This revision applies recommendations **1-7**, with recommendation 2 changed to: **multiple critique agents + one final judge** (single judge retained for now).

## Key Changes
1. **Canonical state split (structured truth + narrative view)**
- Add `StoryState.json` as the authoritative turn state (entities, locations, facts, beat state, open threads, constraints, version).
- Keep `STORY.md` as agent-readable narrative workspace generated from structured truth plus approved notes.
- Orchestrator remains the only writer to both artifacts.

2. **Coherence gate: multi-agent critique, single final judge**
- Add multiple critique agents (for example: continuity critic, causality critic, dialogue-fit critic) that each return rubric-scored feedback.
- Keep one `Director/Judge` as final arbiter that aggregates critique outputs and issues pass/fail.
- Keep weighted rubric + threshold `>=80/100`, with critical-dimension floors and max `10` rounds.

3. **Deterministic validators before judge loop**
- Add rule validators that run before any scoring round:
  - entity existence/reachability
  - inventory/location consistency
  - contradiction checks against prior committed state
  - beat-transition legality from Story Supervisor
- Reject invalid candidate early and force revision without consuming full critique budget.

4. **Turn budgets and fail-fast controls**
- Define hard limits per turn:
  - max critique rounds (`10`)
  - token budget per role
  - wall-clock timeout
- If budget exhausted without pass: invoke controlled hard-fail path.

5. **Hard-fail recovery with constrained reversal**
- Story Supervisor authors reversal seed.
- Reversal must preserve committed facts/player agency and explicitly list what is changed vs preserved.
- Replan from reversal state through normal critique pipeline.

6. **Strict typed contracts for agent I/O**
- Define schemas for:
  - `AgentProposal`
  - `StoryPatch`
  - `CritiqueReport`
  - `JudgeDecision`
  - `RevisionDirective`
- Require structured outputs from all roles; natural-language rationale allowed only in bounded fields.

7. **Evaluation harness aligned to classic IF output contract**
- Add golden-turn checks for:
  - non-debug diegetic-only output
  - debug-only internal diagnostics
  - room-first display structure
  - direct clarification prompts for ambiguity
  - transcript-only command echo
- Add coherence regression tests on fixed seeds/commands.

## Test Plan
- Determinism: same seed + command stream => identical `StoryState.json` history and accepted turn outputs.
- Validation gates: malformed/contradictory proposals fail pre-judge.
- Critique loop: pass path and budget-exhaustion path both deterministic.
- Single judge integration: judge decision must reference critic reports and rubric components.
- Reversal path: triggered only on threshold failure after max rounds; produces valid replan candidate.
- Output contract: non-debug contains no engine labels/scores; debug exposes internals.

## Assumptions and Defaults
- Big-bang rewrite remains the migration strategy.
- Single final judge retained for v1; critique support comes from additional specialist agents.
- Threshold defaults: total `>=80/100`, critical floors enabled, max `10` rounds.
- Orchestrator single-writer lock is mandatory; agents never directly mutate canonical files.
