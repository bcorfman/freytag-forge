# Test-suite performance guide

> V2 cutover update: the suite covers compiled-story authoring, the standalone runtime, V2 persistence, the Cloudflare turn-model transport, hosted adapter behavior, and deployment-channel isolation. Retained `data/` remains available to V2 fixtures.

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
| unit | Parser, contracts, facts, policies, rules, plot, scene, impact, event, phase modules, `test_runtime_v2.py`, and `test_deployment_channel_contract.py` | Pure helpers and typed policy contracts; no web client or SQLite. |
| component | `test_adapters.py`, `test_dialogue_policy.py`, `test_freeform_unit.py`, `test_grounded_turn_contract_baseline.py`, `test_llm_context.py`, `test_story_coherence.py`, `test_world_builder.py`, `test_world_presentation.py` | One subsystem with injected narrators/directors or a focused world projection. |
| integration | `test_cli.py`, `test_cli_more.py`, `test_hosted_demo_e2e.py`, `test_mvp_gaps.py`, `test_savegame_sqlite.py`, `test_story_state_artifacts.py`, `test_vector_memory.py`, `test_web_api.py`, `test_web_demo_api.py`, `test_web_surface_parity.py` | Composed turn, persistence, artifact, memory, adapter, and deployed hosted-demo contracts. |
| evaluation | `test_evaluation.py`, `test_reproducibility.py`, `test_runtime_quality_evaluation.py` | Cross-genre replay, deterministic artifacts, and frozen ordinary-runtime quality. |

The collection guard also parses test modules for duplicate `test_*`
definitions. The per-test health report records source-level construction,
runtime `run_turn`, SQLite, and `TestClient` counts. Unit and component budgets are
available with `--strict-test-budgets`; the normal CI run records counts and
timings without making the existing behavioral suite brittle during migration.

Separately, every test receives one exclusive quality classification:
`runtime_safety` or `authoring_quality`. This is not a performance tier and
does not alter the unit/component/integration/evaluation budgets. The
`authoring_quality` suite covers offline completeness, the Phase-1 immutable
Story Blueprint graph contract, cross-genre blueprint fixture loading, and
causal baselines;
its collection totals are informational, never fixed-count gates. See
[genre-blueprint authoring](genre-blueprint-authoring.md) for the command and
current coverage.

## Migration retirement rule

During the LLM-first migration, tests for a surface scheduled for deletion are
not retained merely to preserve coverage. Each such test must either prove a
retained hosted-demo/channel contract, move to a V1 rollback-evidence fixture,
or be removed with the retired surface in Phase 4 or Phase 6. The pure
`test_deployment_channel_contract.py` guard is intentionally retained: it
prevents the root production and `/dev/` staging channels from sharing API,
session, database, or Railway-environment configuration.

Fast synthetic state/package/proposal/event factories live in
[`tests/fast_fixtures.py`](../tests/fast_fixtures.py). They clone mutable
runtime state from immutable authoring inputs and initialize canonical facts,
so narrow tests do not need to pay for the full story package builder.

Serializer/deserializer contract tests use the injected `state_factory` seam in
`deserialize_state`; SQLite tests retain the real persistence boundary.
Adapter tests that do not exercise SQLite persistence inject a fresh
`InMemorySaveStore` per app. This preserves isolation while keeping the real
SQLite boundary in the save/load, artifact, authoring-CLI, evaluation, and parity proofs.
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

Shared web request/response projection behavior is tested below the hosted
adapter boundary. Hosted adapter tests retain one representative lifecycle/
parity path plus credential, backend, CORS, quota,
rate-limit, and fail-closed coverage. The current full-suite runtime report
tracks `TestClient` and SQLite-store constructions; collection totals are
informational and intentionally not pinned.
the prior Phase 2 report recorded 70 SQLite stores and 43 clients in the
boundary-heavy run.

## CI jobs

`Required coverage gate` is the merge-validation job. It runs the complete
suite with ordinary `--cov`, two pytest workers (`-n 2`), the existing 90%
threshold, collection guards, and the health artifact. It is the authoritative
required result; pytest-cov merges the two worker coverage data sets before
enforcing the project-wide threshold. Its uv dependency cache is keyed by
`uv.lock`; the cache hit or miss is recorded in the uploaded `ci-cache.json`
artifact and job summary.

`Fast feedback (unit and component)` runs without coverage for quick pull
request feedback. It is not a replacement for the required coverage gate.
`Coverage context report (informational)` retains `--cov-context=test` for
per-test attribution. It runs nightly at 05:23 UTC and is manually
dispatchable; it is intentionally outside the normal pull-request and
production-promotion path because context coverage reruns the full suite.

The normal CI command does not include `--durations`. Use it only as an opt-in
diagnostic, for example:

```text
TMPDIR=/tmp uv run pytest -q --cov -n 2 --durations=50
```

`test_hosted_demo_e2e.py` is intentionally skipped for local runs without a
deployed URL. A successful trusted `main` `tests` workflow triggers the isolated
staging deployment and `/dev/` Pages bundle. The manual production-promotion
workflow accepts only a full SHA carrying the successful `staging-deployment`
status, checks its production health identity, publishes the root bundle while
preserving `/dev/`, and then runs the hosted-demo E2E at the production root.
The promotion workflow queries Railway for its rollback candidate immediately
before deployment, so no mutable known-good deployment variable is maintained.
The separate `Hosted demo post-deploy E2E` workflow remains manually
dispatchable for diagnosis only and cannot trigger a deployment.

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
TMPDIR=/tmp uv run pytest -q --cov -n 2
TMPDIR=/tmp uv run pytest -q --cov-context=test
TMPDIR=/tmp uv run pytest -q --cov -n 2 --tier-report=/tmp/health.json
```

The required coverage command must remain the full behavioral suite. Benchmark
results should include the commit, exact command, test count, coverage mode,
pytest elapsed time, and a link to the machine-readable health artifact. Use
the implementation plan for the current baseline, comparisons, and phase
exit criteria.

The causal compiler's source loader caches normalized outline inventories by
their exact bytes for the lifetime of the process. This matters because the
inventory contains thousands of outlines and Phase 3 validation previously
parsed and re-hashed the entire file for every `select_outline()` call. Cache
hits still return independent model copies, so callers cannot mutate the
cached authoring input. A changed file gets a new cache key and is fully
revalidated.
