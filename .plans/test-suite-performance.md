# Test Suite Performance and Signal Plan

## Objective

Reduce the GitHub Actions test runtime from the current 569-test baseline of
approximately 140 seconds while preserving behavioral confidence, generalized
cross-genre coverage, persistence/integrity guarantees, and the project-wide
90% coverage requirement.

The central diagnosis is that many tests described as unit tests repeatedly
execute the complete runtime stack. The suite currently contains approximately
333 `build_default_state()` calls, 89 `run_turn()` calls, 36 FastAPI client
constructions, and 20 SQLite store constructions. The optimization strategy
is to move assertions down to the narrowest useful boundary and retain a
smaller number of explicit integration tests for orchestration contracts.

## Baseline and guardrails

Record before each phase:

- total test count and pass/fail result;
- wall-clock time with and without coverage;
- slowest 20 tests from `--durations`;
- statement and branch coverage;
- number of `build_default_state`, `run_turn`, `TestClient`, and
  `SqliteSaveStore` calls in tests;
- collection count, including duplicate or overwritten test definitions.

Use the WSL-safe invocation documented in `AGENTS.md`:

```text
TMPDIR=/tmp uv run pytest -q
```

Do not reduce coverage by removing production modules from coverage scope,
weakening `--cov-fail-under`, or replacing behavior assertions with snapshots
that merely exercise code. Facts remain canonical, web and hosted-demo
adapters remain separate, and ordinary gameplay behavior remains proposal-first.

## Target test architecture

Use four explicit tiers:

1. **Unit** — pure parser, policy, contract, formatter, fact, rule, and
   serializer tests with tiny synthetic inputs and no full application startup.
2. **Component** — one subsystem plus injected fakes, such as the freeform
   policy, narrator boundary, persistence adapter, or renderer.
3. **Integration** — a small number of real `run_turn`, SQLite, web, and
   story-director flows proving composition and adapter contracts.
4. **Evaluation/full** — cross-genre deterministic replay, artifact integrity,
   local/hosted parity, and longer scenario tests.

The default PR command should run unit, component, and a compact integration
smoke set. The full evaluation tier should remain available and run in CI on
the main branch or as a dedicated required job according to repository policy.
No behavior is removed solely because it is moved to a slower tier.

## TDD guards against regression

Every test-suite performance change follows this loop:

1. Write a failing test or guard that expresses the intended behavior and
   performance boundary.
2. Make the smallest fixture, production, or test change needed to satisfy it.
3. Run the narrow test first, then the relevant tier, then the full suite.
4. Review timing, coverage, collection count, and fixture-use deltas before
   merging.

Add these guards during the first implementation phase and keep them in the
repository:

- **Tier enforcement:** configure markers and CI commands so unit tests cannot
  silently depend on full web apps, SQLite stores, outbound transports, or
  full-world builders without being marked component/integration/evaluation.
- **Collection integrity:** add a collection-time check that fails on duplicate
  test function names, unexpected collection-count changes, or tests collected
  outside the declared tier paths.
- **Fixture budgets:** add a test-only counter or instrumentation hook for
  `build_default_state()`, `run_turn()`, `TestClient`, and SQLite construction.
  Enforce budgets for the unit/component tiers and report full-suite counts as
  CI artifacts.
- **Per-test timing budgets:** establish warning and failure thresholds for
  unit/component tests, with a deliberately higher budget for integration and
  evaluation tests. A new slow test must be explicitly marked and justified.
- **Coverage-context review:** run coverage with test contexts and fail or
  require review when a change adds many tests but contributes no new covered
  lines, unless the tests are documented contract, negative-path, or
  cross-boundary coverage.
- **Mutation guards:** periodically mutate selected validators, fact commits,
  speaker checks, persistence checks, and hosted fail-closed branches. The
  retained suite must detect those mutations before tests are deleted or
  consolidated.
- **Fixture isolation:** test that shared package fixtures are immutable and
  runtime state is cloned/reset per test. Never solve performance by sharing
  mutable canonical facts across tests.
- **Integration quota:** keep a small, explicit budget for tests invoking the
  complete `run_turn()` or web orchestration path. New coverage should prefer
  the narrowest boundary that proves the behavior.
- **CI trend tracking:** publish test count, tier counts, total duration,
  slowest tests, coverage, and fixture-construction counts. Fail on a sustained
  regression rather than allowing gradual accumulation.
