# Consolidated implementation plan

Status: **active; consolidated 2026-10-15 at local HEAD `5ea01199`.** This is
the execution queue for remaining work from `.plans/`. Superseded source plans and review drafts have been removed from this
directory; their evidence and decisions remain in git history. Their old
unchecked boxes and opening status lines are not additional queues. This consolidation does not authorize a
pipeline migration, experimental default, production promotion, or billed
experiment previously put on hold.

## Resume here

Start with **1. Budget-service reliability**, then finish the measurement gaps
in **2** before repeating the hosted spine in **3**. Continue with reference
resolution (**4**), reproduced correctness gaps (**5**), authoring visibility
(**6**), and playthrough qualification (**7**). Revisit the pipeline experiment
(**8**) only after its decision gate is met. Operational cleanup (**9**) can
accompany the relevant earlier phase.

The last recorded hosted spine on `9ec05da2` completed in 73 turns with no
`must_convey` misses, recovery, guard retry, or fallback. An earlier attempt
failed with `BUDGET_UNAVAILABLE`. This is one clean sample, not a reliability
claim or proof that unscripted players can finish well. No live environment
was inspected or changed for this consolidation.

## Execution rules

- Follow the [PRD](../docs/PRD.md), [contributor guide](../docs/contributor-guide.md),
  [agent workflow](../docs/agent-workflow-guide.md), and
  [testing runbook](../docs/testing-runbook.md). Verify current source and CLI
  behavior before relying on old file paths, commands, environment settings,
  or schema versions in a source plan.
- Facts remain the sole mutable world truth. Shared runtime stays story-agnostic
  and LLM-proposal-first. Preserve atomic commits, rollback, bounded model
  proposals, and clarification without advancing story time.
- Read the [grounding guide](../docs/world-model-grounding.md) before story
  placement or model-facing place descriptions. Follow the
  [scene-fixing](../docs/scene-fixing-guide.md),
  [narrator-writing](../docs/narrator-writing-guide.md), and
  [player-input](../docs/player-input-guide.md) guides. Diagnose recorded prompts
  before adding rules; authoring repairs belong in source material.
- Carry forward the active plans' Ringer workflow: one scoped code/data task
  per run unit, hermetic regression checks, Ruff and appropriate suite/coverage
  gates. Verify installed runner options and timeouts rather than copying old
  model or invocation settings.
- Smoke-test before billed runs; enforce every endpoint's call/spend guard.
  Bind evidence to code/package/config identity and record every attempt,
  including successes, refusals, infrastructure failures, and incomplete runs.
  Keep diagnostic and held-out commands separate. Small repeated samples are
  smoke evidence, not independent proof of reliability.
- Use SHA-bound staging deployment and verify its identity before hosted E2E;
  do not merge during a run. Follow the
  [promotion guide](../docs/railway-production-promotion.md). Production
  promotion remains outside this playthrough plan.
- After each completed feature, update this file's status and Resume here with
  commit/PR, verification, artifact location, and remaining limitations. Change
  runbook procedures in place only when procedures change.

## 1. Diagnose and repair budget-service reliability

Sources: assessment follow-up (`astra-assessment-implementation-plan.md`, historical),
rate limits (`rate-limits.md`, historical).

- [ ] Trace the failed daily-budget Durable Object call from the recorded
  `9ec05da2` journey (turn 58). Separate counter availability, Worker errors,
  transport, and API translation; reproduce with controlled failures before
  changing retries or status mappings.
- [ ] Resolve why `BUDGET_UNAVAILABLE` reached the client as HTTP 502 while the
  Worker documentation says 503. Align implementation, error-contract tests,
  and documentation with the intended behavior.
- [ ] Preserve fail-closed reservation/settlement and the daily spend cap;
  demonstrate that failure/retry cannot bypass accounting or partly commit a
  turn. Record the diagnosed cause or the precise remaining uncertainty.
