# T8 second live shadow sample: preregistration (unapproved)

Status: written 2026-10-26 for Brandon's approval. No billed call has been made for this sample. Sample 1 (`t8-shadow-sample-prereg.md`) failed its gate on clause 2b; this one re-asks the same question after the fixes listed below. Its numbers are never pooled with sample 1.

**Questions.**
1. Verifier (Jev, `observation-relation-v1`, accept > 0.65, reject < 0.35, unchanged) on live 70B narration: does it now meet the same gate as sample 1, with the stale requirement dropped and held items reduced to mention-only relations?
2. Narration defects the verifier cannot see: are the two defects found in sample 1 gone from the shipped product path? (a) `feel under the drawer` re-finding the held memory card, 10 of 10 turns in sample 1; (b) invented objects on `inspect the passenger seat`, 3 of 5 turns in sample 1 (the prompt-level probe: arm A3 0/25, arm B2 0/25).

**What changed since sample 1 (all merged on main, or on branch `t8-underside-voiceable` which must be merged before the run).**
- Stale requirement dropped when the scene or the protagonist's area changes during a turn (`_observation_context_for_verification`).
- Held items give a mention-only relation; one short-name rule (first declared alias) in prompt, relations and Jev question.
- Harness: engine-authored move turns no longer carry the previous turn's shadow record.
- Speaker presence: a recording sentence no longer makes a missing speaker present; placement makes one present.
- 1A passenger seat declared `contents_complete: true` (empty seat gives the "Nothing is left in or under the passenger seat" line).
- Exhausted-underside line: "Nothing else is under the drawer. Searching under the drawer finds nothing more." once the card is out from under the drawer (derived from the authored `under` placement).
- `voiceable: false` on the 1A card-recovery statement, so no one is offered it as speech.
The run records the code SHA; it must be the merge commit of the branch above.

**What runs.** Same as sample 1: real engine, product wiring, observation mode on, local Worker on 127.0.0.1 with a hard cap (`local_worker.mjs --max-usd`), 70B JSON off, `shadow_verifier` on, `enforcing_verifier` off. The verifier changes no turn.

**Route (frozen, identical to sample 1).** `observe`, 13 imperative commands: inspect the drawer, pull out the drawer, feel under the drawer, feel under the drawer, go outside, inspect the truck, enter the truck, inspect the passenger seat, examine my laptop, get out of the truck, examine the truck, go inside, inspect the drawer. Commands that set no observation request are listed as skipped, not replaced.

**Counts and cost.**
- Smoke (billed, not counted in any rate): 1 replicate of the full route (13 turns), `--max-calls 100`, local-Worker ceiling $0.05, expected about 67 calls and $0.013. It checks that rows carry the shadow record, that turn 13 (scene change) records `requirement_dropped`, and that the underside and seat lines appear in the recorded prompts.
- Full: 10 replicates x 13 = 130 turns (twice sample 1 so the defect clauses have a usable n). Expected about 110 observation turns, about 100 to 140 relations, about 20 `feel under the drawer` turns after recovery, about 8 empty-seat turns. Sample 1 used 336 calls and $0.0633 for 5 replicates, so about 670 calls and $0.13 expected. Caps: `--max-calls 900`, `--max-usd 0.30`. No retries, no replacement samples; stop on any quota code, 429 or 5xx, or a cap; run once and never rerun after a partial result.
- Output goes to `bench/results/environment-narration/shadow-sample2/{smoke,full}`; sample 1's directory is not touched.

**Procedure.** As sample 1: dry run (free), smoke, full (each one Ringer probe task whose check asserts the row count or a stop reason, not only file existence); blind sheet from `shadow_report.py sheet`; I read every observation turn and write, per turn, `acceptable` and the relation labels, plus the defect tags below; labels hash frozen before `join`; `join` prints the confusion table, gate and defect counts. Every turn is read and reported, not pooled.

**Defect tags (hand labels, written with the relation labels, before the verdicts are opened).**
- `refind` on a `feel under the drawer` turn after recovery: the narration presents the held card as found, taken or pocketed again, or quotes the recovery sentence as speech or narration. A mention that Kr already holds it is not a re-find.
- `invented_object` on an `inspect the passenger seat` turn: the narration places an object on or in the seat that the facts do not show. Dust, fabric and floor detail do not count (the same rule as the defect probe).
- Also noted, not gated: invented objects on other turns, unrequested moves, contradictions.

**Gate (set now, before any data).**
Verifier clauses, the same as sample 1:
1. Zero false accepts among labelled relations.
2. Good-turn strict reject at most 10%.
2b. Acceptable turns that enforcement would reject at most 10% (`no_relations` is not a rejection).
3. Verifier request latency p95 at most 2.0 s.
4. At least 30 labelled relations, else inconclusive.
New clauses:
5. Every scene-transition turn (turn 13) records `requirement_dropped` and zero verifier requests. Deterministic; 10 of 10.
6. Held-item mention relations: reported by type; a rejected true mention relation counts under 2b like any other.
7. (D1) `refind` on at most 1 of the `feel under the drawer` turns after recovery, with at least 15 such turns, else inconclusive.
8. (D2) `invented_object` on at most 1 of the empty-seat turns (laptop held, so the seat is empty), with at least 6 such turns, else inconclusive.
Clauses 7 and 8 are product-defect gates, not verifier gates. If 1 to 6 pass and 7 or 8 fails, enforcement design is still allowed but the failing defect is reported as open. If any of 1 to 6 fails, enforcement stays off and the report names the clause and the relation type. A pass does not enable enforcement; T9 is separate.

**Stated limits.** 100 to 140 relations bound zero false accepts only to about 2 to 3% (one-sided 95%), and relations within one turn are correlated. One story, one route, the 70B narrator only. One reader who knows the aim and the arm structure (the blind sheet hides verdicts, not context). The 10 replicates share one route and one starting state, so the `refind` and seat clauses rest on small n. The fixes were measured at prompt level (n=25 per arm); this checks them end to end once, and a pass here does not show the rate is below any specific bound. The underside line fires only when the match model gives the drawer as the focus of `feel under the drawer`; if it does not, the line is absent and the turn counts in D1 anyway. The wording of the underside line is the probe's wording with the focus name filled in; it was not measured by the probe in this generic form. Outcomes depend on the current prompt, model revision and Jev version, all recorded per row.

**Build before the run (free, Ringer, tests first).** (1) `shadow_sample.sh` takes a sample tag so sample 2 writes under `shadow-sample2/` and cannot overwrite sample 1, with the caps above. (2) `shadow_report.py join` prints clauses 5, 7 and 8 from per-turn tags in the labels file (`refind`, `invented_object`) and the rows' `requirement_dropped`, and its labels template carries the new keys. (3) Runner manifests `run-shadow2-smoke.json` and `run-shadow2-full.json`. None of this is billed.
