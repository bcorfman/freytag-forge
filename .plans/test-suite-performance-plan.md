# Test-suite performance implementation plan

## Problem statement

The previous plan optimized the shape of the test suite but did not optimize
the workload that GitHub Actions actually executes. Removing nine tests and
removing `--durations=50` changed the linked CI result from 140.57s for 569
tests to 135.37s for 560 tests. That is only a 3.7% improvement. The target
is therefore not met.

The authoritative performance metric is the elapsed time printed by the
required `pytest` step on the existing `ubuntu-latest` runner class. Local
timings are useful for diagnosis, but cannot be used to claim the CI target.
Test count, source-level call counts, and coverage are guardrails; none is a
proxy for elapsed time.

## Current measured baseline

Measured from Actions run `31143065335`, job `92756810662`, on 2026-08-07:

| Measure | Current result |
| --- | ---: |
| Collected/passing tests | 560 |
| Required coverage | 90.01% |
| Pytest step on GitHub Actions | 135.37s |
| Whole job | 146–147s |
| Local no-coverage run | 25.21s |
| Local coverage run | 69.95s |
| Source-level `build_default_state()` references | 312 |
| Source-level `run_turn()` references | 68 |
| Source-level `TestClient` constructions | 32 |
| Source-level SQLite store constructions | 23 |

Latest benchmark record:

