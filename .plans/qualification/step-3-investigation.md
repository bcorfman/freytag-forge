# Step 3: investigate causes before selecting a repair

Part of the [qualification plan](../dark-factory-diagnostic-qualification-plan.md). The goal, check, estimate and owner's-word text below is the binding audit text, moved verbatim on 2026-11-23; the task list under it tracks progress. The original detailed requirement is [Phase 4](original-phase-spec.md#phase-4-allow-bounded-investigation-before-committing-to-a-cause).

**Read this when:** you change the diagnose or planner stations, or the evidence a solver can retrieve.

## Goal, check, estimate and owner's word

**Goal.** Extend existing diagnosis/planning with bounded retrieval and revisable hypotheses, including defects with no rule row. Reuse the original Phase 4 interface rather than adding an unrestricted agent.

**Check.** Retrieve predecessor turns, complete relevant prompts, source records, fact producers/readers, eligibility and runtime boundary evidence from the pinned case. Preserve provenance, omissions and reconstruction assumptions. Group affected turns and causal dependencies; prioritize blocked progression and player harm, not first row or frequency alone. Require counterevidence and an experiment that separates plausible causes. Persist the proposed three retrieval rounds, six requests per round and two hypothesis revisions, also bounded by tokens and total ticket budget. Restart must not reset limits. A replay from incomplete history remains reconstructed evidence. On development cases, the real solver must revise a wrong confident rule label and identify a no-rule-row defect without receiving the answer. Compare against the saved baseline using the same model and effort.

**Estimate.** 1–2 days, 200k–450k Ringer tokens; revised development evaluation roughly 80k–180k solver/review tokens. No live narrator dollars required.

**Owner's word.** Approve the station change and exact subscription evaluation budget. No per-case diagnosis approval. Missing evidence produces a bounded blocked result, not a request for the owner to solve the story.

## Tasks

- [ ] Read-only evidence interface: bounded turn ranges with rejected attempts; story records and source; fact producers, readers and siblings; reveal eligibility from a recorded or reconstructed pre-turn state; full prompts, provider features and guard rejections; bounded runtime source. Every response carries locator, snapshot hash, truncation status and provenance.
- [ ] Limits (three retrieval rounds, six requests per round, two hypothesis revisions) as configuration, persisted, never reset on restart; precise blocked-evidence result when evidence is missing or limits run out.
- [ ] Structured causal report, schema- and reference-validated.
- [ ] Planner ranks causes by player harm, not first row or frequency (baseline gap: 18c fixed a one-turn Walt row over the six-turn `lead_outside_scene` cause).
- [ ] Development gate: the solver revises a wrong confident rule label, and finds a defect with no rule row (15d's surrender-style defect), without being told the answer.
- [ ] Compare against the saved baseline with the same model and effort (subscription run; owner's figures first).
