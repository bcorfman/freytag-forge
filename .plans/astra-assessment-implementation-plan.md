# Astra assessment follow-up: implementation plan

Source: `.plans/astra-plan-assessment-answer.md` (outside review of `astra-implementation-plan.md`).
Status: **A1 done and committed (08a925ac, Option 1); A2 committed (8901f3c0) with the budget-reset fix (Ringer `astra-budget-reset`: `end_turn()` called in a `finally`, 3 tests, suite 1739 passed; the stale-budget caveat below is closed); A3 done and committed (2026-10-14); B, C, D, E not started.** Branch for A1-A3: continue `astra-established-reveal-409` or cut a new one from main. Update this file after each step (memory: update-plan-after-each-feature).

Ground rules: every code change goes through Ringer (one task per run unit); unit tests stay hermetic (no live worker); no billed run before a smoke test; measure each step before the next; keep the repo ruff-formatted. Findings are numbered as in the assessment (F1-F8).

## Checked against the code before planning

- **F1 confirmed.** `cloudflare.py:341-347`: an exact match sets `authored_handoff`, and if none, `_semantic_authored_handoff` (`:447`, builds `AuthoredHandoff` at `:517`) sets the same field. `validation.py:208` then lets any id equal to `authored_handoff_id` and in `reveal_universe` skip the 4-candidate cap. So a semantic-model pick beyond the cap is accepted, and an exact tie falls into semantic fallback.
- **F2 confirmed.** `engine.py:191` loops `TURN_NARRATION_ATTEMPTS = 2`; each `self.provider(...)` call can also do its own shared recovery request. Contributor guide (`:54`): at most one inference plus one shared recovery per turn.
- **F3 confirmed.** `cloudflare.py:306` appends the full rejection message (which names the protected term) to the system prompt.
- Not rechecked here (taken from the assessment, verify when each step starts): F4 (`bench/pipeline_eval/runner.py:57`), F5, F6 (`p4-refusal-measure-check.sh:25`), F7, F8, and the D-section items.

## Step A1: Settle handoff authority (F1) — highest priority, trust boundary

**Result (2026-10-14, Ringer `astra-handoff-authority`, commit 08a925ac):** Brandon chose Option 1. `AuthoredHandoff.source` (default `semantic`); only `exact` gets the beyond-cap exception; the semantic shortlist is limited to model-visible candidates (at cap 4 it asks Jev about at most 4, not 6); handoff cleared at prompt assembly, turn start, and every failure/rollback path. Four new hermetic tests (semantic, tie, forged JSON, provider reuse). Full suite 1728 passed. The worker reports the semantic and reuse tests failed before the fix; the tie test was not shown failing. Not measured live.

Decision needed from Brandon first (blocks the code): which source may exceed the cap?
- **Option 1 (recommended):** only a unique *exact* match. Semantic picks and tie-breaks stay inside `projection.candidates`. Matches the PRD ("exact match commits; a tie commits nothing") and the stated intent of `7345632d`.
- Option 2: allow semantic picks too, but state it in the contributor guide and test it.

Work (Option 1):
1. Give `AuthoredHandoff` a `source` field (`exact` | `semantic`). Set it where each is built (`cloudflare.py:341`, `:517`).
2. `authored_handoff_id()` returns the id for beyond-cap use only when `source == "exact"`. Semantic handoffs still compose their delivery text, but the resolver cap check treats them as ordinary selections.
3. Exact tie (`:343`): semantic fallback may run, but its result must be a candidate-cap selection, never a beyond-cap one.
4. Clear `authored_handoff` on failure/rollback paths too (`:984` clears at opening only), not just rely on the next prompt overwriting it.
5. Hermetic tests in `tests/test_established_reveal_match.py` (extend, do not fork): exact beyond-cap commits; semantic beyond-cap rejected `ineligible_selection`; exact tie beyond cap rejected; forged narrator JSON selecting a beyond-cap id rejected; provider reused after a rejected turn does not carry the old handoff.

Exit: new tests fail before the change, pass after; full suite and ruff green. No billed run.

## Step A2: Unify recovery accounting and sanitize retry feedback (F2, F3)