- [ ] Verify deployed per-IP isolation and trusted-proxy configuration from the
  rate-limit plan: one client's exhausted session bucket must not block a
  second network. Retain the staging-only token exemption and Worker budget.
  The API/Worker implementation is already merged in PR 482; do not rebuild it.

Exit: regression checks cover the observed failure and error mapping; a
bounded staging smoke succeeds with identity and counter behavior recorded.
If the intermittent failure cannot yet be reproduced, explicitly carry it as
an operational risk into the next measurement rather than reporting it fixed.

## 2. Finish measurement and harness correctness

Sources: assessment A3, playthrough quality (`playthrough-quality.md`, historical),
[world model](world-model.md), Astra Phase 3.

- [x] Include `jev_stats()` in the bench summary so call caps, failures, quota
  stops, requests and cost are visible alongside narration metrics.
  Done (uncommitted, Ringer run `stage2-measurement-correctness`): `budget.jev`
  in `summary.json` with calls/ok/failures/stopped/cap_reached/requests, reset
  per run; tests in `tests/test_jev_summary.py`. Limits: no cost figure (no
  source exists) and no per-failed-replicate snapshot (stats are process-wide).
- [x] Extend the pipeline harness's refusal coverage through the real fixed
  refusal path; its existing runner test uses a stub engine seam. Verify zero
  narration requests, real unchanged state, and all classifier costs.
  Done (uncommitted): `PipelineArm(refusal_ask=...)` builds the real
  `WorldCapture` (fixed + engine refusal); classifier asks count as requests;
  tests use a fake ask, no stub engine. Limit: classifier tokens only counted
  if the ask result carries `usage`.
- [x] Complete the evaluation vocabulary-to-facts mapping where metrics still
  report `unmeasured`. Keep reference, action, state, prose, invention,
  disclosure, forced progress, clarification burden, latency, requests and
  tokens separate. Do not manufacture scores for unavailable observations.
  Done (uncommitted): `<metric>_unmeasured` counters for reference, action, state, prose, false reveal, creation, forced progress, clarification; observation defaults are now `None` (unknown), so absent evidence no longer scores as a pass. `PipelineArm` fills forced progress from `transition_cause`; reference/action/clarification/creation stay unmeasured (runtime exposes no typed evidence).
- [x] Correct journey judging to use committed reveal evidence instead of
  treating narration `grounding_ids` as the complete earned-knowledge set.
  Separate genuine premature disclosure from invented facts, and validate
  disputed judgments by reading the recorded turns. Use the existing journey
  judge; recheck whether the repaired spine also resolves the old
  `@llm-canon` stall before proposing a second script rewrite.
  Done (uncommitted): `judge-journeys.js` builds `revealedKnowledgeIds` from committed attempt-bundle reveals (joined from `scene.bundles` by turn), ignores rejected/game-break turns, falls back to `grounding_ids` only for bundle-less turns and marks `reveal_evidence`; judge prompt separates premature disclosure from invented detail (schema and 7 checks unchanged). NOT done: reading disputed judgments in recorded turns, and rechecking the `@llm-canon` stall (both need a billed run).
- [x] Teach the blind-player harness to record and handle game-break panels,
  with an explicit choice policy and separate outcome counts. Preserve pending
  state/rollback evidence; do not silently classify a panel timeout as a story
  stall or silently choose a destructive branch.
  Done (uncommitted): `BLIND_PLAYER_BREAK_POLICY` (`return` default | `proceed`), `handleGameBreak` records reason/decision/outcome/before/after, timeout stops the scene and is counted separately (`game_break_*_count/rate`), never as stuck; `resolveWarningIfPresent` throws on timeout. Limit: `after` state is null unless a next payload is supplied; no live browser run yet.
