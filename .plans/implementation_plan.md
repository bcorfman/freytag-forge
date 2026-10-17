# Consolidated implementation plan

Status: **active; consolidated 2026-10-15 at local HEAD `5ea01199`.** This is
the execution queue for remaining work from `.plans/`. Superseded source plans and review drafts have been removed from this
directory; their evidence and decisions remain in git history. Their old
unchecked boxes and opening status lines are not additional queues. This consolidation does not authorize a
pipeline migration, experimental default, production promotion, or billed
experiment previously put on hold.

## Resume here

**1. Budget-service reliability is DNF (dropped by Brandon, 2026-10-15); do not
start or retry it.** The measurement gaps in **2** are closed and the hosted
spine baseline in **3** is complete. Start with reference
resolution (**4**), then reproduced correctness gaps (**5**), authoring visibility
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

**Status: DNF (did not finish; dropped by Brandon 2026-10-15). Do not attempt
this stage again unless Brandon reopens it.** The boxes below stay unchecked on
purpose and are not an open queue. Only a read-only diagnosis was done, nothing
was changed or merged, and the Ringer manifest, run and branch were discarded.
Findings, for the record: the client-side 502 comes from
`CloudflareTurnProvider._narration_error` (`storygame/runtime/cloudflare.py`),
which maps every Worker 5xx without a special case to 502, while the Worker
(`worker/src/index.js`) returns 503 for `BUDGET_UNAVAILABLE` and
`docs/cloudflare-narration-worker.md` lists 503; no test covers that mapping.
The client never retries an answered `HTTPError`, and the Worker makes no AI
call when the counter fails (covered by its test). The turn-58 Durable Object
failure was not reproduced and is carried as an unresolved operational risk;
per-IP isolation and the trusted-proxy check were not verified.

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
  Done (uncommitted): `judge-journeys.js` builds `revealedKnowledgeIds` from committed attempt-bundle reveals (joined from `scene.bundles` by turn), ignores rejected/game-break turns, falls back to `grounding_ids` only for bundle-less turns and marks `reveal_evidence`; judge prompt separates premature disclosure from invented detail (schema and 7 checks unchanged). Disputed judgments read 2026-10-15 (canonical x3 of 2026-10-12 judged by Luna; journeys and bundles in `~/dev/ringer-work/keep/canonical-x3/`): the `protected_safe=false` verdicts on rep 1 1A, rep 1 3C and rep 3 1C all land on exit turns whose text is authored runtime delivery, not narrator disclosure (1A t14 and 1C t11 are `transition_cause=forced` handoffs; 3C t14 commits storylet-route ending facts with `story_complete` and no knowledge ids). Committed knowledge ids are empty for those turns, so the repaired judge input still calls them unearned. GAP: judge input must also carry committed authored delivery (forced/timer handoff and ending text, `committed_delta.fact_predicates`, `selected_reveal.delivery_fact_ids`) so authored text is not charged as disclosure. Genuine narrator defects the judge also found stand: rep 1 1A invents an 'old warehouse' meeting text that pulls the player off the scene (t6-t13); rep 3 1C invents a 'biohazard containment zone'; rep 1 3C narrates a hidden panel and corridor. `@llm-canon` stall: cause was the stale fixed 1A script; `canon-journey.js` 1A/1B/2C/3A/3B prompts were repaired 2026-10-13/14 and their hermetic matcher tests pass, hosted `@llm-canon` rerun 2026-10-15 on staging `b6761c9e` (smoke passed; report `bench/results/stage2-llm-canon/canon-report.md`, Ringer `stage2-llm-canon`): both attempts ABORTED, so no judge result is recorded. The 1A stall did not recur (both passed 1A). Attempt 1 stopped in 1C (`committed nothing for 5 turns running`, 20 turns, 3 scenes); attempt 2 stopped in 2A (`Turn 26 is missing pacing event scrutiny_2a`, 25 turns, 4 scenes). Offline check: with the real `_matches_all`, none of the four `1C` prompts in `canon-journey.js` matches any `k_sl_1c_*` reveal, so the 1C stall is the same stale-script cause as 1A (only 1A/1B/2C/3A/3B were repaired); `scrutiny_2a` requires `facility_perimeter_reached`, which the 2A prompts evidently do not establish. The old stall is therefore NOT resolved by the spine repairs. Repaired 2026-10-15: `1C`, `2A`, `2B` prompts now each match exactly one intended reveal in eligible order (`tests/test_{1c,2a,2b}_spine_prompts.py`). 3C left as is: its chain never establishes `captives_reaching_surface`, so prompts 4-5 (d_r1/d_r2) are ineligible; the scene ends on prompt exhaustion, not on those reveals. Two more script faults found and fixed by reruns: 1C prompt 4 named Rebecca before she is introduced (narrator echo, 409 `unavailable entity`; now `tests/test_spine_prompt_names.py` guards all nine scenes), and the fixed `MAX_CANON_TURNS = 45` ended runs after six scenes (now `canonTurnBudget(pacing)` = 134 from real handoffs). FIRST COUNTED hosted `@llm-canon` run 2026-10-15, staging `b6761c9e`, fourth attempt of the day (three earlier aborted, archived under `bench/results/stage2-llm-canon-aborted-*`; the first reused attempt counts): all nine scenes, 69 turns, no stall, judge Luna: 28 of 63, 0 of 9 scenes pass. Per check (of 9 scenes): protected_safe 6, exit_motivated 6, rewards_investigation 2, scene_local 6, progressive 2, canon_consistent 1, rich 5. protected_safe failed in 1B, 2A, 3B. Artifacts and report: `bench/results/stage2-llm-canon/` (gitignored). Limits: one run is a sample; this run's judge input did not carry `authored_delivery` markers (the spec builds its own turns), so the authored-text guidance was not exercised here; for scale, the 2026-10-12 recorded-journey judging averaged 35/63 canonical and 26/63 raw. Read: 1B, 2A and 3B `protected_safe` failures were judge errors on authored runtime text from committed reveals (freight-terminal route line, records-archive handoff, 'began the broadcast' delivery); the judge also found genuine invention there (hidden bench compartment; wheelchair, vehicle and keys; fake distress signal), which belongs under canon_consistent. Markers rerun (fifth hosted run, same day, same staging `b6761c9e`, commit `7240d611`; run 4 archived in `bench/results/stage2-llm-canon-run4-no-markers`): 9 scenes, 69 turns, `bundles_seen` 69, `authored_delivery_turns` 26, 28/63 again; protected_safe 8 of 9 (was 6; 1B and 2A now pass; 3B still fails), exit_motivated 3 (was 6), rewards 6, scene_local 5, progressive 1, canon_consistent 2, rich 3. Total unchanged and per-check swings of 3 are within the run-to-run noise the runbook warns about, so the exit_motivated drop is unexplained, not a regression claim. GAP found: the 3B departure turn ('began the broadcast', a committed `k_sl_3b_c_r1` delivery) carried no marker. Offline over the saved canonical bundles, 23 of 91 committed reveals whose knowledge entry has `delivery_text` and 22 earned-transition turns get no marker, because `delivery_fact_ids` is empty for them. SUPERSEDED 2026-10-15 by the external review `.plans/astra-canon-markers-answer.md` (D6 rejected: a committed reveal licenses particular content, not every sentence on the turn; D5 corrected: 'began the broadcast' is the `t_3b_3c` `bridge_text` in plot.md, not a reveal delivery). Implemented instead (commits `04276035`, `a914909a`, `e48d9952`, and the fallback-eligibility commit): `frontend/e2e/authored-spans.js` attributes literal authored sentences (delivery, cue, handoff fallback when its fact was committed that turn, bridge, entry, route fallback) per committed turn and leaves everything else narrator; judge turns carry `authored_spans` and temporal `knowledge_available` (whole-turn markers removed); the judge prompt uses the reviewed wording; the hosted canon test reads reveals from committed bundles and saves segments, bundle summaries, `story_complete_seen`, `authored_span_turns`, `bundles_seen`, `reveal_evidence_fallback_turns`; `frontend/e2e/attribution-audit.js` audits saved journeys (239 turns: 0 reconstruction failures, 0 forced/timer/ending turns without an authored span). Not done, awaiting a billed go-ahead: the 30-call sentence-isolation rejudge (the exit_motivated question), and the 162-call paired pilot with blind labels; blind labelling of disputed and held-out turns is also not done. Neither the 28/63 results nor the 6-to-8 protected_safe change should be read as evidence about the judge until that pilot exists. SENTENCE ISOLATION RUN (2026-10-15, 30 billed Luna calls + 1 smoke; Ringer `stage2-sentence-isolation`; files in `~/dev/ringer-work/stage2-isolation/`): run-5 inputs frozen, only the `Still judge authored_delivery for exit_motivated ...` sentence varied (diff proof: exactly one line), 5 scenes x 2 arms x 3 repeats interleaved. exit_motivated true: with sentence 4/15, without 4/15 (1A 0/0, 1C 2/1, 2A 1/2, 3A 0/1, 3B 1/0); other checks within a few points (protected_safe 12 vs 11, rewards 11 vs 9, scene_local 9 vs 8, canon_consistent 5 vs 3, rich 6 vs 7, progressive 0 vs 0). Conclusion: not distinguishable; the sentence does not explain the run 4 to run 5 exit_motivated drop. The more important finding is judge-only noise: on byte-identical input, exit_motivated flipped between repeats in 1C, 2A, 3A and 3B, and 3A (true in run 5) was true in only 1 of 6 reruns, so a single run's per-scene verdict is not a stable measurement. `progressive` was 0/30 on this input. Orchestrator note: the operator's secondary-check table was wrong for 5 of 6 checks and was corrected from results.json; recompute worker-reported numbers from raw rows. PROMPT SIMPLIFICATION CHECK (2026-10-15, 30 billed Luna calls; Ringer `stage2-prompt-compare`; `~/dev/ringer-work/stage2-prompt-compare/`; manifest `scripts/ringer/stage2/prompt-compare.json`): same frozen run-5 inputs, system prompt old (550-word paragraph) vs a 247-word rewrite with one rule per check (`simple-prompt.txt`; offline probe proves only the system prompt differs), 5 scenes x 2 x 3 interleaved. True counts of 15 old/new: exit_motivated 2/7, protected_safe 9/8, rewards 8/15, scene_local 5/11, progressive 0/3, canon_consistent 3/11, rich 6/15; scene-checks with mixed repeats (of 35): old 13, new 7; verdict pass 0/3. The simple prompt is steadier on most checks but also far more lenient (rewards and rich at 15/15 ceiling, canon_consistent 3 to 11), and canon_consistent flipped MORE (3 of 5 scenes vs 0). No labels exist, so this does not show the new prompt is more accurate; it only shows prompt wording moves verdicts a lot. Not adopted. Needs blind labels before any prompt change is judged. DECISION 2026-10-15 (Brandon): judge calibration is DROPPED. Blind labelling of saved Continuity Initiative turns, the 162-call paired pilot and further judge-prompt rewriting would overfit an LLM judge to one story, and general labelling criteria for several stories are not being written. Kept: the judge-input fixes (span labels, bundle-based reveal evidence), which correct a demonstrated fault independent of any story. The `@llm-canon` scores (per-scene verdicts, 28/63) are a coarse smoke signal only and must not be used to compare arms; rely on deterministic checks (attempt-bundle reports, structural evidence, attribution audit). Next: Stage 3.
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

