# Test-suite performance guide

The live implementation checklist, measured results, and phase status are
maintained in the [test-suite performance implementation plan](../.plans/test-suite-performance-plan.md).
This guide documents the stable test-suite conventions; update the plan when
recording new benchmarks or changing completion status.

The suite uses four pytest tiers. `tests/conftest.py` assigns a tier to every
collected test from the file map below and fails collection if a test has zero
or multiple tiers. The assignment keeps test behavior unchanged while making
the intended boundary visible to contributors.

| Tier | Test files | Runtime dependencies and contract |
| --- | --- | --- |
| unit | Parser, contracts, facts, policies, rules, plot, scene, impact, event, and phase modules | Pure helpers and typed policy contracts; no web client or SQLite. |
| component | `test_adapters.py`, `test_dialogue_policy.py`, `test_freeform_unit.py`, `test_llm_context.py`, `test_story_coherence.py`, `test_world_builder.py`, `test_world_presentation.py` | One subsystem with injected narrators/directors or a focused world projection. |
| integration | `test_cli.py`, `test_cli_more.py`, `test_mvp_gaps.py`, `test_savegame_sqlite.py`, `test_story_state_artifacts.py`, `test_vector_memory.py`, `test_web_api.py`, `test_web_demo_api.py`, `test_web_surface_parity.py` | Composed turn, persistence, artifact, memory, and adapter contracts. |
| evaluation | `test_evaluation.py`, `test_reproducibility.py`, `test_if_output_contract.py` | Cross-genre replay, deterministic artifacts, and output parity. |

The collection guard also parses test modules for duplicate `test_*`
definitions. The per-test health report records source-level construction,
runtime `run_turn`, SQLite, and `TestClient` counts. Unit and component budgets are
available with `--strict-test-budgets`; the normal CI run records counts and
timings without making the existing behavioral suite brittle during migration.

Fast synthetic state/package/proposal/event factories live in
[`tests/fast_fixtures.py`](../tests/fast_fixtures.py). They clone mutable
runtime state from immutable authoring inputs and initialize canonical facts,
so narrow tests do not need to pay for the full story package builder.

Serializer/deserializer contract tests use the injected `state_factory` seam in
`deserialize_state`; SQLite tests retain the real persistence boundary.
Adapter tests that do not exercise SQLite persistence inject a fresh
`InMemorySaveStore` per app. This preserves isolation while keeping the real
SQLite boundary in the save/load, artifact, CLI, evaluation, and parity proofs.
The few component tests that call `run_turn()` do so deliberately to verify
room-transition rendering and follower continuity; the bootstrap save/load
case in `test_turn_runtime.py` is explicitly marked integration.

Complete-turn tests are retained only for distinct orchestration contracts.
The health artifact records the contract class, commands, and retention reason
for each test that invokes `run_turn()`. The current classes are proposal/commit
contract, deterministic affordance, dialogue boundary, recovery/confirmation,
output contract, persistence, and evaluation. Wording and alias matrices belong
in direct policy tests; branches sharing one setup should clone the setup state
instead of repeating a warning, bootstrap, or replay turn.

Shared web request/response projection behavior is tested below the adapter
boundary in `test_web_runtime.py`. Local and hosted adapter tests retain one
representative lifecycle/parity path plus credential, backend, CORS, quota,
rate-limit, and fail-closed coverage. The current full-suite runtime report
tracks `TestClient` and SQLite-store constructions; collection totals are
informational and intentionally not pinned.
the prior Phase 2 report recorded 70 SQLite stores and 43 clients in the
boundary-heavy run.

## CI jobs

`Required coverage gate` is the merge-validation job. It runs the complete
555-test suite with ordinary `--cov`, the existing 90% threshold, collection
guards, and the health artifact. It is the authoritative required result. Its
uv dependency cache is keyed by `uv.lock`; the cache hit or miss is recorded in
the uploaded `ci-cache.json` artifact and job summary.

`Fast feedback (unit and component)` runs without coverage for quick pull
request feedback. It is not a replacement for the required coverage gate.
`Coverage context report (informational)` retains `--cov-context=test` for
per-test attribution; it is separate because context coverage is slower than
ordinary coverage on this project.

The normal CI command does not include `--durations`. Use it only as an opt-in
diagnostic, for example:

```text
TMPDIR=/tmp uv run pytest -q --cov --durations=50
```

The manual `test-suite five-run benchmark` workflow runs the exact required
coverage command five times on `ubuntu-latest`, reports every sample and their
median, and uploads each health report. Record that workflow URL with timing
claims; local timings do not establish the CI target.

## Measuring locally

Use the same environment and temporary directory convention as CI:

```text
TMPDIR=/tmp uv run pytest -q
```

For performance diagnosis, compare these variants on the same commit:

```text
TMPDIR=/tmp uv run pytest -q --no-cov --collect-only
TMPDIR=/tmp uv run pytest -q --no-cov
TMPDIR=/tmp uv run pytest -q --cov
TMPDIR=/tmp uv run pytest -q --cov-context=test
TMPDIR=/tmp uv run pytest -q --cov --tier-report=/tmp/health.json
```

The required coverage command must remain the full behavioral suite. Benchmark
results should include the commit, exact command, test count, coverage mode,
pytest elapsed time, and a link to the machine-readable health artifact. Use
the implementation plan for the current baseline, comparisons, and phase
exit criteria.