- [x] Reuse attempt bundles for remaining targeted checks: reveal earned versus
  cue delivered, earned/forced/timer exits, rare selection outcomes, refusal
  telemetry, and recovery stages. Keep hermetic coverage for rare outcomes
  rather than spending until they happen by chance.
  Done (uncommitted): `python -m bench.bundle_report PATH...` (reveal earned vs cue, exits by cause, selection outcomes incl. never-observed ones, refusal telemetry, recovery stages, invalid bundles). On the saved 69 attempts: 0 invalid; `budget_exhausted`, `exact_tie`, `provider_error` never observed (need hermetic scenarios, not live spend).

Stage 2 status: all six items implemented 2026-10-15 via Ringer run `stage2-measurement-correctness` (manifests in `scripts/ringer/stage2/`), uncommitted on `astra-step-d`; full suite 1813 passed, ruff clean on bench/tests/storygame. Open: the rare-outcome hermetic scenarios, the billed judge validation above.

Exit: saved records and hermetic scenarios produce truthful summaries, with
unmeasured fields explicitly identified. The next billed run can answer its
stated question without another harness repair.

## 3. Establish the current staging baseline

Sources: assessment latest/Step B, Astra latest, playthrough quality.

- [ ] Repeat hosted `@spine` on a stable, identified staged build. Choose and
  record the replicate count and stopping rule first; include failed attempts
  in the denominator. Report infrastructure failure rate separately from
  gameplay failures and recovery/fallback rates.
- [ ] Preserve assertions that the intended reveal chains commit, including
  2C C-R2, and that the story actually completes. Reaching 3C alone is not
  the ending. A transition at `min_turns` need not commit another reveal.
- [ ] Verify the merged player-facing engine-error line on staging: rejected
  turns do not expose protected terms, state remains unchanged, and provider
  outages retain their separate error contract.
- [ ] Fold the remaining linked 1A-to-1B phone-alias smoke into this work only
  with a script that actually elicits the relevant ordinary photo words.
  The existing 0-versus-0 probe did not exercise the defect; do not repeat it
  unchanged or claim it measured an improvement.

Exit: a current baseline table with artifact links, attempted/completed runs,
reveals, exits, ending, failures, requests, latency, and evidence limitations.

## 4. Resolve references from accepted context

Sources: assessment C2 / Astra Phase 4.3;
scene affordances (`scene-affordance-e2e.md`, historical), “resolve a bare noun” decision.

- [ ] Reproduce the recent-cue follow-up miss with a narrow engine test. Add a
  bounded projection of the last accepted authored cue's referents, entity
  links and source spans to reference matching. Do not add transcript memory
  or a permanent alias for an incidental cue phrase. Rejected turns must not
  update the record; test expiration, scene changes, ambiguity and save/load.
- [ ] Reconcile and implement the still-unbuilt scene-local bare-noun decision
  through the same resolution boundary, avoiding a competing matching path.
  Unique in-scope referents resolve; multiple referents produce the agreed
  fixed system question without narration, facts, or clock advancement.
- [ ] Preserve the October 6 answer policy: splice a recognized answer into
  the original command; unrelated input cancels the pending question and runs
  normally; cap clarification rounds at two. Clear pending questions on scene
  change and reload. Pending interaction context is transient, not a world
  fact and not narrator knowledge. Verify the hosted request lifecycle can
  retain it between requests without making it durable save state.
- [ ] Test full-name precedence, scoped aliases, collisions, wrong-target
  negatives, and no reveal granted solely by reference resolution. Make the
  browser and blind player handle the system question.
- [ ] Measure the targeted follow-ups and the previously identified 3B relay
  cases, including clarification burden and false resolutions, before moving
  to the next behavioral fix.

Exit: bounded references improve the reproduced cases without false grants,
leaks, duplicate entities, or advancing a turn to ask a question.

## 5. Reproduce remaining correctness gaps, then fix individually

Sources: assessment C3, Astra Phase 4, playthrough quality, world model,
scene-affordance open cases and raw-language corpus.