- [x] Repeat hosted `@spine` on a stable, identified staged build. Choose and
  record the replicate count and stopping rule first; include failed attempts
  in the denominator. Report infrastructure failure rate separately from
  gameplay failures and recovery/fallback rates.
  Done 2026-10-15, see Stage 3 status below.
- [x] Preserve assertions that the intended reveal chains commit, including
  2C C-R2, and that the story actually completes. Reaching 3C alone is not
  the ending. A transition at `min_turns` need not commit another reveal.
  Done (commits `d22cb1da`, `a2f985f8`): `@spine` records attempt bundles, asserts
  story completion, 2C C-R2 and the intended chains (`spine-expected-reveals.json`,
  drift-guarded by `tests/test_spine_expected_reveals.py`) after writing its report.
- [x] Verify the merged player-facing engine-error line on staging (partly: see Stage 3 status): rejected
  turns do not expose protected terms, state remains unchanged, and provider
  outages retain their separate error contract.
- [x] Fold the remaining linked 1A-to-1B phone-alias smoke into this work only
  with a script that actually elicits the relevant ordinary photo words.
  The existing 0-versus-0 probe did not exercise the defect; do not repeat it
  unchanged or claim it measured an improvement.
  Done 2026-10-16, see Item 4 below.

Exit: a current baseline table with artifact links, attempted/completed runs,
reveals, exits, ending, failures, requests, latency, and evidence limitations.

