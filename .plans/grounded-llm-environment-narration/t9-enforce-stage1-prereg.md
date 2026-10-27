# T9 stage 1: first enforced run: preregistration (written 2026-10-27, before any billed call)

Status: written for Brandon's approval of the numbers and gates, then his go on the smoke and the full run. Nothing is built for it yet except the switch (T9a, PR #713). No billed call has been made. This is a screen of the enforcement mechanism on one route; it is NOT the T9 confirmation (12 withheld start states, 300 turns), which needs fixtures that do not exist yet. Its rates are never pooled with any shadow sample.

**Why.** The shadow verifier passed its gate under the corrected order (re-run result in the plan: 0 false accepts in 158 relations, 2b exactly 10.0%). Enforcement itself has never run live: its preview, its one shared recovery and its exact rollback are proven only with stubs. The 8 rejections of the re-run were the 70B omitting the drawer's contents on identical prompts; under enforcement each becomes a retry. This run measures what that costs and whether recovery works.

**Question.** With the enforcing verifier ON, on the `observe_topup` route: (1) how often is a first narration rejected, (2) how often does the one recovery fix it, (3) does a turn that fails restore the world exactly, (4) is the committed prose actually right, (5) what do latency and cost become?

**Code.** The run's SHA is the merge commit on main that contains PR #713 plus this stage's harness, recorded per row. Staging deployed and recorded for that SHA before any billed run, and no merge to main while a run is in progress. The hosted environment is NOT changed: the run uses the local-Worker bench with `--enforce`; `FREYTAG_OBSERVATION_ENFORCE` is not set anywhere hosted.

**What runs.** Real engine, product wiring, observation mode on, `enforcing_verifier` on (`live_baseline.py --enforce`), `shadow_verifier` off, local Worker on 127.0.0.1 with a hard dollar cap (`local_worker.mjs --max-usd`), 70B JSON off, the 20 s timeout with no retry on a timeout. Verifier thresholds as shipped (accept above 0.65, reject below 0.35, at most 2 requests per turn).

**Route.** `observe_topup`, frozen, the same 9 imperative commands as the re-run, so the comparison isolates enforcement: `inspect the drawer`, `pull out the drawer`, `feel under the drawer`, `feel under the drawer`, `go outside`, `inspect the truck`, `enter the truck`, `pick up my laptop`, `inspect the passenger seat`. No scene transition. An unsuccessful turn rolls the world back; the route continues with the next command from the restored state and is reported as it is (later turns may differ from the shadow route).

**Counts and cost.** The re-run measured 500 calls and $0.0863 for 90 turns without enforcement; each rejection adds roughly one narration call, one item-facts match call and one verifier call.
- Smoke (billed, not counted in any rate): 1 replicate x 9 turns, `--max-calls 70`, `--max-usd 0.03`; expected about 50 calls and $0.009. It tests the plumbing only: rows carry `observation_enforce`, `narration_attempts`, `verifier_requests`; a turn with relations asks the verifier; the report builds a sheet from the rows. A smoke that never rejects is fine and proves nothing about recovery.
- Full: 10 replicates x 9 = 90 turns, `--max-calls 700`, `--max-usd 0.20`; expected about 540 calls and $0.10. No replacement samples, no reruns. Stop on any quota code, 429, 5xx or cap and keep the partial result. A turn that fails because enforcement exhausted its recovery is a RESULT, not a stop.
- Output to `bench/results/environment-narration/enforce-stage1/{smoke,full}`; the shadow directories are untouched.

**Procedure.** Free dry run, billed smoke, billed full (each one Ringer probe task whose check asserts a stop reason or the exact row count; the runner must be told to wait for the billed process, as in the earlier lesson). Then a blind sheet from the new report script: for each turn the reader sees the command, the committed narration (or "no narration: turn failed"), and for a turn that needed recovery also the rejected first attempt, in random order, with no verifier score, no verdict and no attempt number. I read every turn and write the labels below before any verdict is opened, freeze the labels hash, then run `join`. Every turn is reported, none dropped.

Labels, from the narration text only (rule from the re-run: a thing counts as presented only if the narration presents it):
- per committed narration: `presents_required` (every thing the engine required for that turn is presented at its permitted place, or mentioned when held), `acceptable` (nothing contradicts the committed world and the scene is not broken), and the tags `refind`, `invented_object`, `leak`, `wrong_custody`, `unrequested_move`;
- per rejected first attempt: `really_deficient` (it omitted a required thing or contradicted the world), so a rejection can be called correct or a false reject.

**Gate (set now, before any data).** Unsuccessful turn = a turn that ends with no committed narration after the recovery.
1. Observation turns that end unsuccessful: at most 1 of the observation turns (about 80); report the Wilson upper bound (the plan's 99% target is not provable at this n).
2. Committed narrations that fail `presents_required`: zero (a false accept at the turn level).
3. Committed narrations with a `leak`, `wrong_custody` or `unrequested_move` tag: zero. `refind` and `invented_object`: at most 1 each.
4. Rollback: for every unsuccessful turn the world after equals the world before (`places_after == places_before`), the row has the typed error and no narration, and the next turn runs normally. Zero violations.
5. Request budget: no turn uses more than 2 narration attempts or 2 verifier requests; zero violations.
6. Latency: end-to-end turn p95 of turns that needed no recovery at most 10 s (the plan's target); recovery turns reported separately with their own p50 and max.
7. False rejects: rejected first attempts labelled not `really_deficient` at most 1 of all rejected attempts, or if there are fewer than 5 rejected attempts this clause is inconclusive.
Printed for information, not gated: first-attempt rejection rate (expected about 10%, from 8 of 80), recovery success rate, cost per successful turn, narration calls per turn, clauses 7 and 8 of the shadow samples (re-find of the held card on `feel under the drawer`, invented object on the empty seat).

A pass does not deploy anything and does not turn the hosted switch on. It permits writing the T9 confirmation preregistration. Clause 2 failing is a stop: the verifier is letting deficient prose through.

**Expected, not measured:** about 8 first-attempt rejections of 80 on the drawer-contents omission, most fixed by the single retry (if retries were independent, about 1 turn in 80 still fails). If the retry reproduces the omission more often than that, the retry feedback or the prompt needs a fix before T9, and the report names the turns.

**Stated limits.** One story, one route, 70B only, one reader who knows the aim (arm labels do not exist here, but the reader knows what enforcement is for). Ten replicates share one starting state, so turns are correlated. About 80 observation turns bound a zero count only to about 4% (one-sided 95%). The 70B's omission rate moved between 0 and 30% at a fixed prompt across the earlier samples, so the rejection rate here can move the same way. This stage cannot show the 99% successful-turn target.

**Build (free, Ringer, tests first, after approval).** (1) `enforce_stage1.sh smoke|full` (port 8795, caps above, output under `enforce-stage1/`) and runner manifests derived from the re-run's by a generator that asserts every replacement. (2) `enforce_report.py` with `template`, `sheet` (blind, includes the rejected first attempt of a recovered turn, with no verdict) and `join` (clauses 1 to 7, plus the information lines), tested on the T9a smoke rows and on synthetic rows that include a failed turn, a recovered turn and a violation of each clause. The shadow report is untouched. (3) A test that the script and manifests carry only this stage's numbers and paths.