- [ ] Reproduce concealment after discovery and a subsequent NPC encounter.
  If the discovery-hidden state is being reused for concealment, separate
  possession, observer knowledge and concealment through validated facts.
  If no confusion is reproduced, close the implementation item with evidence.
- [ ] Check the raw-language corpus's documented false grants, pronoun misses,
  correction/compound-action and unrelated-restraint cases against current
  runtime behavior. Use author-reviewed evidence changes for proven authoring
  misses; preserve ties and negation safety. Do not widen matching solely to
  turn corpus entries green.
- [ ] Reassess the remaining narration-quality failures using accepted turn
  evidence: invented routes/clues, unrequested plot-changing actions, repeated
  scene tails, contradictory custody or rescue state, and unmotivated exits.
  Warehouse drift has no diagnosed source line; do not treat it as an approved
  story-text edit. Use the existing invention cases to bound any proposed fix.
- [ ] Replay skipped-copy and Michelle-first 2C paths, 1A avoiding the drawer,
  and late-scene disclosure/custody cases. Include the 3A medical-records item
  and scene-scoped place vocabulary. Review residual guard complaints against
  [disclosure decisions](disclosure-decisions.md); ordinary vocabulary and
  earned secrets must not be conflated. Do not weaken a correct guard because
  a player's command asks for protected knowledge.
- [ ] Read unresolved pointer-placement failures before changing cue text;
  preserve the proven escalation timing and distinguish an abrupt appended
  pointer from failure to deliver a pointer.
- [ ] Carry the unknown-identity fix's live limitation into the appropriate
  run: the prefix fix covers declared unnamed characters, not every unresolved
  existing entity. Reopen parked knock-out, state-echo, false-pole, bare-corridor
  and residual hand-back defects only when current play reproduces them.

Exit per fix: recorded reproduction, smallest appropriate source/runtime
change, meaningful regressions, and targeted measurement. Preserve failures
that remain; a clean scripted spine cannot close these cases.

## 6. Build the read-only scene contract report

Source: design review (`design-review-implementation.md`, historical), Step 10.

- [ ] Assemble plot metadata, knowledge, action evidence/contracts, routes,
  handoffs, pacing, effects and exits per scene, with source provenance and
  duplicate-value warnings. Keep generated output read-only.
- [ ] Demonstrate that a reviewer can trace cue → action → delivery → effect →
  exit for 2C from one report, including timing and prerequisite gates.
- [ ] Use the report for the remaining package audit: earned reachability of
  every reveal/exit, fresh disclosure matrix and narration corpus, save/load
  at scene boundaries and re-entry, pacing against the two-hour target, and
  forced-handoff consequences. Reuse existing audit tools.

Exit: reviewable report and concrete authoring risks. A compiler pilot remains
deferred until this report demonstrates work it would actually remove.

## 7. Qualify the whole playthrough and continuity

Sources: playthrough quality Phases 1–5; continuity Phases 7–8; world-model
runtime sweep; design-review recovery and skipped-reveal limitations.

- [ ] After targeted fixes, run hosted canonical and raw blind-player journeys
  over all nine scenes, three matched starts per profile after a smoke. Use
  earned entries and include the skipped-copy/Michelle-first coverage from
  phase 5; add linked late-scene continuations where the journeys do not cover it.
- [ ] Read two complete transcripts for continuity, tone, repetition and the
  ending. Inspect reveal, pointer and exit turns in every targeted continuation.
  Verify the ending marker, disabled input and provider-free completed-session
  behavior, including a final forced-handoff path.
- [ ] Measure world-state accuracy on the actual runtime path with calibrated
  judges, including scene exits, custody, dependency breaks, proceed/return,
  save/load and initiative capture. Report per-change-type denominators against
  the inherited 92% target; do not substitute a pooled percentage or judge
  noise for passing each category. Record per-turn token and latency costs.
