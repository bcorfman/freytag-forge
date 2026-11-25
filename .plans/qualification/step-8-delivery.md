# Step 8: certify continuous 1A–3C completion and deliver the staged build

Part of the [qualification plan](../dark-factory-diagnostic-qualification-plan.md). The goal, check, estimate and owner's-word text below is the binding audit text, moved verbatim on 2026-11-23; the task list under it tracks progress. 

**Read this when:** you prepare or run the final whole-game sample or the delivery report.

## Goal, check, estimate and owner's word

**Goal.** Meet the whole-game bar on one immutable candidate SHA, using actual carried state and independent players.

**Check.** Before billed work, prove the report validator rejects partial or skipped scene lists, substituted snapshots, forced exits, unknown causes, a single failed replicate and false terminal completion. Freeze twelve continuous final runs, proposed as six canonical and six raw-profile players, with one source/provider/judge configuration and a declared total-turn ceiling. Keep canonical probe/example language per the player-input guide; raw is the explicit player-language exception. All twelve must satisfy the nine-scene completion contract above, plus continuity and fun gates. Include save/resume continuity as a separate check. **Before billed work, the whole-game fun gate (Fun requirements, item 6) must exist, be frozen and be calibrated; without it the "continuity and fun" part of this bar cannot be evaluated.** Every final run also reports whether the 3C epilogue (N-3) was offered and taken. Any confirmed stuck turn opens a blocking ticket; after repair, a new candidate SHA gets a new complete final sample and the failed sample remains recorded. The factory may stop early on a decisive failure, but may not report that partial sample as a pass.

Merge implementation only through the existing rules, wait for successful SHA-bound `main` CI/staging deployment, verify API/Pages identity, and do not merge other work during staged runs. Deliver the staged SHA, all transcripts, per-scene/replicate outcomes, structural coverage limits, repair lineage and complete cost ledger in `qualification/final-assessment.md`. Production promotion is separate and retains its exact-SHA staging and coverage requirements.

**Estimate.** 0.5–1 day preparation/review plus live latency and quota waits. At the parent's proposed 160-turn ceiling, twelve runs allow 1,920 counted turns. The historical $0.0074 rate gives $14.21 before opening/retry/judge margins; $0.0016 seeded observations give $3.07 but are not a full-game rate. Reserve provisionally $20–$30 for one final campaign, then replace this with a provider-specific measured estimate. Approximately 100k–300k subscription review tokens; API player usage must be counted separately from narrator spend. A failed campaign needing a new sample needs remaining authorized budget or a new approval.

## Tasks

- [ ] Report validator (task 2.6) proven to reject partial or skipped scene lists, substituted snapshots, forced exits, unknown causes, a single failed replicate and false terminal completion.
- [ ] Whole-game fun gate (fun requirement 6) exists, is frozen and calibrated.
- [ ] Twelve continuous final runs frozen (six canonical, six raw profile), one configuration, declared turn ceiling; estimate written first.
- [ ] Every run reports whether the 3C epilogue was offered and taken; a run where it was never offered fails.
- [ ] Save/resume continuity check.
- [ ] Merge, SHA-bound CI and staging deploy verified; no other merges during staged runs.
- [ ] `qualification/final-assessment.md` with the staged SHA, transcripts, outcomes, coverage limits, repair lineage and cost ledger.
