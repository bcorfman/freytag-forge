# T9b: scope-aware observation contract: preregistration (written 2026-10-27, before any billed call)

Status: written for Brandon's approval of the numbers and gates, then his go on each stage (P, S, F below) separately. The contract is built (PR #716: kind `under`, typed Jev question `searches_underneath`, the opening duty line). Nothing below is built yet except that. No billed call has been made. This replaces the stage-1 full run, which stays on hold: its first gate would have measured the old requirement. `t9-enforce-stage1-prereg.md`, its smoke and its harness stay as the record of the first design; their numbers are never pooled with these.

**Why.** Enforcement's first live smoke failed a turn because the verifier required a drawer's supplies on an underside search (Brandon: only the card under the drawer matters). ChatGPT's diagnosis (`.plans/answer.md`, recorded in the plan) found a second gap: on a command that opens a closed container the verifier required the exposed contents but the narrator was never told. T9b fixes both. Two things are not yet measured: whether Jev classifies real phrasings correctly (stubs only), and what enforcement does end to end with the new contract.

**Question.** (P) Does Jev answer `searches_underneath` correctly? (S, F) With enforcement ON and the new contract, do the stage-1 gates pass, does the contract avoid being vacuous, and can the player still find the hidden card by an underside search?

**Code.** The run's SHA is the merge commit on main that contains PRs #715, #716 and the harness PR for this preregistration, recorded per row; staging deployed and recorded for that SHA before any billed run; no merge to main while a run is in progress. The hosted environment is NOT changed (`FREYTAG_OBSERVATION_ENFORCE` stays unset there).

## Stage P: Jev classification probe

Asks the real `searches_underneath(ask, command, thing)` through the product's Jev client on a frozen list, 2 samples each. No narration, no engine. Hand labels are fixed here, before any call. Player-input voice: imperative with a direct object (`docs/player-input-guide.md`).

Positives (20, answer must be true): Feel under the drawer. [drawer] / Search beneath the drawer. [drawer] / Look under the drawer. [drawer] / Check below the drawer. [drawer] / Run my hand under the drawer. [drawer] / Reach beneath the drawer. [drawer] / Feel under the passenger seat. [passenger seat] / Look under the passenger seat. [passenger seat] / Search beneath the passenger seat. [passenger seat] / Check under the driver's seat. [driver's seat] / Feel under the desk. [desk] / Search under the bed. [bed] / Look beneath the tray. [telescope tray] / Feel under the telescope tray. [telescope tray] / Check under the bench. [skiff bench] / Reach under the locker. [locker] / Search below the workbench. [workbench] / Look under the crate. [crate] / Feel beneath the table. [table] / Slide my hand under the shelf. [shelf].

Negatives (29, answer must be false): drawer: Inspect the drawer. / Open the drawer. / Pull out the drawer. / Search the drawer. / Feel inside the drawer. / Look inside the drawer. / Close the drawer. / Look behind the drawer. / Check the top of the drawer. / Take the pens from the drawer. Seat: Inspect the passenger seat. / Sit on the passenger seat. / Search the passenger seat. / Put my laptop on the passenger seat. / Look at the driver's seat. Other: Inspect the telescope tray. / Look in the locker. / Open the crate. / Examine the bench. / Search the table. / Clear the desk. / Check on top of the shelf. / Look behind the bed. / Search the workbench. / Wipe the table. / Push the chair under the desk. / Slide the tray under the telescope. / Lift the crate. / Read the label on the locker. (The two "under" commands that move something are deliberate hard negatives: the question must not answer true for them.)

Counts and cost: 49 cases x 2 samples = 98 requests, estimate under $0.003, ceiling $0.01 (local Worker `--max-usd 0.01`), stop on 429, auth failure or cap, no rerun.

Gate P (set now):
- J1: false-true answers on negatives: **zero** of 58 samples (one-sided 95% bound about 5%). A true on a negative lowers the requirement, so this is the safe direction to be strict on.
- J2: true answers on positives: at least **36 of 40** samples (90%); every missed positive is listed by name. A miss only leaves today's stricter scope, but if the question rarely fires the contract does not reach Brandon's requirement.
- Not true counts any `None`/unknown answer as not true; report their number and every score.
J1 or J2 failing stops the plan here: no enforced run; a new question wording needs its own preregistration, tested on a fresh phrase list (not tuned on this one).

## Stages S and F: enforced runs with the new contract

**What runs.** As stage 1: real engine, product wiring, observation mode on, `enforcing_verifier` on (`live_baseline.py --enforce`), shadow off, local Worker with a hard dollar cap, 70B JSON off, 20 s timeout and no retry on a timeout. New: the contract of PR #716.