- [ ] Apply the playthrough gate: at least two of three runs per profile finish
  through earned exits, no rejected ordinary vocabulary, no premature secrets,
  and pacing within the target. Report forced/assisted progress separately.
  Use paired entry scenarios and uncertainty estimates for efficacy claims;
  three journeys are a smoke gate, not a measured player-success rate.
- [ ] Write the missing sign-off: passed, failed, unmeasured, known risks and
  next decisions. Human-player benefit and cross-story reliability remain
  unproven; the earlier second-story live gate was explicitly dropped.

Exit: an honest staging readiness report. Failure returns to the relevant
targeted phase, not to broad prompt tuning or a new architecture by default.

## 8. Conditional pipeline comparison and adoption

Sources: Astra Phases 5–6; assessment Step E; design-review Step 8 correction.

**Hold until measurement is trustworthy and numeric keep/drop margins are
written.** Cheap correctness fixes and evidence collection precede this work.

- [ ] Specify numeric held-out gain, false-reveal/invention ceilings, refusal
  and clarification burden, latency and total-cost margins before any run.
  Establish the live claim judge and full request/state accounting still
  missing from the comparison; use fresh commands and varied starting states.
- [ ] Compare A: repaired current pipeline; B: the same pipeline with a
  stronger model; C: the smallest outcome-first prototype on the existing
  drawer-to-truck sequence. Do not rewrite all scenes. C reuses facts and
  worldkeeper, resolves once, validates bounded consequences, narrates accepted
  outcomes, and publishes atomically.
- [ ] Drop C if held-out gains disappear, unsafe invention/disclosure rises,
  or apparent improvement comes from refusing ordinary play. Prefer A or B
  when they meet the criteria more simply. Record each metric and the decision.
- [ ] Only if C wins and adoption is chosen: migrate behind a flag, then extend
  outcome validation to timed events and openings. Otherwise retain the current
  pipeline and close the architecture experiment. Update README promise
  qualifications, PRD and affected runbook procedures to match the decision.

The typed action contract remains shadow-only and off by default: its claimed
live recall gain was withdrawn because exact matching already covered the
examples. Expansion/activation requires genuinely missed held-out actions,
more near misses, and a decision on state-check versus state-claim semantics.
`renarrate` and the absent-thing rule remain off; do not resume their adoption
work on the failed measurements.

## 9. Operational and historical closure

- [ ] Remove the HTTP test-clock seconds field, header, CORS entry and route
  plumbing as specified in rate limits (`rate-limits.md`, historical). It is still present
  in current code. Keep the staging token exemption and the in-process engine
  clock used by tests; update HTTP compatibility checks and the runbook in place.
- [ ] Verify and restore the staging turn cap left at 60 in the October 12
  records. Verify the temporary 500-session override is no longer effective
  after deployment. Prefer the existing scoped exemption for E2E. Do not assume
  these old configuration values describe today's service.
- [ ] Keep the persisted per-session semantic-call budget as a deferred
  follow-up, distinct from the implemented per-turn narration budget and
  Worker-wide spend cap. Reopen with explicit session-lifetime accounting and
  save/load tests; the old per-provider counter is not a session budget.
- [ ] Reconcile the old escalation Phase 9 ledger: locate partial live trials,
  label completed versus missing arms and record the remaining n≥50-per-arm
  comparison as held pending its original spending decision. Do not rerun a
  historical control automatically against today's substantially changed
  package. Option C (all exit scenes) remains contingent on Option B's result.
- [ ] Preserve deferred 2A credentials/1B transit placement and cross-scene
  command execution issues for reproduction. Do not implement an automatic
  next-scene transition from the old continuity sketch without a current
  progression contract. Retire stale flat-state and narrator-regeneration
  tasks superseded by worldkeeper and the later refuse-and-record decision.

## Source reconciliation

