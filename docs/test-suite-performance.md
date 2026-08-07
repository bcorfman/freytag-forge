# Test-suite performance map

The suite uses four pytest tiers. `tests/conftest.py` assigns a tier to every
collected test from the file map below and fails collection if a test has zero
or multiple tiers. The assignment keeps test behavior unchanged while making
the intended boundary visible to contributors.

| Tier | Test files | Runtime dependencies and contract |
| --- | --- | --- |
| unit | Parser, contracts, facts, policies, rules, plot, scene, impact, event, and phase modules | Pure helpers and typed policy contracts; no web client or SQLite. |
| component | `test_adapters.py`, `test_freeform_unit.py`, `test_llm_context.py`, `test_narration_state.py`, `test_story_coherence.py`, `test_world_builder.py`, `test_world_presentation.py` | One subsystem with injected narrators/directors or a focused world projection. |
| integration | `test_cli.py`, `test_cli_more.py`, `test_savegame_sqlite.py`, `test_vector_memory.py`, `test_web_api.py`, `test_web_demo_api.py`, `test_web_surface_parity.py` | Composed turn, persistence, memory, and adapter contracts. |
| evaluation | `test_evaluation.py`, `test_reproducibility.py`, `test_if_output_contract.py` | Cross-genre replay, deterministic artifacts, and output parity. |

The collection guard also parses test modules for duplicate `test_*`
definitions. The per-test health report records source-level construction,
`run_turn`, SQLite, and web-client counts. Unit and component budgets are
available with `--strict-test-budgets`; the normal CI run records counts and
timings without making the existing behavioral suite brittle during migration.

Fast synthetic state/package/proposal/event factories live in
[`tests/fast_fixtures.py`](../tests/fast_fixtures.py). They clone mutable
runtime state from immutable authoring inputs and initialize canonical facts,
so narrow tests do not need to pay for the full story package builder.

Serializer/deserializer contract tests use the injected `state_factory` seam in
`deserialize_state`; SQLite tests retain the real persistence boundary.

## Phase 0 measurement

The post-guard baseline was 577 tests. After the Phase 2–3 consolidation, the
current suite is 561 tests. Current local measurements are 25.21s without
coverage, 69.95s with ordinary coverage, 74.55s with test contexts, and
69.95s with the health report. The current source-level health report
counts 312 full-world builder calls, 68 `run_turn` calls, 32 web clients, and
23 SQLite store constructions. The first runtime-instrumented local
no-coverage run records 456 full-world builds, 157 complete turns, and 70
SQLite-store constructions. The CLI module itself now has 39 direct
`run_turn` calls; remaining calls belong to distinct output, presentation,
memory, and evaluation integration contracts.

The authoritative CI measurement is the required pytest step, not the local
run. Actions run 31143065335/job 92756810662 took 135.37s for pytest and 560
passing tests. The immediately preceding 569-test run took 140.57s, so the
consolidation delivered only a 3.7% CI reduction. The 40% reduction target
remains open.