Stage 3 status (2026-10-15): items 1-2 done, item 3 done for the hosted rejection (fixed line and outage contract still local-only), item 4 done. Staging
`b6761c9e` (runtime `scene-v1`, channel staging) for every attempt; code under
test `d22cb1da`/`a2f985f8` on `astra-step-d`. Ringer `stage3-spine-baseline`
(harness) and `stage3-hosted-spine` (attempts); artifacts in gitignored
`bench/results/stage3-spine-series-a/` and `bench/results/stage3-spine/`.
Stopping rule fixed before running: exactly 3 attempts per series, failures
counted, no replacements, stop on quota stop or staging sha change.

| Series | Attempt | Turns | Reached | Story complete | Result | Median / total latency |
|---|---|---|---|---|---|---|
| A (3C cap 11 turns, harness bug) | 1, 2, 3 | 75 each | 3C | no | identical commits in all three; ending needs 3C scene turns 13-14, so cap was too small | 3.1 / 258 s, 2.9 / 257 s, 2.8 / 249 s |
| B (3C cap 24) | 1 | 78 | 3C | yes | ending reached; chain assertion failed | 3.2 / 283 s |
| B | 2 | 30 | 2A | no | gameplay failure, HTTP 409 `narration mentions unavailable knowledge 'front gate'` at turn 30 | 2.8 / 92 s |
| B | 3 | 78 | 3C | yes | ending reached; chain assertion failed | 3.2 / 290 s |

Series B: 3 attempted, 2 completed the story, 0 infrastructure failures, 1
gameplay failure (a rejected turn). Delivery: 0 must_convey misses, 0 fallback,
0 guard retries in all attempts; recovery 2 turns in B1, 0 elsewhere. 2C C-R2
committed in both full runs. Exits in a full run: 8 earned handoffs, 67 turns
with none. Both full runs miss the same six intended reveals, which also
missed in all of series A: `k_sl_1a_b_r2`, `k_sl_1a_d_r1`, `k_sl_1b_a_r1`,
`k_sl_1c_c_r2`, `k_sl_2b_a_r2`, `k_sl_2c_a_r1`. Each of these was the
action of a scripted prompt that matches offline (`_matches_all`), yet the
runtime committed no reveal that turn. NOT diagnosed: some may be one-reveal-
per-turn displacement (1A prompt 3 matches both b_r1 and b_r2) rather than a
defect, so the assertion is currently over-strict for those; others (1B a_r1,
2B a_r2, 2C a_r1 have no `requires`) look like real misses. Carried to
Stage 5, not fixed. Limits: three attempts are a smoke sample, not a
reliability rate; scripted prompts are not unscripted play; narration requests,
tokens and cost are not recorded (no source exposes them to the test); the
`stage3-hosted-spine` Ringer verdicts read FAIL only because `expect_files`
resolves against the Ringer workdir, while every check passed.