**Routes.**
- **A `observe_topup`** (unchanged, 9 commands): `inspect the drawer`, `pull out the drawer`, `feel under the drawer`, `feel under the drawer`, `go outside`, `inspect the truck`, `enter the truck`, `pick up my laptop`, `inspect the passenger seat`. Same route as the shadow re-run and the stage-1 smoke, so the comparison isolates the contract change.
- **B `observe_under_first`** (new, 4 commands): `feel under the drawer`, `feel under the drawer`, `inspect the drawer`, `pull out the drawer`. It starts with the card still hidden, so the first underside search is the one Brandon cares about. Added to `ROUTES` in `live_baseline.py` with the other routes.

**Counts and cost.** A: expected about 600 calls and $0.11 (the stage-1 smoke measured 56 calls for one replicate; the new Jev question adds about 4 requests per replicate). B: about 25 calls per replicate.
- Stage S (billed once, not counted in any rate): A 1 replicate (`--max-calls 90`) then B 1 replicate (`--max-calls 40`), local Worker `--max-usd 0.05`, expected about $0.02. It checks plumbing: rows carry the request kind, the underside question is asked only for container or supporter focuses, the report builds sheets for both routes.
- Stage F (billed once): A 10 replicates (`--max-calls 800`) then B 5 replicates (`--max-calls 250`), `--max-usd 0.30`, expected about $0.15. No retries, no replacement samples. Stop on any quota code, 429, 5xx or cap and keep the partial result. A turn that fails because enforcement exhausted its recovery is a result, not a stop.
- Output to `bench/results/environment-narration/t9b-scope/{probe,smoke,full}/{a,b}`; no earlier directory is touched.

**Procedure.** As stage 1: free dry run, billed stage, each one Ringer probe task whose check asserts a stop reason or the exact row count; blind sheet; I read every turn and freeze the labels hash before any verdict is opened; then `join`. Added labels, from the narration and command text only: `underside_search` per container or supporter turn (is the command an underside search?), and `card_found_in_prose` on route B turns where the card moves to the player.

**Gate (set now).**
- All stage-1 clauses 1 to 7 on route A, unchanged (at most 1 unsuccessful observation turn; zero committed narrations missing a required thing; zero leak / wrong custody / unrequested move, at most 1 each of refind and invented object; exact rollback; at most 2 narration attempts and 2 verifier requests; p95 of no-recovery turns at most 10 s; false rejects at most 1, inconclusive under 5 rejections).
- S1 classification audit (both routes): every turn whose recorded kind is `under` has `underside_search` true: **zero** violations. A violation means coverage was suppressed on a command that was not an underside search.
- S2 non-vacuity (route A): at least 10 turns with kind `under` and at least 20 turns with a non-empty required list, else INCONCLUSIVE, never a pass. This stops an empty requirement list from manufacturing a pass.
- S3 (route B): in at least 4 of 5 replicates the card is held by the player after the second command AND the narration of that turn shows it being found (`card_found_in_prose`); zero turns mention the card before it is found (`leak` tag). If it fails, the report says whether the first underside search or the reveal failed; it is then a finding about the reveal path (the verb `feel` may not match an authored action group), not a verdict on the contract.
- Route B is also held to clauses 2 to 5; its counts are too small for clause 1, 6 and 7.
Printed, not gated: kind distribution per route; underside-labelled turns not classified `under` (misses); opening turns (kind `open` on a closed container) and the share whose committed narration presents the public contents; count of `searches_underneath` requests per replicate (from the recorded prompts); first-attempt rejection rate and recovery success rate (stage-1 definitions).

A pass does not deploy anything and does not turn the hosted switch on. It permits writing the T9 confirmation preregistration. Clause 2 failing is a stop.

**Expected, not measured:** the six underside rejections of the shadow re-run vanish (no required relations on `under` turns); opening turns now carry the duty line, so their rejections should drop; the unknowns are Jev's classification, the `feel` reveal path in route B, and the retry's behaviour on whatever rejections remain.

**Stated limits.** One story and 70B only; one reader who knows the aim; ten replicates share one start. The phrase list is small and hand-made; a pass shows the question works on these phrases, not on all player language. An `under` turn has no verifier relations, so the verifier cannot catch an invented find under the object or a false "nothing is there"; the `refind` and `invented_object` tags (hand-read) are the only check there. The old stage-1 gates were not tuned to this contract.

**Build (free, Ringer, tests first, after approval).** (1) `under_question_probe.py` modelled on `holder_wording_probe.py` (frozen cases with a SHA-256 lock, `--check-corpus`, `--dry-run`, `--run --confirm`, `--report` with J1 and J2 and every score), its frozen case file, tests, and a one-task runner manifest with a row-count check. (2) Route `observe_under_first` in `live_baseline.py`; `--enforce` rows also record `observation_request` (kind and focus; the same stale-record rule as `--shadow`). (3) `enforce_stage2.sh smoke|full` (port 8796; both routes in sequence under one Worker cap; output `t9b-scope/`) and runner manifests from a generator that asserts every number. (4) `enforce_report.py`: labels `underside_search` and `card_found_in_prose`, clauses S1 to S3 chosen by the rows' route, and the new information lines, tested with synthetic rows that violate each clause. The earlier script, manifests and report tests keep passing.
