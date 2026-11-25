# Step 4: complete repairs that the current menu cannot express

Part of the [qualification plan](../dark-factory-diagnostic-qualification-plan.md). The goal, check, estimate and owner's-word text below is the binding audit text, moved verbatim on 2026-11-23; the task list under it tracks progress. The original detailed requirement is [Phase 5](original-phase-spec.md#phase-5-make-structural-repair-a-real-factory-capability); N-3 detail is in [fun requirements](fun-requirements.md#the-n-3-decision).

**Read this when:** you build the structural or adaptive repair route, or work on N-3.

## Goal, check, estimate and owner's word

**Goal.** Turn a justified structural or adaptive route into bounded work with a verified result. Reuse supported follow-up realizations, source-record edits, pacing and Worldkeeper capabilities before inventing a technique. Keep story-specific repairs in authored data; world-only rules remain `World` methods and tests in `packages/worldkeeper`.

**Check.** The solver writes the Phase 5 repair contract itself: source scope, preserved intent, causal prediction, downstream readers, forbidden shortcuts and acceptance checks. Ringer implements it in an owned checkout. A parent waits for child implementation, independent diff review, free gates, appropriate experiment and fun review; then resumes against the resulting source hash. Test duplicate prevention, restart, rejected repair, exhausted budget and dependency-cycle prevention. Adaptive guidance uses a responding blind player; fixed actions cannot demonstrate that a cue changes choices. Known structural cases exercise this route but are not independence evidence. **First real use: N-3** (the 3C epilogue must be reachable; see "Fun requirements and the N-3 decision"). An unsupported policy change still stops safely; ordinary supported repairs must not park for manual fix selection.

**Estimate.** 2–3 days, 300k–700k Ringer tokens, 100k–250k planning/review tokens. Development live experiment, if necessary, approximately $0.50–$3 per matched arm pair; exact turns, openings, retries and judges determine the run estimate.

**Owner's word.** Approve station work, ownership boundaries and spend. Claude authors player-facing prose; Luna/Ringer implements and tests; Opus owns fun-judge design/checking and required high-risk review. Existing factory-fix merge authority applies only after its gates; hand-built station PRs still require the owner's word.

## Tasks

- [ ] Solver-written repair contract (source scope, preserved intent, causal prediction, downstream readers, forbidden shortcuts, acceptance checks).
- [ ] Persisted parent/child work: the parent waits for the child's implementation, independent diff review, free gates, experiment and fun review, then resumes against the new source hash.
- [ ] Tests for duplicate prevention, restart, rejected repair, exhausted budget and dependency-cycle prevention.
- [ ] Adaptive guidance tested with a responding blind player, never fixed replay.
- [ ] Ordinary supported repairs no longer park as `owner_wait`; an unsupported policy change still stops safely.
- [ ] **N-3 through the route** (class `unreachable_authored_content`): the four pinned journeys pass without `xfail`; SL-3C-D and SL-3C-E are offered after both evacuation routes; no stuck state in the epilogue; nothing changes outside it. Any world-model support (for example "ending latched but play continues") is a worldkeeper `World` method built first.