**Result (2026-10-14, Ringer `astra-recovery-budget`, applied, not committed):** Brandon took the recommendation (keep the guide, make the budget real). `CloudflareTurnProvider._request` enforces 2 sends per engine turn (`begin_turn` resets it); exhaustion raises `NarrationProviderError` `NARRATION_REQUEST_BUDGET_EXHAUSTED` (503) and the engine now restores the snapshot on provider errors. The guard retry only fires if budget remains. `note_rejection(code)` sends a generic sentence chosen by code, never the validator text or the term. Explicit Protocols replace `isinstance`/`getattr` in `engine.py`. Runbook row updated. New `tests/test_recovery_budget.py` (8 tests). Full suite 1736 passed, ruff clean. Caveats: the worker says the new tests are "intended to fail" pre-fix, not shown; the budget stays set after a turn ends, so a provider call outside an engine turn (e.g. a later opening or probe on the same provider object) could hit an exhausted count until the next `begin_turn`; not yet measured live (rescue rate is the A2 billed measurement still to do).

Decision needed: is the guard retry a *second* request inside the shared budget (so a guard retry consumes the recovery slot), or does the guard policy change the contributor guide? Recommended: keep the guide, make the budget real.

Work:
1. One per-turn request counter owned by the engine, passed to the provider; the provider's JSON-mode/malformed/transient recovery and the engine's guard retry draw from the same cap of 2 requests. Exhaustion stays a typed fail-closed error with state restored.
2. Replace the raw rejection message in `note_rejection` with a sanitized note: a generic reason by error code ("your reply used a name or fact the player has not met; write it again without inventing one"), never the protected term. Check against `docs/narrator-writing-guide.md` and write the line at 12th-grade level.
3. Replace `isinstance(CloudflareTurnProvider)` / `getattr(note_rejection)` in `engine.py:198` with an explicit Protocol method on the provider interface (contributor guide `:64`); default no-op for other providers.
4. Hermetic scripted sequences: malformed then good; transient then good; guard-reject then good; guard-reject then malformed; guard-reject twice. Assert total requests <= 2, rollback on failure, and that the retry prompt contains no protected term.
5. Update `docs/testing-runbook.md:325` in place (rejected narration is retried once for guard rejections; others not). Keep the runbook short.

