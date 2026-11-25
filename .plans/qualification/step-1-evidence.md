# Step 1: make the evidence set trustworthy

Part of the [qualification plan](../dark-factory-diagnostic-qualification-plan.md). The goal, check, estimate and owner's-word text below is the binding audit text, moved verbatim on 2026-11-23; the task list under it tracks progress. Work spec: `qual-20261122/qualification/step1-spec.md`.

**Read this when:** you work on answer records, citations, isolation, the held-out case set or sealing it.

## Goal, check, estimate and owner's word

**Goal.** Refresh the inventory at the implementation SHA, correct answer citations with an audit trail, and seal only a genuinely isolated, derivable evaluation. Keep the current cases as candidates until this gate passes.

**Check.** Validate complete literal quotations at exact turn/source locators; distinguish paraphrase from quotation. Hash source, records, answers and scorer. A separate evaluator checks derivability and acceptable alternatives, including 15d's unresolved references and 3A's two errors. Test path-denial and contamination canaries without models. Include a healthy development case before scoring controls. Keep 3B's two-mechanism result; obtain a new structural case from previously unexamined evidence or a separately authored synthetic case. Label synthetic evidence and retain live transfer. N-3 and 15d are known, so neither fills the unseen slot. Do not pass this audit or private case descriptions to the solver/implementation worker. The frozen `qualification/scoring-spec.md` says a scoring change moves every affected case to development. Version the new measurement/scoring contract; move affected candidates accordingly and obtain replacements before sealing. Do not silently re-score them under a new rule and call the result blind.

**Estimate.** 4–8 hours preparation; roughly 35k–65k subscription tokens per fresh evaluator, 210k–390k for six sign-offs, plus one new-case evaluation if needed. Saved-evidence work $0; a new seeded three-replicate scene screen provisionally $0.05–$0.50 narrator/player spend, with no guarantee it yields the needed mechanism.

**Owner's word.** Approve evaluator/subscription runs and any fresh billed screen after its exact specification is ready. Recommend retaining structural coverage, not waiving it. No owner choice of a particular fix is needed.

## Tasks

- [x] **1.1 Citation validator** (`qual-20261122/tools/citation_check.py`, workspace commit `719adfb`). Full-quote, line-accurate; `run_evaluator.validate` delegates to it. Found 32 problems in the nine answer records that the old validator passed.
- [x] **1.2 Answer-record corrections** for all nine records (`private/answer.v2.json` per case; originals untouched; hashes in `qualification/answer-versions.json`; audit trail `qualification/answer-corrections-<case>.json`). Caveat: shortened quotes locate evidence but may support less; 1.4 must judge that.
- [x] **1.3 Isolation and contamination check without models** (`tools/isolation_check.py`, 16 tests). Does not prove the tool sandbox itself; 1.5 does.
- [x] **1.4 Derivability sign-off** (2026-11-24, after the confinement fix; 11 sessions, 393,213 tokens, results in `qual-20261122/qualification/signoffs/<case>.json`). **Only 2 of 11 signed off** (`dev-1A-15d`, `dev-1C-healthy-r3`); 9 are `inconclusive` and, by the rule, excluded and not forced. Every session judged its case derivable; the disagreement is about the conclusion. Table below.
- [x] **1.5 Model-based isolation canary** (2026-11-24). First run FAILED: sessions could read the private answer, a sibling case and an absolute path. Fixed by round 33c (path-scoped rules); re-run PASSED (5 of 5 escapes refused, legitimate read works). Proves those paths only.
- [ ] **1.6 The structural case.** Recommended: a labelled synthetic case first (free), then a seeded billed screen on an unexamined scene only after Step 2 lands. 3B stays `wording_or_matching`; N-3 and 15d are known and cannot fill the slot.
- [x] **1.7 Healthy development case** (2026-11-24, free): `cases/dev-1C-healthy-r1` and `cases/dev-1C-healthy-r3` in the workspace, single-replicate exports of `r4-1C.json` at `83dac802`, labelled `development`, verdict `healthy` (correct answer: no change). Answer records `private/answer.v2.json` validate with zero citation problems; the isolation scan passes with tokens derived by `derive_forbidden_tokens` (the case manifests carry them). Derivability sign-off for these two is part of 1.4.
- [ ] **Scoring spec v2** with a new sha256. Step 2 changes the stuck definition, so under the frozen `scoring-spec.md` every affected candidate moves to development and needs a replacement before sealing.
- [ ] **Seal the held-out set**: four defects (at least three mechanisms, two scenes, one story_structure) and two controls.

## Held-out candidates (not sealed)

Controls: 1B, 2A, 1C. Defects: 2B and 2C (`narration_provenance`), 3A and 3B (`wording_or_matching`; 3B allows an authored stall beat as an alternative repair). Missing: a pure `story_structure` defect outside the 1A development scenes. Evidence for each verdict is in the [resume log](resume-log.md).

## Sign-off results (2026-11-24)

| Case | Role | Outcome | Independent reading | Original record | Cited items judged unsupported / partly |
|---|---|---|---|---|---|
| dev-1A-15d | development | signed off | defect, story_structure | same | 0 / 6 |
| dev-1C-healthy-r3 | development | signed off | healthy | same | 0 / 3 |
| dev-1C-healthy-r1 | development | inconclusive (agrees, one cited item unsupported) | healthy | same | 1 / 3 |
| dev-1A-18c | development | inconclusive | defect, narration_provenance | defect, wording_or_matching | 0 / 8 |
| heldout 1B (control) | control | inconclusive | defect, harness_or_runtime | healthy | 2 / 4 |
| heldout 1C (control) | control | inconclusive | defect, story_structure | healthy | 0 / 5 |
| heldout 2A (control) | control | inconclusive | defect, wording_or_matching | healthy | 0 / 8 |
| heldout 2B | defect | inconclusive | defect, story_structure | defect, narration_provenance | 0 / 1 |
| heldout 2C | defect | inconclusive (agrees, 3 cited items unsupported) | defect, narration_provenance | same | 3 / 1 |
| heldout 3A | defect | inconclusive | defect, story_structure | defect, wording_or_matching | 1 / 4 |
| heldout 3B | defect | inconclusive | defect, story_structure | defect, wording_or_matching | 0 / 3 |

**What this means.**
- **None of the three controls signs off.** A fresh reader finds a defect in each. Either the controls are not healthy or the sign-off reader over-finds; this run cannot tell which. 1C's own record already says a story_structure reading of its replicate 2 is arguable.
- **The mechanism class is the contested part.** 3A and 3B were already known as a wording-versus-structure judgment call; 2B differs in a different pair. The honest reading is that the class labels are not reproducible by a second reader, so scoring a solver on them would be unfair.
- **Two records agree on the verdict and class but cite evidence the second reader says does not support it** (1C-r1 once; 2C three times; the quotes were shortened in step 1.2, which this was meant to test).
- **No case was forced or re-labelled.** The held-out set stays unsealed. Options that need your decision: (a) adjudicate each disagreement by reading both records (Opus design session, then a fresh sign-off), (b) rebuild the controls and defects from new evidence, (c) score only on verdict (defect versus healthy) and treat the class as advisory.
