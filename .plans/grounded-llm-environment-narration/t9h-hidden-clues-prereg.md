# T9h route E: hidden bench clues, billed stages (preregistration)

Status: FROZEN before any billed call of these stages (2026-10-30). Source plan:
`.plans/chatgpt-t9h-route-e-hidden-clues-plan.md`. Brandon's authorisation: "run the billed stages when ready"
(2026-10-30). All stages run behind `local_worker.mjs --max-usd`, a hard spend cap. Each stage is billed once;
never rerun after a partial result; no replacement samples. Stop on a quota, 429, 5xx or a cap. A failed
stage stops the chain; the next stage runs only on a clean pass of the one before it.

What changed since the plan (all free work is done and green before stage 1): the three clues are `hidden: true`
under `park_bench`; knowledge `k_sl_1b_d_r1` (storylet SL-1B-D) is the find and asserts `bench_clues_recovered`;
`k_sl_1b_a_r1`, `k_sl_1b_a_r2` and `k_sl_1b_b_r1` require it; and, by Brandon's instruction, a public,
repeatable, non-voiceable pointer `k_sl_1b_e_r1` (storylet SL-1B-E, fact `bench_underside_pointed_out`) says
"The bench is ordinary. The space beneath it is shadowed and deep enough for Kristin to reach under." when the
player looks at the bench without going underneath. It never names a clue. One deviation from the plan: D has no
self-prerequisite (the loader forbids it); its storylet's activation condition and spent source stop rediscovery.

## Stage 1: semantic earning boundary (matcher probe)

Replays the real `reaches_reveals` request (one Jev call per evaluation, shortlist capped at six) at a fresh,
unrecovered scene 1B checkpoint. Arms: P0 = the candidates the HEAD package offers; P1 = the working package.
Six inputs, 10 samples each, 2 arms = 120 evaluations = 120 HTTP calls (one per evaluation; the harness dry-run
must confirm this). Every sample gets a fresh provider (the fallback budget is 40 per provider). Ceiling: 120
calls, $0.02. Estimate under $0.01.

| id | input | P1 requirement |
| --- | --- | --- |
| u1 | `Look under the park bench.` | selects `k_sl_1b_d_r1` |
| u2 | `Feel beneath the park bench.` | selects `k_sl_1b_d_r1` |
| n1 | `Inspect the park bench.` | never selects `k_sl_1b_d_r1` |
| n2 | `Search the park bench.` | never selects `k_sl_1b_d_r1` |
| n3 | `Examine Michelle's photograph.` | selects nothing |
| n4 | `Inspect the storm drain.` | selects nothing |

Gates (P1 only; P0 is a diagnostic control and is not gated):
- **M1**: u1 and u2 each select D in at least 9 of 10 samples.
- **M2**: u1 and u2 each select the pointer `k_sl_1b_e_r1` in at most 1 of 10 samples.
- **M3**: n1 and n2 select D in 0 of 10 samples each (zero false finds).
- **M4**: n3 and n4 select nothing in 10 of 10 samples each.
- **M5**: no stop reason, and unusable answers at most 10% of evaluations.
Informational, not gated: how often n1 and n2 select the pointer (exact matching handles them in real play).
This qualifies earning wording only, not concealment or narration.

## Stage 2: prose (narration payloads)

Three frozen states at scene 1B built through the real engine with the network stubbed to capture the narrator
request: **opening** (no action), **pre-find** (after `Inspect the park bench.`), **find** (after
`Look under the park bench.`). Two arms: P0 = HEAD package payload, P1 = working package payload. 10 samples per
state per arm = 60 narration calls through the real narration request path. Ceiling: 60 calls plus no retries,
$0.06. Estimate about $0.042.

Free pre-flight (no calls; the harness aborts before spending if any fails): in every P1 payload for the opening
and pre-find states, none of `transit`, `token`, `number sequence`, `photograph`, `photo` appears in the
narrator material (THINGS, PLAYER, Details, NPC talk, appended cues); P1 find-state payload carries the authored
find text.

Labels are written by Claude from the narration text, blind to arm, with a frozen hash before the join.
Gates (P1):
- **P1a**: 0 of 20 opening and pre-find samples name a clue object, describe photograph content, state a route or
  identity, claim the space under the bench is empty or that nothing is there, or move the fixed bench.
- **P1b**: at least 9 of 10 find-state samples convey all three objects and Kristin keeping them, with no
  route, face or identity statement.