**Billed measurement result (2026-10-14, Ringer `astra-guard-retry-measurement`, 30 billed turns, build after commit "Classify any guard-retried rejected turn", 1A, imperative prompts):** the first probe (10 prompts) found the retry never fired: item-facts `single_call` match requests drew on the 2-request narration budget, so a leak after the match found zero budget (diagnosis `ringer-work/astra-guard-retry-diagnose-notes`, repro printed `guard_retry_fired=False http_requests=2`). Fixed by giving item-facts matches their own cap of 2 (`ITEM_FACTS_REQUEST_BUDGET`); a non-budget match error is still logged, not fatal. Final run, 16 turns (p5, p9, q1, q2 x4): 7 clean on first pass, retry fired 9, rescued 4, failed after retry 5; **rescue rate 4/9 (44%)**, no rescued reply repeated the term. Per prompt: p5 "Look for a maintenance access route into the facility." 0/4 rescued (the player's own words contain the protected phrase, and the sanitized note does not name it, so the second reply repeated it); p9 "Look for Michelle's coded note in the kitchen." 2/3 rescued; q1 "Search the kitchen for a maintenance access route." 2/2 rescued; q2 no rejection. N is small and prompts were chosen to bait rejections, so the rate is not a population estimate. Follow-up built (Ringer `astra-retry-typed-term`, 2026-10-14, Brandon's choice): the retry note now names the rejected term only when the player typed it (word-boundary, case-insensitive; `ProposalValidationError.term` is structured; untyped terms never reach the narrator); not yet re-measured live. Was open: p5-type prompts (player text carries the protected phrase) were not rescued by the sanitized note; an earlier probe turn narrated 'memory card' in 1A with no rejection (unchecked).

Exit: tests green. Then one billed measurement (smoke test first): replay known rejection cases (the 1B `bench`/`michelle's files` style prompts) N times, report retry rescue rate and whether the second reply avoids the phrase. Report every turn, successes included.

## Step A3: Evidence gates before any further billed spending (F6, F4, F5)

**Result (2026-10-14, Ringer `astra-a3-gates` x3 + `astra-a3-merge`, suite 1759 passed):** (1) `refusal_summary.py` (new, replaces the checker's heredoc) counts `engine_refusal` turns; on the saved engine-arm record it now reports refused=1 where the old summary said 0. New gates: `--expect-turns`, `--expect-refused-min`, provenance (git SHA and variation sha256 into the output), dirty-tree refusal unless `ALLOW_DIRTY=1`. (2) `bench/jev_use.py`: call cap (400, `FREYTAG_BENCH_JEV_MAX_CALLS`), stop on 429/AI_QUOTA_EXCEEDED/AI_DAILY_BUDGET_EXCEEDED, stop after 5 consecutive failures, `jev_stats()`; callers still get None. `bench/core.py` does not yet put `jev_stats()` in its summary. (3) Phase 3 `PipelineArm` reports real request and token counts (0 for an engine-refused turn) and real grounded state; ungrounded state keys are "unmeasured", counted in the aggregate. Process note: the first A3 run failed on my own brief (told workers to put tests under `bench/`, which `testpaths` never collects, and the check script collected `bench/` into the shard-balance test); the merge task moved all tests into `tests/`. Open: wire `jev_stats()` into the bench summary; the refusal-refused-via-stub test in the runner uses a stub engine seam, not the real fixed-refusal path.

1. `p4-refusal-measure-check.sh`: count refusals from the current telemetry field, not old capture messages; assert the treatment is active (engine-refusal arm shows refusals > 0 where scheduled), assert expected turn counts, and bind the artifact to the build SHA. Add a self-test fixture of a known engine-arm output.
2. `bench/jev_use.py` / the refusal wrapper: add a per-endpoint budget guard and stop swallowing request errors (memory: guard-every-billed-model-endpoint).
3. `bench/pipeline_eval/runner.py:57`: report real state and the real request count per arm, so the Phase 5 comparison can measure state and total cost. Fix before Phase 5 is reopened.
4. Record in the main plan that the refusal-tuning freezes were revised after the fact (mixed freeze vs tuning freeze vs the dropped second-package gate): disclosed policy changes, not strict preregistration. No new run needed.

Exit: checker rejects the old zero-refusal summary on the saved engine-arm output; runner reports non-empty state.

## Step B: Re-add `assess` to C-R2 (only after A1)

1. Add a hermetic stubbed-provider *engine-turn* test at the 2C state with a fifth eligible candidate: matcher -> projection -> eligibility -> commit, not just YAML evidence groups (replaces the logic gap in `tests/test_2c_assess_verbs.py`).
2. Re-add `assess`/`evaluate` and "our evidence" to `k_sl_2c_c_r2`; confirm no tie with `c_r1` through the real matcher.
3. Hosted `@spine` on a build that includes `7345632d` (the 813d0751 pass predates it and cannot validate it). Assert in the spec that the 2C turn earns the reveal, not only that 3C is reached.

## Step C: Spine and authoring gaps (value/cost order from the assessment)

1. Third 2C spine command ("Follow Michelle's coded message..."): first reproduce the semantic path on the real matcher; D-R1 says "decodes or reads", so do not award the reveal on a bare missing `follow`. Fix the prompt to the authored reading action, or add `follow` only if the contract supports it.
2. Phase 4.3 recent-cue reference resolution: narrow test; the record is a bounded projection of accepted facts, not transcript memory (PRD).
3. Phase 4.4 concealment/discovery: reproduce the confusion first; implement only if reproduced.
4. `hideout`: no change until it rejects something.
5. `renarrate`: stays off; stop adoption work on current evidence.

## Step D: Plan hygiene (F5, F7, F8)

1. Fix the marker control totals in `astra-implementation-plan.md:185` (3/24, 7/24, 1/24 if "stuck, then opens" counts; check the saved control).
2. Rewrite the opening status line and the stale "not merged" entries to match the later ones.
3. Correct the "renarrate removes the false claim" wording (the cue-restored run still had one success claim and three contradictions); narrow "wording is not the lever" to "these variants failed"; drop or measure the "40% combined saving" estimate.
4. Fix the stale diagnosis in `tests/test_2c_assess_verbs.py:33` (established-reveal reading is disproved).
5. Soften the 1C-pointer claim to "kept as a small authoring repair; improvement not demonstrated" (10/12 -> 11/12 is not an effect estimate).

## Step E: Phase 5 decision

Hold. Reopen only after A3.3 gives the harness real state/cost, and give the keep/drop conditions numeric margins (held-out gain, false-reveal and invention ceilings, refusal burden) before any run. Until then, A and B repairs above are cheaper than building C.

## Order and dependencies

A1 -> A2 -> A3 (A3 can run in parallel with A2) -> B -> C -> D (D can start any time, no code) -> E.
Brandon decisions needed: A1 Option 1 vs 2; A2 budget policy. Nothing here changes `main` without a per-PR instruction to merge.

## Not assessable from the files (from the review)

Independent human agreement, human-player benefit, cross-story reliability, deployment identity of older runs, and the exact turn-48 snapshot. A cross-story check is not planned here; the Step A/B changes avoid story-specific branches.