Item 3 (ran 2026-10-15, run by Brandon at the terminal; staging sha `b6761c9e`,
verified back on live narration afterwards): `scripts/knowledge_timeline_probe.sh`
switched staging to scripted narration and the `@knowledge-timeline` test FAILED
at its third turn, before reaching its designed future-lead rejection. The probe
script is stale: `deployment/knowledge-timeline-script.json` turn 3 selects
`k_sl_1a_b_r2` for 'Search the drawer for Michelle's research and a damaged
recording', but b_r2 now requires `memory_card_recovered` (earned by the
`k_sl_1a_b_r0` drawer search first), so the runtime rejected it. Evidence from the
page snapshot only (`frontend/test-results/`, gitignored): the player-visible line
for that rejected turn was 'selected knowledge is not eligible for this turn' with
no knowledge id or protected term; the turn input was echoed. NOT verified: the
HTTP status and `X-Freytag-Rejection-Code` header (the snapshot does not show
them), that state was unchanged, the fixed engine-error line for an unexpected
engine error, and the provider-outage contract. REPAIRED 2026-10-15 (Ringer `stage3-timeline-repair`, commits after `59c46fb2`):
the script and test follow the current 1A chain (drawer turn selects
`k_sl_1a_b_r0`); `tests/test_knowledge_timeline_script.py` replays the eligible
prefix through the real engine and proves the deliberate `k_future_invalid`
selection is rejected `ineligible_selection` with turn index, facts and scene
unchanged (state-unchanged is proven locally, not hosted, because a rejected
turn restores the scripted index so a hosted follow-up cannot work). The hosted
test records status, rejection code, visible line and `diagnostic_detail_exposed`.
FINDING: staging runs with `FREYTAG_EXPOSE_PROMPT=1`, so a hosted 409 shows the
raw reason ('selected knowledge is not eligible for this turn'), not the fixed
line; the fixed line `I don't understand. Can you try something else?` is
verified only by `tests/test_engine_error_line.py` (local). Hosted verification
of the fixed line would need that flag unset on staging, which is not done.
RERUN PASSED 2026-10-15 22:12 on staging `e3f66225` (PR 645 merge plus dependabot
bumps; run by Brandon at the terminal): `@knowledge-timeline` passed. Report
`artifacts/e2e-knowledge-timeline.json` (gitignored): 5 committed turns, drawer
turn selected `k_sl_1a_b_r0` (resolved `SL-1A-E/SL-1A-E-R1`); the future-lead
turn was rejected HTTP 409 with `X-Freytag-Rejection-Code: ineligible_selection`
after committed turn_index 5; visible line 'selected knowledge is not eligible for
this turn' (no id or protected term; `diagnostic_detail_exposed` true because
staging sets `FREYTAG_EXPOSE_PROMPT=1`). Verified hosted: status, code, visible
line leak-free. Verified only locally: state unchanged after rejection
(`tests/test_knowledge_timeline_script.py`) and the fixed engine-error line
(`tests/test_engine_error_line.py`). NOT verified anywhere hosted: the fixed line
itself, an unexpected-engine-error 500, the provider-outage contract. Revert note:
the probe printed 'staging did not show a live opening after the revert'; the
first of three sessions opened minutes later still showed the scripted opening,
the next two were live, so the revert lagged its 60 s wait and then completed.

Item 4 (done 2026-10-16): the old probe asked only 'Examine Michelle's phone.',
which never made the narrator write a photo word (0 of 24). New prompts ask about
photos on the phone, so the word appears: 'Look through the photos on Michelle's
phone.', 'Search Michelle's phone for her last picture.', 'Check Michelle's phone
for a recent photograph.' Local narration bench (Ringer `stage3-photo-alias`,
smoke n=2 then n=12 per cell; `bench/variations/stage3-photo-{baseline,current}.json`,
artifacts `~/dev/ringer-work/stage3-photo-alias/`): global-alias baseline rejected
6 of 36 turns, every one 'narration mentions an unavailable entity photo/photograph'
(`narration_known_term_leak`: picture prompt 3/12, photograph prompt 3/12, photos
prompt 0/12); the shipped scoped aliases rejected 0 of 36 (exact one-sided
p = 0.012, single package pair, one story). The narrator wrote a photo word in
33 of 36 current-arm and 21 of 30 narrated baseline turns. Hosted linked smoke
(`@alias-smoke`, Ringer `stage3-alias-smoke`, staging `e3f66225`, exactly 3
attempts, stopping rule fixed first): 3 of 3 passed; in each, both 1A photo
prompts were accepted and the narration used a photo word, 1A reached 1B, and
'Examine the photograph beneath the bench.' and 'Show Michelle's photograph to
the man and ask who he is.' committed `k_sl_1b_a_r2` and `k_sl_1b_b_r1` with 0
rejections (10 turns each, bundles visible). Limits: the hosted run has no
global-alias arm (staging cannot run the old package), so it shows the shipped
fix works end to end and does not regress 1B, while the improvement estimate
comes from the local bench alone; the photograph prompt contains the photo word
itself, so this tests ordinary photo words, not an unprompted narrator; three
hosted runs are a smoke sample.

## 4. Resolve references from accepted context

Sources: assessment C2 / Astra Phase 4.3;
scene affordances (`scene-affordance-e2e.md`, historical), “resolve a bare noun” decision.