- **P1c**: no sample invents a fourth physical object under the bench.
Prose samples cannot replace full-turn validation (stage 3).

## Stage 3: Route E integration smoke (candidate only)

Unchanged route `observe_park_bench_1b`: `inspect the park bench`, `look under the park bench`,
`search the park bench`, `check the park bench`, `look under the park bench`, `inspect the storm drain`; 3
replicates, enforcing verifier on, no scene-state flag. New output directory
`bench/results/environment-narration/t9h-hidden/smoke`; the old S sample is not overwritten and this is not
"T9h F". Caps: 240 HTTP calls, $0.07 (expected $0.03 to $0.04). Latency target 10 s per turn is reported, not gated.

Gates:
- **S1**: in every replicate the `look under the park bench` turn commits, and after it `bench_clues_recovered`
  holds and all three clues are carried by Kristin and visible (checked from `world_after` and the state digest).
- **S2**: no clue name appears in the opening, in turn 0 (`inspect the park bench`) narration or its payload.
- **S3**: no second recovery: turns after the find leave custody unchanged and `bench_clues_recovered` is asserted
  exactly once per replicate.
- **S4**: none of `brandon_face_known`, `brandon_identified`, `transport_route_identified` is asserted by the
  find turn.
- **S5**: every ordinarily rejected turn restores the exact pre-turn state digest. A call-cap exception is
  reported separately and is not counted as an ordinary rejection.
- **S6**: per-turn request budgets unchanged. Drain (`inspect the storm drain`) rejections and latency are
  reported separately and are not part of the gates, because the drain-verifier defect is a separate known issue.

## After the stages

Record raw results in `.plans/grounded-llm-environment-narration.md`. A pass authorises nothing further: no
threshold waiver, no production switch, no deployment. A fail is recorded as measured; the plot is not tuned to
the sample.

## Stage 3 addendum: separate authorisation after the stage 2 FAIL (2026-10-30)

The chain rule above (a stage runs only after a clean pass of the one before) blocked stage 3 when stage 2 failed.
Brandon has now approved stage 3 explicitly: "i approve of stage 3 when you're ready" (2026-10-30). This is a
**separate diagnostic authorisation**: stage 2 stays recorded as FAIL, its labels and artifacts are unchanged, and a
stage 3 result neither repairs nor reinterprets it. Stage 3 is billed once; never rerun after a partial result; no
replacement samples; stop on 429, 401/403, 5xx or the call or spend cap.

What changed since the stage 3 section was frozen (all free, all Ringer-verified):
- The runner (`live_baseline.py`) now records `story_facts_after` on the opening and every turn row, rejected turns
  included, and per-turn `item_facts_requests` and `shared_recovery_requests` from existing counters.
- The reporter (`hidden_clues_smoke_report.py`) makes S6 a real gate (the run passes only if complete and S1 to S6 all
  PASS; missing evidence is `insufficient evidence`, never PASS). S1 needs the find turn committed, the recovery fact
  true in `story_facts_after`, and the three clues carried by Kristin and visible. S3 counts false-to-true transitions
  of the recovery fact (exactly one, at turn 1), forbids a repeat delivery and a custody change. S6 now also checks
  item-facts and shared-recovery requests (each at most 2 per turn, unchanged budget). S2 still scans all recorded
  prompts and responses because private selector traffic is not separable in these rows (the report says so).
- Free dry-run of the unchanged route with the stub provider: 3 replicates x 6 turns, 87 stubbed calls against the
  240-call ceiling (about a 2.7x margin), and the reporter evaluated S1 to S6 end to end.

Unchanged: route `observe_park_bench_1b`, 3 replicates, enforcing verifier on, shadow off, no scene-state flag, caps 240
calls and $0.07 behind `local_worker.mjs --max-usd 0.07` (expect $0.03 to $0.04; the probe's earlier estimates ran 8 to
10 times low, so the cap, not the estimate, is the guard), output directory
`bench/results/environment-narration/t9h-hidden/smoke`. Drain (`inspect the storm drain`) rejections and latency are
reported separately and are not gated. A pass authorises nothing further (no threshold waiver, production switch or
deployment) and certifies nothing about narrative secrecy or prose quality: S2 is a substring scan and a named Brandon
in prose can coexist with S4. A fail is recorded as measured; the plot is not tuned to the sample.
