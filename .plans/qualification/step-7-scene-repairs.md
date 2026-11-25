# Step 7: run the factory through actual scene repairs

Part of the [qualification plan](../dark-factory-diagnostic-qualification-plan.md). The goal, check, estimate and owner's-word text below is the binding audit text, moved verbatim on 2026-11-23; the task list under it tracks progress. The original detailed requirement is [Phase 7](original-phase-spec.md#phase-7-demonstrate-transfer-to-the-actual-player-experience).

**Read this when:** you plan or run a repair campaign on real play.

## Goal, check, estimate and owner's word

**Goal.** Transfer the qualified workflow to unresolved real play and clear the nine-scene backlog without an operator choosing fixes.

**Check.** The factory selects the next evidenced defect, investigates, preregisters a discriminating control/candidate experiment, repairs, reviews and verifies. Include a fresh defect not used in development or qualification. Use seeded canonical entry for focused tests and reachable optional carry-in states where relevant; label them. Preserve provider settings, profiles and entry distributions between arms. Use the applicable runbook's sample size (live bench at least four; three hosted replicates are a smoke), then twelve for adoption where required by the parent plan. After shared-engine/prompt changes, repeat affected-scene checks and continuity checks. A targeted improvement does not mark the scene zero-stuck. Automatically reopen residual failures and stop on unchanged-failure/budget breakers. The solver, not the owner, chooses ordinary fixes.

**Estimate.** 2–5 days for an initial bounded repair campaign, not a promise all defects fit; 0.5M–1.5M subscription tokens and a provisional $5–$15 narrator/player/judge envelope. Unknown defect count is the main uncertainty. Reserve cumulative spend by ticket and campaign; prepare each run specification before requesting authority.

**Owner's word.** Authorize a concrete bounded campaign, model windows and permissible merges before start. An approved campaign can cover its specified calls without per-fix questions. Policy changes, budget increases and circuit breakers still return to the owner; they do not count as autonomous success.

## Tasks

- [ ] Owner authorizes a concrete bounded campaign (model windows, spend, permissible merges), with an estimate written first.
- [ ] Include a fresh defect not used in development or qualification.
- [ ] Each repair: evidenced selection, investigation, preregistered control/candidate experiment, review, verification; residual failures reopen automatically.
- [ ] Repeat affected-scene and continuity checks after any shared engine or prompt change.
- [ ] Actual cost recorded beside each estimate in the factory plan's calibration table.
