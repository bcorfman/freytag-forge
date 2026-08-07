# Test-suite performance plan

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

- [ ] Run the same four variants in a disposable Actions benchmark job and
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

- [ ] There is a reproducible top-cost list from the actual CI command.
- [ ] The cost of `--cov-context=test`, the health hook, collection, and test
  bodies is measured separately.
- [ ] At least two CI runs establish a baseline within an explicitly recorded
  variance range.
- [ ] No test is deleted or merely moved to another tier based only on local
  timing or source-reference counts.

## Workload reduction

### Phase 1 — Remove repeated full-world construction

The first implementation target is repeated construction, not test count.
For each top-cost test, replace only the unnecessary portion with injected
minimal state/package fixtures. A test may retain the full builder when world
realization, canonical identity, cross-genre data, or runtime wiring is the
behavior under test.

- [ ] For every top-20 full-world test, document why the full world is needed;
  otherwise migrate it to `tests/fast_fixtures.py` or a narrower factory.
- [ ] Convert pure parser, fact, policy, contract, context, formatter, and
  renderer assertions to tiny synthetic state.
- [ ] Convert serializer payload/normalization cases to injected state
  factories; retain real SQLite round trips as integration tests.
- [ ] Ensure fixture cloning is immutable-per-test and cannot share facts or
  RNG state across tests.
- [x] Add a runtime counter, not just an AST/source counter, for calls to
  `build_default_state()` and report it by tier.
- [ ] Reduce full-world builds from 312 source references to fewer than 150
  actual invocations in the complete suite, then verify the measured pytest
  time changed on Actions.
- [ ] Keep unit/component tests free of SQLite, web clients, and complete
  turn orchestration unless an explicit exception is recorded.

### Phase 1 exit criteria

- [ ] Actual full-world invocations are below 150.
- [ ] The top-20 report shows a measurable reduction in setup/call time.
- [ ] Two CI benchmark runs show at least a 15% reduction from the 135.37s
  baseline, or the benchmark identifies a non-test-execution bottleneck that
  must be addressed next.
- [ ] Coverage and all guardrails pass.

### Phase 2 — Reduce orchestration and replay work

The previous Phase 2 counted fewer CLI tests but left expensive orchestration
in many remaining tests. This phase must reduce complete turn work itself.

- [x] Add a runtime counter for `run_turn()` and record commands/turns per
  test, not only references in source.
- [ ] For each test invoking `run_turn()`, classify it as one of:
  proposal/commit contract, deterministic affordance, dialogue boundary,
  recovery/confirmation, output contract, persistence, or evaluation.
- [ ] Retain one integration proof per distinct orchestration contract and
  move wording/normalization matrices to direct policy tests.
- [ ] Parameterize equivalent inputs only when the parameter cases share one
  fixture setup and do not multiply complete-world/replay work unnecessarily.
- [ ] Shorten replay scripts to the minimum turns needed to prove the stated
  invariant. Use direct replay-signature tests for determinism and one real
  save/load continuation test for composition.
- [ ] Keep one compact cross-genre smoke matrix and avoid repeating the same
  long command sequence for every genre unless the genre-specific behavior is
  the assertion.
- [ ] Reduce actual complete `run_turn()` invocations below 40 and document
  every remaining integration/evaluation invocation.
- [ ] Use mutation or targeted fault-injection checks before deleting or
  merging tests covering validators, fact commits, persistence integrity,
  speaker checks, and fail-closed behavior.

### Phase 2 exit criteria

- [ ] Actual complete-turn invocations are below 40.
- [ ] The top-20 CI report no longer contains redundant replay/orchestration
  cases.
- [ ] Two CI benchmark runs show at least a 25% reduction from baseline, or
  the remaining cost is demonstrated to be outside test execution.
- [ ] No coverage or behavioral guardrail regresses.

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
- [ ] Actual full-world builds below 150 and actual complete-turn calls below
  40, with both counts reported in CI artifacts.
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