- [x] Reproduce the recent-cue follow-up miss with a narrow engine test. Add a
  bounded projection of the last accepted authored cue's referents, entity
  links and source spans to reference matching. Do not add transcript memory
  or a permanent alias for an incidental cue phrase. Rejected turns must not
  update the record; test expiration, scene changes, ambiguity and save/load.
  Done 2026-10-16 on `stage4-references` (not merged; Ringer `stage4-references`,
  manifests in `scripts/ringer/stage4/`; commits `bd6b3bce` reproduction,
  `8e1d40eb` projection, `dfcf21ae` scene-check fix). Reproduced: after
  'Open the drawer.' commits the gap pointer `k_sl_1a_f_r1`, 'Search the gap.'
  (also 'Feel along the gap.', 'Check the gap.') earned nothing with semantic
  matching on or off, because `k_sl_1a_b_r0` needs a drawer word. Fix:
  `storygame/runtime/recent_cue.py::recent_cue_referent_text` derives one owner
  name from the LAST accepted `TurnRecord` (no new state, nothing persisted,
  rejected turns write no record) and `CloudflareTurnProvider._evidence_input`
  appends it to the text seen by the exact/shadow evidence matchers only; the
  narrator prompt, negation check and semantic matcher keep the original input.
  Rules: one accepted turn of life, current scene only (turn_index versus
  scene_entered_at_turn and no transition record), exactly one non-protagonist
  owner, a shared non-verb content word with the cue's delivery text, owner not
  already named; it never grants a reveal alone. Review caught that the first
  version parsed `TurnRecord.id`, which stays `turn_25` after 24 accepted turns
  and would have disabled the cue in every late scene; fixed and covered by a
  saturation test that fails on the old code. Verification: full suite 1848
  passed, new tests `tests/test_recent_cue_reference.py` (reproduction no longer
  xfail) and `tests/test_recent_cue_unit.py`. Limits: offline only, one story
  and one cue (1A gap); not measured on a hosted run; pronoun follow-ups ('it')
  are out of scope; the cue life of one turn is a choice, not a measured
  optimum; the repo's `ruff check .` still reports 47 findings in older
  `scripts/ringer/*` check scripts (not touched here).
