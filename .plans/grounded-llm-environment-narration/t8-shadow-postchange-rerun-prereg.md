# T8 shadow re-run under the corrected order: preregistration (written 2026-10-27, before any billed call)

Status: written for Brandon's go on the smoke and then the full run (he asked for the re-run on 2026-10-27; the numbers below follow the plan's "Next" line). No billed call has been made. Nothing here changes `t8-shadow-sample2-topup-prereg.md` or its result. This is a separate sample; its rates are never pooled with sample 1, sample 2 or the top-up.

**Why.** The top-up's verifier gate failed on 2b (9 of 78 acceptable turns would be rejected, 11.5%, limit 10%). Six of the nine were `pick up my laptop` turns where the shadow required the laptop on the seat, the place BEFORE the turn, because `WorldCapture.after_commit` ran the shadow before `apply_item_facts`. Enforcement (`preview_commit`) builds the context on the post-change world. PR #710 (merge `59792b1e`) moved the shadow block after the item facts, so the shadow now measures the requirement enforcement would use. This sample re-measures the verifier gate with the fix in place. The three other rejections (the card omitted on two `enter the truck` turns, drawer contents omitted on one `feel under the drawer` turn) are narration gaps, not touched by the fix.

**Question.** On the top-up route, does the verifier gate (clauses 1 to 4, 2b and 6 below) now pass?

**Code.** The run's SHA is the merge commit on main that contains PR #710 plus this harness (recorded per row). Staging deployed and recorded for that SHA before any billed run, and no merge to main while the run is in progress. No product code changes beyond PR #710.

**What runs.** Unchanged from the top-up: real engine, product wiring, observation mode on, `shadow_verifier` on, `enforcing_verifier` off, local Worker on 127.0.0.1 with a hard dollar cap (`local_worker.mjs --max-usd`), 70B JSON off. The verifier changes no turn.

**Route.** `observe_topup`, frozen, 9 imperative commands: `inspect the drawer`, `pull out the drawer`, `feel under the drawer`, `feel under the drawer`, `go outside`, `inspect the truck`, `enter the truck`, `pick up my laptop`, `inspect the passenger seat`. Same route as the top-up, so the comparison isolates the order fix (and the 70B's run-to-run variation). It has no scene-transition turn, so clause 5 prints `INCONCLUSIVE (n=0)` as designed.

**Counts and cost.** The top-up measured 495 calls and $0.0873 for 90 turns.
- Smoke (billed, not counted in any rate): 1 replicate x 9 turns, `--max-calls 70`, `--max-usd 0.03`; expected about 50 calls and $0.009. Checks: rows carry the shadow record; the `pick up my laptop` turn is narrated without error; if the laptop was on the seat before that turn and the narration picks it up, the shadow relations for it are mention-only (no place `on the seat`); the report accepts the route.
- Full: 10 replicates x 9 = 90 turns, `--max-calls 600`, `--max-usd 0.20`; expected about 495 calls and $0.09. No retries, no replacement samples. Stop on any quota code, 429, 5xx or cap, keep the partial result, never rerun. A single fast connection error keeps the product's one retry; a timeout is not retried.
- Output to `bench/results/environment-narration/shadow-sample3-postchange/{smoke,full}`; the top-up directory is not touched.

**Procedure.** As the top-up: free dry run, billed smoke, billed full (each one Ringer probe task whose check asserts a stop reason or the exact row count); blind sheet from `shadow_report.py sheet`; I read every observation turn and write `acceptable`, the relation labels and the two tags before any verdict is opened; freeze the labels hash; then `join`. Every turn is reported, none dropped.
- **Labelling rule (added after the top-up's error).** A relation is labelled true only if the narration presents that thing as being at the required place (or, for a mention-only relation, mentions it). A narration that never presents the thing makes the relation false, and the turn is acceptable only if that omission does not break the scene. I label from the narration text, not from what the facts say should be there.

**Gate (set now, before any data).** Verifier clauses, the same limits as sample 2 and the top-up's information line:
1. Zero false accepts among labelled relations.
2. Good-turn strict reject at most 10%.
2b. Acceptable turns that enforcement would reject at most 10% (`no_relations` is not a rejection).
3. Verifier request latency p95 at most 2.0 s.
4. At least 30 labelled relations, else inconclusive.
5. Scene-transition turns record `requirement_dropped`: n = 0 on this route, inconclusive by design, not a failure.
6. Held-item mention relations reported by type; a rejected true mention relation counts under 2b.
Clauses 7 and 8 (re-find of the held card, invented object on the empty seat) are printed for information. They closed in the top-up with no defect seen and are not this sample's gate; if either shows 2 or more failures it is reported as a regression. A pass of clauses 1 to 6 does not enable enforcement; T9 is separate.

**Expected, not measured:** about 3 of 78 acceptable turns rejected (the omissions), under the limit. If 2b still fails, the report names the turns and relation types, and the pick-up explanation is wrong or incomplete.

**Stated limits.** One story, one route, 70B only, one reader who knows the aim. Ten replicates share one starting state, and relations within a turn are correlated. 0 false accepts in about 128 relations bounds the rate only to about 2 to 3% (one-sided 95%). The top-up's labelled omissions came from the 70B's narration; they vary between samples, so 2b can move either way by chance alone (one turn is 1.3 points). This sample does not re-derive sample 1's or sample 2's numbers.

**Build (free, Ringer, tests first).** (1) `shadow_sample3_postchange.sh smoke|full` (port 8794, the caps above, output under `shadow-sample3-postchange/`); the top-up script is untouched. (2) Runner manifests `run-shadow3-postchange-{smoke,full}.json` from a generator that derives them from the top-up manifests, with a test that no top-up path remains. (3) A test that the script and manifests carry only this sample's numbers and paths.