| Measure | Result |
| --- | ---: |
| Commit | [`9d8d81ff86ee5430d34afdb87108f545f73988e8`](https://github.com/bcorfman/freytag-forge/commit/9d8d81ff86ee5430d34afdb87108f545f73988e8) |
| Actions run/job | [`31147792358`](https://github.com/bcorfman/freytag-forge/actions/runs/31147792358) / [`92770845095`](https://github.com/bcorfman/freytag-forge/actions/runs/31147792358/job/92770845095) |
| Exact command | `TMPDIR=/tmp uv run pytest -q --cov-context=test --expected-test-count=561 --tier-report=artifacts/test-suite-health.json` |
| Tests / coverage | 561 passed / 90.03% |
| Pytest wall / CPU | 114.20s / 112.68s |
| Runtime full-world builds / turns / SQLite stores | 433 / 157 / 70 |
| Health artifact | [`test-suite-health`](https://github.com/bcorfman/freytag-forge/actions/runs/31147792358/artifacts/8982161716), SHA-256 `4e260636eb5d05d50b08f502290800224258a3d0df3e5f75d8058a91c49a5c1b` |

This is a 15.6% reduction from the 135.37s baseline. It is the first
authoritative post-change benchmark; the two-run Phase 1 criterion remains
open.

Phase 0 disposable benchmark baseline runs were completed twice on commit
`785418f8495f3836be9df774e99396edef0db0c7` using the matrix workflow's exact
commands (`TMPDIR=/tmp uv run pytest -q <variant> --expected-test-count=561
--tier-report=artifacts/<variant>.json`):

| Variant | Run `31154668791` | Run `31154911286` | Median |
| --- | ---: | ---: | ---: |
| `--no-cov` | 40.20s | 28.23s | 34.22s |
| `--cov` | 127.48s | 113.12s | 120.30s |
| `--cov-context=test` | 132.64s | 132.07s | 132.36s |
| `--cov --tier-report` | 127.29s | 126.05s | 126.67s |

Run/job records: [31154668791](https://github.com/bcorfman/freytag-forge/actions/runs/31154668791)
([no-cov](https://github.com/bcorfman/freytag-forge/actions/runs/31154668791/job/92791473838),
[coverage](https://github.com/bcorfman/freytag-forge/actions/runs/31154668791/job/92791473819),
[contexts](https://github.com/bcorfman/freytag-forge/actions/runs/31154668791/job/92791473882),
[health](https://github.com/bcorfman/freytag-forge/actions/runs/31154668791/job/92791473837))
and [31154911286](https://github.com/bcorfman/freytag-forge/actions/runs/31154911286)
([no-cov](https://github.com/bcorfman/freytag-forge/actions/runs/31154911286/job/92792203474),
[coverage](https://github.com/bcorfman/freytag-forge/actions/runs/31154911286/job/92792203432),
[contexts](https://github.com/bcorfman/freytag-forge/actions/runs/31154911286/job/92792203435),
[health](https://github.com/bcorfman/freytag-forge/actions/runs/31154911286/job/92792203487)).
Both health artifacts report 561 tests, 90.03% coverage, 433 full-world
builds, 157 complete turns, and 70 SQLite stores. The ordinary-coverage
variance is 14.36s (12.7%), so runner variance is material.

The subsequent local migration reduced the runtime health counts to 140
full-world builds and 146 complete turns. The required local suite passed 561
tests at 90.03% coverage in 46.56s; the CI confirmation is recorded below.

Post-migration CI confirmation was completed twice on commit
[`cab7564ce6ba075027a19d709a746595311de3e4`](https://github.com/bcorfman/freytag-forge/commit/cab7564ce6ba075027a19d709a746595311de3e4):

| Variant | Run `31173950336` | Run `31184700103` | Median |
| --- | ---: | ---: | ---: |
| `--no-cov` | 22.92s | 25.42s | 24.17s |
| `--cov` | 79.11s | 81.16s | 80.14s |
| `--cov-context=test` | 82.76s | 83.85s | 83.31s |
| `--cov --tier-report` | 80.16s | 79.78s | 79.97s |

Run/job records: [31173950336](https://github.com/bcorfman/freytag-forge/actions/runs/31173950336)
and [31184700103](https://github.com/bcorfman/freytag-forge/actions/runs/31184700103).
Both health artifacts report 561 tests, 90.03% coverage, 140 full-world
builds, 146 complete turns, and 70 SQLite stores. The health-variant median is
79.97s, a 40.9% reduction from the 135.37s baseline.

After the targeted fixture migration and collection benchmark addition, the
same five variants were run twice on commit
[`bcb5cdb9d0239ec01a8d5de06f05ce75126daa20`](https://github.com/bcorfman/freytag-forge/commit/bcb5cdb9d0239ec01a8d5de06f05ce75126daa20):

| Variant | Run `31188890834` | Run `31188909247` | Median |
| --- | ---: | ---: | ---: |
| `--no-cov --collect-only` | 1.63s | 1.68s | 1.66s |
| `--no-cov` | 22.71s | 25.95s | 24.33s |
| `--cov` | 75.91s | 76.59s | 76.25s |
| `--cov-context=test` | 79.90s | 79.24s | 79.57s |
| `--cov --tier-report` | 77.63s | 65.19s | 71.41s |

Run records: [31188890834](https://github.com/bcorfman/freytag-forge/actions/runs/31188890834)
([collection](https://github.com/bcorfman/freytag-forge/actions/runs/31188890834/job/92900358160),
[no-cov](https://github.com/bcorfman/freytag-forge/actions/runs/31188890834/job/92900358134),
[coverage](https://github.com/bcorfman/freytag-forge/actions/runs/31188890834/job/92900358093),
[context](https://github.com/bcorfman/freytag-forge/actions/runs/31188890834/job/92900358215),
[health](https://github.com/bcorfman/freytag-forge/actions/runs/31188890834/job/92900358187))
and [31188909247](https://github.com/bcorfman/freytag-forge/actions/runs/31188909247)
([collection](https://github.com/bcorfman/freytag-forge/actions/runs/31188909247/job/92900426528),
[no-cov](https://github.com/bcorfman/freytag-forge/actions/runs/31188909247/job/92900426611),
[coverage](https://github.com/bcorfman/freytag-forge/actions/runs/31188909247/job/92900426669),
[context](https://github.com/bcorfman/freytag-forge/actions/runs/31188909247/job/92900426378),
[health](https://github.com/bcorfman/freytag-forge/actions/runs/31188909247/job/92900426579)).
All variants passed; both health artifacts report 561 tests, 90.03% coverage,
120 full-world builds, 146 complete turns, and 70 SQLite stores. The large
health-runtime spread confirms that runner variance remains material, so the
new health median is recorded for diagnosis rather than claimed as a second
performance improvement.

The CI command currently is:

```text
TMPDIR=/tmp uv run pytest -q --cov-context=test \
  --expected-test-count=561 \
  --tier-report=artifacts/test-suite-health.json
```

`--durations=50` is a reporting option and must not be treated as a runtime
optimization. The prior run with and without it was effectively identical.

## Non-negotiable guardrails

- Run the full required suite with `TMPDIR=/tmp uv run pytest -q` before
  merging performance work.
- Preserve at least 90% project coverage and all existing coverage scope.
- Preserve cross-genre evaluation, persistence/RNG replay, artifact
  integrity, fact authority, NPC speaker/observer boundaries, and hosted
  fail-closed behavior.
- Do not make the PR check faster by omitting tests, weakening assertions,
  disabling coverage, or moving required tests to an unrequired job.
- Keep `storygame.web` and `storygame.web_demo` independently tested.
- Every timing claim must include: commit SHA, runner/job URL, exact command,
  test count, coverage mode, and pytest elapsed time.
- Repeat a CI benchmark at least twice before accepting a change; use the
  median and retain both raw results.

## Measurement harness (must be completed before more deletion)

### Phase 0 — Establish the actual cost model

- [x] Add a CI benchmark artifact containing, for each test:
  node ID, tier, setup time, call time, teardown time, and whether it creates
  a full world, `TestClient`, SQLite store, or calls `run_turn()`.
- [x] Record separate timings for these local commands on the same commit:

  ```text
  TMPDIR=/tmp uv run pytest -q --no-cov
  TMPDIR=/tmp uv run pytest -q --cov
  TMPDIR=/tmp uv run pytest -q --cov-context=test
  TMPDIR=/tmp uv run pytest -q --cov --tier-report=/tmp/health.json
  ```

- [x] Run the same four variants in a disposable Actions benchmark job and
  compare them with the current required job. This identifies whether the
  cost is coverage, the health hook, test execution, or runner slowdown.
- [x] Add a machine-readable timing summary to the health artifact. Do not
  infer total runtime from the sum of per-test durations without labeling
  setup/collection/teardown overhead.
- [x] Capture CPU time and wall time for the pytest process. If wall time is
  much larger, investigate runner contention or process/file-system waits
  before changing tests.
- [x] Produce a ranked table of the top 20 tests by call time and by setup
  time. The table must include the number of full-world builds and turn
  executions attributable to each test.
- [x] Keep collection-count and duplicate-definition guards.
- [x] Keep tier assignment and health-report generation.

### Phase 0 exit criteria

- [x] There is a reproducible top-cost list from the actual CI command.
- [x] The cost of `--cov-context=test`, the health hook, collection, and test
  bodies is measured separately.
- [x] At least two CI runs establish a baseline within an explicitly recorded
  variance range.
- [x] No test is deleted or merely moved to another tier based only on local
  timing or source-reference counts.

## Workload reduction

### Phase 1 — Remove repeated full-world construction

The first implementation target is repeated construction, not test count.
For each top-cost test, replace only the unnecessary portion with injected
minimal state/package fixtures. A test may retain the full builder when world
realization, canonical identity, cross-genre data, or runtime wiring is the
behavior under test.

The current top-call report's full-world tests have these retained-boundary
reasons:

| Top-cost test group | Why a real world remains necessary |
| --- | --- |
| `test_evaluation.py::test_phase_zero_fixture_initializes_saves_loads_and_replays_deterministically[*]` | Cross-genre package construction plus real SQLite save/load and replay composition. |
| `test_savegame_sqlite.py::test_load_resume_replays_deterministically_with_post_load_commands` | Persistence integrity and post-load continuation across the real store boundary. |
| `test_web_api.py` save/load and turn endpoint tests | Hosted/local adapter wiring, session state, and persistence through the web boundary. |
| `test_web_surface_parity.py::test_first_substantive_turn_matches_between_local_web_and_demo` | Local/hosted adapter parity for a substantive turn. |
| `test_cli.py` replay/save-load tests | CLI orchestration and store composition, including completion behavior. |
| `test_web_demo_api.py` quota/rate-limit/fail-closed tests | Demo adapter lifecycle, quota state, and failure behavior. |
| `test_story_state_artifacts.py::test_story_state_canonical_text_is_stable_across_processes` | Canonical artifact projection from a complete story package. |
| `test_adapters.py::test_openai_adapter_missing_api_key_raises` | Adapter boundary initialization and credential failure behavior. |

Pure context, fact, policy, scene, impact, event, rule, plot, output, and
reproducibility tests use cloned or synthetic state; the two highest-cost
reproducibility/output cases were migrated to cloned state in this pass.

- [x] For every top-20 full-world test, document why the full world is needed;
  otherwise migrate it to `tests/fast_fixtures.py` or a narrower factory.
- [x] Convert pure parser, fact, policy, contract, context, formatter, and
  renderer assertions to tiny synthetic state where the assertion does not
  require authored world realization. The migrated state, impact, and event
  policy cases use `make_tiny_state`; authored presentation/context cases keep
  their explicit story-package boundary.
- [x] Convert serializer payload/normalization cases to injected state
  factories; retain real SQLite round trips as integration tests. The
  `deserialize_state(state_factory=...)` seam and the narrow persistence
  factory now cover the non-SQLite serializer cases.
- [x] Ensure fixture cloning is immutable-per-test and cannot share facts or
  RNG state across tests.
- [x] Add a runtime counter, not just an AST/source counter, for calls to
  `build_default_state()` and report it by tier.
- [x] Reduce full-world builds from 312 source references to fewer than 150
  actual invocations in the complete suite, then verify the measured pytest
  time changed on Actions.
- [x] Keep unit/component tests free of SQLite, web clients, and complete
  turn orchestration unless an explicit exception is recorded. Artifact and
  CLI-composition tests that cross those boundaries are classified as
  integration tests; the remaining component exceptions are the three
  room-transition/follower rendering tests documented in the performance
  guide.

### Phase 1 exit criteria

- [x] Actual full-world invocations are below 150.
- [ ] The top-20 report shows a measurable reduction in setup/call time.
- [x] Two CI benchmark runs show at least a 15% reduction from the 135.37s
  baseline, or the benchmark identifies a non-test-execution bottleneck that
  must be addressed next.
- [x] Coverage and all guardrails pass.

### Phase 2 — Reduce orchestration and replay work

The previous Phase 2 counted fewer CLI tests but left expensive orchestration
in many remaining tests. This phase reduces redundant replay/orchestration
work in the highest-cost tests while retaining the integration contracts that
actually need a complete turn.

The originally proposed hard limit of fewer than 40 complete turns is retired
as a performance requirement. CI showed that the major improvement came from
reducing full-world builds (433 to 140), while complete turns changed only
from 157 to 146. Further reductions should therefore be justified by the
top-cost report or by removing redundant coverage, not by reaching an
arbitrary count.

- [x] Add a runtime counter for `run_turn()` and record commands/turns per
  test, not only references in source.
- [x] For each test invoking `run_turn()`, classify it as one of:
  proposal/commit contract, deterministic affordance, dialogue boundary,
  recovery/confirmation, output contract, persistence, or evaluation.
- [ ] Retain one integration proof per distinct orchestration contract and
  move wording/normalization matrices to direct policy tests.
- [ ] Parameterize equivalent inputs only when the parameter cases share one
  fixture setup and do not multiply complete-world/replay work unnecessarily.
- [x] Shorten replay scripts to the minimum turns needed to prove the stated
  invariant. Use direct replay-signature tests for determinism and one real
  save/load continuation test for composition.
- [x] Keep one compact cross-genre smoke matrix and avoid repeating the same
  long command sequence for every genre unless the genre-specific behavior is
  the assertion.
- [ ] Remove redundant complete `run_turn()` invocations from the top-cost
  tests and document why each remaining integration/evaluation invocation is
  required.
- [ ] Use mutation or targeted fault-injection checks before deleting or
  merging tests covering validators, fact commits, persistence integrity,
  speaker checks, and fail-closed behavior.

### Phase 2 exit criteria

- [ ] The top-20 CI report no longer contains redundant replay/orchestration
  cases, or each retained case has a documented integration/evaluation reason.
- [x] Two CI benchmark runs show at least a 25% reduction from baseline, or
  the remaining cost is demonstrated to be outside test execution.
- [x] No coverage or behavioral guardrail regresses.

### Phase 3 — Reduce web, SQLite, and adapter setup cost

- [ ] Count runtime `TestClient` and SQLite constructions per test.
- [ ] Test shared request/response behavior below the adapter boundary with
  injected fakes; retain adapter-specific credential, quota, rate-limit,
  backend, and fail-closed tests.
- [ ] Retain one local/hosted parity integration test and one representative
  lifecycle test per surface.
- [ ] Reuse only immutable configuration and factories; never share mutable
  application state between tests.
- [ ] Reduce actual client and store constructions by at least 50% without
  weakening isolation.

### Phase 3 exit criteria

- [ ] Web/SQLite setup is no longer in the top-20 cost list except for tests
  whose boundary explicitly requires it.
- [ ] Two CI benchmark runs show at least a 30% reduction from baseline.
- [ ] Local and hosted boundaries and all persistence integrity guarantees
  remain covered.

## CI execution design

### Phase 4 — Make the required CI job observable and efficient

- [ ] Keep the full required coverage suite in the required job.
- [ ] Add a separate fast unit/component job for pull-request feedback; do
  not present it as a replacement for the full suite.
- [ ] Cache uv dependencies using the lockfile and record cache hit/miss.
- [ ] Compare `--cov-context=test` with ordinary coverage in Phase 0. If test
  contexts are materially expensive, run them in a dedicated reporting job
  while keeping ordinary coverage in the required gate; document the tradeoff.
- [ ] Do not add `--durations` to the normal command unless its measured
  overhead is negligible; expose it as an opt-in diagnostic command.
- [ ] Upload the timing/health artifact even on failure.
- [ ] Track the required job's median duration over five runs, not one run.

### Phase 4 exit criteria

- [ ] Required CI remains behaviorally equivalent and coverage-gated.
- [ ] Fast feedback and full validation jobs are clearly named and documented.
- [ ] The required job meets the final timing target on the same runner class.

## Final success criteria

- [ ] 560 or fewer tests only if every removed case is covered by a documented
  narrower contract or mutation check; test count alone is not a target.
- [ ] At least 40% reduction from the 135.37s CI pytest baseline, targeting
  85s or less on the existing GitHub Actions runner class.
- [ ] 90% minimum project coverage, unchanged coverage scope.
- [x] Actual full-world builds below 150, with runtime counts reported in CI
  artifacts; complete-turn counts remain reported for cost diagnosis.
- [ ] No unclassified test in the top-20 timing report exceeds the approved
  tier budget.
- [ ] Five-run median, not a best-case run, satisfies the target.
- [ ] Documentation reports CI measurements separately from local measurements
  and names the exact commit/run used.

## Required review record for each performance change

For every change, record:

1. Which expensive operation was removed or shortened.
2. Which behavior contract still proves it.
3. Before/after runtime on Actions using the exact required command.
4. Before/after runtime counts for world builds, turns, clients, and stores.
5. Coverage and mutation/fault-injection evidence.
6. Any variance caused by runner scheduling or dependency/cache state.

If the measured CI runtime does not improve, the phase is incomplete even if
the test count, source lines, or local timing improves.
