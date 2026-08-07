# Evaluation baseline

Phase 0 freezes a repeatable, deterministic starting point for later engine
changes. The fixture input is [evaluation_fixtures.yaml](../data/evaluation_fixtures.yaml).
It fixes the model identifier, prompt version, temperature, token limit, and
seed for each evaluation run.

## Fixture slices

| Fixture | Genre | What it covers | Seed |
| --- | --- | --- | --- |
| Mystery investigation | mystery | investigation and evidence | 101 |
| Fantasy journey | fantasy | travel and adventure | 202 |
| Sci-fi technical crisis | sci-fi | technical pressure | 303 |
| Relationship social scene | romance | social and relationship play | 404 |

Each slice initializes a package, saves and loads it, and replays its scripted
commands twice with the same result. Evaluation failures are derived from
structured artifacts, with categories for contradiction, impossible action,
hidden-information leak, role drift, causal omission, uncommitted narration,
repetitive scene pressure, and blocked player agency.

## Recorded baseline

Recorded 2026-08-06 on the repository test environment:

| Measure | Result |
| --- | --- |
| Full test suite | 557 passed in 55.59s, no warnings |
| Branch coverage | 90.14% |
| Local web ordinary turn | 10 stub-model calls; 268.9 ms |
| Hosted-demo ordinary turn | 10 stub-model calls; 11.7 ms |

The current pre-performance-refactor measurement is 569 collected and passing
tests in 77.51s with 90.04% branch coverage. The duplicate CLI definition
identified by the performance plan was corrected during Phase 0; with the
seven suite-health guard tests, plus the consolidated CLI cases removed in
Phases 2–3, the expected collection count is now 561. The
older 557-test row above is retained as the original recorded
baseline.

The surface timings use FastAPI's in-process test client and the frozen
`phase0-deterministic-stub-v1` response. They measure orchestration rather
than network/model service latency. The call counts are the useful baseline:
later phases should reduce them while retaining fact validation and fail-closed
surface behavior.

After the Phase 2–3 changes, the suite has 561 passing tests with 90.01%
branch coverage. The current local no-coverage run is 25.21s; ordinary
coverage is 69.95s; coverage with test contexts is 74.55s; and coverage with
the health report is 69.95s. The authoritative Actions run
31143065335/job 92756810662 completed pytest in 135.37s. The health report
currently records source-level counts of 312 full-world builds, 68
`run_turn()` calls, 32 web clients, and 23 SQLite stores. The first
runtime-instrumented local no-coverage run records 456 full-world builds, 157
complete turns, and 70 SQLite-store constructions; these are the new workload
baseline for Phases 1–2.

The authoritative post-change Actions job [31147792358](https://github.com/bcorfman/freytag-forge/actions/runs/31147792358)
on commit `9d8d81ff86ee5430d34afdb87108f545f73988e8` completed 561 tests with
90.03% coverage in 114.20s wall time (112.68s CPU), 15.6% below the 135.37s
baseline. Its health artifact recorded 433 full-world builds, 157 complete
turns, and 70 SQLite stores.

Phase 7 local verification on 2026-08-07 completed 550 tests in 39.27s with
90.19% total coverage. New rendering regressions verify that deterministic
affordances use one story-model rendering call and that accepted prose cannot
append narration-derived fact operations. The verification command was
`TMPDIR=/tmp uv run pytest -q`.

Phase 8 local verification completed 555 tests in 13.50s without coverage and
retained 90% total coverage with `TMPDIR=/tmp uv run pytest -q --cov`. The new
offline package checks cover deterministic reachability/ending validation,
parallel specialist review, bounded recovery records, and all six play styles
for every frozen fixture.

Phase 9 cutover verification completed the full suite with branch coverage at
the required 90% threshold. The separate cutover contract gate runs the frozen
fixture/evaluation report, local and hosted API smoke suites, and artifact
integrity checks; its workflow artifact is retained as `cutover-contracts`.