- **Fast-path developer command:** maintain a documented command for the unit
  and component tiers, and require it in pre-commit or pull-request checks so
  contributors receive feedback before the full suite runs.

These guards must themselves be cheap, deterministic, and independent of
network/model credentials. They enforce test design and suite health; they do
not weaken behavioral coverage requirements.

## Phase 0 — Instrumentation and test inventory

### Work

- [x] Add or standardize markers for `unit`, `component`, `integration`, and
  `evaluation` without changing test behavior.
- [x] Add a documented timing command using `--durations=50` and a repeatable
  collection command.
- [x] Use coverage contexts to identify tests that add no uniquely covered
  production lines, while treating that result as a review signal rather than
  an automatic deletion rule.
- [x] Detect duplicate test function names during collection or linting. Fix the
  duplicate `test_run_turn_fails_closed_for_parroting_npc_dialogue` definition
  in `tests/test_cli.py`, where one definition currently overwrites the other.
- [x] Produce a table mapping each test file to its tier, runtime dependencies,
  number of full-world builds, and intended contract.
- [x] Write the first failing guard tests for duplicate names, tier markers,
  fixture-construction budgets, and per-test timing reporting.

### Exit criteria

- [x] Baseline is recorded locally and in CI-compatible form.
- [x] Every test has an explicit tier or a documented exception.
- [x] Collection reports the expected test count with no silently overwritten tests.
- [x] Coverage-context output is available for later deletion/consolidation review.
- TDD guards fail on a deliberately introduced duplicate name or an unmarked
  full-world/unit-tier dependency.

## Phase 1 — Build fast fixtures and narrow pure tests

### Work

- [x] Add reusable factories for tiny rooms, actors, items, facts, proposals,
  events, and minimal `GameState` instances.
- [x] Add a fixture for an immutable authoring/world package and clone it when a
  mutable runtime state is required; never share mutable facts between tests.
- Replace `build_default_state()` in parser, policy, formatter, contract,
  context, and renderer tests where the default world is not the behavior under
  test.
- Keep `build_default_state()` only where package realization, canonical
  identity, cross-genre data, or full runtime wiring is part of the assertion.
- Inject narrators, directors, coherence gates, memory stores, and persistence
  adapters through existing Protocols rather than constructing real services.
- [x] Add tests proving the fast fixtures preserve fact invariants and cannot leak
  mutations between test cases.

### Priority files

- `tests/test_freeform_unit.py`
- `tests/test_cli.py` pure helper sections
- `tests/test_llm_context.py`
- `tests/test_narration_state.py`
- `tests/test_world_presentation.py`
- `tests/test_world_builder.py`
- `tests/test_adapters.py`

### Exit criteria

- Full-world construction calls decrease substantially, with a target below
  150 calls across the suite.
- Unit/component tests do not create SQLite files, FastAPI clients, or full
  story-agent orchestration unless explicitly marked otherwise.
- Coverage remains at least 90%, including branches.
- The unit/component subset is measurably faster than the current full suite.
- Unit/component fixture budgets and timing thresholds pass in CI.

## Phase 2 — Consolidate freeform and CLI coverage

### Work

- [x] Move semantic normalization, dialogue-scope, speaker validation, fallback,
  and fact-operation matrices to direct freeform policy tests.
- [x] Parameterize equivalent input families instead of repeating full `run_turn`
  calls for each wording variant.
- [x] Retain a compact CLI integration set covering:
  - one ordinary proposal-first turn;
  - one deterministic movement/inventory affordance;
  - one addressed-NPC failure and one valid reply;
  - one high-impact confirmation/replan path;
  - one output/editor path;
  - one save/load path.
- [x] Merge or remove overlapping CLI tests that assert the same output through
  different narrators or equivalent command phrasings.
- [x] Preserve explicit regression tests for wrong-speaker, prompt-parroting,
  protected-knowledge leakage, off-scene targeting, and uncommitted narration.

### Exit criteria

- [x] `tests/test_cli.py` is no longer the broadest duplicate integration harness.
- [x] `run_turn()` calls in the CLI harness are reduced from approximately 89 toward
  a target below 40, with each remaining call tied to a distinct orchestration
  contract.
- [x] All retained behavior categories have at least one direct unit test and one
  integration test only where composition matters.

## Phase 3 — Reduce persistence and replay cost

### Work

- [x] Separate serializer/deserializer tests from SQLite integration tests.
- [x] Keep one focused SQLite round-trip test for facts, projections, RNG, and
  integrity metadata; cover individual normalization branches directly with
  payloads rather than rebuilding worlds for every case.
