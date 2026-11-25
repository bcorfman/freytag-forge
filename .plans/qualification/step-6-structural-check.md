# Step 6: establish the scope of the whole-game structural check

Part of the [qualification plan](../dark-factory-diagnostic-qualification-plan.md). The goal, check, estimate and owner's-word text below is the binding audit text, moved verbatim on 2026-11-23; the task list under it tracks progress. 

**Read this when:** you change the carry matrix, scripted journeys, the unreachable-content gate or the coverage ledger.

## Goal, check, estimate and owner's word

**Goal.** Ensure every supported branch and recovery has an authored earned continuation, while accurately reporting what the existing carry search covers.

**Check.** Retain one-branch per-change and pairwise nightly checks. Produce a nine-scene coverage ledger of entry-state classes, action classes, pressure responses, earned exits and terminal ending. Add counterexamples for interacting deviations, custody/location changes and missing aftermath. Establish that any state merging preserves future eligibility, world behavior, timing and ending outcomes; do not assume the two-record history projection is universally sufficient. Either exhaust the declared finite abstraction or state unexamined classes explicitly; exhaustion of resource limits is inconclusive. Use branch/no-strand reports and targeted scripted journeys to fill evidenced gaps, not brute-force enumeration that repeats the failed map-size work. Search proving an exit exists does not prove a blind player can discover it. N-3 belongs in the development backlog under the already recorded adopt decision (owner, 2026-11-23: the epilogue must be reachable); it does not become a holdout by hiding its name. Add a free gate that fails when an authored storylet is offered in no scripted journey and is not on an owner-approved retirement list, so the next N-3 is found by the factory, and list every storylet in the coverage ledger as reachable or retired.

**Estimate.** 1–3 days, 150k–400k Ringer tokens and 50k–100k review tokens; local search $0. Runtime estimate must be measured on healthy and deliberately broken fixtures before acceptance; the historical 127-second/55-minute results are not current guarantees.

**Owner's word.** Approve harness changes and any larger resource budget. No new retire-versus-adopt decision for N-3 unless an explicit later instruction overrides the recorded adoption. Do not weaken the gate to meet a runtime target.

## Tasks

- [x] **Unreachable-content ratchet**: `tests/test_known_unreachable_ratchet.py` and `tests/fixtures/known_unreachable_approved.json` (the four N-3 IDs; the set may only shrink) (PR #825, `97fdde35`).
- [x] **Fast journey reachability check** `factory.checks.library.journey_reachability_check()` (92 journeys, `--run-nightly -n 8`, 240 s budget) (PR #825).
- [x] Wire the reachability check into station 5's free gates: `journey_reachability` gate in `factory/stations/free_gates.py`, after the carry matrix and before ruff, runs only for story-data tickets (a `source_root` key or a path under the story root); payload `journey_reachability` true or false overrides; 240 s timeout (rounds 32a and 32b, local, not pushed).
- [ ] Nine-scene coverage ledger: entry-state classes, action classes, pressure responses, earned exits, terminal ending; every storylet listed reachable or retired.
- [ ] Counterexamples for interacting deviations, custody and location changes, and missing aftermath.
- [ ] Show that state merging preserves future eligibility, world behavior, timing and endings, or list the unexamined classes.
- [ ] Runtime measured on healthy and deliberately broken fixtures before acceptance.
- [ ] Remove N-3's strict `xfail` when Step 4 lands the repair.
