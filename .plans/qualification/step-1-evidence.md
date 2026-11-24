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
- [ ] **1.4 Derivability sign-off**, one fresh Opus session per case (about 35k to 55k tokens each; spec estimate 440k to 520k in all). Needs the owner's figures first.
- [ ] **1.5 Model-based isolation canary**, one short subscription session (10k to 20k). Needs the owner's figures first.
- [ ] **1.6 The structural case.** Recommended: a labelled synthetic case first (free), then a seeded billed screen on an unexamined scene only after Step 2 lands. 3B stays `wording_or_matching`; N-3 and 15d are known and cannot fill the slot.
- [ ] **1.7 Healthy development case**: single-replicate exports of 1C replicates 1 and 3, labelled development.
- [ ] **Scoring spec v2** with a new sha256. Step 2 changes the stuck definition, so under the frozen `scoring-spec.md` every affected candidate moves to development and needs a replacement before sealing.
- [ ] **Seal the held-out set**: four defects (at least three mechanisms, two scenes, one story_structure) and two controls.

## Held-out candidates (not sealed)

Controls: 1B, 2A, 1C. Defects: 2B and 2C (`narration_provenance`), 3A and 3B (`wording_or_matching`; 3B allows an authored stall beat as an alternative repair). Missing: a pure `story_structure` defect outside the 1A development scenes. Evidence for each verdict is in the [resume log](resume-log.md).