- [x] Refactor the long post-load replay test into:
  - a short save/load continuation test;
  - a pure replay-signature determinism test;
  - one artifact-writing/integrity test.
- Reduce repeated command sequences in the four evaluation fixtures. Validate
  all genres with cheap package/schema assertions, then reserve complete
  save/load/replay flows for a representative fixture plus a compact
  cross-genre smoke matrix.
- [x] Retain the full four-fixture replay matrix in the evaluation/full tier.

### Exit criteria

- [x] The SQLite/replay cluster no longer dominates the slowest-test report.
- [x] Evaluation tests continue to cover mystery, fantasy, science-fiction, and
  relationship-driven packages.
- [x] Save/load, replay, artifact hashes, RNG state, and fact authority remain
  tested through explicit integration contracts.

## Phase 4 — Consolidate rendering, world presentation, and coherence tests

### Work

- Test room-block formatting and line-shortening directly with small synthetic
  room/context values.
- Retain one assembled CLI output test proving room ordering, narration
  precedence, and debug separation.
- Review `test_if_output_contract.py`, `test_story_coherence.py`, and
  `test_world_presentation.py` together; merge tests that traverse the same
  renderer and differ only in redundant prose assertions.
- Keep distinct tests for fact-backed identity, room transitions, assistant
  following, visible-item aliases, and protected/internal debug content.

### Exit criteria

- Rendering tests no longer rebuild the full default world for every formatting
  assertion.
- Coverage remains stable while the number of broad orchestration traversals
  falls.
- Output-contract tests assert externally meaningful contracts rather than
  implementation-path repetition.

## Phase 5 — Consolidate web and adapter tests

### Work

- Build shared test helpers for local and hosted app construction, with injected
  fake runtime/narrator/persistence dependencies.
- Test shared web behavior below the `storygame.web` / `storygame.web_demo`
  adapter boundary once, then retain adapter-specific tests for credentials,
  hosted fail-closed statuses, quotas, rate limits, CORS, and backend selection.
- Keep one local/hosted parity integration test and one representative session
  lifecycle test per surface.
- Parameterize adapter response/error/retry matrices. Test request building,
  payload parsing, retry classification, and error mapping directly; retain
  only a small number of end-to-end adapter calls with mocked transport.
- Avoid creating a new temporary SQLite database and FastAPI `TestClient` for
  every pure response-shaping test.

### Exit criteria

- `TestClient` constructions and SQLite setup are materially reduced from the
  current 36 and 20 instances.
- Local and hosted deployment boundaries remain independently tested.
- Hosted failures still fail closed and do not require local OpenAI credentials.

## Phase 6 — Coverage-driven deletion and validation

### Work

- Re-run coverage contexts and classify each low-unique-coverage test as:
  - behaviorally unique and retained;
  - duplicate and deleted;
  - merged into a parameterized or higher-level test; or
  - intentionally retained as an integration/evaluation contract.
- Use mutation testing or targeted fault injection on candidate deletions to
  ensure assertions detect meaningful regressions.
- Remove obsolete helpers, duplicate fixtures, and tests made redundant by
  lower-level coverage.
- Update test documentation and CI commands to make tier boundaries explicit.
- Run the TDD guards against the final suite and add a small intentional
  regression test to verify each guard reports the expected failure mode.
- Run the full required command with `TMPDIR=/tmp`, including coverage and the
  complete evaluation tier.

### Final success targets

- PR/default test tier: under 30 seconds locally where practical.
- Full suite: at least 40% faster than the current CI baseline, with a target
  near or below 85 seconds on the existing GitHub Actions runner class.
- 90% minimum project coverage preserved, with no coverage-scope exclusions
  added to hide untested production code.
- No loss of cross-genre, persistence, artifact-integrity, epistemic-boundary,
  NPC-role, or hosted fail-closed regression coverage.
- No duplicate test definitions and no unexplained collection-count changes.
- New tests cannot increase the unit/component runtime or full-world fixture
  budget without an explicit tier change and review.

## Review checklist for every deletion or merge

- What production behavior does this test uniquely assert?
- Is that behavior already asserted at a narrower boundary?
- Does the replacement preserve negative/error-path coverage?
- Does it preserve fact-authority and observer/speaker-boundary guarantees?
- Does it preserve at least one integration proof that the components compose?
- Does coverage stay above 90% without broadening exclusions?
- Does the change reduce runtime or fixture setup measurably?
