# T9h latency: hedged short calls (preregistration)

Status: FROZEN before any billed call of this measurement (2026-10-30). Brandon, 2026-10-30: "You must address the
performance issues though; that is completely unusable as-is."

## Baseline (stage 3, recorded, unhedged)

18 turns, mean 9.8 s per turn, 8 of 18 over the 10 s target, slowest 32.3 s. By call kind: narration 50% of turn time
(21 calls, 2.2 to 9.0 s), the item-facts referent match 30% (18 calls; 14 answered in 0.5 to 1.6 s, 4 stalled 5.9, 7.6,
8.2 and 20.0 s), Jev classifiers 15% (71 calls, mean 0.38 s, one 7.6 s stall). Narration time did not track reply length
(the two slowest narration calls had the shortest replies), so the tails look like provider stalls.

## Change under test

`storygame/runtime/hedged_request.py`: one delayed duplicate request, first success wins, 2.5 s delay, applied to the
item-facts referent match and the Jev calls only. Narration is NOT hedged (one narration request per turn). Hedges are
one logical request: logical budgets and counters unchanged. `FREYTAG_HEDGE_DELAY_S=0` disables it.

## Measurement

Unchanged Route E (`observe_park_bench_1b`), enforcing verifier on, shadow off, no scene-state flag, **5 replicates x 6
turns = 30 turns**, same local Worker. Cap 240 HTTP calls and $0.07 behind `local_worker.mjs --max-usd 0.07` (the
baseline spent $0.022 for 3 replicates; hedged duplicates add a little). Billed once; never rerun after a partial
result; stop on 429, 401/403, 5xx or the cap. Fresh directory `bench/results/environment-narration/t9h-latency/hedge-short`.

Reported, with no pass gate: per-turn elapsed (mean, median, 90th percentile, maximum, turns over 10 s), the share of
turn time by call kind, how many hedges fired and which attempt won, and spend. The smoke reporter's S1 to S6 must still
all PASS (hedging must not change behaviour). Latency from one provider on one day is noisy: 30 turns compare a
change against 18 baseline turns, they do not prove a rate. Provider load can differ between runs; a clear improvement
in the stalls (worker and Jev calls over 5 s) matters more than the mean.

Reproduce the statistics with the command recorded in the plan section for this run.

## Run 2: all latency changes on (registered 2026-10-30, before any billed call of this run)

Result of run 1 (hedged short calls only, 30 turns, `hedge-short`): mean 9.5 s, median 7.8 s, p90 14.9 s, max 23.2 s,
10 of 30 turns over 10 s; narration 67% of turn time (mean 5.6 s). One find turn failed outright when narration timed
out at 22 s ("narration service is unavailable"; state rolled back, S5 PASS), which is why S1 and S3 failed in that run.
The reporter also printed "replicates incomplete 5/3" because it hardcodes 3 replicates; that is a reporter limit.

Brandon approved narration hedging ("ok", 2026-10-30). Changes now on, all env-flag separable: (1) hedged short calls,
2.5 s (`FREYTAG_HEDGE_DELAY_S`), (2) Jev classifier batching and prefetch concurrent with the referent match
(`FREYTAG_JEV_BATCH=0` disables), (3) narration hedge, 4.5 s (`FREYTAG_HEDGE_NARRATION_S=0` disables); the contributor
guide now counts a narration hedge as the same one request. Free checks passed (stubbed route: 87 to 69 calls with
batching, S1 to S6 PASS).

Measurement: unchanged Route E, 5 replicates x 6 turns, enforcing verifier on, shadow off, no scene-state flag, cap 240
calls and $0.07 behind the Worker cap, billed once, no replacement samples, stop on 429, 401/403, 5xx or the cap.
Fresh directory `bench/results/environment-narration/t9h-latency/all-on`. Reported with no pass gate: turn mean,
median, p90, max, turns over 10 s, time by call kind, spend, and S1 to S6 (the reporter's "5/3" note is expected).
Compare against stage 3 (18 turns, mean 9.8 s) and run 1 (30 turns, mean 9.5 s). Provider load differs between runs, so
an ablation arm may follow if the result is unclear; this run cannot by itself attribute the gain to one change.

## Run 3: paired on/off after two harness and wiring defects (registered 2026-10-30, before any billed call of these runs)

Run 2 (all changes on) was not a valid test of the changes: (a) the narration hedge was inert in the real game, because
`CloudflareTurnProvider._request_allowing_one_transient_retry` skipped hedging for any subclass overriding `_request`
and the real provider, `ItemFactsProvider`, does (fixed: the hedge now wraps only the raw HTTP send inside the base
`_request`, tests use the real `ItemFactsProvider`); (b) the local Worker proxy (`local_worker.mjs`) queued every model
request behind the previous one, so only one request was ever in flight and a hedged duplicate or a concurrent Jev
prefetch could not overlap (fixed: the queue now applies only when a test supplies `fetchImpl`; spend-cap atomicity
under concurrency is tested). Runs 1 and 2 also ran while the machine was under heavy load, which Brandon reported.

Design: two runs, same day, one after the other, unchanged Route E, 5 replicates x 6 turns, enforcing verifier on,
shadow off, no scene-state flag, cap 240 calls and $0.07 each behind the Worker cap, billed once each, no replacement
samples, stop on 429, 401/403, 5xx or the cap. Arm ON: all three changes on (defaults). Arm OFF: `FREYTAG_JEV_BATCH=0`,
`FREYTAG_HEDGE_DELAY_S=0`, `FREYTAG_HEDGE_NARRATION_S=0` (the concurrent proxy stays in both). Directories
`bench/results/environment-narration/t9h-latency/on-2` and `.../off-2`. Machine load (`uptime`) is recorded before each
run. Reported with no pass gate: turn mean, median, p90, max, turns over 10 s, time by call kind, how many narration
and short-call hedges actually fired (extra HTTP requests recorded in `call_timings`), spend, and S1 to S6. The change
is judged only against the same-day OFF arm; earlier runs are context. Thirty turns per arm still do not prove a rate.