- [x] Reconcile and implement the still-unbuilt scene-local bare-noun decision
  through the same resolution boundary, avoiding a competing matching path.
  Unique in-scope referents resolve; multiple referents produce the agreed
  fixed system question without narration, facts, or clock advancement.
  Lifecycle decision (Brandon, 2026-10-16): the pending question is
  client-held. The 2026-10-06 design (a `RuntimeState` field outside the
  snapshot) cannot work hosted because `POST /api/v1/turn` rebuilds state from
  SQLite on every request, and SQLite or an API-layer map would survive a
  reload, which confuses the player. The server stores nothing: the response
  carries the fixed line plus a `clarification` object, and the next request
  may carry `clarifies` (original command) and a round counter.
  Engine core done (2026-10-16): `storygame/runtime/reference_resolution.py`
  and `RuntimeEngine.turn(..., clarifies=None, clarification_round=0)`. Scope
  reuses `knowledge._entity_in_scene_scope`. Two or more scene things sharing a
  head noun return a `ClarificationTurn` before any provider call, state change
  or clock tick. A unique noun leaves the command exactly as typed (a first
  attempt rewrote it to a full name and broke 12 older tests such as "the
  Kristin's truck"; fixed). Tests: `tests/test_reference_resolution.py`,
  `tests/test_reference_clarification.py`. One older test changed:
  `test_deadline_protected_license` now reads "the archive terminals", since bare
  "terminal" in 2B is a real question. Full suite 1868 passed.
  API done (2026-10-16): `POST /api/v1/turn` accepts optional `clarifies` and
  `clarification_round` and returns a `clarification` object
  (original_command, noun, options, round) plus the fixed line; an ask turn
  does not save state, call the provider or advance the clock
  (`tests/test_web_demo_clarification.py`, suite 1874 passed). Frontend done:
  `frontend/src/clarification.js` holds the question in JS memory only (never
  storage), main.js sends `clarifies`/round; blind player records ask turns
  without counting them as story turns or rejections (139 node tests, vite build
  clean; Playwright specs not run, they need the hosted API). Limits: offline,
  not measured hosted.
- [x] Preserve the October 6 answer policy: splice a recognized answer into
  the original command; unrelated input cancels the pending question and runs
  normally; cap clarification rounds at two. Clear pending questions on scene
  change and reload. Pending interaction context is transient, not a world
  fact and not narrator knowledge. Verify the hosted request lifecycle can
  retain it between requests without making it durable save state.
  Done 2026-10-16: answer by full name, distinguishing word or ordinal; unrelated
  input drops the question; cap of two rounds forces a normal turn; a fresh
  session given only the answer runs it fresh (models a reload). The server
  stores nothing, so the lifecycle holds by construction; tested through the API
  with a fresh session, not on a hosted deployment.
- [x] Test full-name precedence, scoped aliases, collisions, wrong-target
  negatives, and no reveal granted solely by reference resolution. Make the
  browser and blind player handle the system question.
  Done 2026-10-16 in `tests/test_reference_resolution.py`,
  `tests/test_reference_clarification.py`, `tests/test_web_demo_clarification.py`.
  Not separately verified: a scoped-alias collision in a real scene (only 2B
  `terminal` and 1A-1C `seat` collide in the shipped story).
- [ ] Measure the targeted follow-ups and the previously identified 3B relay
  cases, including clarification burden and false resolutions, before moving
  to the next behavioral fix.
  Offline measurement done 2026-10-16 (`.plans/stage4-reference-sim-2026-10-16.md`,
  script `scripts/ringer/stage4/reference_sim.py`, 250 recorded commands from the
  2026-10-11 all-scenes run): 3 asked (1.2 per 100), all in 2B on "the next
  terminal" / "the maintenance reports terminal", where asking is correct; 36
  commands resolve to one thing and now pass through unchanged. The 3B relay
  gain from the 2026-10-06 sim is gone: those commands are no longer in the
  corpus and the engine no longer rewrites unique nouns. Hypothetical (not
  built): appending the resolved full name to the evidence input only would
  change 3 of 250 commands (2C "Copy the encrypted Project Echelon file" would
  earn `k_sl_2c_c_r1`, which is a reveal granted by reference alone and looks
  doubtful; 3A "Lead the captives through the emergency gate" x2 would earn
  `k_sl_3a_c_r1`). Too small a gain to build without Brandon's call. Hosted
  measurement not run (needs Brandon's go-ahead and a smoke test first).
  Evidence append BUILT 2026-10-16 on `stage4-references` (Brandon's call; Ringer
  `stage4-references` task `reference-evidence-append`, manifest
  `scripts/ringer/stage4/reference-evidence.json`): a uniquely resolved bare noun
  appends the thing's full name to the exact/shadow evidence input only
  (`resolved_reference_names`, `CloudflareTurnProvider._evidence_input`; recorded as
  `last_reveal_selection['reference_names']`). The narrator prompt, negation check
  and semantic matcher keep the original command; no persisted state. Full suite
  1880 passed, 1 skipped; ruff clean; `tests/test_reference_evidence_append.py`
  fails on the old code. Live-record check (saved hosted run `1c10272f`, 2026-10-11,
  no new spend): the offline sim ignores the semantic path. 2C 'Copy the encrypted
  Project Echelon file to my laptop.' already earned `k_sl_2c_c_r1` live through the
  semantic matcher (1 sample), so the 2C gain is redundant live and the earlier
  'reveal by reference alone' worry carries no live cost. 3A is the real gain: the
  semantic matcher missed 'Lead the captives through the emergency gate.' (turn 11,
  no reveal) and matched the retry 'Guide the captives through the open emergency
  gate.' (turn 12, `k_sl_3a_c_r1`), so the exact path saves a turn and a semantic
  call. Limits: one run, one story, two commands; offline only, not measured hosted;
  bare 'file' was never added to the 2C authored evidence and no recorded reason was
  found either way.
  HOSTED CHECK 2026-10-16, staging `3c2f9ad3` (runtime `scene-v1`, verified before each
  run; tests `@reference-copy` and `@reference-gate` in `frontend/e2e/reference-copy.spec.js`,
  Ringer `stage4-hosted-2c-copy`; reports `artifacts/e2e-reference-copy.json` and
  `artifacts/e2e-reference-gate.json`, gitignored). 2C: after a 38-turn spine walk,
  'Copy the encrypted Project Echelon file to my laptop.' committed `k_sl_2c_c_r1` with
  `semantic_match.ran` false (exact path; no semantic call). 3A: after a 49-turn walk
  including the first three 3A spine prompts, 'Lead the captives through the emergency
  gate.' committed `k_sl_3a_c_r1`, `ran` false (exact path), not rejected. 'Project
  Echelon' is not a story term (absent from the package); it is the blind player's
  invention. Limits: one run per command, one story; 'Guide the captives through the
  open emergency gate.' was not run; the `reached_2c` field name in the 3A report is
  inherited from the 2C summary.

Exit: bounded references improve the reproduced cases without false grants,
leaks, duplicate entities, or advancing a turn to ask a question.

## 5. Reproduce remaining correctness gaps, then fix individually

Sources: assessment C3, Astra Phase 4, playthrough quality, world model,
scene-affordance open cases and raw-language corpus.

- [x] Reproduce concealment after discovery and a subsequent NPC encounter.
  If the discovery-hidden state is being reused for concealment, separate
  possession, observer knowledge and concealment through validated facts.
  If no confusion is reproduced, close the implementation item with evidence.
  Closed 2026-10-16 as NOT REPRODUCED at the state layer (Ringer `stage5-repro`,
  `tests/test_concealment_repro.py`, 5 tests; note `~/dev/ringer-work/stage5-notes/concealment-repro.md`).
  `wk_hidden` is worldkeeper's one-way discovery flag: seeded from `hidden: true`
  (`model.py:353`), cleared by `World.reveal()` (`:854-860`), and nothing re-sets it; moves
  of a hidden thing and narrated `item_facts` for one are refused (`model.py:664`,
  `item_facts.py:1552`). After the 1A discovery the card is `wk_parent` kristin,
  `carried_by`, visible. A narrated hide ('under the passenger seat', 'in the glovebox') is
  an ordinary validated place move, never `wk_hidden`; no concealed/pocket axis exists.
  The 1B narrator request after discovery has no THINGS line for the carried card and
  Brandon's speaker context is `sayable_knowledge: []`, so nothing treats a carried card
  as seen by the NPC. Possession (`wk_parent`/`wk_relation`), observer knowledge
  (knowledge entries) and discovery (`wk_hidden`) are separate facts; there is no
  concealment fact, so an item carried but not shown is concealed only by omission from
  the prompt. NOT checked: whether a live narrator describes an NPC seeing a pocketed
  card (needs a billed probe; not run).
- [ ] Check the raw-language corpus's documented false grants, pronoun misses,
  correction/compound-action and unrelated-restraint cases against current
  runtime behavior. Use author-reviewed evidence changes for proven authoring
  misses; preserve ties and negation safety. Do not widen matching solely to
  turn corpus entries green.
  Corpus check done 2026-10-16 on `stage5-raw-language` (Ringer `stage5-negation-scope`,
  manifests in `scripts/ringer/stage5/`): 31 entries, 6 gaps, all reproduced on the
  exact matcher and, for restraint, live (the same negation set blocked the semantic
  path at four `cloudflare.py` sites). Fixed: (1) three unrelated-restraint gaps
  (`Open the drawer, but do not take anything yet.`) via `negation_scoped_command` in
  `candidate_matcher.py`, shared by the exact matcher and the four semantic checks. A
  negated trailing clause is dropped only when the leading clause has no negation, the
  restraint clause adds content words and shares none with the kept clauses, and it holds
  no retraction word; everything else stays blocked as before. Review caught a regression
  the first patch introduced ('Open the drawer, never mind.', 'no wait', 'no stop',
  'don't bother' would have granted); fixed with `_RETRACTION_WORDS` and covered by tests.
  'nevermind' as one word now also blocks, which is stricter than before. (2) `2c-near-
  miss-2` was a mislabel (the command is `k_sl_2c_b_r2`'s own act) and is now canonical.
  Still honest gaps: `2a-near-miss-1` (a hideout search for a weapon earns the hideout
  reveal; label judgment pending) and `2c-pronoun` (pronoun-only object; out of scope).
  Suite 1921 passed, 1 skipped. Limits: offline only; clause splitting is a small
  heuristic, not a parser; not measured hosted.
  HOSTED CHECK FAILED then fixed 2026-10-16: on staging `42e3a424` the 1A test
  `@negation-scope` (`frontend/e2e/negation-scope.spec.js`) showed the two blocked
  commands blocked but 'Open the drawer, but do not take anything yet.' earned nothing.
  Cause: the engine's spaCy `split_command` ran first and cut it into 'Open the drawer,
  but do not.' and 'Take anything yet.' (the restraint became a positive command; a
  defect that predates this stage). The corpus tests call the matcher directly and the
  first engine test used a semicolon, so neither saw it; the corpus therefore overstated
  engine behavior for the comma-and-but form. Fix (Ringer `split-negation`): the splitter
  no longer splits at a negated coordinated verb; engine-level tests use the comma form.
  Differential over 916 recorded and corpus inputs: only the 3 restraint commands changed,
  plus 'Open the drawer, take the key, then search the room.' now splits in three pieces
  instead of two (an incidental `then` fix). Engine-path note
  `~/dev/ringer-work/stage5-notes/corpus-engine-path.md`: all 31 corpus entries agree with
  their recorded result after the fix. Suite 1938 passed, 1 skipped. Hosted recheck PASSED 2026-10-16 on
  staging `95490ef7` (PRs 654 and 655, `scene-v1`, verified before the run;
  `artifacts/e2e-negation-scope.json`, gitignored): in one fresh 1A session 'Do not open
  the drawer.' and 'Open the drawer, never mind.' earned nothing, and 'Open the drawer, but
  do not take anything yet.' committed `k_sl_1a_f_r1` on the exact path (`semantic_match.ran`
  false). Limits: one run, one scene, three commands; the 2A and 2C restraint commands were
  not run hosted; `2a-near-miss-1` (label judgment) and `2c-pronoun` remain open gaps.
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
  1A-avoiding-the-drawer part done 2026-10-16 (NOT REPRODUCED; `tests/test_drawer_avoidance_repro.py`,
  2 tests; note `~/dev/ringer-work/stage5-notes/drawer-avoidance-repro.md`): eight 1A reveals
  and eight facts depend only on the drawer path; no later-scene reveal, storylet, handoff or
  route depends on them. Scripted non-drawer play ('Look around.', 'Examine Michelle's
  phone.', 'Search the truck.', 'Walk around the building.') leaves 1A on turn 13, 1B on turn
  13 and 1C on turn 11, all forced, with the forced delivery asserting `memory_card_recovered`
  and the world holding the card as `carried_by` Kristin, so text and facts agree; the same
  script reaches 3C through forced handoffs from every scene. Limits: scripted provider, so
  live narrator wording is unchecked; the replay shows reachability by forced exits, not
  earned play.
  2C paths, 3A medical records, place vocabulary and custody replayed 2026-10-17 (offline,
  scripted provider; Ringer `stage5-2c-replays`, manifest `scripts/ringer/stage5/2c-replays.json`;
  tests `tests/test_2c_paths_repro.py`, `tests/test_late_scene_repro.py`; notes
  `~/dev/ringer-work/stage5-notes/{2c-paths,late-scene}-repro.md`; 35 passed after the vocabulary xfails became characterizations; no xfail remains).
  Michelle-first: coherent. D-R1/D-R2 are rejected `prerequisite_missing` until the copy, then
  2C exits earned. Skipped-copy: NOT A DEFECT (the earlier REPRODUCED call was wrong; diagnosed 2026-10-17). 2C entry already places
  `copied_janus_files` with Kristin ('She could check them now', plot.md 2C item_placements) and
  `janus_evidence` comes from 2B, so `k_sl_2c_c_r1` acknowledges files she carries rather than copying
  them. With no such command the forced turn-16 handoff asserts `evidence_ready_to_transmit` and
  delivers 'obtain enough evidence...', which matches the world; the xfail premise (nothing copied)
  was false and it is now a characterization test. No fix designed or needed. Cosmetic only: the
  cue/fallback wording says 'obtain' where 'have' would be exact. 3A medical records:
  declared with scoped aliases, placed in `medical_level` by `k_sl_3a_b_r1`; the exact entity name
  is rejected before placement; no collision with the 2B medical terminal (ambiguity prompt is
  correct). Custody 2A to 3C stays consistent with authored text. The three vocabulary xfails were diagnosed by hand
  2026-10-17 and are NOT engine defects; they are now characterization tests. (1) Singular
  'infrastructure corridor' is the guarded alias of reveal `k_sl_2a_c_r2` (entering the corridor
  is what the player earns), so rejecting it unearned is the guard working; the place name, the
  plural 'infrastructure corridors', is accepted in 2A and 3B. (2) 'broadcast chamber' is nameable
  in 2C because the whole regional-facility subtree is nameable (`narration_safety.py`); a design
  choice, with no recorded drift from it. (3) 3C `captives` sit in `maintenance_network`, under
  the command levels, outside the 3C scene area and Kristin's, so they are out of reference scope;
  the command passes through unchanged and no reveal depends on it. Reopen any of the three only
  if live play shows drift or a rejected ordinary command. Limits: scripted provider, so live narrator wording is
  unchecked.
  DISCLOSURE REVIEW 2026-10-17 (read-only; `scripts/disclosure_matrix.py` rerun on current code gives a
  byte-identical matrix to `.plans/disclosure-matrix.md`, and a per-scene probe of the decision-table terms):
  the 8 'early reveals' and the never-released secrets (JANUS, Phase Two, purge clock, memory card) all behave
  as decided. Three terms the decisions call PUBLIC are still rejected in their own scene with an unearned
  state: bare `card` in 1A (leak_term and must_convey on the memory-card reveals; `22f818ad` kept it guarded
  on 2026-10-12, a day after the decision, so this may be deliberate), `park bench` in 1A (must_convey), and
  singular `infrastructure corridor` in 2A and 3B (alias of `k_sl_2a_c_r2`; the plural place name passes).
  This corrects the earlier 'by design' reading of the corridor, which ignored the decision table. Also
  rejected everywhere with no decision on record: `front gate` (the series B 409 at turn 30). Recorded older
  rejections of `park bench` (6) and `front gate` (4) show it bites in play. NOT done: any guard change; each
  needs Brandon's ruling (card: public or guarded after 22f818ad?), then an author-reviewed alias edit, not a
  validator change. Remaining open: narration-quality reassessment, pointer placement, unknown identity.
- [x] Split the player-facing refusal line (Brandon, 2026-10-17; Ringer `stage5-refusal-lines`, branch
  `stage5-refusal-lines`): a narration-guard rejection whose term the player typed says 'I don't see the
  item you're referring to.'; a guard rejection of a term only the narrator used (after the existing single
  guard retry) says 'Nothing comes of that. Try something else.'; every other failure keeps 'I don't
  understand. Can you try something else?'. `rejection_message` in `storygame/runtime/validation.py`, used
  by the 409 branch of `web_demo.py`; suite 1955 passed, 1 skipped. Limits: offline; the typed-term test
  duplicates the engine's regex instead of sharing it; hosted e2e specs that quote the old line were not
  run; guard vocabulary for `card`, `park bench`, `infrastructure corridor` and `front gate` is a separate
  open ruling (Brandon's rule: a visible item may be referred to, so declare the 1A house gate as a
  1A-scoped thing).
- [ ] Follow-ups to the refusal-line split (recorded 2026-10-17, not started). (1) Hosted e2e:
  `frontend/e2e/scene-runtime.spec.js:475` computes `diagnosticDetailExposed` as 'visible line is not the
  generic line', which stops meaning 'rejection' now that a guard rejection shows a different line; update
  it (and review `knowledge-timeline-record.test.js:59`) before the next hosted run. (2) Guard vocabulary,
  by Brandon's rule 'if an item is visible in the scene it can be referred to': `front gate` belongs to
  1A (the patrol's reflective tape, plot.md 156-160, `k_sl_1a_f_r2`) but is only a reveal phrase, not a
  declared thing, so the guard also rejects the facility gate in 2A (series B 409, turn 30). Declare the
  house gate as a 1A-placed thing with `front gate` as a scoped alias (grounding guide: Things, Names), then
  give the 2A facility gate its own name. Apply the same approach to `park bench` (1A, must_convey) and
  singular `infrastructure corridor` (2A/3B, alias of `k_sl_2a_c_r2`); bare `card` in 1A needs Brandon's
  ruling first (decision table says public, `22f818ad` re-guarded it). Story wording goes through the
  ChatGPT Desktop round; run a package-payload capture diff after any package change.
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