Historical source filenames below refer to git snapshot `5ea0119955c62b84699a8dc7878a4af770b55a7e`.
Retrieve one with `git show 5ea0119955c62b84699a8dc7878a4af770b55a7e:.plans/<filename>`.
`world-model.md` is now a short checklist of the conditional follow-up not
otherwise explicit here, with retrieval instructions for its historical decisions.
The disclosure decisions/matrix and probe scripts remain in this directory
because current guides and implementation work use them.

Later dated results and recorded decisions take precedence over stale opening
summaries. These items are already done or superseded, not new implementation:

| Source | Reconciled disposition |
|---|---|
| Astra assessment (`astra-assessment-implementation-plan.md`, historical) | A1–A3, B, C1 and the committed-reveal/spine work landed; carry A3 evidence gaps into 2. Step D is complete in local commit `5ea01199`, despite the older header saying otherwise. C2/C3 → 4/5; E → 8. |
| Astra implementation (`astra-implementation-plan.md`, historical) | Do not redo cap authority, shared recovery accounting, typed-term feedback, alias/pointer fixes, fixed refusal or spine prompts. Guard retry was measured, not still awaiting its first measurement. The outside-turn budget-lifecycle caveat was addressed in `a84c8ad8`. Phase 3/4 gaps → 2/4/5; Phases 5/6 → 8. |
| Design review (`design-review-implementation.md`, historical) | Steps 1–9 have later implementation/measurement records; Step 6 and Step 8 merged in PRs 608/610, and Step 9 has hosted profile results. Remaining coverage → 2/5/7; Step 10 → 6. Contract activation, compiler and persistent budget stay conditional. |
| Playthrough quality (`playthrough-quality.md`, historical) | Its “not started” header predates completed journeys, ending implementation, alias/pointer and safety fixes, and recorded judge runs. Carry quality, harness and sign-off gaps into 2/5/7/9. |
| Scene affordances (`scene-affordance-e2e.md`, historical) | The requested all-nine-scene regression ran later in the same file. Newer design/Astra work supersedes many leak/matcher todos. Remaining bare-noun decision → 4; detours, secrecy and quality coverage → 5/7. |
| [World model](world-model.md) | S1–S4 and runtime capture are implemented; the old request to merge the 1B/1C fixes is closed by PR 508 (`2fa40ee2`). Keep residual measured gaps and continuity qualification in 5/7, with explicit parked conditions. |
| Narrated continuity (`narrated-world-continuity.md`, historical), capture experiment (`narrated-world-changes-experiment.md`, historical) | Superseded capture design and flat-state implementation are historical. The full-loop plan exists and runtime integration shipped; retain evaluation/rollout obligations and reproduced independent defects in 5/7/9. |
| Escalation design (`missed-obligation-escalation.md`, historical), implementation (`missed-obligation-escalation-implementation.md`, historical) | Integration merged in PR 464 (`802c12c4`), despite unchecked merge boxes. Preserve remaining measurement accounting and conditional defects in 9, not a second implementation of Phases 1–8. |
| Rate limits (`rate-limits.md`, historical) | Tasks 1/2 merged in PR 482 (`130300fc`); remaining live configuration evidence, budget incident and HTTP cleanup → 1/9. Old `.plans/cloudflare.js` deployment paths are historical; verify current Worker source/config. |
| Jev judge trial (`jev-judge-trial.md`, historical) | Decided: Jev fact judge, Luna continuity judge (`35f2de9f`). Do not restart the abandoned Jev continuity trial. Current judge calibration belongs in 2/7. |
| Reviews, ChatGPT prompts/answers, freeze files, disclosure matrix/decisions, diagnosis notes and probe scripts | Supporting evidence and accepted constraints, not separate execution queues. Refusal freeze changes were disclosed policy revisions, not strict preregistration. Generated matrices and probe artifacts are not authoring truth. |

## Completion record

Consolidation only: reviewed plan status/results and relevant repository
guidance, checked selected stale claims against git history and code discovery,
and created this queue. No runtime changes, tests, billed probes, deployments,
configuration changes, or production promotion were performed.
