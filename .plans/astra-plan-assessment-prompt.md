# ChatGPT prompt: objective assessment of the Astra implementation plan

Paste everything below the line into ChatGPT Desktop with the freytag-forge project files attached.

---

You are an independent reviewer. Assess `.plans/astra-implementation-plan.md` in this repository objectively. Your job is to find what is wrong, weak, unproven or missing, and to say what is sound. Do not flatter, do not soften, and do not pad.

## What the plan is

The plan implements two reviews: `.plans/astra-weak-spots-review.md` (material fixes) and `.plans/astra-arch-review.md` (a proposed outcome-first turn pipeline, to be judged by a three-arm evaluation). The plan has phases 0 to 6, a long list of dated result entries, and a decisions section. The newest entries describe work done on 2026-10-14: a guard-rejection retry, a recovery-flag split, an `assess` verb change that regressed on staging and was reverted, a diagnosed engine defect (candidate cap mismatch) and its fix in PR 632.

## Ground rules

1. **Verify against the repository, not against the plan's own claims.** Every result entry is the author's account. For each claim you rely on, open the code, test, data file, bench result or artifact it refers to, and say whether it supports the claim. Cite `path:line`. If you cannot find the evidence, say "not found", not "plausible".
2. **Separate three things in everything you write:** (a) verified by you in the files, (b) stated in the plan but not verifiable from the files, (c) your inference. Label each.
3. **Read the project rules first:** `AGENTS.md`, `docs/contributor-guide.md`, `docs/PRD.md`, `docs/agent-workflow-guide.md`, `docs/testing-runbook.md`, `docs/world-model-grounding.md`. Judge the plan against these, not against generic practice. Where the plan conflicts with a project rule, say which rule.
4. **Do not propose new features.** Recommend only fixes, cuts, re-orderings, or measurements that the evidence in the repo supports. For each recommendation, say what evidence in the repo (or what missing evidence) leads to it.
5. Be quantitative where the plan is. Where the plan reports a result, say whether the sample size, controls and scoring support the conclusion it draws.

## Questions to answer

### A. Are the conclusions supported by the evidence?
For each of these, state "supported", "partly supported" or "not supported", with the reasons:
1. "Keep the 1C pointer" (Phase 1, paired 12-start comparison across three builds).
2. "`renarrate` with cue-restore is the only measured arm that removes the false claim" and the later "engine-owned refusal meets its bars" (Phase 4 item 2, five sub-experiments, one scene, 16 to 40 distinct commands, one reader, partial blinding).
3. "The marker is not adopted" (wording variants, held-out set H1, pre-registered rule, H2 never run).
4. "`@spine` passes on staging" as evidence for each fix it was used to justify. Specifically check what a passing `@spine` run can and cannot show, using `frontend/e2e/scene-runtime.spec.js`, `docs/testing-runbook.md` section 6, and the plan's own caveat that it asserts no storylet or ending coverage.
5. The diagnosis of the turn-48 HTTP 409. The plan first attributed it to an already-established reveal and then corrected it to a projection-cap mismatch. Check the corrected diagnosis against `storygame/runtime/cloudflare.py`, `storygame/runtime/knowledge.py` and `storygame/runtime/validation.py`. Is it complete? Is the fix in PR 632 (the resolver accepts a selected id beyond the cap only when it equals the provider-owned `authored_handoff_id` and is in `reveal_universe`) correct, minimal and safe? Name any path by which a model reply could obtain that marker, any stale-state path for `authored_handoff`, and any case where the semantic handoff path (`_semantic_authored_handoff`) widens acceptance beyond what the plan says it intends.

### B. Is the process sound?
1. The `assess` change (PR 629) passed its own tests and CI and then broke hosted `@spine`. What does that say about the test strategy for knowledge-data changes? Which check would have caught it before merge, and does the repo already have a place for it (see `tests/test_canon_journey.py`, `tests/test_scene_relative_pacing.py`, the disclosure and leakage matrices)?
2. The plan repeatedly measures with n = 1 to 12 near-deterministic samples and says so. Judge whether the plan's decisions respect its own stated limits, or whether any entry draws a firmer conclusion than its sample allows.
3. Pre-registration: the plan pre-registers bars for the marker variants and the fixed-refusal step. Did later experiments (engine-owned refusal, mixed refusal, tuning) keep that discipline, or were bars or commands changed after seeing results? Cite the freeze files under `.plans/`.
4. Several entries record harness defects found only after a billed run (an unfired marker, a dropped option, a wrong artifact path, a sandbox that cannot write to the checkout). Is there a systematic gap in how billed runs are validated before they are read?

### C. Is the scope and ordering right?
1. Phases 1 to 4 were meant to be cheap fixes that are valid under either pipeline design; Phase 5 compares three arms. Given what has been learned since, is the Phase 5 comparison still justified, and what is the strongest argument for cutting it? What does the plan say it must show for arm C to be kept, and is that bar realistic given the measurement limits above?
2. Rank the open items by value for the cost: Phase 4 items 3 and 4, the retry rescue-rate measurement, the third 2C `@spine` prompt that earns no reveal (`k_sl_2c_d_r1` has no `follow` verb), the `renarrate` default, the `hideout` scoped-alias gap, and re-adding `assess` to `k_sl_2c_c_r2`. Say what you would do next and what you would stop doing.
3. Is anything in the plan done only to close out a list item, with no evidence it helps a player? Check against `docs/PRD.md` and the memory-style rules in the plan's decisions (engine performs prerequisite steps; no regex or reply-phrase parsing; deterministic authored text over LLM generation; facts are the sole mutable truth).

### D. Does the work violate a project rule?
Check the recent changes (PRs 628 to 632 and the Ringer manifests under `scripts/ringer/astra/`) against `AGENTS.md` and the contributor guide. In particular: story-agnostic shared runtime (the engine now has an `isinstance(self.provider, CloudflareTurnProvider)` check and a provider-owned handoff id), LLM-proposal-first, hermetic unit tests, guarding every billed endpoint, and keeping `docs/testing-runbook.md` short. List every violation or near-violation with the file and line.

## Output format

1. **Verdict** (at most six sentences): is the plan on a sound footing, and what is the single biggest risk?
2. **Findings table**, ordered by severity: `#`, severity (blocker / major / minor), claim or decision, what the evidence shows, evidence cited (`path:line`), label (verified / not verifiable / inference).
3. **Answers to A to D**, each with the sub-questions answered by number.
4. **What is sound**: the specific decisions and results you checked and found well supported. Name them; do not write a generic compliment.
5. **Recommended next three actions**, each with the evidence that leads to it and the cheapest way to confirm it.
6. **What you could not assess** and why (missing files, unreadable artifacts, results that exist only as prose in the plan).

Keep the answer under 2,500 words. Write Kristin as Kr and Brandon (the character) as Br where they come up; quotes stay verbatim.
