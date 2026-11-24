# Step 5: qualify independent diagnosis and completed repair

Part of the [qualification plan](../dark-factory-diagnostic-qualification-plan.md). The goal, check, estimate and owner's-word text below is the binding audit text, moved verbatim on 2026-11-23; the task list under it tracks progress. The original detailed requirement is [Phase 6](original-phase-spec.md#phase-6-qualify-independent-diagnosis-and-repair).

**Read this when:** you prepare or run the held-out solver trials.

## Goal, check, estimate and owner's word

**Goal.** Execute original Phase 6 with the repaired measurement, isolation and structural route. Freeze workflow and rubric before unsealing solver outputs.

**Check.** Six sealed cases, two fresh trials each. Score cause, citations, compatible remedy, measurement and execution separately; controls must remain unchanged. Every defect needs a repair/test outcome, and at least one held-out structural repair must reach a verified patch through the line. Unsupported can be honest but cannot satisfy repaired. Workers cannot alter scorer, private checks, caps or judge. Failures stay in denominators. A case used to tune the workflow becomes development evidence; replacement holdout evidence is required for a new independence claim.

**Estimate.** 0.5–1 day setup/review plus model time; roughly 40k–100k solver/review tokens per trial (480k–1.2M total), plus 100k–300k Ringer tokens for a structural implementation. Billed narration $0 for this offline phase. These are provisional until bounded prompts and call limits are prepared.

**Owner's word.** Approve the frozen run specification and subscription ceilings. Do not ask the owner to grade a disputed repair; independent evidence review resolves it or marks the case inconclusive.

## Tasks

- [ ] Freeze workflow, solver model, prompts, rubric and limits; write the run specification with exact call and token ceilings.
- [ ] Twelve fresh trials (six sealed cases, two each); controls unchanged; failures stay in denominators.
- [ ] At least one held-out structural repair reaches a verified patch through the line.
- [ ] `qualification/heldout-results.json`, evaluator evidence, full transcripts and a pass/fail/inconclusive decision.
